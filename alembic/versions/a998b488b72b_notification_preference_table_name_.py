"""Notification preference table name update

Revision ID: a998b488b72b
Revises: e94f778fb5b8
Create Date: 2026-05-07 05:25:25.219195
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'a998b488b72b'
down_revision: Union[str, None] = 'e94f778fb5b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
