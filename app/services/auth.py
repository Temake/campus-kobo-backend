import hmac
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.integrations.email import EmailService
from app.integrations.google_identity import verify_google_id_token
from app.models.onboarding import OnboardingProgress
from app.models.user import (
    AuthProvider,
    EmailVerificationCode,
    RefreshToken,
    User,
    UserSession,
    UserStatus,
    VerificationPurpose,
)
from app.schemas.auth import (
    ActionResponse,
    AuthUserResponse,
    ChangeEmailRequest,
    ChangePasswordRequest,
    CreatePinRequest,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    VerifyEmailRequest,
)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.email_service = EmailService()

    async def register(self, payload: RegisterRequest, request: Request, background_tasks: BackgroundTasks) -> TokenResponse:
        self._ensure_email_delivery_ready()
        normalized_email = self._normalize_email(payload.email)
        existing_user = await self.db.scalar(select(User).where(User.email == normalized_email))
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

        user = User(
            email=normalized_email,
            full_name=payload.full_name,
            password_hash=await self._hash_secret(payload.password),
            status=UserStatus.pending_verification,
            is_email_verified=False,
            provider=AuthProvider.email,
        )
        self.db.add(user)
        await self.db.flush()

        await self._ensure_onboarding_progress(user.id)
        verification_code = await self._issue_email_verification_code(
            user=user,
            purpose=VerificationPurpose.signup,
            target_email=normalized_email,
        )

        token_response = await self._issue_tokens(user, request)
        await self.db.commit()
        self._queue_verification_email(background_tasks, normalized_email, verification_code, VerificationPurpose.signup)

        if settings.app_debug:
            return token_response.model_copy(update={"verification_code": verification_code})
        return token_response

    async def google_auth(self, payload: GoogleAuthRequest, request: Request) -> TokenResponse:
        google_payload = await verify_google_id_token(payload.id_token)
        google_email = self._normalize_email(google_payload["email"])
        google_subject = google_payload["sub"]
        google_name = google_payload.get("name")

        user = await self.db.scalar(select(User).where(User.provider_subject == google_subject))
        if user is None:
            user = await self.db.scalar(select(User).where(User.email == google_email))

        if user is None:
            user = User(
                email=google_email,
                full_name=google_name,
                provider=AuthProvider.google,
                provider_subject=google_subject,
                status=UserStatus.active,
                is_email_verified=True,
            )
            self.db.add(user)
            await self.db.flush()
            await self._ensure_onboarding_progress(user.id)
        else:
            if user.status == UserStatus.suspended:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended")
            if user.status == UserStatus.deleted:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is no longer available")
            if user.provider_subject and user.provider_subject != google_subject:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Google account linkage mismatch")

            user.provider_subject = google_subject
            if not user.full_name and google_name:
                user.full_name = google_name
            user.is_email_verified = True
            user.status = UserStatus.active
            await self._ensure_onboarding_progress(user.id)

        token_response = await self._issue_tokens(user, request)
        await self.db.commit()
        return token_response

    async def login(self, payload: LoginRequest, request: Request) -> TokenResponse:
        normalized_email = self._normalize_email(payload.email)
        user = await self.db.scalar(select(User).where(User.email == normalized_email))
        password_is_valid = False
        if user is not None and user.password_hash is not None:
            password_is_valid = await self._verify_secret(payload.password, user.password_hash)
        if user is None or user.password_hash is None or not password_is_valid:
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
        if self._to_utc_aware(stored_token.expires_at) <= self._utcnow():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

        user = await self.db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found")

        stored_token.revoked_at = self._utcnow()
        token_response = await self._issue_tokens(user, request=None)
        await self.db.commit()
        return token_response

    async def verify_email(self, payload: VerifyEmailRequest) -> None:
        normalized_email = self._normalize_email(payload.email)
        verification_record = await self.db.scalar(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.sent_to_email == normalized_email,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )
        if verification_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active verification request found")
        if self._to_utc_aware(verification_record.expires_at) <= self._utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code has expired")
        if verification_record.attempt_count >= settings.email_verification_max_attempts:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many verification attempts")

        verification_record.attempt_count += 1
        provided_hash = self._hash_verification_code(
            email=normalized_email,
            purpose=verification_record.purpose,
            code=payload.code,
        )
        if not hmac.compare_digest(provided_hash, verification_record.code_hash):
            await self.db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

        user = await self.db.scalar(select(User).where(User.id == verification_record.user_id))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        verification_record.consumed_at = self._utcnow()
        user.email = normalized_email
        user.is_email_verified = True
        user.status = UserStatus.active
        await self.db.commit()

    async def resend_verification(self, email: str, background_tasks: BackgroundTasks) -> None:
        self._ensure_email_delivery_ready()
        normalized_email = self._normalize_email(email)
        verification_record = await self.db.scalar(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.sent_to_email == normalized_email,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )
        if verification_record is not None:
            user = await self.db.scalar(select(User).where(User.id == verification_record.user_id))
            purpose = verification_record.purpose
        else:
            user = await self.db.scalar(select(User).where(User.email == normalized_email))
            purpose = VerificationPurpose.signup

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.is_email_verified and purpose == VerificationPurpose.signup:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified")

        verification_code = await self._issue_email_verification_code(user=user, purpose=purpose, target_email=normalized_email)
        await self.db.commit()
        self._queue_verification_email(background_tasks, normalized_email, verification_code, purpose)

    async def change_password(self, current_user: User, payload: ChangePasswordRequest) -> ActionResponse:
        if current_user.password_hash is None or not await self._verify_secret(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
        if payload.current_password == payload.new_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

        current_user.password_hash = await self._hash_secret(payload.new_password)
        await self.db.commit()
        return ActionResponse(message="Password updated successfully")

    async def change_email(
        self,
        current_user: User,
        payload: ChangeEmailRequest,
        background_tasks: BackgroundTasks,
    ) -> ActionResponse:
        self._ensure_email_delivery_ready()
        if current_user.password_hash is None or not await self._verify_secret(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

        normalized_email = self._normalize_email(payload.new_email)
        if current_user.email == normalized_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New email must be different")

        existing_user = await self.db.scalar(select(User).where(User.email == normalized_email))
        if existing_user is not None and existing_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That email address is already in use")

        current_user.provider_subject = None
        current_user.is_email_verified = False
        current_user.status = UserStatus.pending_verification

        verification_code = await self._issue_email_verification_code(
            user=current_user,
            purpose=VerificationPurpose.change_email,
            target_email=normalized_email,
        )
        await self.db.commit()
        self._queue_verification_email(background_tasks, normalized_email, verification_code, VerificationPurpose.change_email)

        if settings.app_debug:
            return ActionResponse(
                message="Email updated. Verify the new email address to continue using this account.",
                verification_required=True,
                verification_code=verification_code,
            )
        return ActionResponse(
            message="Email updated. Verify the new email address to continue using this account.",
            verification_required=True,
        )

    async def create_pin(self, current_user: User, payload: CreatePinRequest) -> ActionResponse:
        if current_user.has_pin:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PIN already exists for this account")
        if current_user.password_hash is None or not await self._verify_secret(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
        if payload.pin != payload.confirm_pin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN confirmation does not match")
        if not payload.pin.isdigit() or len(payload.pin) != 4:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN must be exactly 4 digits")

        current_user.pin_hash = await self._hash_secret(payload.pin)
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

    async def _issue_email_verification_code(
        self,
        user: User,
        purpose: VerificationPurpose,
        target_email: str,
    ) -> str:
        active_records = (
            await self.db.scalars(
                select(EmailVerificationCode).where(
                    EmailVerificationCode.user_id == user.id,
                    EmailVerificationCode.consumed_at.is_(None),
                )
            )
        ).all()
        active_email_records = (
            await self.db.scalars(
                select(EmailVerificationCode).where(
                    EmailVerificationCode.sent_to_email == target_email,
                    EmailVerificationCode.consumed_at.is_(None),
                )
            )
        ).all()
        now = self._utcnow()
        for record in active_email_records:
            if record.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A verification process is already pending for this email address",
                )
        for record in active_records:
            if (now - self._to_utc_aware(record.last_sent_at)).total_seconds() < settings.email_verification_resend_cooldown_seconds:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Please wait before requesting another verification code",
                )
            record.consumed_at = now

        code = self._generate_verification_code()
        record = EmailVerificationCode(
            user_id=user.id,
            purpose=purpose,
            sent_to_email=target_email,
            code_hash=self._hash_verification_code(target_email, purpose, code),
            expires_at=now + timedelta(minutes=settings.email_verification_code_expire_minutes),
            last_sent_at=now,
            attempt_count=0,
        )
        self.db.add(record)
        await self.db.flush()
        return code

    async def _ensure_onboarding_progress(self, user_id: UUID) -> OnboardingProgress:
        onboarding = await self.db.scalar(select(OnboardingProgress).where(OnboardingProgress.user_id == user_id))
        if onboarding is None:
            onboarding = OnboardingProgress(user_id=user_id, current_step="intro", completed_step_count=0, is_completed=False)
            self.db.add(onboarding)
            await self.db.flush()
        return onboarding

    def _queue_verification_email(
        self,
        background_tasks: BackgroundTasks,
        recipient_email: str,
        code: str,
        purpose: VerificationPurpose,
    ) -> None:
        if not self.email_service.is_configured():
            return
        background_tasks.add_task(
            self.email_service.send_verification_code,
            recipient_email,
            code,
            purpose.value,
            settings.email_verification_code_expire_minutes,
        )

    def _ensure_email_delivery_ready(self) -> None:
        if not settings.app_debug and not self.email_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email delivery is not configured",
            )

    @staticmethod
    def _generate_verification_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _to_utc_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

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

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    async def _hash_secret(value: str) -> str:
        return await run_in_threadpool(hash_password, value)

    @staticmethod
    async def _verify_secret(plain_value: str, hashed_value: str) -> bool:
        return await run_in_threadpool(verify_password, plain_value, hashed_value)

    async def _serialize_user(self, user: User) -> AuthUserResponse:
        onboarding = await self.db.scalar(select(OnboardingProgress).where(OnboardingProgress.user_id == user.id))
        return AuthUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            onboarding_completed=bool(onboarding and onboarding.is_completed),
            has_pin=user.has_pin,
        )

    def _hash_verification_code(self, email: str, purpose: VerificationPurpose, code: str) -> str:
        message = f"{self._normalize_email(email)}:{purpose.value}:{code}".encode("utf-8")
        secret = settings.jwt_secret_key.encode("utf-8")
        return hmac.new(secret, message, sha256).hexdigest()
