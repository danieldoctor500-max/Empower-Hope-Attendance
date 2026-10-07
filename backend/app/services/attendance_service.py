from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EnrollmentStatus, UserRole
from app.models.enrollment import Enrollment
from app.models.session import AttendanceSession
from app.models.user import User


def eligible_students(db: Session, session: AttendanceSession) -> list[User]:
	statement = select(User).where(User.role == UserRole.STUDENT, User.is_active.is_(True))
	if session.class_id is not None:
		statement = statement.join(Enrollment).where(
			Enrollment.class_id == session.class_id,
			Enrollment.status == EnrollmentStatus.ACTIVE,
		)
	return list(db.scalars(statement.order_by(User.last_name, User.first_name)).unique().all())
