from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.budget import BudgetCreateRequest, BudgetResponse
from app.services.budgets import BudgetService

router = APIRouter()


@router.get("", response_model=list[BudgetResponse])
def list_budgets(current_user_id: Annotated[str, Depends(get_current_user_id)], db: DBSession) -> list[BudgetResponse]:
    return BudgetService(db).list_budgets(current_user_id)


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> BudgetResponse:
    return BudgetService(db).create_budget(current_user_id, payload)
