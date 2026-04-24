from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.onboarding import (
    BudgetSetupRequest,
    CategorySetupRequest,
    GoalSelectionRequest,
    OnboardingProgressResponse,
)


class OnboardingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_progress(self, user_id: str) -> OnboardingProgressResponse:
        # Read onboarding progress from storage.
        return OnboardingProgressResponse(current_step="goal_selection", completed_step_count=1, is_completed=False)

    def select_goal(self, user_id: str, payload: GoalSelectionRequest) -> None:
        if not payload.goal_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Goal type is required")
        # Persist selected goal and advance onboarding step.

    def setup_budget(self, user_id: str, payload: BudgetSetupRequest) -> None:
        if payload.amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Budget must be positive")
        # Create initial monthly budget during onboarding.

    def setup_categories(self, user_id: str, payload: CategorySetupRequest) -> None:
        # Persist starter categories selected by the user.
        if not payload.category_ids:
            return
