from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.dashboard import RecentTransactionResponse


class BudgetBaseRequest(BaseModel):
    name: str = "Monthly Budget"
    amount: Decimal = Field(gt=0)
    currency: str = "NGN"
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def validate_period(self) -> "BudgetBaseRequest":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class BudgetCreateRequest(BudgetBaseRequest):
    pass


class BudgetUpdateRequest(BudgetBaseRequest):
    pass


class BudgetResponse(BudgetBaseRequest):
    id: str
    status: str
    total_budget: Decimal
    total_spent: Decimal
    remaining_amount: Decimal
    percentage_used: float
    days_left: int
    highest_spent: str | None = None
    recent_transactions: list[RecentTransactionResponse] = Field(default_factory=list)
