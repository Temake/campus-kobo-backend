from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class SavingsGoalCreateRequest(BaseModel):
    goal_name: str = Field(min_length=1, max_length=255)
    target_amount: Decimal = Field(gt=0)
    target_date: date | None = None
    initial_deposit: Decimal = Field(ge=0)
    note: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_initial_deposit(self) -> "SavingsGoalCreateRequest":
        if self.initial_deposit > self.target_amount:
            raise ValueError("initial_deposit cannot exceed target_amount")
        return self


class SavingsGoalUpdateRequest(SavingsGoalCreateRequest):
    pass


class SavingsGoalResponse(BaseModel):
    id: str
    goal_name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date | None = None
    note: str | None = None
    percentage_progress: float
    status: str
    created_at: datetime
    updated_at: datetime


class SavingsContributionRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    note: str | None = None
