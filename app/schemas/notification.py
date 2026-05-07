from datetime import time

from pydantic import BaseModel, Field, model_validator


NOTIFICATION_FIELDS = {
    "all_notifications",
    "budget_alerts",
    "savings_reminders",
    "bill_reminders",
    "new_content",
    "finance_101",
    "podcast_updates",
    "app_updates",
    "bof_announcements",
}


class NotificationPreferenceUpdateRequest(BaseModel):
    all_notifications: bool | None = None
    budget_alerts: bool | None = None
    savings_reminders: bool | None = None
    bill_reminders: bool | None = None
    new_content: bool | None = None
    finance_101: bool | None = None
    podcast_updates: bool | None = None
    app_updates: bool | None = None
    bof_announcements: bool | None = None
    do_not_disturb: bool | None = None
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    notification_type: str | None = Field(default=None, exclude=True)
    is_enabled: bool | None = Field(default=None, exclude=True)
    quiet_hours_enabled: bool | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def validate_quiet_hours(self) -> "NotificationPreferenceUpdateRequest":
        quiet_hours_enabled = self.do_not_disturb if self.do_not_disturb is not None else self.quiet_hours_enabled
        if quiet_hours_enabled and (self.quiet_hours_start is None or self.quiet_hours_end is None):
            raise ValueError("quiet_hours_start and quiet_hours_end are required when quiet hours are enabled")
        if self.notification_type is not None and self.notification_type not in NOTIFICATION_FIELDS:
            raise ValueError("Invalid notification_type")
        if self.notification_type is not None and self.is_enabled is None:
            raise ValueError("is_enabled is required when notification_type is provided")
        return self


class NotificationPreferenceResponse(BaseModel):
    user_id: str
    all_notifications: bool
    budget_alerts: bool
    savings_reminders: bool
    bill_reminders: bool
    new_content: bool
    finance_101: bool
    podcast_updates: bool
    app_updates: bool
    bof_announcements: bool
    do_not_disturb: bool
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
