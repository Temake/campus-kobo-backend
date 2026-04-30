from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    setup_token: str
    ip_allowlist: str | None = None


class AdminUserResponse(BaseModel):
    id: str
    email: EmailStr | None = None
    full_name: str | None = None
    role: str


class AdminTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: AdminUserResponse


class AdminAnalyticsResponse(BaseModel):
    total_users: int
    learning: dict[str, int]
