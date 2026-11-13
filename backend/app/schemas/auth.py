"""
auth.py

Request and response shapes for registration and login.

Responses are explicit: `UserOut` lists exactly which fields leave the
server, so the password hash can't leak by accident if the model grows.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, field_validator

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128  # argon2 is deliberately slow; don't let huge inputs be used to burn CPU


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    # The person must explicitly accept, and say which version of the privacy
    # text they saw, so what we record is what they actually agreed to.
    consent_accepted: StrictBool
    consent_version: str = Field(min_length=1, max_length=32)

    @field_validator("consent_accepted")
    @classmethod
    def _consent_must_be_true(cls, value: bool) -> bool:
        if not value:
            raise ValueError("You must accept the privacy notice to create an account.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    # No minimum here: login must never reveal the password rules, and must
    # keep working if those rules are tightened later.
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    consent_version: str
    consented_at: datetime
    created_at: datetime
