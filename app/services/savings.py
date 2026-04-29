from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.savings import SavingsContribution, SavingsGoal, SavingsGoalStatus
from app.schemas.savings import SavingsContributionRequest, SavingsGoalCreateRequest, SavingsGoalResponse, SavingsGoalUpdateRequest


class SavingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_goals(self, user_id: str) -> list[SavingsGoalResponse]:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        goals = (
            await self.db.scalars(
                select(SavingsGoal).where(SavingsGoal.user_id == parsed_user_id).order_by(SavingsGoal.created_at.desc())
            )
        ).all()
        return [self._serialize_goal(goal) for goal in goals]

    async def create_goal(self, user_id: str, payload: SavingsGoalCreateRequest) -> SavingsGoalResponse:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        current_amount = Decimal(payload.initial_deposit)
        goal = SavingsGoal(
            user_id=parsed_user_id,
            title=payload.goal_name,
            description=payload.note,
            target_amount=Decimal(payload.target_amount),
            current_amount=current_amount,
            currency="NGN",
            target_date=payload.target_date,
            status=self._status_for_amount(current_amount, Decimal(payload.target_amount)),
        )
        self.db.add(goal)
        await self.db.commit()
        await self.db.refresh(goal)
        return self._serialize_goal(goal)

    async def get_goal(self, user_id: str, goal_id: str) -> SavingsGoalResponse:
        goal = await self._get_owned_goal(user_id, goal_id)
        return self._serialize_goal(goal)

    async def update_goal(self, user_id: str, goal_id: str, payload: SavingsGoalUpdateRequest) -> SavingsGoalResponse:
        goal = await self._get_owned_goal(user_id, goal_id)
        goal.title = payload.goal_name
        goal.description = payload.note
        goal.target_amount = Decimal(payload.target_amount)
        goal.current_amount = Decimal(payload.initial_deposit)
        goal.target_date = payload.target_date
        goal.status = self._status_for_amount(goal.current_amount, goal.target_amount)
        await self.db.commit()
        await self.db.refresh(goal)
        return self._serialize_goal(goal)

    async def delete_goal(self, user_id: str, goal_id: str) -> None:
        goal = await self._get_owned_goal(user_id, goal_id)
        await self.db.delete(goal)
        await self.db.commit()

    async def add_contribution(self, user_id: str, goal_id: str, payload: SavingsContributionRequest) -> SavingsGoalResponse:
        goal = await self._get_owned_goal(user_id, goal_id)
        contribution = SavingsContribution(
            savings_goal_id=goal.id,
            amount=Decimal(payload.amount),
            note=payload.note,
        )
        self.db.add(contribution)
        goal.current_amount = Decimal(goal.current_amount) + Decimal(payload.amount)
        goal.status = self._status_for_amount(goal.current_amount, goal.target_amount)
        await self.db.commit()
        await self.db.refresh(goal)
        return self._serialize_goal(goal)

    async def _get_owned_goal(self, user_id: str, goal_id: str) -> SavingsGoal:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        parsed_goal_id = self._parse_uuid(goal_id, "Invalid savings identifier")
        goal = await self.db.scalar(
            select(SavingsGoal).where(SavingsGoal.id == parsed_goal_id, SavingsGoal.user_id == parsed_user_id)
        )
        if goal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Savings goal not found")
        return goal

    def _serialize_goal(self, goal: SavingsGoal) -> SavingsGoalResponse:
        return SavingsGoalResponse(
            id=str(goal.id),
            goal_name=goal.title,
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
            target_date=goal.target_date,
            note=goal.description,
            percentage_progress=self._percentage(goal.current_amount, goal.target_amount),
            status=goal.status.value,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )

    @staticmethod
    def _percentage(amount: Decimal, total: Decimal) -> float:
        if total == 0:
            return 0.0
        return round(float((Decimal(amount) / Decimal(total)) * 100), 2)

    @staticmethod
    def _status_for_amount(current_amount: Decimal, target_amount: Decimal) -> SavingsGoalStatus:
        if current_amount >= target_amount:
            return SavingsGoalStatus.completed
        return SavingsGoalStatus.active

    @staticmethod
    def _parse_uuid(value: str, detail: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
