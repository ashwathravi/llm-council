
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from backend import openrouter

@pytest.mark.asyncio
async def test_client_instantiation_shared():
    """Verify that httpx.AsyncClient is instantiated ONLY ONCE across multiple query_model calls."""

    # Reset global client to ensure test starts fresh
    openrouter._client = None

    # We patch httpx.AsyncClient to track instantiation
    with patch("httpx.AsyncClient", autospec=True) as mock_client_cls:
        # Configure the mock to return an async context manager (if used as such) or just an instance
        mock_instance = mock_client_cls.return_value

        # Mock methods
        mock_instance.post = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response", "reasoning_details": None}}]
        }
        mock_instance.post.return_value = mock_response

        # Call query_model twice
        messages = [{"role": "user", "content": "hello"}]
        await openrouter.query_model("model-a", messages)
        await openrouter.query_model("model-b", messages)

        # Assert that AsyncClient was instantiated EXACTLY ONCE
        assert mock_client_cls.call_count == 1

    # Cleanup
    openrouter._client = None
