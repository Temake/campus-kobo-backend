from datetime import time

from pydantic import BaseModel


class NotificationPreferenceUpdateRequest(BaseModel):
    notification_type: str
    is_enabled: bool
    quiet_hours_enabled: bool = False
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
