from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.budget import BudgetCreateRequest, BudgetResponse, BudgetUpdateRequest
from app.services.budgets import BudgetService

router = APIRouter()


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> list[BudgetResponse]:
    return await BudgetService(db).list_budgets(current_user_id)


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> BudgetResponse:
    return await BudgetService(db).create_budget(current_user_id, payload)


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> BudgetResponse:
    return await BudgetService(db).get_budget(current_user_id, budget_id)


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    payload: BudgetUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> BudgetResponse:
    return await BudgetService(db).update_budget(current_user_id, budget_id, payload)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await BudgetService(db).delete_budget(current_user_id, budget_id)
