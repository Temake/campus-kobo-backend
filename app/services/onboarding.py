from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.onboarding import (
    BudgetSetupRequest,
    CategorySetupRequest,
    GoalSelectionRequest,
    OnboardingProgressResponse,
)


class OnboardingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_progress(self, user_id: str) -> OnboardingProgressResponse:
        return OnboardingProgressResponse(current_step="goal_selection", completed_step_count=1, is_completed=False)

    async def select_goal(self, user_id: str, payload: GoalSelectionRequest) -> None:
        if not payload.goal_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Goal type is required")

    async def setup_budget(self, user_id: str, payload: BudgetSetupRequest) -> None:
        if payload.amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Budget must be positive")

    async def setup_categories(self, user_id: str, payload: CategorySetupRequest) -> None:
        if not payload.category_ids:
            return
