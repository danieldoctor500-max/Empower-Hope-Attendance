from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from app.models.enums import SessionStatus, SessionType


class AttendanceSessionCreate(BaseModel):
    name: str
    session_type: SessionType
    session_date: date
    start_time: time
    end_time: time
    class_id: int | None = None


class AttendanceSessionUpdate(BaseModel):
    name: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: SessionStatus | None = None
    class_id: int | None = None


class AttendanceSessionResponse(BaseModel):
    id: int
    name: str
    session_type: SessionType
    session_date: date
    start_time: time
    end_time: time
    status: SessionStatus
    class_id: int | None
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)