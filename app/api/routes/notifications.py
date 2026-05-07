from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.notification import NotificationPreferenceResponse, NotificationPreferenceUpdateRequest
from app.services.notifications import NotificationService

router = APIRouter()


@router.get("/preferences")
async def get_preferences(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> NotificationPreferenceResponse:
    return await NotificationService(db).get_preferences(current_user_id)


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preference(
    payload: NotificationPreferenceUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> NotificationPreferenceResponse:
    return await NotificationService(db).upsert_preference(current_user_id, payload)
