from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.expense import ExpenseCreateRequest, ExpenseResponse, ExpenseUpdateRequest
from app.services.expenses import ExpenseService

router = APIRouter()


@router.get("", response_model=list[ExpenseResponse])
async def list_expenses(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> list[ExpenseResponse]:
    return await ExpenseService(db).list_expenses(current_user_id)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> ExpenseResponse:
    return await ExpenseService(db).create_expense(current_user_id, payload)


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> ExpenseResponse:
    return await ExpenseService(db).get_expense(current_user_id, expense_id)


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    payload: ExpenseUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> ExpenseResponse:
    return await ExpenseService(db).update_expense(current_user_id, expense_id, payload)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await ExpenseService(db).delete_expense(current_user_id, expense_id)
