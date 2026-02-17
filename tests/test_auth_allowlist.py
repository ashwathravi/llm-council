import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend import config
from backend.security import _limiter_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_rate_limit():
    """Clear rate limit store before each test."""
    _limiter_store.clear()

@pytest.fixture
def mock_verify_google_token():
    with patch("backend.auth.verify_google_token") as mock:
        yield mock

def test_login_no_allowlist(mock_verify_google_token):
    """Test login succeeds when allowlist is empty (default)."""
    mock_verify_google_token.return_value = {
        "sub": "12345",
        "email": "user@example.com",
        "name": "Test User"
    }

    # Ensure config is empty
    with patch.object(config, "ALLOWED_USERS", set()), \
         patch.object(config, "ALLOWED_DOMAINS", set()):

        response = client.post("/api/auth/login", json={"id_token": "fake_token"})
        assert response.status_code == 200
        assert "access_token" in response.json()

def test_login_allowed_user(mock_verify_google_token):
    """Test login succeeds for explicitly allowed user."""
    mock_verify_google_token.return_value = {
        "sub": "12345",
        "email": "allowed@example.com"
    }

    with patch.object(config, "ALLOWED_USERS", {"allowed@example.com"}), \
         patch.object(config, "ALLOWED_DOMAINS", set()):

        response = client.post("/api/auth/login", json={"id_token": "fake_token"})
        assert response.status_code == 200

def test_login_blocked_user(mock_verify_google_token):
    """Test login fails for user not in allowlist."""
    mock_verify_google_token.return_value = {
        "sub": "67890",
        "email": "blocked@example.com"
    }

    with patch.object(config, "ALLOWED_USERS", {"allowed@example.com"}), \
         patch.object(config, "ALLOWED_DOMAINS", set()):

        response = client.post("/api/auth/login", json={"id_token": "fake_token"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied: User not authorized."

def test_login_allowed_domain(mock_verify_google_token):
    """Test login succeeds for user in allowed domain."""
    mock_verify_google_token.return_value = {
        "sub": "12345",
        "email": "user@company.com"
    }

    with patch.object(config, "ALLOWED_USERS", set()), \
         patch.object(config, "ALLOWED_DOMAINS", {"company.com"}):

        response = client.post("/api/auth/login", json={"id_token": "fake_token"})
        assert response.status_code == 200

def test_login_blocked_domain(mock_verify_google_token):
    """Test login fails for user in blocked domain."""
    mock_verify_google_token.return_value = {
        "sub": "67890",
        "email": "user@other.com"
    }

    with patch.object(config, "ALLOWED_USERS", set()), \
         patch.object(config, "ALLOWED_DOMAINS", {"company.com"}):

        response = client.post("/api/auth/login", json={"id_token": "fake_token"})
        assert response.status_code == 403

def test_login_mixed_config(mock_verify_google_token):
    """Test priority: explicit user allow overrides domain check."""
    mock_verify_google_token.return_value = {
        "sub": "12345",
        "email": "vip@other.com"
    }

    # Domain 'other.com' is NOT allowed, but user 'vip@other.com' IS allowed.
    with patch.object(config, "ALLOWED_USERS", {"vip@other.com"}), \
         patch.object(config, "ALLOWED_DOMAINS", {"company.com"}):

        response = client.post("/api/auth/login", json={"id_token": "fake_token"})
        assert response.status_code == 200
