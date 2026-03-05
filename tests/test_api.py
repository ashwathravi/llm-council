
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.main import app
from backend import auth

@pytest.mark.asyncio
async def test_status_authenticated(async_client):
    """Test that the status endpoint returns 200 and expected structure when authenticated."""
    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        response = await async_client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "storage_mode" in data
        assert "origin" in data
        assert "database_url_configured" in data
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_status_unauthenticated(async_client):
    """Test that the status endpoint returns 401 when unauthenticated."""
    response = await async_client.get("/api/status")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_health_check_public(async_client):
    """Test that the health endpoint is public."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_list_models_mocked(async_client):
    """Test listing models uses the mocked OpenRouter auth."""
    mock_models = [
        {"id": "test/model-1", "name": "Test Model 1"},
        {"id": "test/model-2", "name": "Test Model 2"},
    ]
    
    # Updated to patch backend.openrouter.fetch_models
    from unittest.mock import AsyncMock
    with patch("backend.openrouter.fetch_models", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_models
        
        app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
        try:
            response = await async_client.get("/api/models")
            assert response.status_code == 200
            assert response.json() == mock_models
        finally:
            app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_conversations_empty(async_client):
    """Test listing conversations returns empty list initially."""
    # Define async mock function
    async def mock_return_empty(*args, **kwargs):
        return []

    with patch("backend.storage.list_conversations", side_effect=mock_return_empty):
        app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
        try:
            response = await async_client.get("/api/conversations")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_create_conversation_invalid_framework(async_client):
    """Test that creating a conversation with an invalid framework returns 422."""

    # Mock authentication
    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        response = await async_client.post(
            "/api/conversations",
            json={
                "framework": "invalid_framework",
                "council_models": ["model1"]
            }
        )

        assert response.status_code == 422
        # FastAPI/Pydantic returns detail about the validation error
        data = response.json()
        assert "detail" in data
        assert any("framework" in error["loc"] for error in data["detail"])
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_retry_failed_stage1_models_success(async_client):
    conversation = {
        "id": "conv-1",
        "framework": "standard",
        "council_models": ["model-good", "model-bad"],
        "messages": [
            {"role": "user", "content": "How do I optimize this query?"},
            {
                "role": "assistant",
                "stage1": [{"model": "model-good", "response": "Use indexes and EXPLAIN."}],
                "stage2": [],
                "stage3": {"model": "chair", "response": "Use index tuning."},
                "metadata": {
                    "effective_council_models": ["model-good", "model-bad"],
                    "stage1_errors": [{"model": "model-bad", "error": "timeout"}],
                    "responded_council_models": ["model-good"],
                },
            },
        ],
    }

    async def mock_stage1_stream(*args, **kwargs):
        yield {"model": "model-bad", "response": "Add covering indexes and check cardinality."}

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.update_message", new_callable=AsyncMock) as mock_update_message, \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.stage1_collect_responses", side_effect=mock_stage1_stream):
            mock_get_conversation.return_value = conversation
            mock_retrieval.return_value = ("", [])

            response = await async_client.post(
                "/api/conversations/conv-1/messages/1/retry-stage1",
                json={}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["retried_models"] == ["model-bad"]
            assert data["recovered_models"] == ["model-bad"]
            assert data["failed_models"] == []
            assert len(data["stage1"]) == 2
            assert {item["model"] for item in data["stage1"]} == {"model-good", "model-bad"}

            assert mock_update_message.await_count == 1
            update_call = mock_update_message.await_args[0]
            assert update_call[0] == "conv-1"
            assert update_call[1] == "test_user"
            assert update_call[2] == 1
            assert isinstance(update_call[3], dict)
            assert len(update_call[3]["stage1"]) == 2
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_retry_failed_stage1_models_without_failures_returns_400(async_client):
    conversation = {
        "id": "conv-2",
        "framework": "standard",
        "council_models": ["model-good"],
        "messages": [
            {"role": "user", "content": "Explain joins"},
            {
                "role": "assistant",
                "stage1": [{"model": "model-good", "response": "Use inner joins for matching rows."}],
                "stage2": [],
                "stage3": {"model": "chair", "response": "Use joins carefully."},
                "metadata": {
                    "effective_council_models": ["model-good"],
                    "stage1_errors": [],
                    "responded_council_models": ["model-good"],
                },
            },
        ],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation:
            mock_get_conversation.return_value = conversation

            response = await async_client.post(
                "/api/conversations/conv-2/messages/1/retry-stage1",
                json={}
            )

            assert response.status_code == 400
            assert response.json()["detail"] == "No failed models found to retry"
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_retry_endpoint_can_refresh_synthesis_without_retrying_models(async_client):
    conversation = {
        "id": "conv-3",
        "framework": "standard",
        "council_models": ["model-a", "model-b"],
        "chairman_model": "chair-model",
        "messages": [
            {"role": "user", "content": "How should we scale this service?"},
            {
                "role": "assistant",
                "stage1": [
                    {"model": "model-a", "response": "Use horizontal scaling and caching."},
                    {"model": "model-b", "response": "Add autoscaling and load balancing."},
                ],
                "stage2": [{"model": "old-ranker", "ranking": "old"}],
                "stage3": {"model": "chair-model", "response": "Old synthesis"},
                "metadata": {
                    "effective_council_models": ["model-a", "model-b"],
                    "stage1_errors": [],
                    "responded_council_models": ["model-a", "model-b"],
                    "label_to_model": {"Response A": "model-a", "Response B": "model-b"},
                    "aggregate_rankings": [{"model": "model-a", "average_rank": 1.0, "rankings_count": 1}],
                },
            },
        ],
    }

    async def mock_stage3_stream(*args, **kwargs):
        yield "Refreshed "
        yield "synthesis"

    def fail_if_called(*args, **kwargs):
        raise AssertionError("stage1_collect_responses should not be called for refresh-only requests")

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.update_message", new_callable=AsyncMock) as mock_update_message, \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.stage1_collect_responses", side_effect=fail_if_called), \
             patch("backend.main.stage2_collect_rankings", new_callable=AsyncMock) as mock_stage2, \
             patch("backend.main.calculate_aggregate_rankings", return_value=[{"model": "model-b", "average_rank": 1.0, "rankings_count": 1}]), \
             patch("backend.main.stage3_synthesize_final", side_effect=mock_stage3_stream):
            mock_get_conversation.return_value = conversation
            mock_retrieval.return_value = ("retrieval context", [])
            mock_stage2.return_value = (
                [{"model": "ranker", "ranking": "FINAL RANKING:\n1. Response B\n2. Response A", "parsed_ranking": ["Response B", "Response A"]}],
                {"Response A": "model-a", "Response B": "model-b"},
            )

            response = await async_client.post(
                "/api/conversations/conv-3/messages/1/retry-stage1",
                json={"refresh_synthesis": True}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["retried_models"] == []
            assert data["recovered_models"] == []
            assert data["failed_models"] == []
            assert data["synthesis_refreshed"] is True
            assert data["synthesis_refresh_error"] is None
            assert data["stage3"]["response"] == "Refreshed synthesis"
            assert len(data["stage2"]) == 1

            assert mock_update_message.await_count == 1
            update_call = mock_update_message.await_args[0]
            assert update_call[0] == "conv-3"
            assert update_call[1] == "test_user"
            assert update_call[2] == 1
            assert update_call[3]["stage3"]["response"] == "Refreshed synthesis"
            assert "synthesis_refreshed_at_ms" in update_call[3]["metadata"]
    finally:
        app.dependency_overrides = {}
