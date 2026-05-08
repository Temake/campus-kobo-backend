import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class ExpenseStatus(str, enum.Enum):
    logged = "logged"
    edited = "edited"
    deleted = "deleted"


class ExpenseRepeat(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_user_spent_on", "user_id", "spent_on"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("expense_categories.id", ondelete="SET NULL"))
    category_name: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="NGN", nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String(255))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    repeats: Mapped[ExpenseRepeat | None] = mapped_column(Enum(ExpenseRepeat))
    next_due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ExpenseStatus] = mapped_column(Enum(ExpenseStatus), default=ExpenseStatus.logged, nullable=False)
