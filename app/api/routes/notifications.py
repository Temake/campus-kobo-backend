from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.notification import NotificationPreferenceUpdateRequest
from app.services.notifications import NotificationService

router = APIRouter()


@router.get("/preferences")
async def list_preferences(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> list[dict]:
    return await NotificationService(db).list_preferences(current_user_id)


@router.put("/preferences", status_code=status.HTTP_204_NO_CONTENT)
async def update_preference(
    payload: NotificationPreferenceUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await NotificationService(db).upsert_preference(current_user_id, payload)
