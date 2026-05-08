import enum
from typing import Optional
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class LearningCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon_name: Mapped[Optional[str]] = mapped_column(Text)


class LearningContentStatus(str, enum.Enum):
    draft = "draft"
    published = "published"


class LearningContent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_content"

    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("learning_categories.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(32), default="article", nullable=False)
    media_url: Mapped[str | None] = mapped_column(String(500))
    media_public_id: Mapped[str | None] = mapped_column(String(255))
    media_resource_type: Mapped[str | None] = mapped_column(String(32))
    duration: Mapped[str | None] = mapped_column(String(100))
    key_takeaways: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    related_content_ids: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    episode_number: Mapped[int | None] = mapped_column(Integer)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[LearningContentStatus] = mapped_column(
        Enum(LearningContentStatus), default=LearningContentStatus.draft, nullable=False
    )
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class GlossaryTerm(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "glossary_terms"

    term: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    part_of_speech: Mapped[str | None] = mapped_column(String(50), default="noun")
    example: Mapped[str | None] = mapped_column(Text)
    related_terms: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    is_term_of_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ContentBookmark(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "content_id", name="uq_content_bookmarks_user_content"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learning_content.id"), nullable=False)
