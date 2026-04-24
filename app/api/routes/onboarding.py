from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.onboarding import (
    BudgetSetupRequest,
    CategorySetupRequest,
    GoalSelectionRequest,
    OnboardingProgressResponse,
)
from app.services.onboarding import OnboardingService

router = APIRouter()


@router.get("/progress", response_model=OnboardingProgressResponse)
async def get_progress(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> OnboardingProgressResponse:
    return await OnboardingService(db).get_progress(current_user_id)


@router.post("/goal", status_code=status.HTTP_204_NO_CONTENT)
async def select_goal(
    payload: GoalSelectionRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await OnboardingService(db).select_goal(current_user_id, payload)


@router.post("/budget", status_code=status.HTTP_204_NO_CONTENT)
async def setup_budget(
    payload: BudgetSetupRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await OnboardingService(db).setup_budget(current_user_id, payload)


@router.post("/categories", status_code=status.HTTP_204_NO_CONTENT)
async def setup_categories(
    payload: CategorySetupRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await OnboardingService(db).setup_categories(current_user_id, payload)
