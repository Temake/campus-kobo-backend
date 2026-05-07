"""add app_lock_enabled and face_id_enabled to users

Revision ID: 0007_app_lock_face_id
Revises: 35fa4ce0bb6c
Create Date: 2026-05-07 08:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_app_lock_face_id"
down_revision: Union[str, None] = "35fa4ce0bb6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column_if_missing(
        "users",
        sa.Column("app_lock_enabled", sa.Boolean(), nullable=True, server_default=sa.false()),
    )
    _add_column_if_missing(
        "users",
        sa.Column("face_id_enabled", sa.Boolean(), nullable=True, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "face_id_enabled")
    op.drop_column("users", "app_lock_enabled")
