"""
account.py (routes)

  GET    /account/export   download everything stored about you, as JSON
  DELETE /account          permanently erase your account and all your screenings

Both are for the signed-in user's own data only. The export never includes
the password hash (the repository builds it from an explicit field list).
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.security import verify_password
from app.db.session import get_db
from app.repositories import users as user_repo
from app.schemas.account import DeleteAccountRequest

router = APIRouter(prefix="/account", tags=["account"])

DbSession = Annotated[Session, Depends(get_db)]

EXPORT_FORMAT_VERSION = 1


@router.get("/export")
def export_my_data(user: CurrentUser, db: DbSession) -> JSONResponse:
    data = user_repo.export_user_data(db, user)
    payload = {
        "format_version": EXPORT_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": 'attachment; filename="my-screening-data.json"'},
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(body: DeleteAccountRequest, user: CurrentUser, db: DbSession) -> Response:
    if not verify_password(body.password, user.password_hash):
        # 403, not 401: the token is fine, and a 401 would make a frontend
        # treat the session as expired and sign the person out.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect password.")
    user_repo.delete_user_and_data(db, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
