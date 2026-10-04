"""Authentication schemas."""

import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator, model_validator


class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = False
    otp_code: Optional[str] = Field(None, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_uri: str


class TwoFactorVerifyRequest(BaseModel):
    otp_code: str = Field(..., min_length=6, max_length=6)


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: Optional[str]
    role: str
    is_verified: bool
    two_factor_enabled: bool
    avatar_url: Optional[str]

    model_config = {"from_attributes": True}

    @field_serializer("role")
    def serialize_role(self, value):
        return value.value if hasattr(value, "value") else value


class SessionResponse(BaseModel):
    id: UUID
    device_name: Optional[str]
    device_type: Optional[str]
    ip_address: Optional[str]
    last_used_at: str
    is_active: bool

    model_config = {"from_attributes": True}
