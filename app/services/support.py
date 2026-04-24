import uuid

from sqlalchemy.orm import Session

from app.schemas.support import SupportMessageCreateRequest


class SupportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_faqs(self, search: str | None = None, category: str | None = None) -> list[dict]:
        # Query published FAQ items and support search/filter.
        return []

    def create_message(self, payload: SupportMessageCreateRequest) -> dict:
        # Persist support message and enqueue ticket/email notification.
        return {"id": str(uuid.uuid4()), **payload.model_dump()}
