import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.onboarding import OnboardingProgress
from app.models.user import EmailVerificationCode, RefreshToken, User, UserSession, UserStatus
from app.schemas.auth import AuthUserResponse, LoginRequest, RegisterRequest, TokenResponse, VerifyEmailRequest


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, payload: RegisterRequest, request: Request) -> TokenResponse:
        existing_user = self.db.scalar(select(User).where(User.email == payload.email))
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            status=UserStatus.pending_verification,
            is_email_verified=False,
        )
        self.db.add(user)
        self.db.flush()

        self.db.add(OnboardingProgress(user_id=user.id, current_step="intro", completed_step_count=0, is_completed=False))
        verification_code = self._create_email_verification_code(user.id)

        token_response = self._issue_tokens(user, request)
        self.db.commit()
        if settings.app_debug:
            return token_response.model_copy(update={"verification_code": verification_code.code})
        return token_response

    def login(self, payload: LoginRequest, request: Request) -> TokenResponse:
        user = self.db.scalar(select(User).where(User.email == payload.email))
        if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if user.status == UserStatus.suspended:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended")
        if user.status == UserStatus.deleted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is no longer available")
        if not user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email address is not verified. Verify your email before logging in.",
            )

        user.status = UserStatus.active
        token_response = self._issue_tokens(user, request)
        self.db.commit()
        return token_response

    def refresh(self, refresh_token: str) -> TokenResponse:
        payload = self._decode_token(refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        stored_token = self.db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token))
        if stored_token is None or stored_token.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or revoked")
        if stored_token.expires_at <= self._utcnow():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

        user = self.db.scalar(select(User).where(User.id == UUID(user_id)))
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found")

        stored_token.revoked_at = self._utcnow()
        token_response = self._issue_tokens(user, request=None)
        self.db.commit()
        return token_response

    def verify_email(self, payload: VerifyEmailRequest) -> None:
        user = self.db.scalar(select(User).where(User.email == payload.email))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        code_entry = self.db.scalar(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.user_id == user.id,
                EmailVerificationCode.code == payload.code,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )
        if code_entry is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")
        if code_entry.expires_at <= self._utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code has expired")

        code_entry.consumed_at = self._utcnow()
        user.is_email_verified = True
        user.status = UserStatus.active
        self.db.commit()

    def resend_verification(self, email: str) -> None:
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.is_email_verified:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified")

        self._create_email_verification_code(user.id)
        self.db.commit()

    def logout(self, refresh_token: str) -> None:
        stored_token = self.db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token))
        if stored_token is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refresh token not found")
        if stored_token.revoked_at is None:
            stored_token.revoked_at = self._utcnow()
        self.db.commit()

    def _issue_tokens(self, user: User, request: Request | None) -> TokenResponse:
        access_token = create_access_token(str(user.id), extra={"email": user.email})
        refresh_token = create_refresh_token(str(user.id), extra={"email": user.email})

        user.last_login_at = self._utcnow()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token=refresh_token,
                expires_at=self._utcnow() + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        self.db.add(
            UserSession(
                user_id=user.id,
                device_name=request.headers.get("user-agent") if request else None,
                platform="mobile" if request else None,
                ip_address=request.client.host if request and request.client else None,
                is_active=True,
                last_seen_at=self._utcnow(),
            )
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=self._serialize_user(user),
            verification_required=not user.is_email_verified,
        )

    def _create_email_verification_code(self, user_id: UUID) -> EmailVerificationCode:
        existing_codes = self.db.scalars(
            select(EmailVerificationCode).where(
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.consumed_at.is_(None),
            )
        ).all()
        now = self._utcnow()
        for existing_code in existing_codes:
            existing_code.consumed_at = now

        code_entry = EmailVerificationCode(
            user_id=user_id,
            code=self._generate_verification_code(),
            expires_at=now + timedelta(minutes=15),
        )
        self.db.add(code_entry)
        return code_entry

    @staticmethod
    def _generate_verification_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    def _decode_token(self, token: str, expected_type: str) -> dict:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        if payload.get("type") != expected_type:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return payload

    def _serialize_user(self, user: User) -> AuthUserResponse:
        onboarding = self.db.scalar(select(OnboardingProgress).where(OnboardingProgress.user_id == user.id))
        return AuthUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            onboarding_completed=bool(onboarding and onboarding.is_completed),
        )
