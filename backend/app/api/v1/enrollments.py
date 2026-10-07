from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.class_model import Class
from app.models.class_staff import ClassStaff
from app.models.enums import AssignmentStatus, EnrollmentStatus, UserRole
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.enrollment import EnrollmentCreate, EnrollmentResponse, EnrollmentUpdate
from app.security.dependencies import get_current_user, require_roles
from app.services.audit_service import record_audit


router = APIRouter(prefix="/enrollments", tags=["Enrollments"])
admin_user = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
staff_user = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF)


@router.get("", response_model=list[EnrollmentResponse])
def list_enrollments(
	class_id: int | None = None,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> list[Enrollment]:
	statement = select(Enrollment).where(Enrollment.status == EnrollmentStatus.ACTIVE)
	if class_id is not None:
		statement = statement.where(Enrollment.class_id == class_id)
	if current_user.role == UserRole.STUDENT:
		statement = statement.where(Enrollment.student_id == current_user.id)
	elif current_user.role == UserRole.STAFF:
		statement = statement.join(ClassStaff).where(
			ClassStaff.staff_id == current_user.id,
			ClassStaff.status == AssignmentStatus.ACTIVE,
			Enrollment.class_id == ClassStaff.class_id,
		)
	return list(db.scalars(statement.order_by(Enrollment.enrolled_at.desc())).unique().all())


@router.post("", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def create_enrollment(
	enrollment_data: EnrollmentCreate,
	db: Session = Depends(get_db),
	current_user: User = Depends(admin_user),
) -> Enrollment:
	student = db.get(User, enrollment_data.student_id)
	class_ = db.get(Class, enrollment_data.class_id)
	if student is None or student.role != UserRole.STUDENT or not student.is_active:
		raise HTTPException(status_code=400, detail="An active student account is required")
	if class_ is None:
		raise HTTPException(status_code=404, detail="Class not found")
	enrollment = Enrollment(student_id=student.id, class_id=class_.id)
	db.add(enrollment)
	try:
		db.flush()
		record_audit(db, current_user, "ENROLL", "enrollment", enrollment.id, f"Enrolled {student.email} in {class_.name}")
		db.commit()
	except IntegrityError as error:
		db.rollback()
		existing = db.scalar(
			select(Enrollment.id).where(
				Enrollment.student_id == student.id,
				Enrollment.class_id == class_.id,
			)
		)
		if existing is not None:
			raise HTTPException(status_code=409, detail="Student is already enrolled in this class") from error
		raise
	db.refresh(enrollment)
	return enrollment


@router.patch("/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment(
	enrollment_id: int,
	enrollment_data: EnrollmentUpdate,
	db: Session = Depends(get_db),
	current_user: User = Depends(admin_user),
) -> Enrollment:
	enrollment = db.get(Enrollment, enrollment_id)
	if enrollment is None:
		raise HTTPException(status_code=404, detail="Enrollment not found")
	changes = enrollment_data.model_dump(exclude_unset=True)
	previous = enrollment.status.value
	for key, value in changes.items():
		setattr(enrollment, key, value)
	record_audit(
		db,
		current_user,
		"UPDATE",
		"enrollment",
		enrollment.id,
		"Updated student enrollment",
		old_values={"status": previous},
		new_values={"status": enrollment.status.value},
	)
	db.commit()
	db.refresh(enrollment)
	return enrollment
