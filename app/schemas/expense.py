from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.expense import ExpenseRepeat


class ExpenseBaseRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    currency: str = "NGN"
    date: date | None = None
    spent_on: date | None = None
    note: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category_id: str | None = None
    merchant_name: str | None = Field(default=None, max_length=255)
    is_recurring: bool = False
    repeats: ExpenseRepeat | None = None
    next_due_date: date | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "ExpenseBaseRequest":
        if self.date is None and self.spent_on is None:
            raise ValueError("date is required")
        if self.is_recurring and (self.repeats is None or self.next_due_date is None):
            raise ValueError("Recurring expenses require repeats and next_due_date")
        if not self.is_recurring:
            self.repeats = None
            self.next_due_date = None
        return self


class ExpenseCreateRequest(ExpenseBaseRequest):
    pass


class ExpenseUpdateRequest(ExpenseBaseRequest):
    pass


class ExpenseResponse(BaseModel):
    id: str
    title: str
    category: str | None = None
    amount: Decimal
    currency: str = "NGN"
    date: date
    note: str | None = None
    is_recurring: bool
    repeats: ExpenseRepeat | None = None
    next_due_date: date | None = None
    percentage_of_total_expenses: float
    percentage_of_budget: float | None = None
    status: str
    created_at: datetime
    updated_at: datetime
