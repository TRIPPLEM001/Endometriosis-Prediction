"""
account.py (schemas)

Request and response shapes for the privacy endpoints (export and delete).
"""

from pydantic import BaseModel, Field

from app.schemas.auth import PASSWORD_MAX_LENGTH


class DeleteAccountRequest(BaseModel):
    # Deleting an account is irreversible, so the current password is required
    # again. A stolen or left-open session alone can't erase someone's data.
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class DeletedCount(BaseModel):
    deleted: int
