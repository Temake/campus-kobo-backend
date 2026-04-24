from sqlalchemy.orm import Session


class LearningService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_content(self) -> list[dict]:
        return []

    def bookmark_content(self, user_id: str, content_id: str) -> None:
        # Create or toggle bookmark mapping for user and content.
        return None
