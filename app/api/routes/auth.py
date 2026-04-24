from fastapi import APIRouter, Request, status

from app.api.deps import DBSession
from app.schemas.auth import (
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
def register(payload: RegisterRequest, request: Request, db: DBSession) -> TokenResponse:
    return AuthService(db).register(payload, request)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DBSession) -> TokenResponse:
    return AuthService(db).login(payload, request)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: DBSession) -> TokenResponse:
    return AuthService(db).refresh(payload.refresh_token)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(payload: VerifyEmailRequest, db: DBSession) -> None:
    AuthService(db).verify_email(payload)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification(payload: ResendVerificationRequest, db: DBSession) -> None:
    AuthService(db).resend_verification(payload.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshTokenRequest, db: DBSession) -> None:
    AuthService(db).logout(payload.refresh_token)
