from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.notification import NotificationPreferenceUpdateRequest
from app.services.notifications import NotificationService

router = APIRouter()


@router.get("/preferences")
def list_preferences(current_user_id: Annotated[str, Depends(get_current_user_id)], db: DBSession) -> list[dict]:
    return NotificationService(db).list_preferences(current_user_id)


@router.put("/preferences", status_code=status.HTTP_204_NO_CONTENT)
def update_preference(
    payload: NotificationPreferenceUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    NotificationService(db).upsert_preference(current_user_id, payload)
