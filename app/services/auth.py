from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, payload: RegisterRequest) -> TokenResponse:
        # Boilerplate placeholder:
        # 1. Validate uniqueness of email/phone.
        # 2. Persist user with pending verification state.
        # 3. Send OTP/email verification code.
        user_id = payload.email
        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )

    def login(self, payload: LoginRequest) -> TokenResponse:
        # Boilerplate placeholder:
        # 1. Load user by email.
        # 2. Verify password hash and account state.
        # 3. Update session metadata and last login.
        if not payload.email or not payload.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")
        return TokenResponse(
            access_token=create_access_token(payload.email),
            refresh_token=create_refresh_token(payload.email),
        )

    def refresh(self, refresh_token: str) -> TokenResponse:
        # Validate refresh token, ensure it is not revoked, then issue new tokens.
        return TokenResponse(
            access_token=create_access_token("user-id"),
            refresh_token=create_refresh_token("user-id"),
        )

    def verify_email(self, code: str) -> None:
        # Resolve pending verification with code and activate account.
        if not code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

    def logout(self, refresh_token: str) -> None:
        # Mark refresh token revoked and optionally deactivate current device session.
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing refresh token")
