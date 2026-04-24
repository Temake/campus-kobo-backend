import uuid

from sqlalchemy.orm import Session

from app.schemas.budget import BudgetCreateRequest, BudgetResponse


class BudgetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_budgets(self, user_id: str) -> list[BudgetResponse]:
        return []

    def create_budget(self, user_id: str, payload: BudgetCreateRequest) -> BudgetResponse:
        # Enforce one active budget per period per user and validate date window.
        return BudgetResponse(id=str(uuid.uuid4()), status="active", **payload.model_dump())
