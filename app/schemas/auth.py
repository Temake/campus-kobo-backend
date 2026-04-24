from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "AuthUserResponse"
    verification_required: bool = False
    verification_code: str | None = None


class AuthUserResponse(BaseModel):
    id: str
    email: EmailStr | None = None
    full_name: str | None = None
    onboarding_completed: bool = False
    has_pin: bool = False


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ChangeEmailRequest(BaseModel):
    current_password: str
    new_email: EmailStr


class CreatePinRequest(BaseModel):
    current_password: str
    pin: str = Field(min_length=4, max_length=4)
    confirm_pin: str = Field(min_length=4, max_length=4)


class ActionResponse(BaseModel):
    message: str
    verification_required: bool = False
    verification_code: str | None = None


TokenResponse.model_rebuild()
