from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import ExpenseCategory
from app.models.expense import Expense, ExpenseStatus
from app.models.onboarding import OnboardingProgress
from app.schemas.expense import ExpenseCreateRequest, ExpenseResponse


class ExpenseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_expenses(self, user_id: str) -> list[ExpenseResponse]:
        parsed_user_id = self._parse_user_id(user_id)
        expenses = (
            await self.db.scalars(
                select(Expense)
                .where(Expense.user_id == parsed_user_id, Expense.status != ExpenseStatus.deleted)
                .order_by(Expense.spent_on.desc(), Expense.created_at.desc())
            )
        ).all()
        return [self._serialize_expense(expense) for expense in expenses]

    async def create_expense(self, user_id: str, payload: ExpenseCreateRequest) -> ExpenseResponse:
        parsed_user_id = self._parse_user_id(user_id)
        category_id = self._parse_optional_uuid(payload.category_id, "Invalid category id")

        if category_id is not None:
            category = await self.db.scalar(select(ExpenseCategory).where(ExpenseCategory.id == category_id))
            if category is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
            if category.user_id not in {None, parsed_user_id}:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Category does not belong to the current user")
            if category.user_id is None and not category.is_default:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is not available")

        expense = Expense(
            user_id=parsed_user_id,
            category_id=category_id,
            title=payload.title,
            description=payload.description,
            amount=payload.amount,
            currency=payload.currency,
            spent_on=payload.spent_on,
            merchant_name=payload.merchant_name,
            status=ExpenseStatus.logged,
        )
        self.db.add(expense)
        await self.db.flush()

        await self._complete_onboarding_after_first_expense(parsed_user_id)
        await self.db.commit()
        await self.db.refresh(expense)
        return self._serialize_expense(expense)

    async def _complete_onboarding_after_first_expense(self, user_id: UUID) -> None:
        progress = await self.db.scalar(select(OnboardingProgress).where(OnboardingProgress.user_id == user_id))
        if progress is None or progress.is_completed:
            return

        progress.current_step = "completed"
        progress.completed_step_count = max(progress.completed_step_count, 4)
        progress.is_completed = True

    @staticmethod
    def _serialize_expense(expense: Expense) -> ExpenseResponse:
        return ExpenseResponse(
            id=str(expense.id),
            title=expense.title,
            description=expense.description,
            amount=expense.amount,
            currency=expense.currency,
            spent_on=expense.spent_on,
            category_id=str(expense.category_id) if expense.category_id else None,
            merchant_name=expense.merchant_name,
            status=expense.status.value,
        )

    @staticmethod
    def _parse_user_id(user_id: str) -> UUID:
        return ExpenseService._parse_uuid(user_id, "Invalid user identifier")

    @staticmethod
    def _parse_optional_uuid(value: str | None, detail: str) -> UUID | None:
        if value is None:
            return None
        return ExpenseService._parse_uuid(value, detail)

    @staticmethod
    def _parse_uuid(value: str, detail: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
