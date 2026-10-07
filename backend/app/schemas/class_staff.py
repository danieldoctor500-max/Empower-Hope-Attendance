from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AssignmentStatus


class ClassStaffCreate(BaseModel):
    staff_id: int


class ClassStaffResponse(BaseModel):
    id: int
    class_id: int
    staff_id: int
    status: AssignmentStatus
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AssignmentStatus


class ClassStaffCreate(BaseModel):
    class_id: int
    staff_id: int


class ClassStaffUpdate(BaseModel):
    status: AssignmentStatus | None = None


class ClassStaffResponse(BaseModel):
    id: int
    class_id: int
    staff_id: int
    status: AssignmentStatus
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)