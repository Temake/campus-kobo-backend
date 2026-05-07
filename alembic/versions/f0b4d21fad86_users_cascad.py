"""users cascad

Revision ID: f0b4d21fad86
Revises: 0004_cascade_savings_deletes
Create Date: 2026-05-06 23:56:48.443712
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'f0b4d21fad86'
down_revision: Union[str, None] = '0004_cascade_savings_deletes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
