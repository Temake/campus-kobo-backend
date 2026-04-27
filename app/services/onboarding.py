from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetStatus
from app.models.category import ExpenseCategory
from app.models.onboarding import OnboardingProgress, UserGoal, UserGoalType
from app.schemas.onboarding import (
    BudgetSetupRequest,
    CategorySetupRequest,
    GoalSelectionRequest,
    OnboardingProgressResponse,
)


class OnboardingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_progress(self, user_id: str) -> OnboardingProgressResponse:
        parsed_user_id = self._parse_user_id(user_id)
        progress = await self._get_or_create_progress(parsed_user_id)
        await self.db.commit()
        return self._serialize_progress(progress)

    async def select_goal(self, user_id: str, payload: GoalSelectionRequest) -> None:
        parsed_user_id = self._parse_user_id(user_id)
        goal_type = self._parse_goal_type(payload.goal_type)
        progress = await self._get_or_create_progress(parsed_user_id)

        existing_primary_goal = await self.db.scalar(
            select(UserGoal).where(UserGoal.user_id == parsed_user_id, UserGoal.is_primary.is_(True))
        )
        if existing_primary_goal is None:
            self.db.add(UserGoal(user_id=parsed_user_id, goal_type=goal_type, is_primary=True))
        else:
            existing_primary_goal.goal_type = goal_type
            existing_primary_goal.is_primary = True

        self._advance_progress(progress, next_step="budget_setup", minimum_completed_steps=1)
        await self.db.commit()

    async def setup_budget(self, user_id: str, payload: BudgetSetupRequest) -> None:
        parsed_user_id = self._parse_user_id(user_id)
        progress = await self._get_or_create_progress(parsed_user_id)

        amount = Decimal(payload.amount)
        if amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Budget must be positive")

        period_start, period_end = self._current_month_period()
        existing_budget = await self.db.scalar(
            select(Budget).where(
                Budget.user_id == parsed_user_id,
                Budget.period_start == period_start,
                Budget.period_end == period_end,
            )
        )

        if existing_budget is None:
            self.db.add(
                Budget(
                    user_id=parsed_user_id,
                    name="Monthly Budget",
                    amount=amount,
                    currency=payload.currency,
                    period_start=period_start,
                    period_end=period_end,
                    status=BudgetStatus.active,
                )
            )
        else:
            existing_budget.amount = amount
            existing_budget.currency = payload.currency
            existing_budget.status = BudgetStatus.active

        self._advance_progress(progress, next_step="category_setup", minimum_completed_steps=2)
        await self.db.commit()

    async def setup_categories(self, user_id: str, payload: CategorySetupRequest) -> None:
        parsed_user_id = self._parse_user_id(user_id)
        progress = await self._get_or_create_progress(parsed_user_id)

        if not payload.category_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one category is required")

        parsed_category_ids = [self._parse_uuid(category_id, "Invalid category id") for category_id in payload.category_ids]
        categories = (
            await self.db.scalars(select(ExpenseCategory).where(ExpenseCategory.id.in_(parsed_category_ids)))
        ).all()
        category_map = {category.id: category for category in categories}

        if len(category_map) != len(set(parsed_category_ids)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more categories were not found")

        existing_user_categories = (
            await self.db.scalars(select(ExpenseCategory).where(ExpenseCategory.user_id == parsed_user_id))
        ).all()
        existing_user_category_names = {category.name for category in existing_user_categories}

        for category_id in parsed_category_ids:
            category = category_map[category_id]
            if category.user_id == parsed_user_id:
                continue
            if category.user_id is not None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Category does not belong to the current user")
            if not category.is_default:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is not available for onboarding")
            if category.name in existing_user_category_names:
                continue

            self.db.add(
                ExpenseCategory(
                    user_id=parsed_user_id,
                    name=category.name,
                    icon_name=category.icon_name,
                    color_hex=category.color_hex,
                    is_default=False,
                    is_active=True,
                )
            )
            existing_user_category_names.add(category.name)

        self._advance_progress(progress, next_step="first_expense", minimum_completed_steps=3)
        await self.db.commit()

    async def _get_or_create_progress(self, user_id: UUID) -> OnboardingProgress:
        progress = await self.db.scalar(select(OnboardingProgress).where(OnboardingProgress.user_id == user_id))
        if progress is None:
            progress = OnboardingProgress(user_id=user_id, current_step="intro", completed_step_count=0, is_completed=False)
            self.db.add(progress)
            await self.db.flush()
        return progress

    @staticmethod
    def _advance_progress(progress: OnboardingProgress, next_step: str, minimum_completed_steps: int) -> None:
        progress.current_step = next_step
        progress.completed_step_count = max(progress.completed_step_count, minimum_completed_steps)
        progress.is_completed = False

    @staticmethod
    def _serialize_progress(progress: OnboardingProgress) -> OnboardingProgressResponse:
        return OnboardingProgressResponse(
            current_step=progress.current_step,
            completed_step_count=progress.completed_step_count,
            is_completed=progress.is_completed,
        )

    @staticmethod
    def _parse_goal_type(goal_type: str) -> UserGoalType:
        try:
            return UserGoalType(goal_type)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid goal type") from exc

    @staticmethod
    def _parse_user_id(user_id: str) -> UUID:
        return OnboardingService._parse_uuid(user_id, "Invalid user identifier")

    @staticmethod
    def _parse_uuid(value: str, detail: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

    @staticmethod
    def _current_month_period(today: date | None = None) -> tuple[date, date]:
        current_day = today or date.today()
        period_start = current_day.replace(day=1)
        period_end = current_day.replace(day=monthrange(current_day.year, current_day.month)[1])
        return period_start, period_end
