from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.attendance import Attendance
from app.models.class_staff import ClassStaff
from app.models.enums import AttendanceStatus, AssignmentStatus, SessionStatus, UserRole
from app.models.session import AttendanceSession
from app.models.user import User
from app.schemas.report import DashboardSummary
from app.security.dependencies import get_current_user


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def read_summary(
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> DashboardSummary:
	class_ids = select(ClassStaff.class_id).where(
		ClassStaff.staff_id == current_user.id,
		ClassStaff.status == AssignmentStatus.ACTIVE,
	)
	session_statement = select(AttendanceSession).where(AttendanceSession.session_date == date.today())
	attendance_statement = (
		select(Attendance.status, func.count(Attendance.id))
		.join(AttendanceSession)
		.where(AttendanceSession.session_date == date.today())
	)
	if current_user.role == UserRole.STAFF:
		session_statement = session_statement.where(
			(AttendanceSession.class_id.is_(None)) | AttendanceSession.class_id.in_(class_ids)
		)
		attendance_statement = attendance_statement.where(
			(AttendanceSession.class_id.is_(None)) | AttendanceSession.class_id.in_(class_ids)
		)
	elif current_user.role == UserRole.STUDENT:
		session_statement = session_statement.join(Attendance, Attendance.session_id == AttendanceSession.id).where(
			Attendance.student_id == current_user.id
		)
		attendance_statement = attendance_statement.where(Attendance.student_id == current_user.id)

	sessions = list(db.scalars(session_statement).unique().all())
	counts = dict(db.execute(attendance_statement.group_by(Attendance.status)).all())
	present = counts.get(AttendanceStatus.PRESENT, 0)
	late = counts.get(AttendanceStatus.LATE, 0)
	absent = counts.get(AttendanceStatus.ABSENT, 0)
	excused = counts.get(AttendanceStatus.EXCUSED, 0)
	recorded = sum(counts.values())
	return DashboardSummary(
		today_sessions=len(sessions),
		open_sessions=sum(session.status == SessionStatus.OPEN for session in sessions),
		present=present,
		absent=absent,
		late=late,
		excused=excused,
		recorded=recorded,
		attendance_rate=round((present + late) * 100 / recorded, 1) if recorded else 0.0,
	)
