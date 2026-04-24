from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class BudgetCreateRequest(BaseModel):
    name: str = "Monthly Budget"
    amount: Decimal = Field(gt=0)
    currency: str = "NGN"
    period_start: date
    period_end: date


class BudgetResponse(BudgetCreateRequest):
    id: str
    status: str
