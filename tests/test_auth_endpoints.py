import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.user import EmailVerificationCode, RefreshToken, VerificationPurpose
from app.services.auth import AuthService


async def _register_user(
    client,
    *,
    email: str,
    password: str = "StrongPass123",
    full_name: str = "Student User",
):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert response.status_code == 201
    return response.json()


async def _verify_user_email(client, *, email: str, code: str):
    response = await client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": email,
            "code": code,
        },
    )
    assert response.status_code == 204


async def _login_user(client, *, email: str, password: str):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    return response


async def _create_verified_user(
    client,
    *,
    email: str = "verified@example.com",
    password: str = "StrongPass123",
    full_name: str = "Verified User",
):
    register_body = await _register_user(client, email=email, password=password, full_name=full_name)
    await _verify_user_email(client, email=email, code=register_body["verification_code"])
    login_response = await _login_user(client, email=email, password=password)
    assert login_response.status_code == 200
    return {
        "register": register_body,
        "login": login_response.json(),
        "email": email,
        "password": password,
    }


async def test_register_returns_tokens_and_verification_code(client):
    body = await _register_user(client, email="student@example.com")

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["verification_required"] is True
    assert len(body["verification_code"]) == 6
    uuid.UUID(body["user"]["id"])
    assert body["user"]["email"] == "student@example.com"


async def test_verify_then_login_refresh_logout_change_password_and_create_pin(client):
    verified_user = await _create_verified_user(
        client,
        email="verifyme@example.com",
        password="StrongPass123",
        full_name="Verify Me",
    )
    login_body = verified_user["login"]
    access_token = login_body["access_token"]
    refresh_token = login_body["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    refreshed_body = refresh_response.json()
    assert refreshed_body["access_token"]
    assert refreshed_body["refresh_token"] != refresh_token

    change_password_response = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "StrongPass123",
            "new_password": "NewStrongPass456",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert change_password_response.status_code == 200

    create_pin_response = await client.post(
        "/api/v1/auth/create-pin",
        json={
            "current_password": "NewStrongPass456",
            "pin": "1234",
            "confirm_pin": "1234",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert create_pin_response.status_code == 200

    relogin_response = await _login_user(
        client,
        email="verifyme@example.com",
        password="NewStrongPass456",
    )
    assert relogin_response.status_code == 200
    assert relogin_response.json()["user"]["has_pin"] is True

    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refreshed_body["refresh_token"]},
    )
    assert logout_response.status_code == 204

    revoked_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refreshed_body["refresh_token"]},
    )
    assert revoked_refresh_response.status_code == 401


async def test_expired_refresh_token_is_deleted_from_database(client, test_session_factory):
    verified_user = await _create_verified_user(
        client,
        email="expired-refresh@example.com",
        password="StrongPass123",
    )
    refresh_token = verified_user["login"]["refresh_token"]

    async with test_session_factory() as session:
        stored_token = await session.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token))
        assert stored_token is not None
        stored_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await session.commit()

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Refresh token has expired"

    async with test_session_factory() as session:
        stored_token = await session.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token))
        assert stored_token is None


async def test_cleanup_expired_refresh_tokens_removes_only_expired_rows(client, test_session_factory):
    first_user = await _create_verified_user(client, email="cleanup-expired@example.com")
    second_user = await _create_verified_user(client, email="cleanup-valid@example.com")
    expired_refresh_token = first_user["login"]["refresh_token"]
    valid_refresh_token = second_user["login"]["refresh_token"]

    async with test_session_factory() as session:
        expired_token = await session.scalar(select(RefreshToken).where(RefreshToken.token == expired_refresh_token))
        assert expired_token is not None
        expired_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await session.commit()

    async with test_session_factory() as session:
        deleted_count = await AuthService(session).cleanup_expired_refresh_tokens()
        assert deleted_count == 1

    async with test_session_factory() as session:
        expired_token = await session.scalar(select(RefreshToken).where(RefreshToken.token == expired_refresh_token))
        valid_token = await session.scalar(select(RefreshToken).where(RefreshToken.token == valid_refresh_token))
        assert expired_token is None
        assert valid_token is not None


