from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user_id
from app.schemas.learning import GlossaryTermResponse, LearningContentResponse
from app.services.learning import LearningService

router = APIRouter()


@router.get("/content")
async def list_content(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
    search: str | None = None,
    category: str | None = None,
    content_type: str | None = None,
    featured: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    del current_user_id
    return await LearningService(db).list_content(
        search=search,
        category=category,
        content_type=content_type,
        featured=featured,
        limit=limit,
        offset=offset,
    )


@router.get("/categories")
async def list_categories(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> list[dict]:
    del current_user_id
    return await LearningService(db).list_categories()


@router.get("/content/{content_id}", response_model=LearningContentResponse)
async def get_content(
    content_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> LearningContentResponse:
    del current_user_id
    return await LearningService(db).get_content(content_id)


@router.get("/glossary")
async def list_glossary_terms(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
    search: str | None = None,
    term_of_day: bool | None = None,
) -> list[dict]:
    del current_user_id
    return await LearningService(db).list_glossary_terms(search=search, term_of_day=term_of_day)


@router.get("/glossary/{term_id}", response_model=GlossaryTermResponse)
async def get_glossary_term(
    term_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> GlossaryTermResponse:
    del current_user_id
    return await LearningService(db).get_glossary_term(term_id)


@router.post("/content/{content_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
async def bookmark_content(
    content_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> None:
    await LearningService(db).bookmark_content(current_user_id, content_id)
