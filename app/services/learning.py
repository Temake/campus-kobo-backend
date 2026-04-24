from sqlalchemy.ext.asyncio import AsyncSession


class LearningService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_content(self) -> list[dict]:
        return []

    async def bookmark_content(self, user_id: str, content_id: str) -> None:
        return None
