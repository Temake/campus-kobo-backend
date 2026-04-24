from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.dashboard import DashboardSummaryResponse


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_summary(self, user_id: str) -> DashboardSummaryResponse:
        # Aggregate budget, expenses, savings, and recent activity.
        return DashboardSummaryResponse(
            monthly_budget=Decimal("50000.00"),
            total_spent=Decimal("12000.00"),
            remaining_budget=Decimal("38000.00"),
            savings_total=Decimal("5000.00"),
            recent_expense_count=3,
        )
