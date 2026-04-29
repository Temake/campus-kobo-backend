"""add income table and expense recurring fields

Revision ID: 0002_add_income_recurring
Revises: 0001_initial_schema
Create Date: 2026-04-29 22:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_add_income_recurring"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Create ExpenseRepeat enum (PostgreSQL only) ──────────────────
    expense_repeat = postgresql.ENUM("daily", "weekly", "monthly", "yearly", name="expenserepeat", create_type=False)
    expense_repeat.create(bind, checkfirst=True)

    # ── 2. Create income table ──────────────────────────────────────────
    op.create_table(
        "income",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_income_user_id", "income", ["user_id"], unique=False)
    op.create_index("ix_income_user_received_on", "income", ["user_id", "received_on"], unique=False)

    # ── 3. Add missing columns to expenses ──────────────────────────────
    op.add_column("expenses", sa.Column("category_name", sa.String(length=100), nullable=True))
    op.add_column("expenses", sa.Column("is_recurring", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("expenses", sa.Column("repeats", expense_repeat, nullable=True))
    op.add_column("expenses", sa.Column("next_due_date", sa.Date(), nullable=True))

    # ── 4. Add missing indexes ──────────────────────────────────────────
    op.create_index("ix_expenses_user_spent_on", "expenses", ["user_id", "spent_on"], unique=False)
    op.create_index("ix_budgets_user_period", "budgets", ["user_id", "period_start", "period_end"], unique=False)
    op.create_index("ix_savings_goals_user_target_date", "savings_goals", ["user_id", "target_date"], unique=False)


def downgrade() -> None:
    # ── Indexes ─────────────────────────────────────────────────────────
    op.drop_index("ix_savings_goals_user_target_date", table_name="savings_goals")
    op.drop_index("ix_budgets_user_period", table_name="budgets")
    op.drop_index("ix_expenses_user_spent_on", table_name="expenses")

    # ── Expense columns ────────────────────────────────────────────────
    op.drop_column("expenses", "next_due_date")
    op.drop_column("expenses", "repeats")
    op.drop_column("expenses", "is_recurring")
    op.drop_column("expenses", "category_name")

    # ── Income table ───────────────────────────────────────────────────
    op.drop_index("ix_income_user_received_on", table_name="income")
    op.drop_index("ix_income_user_id", table_name="income")
    op.drop_table("income")

    # ── Enum ───────────────────────────────────────────────────────────
    op.execute(sa.text("DROP TYPE IF EXISTS expenserepeat CASCADE;"))
