from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import ContentBookmark, GlossaryTerm, LearningCategory, LearningContent, LearningContentStatus
from app.models.user import AdminAuditLog, User, UserRole
from app.schemas.learning import (
    GlossaryTermCreateRequest,
    GlossaryTermResponse,
    GlossaryTermUpdateRequest,
    LearningCategoryCreateRequest,
    LearningCategoryResponse,
    LearningCategoryUpdateRequest,
    LearningContentCreateRequest,
    LearningContentResponse,
    LearningContentUpdateRequest,
)


class LearningService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_categories(self) -> list[dict]:
        categories = (
            await self.db.scalars(select(LearningCategory).order_by(LearningCategory.name.asc()))
        ).all()
        return [self._serialize_category(category).model_dump(mode="json") for category in categories]

    async def list_content(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        content_type: str | None = None,
        featured: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        query = select(LearningContent).where(LearningContent.status == LearningContentStatus.published)
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(
                func.lower(LearningContent.title).like(pattern)
                | func.lower(LearningContent.summary).like(pattern)
                | func.lower(LearningContent.body).like(pattern)
            )
        if category:
            category_id = self._parse_optional_uuid(category, "Category not found")
            if category_id is not None:
                query = query.where(LearningContent.category_id == category_id)
        if content_type:
            query = query.where(LearningContent.content_type == content_type)
        if featured is not None:
            query = query.where(LearningContent.is_featured == featured)
        content_items = (
            await self.db.scalars(
                query.order_by(LearningContent.is_featured.desc(), LearningContent.created_at.desc())
                .offset(offset)
                .limit(min(limit, 100))
            )
        ).all()
        return [self._serialize_content(content).model_dump(mode="json") for content in content_items]

    async def get_content(self, content_id: str) -> LearningContentResponse:
        parsed_content_id = self._parse_uuid(content_id, "Content not found", not_found=True)
        content = await self.db.scalar(
            select(LearningContent).where(
                LearningContent.id == parsed_content_id,
                LearningContent.status == LearningContentStatus.published,
            )
        )
        if content is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
        content.view_count += 1
        await self.db.commit()
        await self.db.refresh(content)
        return self._serialize_content(content)

    async def list_glossary_terms(self, search: str | None = None, term_of_day: bool | None = None) -> list[dict]:
        query = select(GlossaryTerm)
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(
                func.lower(GlossaryTerm.term).like(pattern) | func.lower(GlossaryTerm.definition).like(pattern)
            )
        if term_of_day is not None:
            query = query.where(GlossaryTerm.is_term_of_day == term_of_day)
        terms = (await self.db.scalars(query.order_by(GlossaryTerm.term.asc()))).all()
        return [self._serialize_glossary_term(term).model_dump(mode="json") for term in terms]

    async def get_glossary_term(self, term_id: str) -> GlossaryTermResponse:
        parsed_term_id = self._parse_uuid(term_id, "Glossary term not found", not_found=True)
        term = await self.db.scalar(select(GlossaryTerm).where(GlossaryTerm.id == parsed_term_id))
        if term is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glossary term not found")
        return self._serialize_glossary_term(term)

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
        category = LearningCategory(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            icon_name=payload.icon_name,
        )
        self.db.add(category)
        await self.db.flush()
        self._add_audit_log(admin, "learning_category.create", "learning_category", str(category.id), ip_address)
        await self.db.commit()
        await self.db.refresh(category)
        return self._serialize_category(category)

    async def update_category(
        self,
        admin: User,
        category_id: str,
        payload: LearningCategoryUpdateRequest,
        ip_address: str | None,
    ) -> LearningCategoryResponse:
        parsed_category_id = self._parse_uuid(category_id, "Category not found", not_found=True)
        category = await self.db.scalar(select(LearningCategory).where(LearningCategory.id == parsed_category_id))
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        for field_name in ("name", "slug", "description", "icon_name"):
            value = getattr(payload, field_name)
            if value is not None:
                setattr(category, field_name, value)
        self._add_audit_log(admin, "learning_category.update", "learning_category", str(category.id), ip_address)
        await self.db.commit()
        await self.db.refresh(category)
        return self._serialize_category(category)

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
            duration=payload.duration,
            key_takeaways=payload.key_takeaways,
            related_content_ids=payload.related_content_ids,
            episode_number=payload.episode_number,
            is_featured=payload.is_featured,
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
            "duration",
            "key_takeaways",
            "related_content_ids",
            "episode_number",
            "is_featured",
            "status",
        ):
            value = getattr(payload, field_name)
            if value is not None:
                setattr(content, field_name, value)

        self._add_audit_log(admin, "learning_content.update", "learning_content", str(content.id), ip_address)
        await self.db.commit()
        await self.db.refresh(content)
        return self._serialize_content(content)

    async def create_glossary_term(
        self,
        admin: User,
        payload: GlossaryTermCreateRequest,
        ip_address: str | None,
    ) -> GlossaryTermResponse:
        term = GlossaryTerm(
            term=payload.term,
            definition=payload.definition,
            part_of_speech=payload.part_of_speech,
            example=payload.example,
            related_terms=payload.related_terms,
            is_term_of_day=payload.is_term_of_day,
        )
        self.db.add(term)
        await self.db.flush()
        self._add_audit_log(admin, "glossary_term.create", "glossary_term", str(term.id), ip_address)
        await self.db.commit()
        await self.db.refresh(term)
        return self._serialize_glossary_term(term)

    async def update_glossary_term(
        self,
        admin: User,
        term_id: str,
        payload: GlossaryTermUpdateRequest,
        ip_address: str | None,
    ) -> GlossaryTermResponse:
        parsed_term_id = self._parse_uuid(term_id, "Glossary term not found", not_found=True)
        term = await self.db.scalar(select(GlossaryTerm).where(GlossaryTerm.id == parsed_term_id))
        if term is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glossary term not found")
        for field_name in ("term", "definition", "part_of_speech", "example", "related_terms", "is_term_of_day"):
            value = getattr(payload, field_name)
            if value is not None:
                setattr(term, field_name, value)
        self._add_audit_log(admin, "glossary_term.update", "glossary_term", str(term.id), ip_address)
        await self.db.commit()
        await self.db.refresh(term)
        return self._serialize_glossary_term(term)

    async def delete_glossary_term(self, admin: User, term_id: str, ip_address: str | None) -> None:
        parsed_term_id = self._parse_uuid(term_id, "Glossary term not found", not_found=True)
        term = await self.db.scalar(select(GlossaryTerm).where(GlossaryTerm.id == parsed_term_id))
        if term is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glossary term not found")
        await self.db.delete(term)
        self._add_audit_log(admin, "glossary_term.delete", "glossary_term", str(parsed_term_id), ip_address)
        await self.db.commit()

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
            content=content.body,
            cover_image_url=content.cover_image_url,
            content_type=content.content_type,
            type=content.content_type,
            media_url=content.media_url,
            media_public_id=content.media_public_id,
            media_resource_type=content.media_resource_type,
            duration=content.duration,
            key_takeaways=content.key_takeaways or [],
            related_content_ids=content.related_content_ids or [],
            episode_number=content.episode_number,
            is_featured=content.is_featured,
            status=content.status,
            view_count=content.view_count,
        )

    @staticmethod
    def _serialize_category(category: LearningCategory) -> LearningCategoryResponse:
        return LearningCategoryResponse(
            id=str(category.id),
            name=category.name,
            slug=category.slug,
            description=category.description,
            icon_name=category.icon_name,
        )

    @staticmethod
    def _serialize_glossary_term(term: GlossaryTerm) -> GlossaryTermResponse:
        return GlossaryTermResponse(
            id=str(term.id),
            term=term.term,
            definition=term.definition,
            part_of_speech=term.part_of_speech,
            example=term.example,
            related_terms=term.related_terms or [],
            is_term_of_day=term.is_term_of_day,
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
