from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.services.learning import LearningService

router = APIRouter()


@router.get("/content")
async def list_content(db: DBSession) -> list[dict]:
    return await LearningService(db).list_content()


@router.post("/content/{content_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
async def bookmark_content(
    content_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await LearningService(db).bookmark_content(current_user_id, content_id)
