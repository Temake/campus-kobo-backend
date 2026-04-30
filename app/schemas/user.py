from datetime import datetime

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: str
    email: str | None = None
    phone_number: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None
    has_pin: bool
    biometric_enabled: bool
    hide_balance: bool = False
    allow_analytics: bool = True


class UserProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = Field(default=None, max_length=500)


class BiometricSettingsRequest(BaseModel):
    biometric_enabled: bool


class PrivacySettingsRequest(BaseModel):
    hide_balance: bool | None = None
    allow_analytics: bool | None = None


class UserSessionResponse(BaseModel):
    id: str
    device_name: str | None = None
    device_id: str | None = None
    platform: str | None = None
    ip_address: str | None = None
    is_active: bool
    last_seen_at: datetime | None = None
    revoked_at: datetime | None = None
