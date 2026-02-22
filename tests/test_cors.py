import pytest
import os
import importlib
from unittest.mock import patch
from backend import config

@pytest.mark.asyncio
async def test_cors_default_origins(async_client):
    """Test that default origins are allowed."""
    for origin in config.CORS_ALLOWED_ORIGINS:
        response = await async_client.get(
            "/api/health",
            headers={"Origin": origin}
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin

@pytest.mark.asyncio
async def test_cors_disallowed_origin(async_client):
    """Test that a disallowed origin does not get CORS headers."""
    response = await async_client.get(
        "/api/health",
        headers={"Origin": "http://malicious.com"}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers

@pytest.mark.asyncio
async def test_cors_methods(async_client):
    """Test that allowed methods are permitted via CORS preflight."""
    origin = config.CORS_ALLOWED_ORIGINS[0]

    # Test allowed method
    response = await async_client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code == 200
    assert "GET" in response.headers.get("access-control-allow-methods", "")

    # Test disallowed method
    response = await async_client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "PUT"
        }
    )
    # For disallowed methods, CORSMiddleware should not return the allow-methods header including PUT
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "PUT" not in allow_methods

def test_config_parsing():
    """Test that CORS_ALLOWED_ORIGINS is correctly parsed from environment variables."""
    with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "http://test1.com, http://test2.com "}):
        # Reload config to pick up new env var
        import backend.config
        importlib.reload(backend.config)
        assert "http://test1.com" in backend.config.CORS_ALLOWED_ORIGINS
        assert "http://test2.com" in backend.config.CORS_ALLOWED_ORIGINS
        assert len(backend.config.CORS_ALLOWED_ORIGINS) == 2

    # Reset to default (or whatever is currently in env)
    importlib.reload(backend.config)
