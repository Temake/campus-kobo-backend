import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class LearningCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class LearningContent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_content"

    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("learning_categories.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ContentBookmark(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "content_id", name="uq_content_bookmarks_user_content"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learning_content.id"), nullable=False)
