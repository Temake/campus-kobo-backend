from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import ContentBookmark, LearningCategory, LearningContent, LearningContentStatus
from app.models.user import AdminAuditLog, User, UserRole
from app.schemas.learning import (
    LearningCategoryCreateRequest,
    LearningCategoryResponse,
    LearningContentCreateRequest,
    LearningContentResponse,
    LearningContentUpdateRequest,
)


class LearningService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_content(self) -> list[dict]:
        content_items = (
            await self.db.scalars(
                select(LearningContent)
                .where(LearningContent.status == LearningContentStatus.published)
                .order_by(LearningContent.created_at.desc())
            )
        ).all()
        return [self._serialize_content(content).model_dump(mode="json") for content in content_items]

    async def bookmark_content(self, user_id: str, content_id: str) -> None:
        parsed_user_id = self._parse_uuid(user_id, "Invalid user identifier")
        parsed_content_id = self._parse_uuid(content_id, "Content not found", not_found=True)
        content = await self.db.scalar(
            select(LearningContent).where(
                LearningContent.id == parsed_content_id,
                LearningContent.status == LearningContentStatus.published,
            )
        )
        if content is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

        existing = await self.db.scalar(
            select(ContentBookmark).where(
                ContentBookmark.user_id == parsed_user_id,
                ContentBookmark.content_id == parsed_content_id,
            )
        )
        if existing is None:
            self.db.add(ContentBookmark(user_id=parsed_user_id, content_id=parsed_content_id))
            await self.db.commit()

    async def create_category(self, admin: User, payload: LearningCategoryCreateRequest, ip_address: str | None) -> LearningCategoryResponse:
        category = LearningCategory(name=payload.name, slug=payload.slug)
        self.db.add(category)
        await self.db.flush()
        self._add_audit_log(admin, "learning_category.create", "learning_category", str(category.id), ip_address)
        await self.db.commit()
        await self.db.refresh(category)
        return LearningCategoryResponse(id=str(category.id), name=category.name, slug=category.slug)

    async def create_content(
        self,
        admin: User,
        payload: LearningContentCreateRequest,
        ip_address: str | None,
    ) -> LearningContentResponse:
        category_id = self._parse_optional_uuid(payload.category_id, "Category not found")
        if category_id is not None:
            await self._ensure_category_exists(category_id)
        content = LearningContent(
            category_id=category_id,
            created_by=admin.id,
            title=payload.title,
            summary=payload.summary,
            body=payload.body,
            cover_image_url=payload.cover_image_url,
            content_type=payload.content_type,
            media_url=payload.media_url,
            media_public_id=payload.media_public_id,
            media_resource_type=payload.media_resource_type,
            status=payload.status,
            view_count=0,
        )
        self.db.add(content)
        await self.db.flush()
        self._add_audit_log(admin, "learning_content.create", "learning_content", str(content.id), ip_address)
        await self.db.commit()
        await self.db.refresh(content)
        return self._serialize_content(content)

    async def update_content(
        self,
        admin: User,
        content_id: str,
        payload: LearningContentUpdateRequest,
        ip_address: str | None,
    ) -> LearningContentResponse:
        parsed_content_id = self._parse_uuid(content_id, "Content not found", not_found=True)
        content = await self.db.scalar(select(LearningContent).where(LearningContent.id == parsed_content_id))
        if content is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

        if payload.category_id is not None:
            category_id = self._parse_optional_uuid(payload.category_id, "Category not found")
            if category_id is not None:
                await self._ensure_category_exists(category_id)
            content.category_id = category_id
        for field_name in (
            "title",
            "summary",
            "body",
            "cover_image_url",
            "content_type",
            "media_url",
            "media_public_id",
            "media_resource_type",
            "status",
        ):
            value = getattr(payload, field_name)
            if value is not None:
                setattr(content, field_name, value)

        self._add_audit_log(admin, "learning_content.update", "learning_content", str(content.id), ip_address)
        await self.db.commit()
        await self.db.refresh(content)
        return self._serialize_content(content)

    async def delete_content(self, admin: User, content_id: str, ip_address: str | None) -> None:
        parsed_content_id = self._parse_uuid(content_id, "Content not found", not_found=True)
        content = await self.db.scalar(select(LearningContent).where(LearningContent.id == parsed_content_id))
        if content is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

        existing_bookmarks = (
            await self.db.scalars(select(ContentBookmark).where(ContentBookmark.content_id == parsed_content_id))
        ).all()
        for bookmark in existing_bookmarks:
            await self.db.delete(bookmark)
        await self.db.delete(content)
        self._add_audit_log(admin, "learning_content.delete", "learning_content", str(parsed_content_id), ip_address)
        await self.db.commit()

    async def admin_analytics(self) -> dict:
        total_users = await self.db.scalar(select(func.count()).select_from(User))
        total_content = await self.db.scalar(select(func.count()).select_from(LearningContent))
        published_content = await self.db.scalar(
            select(func.count()).select_from(LearningContent).where(LearningContent.status == LearningContentStatus.published)
        )
        total_views = await self.db.scalar(select(func.coalesce(func.sum(LearningContent.view_count), 0)))
        total_bookmarks = await self.db.scalar(select(func.count()).select_from(ContentBookmark))
        return {
            "total_users": int(total_users or 0),
            "learning": {
                "total_content": int(total_content or 0),
                "published_content": int(published_content or 0),
                "total_views": int(total_views or 0),
                "total_bookmarks": int(total_bookmarks or 0),
            },
        }

    async def _ensure_category_exists(self, category_id: UUID) -> None:
        category = await self.db.scalar(select(LearningCategory).where(LearningCategory.id == category_id))
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

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
    def _serialize_content(content: LearningContent) -> LearningContentResponse:
        return LearningContentResponse(
            id=str(content.id),
            category_id=str(content.category_id) if content.category_id else None,
            created_by=str(content.created_by) if content.created_by else None,
            title=content.title,
            summary=content.summary,
            body=content.body,
            cover_image_url=content.cover_image_url,
            content_type=content.content_type,
            media_url=content.media_url,
            media_public_id=content.media_public_id,
            media_resource_type=content.media_resource_type,
            status=content.status,
            view_count=content.view_count,
        )

    @staticmethod
    def _parse_optional_uuid(value: str | None, detail: str) -> UUID | None:
        if value is None:
            return None
        return LearningService._parse_uuid(value, detail, not_found=True)

    @staticmethod
    def _parse_uuid(value: str, detail: str, not_found: bool = False) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            code = status.HTTP_404_NOT_FOUND if not_found else status.HTTP_401_UNAUTHORIZED
            raise HTTPException(status_code=code, detail=detail) from exc
