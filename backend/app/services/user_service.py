from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import get_by_id, list_users as repository_list_users


def get_user(db: Session, user_id: int) -> User | None:
	return get_by_id(db, user_id)


def list_users(
	db: Session,
	role: UserRole | None = None,
	active: bool | None = None,
) -> list[User]:
	return repository_list_users(db, role=role, active=active)
