from decimal import Decimal

from pydantic import BaseModel, Field


class GoalSelectionRequest(BaseModel):
    goal_type: str


class BudgetSetupRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = "NGN"


class CategorySetupRequest(BaseModel):
    category_ids: list[str] = Field(default_factory=list)


class OnboardingProgressResponse(BaseModel):
    current_step: str
    completed_step_count: int
    is_completed: bool
