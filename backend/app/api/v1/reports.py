import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.database.session import get_db
from app.models.attendance import Attendance
from app.models.class_model import Class
from app.models.class_staff import ClassStaff
from app.models.enums import AssignmentStatus, UserRole
from app.models.session import AttendanceSession
from app.models.user import User
from app.schemas.report import AttendanceReportRow
from app.security.dependencies import get_current_user
from app.services.report_service import validate_date_range


router = APIRouter(prefix="/reports", tags=["Reports"])


def report_rows(
	db: Session,
	current_user: User,
	start_date: date,
	end_date: date,
	class_id: int | None,
) -> list[dict]:
	validate_date_range(start_date, end_date)
	student_user = aliased(User)
	marker_user = aliased(User)
	statement = (
		select(Attendance, AttendanceSession, student_user, Class, marker_user)
		.join(AttendanceSession, Attendance.session_id == AttendanceSession.id)
		.join(student_user, Attendance.student_id == student_user.id)
		.outerjoin(Class, AttendanceSession.class_id == Class.id)
		.outerjoin(marker_user, Attendance.marked_by == marker_user.id)
		.where(AttendanceSession.session_date.between(start_date, end_date))
	)
	if class_id is not None:
		statement = statement.where(AttendanceSession.class_id == class_id)
	if current_user.role == UserRole.STUDENT:
		statement = statement.where(Attendance.student_id == current_user.id)
	elif current_user.role == UserRole.STAFF:
		allowed_classes = select(ClassStaff.class_id).where(
			ClassStaff.staff_id == current_user.id,
			ClassStaff.status == AssignmentStatus.ACTIVE,
		)
		statement = statement.where(
			AttendanceSession.class_id.in_(allowed_classes)
		)
	result = db.execute(statement.order_by(AttendanceSession.session_date.desc(), student_user.last_name, student_user.first_name))
	return [
		{
			"session_id": session.id,
			"session_name": session.name,
			"session_date": session.session_date,
			"class_name": class_.name if class_ else None,
			"student_id": student.id,
			"student_name": f"{student.first_name} {student.last_name}",
			"email": student.email,
			"status": attendance.status,
			"marked_by": f"{marker.first_name} {marker.last_name}" if marker else None,
			"updated_at": attendance.updated_at,
		}
		for attendance, session, student, class_, marker in result
	]


@router.get("/attendance", response_model=list[AttendanceReportRow])
def get_attendance_report(
	start_date: date = Query(default_factory=date.today),
	end_date: date = Query(default_factory=date.today),
	class_id: int | None = None,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> list[dict]:
	return report_rows(db, current_user, start_date, end_date, class_id)


@router.get("/attendance.csv")
def export_attendance_csv(
	start_date: date = Query(default_factory=date.today),
	end_date: date = Query(default_factory=date.today),
	class_id: int | None = None,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> StreamingResponse:
	rows = report_rows(db, current_user, start_date, end_date, class_id)
	output = StringIO()
	fieldnames = ["session_date", "session_name", "class_name", "student_id", "student_name", "email", "status", "marked_by", "updated_at"]
	writer = csv.DictWriter(output, fieldnames=fieldnames)
	writer.writeheader()
	writer.writerows(
		{
			key: _safe_csv_value(value.value if key == "status" else value)
			for key, value in row.items()
		}
		for row in rows
	)
	output.seek(0)
	return StreamingResponse(
		iter([output.getvalue()]),
		media_type="text/csv",
		headers={"Content-Disposition": "attachment; filename=attendance-report.csv"},
	)


def _safe_csv_value(value: object) -> object:
	if not isinstance(value, str):
		return value
	first_visible = value.lstrip()
	while first_visible and (ord(first_visible[0]) < 0x20 or first_visible[0] == "\ufeff"):
		first_visible = first_visible[1:]
	if first_visible.startswith(("=", "+", "-", "@")):
		return f"'{value}"
	return value
