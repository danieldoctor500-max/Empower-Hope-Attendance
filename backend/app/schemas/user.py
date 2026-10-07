from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole, UserStatus


class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    student_id: str | None = Field(default=None, min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.STUDENT


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    id: int
    role: UserRole
    status: UserStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)