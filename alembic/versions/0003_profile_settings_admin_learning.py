"""profile settings and admin learning

Revision ID: 0003_profile_admin_learning
Revises: 0002_add_income_recurring
Create Date: 2026-04-30 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_profile_admin_learning"
down_revision: Union[str, None] = "0002_add_income_recurring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        user_role = postgresql.ENUM("user", "admin", name="userrole", create_type=False)
        learning_content_status = postgresql.ENUM("draft", "published", name="learningcontentstatus", create_type=False)
    else:
        user_role = sa.String(length=16)
        learning_content_status = sa.String(length=16)

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                    CREATE TYPE userrole AS ENUM ('user', 'admin');
                END IF;
            END
            $$;
            """
        )
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'learningcontentstatus') THEN
                    CREATE TYPE learningcontentstatus AS ENUM ('draft', 'published');
                END IF;
            END
            $$;
            """
        )

    _add_column_if_missing("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    _add_column_if_missing("users", sa.Column("role", user_role, nullable=False, server_default="user"))
    _add_column_if_missing("users", sa.Column("hide_balance", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing("users", sa.Column("allow_analytics", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column_if_missing("users", sa.Column("admin_two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing("users", sa.Column("admin_two_factor_secret", sa.String(length=255), nullable=True))
    _add_column_if_missing("users", sa.Column("admin_ip_allowlist", sa.Text(), nullable=True))

    _add_column_if_missing("user_sessions", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))

    _add_column_if_missing("learning_content", sa.Column("created_by", sa.Uuid(), nullable=True))
    _add_column_if_missing(
        "learning_content",
        sa.Column(
            "status",
            learning_content_status,
            nullable=False,
            server_default="draft",
        ),
    )
    _add_column_if_missing(
        "learning_content", sa.Column("content_type", sa.String(length=32), nullable=False, server_default="article")
    )
    _add_column_if_missing("learning_content", sa.Column("media_url", sa.String(length=500), nullable=True))
    _add_column_if_missing("learning_content", sa.Column("media_public_id", sa.String(length=255), nullable=True))
    _add_column_if_missing("learning_content", sa.Column("media_resource_type", sa.String(length=32), nullable=True))
    _add_column_if_missing("learning_content", sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"))

    if bind.dialect.name == "postgresql":
        op.create_foreign_key("fk_learning_content_created_by_users", "learning_content", "users", ["created_by"], ["id"])
        op.execute("UPDATE learning_content SET status = 'published' WHERE is_published = true")
    else:
        op.execute("UPDATE learning_content SET status = 'published' WHERE is_published = 1")

    if not _has_table("admin_audit_logs"):
        op.create_table(
            "admin_audit_logs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("admin_user_id", sa.Uuid(), nullable=False),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("resource_type", sa.String(length=100), nullable=False),
            sa.Column("resource_id", sa.String(length=100), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("admin_audit_logs")
    op.drop_constraint("fk_learning_content_created_by_users", "learning_content", type_="foreignkey")
    op.drop_column("learning_content", "view_count")
    op.drop_column("learning_content", "media_resource_type")
    op.drop_column("learning_content", "media_public_id")
    op.drop_column("learning_content", "media_url")
    op.drop_column("learning_content", "content_type")
    op.drop_column("learning_content", "status")
    op.drop_column("learning_content", "created_by")
    op.drop_column("user_sessions", "revoked_at")
    op.drop_column("users", "admin_ip_allowlist")
    op.drop_column("users", "admin_two_factor_secret")
    op.drop_column("users", "admin_two_factor_enabled")
    op.drop_column("users", "allow_analytics")
    op.drop_column("users", "hide_balance")
    op.drop_column("users", "role")
    op.drop_column("users", "avatar_url")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP TYPE IF EXISTS learningcontentstatus CASCADE;"))
        op.execute(sa.text("DROP TYPE IF EXISTS userrole CASCADE;"))
