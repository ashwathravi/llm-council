
import pytest
import pytest_asyncio
import os

# Set a dummy secret key for tests BEFORE importing any backend modules
# that might trigger the RuntimeError.
os.environ.setdefault("JWT_SECRET_KEY", "test_only_dummy_secret_key_for_unit_tests")

from httpx import AsyncClient, ASGITransport
from backend.main import app

# Ensure we're in a test usage
# (Optional: mock authentication if needed, but for now we'll use the real auth 
#  or mock the verify_token dependency in specific tests)

@pytest_asyncio.fixture
async def async_client():
    """
    Async HTTP client for testing FastAPI endpoints.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
