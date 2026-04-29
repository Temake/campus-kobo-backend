from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetStatus
from app.models.expense import Expense, ExpenseStatus
from app.schemas.budget import BudgetCreateRequest, BudgetResponse, BudgetUpdateRequest
from app.schemas.dashboard import RecentTransactionResponse


class BudgetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_budgets(self, user_id: str) -> list[BudgetResponse]:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        budgets = (
            await self.db.scalars(
                select(Budget).where(Budget.user_id == parsed_user_id).order_by(Budget.period_start.desc(), Budget.created_at.desc())
            )
        ).all()
        return [await self._serialize_budget(budget, include_transactions=False) for budget in budgets]

    async def create_budget(self, user_id: str, payload: BudgetCreateRequest) -> BudgetResponse:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        budget = Budget(
            user_id=parsed_user_id,
            name=payload.name,
            amount=Decimal(payload.amount),
            currency=payload.currency,
            period_start=payload.period_start,
            period_end=payload.period_end,
            status=BudgetStatus.active,
        )
        self.db.add(budget)
        await self.db.commit()
        await self.db.refresh(budget)
        return await self._serialize_budget(budget, include_transactions=True)

    async def get_budget(self, user_id: str, budget_id: str) -> BudgetResponse:
        budget = await self._get_owned_budget(user_id, budget_id)
        return await self._serialize_budget(budget, include_transactions=True)

    async def update_budget(self, user_id: str, budget_id: str, payload: BudgetUpdateRequest) -> BudgetResponse:
        budget = await self._get_owned_budget(user_id, budget_id)
        budget.name = payload.name
        budget.amount = Decimal(payload.amount)
        budget.currency = payload.currency
        budget.period_start = payload.period_start
        budget.period_end = payload.period_end
        budget.status = BudgetStatus.active
        await self.db.commit()
        await self.db.refresh(budget)
        return await self._serialize_budget(budget, include_transactions=True)

    async def delete_budget(self, user_id: str, budget_id: str) -> None:
        budget = await self._get_owned_budget(user_id, budget_id)
        await self.db.delete(budget)
        await self.db.commit()

    async def _get_owned_budget(self, user_id: str, budget_id: str) -> Budget:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        parsed_budget_id = self._parse_uuid(budget_id, "Invalid budget identifier")
        budget = await self.db.scalar(
            select(Budget).where(Budget.id == parsed_budget_id, Budget.user_id == parsed_user_id)
        )
        if budget is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
        return budget

    async def _serialize_budget(self, budget: Budget, *, include_transactions: bool) -> BudgetResponse:
        total_spent = await self._get_total_spent(budget)
        return BudgetResponse(
            id=str(budget.id),
            name=budget.name,
            amount=budget.amount,
            currency=budget.currency,
            period_start=budget.period_start,
            period_end=budget.period_end,
            status=budget.status.value,
            total_budget=budget.amount,
            total_spent=total_spent,
            remaining_amount=budget.amount - total_spent,
            percentage_used=self._percentage(total_spent, budget.amount),
            days_left=max((budget.period_end - date.today()).days, 0),
            highest_spent=await self._get_highest_spent_category(budget),
            recent_transactions=await self._get_recent_transactions(budget) if include_transactions else [],
        )

    async def _get_total_spent(self, budget: Budget) -> Decimal:
        total = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == budget.user_id,
                Expense.status != ExpenseStatus.deleted,
                Expense.spent_on >= budget.period_start,
                Expense.spent_on <= budget.period_end,
            )
        )
        return Decimal(total or 0)

    async def _get_highest_spent_category(self, budget: Budget) -> str | None:
        row = (
            await self.db.execute(
                select(Expense.category_name, func.coalesce(func.sum(Expense.amount), 0).label("total"))
                .where(
                    Expense.user_id == budget.user_id,
                    Expense.status != ExpenseStatus.deleted,
                    Expense.spent_on >= budget.period_start,
                    Expense.spent_on <= budget.period_end,
                )
                .group_by(Expense.category_name)
                .order_by(func.sum(Expense.amount).desc(), Expense.category_name.asc())
                .limit(1)
            )
        ).first()
        return None if row is None else row[0]

    async def _get_recent_transactions(self, budget: Budget) -> list[RecentTransactionResponse]:
        expenses = (
            await self.db.scalars(
                select(Expense)
                .where(
                    Expense.user_id == budget.user_id,
                    Expense.status != ExpenseStatus.deleted,
                    Expense.spent_on >= budget.period_start,
                    Expense.spent_on <= budget.period_end,
                )
                .order_by(Expense.spent_on.desc(), Expense.created_at.desc())
                .limit(5)
            )
        ).all()
        return [
            RecentTransactionResponse(
                id=str(expense.id),
                type="expense",
                title=expense.title,
                amount=expense.amount,
                date=expense.spent_on,
                category=expense.category_name or expense.title,
            )
            for expense in expenses
        ]

    @staticmethod
    def _percentage(amount: Decimal, total: Decimal) -> float:
        if total == 0:
            return 0.0
        return round(float((Decimal(amount) / Decimal(total)) * 100), 2)

    @staticmethod
    def _parse_uuid(value: str, detail: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
