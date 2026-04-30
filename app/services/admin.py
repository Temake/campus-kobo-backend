import hmac
from datetime import timedelta

from fastapi import HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.user import AdminAuditLog, RefreshToken, User, UserRole, UserSession, UserStatus
from app.schemas.admin import AdminLoginRequest, AdminRegisterRequest, AdminTokenResponse, AdminUserResponse
from app.services.auth import AuthService


class AdminAuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, payload: AdminRegisterRequest, request: Request) -> AdminUserResponse:
        if not settings.admin_setup_token or not hmac.compare_digest(payload.setup_token, settings.admin_setup_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin setup token")
        AuthService._ensure_strong_password(payload.password)

        normalized_email = payload.email.strip().lower()
        existing_user = await self.db.scalar(select(User).where(User.email == normalized_email))
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

        admin = User(
            email=normalized_email,
            full_name=payload.full_name,
            password_hash=await run_in_threadpool(hash_password, payload.password),
            status=UserStatus.active,
            is_email_verified=True,
            role=UserRole.admin,
            admin_two_factor_enabled=False,
            admin_ip_allowlist=payload.ip_allowlist,
        )
        self.db.add(admin)
        await self.db.flush()
        self.db.add(
            AdminAuditLog(
                admin_user_id=admin.id,
                action="admin.register",
                resource_type="admin_user",
                resource_id=str(admin.id),
                ip_address=request.client.host if request.client else None,
            )
        )
        await self.db.commit()
        await self.db.refresh(admin)
        return AdminUserResponse(id=str(admin.id), email=admin.email, full_name=admin.full_name, role=admin.role.value)

    async def login(self, payload: AdminLoginRequest, request: Request) -> AdminTokenResponse:
        normalized_email = payload.email.strip().lower()
        user = await self.db.scalar(select(User).where(User.email == normalized_email))
        password_valid = False
        if user is not None and user.password_hash is not None:
            password_valid = await run_in_threadpool(verify_password, payload.password, user.password_hash)

        if user is None or user.role != UserRole.admin or user.password_hash is None or not password_valid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")
        if user.status != UserStatus.active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is not active")
        if not self._ip_allowed(user, request):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin login is not allowed from this IP")

        token_claims = {"email": user.email, "role": user.role.value}
        access_token = create_access_token(str(user.id), extra=token_claims)
        refresh_token = create_refresh_token(str(user.id), extra=token_claims)

        user.last_login_at = AuthService._utcnow()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token=refresh_token,
                expires_at=AuthService._utcnow() + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        self.db.add(
            UserSession(
                user_id=user.id,
                device_name=request.headers.get("user-agent"),
                platform="admin",
                ip_address=request.client.host if request.client else None,
                is_active=True,
                last_seen_at=AuthService._utcnow(),
            )
        )
        self.db.add(
            AdminAuditLog(
                admin_user_id=user.id,
                action="admin.login",
                resource_type="admin_session",
                ip_address=request.client.host if request.client else None,
            )
        )
        await self.db.commit()

        return AdminTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=AdminUserResponse(id=str(user.id), email=user.email, full_name=user.full_name, role=user.role.value),
        )

    @staticmethod
    def _ip_allowed(user: User, request: Request) -> bool:
        if not user.admin_ip_allowlist:
            return True
        if request.client is None:
            return False
        allowed_ips = {item.strip() for item in user.admin_ip_allowlist.split(",") if item.strip()}
        return request.client.host in allowed_ips
