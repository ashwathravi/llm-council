
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from backend import auth, config

@pytest.mark.asyncio
async def test_validate_user_access_no_config():
    """Test that access is allowed when no allowlists are configured."""
    with patch("backend.config.ALLOWED_USERS", new=set()), \
         patch("backend.config.ALLOWED_DOMAINS", new=set()):
        auth.validate_user_access("test@example.com")
        # Should not raise

@pytest.mark.asyncio
async def test_validate_user_access_allowed_user():
    """Test that access is allowed for a user in ALLOWED_USERS."""
    with patch("backend.config.ALLOWED_USERS", new={"test@example.com"}), \
         patch("backend.config.ALLOWED_DOMAINS", new=set()):
        auth.validate_user_access("test@example.com")
        auth.validate_user_access("TEST@EXAMPLE.COM") # Case insensitive
        # Should not raise

@pytest.mark.asyncio
async def test_validate_user_access_allowed_domain():
    """Test that access is allowed for a user in ALLOWED_DOMAINS."""
    with patch("backend.config.ALLOWED_USERS", new=set()), \
         patch("backend.config.ALLOWED_DOMAINS", new={"example.com"}):
        auth.validate_user_access("user@example.com")
        auth.validate_user_access("USER@EXAMPLE.COM")
        # Should not raise

@pytest.mark.asyncio
async def test_validate_user_access_denied():
    """Test that access is denied for a user not in allowlists."""
    with patch("backend.config.ALLOWED_USERS", new={"admin@example.com"}), \
         patch("backend.config.ALLOWED_DOMAINS", new={"internal.com"}):

        with pytest.raises(HTTPException) as excinfo:
            auth.validate_user_access("attacker@public.com")
        assert excinfo.value.status_code == 403
        assert "Access denied" in excinfo.value.detail

@pytest.mark.asyncio
async def test_login_integration_allowed(async_client):
    """Test login endpoint allows authorized users."""
    mock_user = {
        "sub": "123",
        "email": "allowed@example.com",
        "name": "Allowed",
        "picture": "pic.jpg"
    }

    with patch("backend.auth.verify_google_token", return_value=mock_user), \
         patch("backend.config.ALLOWED_USERS", new={"allowed@example.com"}):

        response = await async_client.post(
            "/api/auth/login",
            json={"id_token": "valid_token"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_integration_denied(async_client):
    """Test login endpoint denies unauthorized users."""
    mock_user = {
        "sub": "456",
        "email": "denied@example.com",
        "name": "Denied",
        "picture": "pic.jpg"
    }

    with patch("backend.auth.verify_google_token", return_value=mock_user), \
         patch("backend.config.ALLOWED_USERS", new={"allowed@example.com"}):

        response = await async_client.post(
            "/api/auth/login",
            json={"id_token": "valid_token"}
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
