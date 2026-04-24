
import pytest
import json
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
async def test_create_conversation_invalid_session_type(async_client):
    """Test that creating a conversation with an invalid session type returns 422."""

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        response = await async_client.post(
            "/api/conversations",
            json={
                "framework": "standard",
                "session_type": "bad_session_type",
                "council_models": ["model1"]
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("session_type" in error["loc"] for error in data["detail"])
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_visual_review_uses_image_payload_and_filters_non_vision(async_client):
    conversation = {
        "id": "conv-visual",
        "framework": "standard",
        "session_type": "visual_review",
        "council_models": ["openai/gpt-5.2", "acme/text-only-model"],
        "chairman_model": "chair-model",
        "primary_artifacts": [
            {
                "id": "img-1",
                "kind": "image",
                "label": "mockup.png",
                "source": "upload",
                "status": "ready",
                "filename": "mockup.png",
                "mime_type": "image/png",
                "size_bytes": 128,
                "storage_path": "conv-visual/img-1.png",
                "preview_url": "/artifact-files/conv-visual/img-1.png",
            }
        ],
        "messages": [],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock) as mock_add_user_message, \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock) as mock_update_title, \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock) as mock_add_assistant_message, \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.run_full_council", new_callable=AsyncMock) as mock_run_council, \
             patch("backend.image_artifacts.load_image_as_data_url", return_value="data:image/png;base64,abc"):
            mock_get_conversation.return_value = conversation
            mock_generate_title.return_value = "Visual Review"
            mock_retrieval.return_value = ("", [])
            mock_run_council.return_value = (
                [{"model": "openai/gpt-5.2", "response": "The hierarchy is clear."}],
                [],
                {"model": "chair-model", "response": "Looks solid overall."},
                {},
            )

            response = await async_client.post(
                "/api/conversations/conv-visual/message",
                json={"content": "Review this layout"}
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["metadata"]["effective_council_models"] == ["openai/gpt-5.2"]
            assert payload["metadata"]["excluded_non_vision_models"] == ["acme/text-only-model"]

            run_args = mock_run_council.await_args
            history = run_args.args[0]
            assert run_args.kwargs["council_models"] == ["openai/gpt-5.2"]
            assert history[-1]["role"] == "user"
            assert isinstance(history[-1]["content"], list)
            assert history[-1]["content"][0]["type"] == "text"
            assert history[-1]["content"][0]["text"] == "Review this layout"
            assert history[-1]["content"][1]["type"] == "image_url"

            mock_add_user_message.assert_awaited_once()
            mock_update_title.assert_awaited_once()
            mock_add_assistant_message.assert_awaited_once()
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_code_review_includes_uploaded_code_context(async_client):
    conversation = {
        "id": "conv-code",
        "framework": "standard",
        "session_type": "code_review",
        "specialist_template_id": "code_security_review",
        "council_models": ["openai/gpt-5.2"],
        "chairman_model": "chair-model",
        "primary_artifacts": [
            {
                "id": "code-1",
                "kind": "code",
                "label": "app.py",
                "source": "upload",
                "status": "ready",
                "filename": "app.py",
                "mime_type": "text/x-python",
                "size_bytes": 42,
                "storage_path": "conv-code/code-1-app.py",
                "line_count": 2,
                "language": "Python",
                "summary": "Python • 2 lines",
            }
        ],
        "messages": [],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock), \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock), \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock), \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.run_full_council", new_callable=AsyncMock) as mock_run_council, \
             patch("backend.code_artifacts.load_code_file", return_value="def foo():\n    return 1\n"):
            mock_get_conversation.return_value = conversation
            mock_generate_title.return_value = "Code Review"
            mock_retrieval.return_value = ("retrieval context", [])
            mock_run_council.return_value = (
                [{"model": "openai/gpt-5.2", "response": "There is no issue here."}],
                [],
                {"model": "chair-model", "response": "Structured review."},
                {},
            )

            response = await async_client.post(
                "/api/conversations/conv-code/message",
                json={"content": "Review this file"}
            )

            assert response.status_code == 200
            run_args = mock_run_council.await_args
            effective_context = run_args.kwargs["retrieval_context"]
            assert "retrieval context" in effective_context
            assert "SPECIALIST TEMPLATE:" in effective_context
            assert "Security Review Council" in effective_context
            assert "CODE REVIEW ARTIFACT" in effective_context
            assert "File: app.py" in effective_context
            assert "1 | def foo():" in effective_context
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_create_conversation_persists_specialist_template(async_client):
    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.create_conversation", new_callable=AsyncMock) as mock_create_conversation:
            mock_create_conversation.return_value = {
                "id": "conv-template",
                "created_at": "2026-04-19T00:00:00",
                "title": "New Conversation",
                "framework": "standard",
                "session_type": "code_review",
                "specialist_template_id": "code_security_review",
                "execution_mode": "safe_patch_checks",
                "session_config": {},
                "council_models": ["openai/gpt-5.2"],
                "chairman_model": None,
                "primary_artifacts": [],
                "messages": [],
            }

            response = await async_client.post(
                "/api/conversations",
                json={
                    "framework": "standard",
                    "session_type": "code_review",
                    "specialist_template_id": "code_security_review",
                    "execution_mode": "safe_patch_checks",
                    "council_models": ["openai/gpt-5.2"],
                }
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["session_type"] == "code_review"
            assert payload["specialist_template_id"] == "code_security_review"
            assert payload["execution_mode"] == "safe_patch_checks"
            assert mock_create_conversation.await_args.kwargs["specialist_template_id"] == "code_security_review"
            assert mock_create_conversation.await_args.kwargs["execution_mode"] == "safe_patch_checks"
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_create_conversation_persists_design_studio_session_config(async_client):
    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.create_conversation", new_callable=AsyncMock) as mock_create_conversation:
            mock_create_conversation.return_value = {
                "id": "conv-design",
                "created_at": "2026-04-22T00:00:00",
                "title": "New Conversation",
                "framework": "standard",
                "session_type": "design_studio",
                "specialist_template_id": "design_cross_platform_studio",
                "execution_mode": "disabled",
                "session_config": {
                    "design_target": "mixed",
                    "studio_goal": "handoff",
                    "approved_direction_id": None,
                },
                "council_models": ["openai/gpt-5.2"],
                "chairman_model": None,
                "primary_artifacts": [],
                "messages": [],
            }

            response = await async_client.post(
                "/api/conversations",
                json={
                    "framework": "standard",
                    "session_type": "design_studio",
                    "specialist_template_id": "design_cross_platform_studio",
                    "session_config": {
                        "design_target": "mixed",
                        "studio_goal": "handoff",
                    },
                    "council_models": ["openai/gpt-5.2"],
                }
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["session_type"] == "design_studio"
            assert payload["session_config"] == {
                "design_target": "mixed",
                "studio_goal": "handoff",
                "approved_direction_id": None,
            }
            assert mock_create_conversation.await_args.kwargs["session_config"] == {
                "design_target": "mixed",
                "studio_goal": "handoff",
                "approved_direction_id": None,
            }
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_approve_design_direction_persists_refinement_config(async_client):
    conversation = {
        "id": "conv-approve",
        "created_at": "2026-01-01T00:00:00",
        "title": "Approve Direction",
        "framework": "standard",
        "session_type": "design_studio",
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "compare",
            "approved_direction_id": None,
        },
        "council_models": ["model-a"],
        "chairman_model": "chair-model",
        "primary_artifacts": [],
        "messages": [
            {
                "role": "assistant",
                "metadata": {
                    "design_studio": {
                        "candidate_directions": [
                            {"id": "direction-b", "label": "Direction B"},
                        ],
                    },
                },
            },
        ],
    }
    updated = {
        **conversation,
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "iterate",
            "approved_direction_id": "direction-b",
        },
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.update_conversation_context", new_callable=AsyncMock) as mock_update_context:
            mock_get_conversation.return_value = conversation
            mock_update_context.return_value = updated

            response = await async_client.post(
                "/api/conversations/conv-approve/design-studio/approved-direction",
                json={"direction_id": " direction-b "},
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["session_config"] == updated["session_config"]
            mock_update_context.assert_awaited_once_with(
                "conv-approve",
                "test_user",
                session_config={
                    "design_target": "web_app",
                    "studio_goal": "iterate",
                    "approved_direction_id": "direction-b",
                },
            )
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_approve_design_direction_rejects_non_design_sessions(async_client):
    conversation = {
        "id": "conv-general",
        "framework": "standard",
        "session_type": "general",
        "session_config": {},
        "council_models": ["model-a"],
        "chairman_model": "chair-model",
        "primary_artifacts": [],
        "messages": [],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.update_conversation_context", new_callable=AsyncMock) as mock_update_context:
            mock_get_conversation.return_value = conversation

            response = await async_client.post(
                "/api/conversations/conv-general/design-studio/approved-direction",
                json={"direction_id": "direction-a"},
            )

            assert response.status_code == 400
            mock_update_context.assert_not_awaited()
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_approve_design_direction_rejects_unknown_candidate(async_client):
    conversation = {
        "id": "conv-approve",
        "framework": "standard",
        "session_type": "design_studio",
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "compare",
            "approved_direction_id": None,
        },
        "council_models": ["model-a"],
        "chairman_model": "chair-model",
        "primary_artifacts": [],
        "messages": [
            {
                "role": "assistant",
                "metadata": {
                    "design_studio": {
                        "candidate_directions": [
                            {"id": "direction-a", "label": "Direction A"},
                        ],
                    },
                },
            },
        ],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.update_conversation_context", new_callable=AsyncMock) as mock_update_context:
            mock_get_conversation.return_value = conversation

            response = await async_client.post(
                "/api/conversations/conv-approve/design-studio/approved-direction",
                json={"direction_id": "direction-b"},
            )

            assert response.status_code == 400
            mock_update_context.assert_not_awaited()
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_design_studio_includes_session_context(async_client):
    conversation = {
        "id": "conv-design-studio",
        "framework": "standard",
        "session_type": "design_studio",
        "specialist_template_id": "design_cross_platform_studio",
        "session_config": {
            "design_target": "mixed",
            "studio_goal": "compare",
            "approved_direction_id": "direction-beta",
        },
        "council_models": ["openai/gpt-5.2"],
        "chairman_model": "chair-model",
        "primary_artifacts": [],
        "messages": [],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock), \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock), \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock), \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.run_full_council", new_callable=AsyncMock) as mock_run_council:
            mock_get_conversation.return_value = conversation
            mock_generate_title.return_value = "Design Studio"
            mock_retrieval.return_value = ("retrieval context", [])
            mock_run_council.return_value = (
                [{"model": "openai/gpt-5.2", "response": "Direction A is stronger."}],
                [],
                {"model": "chair-model", "response": "Recommend Direction A."},
                {},
            )

            response = await async_client.post(
                "/api/conversations/conv-design-studio/message",
                json={"content": "Generate cross-platform options"}
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["metadata"]["session_config"] == conversation["session_config"]

            effective_context = mock_run_council.await_args.kwargs["retrieval_context"]
            assert "SPECIALIST TEMPLATE:" in effective_context
            assert "Cross-Platform Design Studio" in effective_context
            assert "DESIGN STUDIO CONFIG:" in effective_context
            assert "Target: Mixed Web + iOS" in effective_context
            assert "Goal: Compare" in effective_context
            assert "Approved Direction: direction-beta" in effective_context
            assert "retrieval context" in effective_context
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_design_studio_allows_text_only_models_without_images(async_client):
    conversation = {
        "id": "conv-design-text",
        "framework": "standard",
        "session_type": "design_studio",
        "specialist_template_id": "design_web_app_studio",
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "generate",
            "approved_direction_id": None,
        },
        "council_models": ["acme/text-only-model", "openai/gpt-5.2"],
        "chairman_model": "chair-model",
        "primary_artifacts": [],
        "messages": [],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock), \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock), \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock), \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.run_full_council", new_callable=AsyncMock) as mock_run_council:
            mock_get_conversation.return_value = conversation
            mock_generate_title.return_value = "Design Studio"
            mock_retrieval.return_value = ("", [])
            mock_run_council.return_value = (
                [{"model": "acme/text-only-model", "response": "Direction A."}],
                [],
                {"model": "chair-model", "response": "Recommend Direction A."},
                {},
            )

            response = await async_client.post(
                "/api/conversations/conv-design-text/message",
                json={"content": "Generate web app directions"}
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["metadata"]["effective_council_models"] == [
                "acme/text-only-model",
                "openai/gpt-5.2",
            ]
            assert payload["metadata"]["excluded_non_vision_models"] == []
            assert payload["metadata"]["model_selection"]["vision_required"] is False
            assert payload["metadata"]["model_selection"]["degraded"] is False

            run_args = mock_run_council.await_args
            assert run_args.kwargs["council_models"] == ["acme/text-only-model", "openai/gpt-5.2"]
            assert run_args.args[0][-1]["content"] == "Generate web app directions"
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_design_studio_with_images_prefers_vision_models(async_client):
    conversation = {
        "id": "conv-design-image",
        "framework": "standard",
        "session_type": "design_studio",
        "specialist_template_id": "design_web_app_studio",
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "generate",
            "approved_direction_id": None,
        },
        "council_models": ["acme/text-only-model", "openai/gpt-5.2"],
        "chairman_model": "chair-model",
        "primary_artifacts": [
            {
                "id": "img-1",
                "kind": "image",
                "label": "reference.png",
                "source": "upload",
                "status": "ready",
                "filename": "reference.png",
                "mime_type": "image/png",
                "size_bytes": 128,
                "storage_path": "conv-design-image/img-1.png",
                "preview_url": "/artifact-files/conv-design-image/img-1.png",
            }
        ],
        "messages": [],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock), \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock), \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock), \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.run_full_council", new_callable=AsyncMock) as mock_run_council, \
             patch("backend.image_artifacts.load_image_as_data_url", return_value="data:image/png;base64,abc"):
            mock_get_conversation.return_value = conversation
            mock_generate_title.return_value = "Design Studio"
            mock_retrieval.return_value = ("", [])
            mock_run_council.return_value = (
                [{"model": "openai/gpt-5.2", "response": "Use this visual direction."}],
                [],
                {"model": "chair-model", "response": "Recommend the visual direction."},
                {},
            )

            response = await async_client.post(
                "/api/conversations/conv-design-image/message",
                json={"content": "Generate directions from this reference"}
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["metadata"]["effective_council_models"] == ["openai/gpt-5.2"]
            assert payload["metadata"]["excluded_non_vision_models"] == ["acme/text-only-model"]
            assert payload["metadata"]["model_selection"]["vision_required"] is True
            assert payload["metadata"]["model_selection"]["excluded_models"] == [
                {"model": "acme/text-only-model", "reason": "missing_vision_capability"}
            ]

            history = mock_run_council.await_args.args[0]
            assert isinstance(history[-1]["content"], list)
            assert history[-1]["content"][0]["type"] == "text"
            assert history[-1]["content"][1]["type"] == "image_url"
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_design_studio_with_images_degrades_when_no_vision_models(async_client):
    conversation = {
        "id": "conv-design-degraded",
        "framework": "standard",
        "session_type": "design_studio",
        "specialist_template_id": "design_web_app_studio",
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "generate",
            "approved_direction_id": None,
        },
        "council_models": ["acme/text-only-model"],
        "chairman_model": "chair-model",
        "primary_artifacts": [
            {
                "id": "img-1",
                "kind": "image",
                "label": "reference.png",
                "source": "upload",
                "status": "ready",
                "filename": "reference.png",
                "mime_type": "image/png",
                "size_bytes": 128,
                "storage_path": "conv-design-degraded/img-1.png",
                "preview_url": "/artifact-files/conv-design-degraded/img-1.png",
            }
        ],
        "messages": [],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock), \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock), \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock), \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.run_full_council", new_callable=AsyncMock) as mock_run_council, \
             patch("backend.image_artifacts.load_image_as_data_url") as mock_load_image:
            mock_get_conversation.return_value = conversation
            mock_generate_title.return_value = "Design Studio"
            mock_retrieval.return_value = ("", [])
            mock_run_council.return_value = (
                [{"model": "acme/text-only-model", "response": "Use a calmer layout."}],
                [],
                {"model": "chair-model", "response": "Recommend a text-grounded direction."},
                {},
            )

            response = await async_client.post(
                "/api/conversations/conv-design-degraded/message",
                json={"content": "Generate directions from this reference"}
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["metadata"]["effective_council_models"] == ["acme/text-only-model"]
            assert payload["metadata"]["excluded_non_vision_models"] == []
            assert payload["metadata"]["model_selection"]["vision_required"] is True
            assert payload["metadata"]["model_selection"]["degraded"] is True
            assert payload["metadata"]["model_selection"]["warnings"] == [
                "Image artifacts are attached, but no vision-capable council models were selected. Design Studio will run without image payloads."
            ]

            history = mock_run_council.await_args.args[0]
            assert history[-1]["content"] == "Generate directions from this reference"
            mock_load_image.assert_not_called()
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_stream_design_studio_emits_structured_stage_metadata(async_client):
    conversation = {
        "id": "conv-design-stream",
        "framework": "standard",
        "session_type": "design_studio",
        "specialist_template_id": "design_web_app_studio",
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "compare",
            "approved_direction_id": None,
        },
        "council_models": ["model-a", "model-b"],
        "chairman_model": "chair-model",
        "primary_artifacts": [],
        "messages": [],
    }
    stage2_results = [
        {
            "model": "judge",
            "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
            "parsed_ranking": ["Response B", "Response A"],
            "confidence": 91,
            "rubric_scores": {
                "Response A": {"hierarchy": 3},
                "Response B": {"hierarchy": 5},
            },
        }
    ]
    aggregate_rankings = [
        {"model": "model-b", "average_rank": 1.0, "rankings_count": 1},
        {"model": "model-a", "average_rank": 2.0, "rankings_count": 1},
    ]
    aggregate_rubrics = [
        {
            "model": "model-b",
            "overall_score": 4.8,
            "criteria": [{"key": "hierarchy", "label": "Hierarchy", "average_score": 5.0}],
        }
    ]

    async def mock_stage1_stream(*args, **kwargs):
        yield {"model": "model-a", "response": "Direction A\nDense operations layout."}
        yield {"model": "model-b", "response": "Direction B\nCalmer editorial layout."}

    async def mock_stage3_stream(*args, **kwargs):
        yield "Ship Direction B."

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock), \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock), \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock) as mock_add_assistant_message, \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.stage1_collect_responses", side_effect=mock_stage1_stream), \
             patch("backend.main.stage2_collect_rankings", new_callable=AsyncMock) as mock_stage2, \
             patch("backend.main.calculate_aggregate_rankings", return_value=aggregate_rankings), \
             patch("backend.main.calculate_aggregate_rubrics", return_value=aggregate_rubrics), \
             patch("backend.main.stage3_synthesize_final", side_effect=mock_stage3_stream):
            mock_get_conversation.return_value = conversation
            mock_retrieval.return_value = ("", [])
            mock_generate_title.return_value = "Design Studio"
            mock_stage2.return_value = (
                stage2_results,
                {"Response A": "model-a", "Response B": "model-b"},
            )

            async with async_client.stream(
                "POST",
                "/api/conversations/conv-design-stream/message/stream",
                json={"content": "Compare two web app directions"},
            ) as response:
                assert response.status_code == 200
                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))

            stage1_complete = next(event for event in events if event["type"] == "stage1_complete")
            stage2_complete = next(event for event in events if event["type"] == "stage2_complete")
            stage3_complete = next(event for event in events if event["type"] == "stage3_complete")

            stage1_design = stage1_complete["metadata"]["design_studio"]
            assert [item["id"] for item in stage1_design["candidate_directions"]] == [
                "direction-a",
                "direction-b",
            ]
            assert stage1_design["comparison"]["status"] == "pending"

            stage2_design = stage2_complete["metadata"]["design_studio"]
            assert stage2_design["comparison"]["status"] == "complete"
            assert stage2_design["comparison"]["ranked_directions"][0]["direction_id"] == "direction-b"
            assert stage2_design["selected_direction_id"] == "direction-b"

            stage3_design = stage3_complete["metadata"]["design_studio"]
            assert stage3_design["handoff"]["status"] == "ready"
            assert stage3_design["handoff"]["selected_direction_id"] == "direction-b"

            saved_metadata = mock_add_assistant_message.await_args.args[5]
            assert saved_metadata["design_studio"]["selected_direction_id"] == "direction-b"
            assert saved_metadata["design_studio"]["handoff"]["status"] == "ready"
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_stream_design_studio_with_image_findings_enables_critique_surface(async_client):
    conversation = {
        "id": "conv-design-image-stream",
        "framework": "standard",
        "session_type": "design_studio",
        "specialist_template_id": "design_web_app_studio",
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "review",
            "approved_direction_id": None,
        },
        "council_models": ["vision-a", "vision-b"],
        "chairman_model": "chair-model",
        "primary_artifacts": [
            {
                "id": "img-1",
                "kind": "image",
                "label": "mockup.png",
                "source": "upload",
                "status": "ready",
                "filename": "mockup.png",
                "mime_type": "image/png",
                "size_bytes": 128,
                "storage_path": "conv-design-image-stream/img-1.png",
                "preview_url": "/artifact-files/conv-design-image-stream/img-1.png",
            }
        ],
        "messages": [],
    }

    async def mock_stage1_stream(*args, **kwargs):
        yield {"model": "vision-a", "response": "Direction A critiques the current hero."}
        yield {"model": "vision-b", "response": "Direction B critiques the current card layout."}

    async def mock_stage3_stream(*args, **kwargs):
        yield """Ship Direction A.

VISUAL FINDINGS JSON:
```json
[
  {
    "artifact_label": "mockup.png",
    "title": "CTA lacks contrast",
    "comment": "The primary action is too low contrast against the background.",
    "severity": "high",
    "x": 60,
    "y": 20,
    "w": 18,
    "h": 10
  }
]
```"""

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock), \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock), \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock) as mock_add_assistant_message, \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.stage1_collect_responses", side_effect=mock_stage1_stream), \
             patch("backend.main.stage2_collect_rankings", new_callable=AsyncMock) as mock_stage2, \
             patch("backend.main.stage3_synthesize_final", side_effect=mock_stage3_stream) as mock_stage3, \
             patch("backend.openrouter.supports_vision_model", return_value=True), \
             patch("backend.image_artifacts.load_image_as_data_url", return_value="data:image/png;base64,abc"):
            mock_get_conversation.return_value = conversation
            mock_retrieval.return_value = ("", [])
            mock_generate_title.return_value = "Design Image Review"
            mock_stage2.return_value = (
                [{"model": "judge", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B"}],
                {"Response A": "vision-a", "Response B": "vision-b"},
            )

            async with async_client.stream(
                "POST",
                "/api/conversations/conv-design-image-stream/message/stream",
                json={"content": "Critique this mockup"},
            ) as response:
                assert response.status_code == 200
                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))

            stage3_complete = next(event for event in events if event["type"] == "stage3_complete")
            assert stage3_complete["data"]["response"] == "Ship Direction A."
            assert stage3_complete["metadata"]["visual_review"]["panel_enabled"] is True
            assert stage3_complete["metadata"]["visual_review"]["mode"] == "design_studio_critique"
            assert stage3_complete["metadata"]["visual_review"]["tab_label"] == "Critique"
            assert stage3_complete["metadata"]["visual_findings"][0]["artifact_id"] == "img-1"

            assert mock_stage3.call_args.kwargs["visual_findings_enabled"] is True
            saved_metadata = mock_add_assistant_message.await_args.args[5]
            assert saved_metadata["visual_review"]["panel_enabled"] is True
            assert saved_metadata["visual_findings"][0]["title"] == "CTA lacks contrast"
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_send_message_code_review_returns_execution_metadata(async_client):
    conversation = {
        "id": "conv-exec",
        "framework": "standard",
        "session_type": "code_review",
        "specialist_template_id": "code_security_review",
        "execution_mode": "safe_patch_checks",
        "council_models": ["openai/gpt-5.2"],
        "chairman_model": "chair-model",
        "primary_artifacts": [],
        "messages": [],
    }

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.add_user_message", new_callable=AsyncMock), \
             patch("backend.storage.update_conversation_title", new_callable=AsyncMock), \
             patch("backend.storage.add_assistant_message", new_callable=AsyncMock), \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.generate_conversation_title", new_callable=AsyncMock) as mock_generate_title, \
             patch("backend.main.run_full_council", new_callable=AsyncMock) as mock_run_council:
            mock_get_conversation.return_value = conversation
            mock_generate_title.return_value = "Exec Review"
            mock_retrieval.return_value = ("", [])
            mock_run_council.return_value = (
                [{"model": "openai/gpt-5.2", "response": "Apply the patch."}],
                [],
                {"model": "chair-model", "response": "Use the candidate patch."},
                {
                    "execution": {
                        "mode": "safe_patch_checks",
                        "status": "completed",
                        "candidate_patch": {"status": "applied", "changed_files": ["app.py"]},
                        "checks": [],
                        "summary": {"passed": 0, "failed": 0, "skipped": 0},
                    },
                },
            )

            response = await async_client.post(
                "/api/conversations/conv-exec/message",
                json={"content": "Review this change"}
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["metadata"]["execution_mode"] == "safe_patch_checks"
            assert payload["metadata"]["execution"]["candidate_patch"]["status"] == "applied"
            assert mock_run_council.await_args.kwargs["execution_mode"] == "safe_patch_checks"
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
async def test_retry_failed_stage1_design_studio_refreshes_direction_metadata(async_client):
    conversation = {
        "id": "conv-design-retry",
        "framework": "standard",
        "session_type": "design_studio",
        "council_models": ["model-good", "model-bad"],
        "messages": [
            {"role": "user", "content": "Generate two product directions"},
            {
                "role": "assistant",
                "stage1": [{"model": "model-good", "response": "Direction A"}],
                "stage2": [],
                "stage3": {"model": "chair", "response": "Use Direction A for now."},
                "metadata": {
                    "effective_council_models": ["model-good", "model-bad"],
                    "stage1_errors": [{"model": "model-bad", "error": "timeout"}],
                    "responded_council_models": ["model-good"],
                },
            },
        ],
    }

    async def mock_stage1_stream(*args, **kwargs):
        yield {"model": "model-bad", "response": "Direction B"}

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
    try:
        with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_get_conversation, \
             patch("backend.storage.update_message", new_callable=AsyncMock) as mock_update_message, \
             patch("backend.retrieval.build_retrieval_context", new_callable=AsyncMock) as mock_retrieval, \
             patch("backend.main.stage1_collect_responses", side_effect=mock_stage1_stream):
            mock_get_conversation.return_value = conversation
            mock_retrieval.return_value = ("", [])

            response = await async_client.post(
                "/api/conversations/conv-design-retry/messages/1/retry-stage1",
                json={}
            )

            assert response.status_code == 200
            metadata = response.json()["metadata"]
            assert [
                item["source_model"]
                for item in metadata["design_studio"]["candidate_directions"]
            ] == ["model-good", "model-bad"]
            assert metadata["design_studio"]["candidate_directions"][1]["id"] == "direction-b"

            updated_message = mock_update_message.await_args.args[3]
            assert [
                item["source_model"]
                for item in updated_message["metadata"]["design_studio"]["candidate_directions"]
            ] == ["model-good", "model-bad"]
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
