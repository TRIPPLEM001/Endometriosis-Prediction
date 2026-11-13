"""
screenings.py (routes)

  POST /screenings              submit symptom answers, get a scored result
  GET  /screenings              list your screenings (newest first, paginated)
  GET  /screenings/{id}         one screening with factors and the full report
  POST /screenings/{id}/labs    add CA-125 / CRP to refine an elevated result
  DELETE /screenings/{id}       permanently delete one screening
  DELETE /screenings?confirm=true   permanently delete all your screenings (keeps the account)

Every route requires a signed-in user and only ever touches that user's own
screenings. Someone else's screening id gets the same 404 as one that
doesn't exist.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_registry
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.repositories import screenings as screening_repo
from app.schemas.account import DeletedCount
from app.schemas.screening import (
    LabResults,
    ScreeningDetail,
    ScreeningList,
    ScreeningSummary,
    SymptomAnswers,
)
from app.services import screening as screening_service
from app.services.model_registry import ModelRegistry

router = APIRouter(prefix="/screenings", tags=["screenings"])

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
Registry = Annotated[ModelRegistry, Depends(get_registry)]

def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening not found.")


@router.post("", response_model=ScreeningDetail, status_code=status.HTTP_201_CREATED)
def create_screening(
    body: SymptomAnswers,
    user: CurrentUser,
    db: DbSession,
    registry: Registry,
    settings: AppSettings,
):
    return screening_service.create_screening(
        db, user.id, body.to_model_inputs(), registry, settings
    )


@router.get("", response_model=ScreeningList)
def list_screenings(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=screening_repo.MAX_PAGE_SIZE)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = screening_repo.list_screenings(db, user.id, limit=limit, offset=offset)
    return ScreeningList(
        items=[ScreeningSummary.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{screening_id}", response_model=ScreeningDetail)
def get_screening(screening_id: uuid.UUID, user: CurrentUser, db: DbSession):
    screening = screening_repo.get_screening(db, user.id, screening_id)
    if screening is None:
        raise _not_found()
    return screening


@router.post("/{screening_id}/labs", response_model=ScreeningDetail)
def add_labs(
    screening_id: uuid.UUID,
    body: LabResults,
    user: CurrentUser,
    db: DbSession,
    registry: Registry,
    settings: AppSettings,
):
    try:
        screening = screening_service.add_labs(
            db, user.id, screening_id, body.to_model_inputs(), registry, settings
        )
    except screening_service.LabsNotAllowed as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason) from None
    if screening is None:
        raise _not_found()
    return screening


@router.delete("/{screening_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_screening(screening_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    if not screening_repo.delete_screening(db, user.id, screening_id):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", response_model=DeletedCount)
def delete_all_screenings(
    user: CurrentUser,
    db: DbSession,
    confirm: Annotated[bool, Query(description="Must be true; guards against accidental wipes")],
):
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pass confirm=true to delete all of your screenings.",
        )
    return DeletedCount(deleted=screening_repo.delete_all_for_user(db, user.id))
