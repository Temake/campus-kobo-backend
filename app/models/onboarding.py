import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class UserGoalType(str, enum.Enum):
    stay_on_budget = "stay_on_budget"
    track_expenses = "track_expenses"
    save_money = "save_money"


class UserGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_goals"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    goal_type: Mapped[UserGoalType] = mapped_column(Enum(UserGoalType), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OnboardingProgress(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "onboarding_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="intro")
    completed_step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
