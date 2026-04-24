from fastapi import APIRouter, status

from app.api.deps import DBSession
from app.schemas.support import SupportMessageCreateRequest
from app.services.support import SupportService

router = APIRouter()


@router.get("/faqs")
async def list_faqs(db: DBSession, search: str | None = None, category: str | None = None) -> list[dict]:
    return await SupportService(db).list_faqs(search=search, category=category)


@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def create_support_message(payload: SupportMessageCreateRequest, db: DBSession) -> dict:
    return await SupportService(db).create_message(payload)
