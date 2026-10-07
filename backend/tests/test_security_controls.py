import os
import unittest
import asyncio
from datetime import date, time

os.environ.setdefault("DATABASE_URL", "sqlite:///./test-config.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")

import httpx
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.reports import _safe_csv_value
from app.core.rate_limit import LoginRateLimiter
from app.database.base import Base
from app.database.session import get_db
from app.models.enums import SessionType, UserRole
from app.models.session import AttendanceSession
from app.models.user import User
from app.api.v1.sessions import check_session_access, create_session
from app.schemas.session import AttendanceSessionCreate
from app.main import app


class SecurityControlTests(unittest.TestCase):
    def test_login_rate_limiter_caps_identity_attempts_across_sources(self) -> None:
        limiter = LoginRateLimiter(per_identifier_limit=2, per_ip_limit=10)
        limiter.check_and_consume("192.0.2.1", "STUDENT-1")
        limiter.check_and_consume("192.0.2.2", "student-1")

        with self.assertRaises(HTTPException) as context:
            limiter.check_and_consume("192.0.2.3", "STUDENT-1")

        self.assertEqual(context.exception.status_code, 429)
        self.assertIn("Retry-After", context.exception.headers)

    def test_login_route_enforces_rate_limit(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)

        def override_get_db():
            with Session(engine) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            async def send_requests() -> None:
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://testserver",
                ) as client:
                    ui_response = await client.get("/")
                    self.assertEqual(ui_response.status_code, 200)
                    self.assertIn("Content-Security-Policy", ui_response.headers)
                    self.assertEqual(ui_response.headers["X-Content-Type-Options"], "nosniff")

                    for _ in range(10):
                        response = await client.post(
                            "/api/v1/auth/login",
                            json={"identifier": "test-rate-limit-unique", "password": "bad-password"},
                        )
                        self.assertEqual(response.status_code, 401)

                    response = await client.post(
                        "/api/v1/auth/login",
                        json={"identifier": "test-rate-limit-unique", "password": "bad-password"},
                    )
                    self.assertEqual(response.status_code, 429)
                    self.assertIn("Retry-After", response.headers)

            asyncio.run(send_requests())
        finally:
            app.dependency_overrides.pop(get_db, None)
            Base.metadata.drop_all(engine)
            engine.dispose()

    def test_csv_formula_prefix_is_neutralized_after_whitespace(self) -> None:
        self.assertEqual(_safe_csv_value(" =1+1"), "' =1+1")
        self.assertEqual(_safe_csv_value("\t@SUM(A1:A2)"), "'\t@SUM(A1:A2)")
        self.assertEqual(_safe_csv_value("Sam Student"), "Sam Student")

    def test_staff_cannot_access_classless_general_sessions(self) -> None:
        staff = User(id=7, role=UserRole.STAFF)
        session = AttendanceSession(id=12, session_type=SessionType.GENERAL, class_id=None)

        with self.assertRaises(HTTPException) as context:
            check_session_access(None, staff, session)

        self.assertEqual(context.exception.status_code, 403)

    def test_staff_cannot_create_general_sessions(self) -> None:
        staff = User(id=7, role=UserRole.STAFF)
        data = AttendanceSessionCreate(
            name="All-community session",
            session_type=SessionType.GENERAL,
            session_date=date.today(),
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

        with self.assertRaises(HTTPException) as context:
            create_session(data, None, staff)

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
