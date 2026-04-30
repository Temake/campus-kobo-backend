from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationPreference
from app.schemas.notification import NotificationPreferenceResponse, NotificationPreferenceUpdateRequest


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_preferences(self, user_id: str) -> list[NotificationPreferenceResponse]:
        parsed_user_id = self._parse_uuid(user_id)
        preferences = (
            await self.db.scalars(
                select(NotificationPreference)
                .where(NotificationPreference.user_id == parsed_user_id)
                .order_by(NotificationPreference.notification_type)
            )
        ).all()
        return [self._serialize_preference(preference) for preference in preferences]

    async def upsert_preference(self, user_id: str, payload: NotificationPreferenceUpdateRequest) -> NotificationPreferenceResponse:
        parsed_user_id = self._parse_uuid(user_id)
        preference = await self.db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.user_id == parsed_user_id,
                NotificationPreference.notification_type == payload.notification_type,
            )
        )
        if preference is None:
            preference = NotificationPreference(user_id=parsed_user_id, notification_type=payload.notification_type)
            self.db.add(preference)

        preference.is_enabled = payload.is_enabled
        preference.quiet_hours_enabled = payload.quiet_hours_enabled
        preference.quiet_hours_start = payload.quiet_hours_start if payload.quiet_hours_enabled else None
        preference.quiet_hours_end = payload.quiet_hours_end if payload.quiet_hours_enabled else None

        await self.db.commit()
        await self.db.refresh(preference)
        return self._serialize_preference(preference)

    @staticmethod
    def _parse_uuid(value: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identifier") from exc

    @staticmethod
    def _serialize_preference(preference: NotificationPreference) -> NotificationPreferenceResponse:
        return NotificationPreferenceResponse(
            id=str(preference.id),
            notification_type=preference.notification_type,
            is_enabled=preference.is_enabled,
            quiet_hours_enabled=preference.quiet_hours_enabled,
            quiet_hours_start=preference.quiet_hours_start,
            quiet_hours_end=preference.quiet_hours_end,
        )
