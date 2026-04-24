from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: str
    email: str | None = None
    phone_number: str | None = None
    full_name: str | None = None
    has_pin: bool
    biometric_enabled: bool
