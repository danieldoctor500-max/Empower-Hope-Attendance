from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_staff import ClassStaff
from app.models.enrollment import Enrollment
from app.models.enums import AssignmentStatus, EnrollmentStatus, UserRole
from app.models.session import AttendanceSession
from app.models.user import User
from app.core.exceptions import not_found
from app.repositories.session_repository import get_by_id, list_sessions


def get_session(db: Session, session_id: int) -> AttendanceSession:
	session = get_by_id(db, session_id)
	if session is None:
		raise not_found("Attendance session")
	return session


def list_accessible_sessions(
	db: Session,
	user: User,
	session_date: date | None = None,
) -> list[AttendanceSession]:
	sessions = list_sessions(db, session_date)
	if user.role == UserRole.STAFF:
		class_ids = set(db.scalars(select(ClassStaff.class_id).where(
			ClassStaff.staff_id == user.id,
			ClassStaff.status == AssignmentStatus.ACTIVE,
		)).all())
		return [session for session in sessions if session.class_id is not None and session.class_id in class_ids]
	if user.role == UserRole.STUDENT:
		class_ids = set(db.scalars(select(Enrollment.class_id).where(
			Enrollment.student_id == user.id,
			Enrollment.status == EnrollmentStatus.ACTIVE,
		)).all())
		return [session for session in sessions if session.class_id is None or session.class_id in class_ids]
	return sessions
