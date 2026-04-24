from decimal import Decimal

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    monthly_budget: Decimal
    total_spent: Decimal
    remaining_budget: Decimal
    savings_total: Decimal
    recent_expense_count: int
