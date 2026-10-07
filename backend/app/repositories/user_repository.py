from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
	return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
	return db.scalar(select(User).where(User.email == email.lower()))


def get_by_student_id(db: Session, student_id: str) -> User | None:
	return db.scalar(select(User).where(User.student_id == student_id.upper()))


def list_users(
	db: Session,
	role: UserRole | None = None,
	active: bool | None = None,
) -> list[User]:
	statement = select(User).order_by(User.last_name, User.first_name)
	if role is not None:
		statement = statement.where(User.role == role)
	if active is not None:
		statement = statement.where(User.is_active == active)
	return list(db.scalars(statement).all())
