import uuid

from sqlalchemy.orm import Session

from app.schemas.expense import ExpenseCreateRequest, ExpenseResponse


class ExpenseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_expenses(self, user_id: str) -> list[ExpenseResponse]:
        # Replace with paginated DB query.
        return []

    def create_expense(self, user_id: str, payload: ExpenseCreateRequest) -> ExpenseResponse:
        # Business rules:
        # - validate category ownership
        # - persist expense
        # - trigger budget recalculation
        # - emit notification if user exceeds threshold
        return ExpenseResponse(id=str(uuid.uuid4()), status="logged", **payload.model_dump())
