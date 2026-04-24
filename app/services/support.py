import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.support import SupportMessageCreateRequest


class SupportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_faqs(self, search: str | None = None, category: str | None = None) -> list[dict]:
        return []

    async def create_message(self, payload: SupportMessageCreateRequest) -> dict:
        return {"id": str(uuid.uuid4()), **payload.model_dump()}
