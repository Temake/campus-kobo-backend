from datetime import time

from pydantic import BaseModel, model_validator


class NotificationPreferenceUpdateRequest(BaseModel):
    notification_type: str
    is_enabled: bool
    quiet_hours_enabled: bool = False
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None

    @model_validator(mode="after")
    def validate_quiet_hours(self) -> "NotificationPreferenceUpdateRequest":
        if self.quiet_hours_enabled and (self.quiet_hours_start is None or self.quiet_hours_end is None):
            raise ValueError("quiet_hours_start and quiet_hours_end are required when quiet hours are enabled")
        return self


class NotificationPreferenceResponse(BaseModel):
    id: str
    notification_type: str
    is_enabled: bool
    quiet_hours_enabled: bool
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
