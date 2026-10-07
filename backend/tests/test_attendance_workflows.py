import asyncio
import os
import unittest
from datetime import date, time
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-config.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.api.v1.auth import change_password, login, oauth_callback, register, register_with_oauth
from app.api.v1.attendance import get_roster, mark_roster
from app.api.v1.classes import create_class
from app.api.v1.dashboard import read_summary
from app.api.v1.enrollments import create_enrollment
from app.api.v1.reports import report_rows
from app.api.v1.sessions import create_session, open_session
from app.api.v1.users import create_user
from app.database.base import Base
from app.core.oauth import create_signup_handoff_token, read_signup_handoff_token
from app.models.attendance import Attendance
from app.models.class_model import Class
from app.models.enums import AttendanceStatus, SessionStatus, UserRole
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.attendance import AttendanceBulkMark, AttendanceEntry
from app.schemas.auth import LoginRequest, OAuthRegisterRequest, PasswordChangeRequest, RegisterRequest
from app.schemas.class_schema import ClassCreate
from app.schemas.enrollment import EnrollmentCreate
from app.schemas.session import AttendanceSessionCreate
from app.schemas.user import UserCreate
from app.security.password import verify_password
from unittest.mock import patch
from app.services.class_service import list_accessible_classes
from app.services.session_service import list_accessible_sessions


class AttendanceWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.admin = create_user(
            UserCreate(
                first_name="Ada",
                last_name="Admin",
                email="ada@example.org",
                password="test-password-123",
                role=UserRole.SUPER_ADMIN,
            ),
            self.db,
            None,
        )
        self.student = create_user(
            UserCreate(
                first_name="Sam",
                last_name="Student",
                email="sam@example.org",
                password="student8",
                role=UserRole.STUDENT,
            ),
            self.db,
            self.admin,
        )

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_class_session_attendance_and_reporting(self) -> None:
        class_ = create_class(ClassCreate(name="Hope Class"), self.db, self.admin)
        enrollment = create_enrollment(
            EnrollmentCreate(student_id=self.student.id, class_id=class_.id),
            self.db,
            self.admin,
        )
        self.assertEqual(enrollment.student_id, self.student.id)

        session = create_session(
            AttendanceSessionCreate(
                name="Morning gathering",
                session_type="CLASS",
                session_date=date.today(),
                start_time=time(8, 0),
                end_time=time(9, 0),
                class_id=class_.id,
            ),
            self.db,
            self.admin,
        )
        session = open_session(session.id, self.db, self.admin)
        self.assertEqual(session.status, SessionStatus.OPEN)

        roster = get_roster(session.id, self.db, self.admin)
        self.assertEqual([item["student_id"] for item in roster], [self.student.id])
        mark_roster(
            session.id,
            AttendanceBulkMark(records=[AttendanceEntry(student_id=self.student.id, status=AttendanceStatus.PRESENT)]),
            self.db,
            self.admin,
        )
        mark_roster(
            session.id,
            AttendanceBulkMark(records=[AttendanceEntry(student_id=self.student.id, status=AttendanceStatus.LATE)]),
            self.db,
            self.admin,
        )
        self.assertEqual(
            self.db.scalar(select(func.count(Attendance.id))),
            1,
        )
        self.assertEqual(self.db.scalar(select(Attendance.status)), AttendanceStatus.LATE)

        summary = read_summary(self.db, self.admin)
        self.assertEqual(summary.late, 1)
        self.assertEqual(summary.attendance_rate, 100.0)
        report = report_rows(self.db, self.admin, date.today(), date.today(), class_.id)
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]["student_name"], "Sam Student")

    def test_duplicate_student_in_bulk_submission_is_rejected(self) -> None:
        class_ = create_class(ClassCreate(name="Hope Class"), self.db, self.admin)
        create_enrollment(EnrollmentCreate(student_id=self.student.id, class_id=class_.id), self.db, self.admin)
        session = create_session(
            AttendanceSessionCreate(
                name="Morning gathering",
                session_type="CLASS",
                session_date=date.today(),
                start_time=time(8, 0),
                end_time=time(9, 0),
                class_id=class_.id,
            ),
            self.db,
            self.admin,
        )
        open_session(session.id, self.db, self.admin)
        duplicate = AttendanceEntry(student_id=self.student.id, status=AttendanceStatus.PRESENT)
        with self.assertRaises(HTTPException) as context:
            mark_roster(
                session.id,
                AttendanceBulkMark(records=[duplicate, duplicate]),
                self.db,
                self.admin,
            )
        self.assertEqual(context.exception.status_code, 422)

    def test_general_session_roster_includes_active_unenrolled_students(self) -> None:
        unenrolled_student = create_user(
            UserCreate(
                first_name="Jo",
                last_name="Community",
                email="jo@example.org",
                password="test-password-789",
                role=UserRole.STUDENT,
            ),
            self.db,
            self.admin,
        )
        session = create_session(
            AttendanceSessionCreate(
                name="Community gathering",
                session_type="GENERAL",
                session_date=date.today(),
                start_time=time(10, 0),
                end_time=time(11, 0),
            ),
            self.db,
            self.admin,
        )
        roster = get_roster(session.id, self.db, self.admin)
        self.assertIn(unenrolled_student.id, {item["student_id"] for item in roster})

    def test_student_can_register_a_new_account(self) -> None:
        token = register(
            RegisterRequest(
                first_name="Nia",
                last_name="Student",
                student_id="eh-000123",
                email="nia@example.org",
                class_name="IT class",
                password="student8",
            ),
            self.db,
        )

        self.assertTrue(token.access_token)
        user = self.db.scalar(select(User).where(User.email == "nia@example.org"))
        self.assertIsNotNone(user)
        self.assertEqual(user.role, UserRole.STUDENT)
        self.assertEqual(user.student_id, "EH-000123")
        enrollment = self.db.scalar(select(Enrollment).where(Enrollment.student_id == user.id))
        self.assertEqual(self.db.get(Class, enrollment.class_id).name, "IT class")
        self.assertTrue(verify_password("student8", user.password_hash))
        self.assertTrue(login(LoginRequest(identifier="eh-000123", password="student8"), self.db).access_token)
        self.assertTrue(login(LoginRequest(identifier="ada@example.org", password="test-password-123"), self.db).access_token)

    def test_oauth_signup_handoff_creates_student_and_class_enrollment(self) -> None:
        handoff_token = create_signup_handoff_token(
            "google",
            "google-subject-123",
            "google.student@example.org",
            "Nia",
            "Student",
        )
        token = register_with_oauth(
            OAuthRegisterRequest(
                first_name="Nia",
                last_name="Student",
                student_id="eh-google-123",
                class_name="Catering",
                oauth_token=handoff_token,
                password="social8!",
            ),
            self.db,
        )

        user = self.db.scalar(select(User).where(User.email == "google.student@example.org"))
        enrollment = self.db.scalar(select(Enrollment).where(Enrollment.student_id == user.id))
        self.assertTrue(token.access_token)
        self.assertEqual(user.student_id, "EH-GOOGLE-123")
        self.assertEqual(user.google_subject, "google-subject-123")
        self.assertEqual(self.db.get(Class, enrollment.class_id).name, "Catering")
        self.assertTrue(verify_password("social8!", user.password_hash))
        with self.assertRaises(HTTPException):
            register_with_oauth(
                OAuthRegisterRequest(
                    first_name="Nia",
                    last_name="Student",
                    student_id="EH-GOOGLE-456",
                    class_name="IT class",
                    oauth_token=handoff_token,
                    password="another-password-123",
                ),
                self.db,
            )

    def test_oauth_callback_rejects_unverified_email(self) -> None:
        class OAuthClientStub:
            async def authorize_access_token(self, _request):
                return {"userinfo": {"sub": "google-subject", "email": "unverified@example.org", "email_verified": False}}

        request = Request({"type": "http", "headers": [], "method": "GET", "scheme": "http", "path": "/callback", "query_string": b""})
        with patch("app.api.v1.auth.oauth.create_client", return_value=OAuthClientStub()):
            response = asyncio.run(oauth_callback("google", request, self.db))

        fragment = parse_qs(urlparse(response.headers["location"]).fragment)
        self.assertEqual(fragment["oauth_error"], ["verified_email_required"])

    def test_student_can_access_only_their_enrolled_classes_and_sessions(self) -> None:
        enrolled_class = create_class(ClassCreate(name="Hope Class"), self.db, self.admin)
        other_class = create_class(ClassCreate(name="Other Class"), self.db, self.admin)
        create_enrollment(EnrollmentCreate(student_id=self.student.id, class_id=enrolled_class.id), self.db, self.admin)

        general_session = create_session(
            AttendanceSessionCreate(
                name="Community gathering",
                session_type="GENERAL",
                session_date=date.today(),
                start_time=time(10, 0),
                end_time=time(11, 0),
            ),
            self.db,
            self.admin,
        )
        enrolled_class_session = create_session(
            AttendanceSessionCreate(
                name="Hope session",
                session_type="CLASS",
                session_date=date.today(),
                start_time=time(12, 0),
                end_time=time(13, 0),
                class_id=enrolled_class.id,
            ),
            self.db,
            self.admin,
        )
        create_session(
            AttendanceSessionCreate(
                name="Closed session",
                session_type="CLASS",
                session_date=date.today(),
                start_time=time(9, 0),
                end_time=time(10, 0),
                class_id=other_class.id,
            ),
            self.db,
            self.admin,
        )

        self.assertEqual([class_.id for class_ in list_accessible_classes(self.db, self.student)], [enrolled_class.id])
        student_sessions = list_accessible_sessions(self.db, self.student, date.today())
        self.assertEqual({session.id for session in student_sessions}, {general_session.id, enrolled_class_session.id})

    def test_password_change_requires_current_password_and_updates_hash(self) -> None:
        with self.assertRaises(HTTPException) as context:
            change_password(
                PasswordChangeRequest(current_password="incorrect-password", new_password="another-password-123"),
                self.student,
                self.db,
            )
        self.assertEqual(context.exception.status_code, 400)

        change_password(
                PasswordChangeRequest(current_password="student8", new_password="changed8!"),
            self.student,
            self.db,
        )
        self.db.refresh(self.student)
        self.assertTrue(verify_password("changed8!", self.student.password_hash))


if __name__ == "__main__":
    unittest.main()