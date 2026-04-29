from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class IncomeBase(BaseModel):
    amount: Decimal = Field(gt=0)
    category: str = Field(min_length=1, max_length=100)
    date: date
    note: str | None = Field(default=None, max_length=255)


class IncomeCreateRequest(IncomeBase):
    pass


class IncomeUpdateRequest(IncomeBase):
    pass


class IncomeResponse(IncomeBase):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
