import importlib
import os
from unittest.mock import patch

import pytest

from backend import config


@pytest.mark.asyncio
async def test_cors_default_origins(async_client):
    """Default configured origins should receive CORS allow-origin headers."""
    for origin in config.CORS_ALLOWED_ORIGINS:
        response = await async_client.get("/api/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin


@pytest.mark.asyncio
async def test_cors_disallowed_origin(async_client):
    """Disallowed origins should not receive allow-origin headers."""
    response = await async_client.get(
        "/api/health",
        headers={"Origin": "http://malicious.com"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_methods(async_client):
    """Allowed methods should be reported in CORS preflight response."""
    origin = config.CORS_ALLOWED_ORIGINS[0]

    response = await async_client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "GET" in response.headers.get("access-control-allow-methods", "")

    response = await async_client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "PUT",
        },
    )
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "PUT" not in allow_methods


@pytest.mark.asyncio
async def test_cors_disallowed_header(async_client):
    """Disallowed headers should not be whitelisted in preflight response."""
    origin = config.CORS_ALLOWED_ORIGINS[0]
    response = await async_client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Malformed-Header",
        },
    )
    allow_headers = response.headers.get("access-control-allow-headers", "")
    assert "X-Malformed-Header" not in allow_headers


def test_config_parsing():
    """CORS_ALLOWED_ORIGINS should parse and trim comma-separated env values."""
    with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "http://test1.com, http://test2.com "}):
        import backend.config

        importlib.reload(backend.config)
        assert backend.config.CORS_ALLOWED_ORIGINS == ["http://test1.com", "http://test2.com"]

    importlib.reload(backend.config)
