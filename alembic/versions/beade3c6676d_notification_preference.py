"""Notification preference

Revision ID: beade3c6676d
Revises: 0005_learning_hub_faq
Create Date: 2026-05-07 02:36:57.885669
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'beade3c6676d'
down_revision: Union[str, None] = '0005_learning_hub_faq'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
