from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_staff import ClassStaff
from app.models.enrollment import Enrollment
from app.models.enums import AssignmentStatus, EnrollmentStatus, UserRole
from app.models.user import User
from app.permissions.roles import ADMIN_ROLES


def is_admin(user: User) -> bool:
	return user.role in ADMIN_ROLES


def require_class_access(db: Session, user: User, class_id: int) -> None:
	if is_admin(user):
		return
	if user.role == UserRole.STUDENT:
		enrollment_id = db.scalar(
			select(Enrollment.id).where(
				Enrollment.class_id == class_id,
				Enrollment.student_id == user.id,
				Enrollment.status == EnrollmentStatus.ACTIVE,
			)
		)
		if enrollment_id is not None:
			return
	assignment_id = db.scalar(
		select(ClassStaff.id).where(
			ClassStaff.class_id == class_id,
			ClassStaff.staff_id == user.id,
			ClassStaff.status == AssignmentStatus.ACTIVE,
		)
	)
	if assignment_id is None:
		raise HTTPException(status_code=403, detail="You are not assigned to this class")
