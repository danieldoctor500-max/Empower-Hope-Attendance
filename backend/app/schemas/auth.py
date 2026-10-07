from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    identifier: str = Field(
        min_length=1,
        max_length=255,
        validation_alias=AliasChoices("identifier", "student_id", "email"),
    )
    password: str


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    student_id: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")
    email: EmailStr
    class_name: Literal["IT class", "Hair & Beauty", "Catering"]
    password: str = Field(min_length=8, max_length=128)


class OAuthRegisterRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    student_id: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")
    class_name: Literal["IT class", "Hair & Beauty", "Catering"]
    oauth_token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    student_id: str | None
    email: EmailStr
    role: str
    status: str
    is_active: bool