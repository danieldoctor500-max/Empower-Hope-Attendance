from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import AttendanceStatus


class DashboardSummary(BaseModel):
	today_sessions: int
	open_sessions: int
	present: int
	absent: int
	late: int
	excused: int
	recorded: int
	attendance_rate: float


class AttendanceReportRow(BaseModel):
	session_id: int
	session_name: str
	session_date: date
	class_name: str | None
	student_id: int
	student_name: str
	email: str
	status: AttendanceStatus
	marked_by: str | None
	updated_at: datetime


class AuditLogItem(BaseModel):
	id: int
	actor: str | None
	action: str
	entity_type: str
	entity_id: int | None
	description: str | None
	created_at: datetime
