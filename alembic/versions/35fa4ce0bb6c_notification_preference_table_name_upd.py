"""Notification preference table name upd

Revision ID: 35fa4ce0bb6c
Revises: a998b488b72b
Create Date: 2026-05-07 05:32:39.926105
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '35fa4ce0bb6c'
down_revision: Union[str, None] = 'a998b488b72b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.rename_table(
        "notification_preferences",
        "notification_preference"
    )


def downgrade():
    op.rename_table(
        "notification_preference",
        "notification_preferences"
    )