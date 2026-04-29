from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.category import ExpenseCategory
from app.models.expense import Expense, ExpenseStatus
from app.models.onboarding import OnboardingProgress
from app.schemas.expense import ExpenseCreateRequest, ExpenseResponse, ExpenseUpdateRequest


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
        total_expenses = await self._get_total_expenses(parsed_user_id)
        budgets = await self._get_user_budgets(parsed_user_id)
        return [self._serialize_expense(expense, total_expenses, budgets) for expense in expenses]

    async def create_expense(self, user_id: str, payload: ExpenseCreateRequest) -> ExpenseResponse:
        parsed_user_id = self._parse_user_id(user_id)
        category_id, category_name = await self._resolve_category(parsed_user_id, payload.category_id, payload.category)
        expense = Expense(
            user_id=parsed_user_id,
            category_id=category_id,
            category_name=category_name,
            title=payload.title or category_name or payload.merchant_name or "Expense",
            description=payload.note or payload.description,
            amount=Decimal(payload.amount),
            currency=payload.currency,
            spent_on=payload.date or payload.spent_on,
            merchant_name=payload.merchant_name,
            is_recurring=payload.is_recurring,
            repeats=payload.repeats,
            next_due_date=payload.next_due_date,
            status=ExpenseStatus.logged,
        )
        self.db.add(expense)
        await self.db.flush()

        await self._complete_onboarding_after_first_expense(parsed_user_id)
        await self.db.commit()
        await self.db.refresh(expense)

        total_expenses = await self._get_total_expenses(parsed_user_id)
        budgets = await self._get_user_budgets(parsed_user_id)
        return self._serialize_expense(expense, total_expenses, budgets)

    async def get_expense(self, user_id: str, expense_id: str) -> ExpenseResponse:
        parsed_user_id = self._parse_user_id(user_id)
        expense = await self._get_owned_expense(parsed_user_id, expense_id)
        total_expenses = await self._get_total_expenses(parsed_user_id)
        budgets = await self._get_user_budgets(parsed_user_id)
        return self._serialize_expense(expense, total_expenses, budgets)

    async def update_expense(self, user_id: str, expense_id: str, payload: ExpenseUpdateRequest) -> ExpenseResponse:
        parsed_user_id = self._parse_user_id(user_id)
        expense = await self._get_owned_expense(parsed_user_id, expense_id)
        category_id, category_name = await self._resolve_category(parsed_user_id, payload.category_id, payload.category)
        expense.category_id = category_id
        expense.category_name = category_name
        expense.title = payload.title or category_name or payload.merchant_name or expense.title
        expense.description = payload.note or payload.description
        expense.amount = Decimal(payload.amount)
        expense.currency = payload.currency
        expense.spent_on = payload.date or payload.spent_on
        expense.merchant_name = payload.merchant_name
        expense.is_recurring = payload.is_recurring
        expense.repeats = payload.repeats
        expense.next_due_date = payload.next_due_date
        expense.status = ExpenseStatus.edited
        await self.db.commit()
        await self.db.refresh(expense)

        total_expenses = await self._get_total_expenses(parsed_user_id)
        budgets = await self._get_user_budgets(parsed_user_id)
        return self._serialize_expense(expense, total_expenses, budgets)

    async def delete_expense(self, user_id: str, expense_id: str) -> None:
        parsed_user_id = self._parse_user_id(user_id)
        expense = await self._get_owned_expense(parsed_user_id, expense_id)
        expense.status = ExpenseStatus.deleted
        await self.db.commit()

    async def _complete_onboarding_after_first_expense(self, user_id: UUID) -> None:
        progress = await self.db.scalar(select(OnboardingProgress).where(OnboardingProgress.user_id == user_id))
        if progress is None or progress.is_completed:
            return

        progress.current_step = "completed"
        progress.completed_step_count = max(progress.completed_step_count, 4)
        progress.is_completed = True

    async def _resolve_category(
        self,
        user_id: UUID,
        category_id_value: str | None,
        category_name_value: str | None,
    ) -> tuple[UUID | None, str | None]:
        category_id = self._parse_optional_uuid(category_id_value, "Invalid category id")
        if category_id is None:
            return None, category_name_value

        category = await self.db.scalar(select(ExpenseCategory).where(ExpenseCategory.id == category_id))
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        if category.user_id not in {None, user_id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Category does not belong to the current user")
        if category.user_id is None and not category.is_default:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is not available")
        return category_id, category.name

    async def _get_owned_expense(self, user_id: UUID, expense_id: str) -> Expense:
        parsed_expense_id = self._parse_uuid(expense_id, "Invalid expense identifier")
        expense = await self.db.scalar(
            select(Expense).where(
                Expense.id == parsed_expense_id,
                Expense.user_id == user_id,
                Expense.status != ExpenseStatus.deleted,
            )
        )
        if expense is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
        return expense

    async def _get_total_expenses(self, user_id: UUID) -> Decimal:
        total = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user_id,
                Expense.status != ExpenseStatus.deleted,
            )
        )
        return Decimal(total or 0)

    async def _get_user_budgets(self, user_id: UUID) -> list[Budget]:
        return (
            await self.db.scalars(
                select(Budget).where(Budget.user_id == user_id).order_by(Budget.period_end.desc(), Budget.created_at.desc())
            )
        ).all()

    def _serialize_expense(self, expense: Expense, total_expenses: Decimal, budgets: list[Budget]) -> ExpenseResponse:
        matching_budget = self._matching_budget(expense.spent_on, budgets)
        category = expense.category_name or expense.title
        return ExpenseResponse(
            id=str(expense.id),
            title=expense.title,
            category=category,
            amount=expense.amount,
            currency=expense.currency,
            date=expense.spent_on,
            note=expense.description,
            is_recurring=expense.is_recurring,
            repeats=expense.repeats,
            next_due_date=expense.next_due_date,
            percentage_of_total_expenses=self._percentage(expense.amount, total_expenses),
            percentage_of_budget=(
                self._percentage(expense.amount, matching_budget.amount) if matching_budget is not None else None
            ),
            status=expense.status.value,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )

    @staticmethod
    def _matching_budget(spent_on, budgets: list[Budget]) -> Budget | None:
        for budget in budgets:
            if budget.period_start <= spent_on <= budget.period_end:
                return budget
        return None

    @staticmethod
    def _percentage(amount: Decimal, total: Decimal) -> float:
        if total == 0:
            return 0.0
        return round(float((Decimal(amount) / Decimal(total)) * 100), 2)

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
