from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import DBSession, get_current_user
from app.models.user import User
from app.schemas.user import (
    BiometricSettingsRequest,
    PrivacySettingsRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserSessionResponse,
)
from app.services.users import UserService

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserProfileResponse:
    return UserService.serialize_profile(current_user)


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UserProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
) -> UserProfileResponse:
    return await UserService(db).update_profile(current_user, payload)


@router.post("/avatar", response_model=UserProfileResponse)
async def upload_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
    file: UploadFile = File(...),
) -> UserProfileResponse:
    return await UserService(db).upload_avatar(current_user, file)


@router.put("/security/biometrics", response_model=UserProfileResponse)
async def update_biometrics(
    payload: BiometricSettingsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
) -> UserProfileResponse:
    return await UserService(db).update_biometrics(current_user, payload)


@router.put("/privacy", response_model=UserProfileResponse)
async def update_privacy(
    payload: PrivacySettingsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
) -> UserProfileResponse:
    return await UserService(db).update_privacy(current_user, payload)


@router.get("/sessions", response_model=list[UserSessionResponse])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
) -> list[UserSessionResponse]:
    return await UserService(db).list_sessions(current_user)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
) -> None:
    await UserService(db).revoke_session(current_user, session_id)
