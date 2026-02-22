import pytest
from unittest.mock import AsyncMock, patch
from backend import storage
from sqlalchemy import insert
from backend.database import DocumentChunkModel

@pytest.mark.asyncio
async def test_db_add_document_chunks_optimization():
    chunks = [
        {
            "document_id": "doc1",
            "conversation_id": "conv1",
            "user_id": "user1",
            "chunk_index": 0,
            "page_number": 1,
            "text": "text1",
            "embedding": [0.1, 0.2]
        }
    ]

    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session

    with patch("backend.storage.AsyncSessionLocal", return_value=mock_session_cm):
        await storage.db_add_document_chunks(chunks)

    # Verify execute was called
    assert mock_session.execute.called
    args, kwargs = mock_session.execute.call_args
    assert args[0].is_insert
    assert args[0].table.name == "document_chunks"

    # Verify data passed to execute
    data = args[1]
    assert len(data) == 1
    assert data[0]["document_id"] == "doc1"
    assert "id" in data[0]
    assert "created_at" in data[0]

    # Verify commit was called
    assert mock_session.commit.called

@pytest.mark.asyncio
async def test_db_add_document_chunks_empty():
    with patch("backend.storage.AsyncSessionLocal") as mock_session_local:
        await storage.db_add_document_chunks([])
        assert not mock_session_local.called
