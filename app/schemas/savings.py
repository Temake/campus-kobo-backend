from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class SavingsGoalCreateRequest(BaseModel):
    title: str
    description: str | None = None
    target_amount: Decimal = Field(gt=0)
    currency: str = "NGN"
    target_date: date | None = None


class SavingsContributionRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    note: str | None = None
