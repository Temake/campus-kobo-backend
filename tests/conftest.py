from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import *  # noqa: F403
from app.models.category import ExpenseCategory
from app.core.config import settings


@pytest_asyncio.fixture
async def test_session_factory(tmp_path) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    database_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield session_factory
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def client(test_session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncClient, None]:
    previous_debug = settings.app_debug
    settings.app_debug = True

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client

    app.dependency_overrides.clear()
    settings.app_debug = previous_debug


@pytest_asyncio.fixture
async def seeded_default_categories(test_session_factory: async_sessionmaker[AsyncSession]) -> list[str]:
    async with test_session_factory() as session:
        categories = [
            ExpenseCategory(name="Food", icon_name="utensils", color_hex="#16A34A", is_default=True, is_active=True),
            ExpenseCategory(name="Transport", icon_name="bus", color_hex="#2563EB", is_default=True, is_active=True),
            ExpenseCategory(name="Data", icon_name="wifi", color_hex="#F59E0B", is_default=True, is_active=True),
        ]
        session.add_all(categories)
        await session.commit()
        return [str(category.id) for category in categories]


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "firstuser@example.com",
            "password": "SuperSecure123",
            "full_name": "First User",
        },
    )
    assert response.status_code == 201
    return response.json()
