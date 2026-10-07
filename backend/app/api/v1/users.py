from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.core.dependencies import get_current_user, require_roles
from app.core.security import hash_password
from app.repositories.user_repository import get_by_email
from app.services.audit_service import record_audit
from app.services.user_service import get_user, list_users as get_users


router = APIRouter(prefix="/users", tags=["Users"])
admin_user = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


@router.get("", response_model=list[UserResponse])
def list_users(
	role: UserRole | None = None,
	active: bool | None = None,
	db: Session = Depends(get_db),
	_: User = Depends(admin_user),
) -> list[User]:
	return get_users(db, role=role, active=active)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
	user_data: UserCreate,
	db: Session = Depends(get_db),
	current_user: User = Depends(admin_user),
) -> User:
	email = str(user_data.email).lower()
	if get_by_email(db, email) is not None:
		raise HTTPException(status_code=409, detail="Email is already registered")

	user = User(
		first_name=user_data.first_name.strip(),
		last_name=user_data.last_name.strip(),
		email=email,
		password_hash=hash_password(user_data.password),
		role=user_data.role,
		status=UserStatus.ACTIVE,
		is_active=True,
	)
	db.add(user)
	try:
		db.flush()
		if user.role == UserRole.STUDENT and user.student_id is None:
			user.student_id = f"EH-{user.id:06d}"
		record_audit(db, current_user, "CREATE", "user", user.id, f"Created {user.role.value.lower()} account {user.email}")
		db.commit()
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(status_code=409, detail="Email is already registered") from error
	db.refresh(user)
	return user


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
	return current_user


@router.get("/{user_id}", response_model=UserResponse)
def read_user(
	user_id: int,
	db: Session = Depends(get_db),
	_: User = Depends(admin_user),
) -> User:
	user = get_user(db, user_id)
	if user is None:
		raise HTTPException(status_code=404, detail="User not found")
	return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
	user_id: int,
	user_data: UserUpdate,
	db: Session = Depends(get_db),
	current_user: User = Depends(admin_user),
) -> User:
	user = get_user(db, user_id)
	if user is None:
		raise HTTPException(status_code=404, detail="User not found")

	changes = user_data.model_dump(exclude_unset=True)
	if "email" in changes:
		changes["email"] = str(changes["email"]).lower()
		duplicate = get_by_email(db, changes["email"])
		if duplicate is not None and duplicate.id != user_id:
			raise HTTPException(status_code=409, detail="Email is already registered")

	if current_user.id == user_id and (
		changes.get("is_active") is False
		or changes.get("status") in {UserStatus.INACTIVE, UserStatus.SUSPENDED}
		or changes.get("role") not in {None, UserRole.ADMIN, UserRole.SUPER_ADMIN}
	):
		raise HTTPException(status_code=400, detail="You cannot disable or demote your own account")

	old_values = {
		field: getattr(user, field).value if hasattr(getattr(user, field), "value") else getattr(user, field)
		for field in changes
	}
	for field, value in changes.items():
		setattr(user, field, value.strip() if field in {"first_name", "last_name"} else value)
	if "status" in changes:
		user.is_active = user.status == UserStatus.ACTIVE
	elif "is_active" in changes:
		user.status = UserStatus.ACTIVE if user.is_active else UserStatus.INACTIVE

	try:
		record_audit(
			db,
			current_user,
			"UPDATE",
			"user",
			user.id,
			f"Updated account {user.email}",
			old_values=old_values,
			new_values={field: value.value if hasattr(value, "value") else value for field, value in changes.items()},
		)
		db.commit()
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(status_code=409, detail="User update conflicts with an existing record") from error
	db.refresh(user)
	return user
