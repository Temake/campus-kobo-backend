from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession
from app.schemas.auth import LoginRequest, RefreshTokenRequest, RegisterRequest, TokenResponse, VerifyEmailRequest
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DBSession) -> TokenResponse:
    return AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DBSession) -> TokenResponse:
    return AuthService(db).login(payload)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: DBSession) -> TokenResponse:
    return AuthService(db).refresh(payload.refresh_token)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(payload: VerifyEmailRequest, db: DBSession) -> None:
    AuthService(db).verify_email(payload.code)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshTokenRequest, db: DBSession) -> None:
    AuthService(db).logout(payload.refresh_token)
