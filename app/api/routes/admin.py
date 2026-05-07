from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.api.deps import DBSession, get_current_admin
from app.models.user import User
from app.schemas.admin import AdminAnalyticsResponse, AdminLoginRequest, AdminRegisterRequest, AdminTokenResponse, AdminUserResponse
from app.schemas.learning import (
    GlossaryTermCreateRequest,
    GlossaryTermResponse,
    GlossaryTermUpdateRequest,
    LearningAssetUploadResponse,
    LearningCategoryCreateRequest,
    LearningCategoryResponse,
    LearningCategoryUpdateRequest,
    LearningContentCreateRequest,
    LearningContentResponse,
    LearningContentUpdateRequest,
)
from app.schemas.support import FAQCategoryCreateRequest, FAQCategoryResponse, FAQItemCreateRequest, FAQItemResponse, FAQItemUpdateRequest
from app.integrations.cloudinary import CloudinaryStorageService
from app.services.admin import AdminAuthService
from app.services.learning import LearningService
from app.services.support import SupportService

router = APIRouter()


@router.post("/auth/login", response_model=AdminTokenResponse)
async def admin_login(payload: AdminLoginRequest, request: Request, db: DBSession) -> AdminTokenResponse:
    return await AdminAuthService(db).login(payload, request)


@router.post("/auth/register", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def admin_register(payload: AdminRegisterRequest, request: Request, db: DBSession) -> AdminUserResponse:
    return await AdminAuthService(db).register(payload, request)


@router.post("/learning/categories", response_model=LearningCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_learning_category(
    payload: LearningCategoryCreateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> LearningCategoryResponse:
    return await LearningService(db).create_category(
        current_admin,
        payload,
        request.client.host if request.client else None,
    )


@router.put("/learning/categories/{category_id}", response_model=LearningCategoryResponse)
async def update_learning_category(
    category_id: str,
    payload: LearningCategoryUpdateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> LearningCategoryResponse:
    return await LearningService(db).update_category(
        current_admin,
        category_id,
        payload,
        request.client.host if request.client else None,
    )


@router.post("/learning/content", response_model=LearningContentResponse, status_code=status.HTTP_201_CREATED)
async def create_learning_content(
    payload: LearningContentCreateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> LearningContentResponse:
    return await LearningService(db).create_content(
        current_admin,
        payload,
        request.client.host if request.client else None,
    )


@router.post("/learning/glossary", response_model=GlossaryTermResponse, status_code=status.HTTP_201_CREATED)
async def create_glossary_term(
    payload: GlossaryTermCreateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> GlossaryTermResponse:
    return await LearningService(db).create_glossary_term(
        current_admin,
        payload,
        request.client.host if request.client else None,
    )


@router.put("/learning/glossary/{term_id}", response_model=GlossaryTermResponse)
async def update_glossary_term(
    term_id: str,
    payload: GlossaryTermUpdateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> GlossaryTermResponse:
    return await LearningService(db).update_glossary_term(
        current_admin,
        term_id,
        payload,
        request.client.host if request.client else None,
    )


@router.delete("/learning/glossary/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_glossary_term(
    term_id: str,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> None:
    await LearningService(db).delete_glossary_term(
        current_admin,
        term_id,
        request.client.host if request.client else None,
    )


@router.post("/learning/assets", response_model=LearningAssetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_learning_asset(
    current_admin: Annotated[User, Depends(get_current_admin)],
    file: UploadFile = File(...),
) -> LearningAssetUploadResponse:
    del current_admin
    result = await CloudinaryStorageService().upload_learning_asset(file)
    return LearningAssetUploadResponse(**result)


@router.put("/learning/content/{content_id}", response_model=LearningContentResponse)
async def update_learning_content(
    content_id: str,
    payload: LearningContentUpdateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> LearningContentResponse:
    return await LearningService(db).update_content(
        current_admin,
        content_id,
        payload,
        request.client.host if request.client else None,
    )


@router.delete("/learning/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_content(
    content_id: str,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> None:
    await LearningService(db).delete_content(
        current_admin,
        content_id,
        request.client.host if request.client else None,
    )


@router.post("/support/faq-categories", response_model=FAQCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_faq_category(
    payload: FAQCategoryCreateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> FAQCategoryResponse:
    return await SupportService(db).create_faq_category(
        current_admin,
        payload,
        request.client.host if request.client else None,
    )


@router.post("/support/faqs", response_model=FAQItemResponse, status_code=status.HTTP_201_CREATED)
async def create_faq_item(
    payload: FAQItemCreateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> FAQItemResponse:
    return await SupportService(db).create_faq_item(
        current_admin,
        payload,
        request.client.host if request.client else None,
    )


@router.put("/support/faqs/{faq_id}", response_model=FAQItemResponse)
async def update_faq_item(
    faq_id: str,
    payload: FAQItemUpdateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> FAQItemResponse:
    return await SupportService(db).update_faq_item(
        current_admin,
        faq_id,
        payload,
        request.client.host if request.client else None,
    )


@router.delete("/support/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq_item(
    faq_id: str,
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> None:
    await SupportService(db).delete_faq_item(
        current_admin,
        faq_id,
        request.client.host if request.client else None,
    )


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_admin_analytics(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> dict:
    return await LearningService(db).admin_analytics()
