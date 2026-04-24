from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import DBSession, get_current_user
from app.models.user import User
from app.schemas.auth import (
    ActionResponse,
    ChangeEmailRequest,
    ChangePasswordRequest,
    CreatePinRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, db: DBSession) -> TokenResponse:
    return await AuthService(db).register(payload, request)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: DBSession) -> TokenResponse:
    return await AuthService(db).login(payload, request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest, db: DBSession) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(payload: VerifyEmailRequest, db: DBSession) -> None:
    await AuthService(db).verify_email(payload)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(payload: ResendVerificationRequest, db: DBSession) -> None:
    await AuthService(db).resend_verification(payload.email)


@router.post("/change-password", response_model=ActionResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
) -> ActionResponse:
    return await AuthService(db).change_password(current_user, payload)


@router.post("/change-email", response_model=ActionResponse)
async def change_email(
    payload: ChangeEmailRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
) -> ActionResponse:
    return await AuthService(db).change_email(current_user, payload)


@router.post("/create-pin", response_model=ActionResponse)
async def create_pin(
    payload: CreatePinRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
) -> ActionResponse:
    return await AuthService(db).create_pin(current_user, payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshTokenRequest, db: DBSession) -> None:
    await AuthService(db).logout(payload.refresh_token)
