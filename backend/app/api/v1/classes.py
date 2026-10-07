from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.class_model import Class
from app.models.class_staff import ClassStaff
from app.models.enums import AssignmentStatus, UserRole
from app.models.user import User
from app.permissions.access_control import require_class_access
from app.schemas.class_schema import ClassCreate, ClassResponse, ClassUpdate
from app.schemas.class_staff import ClassStaffResponse
from app.core.dependencies import get_current_user
from app.security.dependencies import require_roles
from app.services.audit_service import record_audit
from app.services.class_service import list_accessible_classes


router = APIRouter(prefix="/classes", tags=["Classes"])
admin_user = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
staff_user = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF)


@router.get("", response_model=list[ClassResponse])
def list_classes(
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> list[Class]:
	return list_accessible_classes(db, current_user)


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
	class_data: ClassCreate,
	db: Session = Depends(get_db),
	current_user: User = Depends(admin_user),
) -> Class:
	class_ = Class(name=class_data.name.strip(), description=class_data.description)
	db.add(class_)
	try:
		db.flush()
		record_audit(db, current_user, "CREATE", "class", class_.id, f"Created class {class_.name}")
		db.commit()
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(status_code=409, detail="A class with that name already exists") from error
	db.refresh(class_)
	return class_


@router.get("/{class_id}", response_model=ClassResponse)
def read_class(
	class_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Class:
	class_ = db.get(Class, class_id)
	if class_ is None:
		raise HTTPException(status_code=404, detail="Class not found")
	require_class_access(db, current_user, class_id)
	return class_


@router.patch("/{class_id}", response_model=ClassResponse)
def update_class(
	class_id: int,
	class_data: ClassUpdate,
	db: Session = Depends(get_db),
	current_user: User = Depends(admin_user),
) -> Class:
	class_ = db.get(Class, class_id)
	if class_ is None:
		raise HTTPException(status_code=404, detail="Class not found")
	changes = class_data.model_dump(exclude_unset=True)
	if "name" in changes:
		changes["name"] = changes["name"].strip()
	old_values = {key: getattr(class_, key).value if hasattr(getattr(class_, key), "value") else getattr(class_, key) for key in changes}
	for key, value in changes.items():
		setattr(class_, key, value)
	try:
		record_audit(db, current_user, "UPDATE", "class", class_id, f"Updated class {class_.name}", old_values=old_values, new_values={key: value.value if hasattr(value, "value") else value for key, value in changes.items()})
		db.commit()
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(status_code=409, detail="A class with that name already exists") from error
	db.refresh(class_)
	return class_


@router.put("/{class_id}/staff/{staff_id}", response_model=ClassStaffResponse)
def assign_staff(
	class_id: int,
	staff_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(admin_user),
) -> ClassStaff:
	class_ = db.get(Class, class_id)
	staff = db.get(User, staff_id)
	if class_ is None:
		raise HTTPException(status_code=404, detail="Class not found")
	if staff is None or staff.role != UserRole.STAFF or not staff.is_active:
		raise HTTPException(status_code=400, detail="An active staff user is required")
	assignment = db.scalar(
		select(ClassStaff).where(ClassStaff.class_id == class_id, ClassStaff.staff_id == staff_id)
	)
	if assignment is None:
		assignment = ClassStaff(class_id=class_id, staff_id=staff_id)
		db.add(assignment)
	else:
		assignment.status = AssignmentStatus.ACTIVE
	record_audit(db, current_user, "ASSIGN", "class_staff", assignment.id, f"Assigned {staff.email} to {class_.name}")
	db.commit()
	db.refresh(assignment)
	return assignment


@router.delete("/{class_id}/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_staff(
	class_id: int,
	staff_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(admin_user),
) -> None:
	assignment = db.scalar(
		select(ClassStaff).where(ClassStaff.class_id == class_id, ClassStaff.staff_id == staff_id)
	)
	if assignment is None:
		raise HTTPException(status_code=404, detail="Class staff assignment not found")
	assignment.status = AssignmentStatus.INACTIVE
	record_audit(db, current_user, "UNASSIGN", "class_staff", assignment.id, "Removed staff assignment")
	db.commit()
