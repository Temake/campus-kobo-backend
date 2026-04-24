from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ExpenseCreateRequest(BaseModel):
    title: str
    description: str | None = None
    amount: Decimal = Field(gt=0)
    currency: str = "NGN"
    spent_on: date
    category_id: str | None = None
    merchant_name: str | None = None


class ExpenseResponse(ExpenseCreateRequest):
    id: str
    status: str
