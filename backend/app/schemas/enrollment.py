from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EnrollmentStatus


class EnrollmentCreate(BaseModel):
    student_id: int
    class_id: int


class EnrollmentUpdate(BaseModel):
    status: EnrollmentStatus | None = None


class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    class_id: int
    status: EnrollmentStatus
    enrolled_at: datetime

    model_config = ConfigDict(from_attributes=True)