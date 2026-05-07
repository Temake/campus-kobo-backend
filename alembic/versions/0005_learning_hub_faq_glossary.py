"""learning hub faq glossary

Revision ID: 0005_learning_hub_faq
Revises: f0b4d21fad86
Create Date: 2026-05-06 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_learning_hub_faq"
down_revision: Union[str, None] = "f0b4d21fad86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column_if_missing("learning_categories", sa.Column("description", sa.Text(), nullable=True))
    _add_column_if_missing("learning_categories", sa.Column("icon_name", sa.String(length=100), nullable=True))

    _add_column_if_missing("learning_content", sa.Column("duration", sa.String(length=100), nullable=True))
    _add_column_if_missing("learning_content", sa.Column("key_takeaways", sa.JSON(), nullable=True))
    _add_column_if_missing("learning_content", sa.Column("related_content_ids", sa.JSON(), nullable=True))
    _add_column_if_missing("learning_content", sa.Column("episode_number", sa.Integer(), nullable=True))
    _add_column_if_missing(
        "learning_content",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    if not _has_table("glossary_terms"):
        op.create_table(
            "glossary_terms",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("term", sa.String(length=255), nullable=False),
            sa.Column("definition", sa.Text(), nullable=False),
            sa.Column("part_of_speech", sa.String(length=50), nullable=True),
            sa.Column("example", sa.Text(), nullable=True),
            sa.Column("related_terms", sa.JSON(), nullable=True),
            sa.Column("is_term_of_day", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_glossary_terms_term", "glossary_terms", ["term"])


def downgrade() -> None:
    if _has_table("glossary_terms"):
        op.drop_index("ix_glossary_terms_term", table_name="glossary_terms")
        op.drop_table("glossary_terms")
    op.drop_column("learning_content", "is_featured")
    op.drop_column("learning_content", "episode_number")
    op.drop_column("learning_content", "related_content_ids")
    op.drop_column("learning_content", "key_takeaways")
    op.drop_column("learning_content", "duration")
    op.drop_column("learning_categories", "icon_name")
    op.drop_column("learning_categories", "description")
