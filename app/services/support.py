import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import FAQCategory, FAQItem, SupportMessage, SupportMessageStatus
from app.models.user import AdminAuditLog, User, UserRole
from app.schemas.support import (
    FAQCategoryCreateRequest,
    FAQCategoryResponse,
    FAQItemCreateRequest,
    FAQItemResponse,
    FAQItemUpdateRequest,
    SupportMessageCreateRequest,
    SupportMessageResponse,
)


class SupportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_faq_categories(self) -> list[dict]:
        categories = (await self.db.scalars(select(FAQCategory).order_by(FAQCategory.name.asc()))).all()
        return [self._serialize_faq_category(category).model_dump(mode="json") for category in categories]

    async def list_faqs(self, search: str | None = None, category: str | None = None) -> list[dict]:
        query = select(FAQItem).where(FAQItem.is_published.is_(True))
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(func.lower(FAQItem.question).like(pattern) | func.lower(FAQItem.answer).like(pattern))
        if category:
            query = query.join(FAQCategory, FAQCategory.id == FAQItem.category_id).where(
                func.lower(FAQCategory.slug) == category.lower()
            )
        items = (await self.db.scalars(query.order_by(FAQItem.created_at.asc()))).all()
        return [self._serialize_faq_item(item).model_dump(mode="json") for item in items]

    async def create_message(self, payload: SupportMessageCreateRequest) -> dict:
        message = SupportMessage(
            id=uuid.uuid4(),
            name=payload.name,
            email=str(payload.email),
            subject=payload.subject,
            message=payload.message,
            status=SupportMessageStatus.open,
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return SupportMessageResponse(
            id=str(message.id),
            name=message.name,
            email=message.email,
            subject=message.subject,
            message=message.message,
            status=message.status.value,
        ).model_dump(mode="json")

    async def contact_info(self) -> dict:
        return {
            "email": "support@campuskobo.com",
            "whatsapp": None,
            "instagram": None,
        }

    async def create_faq_category(
        self,
        admin: User,
        payload: FAQCategoryCreateRequest,
        ip_address: str | None,
    ) -> FAQCategoryResponse:
        category = FAQCategory(name=payload.name, slug=payload.slug)
        self.db.add(category)
        await self.db.flush()
        self._add_audit_log(admin, "faq_category.create", "faq_category", str(category.id), ip_address)
        await self.db.commit()
        await self.db.refresh(category)
        return self._serialize_faq_category(category)

    async def create_faq_item(
        self,
        admin: User,
        payload: FAQItemCreateRequest,
        ip_address: str | None,
    ) -> FAQItemResponse:
        category_id = self._parse_optional_uuid(payload.category_id, "FAQ category not found")
        if category_id is not None:
            await self._ensure_faq_category_exists(category_id)
        item = FAQItem(
            category_id=category_id,
            question=payload.question,
            answer=payload.answer,
            is_published=payload.is_published,
        )
        self.db.add(item)
        await self.db.flush()
        self._add_audit_log(admin, "faq_item.create", "faq_item", str(item.id), ip_address)
        await self.db.commit()
        await self.db.refresh(item)
        return self._serialize_faq_item(item)

    async def update_faq_item(
        self,
        admin: User,
        faq_id: str,
        payload: FAQItemUpdateRequest,
        ip_address: str | None,
    ) -> FAQItemResponse:
        parsed_faq_id = self._parse_uuid(faq_id, "FAQ not found", not_found=True)
        item = await self.db.scalar(select(FAQItem).where(FAQItem.id == parsed_faq_id))
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
        if payload.category_id is not None:
            category_id = self._parse_optional_uuid(payload.category_id, "FAQ category not found")
            if category_id is not None:
                await self._ensure_faq_category_exists(category_id)
            item.category_id = category_id
        for field_name in ("question", "answer", "is_published"):
            value = getattr(payload, field_name)
            if value is not None:
                setattr(item, field_name, value)
        self._add_audit_log(admin, "faq_item.update", "faq_item", str(item.id), ip_address)
        await self.db.commit()
        await self.db.refresh(item)
        return self._serialize_faq_item(item)

    async def delete_faq_item(self, admin: User, faq_id: str, ip_address: str | None) -> None:
        parsed_faq_id = self._parse_uuid(faq_id, "FAQ not found", not_found=True)
        item = await self.db.scalar(select(FAQItem).where(FAQItem.id == parsed_faq_id))
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
        await self.db.delete(item)
        self._add_audit_log(admin, "faq_item.delete", "faq_item", str(parsed_faq_id), ip_address)
        await self.db.commit()

    async def _ensure_faq_category_exists(self, category_id: UUID) -> None:
        category = await self.db.scalar(select(FAQCategory).where(FAQCategory.id == category_id))
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ category not found")

    def _add_audit_log(
        self,
        admin: User,
        action: str,
        resource_type: str,
        resource_id: str | None,
        ip_address: str | None,
    ) -> None:
        if admin.role != UserRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges are required")
        self.db.add(
            AdminAuditLog(
                admin_user_id=admin.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
            )
        )

    @staticmethod
    def _serialize_faq_category(category: FAQCategory) -> FAQCategoryResponse:
        return FAQCategoryResponse(id=str(category.id), name=category.name, slug=category.slug)

    @staticmethod
    def _serialize_faq_item(item: FAQItem) -> FAQItemResponse:
        return FAQItemResponse(
            id=str(item.id),
            category_id=str(item.category_id) if item.category_id else None,
            question=item.question,
            answer=item.answer,
            is_published=item.is_published,
        )

    @staticmethod
    def _parse_optional_uuid(value: str | None, detail: str) -> UUID | None:
        if value is None:
            return None
        return SupportService._parse_uuid(value, detail, not_found=True)

    @staticmethod
    def _parse_uuid(value: str, detail: str, not_found: bool = False) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            code = status.HTTP_404_NOT_FOUND if not_found else status.HTTP_401_UNAUTHORIZED
            raise HTTPException(status_code=code, detail=detail) from exc
