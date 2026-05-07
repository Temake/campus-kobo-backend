"""notification preferences shape

Revision ID: 0006_notification_preferences
Revises: beade3c6676d
Create Date: 2026-05-07 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_notification_preferences"
down_revision: Union[str, None] = "beade3c6676d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PREFERENCE_COLUMNS = (
    "all_notifications",
    "budget_alerts",
    "savings_reminders",
    "bill_reminders",
    "new_content",
    "finance_101",
    "podcast_updates",
    "app_updates",
    "bof_announcements",
)


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _create_new_table(table_name: str) -> None:
    op.create_table(
        table_name,
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("all_notifications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("budget_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("savings_reminders", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("bill_reminders", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("new_content", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("finance_101", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("podcast_updates", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("app_updates", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("bof_announcements", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("do_not_disturb", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quiet_hours_start", sa.Time(), nullable=True, server_default=sa.text("'22:00:00'")),
        sa.Column("quiet_hours_end", sa.Time(), nullable=True, server_default=sa.text("'07:00:00'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=f"{table_name}_user_id_fkey",
        ),
        sa.PrimaryKeyConstraint("user_id", name=f"{table_name}_pkey"),
    )


def upgrade() -> None:
    if not _has_table("notification_preferences"):
        _create_new_table("notification_preferences")
        return

    bind = op.get_bind()
    _create_new_table("notification_preferences_new")

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                INSERT INTO notification_preferences_new (
                    user_id,
                    all_notifications,
                    budget_alerts,
                    savings_reminders,
                    bill_reminders,
                    new_content,
                    finance_101,
                    podcast_updates,
                    app_updates,
                    bof_announcements,
                    do_not_disturb,
                    quiet_hours_start,
                    quiet_hours_end,
                    updated_at
                )
                SELECT
                    user_id,
                    all_notifications,
                    budget_alerts,
                    savings_reminders,
                    bill_reminders,
                    new_content,
                    finance_101,
                    podcast_updates,
                    app_updates,
                    bof_announcements,
                    do_not_disturb,
                    quiet_hours_start,
                    quiet_hours_end,
                    updated_at
                FROM notification_preferences
                """
            )
        )
    else:
        op.execute(
            """
            INSERT INTO notification_preferences_new (
                user_id,
                all_notifications,
                budget_alerts,
                savings_reminders,
                bill_reminders,
                new_content,
                finance_101,
                podcast_updates,
                app_updates,
                bof_announcements,
                do_not_disturb,
                quiet_hours_start,
                quiet_hours_end,
                updated_at
            )
            SELECT
                user_id,
                all_notifications,
                budget_alerts,
                savings_reminders,
                bill_reminders,
                new_content,
                finance_101,
                podcast_updates,
                app_updates,
                bof_announcements,
                do_not_disturb,
                quiet_hours_start,
                quiet_hours_end,
                updated_at
            FROM notification_preferences
            """
        )

    op.drop_table("notification_preferences")
    op.rename_table("notification_preferences_new", "notification_preferences")


def downgrade() -> None:
    if not _has_table("notification_preferences"):
        return

    op.create_table(
        "notification_preferences_old",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=100), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quiet_hours_start", sa.Time(), nullable=True),
        sa.Column("quiet_hours_end", sa.Time(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="notification_preferences_user_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "notification_type",
            name="uq_notification_preferences_user_type",
        ),
    )

    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        for column in PREFERENCE_COLUMNS:
            op.execute(
                sa.text(
                    f"""
                    INSERT INTO notification_preferences_old (
                        id,
                        user_id,
                        notification_type,
                        is_enabled,
                        quiet_hours_enabled,
                        quiet_hours_start,
                        quiet_hours_end,
                        created_at,
                        updated_at
                    )
                    SELECT
                        gen_random_uuid(),
                        user_id,
                        '{column}',
                        {column},
                        do_not_disturb,
                        quiet_hours_start,
                        quiet_hours_end,
                        COALESCE(updated_at, now()),
                        COALESCE(updated_at, now())
                    FROM notification_preferences
                    """
                )
            )

    op.drop_table("notification_preferences")
    op.rename_table("notification_preferences_old", "notification_preferences")