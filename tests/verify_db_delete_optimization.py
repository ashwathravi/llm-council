
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from backend import storage
from backend.database import DocumentModel, DocumentChunkModel

@pytest.mark.asyncio
async def test_db_delete_document_success():
    # Mock AsyncSessionLocal and its session
    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session

    # Mock delete results
    mock_result_chunks = MagicMock()
    mock_result_doc = MagicMock()
    mock_result_doc.rowcount = 1  # Success

    mock_session.execute.side_effect = [mock_result_chunks, mock_result_doc]

    with patch("backend.storage.AsyncSessionLocal", return_value=mock_session_cm):
        await storage.db_delete_document("conv1", "doc1", "user1")

    assert mock_session.commit.called
    assert not mock_session.rollback.called

@pytest.mark.asyncio
async def test_db_delete_document_unauthorized_or_not_found():
    # Mock AsyncSessionLocal and its session
    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session

    # Mock delete results
    mock_result_chunks = MagicMock()
    mock_result_doc = MagicMock()
    mock_result_doc.rowcount = 0  # Not found or unauthorized

    mock_session.execute.side_effect = [mock_result_chunks, mock_result_doc]

    with patch("backend.storage.AsyncSessionLocal", return_value=mock_session_cm):
        with pytest.raises(ValueError, match="Unauthorized or not found"):
            await storage.db_delete_document("conv1", "doc1", "user1")

    assert mock_session.rollback.called
    assert not mock_session.commit.called
