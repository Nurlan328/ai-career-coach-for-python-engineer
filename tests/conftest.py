"""Pytest fixtures. Env is configured BEFORE importing the app (offline + eager)."""
import os
import uuid

# Must be set before app / settings import.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./_pytest.db"
os.environ["ANTHROPIC_API_KEY"] = ""  # offline: no token spend in tests
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["CACHE_ENABLED"] = "true"  # uses in-memory fallback (no Redis needed)

import httpx
import pytest_asyncio


@pytest_asyncio.fixture
async def client():
    """Fresh schema per test + an httpx client bound to the ASGI app."""
    import app.models  # noqa: F401  register models
    from app.core.database import Base, engine
    from app.main import app

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register_and_login(client: httpx.AsyncClient, email: str | None = None) -> dict:
    email = email or f"user_{uuid.uuid4().hex[:10]}@test.com"
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "full_name": "Test"},
    )
    r = await client.post(
        "/api/auth/login", data={"username": email, "password": "secret123"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest_asyncio.fixture
async def headers(client):
    return await register_and_login(client)
