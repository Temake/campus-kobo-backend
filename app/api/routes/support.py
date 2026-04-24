from fastapi import APIRouter, status

from app.api.deps import DBSession
from app.schemas.support import SupportMessageCreateRequest
from app.services.support import SupportService

router = APIRouter()


@router.get("/faqs")
def list_faqs(db: DBSession, search: str | None = None, category: str | None = None) -> list[dict]:
    return SupportService(db).list_faqs(search=search, category=category)


@router.post("/messages", status_code=status.HTTP_201_CREATED)
def create_support_message(payload: SupportMessageCreateRequest, db: DBSession) -> dict:
    return SupportService(db).create_message(payload)
