import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.expense import ExpenseCreateRequest, ExpenseResponse


class ExpenseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_expenses(self, user_id: str) -> list[ExpenseResponse]:
        return []

    async def create_expense(self, user_id: str, payload: ExpenseCreateRequest) -> ExpenseResponse:
        return ExpenseResponse(id=str(uuid.uuid4()), status="logged", **payload.model_dump())
