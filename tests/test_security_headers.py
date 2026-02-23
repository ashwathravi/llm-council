import pytest

@pytest.mark.asyncio
async def test_security_headers_present(async_client):
    """Test that all security headers are present in the response."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-XSS-Protection"] == "1; mode=block"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    # CSP Check
    assert "Content-Security-Policy" in headers
    csp = headers["Content-Security-Policy"]

    # Check key directives
    assert "default-src 'self'" in csp
    assert "script-src" in csp
    assert "'unsafe-inline'" in csp  # Required for React/Vite dev mode + some prod scenarios
    assert "https://accounts.google.com" in csp
    assert "frame-src 'self' https://accounts.google.com" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
