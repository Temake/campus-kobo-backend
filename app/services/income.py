from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income import Income
from app.schemas.income import IncomeCreateRequest, IncomeResponse, IncomeUpdateRequest


class IncomeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_income(self, user_id: str) -> list[IncomeResponse]:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        rows = (
            await self.db.scalars(
                select(Income)
                .where(Income.user_id == parsed_user_id)
                .order_by(Income.received_on.desc(), Income.created_at.desc())
            )
        ).all()
        return [self._serialize(row) for row in rows]

    async def create_income(self, user_id: str, payload: IncomeCreateRequest) -> IncomeResponse:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        income = Income(
            user_id=parsed_user_id,
            amount=Decimal(payload.amount),
            category=payload.category,
            received_on=payload.date,
            note=payload.note,
        )
        self.db.add(income)
        await self.db.commit()
        await self.db.refresh(income)
        return self._serialize(income)

    async def get_income(self, user_id: str, income_id: str) -> IncomeResponse:
        income = await self._get_owned_income(user_id, income_id)
        return self._serialize(income)

    async def update_income(self, user_id: str, income_id: str, payload: IncomeUpdateRequest) -> IncomeResponse:
        income = await self._get_owned_income(user_id, income_id)
        income.amount = Decimal(payload.amount)
        income.category = payload.category
        income.received_on = payload.date
        income.note = payload.note
        await self.db.commit()
        await self.db.refresh(income)
        return self._serialize(income)

    async def delete_income(self, user_id: str, income_id: str) -> None:
        income = await self._get_owned_income(user_id, income_id)
        await self.db.delete(income)
        await self.db.commit()

    async def _get_owned_income(self, user_id: str, income_id: str) -> Income:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        parsed_income_id = self._parse_uuid(income_id, "Invalid income identifier")
        income = await self.db.scalar(
            select(Income).where(Income.id == parsed_income_id, Income.user_id == parsed_user_id)
        )
        if income is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income not found")
        return income

    @staticmethod
    def _serialize(income: Income) -> IncomeResponse:
        return IncomeResponse(
            id=str(income.id),
            title=income.category,
            amount=income.amount,
            category=income.category,
            date=income.received_on,
            note=income.note,
            created_at=income.created_at,
            updated_at=income.updated_at,
        )

    @staticmethod
    def _parse_uuid(value: str, detail: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
