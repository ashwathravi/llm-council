
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_health_check(async_client):
    """Test that the status endpoint returns 200 and expected structure."""
    response = await async_client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "storage_mode" in data
    assert "origin" in data
    assert "database_url_configured" in data

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
        
        from backend.main import app
        from backend import auth
        
        app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
        
        response = await async_client.get("/api/models")
        assert response.status_code == 200
        assert response.json() == mock_models
        
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_conversations_empty(async_client):
    """Test listing conversations returns empty list initially."""
    # Define async mock function
    async def mock_return_empty(*args, **kwargs):
        return []

    with patch("backend.storage.list_conversations", side_effect=mock_return_empty):
        from backend.main import app
        from backend import auth
        app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"
        
        response = await async_client.get("/api/conversations")
        assert response.status_code == 200
        assert response.json() == []
        
        app.dependency_overrides = {}
