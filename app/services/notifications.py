from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationPreference
from app.schemas.notification import NOTIFICATION_FIELDS, NotificationPreferenceResponse, NotificationPreferenceUpdateRequest


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_preferences(self, user_id: str) -> NotificationPreferenceResponse:
        parsed_user_id = self._parse_uuid(user_id)
        preference = await self._get_or_create_preference(parsed_user_id)
        return self._serialize_preference(preference)

    async def upsert_preference(self, user_id: str, payload: NotificationPreferenceUpdateRequest) -> NotificationPreferenceResponse:
        parsed_user_id = self._parse_uuid(user_id)
        preference = await self._get_or_create_preference(parsed_user_id)

        if payload.notification_type is not None:
            setattr(preference, payload.notification_type, payload.is_enabled)
        for field_name in NOTIFICATION_FIELDS:
            value = getattr(payload, field_name)
            if value is not None:
                setattr(preference, field_name, value)
        do_not_disturb = payload.do_not_disturb
        if do_not_disturb is None:
            do_not_disturb = payload.quiet_hours_enabled
        if do_not_disturb is not None:
            preference.do_not_disturb = do_not_disturb
        if payload.quiet_hours_start is not None:
            preference.quiet_hours_start = payload.quiet_hours_start
        if payload.quiet_hours_end is not None:
            preference.quiet_hours_end = payload.quiet_hours_end

        await self.db.commit()
        await self.db.refresh(preference)
        return self._serialize_preference(preference)

    async def _get_or_create_preference(self, user_id: UUID) -> NotificationPreference:
        preference = await self.db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
        if preference is None:
            preference = NotificationPreference(user_id=user_id)
            self.db.add(preference)
            await self.db.flush()
        return preference

    @staticmethod
    def _parse_uuid(value: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identifier") from exc

    @staticmethod
    def _serialize_preference(preference: NotificationPreference) -> NotificationPreferenceResponse:
        return NotificationPreferenceResponse(
            user_id=str(preference.user_id),
            all_notifications=preference.all_notifications,
            budget_alerts=preference.budget_alerts,
            savings_reminders=preference.savings_reminders,
            bill_reminders=preference.bill_reminders,
            new_content=preference.new_content,
            finance_101=preference.finance_101,
            podcast_updates=preference.podcast_updates,
            app_updates=preference.app_updates,
            bof_announcements=preference.bof_announcements,
            do_not_disturb=preference.do_not_disturb,
            quiet_hours_start=preference.quiet_hours_start,
            quiet_hours_end=preference.quiet_hours_end,
        )
