from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.dependencies import get_db
from app.main import app
from app.models import User, UserRole
from app.services.auth_service import AuthService, get_auth_service
from app.services.email_service import EmailService


@pytest.fixture()
def auth_settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        APP_ENV="test",
        APP_URL="http://testserver",
        API_URL="http://testserver",
        AUTH_COOKIE_SECURE=False,
    )


@pytest.fixture()
async def client(db_session: AsyncSession, auth_settings: Settings) -> AsyncIterator[tuple[AsyncClient, AuthService]]:
    auth_service = AuthService(auth_settings, EmailService(auth_settings))

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client, auth_service
    app.dependency_overrides.clear()


@pytest.fixture()
async def verified_client(db_session: AsyncSession) -> AsyncIterator[tuple[AsyncClient, AuthService]]:
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        APP_ENV="test",
        APP_URL="http://testserver",
        API_URL="http://testserver",
        AUTH_REQUIRE_EMAIL_VERIFICATION=True,
    )
    auth_service = AuthService(settings, EmailService(settings))

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client, auth_service
    app.dependency_overrides.clear()


@pytest.mark.asyncio()
async def test_register_creates_session_and_allows_cookie_auth(client: tuple[AsyncClient, AuthService]) -> None:
    http_client, _ = client

    response = await http_client.post(
        "/api/v1/auth/register",
        json={"email": "sportsman@example.com", "password": "supersecure1", "name": "Sportsman"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["auth_method"] == "session"
    assert payload["user"]["email"] == "sportsman@example.com"
    assert payload["user"]["email_verified"] is True
    assert payload["user"]["has_password"] is True
    assert http_client.cookies.get("cc_session")
    assert http_client.cookies.get("cc_csrf")

    session_response = await http_client.get("/api/v1/auth/session")
    assert session_response.status_code == 200
    assert session_response.json()["auth_method"] == "session"

    me_response = await http_client.get("/api/v1/users/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "sportsman@example.com"


@pytest.mark.asyncio()
async def test_logout_requires_csrf_for_session_auth(client: tuple[AsyncClient, AuthService]) -> None:
    http_client, _ = client
    await http_client.post(
        "/api/v1/auth/register",
        json={"email": "csrf@example.com", "password": "supersecure1", "name": "CSRF User"},
    )

    no_csrf = await http_client.post("/api/v1/auth/logout")
    assert no_csrf.status_code == 403

    logout = await http_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": http_client.cookies["cc_csrf"]},
    )
    assert logout.status_code == 204

    session_response = await http_client.get("/api/v1/auth/session")
    assert session_response.status_code == 401


@pytest.mark.asyncio()
async def test_email_verification_and_reset_tokens_work(verified_client: tuple[AsyncClient, AuthService]) -> None:
    http_client, _ = verified_client

    register = await http_client.post(
        "/api/v1/auth/register",
        json={"email": "verify@example.com", "password": "supersecure1", "name": "Verify Me"},
    )
    assert register.status_code == 200
    register_payload = register.json()
    assert register_payload["requires_email_verification"] is True
    assert register_payload["dev_token"]

    login = await http_client.post(
        "/api/v1/auth/login",
        json={"email": "verify@example.com", "password": "supersecure1"},
    )
    assert login.status_code == 403

    verify = await http_client.post(
        "/api/v1/auth/verify-email",
        json={"token": register_payload["dev_token"]},
    )
    assert verify.status_code == 200
    assert verify.json()["user"]["email_verified"] is True

    forgot = await http_client.post("/api/v1/auth/forgot-password", json={"email": "verify@example.com"})
    assert forgot.status_code == 202
    reset_token = forgot.json()["dev_token"]
    assert reset_token

    reset = await http_client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "password": "newsupersecure1"},
    )
    assert reset.status_code == 200
    assert reset.json()["user"]["has_password"] is True

    relogin = await http_client.post(
        "/api/v1/auth/login",
        json={"email": "verify@example.com", "password": "newsupersecure1"},
    )
    assert relogin.status_code == 200


@pytest.mark.asyncio()
async def test_auth0_bearer_links_existing_email_without_overwriting_role(
    client: tuple[AsyncClient, AuthService],
    db_session: AsyncSession,
) -> None:
    http_client, auth_service = client
    existing = User(email="owner@example.com", name="Owner", role=UserRole.admin)
    db_session.add(existing)
    await db_session.commit()

    auth_service._decode_token = lambda token: {
        "sub": "auth0|linked-owner",
        "email": "owner@example.com",
        "name": "Owner Linked",
        "roles": ["sportsman"],
        "email_verified": True,
    }

    response = await http_client.get("/api/v1/users/me", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "admin"
    assert payload["auth0_id"] == "auth0|linked-owner"
    assert payload["email_verified"] is True


@pytest.mark.asyncio()
async def test_debug_header_auth_still_works(client: tuple[AsyncClient, AuthService]) -> None:
    http_client, _ = client

    response = await http_client.get(
        "/api/v1/users/me",
        headers={
            "X-Debug-User": '{"auth0_id":"auth0|debug-user","email":"debug@example.com","name":"Debug User","role":"sportsman"}'
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "debug@example.com"
