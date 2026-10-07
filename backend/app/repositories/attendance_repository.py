from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance


def get_by_id(db: Session, attendance_id: int) -> Attendance | None:
	return db.get(Attendance, attendance_id)


def list_for_session(db: Session, session_id: int) -> list[Attendance]:
	statement = select(Attendance).where(Attendance.session_id == session_id).order_by(Attendance.student_id)
	return list(db.scalars(statement).all())


def find_for_student(db: Session, session_id: int, student_id: int) -> Attendance | None:
	return db.scalar(
		select(Attendance).where(
			Attendance.session_id == session_id,
			Attendance.student_id == student_id,
		)
	)
