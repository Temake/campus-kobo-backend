async def _create_verified_user(client, *, email="profile@example.com", password="StrongPass123"):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Profile User"},
    )
    assert register_response.status_code == 201
    register_body = register_response.json()

    verify_response = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": register_body["verification_code"]},
    )
    assert verify_response.status_code == 204

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"user-agent": "CampusKobo iOS"},
    )
    assert login_response.status_code == 200
    return login_response.json()


async def test_user_can_update_profile_preferences_security_and_sessions(client):
    login_body = await _create_verified_user(client)
    token = login_body["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    profile_response = await client.put(
        "/api/v1/users/profile",
        json={
            "full_name": "Adeyemo Taiwo M",
            "phone_number": "+2347012345678",
            "avatar_url": "https://res.cloudinary.com/campuskobo/avatar.jpg",
        },
        headers=auth_headers,
    )
    assert profile_response.status_code == 200
    profile_body = profile_response.json()
    assert profile_body["full_name"] == "Adeyemo Taiwo M"
    assert profile_body["phone_number"] == "+2347012345678"
    assert profile_body["avatar_url"].endswith("avatar.jpg")

    preferences_response = await client.put(
        "/api/v1/notifications/preferences",
        json={
            "notification_type": "budget_alerts",
            "is_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00:00",
            "quiet_hours_end": "07:00:00",
        },
        headers=auth_headers,
    )
    assert preferences_response.status_code == 200
    assert preferences_response.json()["quiet_hours_start"] == "22:00:00"

    list_preferences_response = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert list_preferences_response.status_code == 200
    assert list_preferences_response.json()["budget_alerts"] is True

    pin_response = await client.post(
        "/api/v1/auth/create-pin",
        json={"current_password": "StrongPass123", "pin": "1234", "confirm_pin": "1234"},
        headers=auth_headers,
    )
    assert pin_response.status_code == 200

    biometrics_response = await client.put(
        "/api/v1/users/security/biometrics",
        json={"biometric_enabled": True},
        headers=auth_headers,
    )
    assert biometrics_response.status_code == 200
    assert biometrics_response.json()["biometric_enabled"] is True

    sessions_response = await client.get("/api/v1/users/sessions", headers=auth_headers)
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert len(sessions) == 1
    assert sessions[0]["device_name"] == "CampusKobo iOS"
    assert sessions[0]["is_active"] is True

    revoke_response = await client.delete(f"/api/v1/users/sessions/{sessions[0]['id']}", headers=auth_headers)
    assert revoke_response.status_code == 204

    sessions_after_revoke = await client.get("/api/v1/users/sessions", headers=auth_headers)
    assert sessions_after_revoke.status_code == 200
    assert sessions_after_revoke.json()[0]["is_active"] is False


async def test_notification_quiet_hours_require_start_and_end(client):
    login_body = await _create_verified_user(client, email="quiet@example.com")
    token = login_body["access_token"]

    response = await client.put(
        "/api/v1/notifications/preferences",
        json={"notification_type": "app_updates", "is_enabled": True, "quiet_hours_enabled": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_user_avatar_upload_stores_cloudinary_url(client, monkeypatch):
    login_body = await _create_verified_user(client, email="avatar@example.com")
    token = login_body["access_token"]

    async def fake_upload_avatar(self, file):
        assert file.filename == "avatar.png"
        return {
            "url": "https://res.cloudinary.com/campuskobo/image/upload/avatar.png",
            "public_id": "campuskobo/avatars/avatar",
            "resource_type": "image",
        }

    monkeypatch.setattr("app.services.users.CloudinaryStorageService.upload_avatar", fake_upload_avatar)

    response = await client.post(
        "/api/v1/users/avatar",
        files={"file": ("avatar.png", b"fake-image", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["avatar_url"].endswith("avatar.png")
