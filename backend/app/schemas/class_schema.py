from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ClassStatus


class ClassBase(BaseModel):
    name: str
    description: str | None = None


class ClassCreate(ClassBase):
    pass


class ClassUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ClassStatus | None = None


class ClassResponse(ClassBase):
    id: int
    status: ClassStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)