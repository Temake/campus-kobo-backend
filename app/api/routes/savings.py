from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.savings import (
    SavingsContributionRequest,
    SavingsGoalCreateRequest,
    SavingsGoalResponse,
    SavingsGoalUpdateRequest,
)
from app.services.savings import SavingsService

router = APIRouter()


@router.get("", response_model=list[SavingsGoalResponse])
async def list_savings(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> list[SavingsGoalResponse]:
    return await SavingsService(db).list_goals(current_user_id)


@router.post("", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_savings(
    payload: SavingsGoalCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> SavingsGoalResponse:
    return await SavingsService(db).create_goal(current_user_id, payload)


@router.get("/goals", response_model=list[SavingsGoalResponse])
async def list_savings_goals(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> list[SavingsGoalResponse]:
    return await SavingsService(db).list_goals(current_user_id)


@router.post("/goals", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_savings_goal(
    payload: SavingsGoalCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> SavingsGoalResponse:
    return await SavingsService(db).create_goal(current_user_id, payload)


@router.post("/goals/{goal_id}/contributions", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
async def add_contribution(
    goal_id: str,
    payload: SavingsContributionRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> SavingsGoalResponse:
    return await SavingsService(db).add_contribution(current_user_id, goal_id, payload)


@router.get("/{goal_id}", response_model=SavingsGoalResponse)
async def get_savings(
    goal_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> SavingsGoalResponse:
    return await SavingsService(db).get_goal(current_user_id, goal_id)


@router.put("/{goal_id}", response_model=SavingsGoalResponse)
async def update_savings(
    goal_id: str,
    payload: SavingsGoalUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> SavingsGoalResponse:
    return await SavingsService(db).update_goal(current_user_id, goal_id, payload)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_savings(
    goal_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await SavingsService(db).delete_goal(current_user_id, goal_id)
