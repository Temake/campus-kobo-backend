import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.savings import SavingsContributionRequest, SavingsGoalCreateRequest


class SavingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_goals(self, user_id: str) -> list[dict]:
        return []

    async def create_goal(self, user_id: str, payload: SavingsGoalCreateRequest) -> dict:
        return {"id": str(uuid.uuid4()), **payload.model_dump()}

    async def add_contribution(self, user_id: str, goal_id: str, payload: SavingsContributionRequest) -> dict:
        return {"goal_id": goal_id, **payload.model_dump()}
