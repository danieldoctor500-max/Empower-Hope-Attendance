from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import AttendanceSession


def get_by_id(db: Session, session_id: int) -> AttendanceSession | None:
	return db.get(AttendanceSession, session_id)


def list_sessions(db: Session, session_date: date | None = None) -> list[AttendanceSession]:
	statement = select(AttendanceSession)
	if session_date is not None:
		statement = statement.where(AttendanceSession.session_date == session_date)
	statement = statement.order_by(AttendanceSession.session_date.desc(), AttendanceSession.start_time)
	return list(db.scalars(statement).all())
