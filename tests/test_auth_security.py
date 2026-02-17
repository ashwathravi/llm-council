import pytest
from unittest.mock import patch
from fastapi import HTTPException
from backend import auth

from backend.auth import verify_google_token

def test_verify_google_token_missing_client_id():
    """
    Test that verify_google_token raises 503 Service Unavailable
    when GOOGLE_CLIENT_ID is not configured.
    """
    # Patch GOOGLE_CLIENT_ID to be None in backend.auth module
    with patch("backend.auth.GOOGLE_CLIENT_ID", None):
        with pytest.raises(HTTPException) as exc_info:
            verify_google_token("dummy_token")

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Google Sign-In is not configured on the server."

def test_verify_google_token_invalid_token():
    """
    Test that verify_google_token raises 401 Unauthorized
    when GOOGLE_CLIENT_ID is configured but token is invalid.
    """
    # Patch GOOGLE_CLIENT_ID to be a dummy value
    with patch("backend.auth.GOOGLE_CLIENT_ID", "dummy_client_id"):
        # We also need to mock id_token.verify_oauth2_token to raise ValueError
        # because we don't want to make real network calls or verify real tokens here
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                verify_google_token("invalid_token")

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid Google token"


@pytest.mark.asyncio
async def test_validate_user_access_no_config():
    """Access is allowed when allowlists are not configured."""
    with patch("backend.config.ALLOWED_USERS", new=set()), patch(
        "backend.config.ALLOWED_DOMAINS", new=set()
    ):
        auth.validate_user_access("test@example.com")


@pytest.mark.asyncio
async def test_validate_user_access_allowed_user():
    """Access is allowed for users explicitly listed in ALLOWED_USERS."""
    with patch("backend.config.ALLOWED_USERS", new={"test@example.com"}), patch(
        "backend.config.ALLOWED_DOMAINS", new=set()
    ):
        auth.validate_user_access("test@example.com")
        auth.validate_user_access("TEST@EXAMPLE.COM")  # Case-insensitive.


@pytest.mark.asyncio
async def test_validate_user_access_allowed_domain():
    """Access is allowed for users whose email domain is in ALLOWED_DOMAINS."""
    with patch("backend.config.ALLOWED_USERS", new=set()), patch(
        "backend.config.ALLOWED_DOMAINS", new={"example.com"}
    ):
        auth.validate_user_access("user@example.com")
        auth.validate_user_access("USER@EXAMPLE.COM")


@pytest.mark.asyncio
async def test_validate_user_access_denied():
    """Access is denied for users not matching configured allowlists."""
    with patch("backend.config.ALLOWED_USERS", new={"admin@example.com"}), patch(
        "backend.config.ALLOWED_DOMAINS", new={"internal.com"}
    ):
        with pytest.raises(HTTPException) as excinfo:
            auth.validate_user_access("attacker@public.com")
        assert excinfo.value.status_code == 403
        assert "Access denied" in excinfo.value.detail


@pytest.mark.asyncio
async def test_login_integration_allowed(async_client):
    """Login endpoint accepts users allowed by allowlist settings."""
    mock_user = {
        "sub": "123",
        "email": "allowed@example.com",
        "name": "Allowed",
        "picture": "pic.jpg",
    }

    with patch("backend.auth.verify_google_token", return_value=mock_user), patch(
        "backend.config.ALLOWED_USERS", new={"allowed@example.com"}
    ):
        response = await async_client.post(
            "/api/auth/login",
            json={"id_token": "valid_token"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_integration_denied(async_client):
    """Login endpoint rejects users outside configured allowlists."""
    mock_user = {
        "sub": "456",
        "email": "denied@example.com",
        "name": "Denied",
        "picture": "pic.jpg",
    }

    with patch("backend.auth.verify_google_token", return_value=mock_user), patch(
        "backend.config.ALLOWED_USERS", new={"allowed@example.com"}
    ):
        response = await async_client.post(
            "/api/auth/login",
            json={"id_token": "valid_token"},
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
