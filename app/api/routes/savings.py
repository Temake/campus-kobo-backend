from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.savings import SavingsContributionRequest, SavingsGoalCreateRequest
from app.services.savings import SavingsService

router = APIRouter()


@router.get("/goals")
def list_savings_goals(current_user_id: Annotated[str, Depends(get_current_user_id)], db: DBSession) -> list[dict]:
    return SavingsService(db).list_goals(current_user_id)


@router.post("/goals", status_code=status.HTTP_201_CREATED)
def create_savings_goal(
    payload: SavingsGoalCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> dict:
    return SavingsService(db).create_goal(current_user_id, payload)


@router.post("/goals/{goal_id}/contributions", status_code=status.HTTP_201_CREATED)
def add_contribution(
    goal_id: str,
    payload: SavingsContributionRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> dict:
    return SavingsService(db).add_contribution(current_user_id, goal_id, payload)
