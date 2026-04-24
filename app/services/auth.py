import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.onboarding import OnboardingProgress
from app.models.user import EmailVerificationCode, RefreshToken, User, UserSession, UserStatus
from app.schemas.auth import (
    ActionResponse,
    AuthUserResponse,
    ChangeEmailRequest,
    ChangePasswordRequest,
    CreatePinRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    VerifyEmailRequest,
)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, payload: RegisterRequest, request: Request) -> TokenResponse:
        existing_user = await self.db.scalar(select(User).where(User.email == payload.email))
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
        await self.db.flush()

        self.db.add(OnboardingProgress(user_id=user.id, current_step="intro", completed_step_count=0, is_completed=False))
        verification_code = await self._create_email_verification_code(user.id)

        token_response = await self._issue_tokens(user, request)
        await self.db.commit()
        if settings.app_debug:
            return token_response.model_copy(update={"verification_code": verification_code.code})
        return token_response

    async def login(self, payload: LoginRequest, request: Request) -> TokenResponse:
        user = await self.db.scalar(select(User).where(User.email == payload.email))
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
        token_response = await self._issue_tokens(user, request)
        await self.db.commit()
        return token_response

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = self._decode_token(refresh_token, expected_type="refresh")
        user_id = self._parse_uuid(payload.get("sub"))

        stored_token = await self.db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token))
        if stored_token is None or stored_token.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or revoked")
        if stored_token.expires_at <= self._utcnow():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

        user = await self.db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found")

        stored_token.revoked_at = self._utcnow()
        token_response = await self._issue_tokens(user, request=None)
        await self.db.commit()
        return token_response

    async def verify_email(self, payload: VerifyEmailRequest) -> None:
        user = await self.db.scalar(select(User).where(User.email == payload.email))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        code_entry = await self.db.scalar(
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
        await self.db.commit()

    async def resend_verification(self, email: str) -> None:
        user = await self.db.scalar(select(User).where(User.email == email))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.is_email_verified:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified")

        await self._create_email_verification_code(user.id)
        await self.db.commit()

    async def change_password(self, current_user: User, payload: ChangePasswordRequest) -> ActionResponse:
        if current_user.password_hash is None or not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
        if payload.current_password == payload.new_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

        current_user.password_hash = hash_password(payload.new_password)
        await self.db.commit()
        return ActionResponse(message="Password updated successfully")

    async def change_email(self, current_user: User, payload: ChangeEmailRequest) -> ActionResponse:
        if current_user.password_hash is None or not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
        if current_user.email == payload.new_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New email must be different")

        existing_user = await self.db.scalar(select(User).where(User.email == payload.new_email))
        if existing_user is not None and existing_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That email address is already in use")

        current_user.email = payload.new_email
        current_user.is_email_verified = False
        current_user.status = UserStatus.pending_verification
        verification_code = await self._create_email_verification_code(current_user.id)
        await self.db.commit()

        if settings.app_debug:
            return ActionResponse(
                message="Email updated. Verify the new email address to continue logging in.",
                verification_required=True,
                verification_code=verification_code.code,
            )
        return ActionResponse(
            message="Email updated. Verify the new email address to continue logging in.",
            verification_required=True,
        )

    async def create_pin(self, current_user: User, payload: CreatePinRequest) -> ActionResponse:
        if current_user.has_pin:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PIN already exists for this account")
        if current_user.password_hash is None or not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
        if payload.pin != payload.confirm_pin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN confirmation does not match")
        if not payload.pin.isdigit() or len(payload.pin) != 4:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN must be exactly 4 digits")

        current_user.pin_hash = hash_password(payload.pin)
        current_user.has_pin = True
        await self.db.commit()
        return ActionResponse(message="PIN created successfully")

    async def logout(self, refresh_token: str) -> None:
        stored_token = await self.db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token))
        if stored_token is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refresh token not found")
        if stored_token.revoked_at is None:
            stored_token.revoked_at = self._utcnow()
        await self.db.commit()

    async def _issue_tokens(self, user: User, request: Request | None) -> TokenResponse:
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
        if request is not None:
            self.db.add(
                UserSession(
                    user_id=user.id,
                    device_name=request.headers.get("user-agent"),
                    platform="mobile",
                    ip_address=request.client.host if request.client else None,
                    is_active=True,
                    last_seen_at=self._utcnow(),
                )
            )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=await self._serialize_user(user),
            verification_required=not user.is_email_verified,
        )

    async def _create_email_verification_code(self, user_id: UUID) -> EmailVerificationCode:
        existing_codes = (
            await self.db.scalars(
                select(EmailVerificationCode).where(
                    EmailVerificationCode.user_id == user_id,
                    EmailVerificationCode.consumed_at.is_(None),
                )
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
        await self.db.flush()
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

    @staticmethod
    def _parse_uuid(value: str | None) -> UUID:
        if value is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject is missing")
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject is invalid") from exc

    async def _serialize_user(self, user: User) -> AuthUserResponse:
        onboarding = await self.db.scalar(select(OnboardingProgress).where(OnboardingProgress.user_id == user.id))
        return AuthUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            onboarding_completed=bool(onboarding and onboarding.is_completed),
            has_pin=user.has_pin,
        )
