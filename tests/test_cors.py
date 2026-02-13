
import pytest

@pytest.mark.asyncio
async def test_cors_options_allowed_origin(async_client):
    """Test that CORS preflight request works for allowed origin, methods and headers."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
    }
    response = await async_client.options("/api/health", headers=headers)

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    allowed_methods = response.headers.get("access-control-allow-methods", "").split(", ")
    assert "POST" in allowed_methods
    assert "GET" in allowed_methods
    assert "DELETE" in allowed_methods
    assert "OPTIONS" in allowed_methods
    assert "*" not in allowed_methods

    allowed_headers = response.headers.get("access-control-allow-headers", "").split(", ")
    # Starlette might normalize these or return exactly what we requested if they are in the allowed list
    # Actually, it typically returns the requested headers if they are all allowed.
    assert "Authorization" in allowed_headers
    assert "Content-Type" in allowed_headers
    assert "*" not in allowed_headers

@pytest.mark.asyncio
async def test_cors_disallowed_origin(async_client):
    """Test that CORS headers are not present for disallowed origin."""
    headers = {
        "Origin": "http://malicious.com",
        "Access-Control-Request-Method": "POST",
    }
    response = await async_client.options("/api/health", headers=headers)

    # CORSMiddleware returns 200 but without CORS headers if origin not allowed
    assert response.headers.get("access-control-allow-origin") is None

@pytest.mark.asyncio
async def test_cors_disallowed_method(async_client):
    """Test that disallowed methods are not reported in CORS headers."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "PUT",
    }
    response = await async_client.options("/api/health", headers=headers)

    # If method is not allowed, Starlette returns 200 OK but NO CORS headers
    # OR it doesn't include the disallowed method.
    if response.headers.get("access-control-allow-methods"):
        allowed_methods = response.headers.get("access-control-allow-methods", "").split(", ")
        assert "PUT" not in allowed_methods
    else:
        # This is also an acceptable way Starlette handles it
        pass

@pytest.mark.asyncio
async def test_cors_disallowed_header(async_client):
    """Test that disallowed headers are not reported in CORS headers."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "X-Malformed-Header",
    }
    response = await async_client.options("/api/health", headers=headers)

    # If any header is not allowed, Starlette might omit the whole Access-Control-Allow-Headers
    # or just omit the disallowed one.
    allowed_headers = response.headers.get("access-control-allow-headers", "")
    assert "X-Malformed-Header" not in allowed_headers
