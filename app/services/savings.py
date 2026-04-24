import uuid

from sqlalchemy.orm import Session

from app.schemas.savings import SavingsContributionRequest, SavingsGoalCreateRequest


class SavingsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_goals(self, user_id: str) -> list[dict]:
        return []

    def create_goal(self, user_id: str, payload: SavingsGoalCreateRequest) -> dict:
        # Persist savings goal and initialize progress tracking.
        return {"id": str(uuid.uuid4()), **payload.model_dump()}

    def add_contribution(self, user_id: str, goal_id: str, payload: SavingsContributionRequest) -> dict:
        # Validate ownership, save contribution, and update current savings balance.
        return {"goal_id": goal_id, **payload.model_dump()}
