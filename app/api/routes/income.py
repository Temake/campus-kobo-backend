from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.income import IncomeCreateRequest, IncomeResponse, IncomeUpdateRequest
from app.services.income import IncomeService

router = APIRouter()


@router.get("", response_model=list[IncomeResponse])
async def list_income(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> list[IncomeResponse]:
    return await IncomeService(db).list_income(current_user_id)


@router.post("", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
async def create_income(
    payload: IncomeCreateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> IncomeResponse:
    return await IncomeService(db).create_income(current_user_id, payload)


@router.get("/{income_id}", response_model=IncomeResponse)
async def get_income(
    income_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> IncomeResponse:
    return await IncomeService(db).get_income(current_user_id, income_id)


@router.put("/{income_id}", response_model=IncomeResponse)
async def update_income(
    income_id: str,
    payload: IncomeUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> IncomeResponse:
    return await IncomeService(db).update_income(current_user_id, income_id, payload)


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income(
    income_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await IncomeService(db).delete_income(current_user_id, income_id)
