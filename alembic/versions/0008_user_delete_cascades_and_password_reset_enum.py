"""user delete cascades and password reset enum

Revision ID: 0008_user_delete_cascades
Revises: 0007_app_lock_face_id
Create Date: 2026-05-08 23:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_user_delete_cascades"
down_revision: Union[str, None] = "0007_app_lock_face_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_FKS: tuple[tuple[str, tuple[str, ...], str | None], ...] = (
    ("admin_audit_logs", ("admin_user_id",), "CASCADE"),
    ("budgets", ("user_id",), "CASCADE"),
    ("content_bookmarks", ("user_id",), "CASCADE"),
    ("email_verification_codes", ("user_id",), "CASCADE"),
    ("expense_categories", ("user_id",), "CASCADE"),
    ("expenses", ("user_id",), "CASCADE"),
    ("income", ("user_id",), "CASCADE"),
    ("learning_content", ("created_by",), "SET NULL"),
    ("notification_preference", ("user_id",), "CASCADE"),
    ("onboarding_progress", ("user_id",), "CASCADE"),
    ("refresh_tokens", ("user_id",), "CASCADE"),
    ("savings_goals", ("user_id",), "CASCADE"),
    ("support_messages", ("user_id",), "SET NULL"),
    ("user_goals", ("user_id",), "CASCADE"),
    ("user_sessions", ("user_id",), "CASCADE"),
)

OTHER_FKS: tuple[tuple[str, tuple[str, ...], str, tuple[str, ...], str | None], ...] = (
    ("expenses", ("category_id",), "expense_categories", ("id",), "SET NULL"),
)


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _columns_exist(table_name: str, column_names: tuple[str, ...]) -> bool:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    return all(column_name in existing_columns for column_name in column_names)


def _foreign_key_name(table_name: str, constrained_columns: tuple[str, ...]) -> str | None:
    inspector = sa.inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table_name):
        if tuple(foreign_key["constrained_columns"]) == constrained_columns:
            return foreign_key["name"]
    return None


def _replace_foreign_key(
    table_name: str,
    constrained_columns: tuple[str, ...],
    referred_table: str,
    referred_columns: tuple[str, ...],
    ondelete: str | None,
) -> None:
    if not _table_exists(table_name):
        return
    if not _table_exists(referred_table):
        return
    if not _columns_exist(table_name, constrained_columns):
        return
    if not _columns_exist(referred_table, referred_columns):
        return

    existing_name = _foreign_key_name(table_name, constrained_columns)
    if existing_name:
        op.drop_constraint(existing_name, table_name, type_="foreignkey")

    new_name = f"fk_{table_name}_{'_'.join(constrained_columns)}_{referred_table}"
    op.create_foreign_key(
        new_name,
        table_name,
        referred_table,
        list(constrained_columns),
        list(referred_columns),
        ondelete=ondelete,
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TYPE verificationpurpose ADD VALUE IF NOT EXISTS 'forgetpassword'")

    for table_name, columns, ondelete in USER_FKS:
        _replace_foreign_key(table_name, columns, "users", ("id",), ondelete)
    for table_name, columns, referred_table, referred_columns, ondelete in OTHER_FKS:
        _replace_foreign_key(table_name, columns, referred_table, referred_columns, ondelete)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table_name, columns, _ondelete in USER_FKS:
        _replace_foreign_key(table_name, columns, "users", ("id",), None)
    for table_name, columns, referred_table, referred_columns, _ondelete in OTHER_FKS:
        _replace_foreign_key(table_name, columns, referred_table, referred_columns, None)
