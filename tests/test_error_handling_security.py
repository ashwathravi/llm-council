
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from backend.main import app
from backend import auth
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_list_models_error_leak():
    """
    Test that list_models does NOT leak exception details.
    """
    sensitive_info = "Secret DB Connection String"

    # Mock authentication
    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"

    # Mock openrouter.fetch_models to raise an exception with sensitive info
    with patch("backend.openrouter.fetch_models", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = ValueError(sensitive_info)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/models")

            assert response.status_code == 500
            # If fixed, this should NOT contain sensitive_info
            # Currently it leaks, so we expect this assertion to fail after fix
            # For TDD, let's assert what we WANT:
            assert sensitive_info not in response.json()["detail"]
            assert response.json()["detail"] == "Internal server error"

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_send_message_stream_error_leak():
    """
    Test that send_message_stream does NOT leak exception details.
    """
    sensitive_info = "Secret API Key leaked"
    conversation_id = "test-conv-id"

    # Mock authentication
    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"

    # Mock storage.get_conversation
    mock_conversation = {
        "id": conversation_id,
        "messages": [],
        "framework": "standard",
        "council_models": ["model1"],
        "chairman_model": "chairman"
    }

    with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conv, \
         patch("backend.storage.add_user_message", new_callable=AsyncMock), \
         patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
         patch("backend.main.generate_conversation_title", new_callable=AsyncMock), \
         patch("backend.storage.update_conversation_title", new_callable=AsyncMock):

        mock_get_conv.return_value = mock_conversation
        mock_retrieval.side_effect = ValueError(sensitive_info) # Trigger error early

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async with client.stream("POST", f"/api/conversations/{conversation_id}/message/stream", json={"content": "hello"}) as response:

                assert response.status_code == 200

                # Read the stream
                lines = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        lines.append(line)

                # Find error message
                error_found = False
                for line in lines:
                    data = json.loads(line[6:])
                    if data.get("type") == "error":
                        error_found = True
                        error_msg = data.get("error")
                        # We want to assert that sensitive info is NOT in the error message
                        assert sensitive_info not in error_msg
                        assert error_msg == "An internal error occurred."

                assert error_found, "No error message found in stream"

    app.dependency_overrides = {}
