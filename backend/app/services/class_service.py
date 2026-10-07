from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_model import Class
from app.models.enums import ClassStatus, EnrollmentStatus, UserRole
from app.models.enrollment import Enrollment
from app.models.user import User
from app.permissions.access_control import is_admin
from app.repositories.class_repository import list_active


def list_accessible_classes(db: Session, user: User) -> list[Class]:
	if user.role == UserRole.STUDENT:
		statement = select(Class).join(
			Enrollment,
			Enrollment.class_id == Class.id,
		).where(
			Enrollment.student_id == user.id,
			Enrollment.status == EnrollmentStatus.ACTIVE,
			Class.status == ClassStatus.ACTIVE,
		).order_by(Class.name)
		return list(db.scalars(statement).unique().all())
	return list_active(db, staff_id=None if is_admin(user) else user.id)
