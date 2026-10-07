from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AttendanceStatus


class AttendanceCreate(BaseModel):
    session_id: int
    student_id: int


class AttendanceMark(BaseModel):
    status: AttendanceStatus
    notes: str | None = None


class AttendanceEntry(BaseModel):
    student_id: int
    status: AttendanceStatus
    notes: str | None = Field(default=None, max_length=1000)


class AttendanceBulkMark(BaseModel):
    records: list[AttendanceEntry] = Field(min_length=1, max_length=500)


class RosterEntry(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    email: str
    attendance_id: int | None = None
    status: AttendanceStatus | None = None
    notes: str | None = None


class AttendanceResponse(BaseModel):
    id: int
    session_id: int
    student_id: int
    status: AttendanceStatus
    sign_in_at: datetime | None
    sign_out_at: datetime | None
    marked_by: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)