async def test_resend_verification_issues_a_new_code_and_invalidates_the_previous_one(client, monkeypatch):
    original_cooldown = settings.email_verification_resend_cooldown_seconds
    monkeypatch.setattr(settings, "email_verification_resend_cooldown_seconds", 0)

    register_body = await _register_user(client, email="resend@example.com", password="StrongPass123")
    first_code = register_body["verification_code"]

    resend_response = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resend@example.com"},
    )
    assert resend_response.status_code == 204

    login_before_verify = await _login_user(client, email="resend@example.com", password="StrongPass123")
    assert login_before_verify.status_code == 403

    wrong_code_response = await client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": "resend@example.com",
            "code": first_code,
        },
    )
    assert wrong_code_response.status_code == 400

    second_resend_response = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resend@example.com"},
    )
    assert second_resend_response.status_code == 204

    monkeypatch.setattr(settings, "email_verification_resend_cooldown_seconds", original_cooldown)


async def test_change_email_flow_requires_reverification_and_switches_login_email(client):
    verified_user = await _create_verified_user(
        client,
        email="change-email@example.com",
        password="StrongPass123",
        full_name="Email Changer",
    )
    access_token = verified_user["login"]["access_token"]

    change_email_response = await client.post(
        "/api/v1/auth/change-email",
        json={
            "current_password": "StrongPass123",
            "new_email": "changed@example.com",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert change_email_response.status_code == 200
    change_email_body = change_email_response.json()
    assert change_email_body["verification_required"] is True
    assert len(change_email_body["verification_code"]) == 6

    old_email_login_response = await _login_user(
        client,
        email="change-email@example.com",
        password="StrongPass123",
    )
    assert old_email_login_response.status_code == 403

    verify_new_email_response = await client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": "changed@example.com",
            "code": change_email_body["verification_code"],
        },
    )
    assert verify_new_email_response.status_code == 204

    old_email_after_verification = await _login_user(
        client,
        email="change-email@example.com",
        password="StrongPass123",
    )
    assert old_email_after_verification.status_code == 401

    new_email_login_response = await _login_user(
        client,
        email="changed@example.com",
        password="StrongPass123",
    )
    assert new_email_login_response.status_code == 200
    assert new_email_login_response.json()["user"]["email"] == "changed@example.com"


async def test_forget_password_issues_code_and_reset_revokes_old_refresh_token(client, test_session_factory, monkeypatch):
    verified_user = await _create_verified_user(
        client,
        email="forgot-password@example.com",
        password="StrongPass123",
        full_name="Forgot Password",
    )
    old_refresh_token = verified_user["login"]["refresh_token"]
    monkeypatch.setattr("app.services.auth.AuthService._generate_verification_code", staticmethod(lambda: "123456"))

    forgot_response = await client.post(
        "/api/v1/auth/forget-password",
        json={"email": "forgot-password@example.com"},
    )
    assert forgot_response.status_code == 204

    async with test_session_factory() as session:
        verification_record = await session.scalar(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.sent_to_email == "forgot-password@example.com",
                EmailVerificationCode.purpose == VerificationPurpose.forgetpassword,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )

    assert verification_record is not None

    reset_response = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "forgot-password@example.com",
            "code": "123456",
            "new_password": "NewStrongPass456",
        },
    )
    assert reset_response.status_code == 200

    revoked_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert revoked_refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_google_auth_creates_a_verified_user_and_onboarding_record(client, monkeypatch):
    async def fake_verify_google_id_token(token: str) -> dict:
        assert token == "google-id-token"
        return {
            "sub": "google-sub-123",
            "email": "googleuser@example.com",
            "email_verified": True,
            "name": "Google User",
            "iss": "https://accounts.google.com",
        }

    monkeypatch.setattr("app.services.auth.verify_google_id_token", fake_verify_google_id_token)

    response = await client.post(
        "/api/v1/auth/google",
        json={"id_token": "google-id-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["verification_required"] is False
    assert body["user"]["email"] == "googleuser@example.com"
    assert body["user"]["onboarding_completed"] is False


@pytest.mark.asyncio
async def test_google_auth_links_existing_verified_email_user(client, monkeypatch):
    await _create_verified_user(
        client,
        email="linked@example.com",
        password="StrongPass123",
        full_name="Existing User",
    )

    async def fake_verify_google_id_token(token: str) -> dict:
        assert token == "google-link-token"
        return {
            "sub": "google-sub-linked",
            "email": "linked@example.com",
            "email_verified": True,
            "name": "Existing User",
            "iss": "https://accounts.google.com",
        }

    monkeypatch.setattr("app.services.auth.verify_google_id_token", fake_verify_google_id_token)

    response = await client.post(
        "/api/v1/auth/google",
        json={"id_token": "google-link-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "linked@example.com"
    assert body["verification_required"] is False

    password_login_response = await _login_user(
        client,
        email="linked@example.com",
        password="StrongPass123",
    )
    assert password_login_response.status_code == 200
