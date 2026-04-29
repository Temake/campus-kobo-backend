from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.expense import Expense, ExpenseStatus
from app.models.income import Income
from app.models.savings import SavingsGoal, SavingsGoalStatus
from app.schemas.dashboard import (
    DashboardBudgetSection,
    DashboardResponse,
    DashboardSavingsSection,
    DashboardSummaryResponse,
    DashboardSummarySection,
    ExpenseInsightResponse,
    RecentTransactionResponse,
)


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, user_id: str) -> DashboardSummaryResponse:
        dashboard = await self.get_dashboard(user_id)
        return DashboardSummaryResponse(
            monthly_budget=dashboard.budget.total_budget,
            total_spent=dashboard.summary.total_expenses,
            remaining_budget=dashboard.budget.remaining,
            savings_total=dashboard.savings.saved_amount,
            recent_expense_count=sum(1 for row in dashboard.recent_transactions if row.type == "expense"),
        )

    async def get_dashboard(self, user_id: str, *, recent_limit: int = 10) -> DashboardResponse:
        total_income = await self._get_total_income(user_id)
        total_expenses = await self._get_total_expenses(user_id)
        budget = await self._get_budget_section(user_id)
        savings = await self._get_savings_section(user_id)
        recent_transactions = await self._get_recent_transactions(user_id, recent_limit)
        expense_insights = await self._get_expense_insights(user_id, total_expenses)
        return DashboardResponse(
            current_balance=total_income - total_expenses,
            summary=DashboardSummarySection(total_income=total_income, total_expenses=total_expenses),
            budget=budget,
            savings=savings,
            recent_transactions=recent_transactions,
            expense_insights=expense_insights,
        )

    async def _get_total_income(self, user_id: str) -> Decimal:
        parsed_user_id = self._parse_uuid(user_id)
        total = await self.db.scalar(select(func.coalesce(func.sum(Income.amount), 0)).where(Income.user_id == parsed_user_id))
        return Decimal(total or 0)

    async def _get_total_expenses(self, user_id: str) -> Decimal:
        parsed_user_id = self._parse_uuid(user_id)
        total = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == parsed_user_id,
                Expense.status != ExpenseStatus.deleted,
            )
        )
        return Decimal(total or 0)

    async def _get_budget_section(self, user_id: str) -> DashboardBudgetSection:
        parsed_user_id = self._parse_uuid(user_id)
        budget = await self.db.scalar(
            select(Budget).where(Budget.user_id == parsed_user_id).order_by(Budget.period_end.desc(), Budget.created_at.desc())
        )
        if budget is None:
            return DashboardBudgetSection(
                budget_id=None,
                total_budget=Decimal("0.00"),
                spent=Decimal("0.00"),
                remaining=Decimal("0.00"),
                percentage_used=0.0,
            )

        spent = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == parsed_user_id,
                Expense.status != ExpenseStatus.deleted,
                Expense.spent_on >= budget.period_start,
                Expense.spent_on <= budget.period_end,
            )
        )
        spent_decimal = Decimal(spent or 0)
        return DashboardBudgetSection(
            budget_id=str(budget.id),
            total_budget=budget.amount,
            spent=spent_decimal,
            remaining=budget.amount - spent_decimal,
            percentage_used=self._percentage(spent_decimal, budget.amount),
        )

    async def _get_savings_section(self, user_id: str) -> DashboardSavingsSection:
        parsed_user_id = self._parse_uuid(user_id)
        goal = await self.db.scalar(
            select(SavingsGoal)
            .where(
                SavingsGoal.user_id == parsed_user_id,
                SavingsGoal.status.in_([SavingsGoalStatus.active, SavingsGoalStatus.completed]),
            )
            .order_by(SavingsGoal.created_at.desc())
        )
        if goal is None:
            return DashboardSavingsSection(
                goal_id=None,
                goal_name=None,
                saved_amount=Decimal("0.00"),
                target_amount=Decimal("0.00"),
                percentage_progress=0.0,
            )
        return DashboardSavingsSection(
            goal_id=str(goal.id),
            goal_name=goal.title,
            saved_amount=goal.current_amount,
            target_amount=goal.target_amount,
            percentage_progress=self._percentage(goal.current_amount, goal.target_amount),
        )

    async def _get_recent_transactions(self, user_id: str, limit: int) -> list[RecentTransactionResponse]:
        parsed_user_id = self._parse_uuid(user_id)
        income_rows = (
            await self.db.scalars(
                select(Income)
                .where(Income.user_id == parsed_user_id)
                .order_by(Income.received_on.desc(), Income.created_at.desc())
                .limit(limit)
            )
        ).all()
        expense_rows = (
            await self.db.scalars(
                select(Expense)
                .where(Expense.user_id == parsed_user_id, Expense.status != ExpenseStatus.deleted)
                .order_by(Expense.spent_on.desc(), Expense.created_at.desc())
                .limit(limit)
            )
        ).all()

        rows = [
            RecentTransactionResponse(
                id=str(income.id),
                type="income",
                title=income.category,
                amount=income.amount,
                date=income.received_on,
                category=income.category,
            )
            for income in income_rows
        ] + [
            RecentTransactionResponse(
                id=str(expense.id),
                type="expense",
                title=expense.title,
                amount=expense.amount,
                date=expense.spent_on,
                category=expense.category_name or expense.title,
            )
            for expense in expense_rows
        ]
        rows.sort(key=lambda row: (row.date, row.id), reverse=True)
        return rows[:limit]

    async def _get_expense_insights(self, user_id: str, total_expenses: Decimal) -> list[ExpenseInsightResponse]:
        parsed_user_id = self._parse_uuid(user_id)
        rows = (
            await self.db.execute(
                select(Expense.category_name, func.coalesce(func.sum(Expense.amount), 0))
                .where(Expense.user_id == parsed_user_id, Expense.status != ExpenseStatus.deleted)
                .group_by(Expense.category_name)
                .order_by(func.sum(Expense.amount).desc(), Expense.category_name.asc())
            )
        ).all()
        return [
            ExpenseInsightResponse(
                category=row[0] or "Uncategorized",
                amount=Decimal(row[1] or 0),
                percentage_of_total=self._percentage(Decimal(row[1] or 0), total_expenses),
            )
            for row in rows
        ]

    @staticmethod
    def _percentage(amount: Decimal, total: Decimal) -> float:
        if total == 0:
            return 0.0
        return round(float((Decimal(amount) / Decimal(total)) * 100), 2)

    @staticmethod
    def _parse_uuid(value: str) -> UUID:
        return UUID(value)
