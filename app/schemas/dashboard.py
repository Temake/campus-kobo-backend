from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class RecentTransactionResponse(BaseModel):
    id: str
    type: str
    title: str
    amount: Decimal
    date: date
    category: str | None = None


class DashboardSummarySection(BaseModel):
    total_income: Decimal
    total_expenses: Decimal


class DashboardBudgetSection(BaseModel):
    budget_id: str | None = None
    total_budget: Decimal
    spent: Decimal
    remaining: Decimal
    percentage_used: float


class DashboardSavingsSection(BaseModel):
    goal_id: str | None = None
    goal_name: str | None = None
    saved_amount: Decimal
    target_amount: Decimal
    percentage_progress: float


class ExpenseInsightResponse(BaseModel):
    category: str
    amount: Decimal
    percentage_of_total: float


class DashboardResponse(BaseModel):
    current_balance: Decimal
    summary: DashboardSummarySection
    budget: DashboardBudgetSection
    savings: DashboardSavingsSection
    recent_transactions: list[RecentTransactionResponse] = Field(default_factory=list)
    expense_insights: list[ExpenseInsightResponse] = Field(default_factory=list)


class DashboardSummaryResponse(BaseModel):
    monthly_budget: Decimal
    total_spent: Decimal
    remaining_budget: Decimal
    savings_total: Decimal
    recent_expense_count: int
