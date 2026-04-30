from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.api.deps import DBSession, get_current_admin
from app.models.user import User
from app.schemas.admin import AdminAnalyticsResponse, AdminLoginRequest, AdminRegisterRequest, AdminTokenResponse, AdminUserResponse
from app.schemas.learning import (
    LearningAssetUploadResponse,
    LearningCategoryCreateRequest,
    LearningCategoryResponse,
    LearningContentCreateRequest,
    LearningContentResponse,
    LearningContentUpdateRequest,
)
from app.integrations.cloudinary import CloudinaryStorageService
from app.services.admin import AdminAuthService
from app.services.learning import LearningService

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


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_admin_analytics(
    current_admin: Annotated[User, Depends(get_current_admin)],
    db: DBSession,
) -> dict:
    return await LearningService(db).admin_analytics()
