from sqlalchemy.orm import Session

from app.schemas.notification import NotificationPreferenceUpdateRequest


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_preferences(self, user_id: str) -> list[dict]:
        return []

    def upsert_preference(self, user_id: str, payload: NotificationPreferenceUpdateRequest) -> None:
        # Upsert notification preference and validate quiet hour windows.
        return None
