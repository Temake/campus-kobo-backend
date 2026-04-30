from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.cloudinary import CloudinaryStorageService
from app.models.user import User, UserSession
from app.schemas.user import (
    BiometricSettingsRequest,
    PrivacySettingsRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserSessionResponse,
)


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def update_profile(self, current_user: User, payload: UserProfileUpdateRequest) -> UserProfileResponse:
        if payload.full_name is not None:
            current_user.full_name = payload.full_name
        if payload.phone_number is not None:
            current_user.phone_number = payload.phone_number
        if payload.avatar_url is not None:
            current_user.avatar_url = payload.avatar_url

        await self.db.commit()
        await self.db.refresh(current_user)
        return self.serialize_profile(current_user)

    async def upload_avatar(self, current_user: User, file) -> UserProfileResponse:
        upload_result = await CloudinaryStorageService().upload_avatar(file)
        current_user.avatar_url = upload_result["url"]
        await self.db.commit()
        await self.db.refresh(current_user)
        return self.serialize_profile(current_user)

    async def update_biometrics(self, current_user: User, payload: BiometricSettingsRequest) -> UserProfileResponse:
        current_user.biometric_enabled = payload.biometric_enabled
        await self.db.commit()
        await self.db.refresh(current_user)
        return self.serialize_profile(current_user)

    async def update_privacy(self, current_user: User, payload: PrivacySettingsRequest) -> UserProfileResponse:
        if payload.hide_balance is not None:
            current_user.hide_balance = payload.hide_balance
        if payload.allow_analytics is not None:
            current_user.allow_analytics = payload.allow_analytics
        await self.db.commit()
        await self.db.refresh(current_user)
        return self.serialize_profile(current_user)

    async def list_sessions(self, current_user: User) -> list[UserSessionResponse]:
        sessions = (
            await self.db.scalars(
                select(UserSession).where(UserSession.user_id == current_user.id).order_by(UserSession.created_at.desc())
            )
        ).all()
        return [self.serialize_session(session) for session in sessions]

    async def revoke_session(self, current_user: User, session_id: str) -> None:
        try:
            parsed_session_id = UUID(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc

        session = await self.db.scalar(
            select(UserSession).where(UserSession.id == parsed_session_id, UserSession.user_id == current_user.id)
        )
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()

    @staticmethod
    def serialize_profile(user: User) -> UserProfileResponse:
        return UserProfileResponse(
            id=str(user.id),
            email=user.email,
            phone_number=user.phone_number,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            has_pin=user.has_pin,
            biometric_enabled=user.biometric_enabled,
            hide_balance=user.hide_balance,
            allow_analytics=user.allow_analytics,
        )

    @staticmethod
    def serialize_session(session: UserSession) -> UserSessionResponse:
        return UserSessionResponse(
            id=str(session.id),
            device_name=session.device_name,
            device_id=session.device_id,
            platform=session.platform,
            ip_address=session.ip_address,
            is_active=session.is_active,
            last_seen_at=session.last_seen_at,
            revoked_at=session.revoked_at,
        )
