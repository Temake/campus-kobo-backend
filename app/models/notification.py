import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    all_notifications: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    budget_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    savings_reminders: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    bill_reminders: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    new_content: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    finance_101: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    podcast_updates: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    app_updates: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    bof_announcements: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    do_not_disturb: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    quiet_hours_start: Mapped[time | None] = mapped_column(Time, server_default="22:00:00")
    quiet_hours_end: Mapped[time | None] = mapped_column(Time, server_default="07:00:00")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
