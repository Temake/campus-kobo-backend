from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.expense import ExpenseCreateRequest, ExpenseResponse
from app.services.expenses import ExpenseService

router = APIRouter()


@router.get("", response_model=list[ExpenseResponse])
def list_expenses(current_user_id: Annotated[str, Depends(get_current_user_id)], db: DBSession) -> list[ExpenseResponse]:
    return ExpenseService(db).list_expenses(current_user_id)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> ExpenseResponse:
    return ExpenseService(db).create_expense(current_user_id, payload)
