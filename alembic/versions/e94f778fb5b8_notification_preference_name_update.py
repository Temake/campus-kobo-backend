"""Notification preference name update

Revision ID: e94f778fb5b8
Revises: 0006_notification_preferences
Create Date: 2026-05-07 05:20:24.461047
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'e94f778fb5b8'
down_revision: Union[str, None] = '0006_notification_preferences'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
