"""cascade savings goal deletes

Revision ID: 0004_cascade_savings_deletes
Revises: 0003_profile_admin_learning
Create Date: 2026-05-05 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_cascade_savings_deletes"
down_revision: Union[str, None] = "0003_profile_admin_learning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_NAME = "fk_savings_contributions_savings_goal_id_savings_goals"
NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    fk_names = [
        fk["name"] or FK_NAME
        for fk in inspector.get_foreign_keys("savings_contributions")
        if fk.get("referred_table") == "savings_goals"
    ]

    with op.batch_alter_table(
        "savings_contributions",
        naming_convention=NAMING_CONVENTION,
        recreate=recreate,
    ) as batch_op:
        for fk_name in sorted(set(fk_names)):
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            FK_NAME,
            "savings_goals",
            ["savings_goal_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"

    with op.batch_alter_table(
        "savings_contributions",
        naming_convention=NAMING_CONVENTION,
        recreate=recreate,
    ) as batch_op:
        batch_op.drop_constraint(FK_NAME, type_="foreignkey")
        batch_op.create_foreign_key(
            "savings_contributions_savings_goal_id_fkey",
            "savings_goals",
            ["savings_goal_id"],
            ["id"],
        )
