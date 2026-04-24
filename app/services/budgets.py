import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.budget import BudgetCreateRequest, BudgetResponse


class BudgetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_budgets(self, user_id: str) -> list[BudgetResponse]:
        return []

    async def create_budget(self, user_id: str, payload: BudgetCreateRequest) -> BudgetResponse:
        return BudgetResponse(id=str(uuid.uuid4()), status="active", **payload.model_dump())
