from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.notification import NotificationPreferenceUpdateRequest


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_preferences(self, user_id: str) -> list[dict]:
        return []

    async def upsert_preference(self, user_id: str, payload: NotificationPreferenceUpdateRequest) -> None:
        return None
