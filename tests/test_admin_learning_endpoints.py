from uuid import UUID

from jose import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.learning import LearningCategory, LearningContent
from app.models.user import User, UserRole, UserStatus


async def _create_admin(test_session_factory, *, email="admin@example.com", password="AdminPass123!"):
    async with test_session_factory() as session:
        admin = User(
            email=email,
            full_name="CampusKobo Admin",
            password_hash=hash_password(password),
            status=UserStatus.active,
            is_email_verified=True,
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
    return {"email": email, "password": password}


async def _create_user(client, *, email="student-admin-test@example.com", password="StrongPass123"):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Student User"},
    )
    assert register_response.status_code == 201
    body = register_response.json()
    verify_response = await client.post("/api/v1/auth/verify-email", json={"email": email, "code": body["verification_code"]})
    assert verify_response.status_code == 204
    login_response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return login_response.json()


async def _admin_login(client, admin):
    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin["email"], "password": admin["password"]},
    )
    assert response.status_code == 200
    return response.json()


async def test_admin_register_requires_setup_token_and_creates_admin(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_setup_token", "setup-secret")

    denied_response = await client.post(
        "/api/v1/admin/auth/register",
        json={
            "email": "new-admin@example.com",
            "password": "AdminPass123!",
            "full_name": "New Admin",
            "setup_token": "wrong-secret",
        },
    )
    assert denied_response.status_code == 403

    register_response = await client.post(
        "/api/v1/admin/auth/register",
        json={
            "email": "new-admin@example.com",
            "password": "AdminPass123!",
            "full_name": "New Admin",
            "setup_token": "setup-secret",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["role"] == "admin"

    login_response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "new-admin@example.com", "password": "AdminPass123!"},
    )
    assert login_response.status_code == 200


async def test_admin_login_access_token_includes_role(client, test_session_factory):
    admin = await _create_admin(test_session_factory)

    login_body = await _admin_login(client, admin)
    payload = jwt.decode(login_body["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["role"] == "admin"


async def test_admin_can_delete_user(client, test_session_factory):
    admin = await _create_admin(test_session_factory)
    admin_login = await _admin_login(client, admin)
    student_login = await _create_user(client, email="delete-me@example.com")
    user_id = student_login["user"]["id"]

    delete_response = await client.delete(
        f"/api/v1/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_login['access_token']}"},
    )
    assert delete_response.status_code == 204

    async with test_session_factory() as session:
        deleted_user = await session.scalar(select(User).where(User.id == UUID(user_id)))
        assert deleted_user is None


async def test_admin_can_manage_learning_content_and_analytics_without_financial_data(client, test_session_factory):
    admin = await _create_admin(test_session_factory)
    admin_login = await _admin_login(client, admin)
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    category_response = await client.post(
        "/api/v1/admin/learning/categories",
        json={"name": "Budgeting", "slug": "budgeting"},
        headers=admin_headers,
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    content_response = await client.post(
        "/api/v1/admin/learning/content",
        json={
            "category_id": category_id,
            "title": "How to stop overspending as a student",
            "summary": "Simple student budgeting habits.",
            "body": "Create a budget and review it weekly.",
            "cover_image_url": "https://res.cloudinary.com/campuskobo/content.jpg",
            "content_type": "video",
            "media_url": "https://res.cloudinary.com/campuskobo/video/upload/lesson.mp4",
            "media_public_id": "campuskobo/learning/lesson",
            "media_resource_type": "video",
            "status": "draft",
        },
        headers=admin_headers,
    )
    assert content_response.status_code == 201
    content_body = content_response.json()
    assert content_body["created_by"] == admin_login["user"]["id"]
    assert content_body["status"] == "draft"
    assert content_body["view_count"] == 0
    assert content_body["content_type"] == "video"
    assert content_body["media_resource_type"] == "video"

    update_response = await client.put(
        f"/api/v1/admin/learning/content/{content_body['id']}",
        json={"status": "published", "title": "Student Budgeting Basics"},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "published"

    student_login = await _create_user(client)
    bookmark_response = await client.post(
        f"/api/v1/learning/content/{content_body['id']}/bookmark",
        headers={"Authorization": f"Bearer {student_login['access_token']}"},
    )
    assert bookmark_response.status_code == 204

    analytics_response = await client.get("/api/v1/admin/analytics", headers=admin_headers)
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["total_users"] == 2
    assert analytics["learning"]["total_content"] == 1
    assert analytics["learning"]["total_bookmarks"] == 1
    assert "expenses" not in analytics
    assert "budgets" not in analytics
    assert "savings" not in analytics

    delete_response = await client.delete(f"/api/v1/admin/learning/content/{content_body['id']}", headers=admin_headers)
    assert delete_response.status_code == 204

    async with test_session_factory() as session:
        deleted_content = await session.scalar(select(LearningContent).where(LearningContent.id == UUID(content_body["id"])))
        category = await session.scalar(select(LearningCategory).where(LearningCategory.id == UUID(category_id)))
        assert deleted_content is None
        assert category is not None


async def test_regular_user_cannot_access_admin_learning_routes(client):
    login_body = await _create_user(client, email="regular-admin-denied@example.com")

    response = await client.post(
        "/api/v1/admin/learning/content",
        json={"title": "Denied", "body": "Nope", "status": "published"},
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
    )
    assert response.status_code == 403
