from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_model import Class
from app.models.class_staff import ClassStaff
from app.models.enums import AssignmentStatus, ClassStatus


def get_by_id(db: Session, class_id: int) -> Class | None:
	return db.get(Class, class_id)


def list_active(db: Session, staff_id: int | None = None) -> list[Class]:
	statement = select(Class).where(Class.status == ClassStatus.ACTIVE).order_by(Class.name)
	if staff_id is not None:
		statement = statement.join(ClassStaff).where(
			ClassStaff.staff_id == staff_id,
			ClassStaff.status == AssignmentStatus.ACTIVE,
		)
	return list(db.scalars(statement).unique().all())
