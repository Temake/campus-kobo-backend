from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import DashboardSummaryResponse


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, user_id: str) -> DashboardSummaryResponse:
        return DashboardSummaryResponse(
            monthly_budget=Decimal("50000.00"),
            total_spent=Decimal("12000.00"),
            remaining_budget=Decimal("38000.00"),
            savings_total=Decimal("5000.00"),
            recent_expense_count=3,
        )
