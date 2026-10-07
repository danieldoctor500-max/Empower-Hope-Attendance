from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import get_by_email, get_by_student_id
from app.security.password import verify_password


def authenticate_user(db: Session, identifier: str, password: str) -> User | None:
	user = get_by_student_id(db, identifier) or get_by_email(db, identifier)
	if user is None or not verify_password(password, user.password_hash):
		return None
	return user
