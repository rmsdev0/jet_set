from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserRead


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _normalize_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Name is required.")
    return normalized


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    name: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return _normalize_email(str(value))

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_name(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return _normalize_email(str(value))


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return _normalize_email(str(value))


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    password: str = Field(min_length=10, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)


class ResendVerificationRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return _normalize_email(str(value))


class AuthFlowResponse(BaseModel):
    message: str
    user: Optional[UserRead] = None
    auth_method: Optional[Literal["session", "bearer", "debug"]] = None
    requires_email_verification: bool = False
    dev_token: Optional[str] = None


class AuthSessionRead(BaseModel):
    user: UserRead
    auth_method: Literal["session", "bearer", "debug"]
