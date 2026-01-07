from unittest.mock import patch, AsyncMock

import pytest

from backend import documents, retrieval, storage, config


def test_chunk_pages_overlap():
    text = "one two three four five six seven eight nine ten"
    chunks = documents.chunk_pages([text], chunk_words=4, overlap_words=1)

    assert len(chunks) == 3
    assert chunks[0]["text"] == "one two three four"
    assert chunks[1]["text"] == "four five six seven"
    assert chunks[2]["text"] == "seven eight nine ten"


@pytest.mark.asyncio
async def test_build_retrieval_context_orders_results():
    chunks = [
        {
            "document_id": "doc-1",
            "page_number": 1,
            "text": "alpha",
            "embedding": [1.0, 0.0],
        },
        {
            "document_id": "doc-2",
            "page_number": 2,
            "text": "beta",
            "embedding": [0.0, 1.0],
        },
    ]

    with patch("backend.storage.list_document_chunks", new_callable=AsyncMock) as mock_chunks, \
         patch("backend.storage.list_documents", new_callable=AsyncMock) as mock_docs, \
         patch("backend.documents.embed_texts") as mock_embed:
        mock_chunks.return_value = chunks
        mock_docs.return_value = [
            {"id": "doc-1", "filename": "alpha.pdf"},
            {"id": "doc-2", "filename": "beta.pdf"},
        ]
        mock_embed.return_value = [[1.0, 0.0]]

        context, citations = await retrieval.build_retrieval_context("conv", "user", "query")

        assert context is not None
        assert citations[0]["filename"] == "alpha.pdf"
        assert citations[0]["page_number"] == 1


@pytest.mark.asyncio
async def test_upload_documents_endpoint(async_client, monkeypatch, tmp_path):
    from backend.main import app
    from backend import auth

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"

    data_dir = str(tmp_path / "data_temp")
    docs_dir = str(tmp_path / "documents_temp")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "DOCUMENTS_DIR", docs_dir)
    monkeypatch.setattr(storage, "DATA_DIR", data_dir)
    monkeypatch.setattr(storage, "DOCUMENTS_DIR", docs_dir)

    response = await async_client.post(
        "/api/conversations",
        json={"framework": "standard", "council_models": [], "chairman_model": None},
    )
    assert response.status_code == 200
    conversation_id = response.json()["id"]

    with patch("backend.documents.extract_pdf_text", return_value=["Hello world"]), \
         patch("backend.documents.embed_texts", return_value=[[0.1, 0.2]]):
        files = [("files", ("doc.pdf", b"%PDF-1.4 test", "application/pdf"))]
        upload_response = await async_client.post(
            f"/api/conversations/{conversation_id}/documents",
            files=files
        )

        assert upload_response.status_code == 200
        payload = upload_response.json()
        assert payload["documents"][0]["status"] == "ready"
        assert payload["errors"] == []

    app.dependency_overrides = {}
