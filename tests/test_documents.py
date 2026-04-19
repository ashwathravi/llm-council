from unittest.mock import patch, AsyncMock

import pytest

from backend import documents, retrieval, storage, config, image_artifacts, code_artifacts


@pytest.mark.parametrize("filename, content_type, expected", [
    ("test.pdf", "application/pdf", True),
    ("test.PDF", "application/pdf", True),
    ("test.pdf", "APPLICATION/PDF", True),
    ("test.pdf", None, True),
    (None, "application/pdf", True),
    ("test.txt", "text/plain", False),
    ("test.pdf.txt", "text/plain", False),
    (None, None, False),
    ("", "", False),
    ("test.pdf", "text/plain", True),  # filename wins
    ("test.txt", "application/pdf", True),  # content_type wins
])
def test_is_pdf_file(filename, content_type, expected):
    assert documents.is_pdf_file(filename, content_type) == expected


@pytest.mark.parametrize("header, expected", [
    (b"%PDF-1.4", True),
    (b"%PDF-1.7", True),
    (b"%PDF-2.0", True),
    (b"PDF-1.4", False),
    (b"something %PDF-1.4", False),
    (b"NOT A PDF", False),
    (b"", False),
    (b" %PDF-1.4", False),  # Must start with %PDF-
    (b"random bytes", False),
])
def test_validate_pdf_header(header, expected):
    assert documents.validate_pdf_header(header) == expected


@pytest.mark.parametrize("text, expected", [
    ("hello world", "hello world"),
    ("hello   world", "hello world"),
    ("hello\tworld", "hello world"),
    ("hello\nworld", "hello world"),
    ("  hello \n \t world  ", "hello world"),
    ("  hello   world  ", "hello world"),
    ("\nhello\tworld\r", "hello world"),
    ("multiple   spaces   between   words", "multiple spaces between words"),
    ("multiple    spaces", "multiple spaces"),
    ("", ""),
    ("   ", ""),
    ("   \n\t  ", ""),
])
def test_normalize_text(text, expected):
    assert documents.normalize_text(text) == expected


def test_chunk_pages_overlap():
    text = "one two three four five six seven eight nine ten"
    chunks = documents.chunk_pages([text], chunk_words=4, overlap_words=1)

    assert len(chunks) == 3
    assert chunks[0]["text"] == "one two three four"
    assert chunks[1]["text"] == "four five six seven"
    assert chunks[2]["text"] == "seven eight nine ten"


@pytest.mark.asyncio
async def test_build_retrieval_context_orders_results():
    # Mock metadata (embeddings only)
    chunks_meta = [
        {"id": "c1", "document_id": "doc-1", "page_number": 1, "embedding": [1.0, 0.0]},
        {"id": "c2", "document_id": "doc-2", "page_number": 2, "embedding": [0.0, 1.0]},
    ]
    # Mock full chunks (text)
    chunks_full = [
        {"id": "c1", "document_id": "doc-1", "page_number": 1, "text": "alpha", "embedding": [1.0, 0.0]},
        {"id": "c2", "document_id": "doc-2", "page_number": 2, "text": "beta", "embedding": [0.0, 1.0]},
    ]

    with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_conversation, \
         patch("backend.storage.list_document_embeddings", new_callable=AsyncMock) as mock_embeddings, \
         patch("backend.storage.get_document_chunks_by_ids", new_callable=AsyncMock) as mock_chunks, \
         patch("backend.storage.list_documents", new_callable=AsyncMock) as mock_docs, \
         patch("backend.documents.embed_texts") as mock_embed:

        mock_conversation.return_value = {"id": "conv", "primary_artifacts": []}
        mock_embeddings.return_value = chunks_meta
        mock_chunks.return_value = chunks_full
        mock_docs.return_value = [
            {"id": "doc-1", "filename": "alpha.pdf"},
            {"id": "doc-2", "filename": "beta.pdf"},
        ]
        mock_embed.return_value = [[1.0, 0.0]]

        context, citations = await retrieval.build_retrieval_context("conv", "user", "query")

        assert context is not None
        # Should match doc-1 because dot product with [1,0] is 1.0 vs 0.0
        assert citations[0]["filename"] == "alpha.pdf"
        assert citations[0]["page_number"] == 1


@pytest.mark.asyncio
async def test_build_retrieval_context_offloads_embedding_to_threadpool():
    chunks_meta = [
        {"id": "c1", "document_id": "doc-1", "page_number": 1, "embedding": [1.0, 0.0]},
    ]
    chunks_full = [
        {"id": "c1", "document_id": "doc-1", "page_number": 1, "text": "alpha", "embedding": [1.0, 0.0]},
    ]

    with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_conversation, \
         patch("backend.storage.list_document_embeddings", new_callable=AsyncMock) as mock_embeddings, \
         patch("backend.storage.get_document_chunks_by_ids", new_callable=AsyncMock) as mock_chunks, \
         patch("backend.storage.list_documents", new_callable=AsyncMock) as mock_docs, \
         patch("backend.retrieval.run_in_threadpool", new_callable=AsyncMock) as mock_threadpool:

        mock_conversation.return_value = {"id": "conv", "primary_artifacts": []}
        mock_embeddings.return_value = chunks_meta
        mock_chunks.return_value = chunks_full
        mock_docs.return_value = [{"id": "doc-1", "filename": "alpha.pdf"}]
        mock_threadpool.return_value = [[1.0, 0.0]]

        context, citations = await retrieval.build_retrieval_context("conv", "user", "query")

        assert context is not None
        assert citations[0]["filename"] == "alpha.pdf"

        # Verify call to threadpool for embeddings
        mock_threadpool.assert_awaited_once_with(documents.embed_texts, ["query"])


@pytest.mark.asyncio
async def test_build_retrieval_context_includes_code_artifact_citations():
    conversation = {
        "id": "conv",
        "primary_artifacts": [
            {
                "id": "code-1",
                "kind": "code",
                "label": "app.py",
                "status": "ready",
                "storage_path": "conv/code-1-app.py",
            }
        ],
    }

    with patch("backend.storage.get_conversation", new_callable=AsyncMock) as mock_conversation, \
         patch("backend.storage.list_document_embeddings", new_callable=AsyncMock) as mock_embeddings, \
         patch("backend.code_artifacts.load_code_file", return_value="def foo():\n    return 1\n"):
        mock_conversation.return_value = conversation
        mock_embeddings.return_value = []

        context, citations = await retrieval.build_retrieval_context("conv", "user", "foo return")

        assert context is not None
        assert "artifact excerpts" in context
        assert "Source: app.py (lines 1-2)" in context
        assert citations[0]["artifact_type"] == "code"
        assert citations[0]["filename"] == "app.py"
        assert citations[0]["line_start"] == 1
        assert citations[0]["line_end"] == 2


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

    conversation_response = await async_client.get(f"/api/conversations/{conversation_id}")
    assert conversation_response.status_code == 200
    conversation_payload = conversation_response.json()
    assert conversation_payload["session_type"] == "general"
    assert len(conversation_payload["primary_artifacts"]) == 1
    assert conversation_payload["primary_artifacts"][0]["document_id"] == payload["documents"][0]["id"]

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_upload_image_artifacts_endpoint(async_client, monkeypatch, tmp_path):
    from backend.main import app
    from backend import auth

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"

    data_dir = str(tmp_path / "data_temp")
    docs_dir = str(tmp_path / "documents_temp")
    artifacts_dir = str(tmp_path / "artifacts_temp")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "DOCUMENTS_DIR", docs_dir)
    monkeypatch.setattr(config, "ARTIFACT_FILES_DIR", artifacts_dir)
    monkeypatch.setattr(storage, "DATA_DIR", data_dir)
    monkeypatch.setattr(storage, "DOCUMENTS_DIR", docs_dir)
    monkeypatch.setattr(image_artifacts, "ARTIFACT_FILES_DIR", artifacts_dir)

    response = await async_client.post(
        "/api/conversations",
        json={
            "framework": "standard",
            "session_type": "visual_review",
            "council_models": [],
            "chairman_model": None,
        },
    )
    assert response.status_code == 200
    conversation_id = response.json()["id"]

    png_bytes = b"\x89PNG\r\n\x1a\nmock"
    upload_response = await async_client.post(
        f"/api/conversations/{conversation_id}/artifacts/images",
        files=[("files", ("mockup.png", png_bytes, "image/png"))]
    )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["errors"] == []
    assert payload["artifacts"][0]["kind"] == "image"
    assert payload["artifacts"][0]["mime_type"] == "image/png"
    assert payload["artifacts"][0]["preview_url"].startswith("/artifact-files/")
    assert payload["artifacts"][0]["storage_path"].startswith(f"{conversation_id}/")

    conversation_response = await async_client.get(f"/api/conversations/{conversation_id}")
    assert conversation_response.status_code == 200
    conversation_payload = conversation_response.json()
    assert conversation_payload["session_type"] == "visual_review"
    assert len(conversation_payload["primary_artifacts"]) == 1
    assert conversation_payload["primary_artifacts"][0]["kind"] == "image"

    saved_path = tmp_path / "artifacts_temp" / conversation_payload["primary_artifacts"][0]["storage_path"]
    assert saved_path.exists()

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_upload_code_artifacts_endpoint(async_client, monkeypatch, tmp_path):
    from backend.main import app
    from backend import auth

    app.dependency_overrides[auth.get_current_user_id] = lambda: "test_user"

    data_dir = str(tmp_path / "data_temp")
    docs_dir = str(tmp_path / "documents_temp")
    artifacts_dir = str(tmp_path / "artifacts_temp")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "DOCUMENTS_DIR", docs_dir)
    monkeypatch.setattr(config, "ARTIFACT_FILES_DIR", artifacts_dir)
    monkeypatch.setattr(storage, "DATA_DIR", data_dir)
    monkeypatch.setattr(storage, "DOCUMENTS_DIR", docs_dir)
    monkeypatch.setattr(image_artifacts, "ARTIFACT_FILES_DIR", artifacts_dir)
    monkeypatch.setattr(code_artifacts, "ARTIFACT_FILES_DIR", artifacts_dir)

    response = await async_client.post(
        "/api/conversations",
        json={
            "framework": "standard",
            "session_type": "code_review",
            "council_models": [],
            "chairman_model": None,
        },
    )
    assert response.status_code == 200
    conversation_id = response.json()["id"]

    upload_response = await async_client.post(
        f"/api/conversations/{conversation_id}/artifacts/code-files",
        files=[("files", ("app.py", b"def foo():\n    return 1\n", "text/x-python"))]
    )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["errors"] == []
    assert payload["artifacts"][0]["kind"] == "code"
    assert payload["artifacts"][0]["language"] == "Python"
    assert payload["artifacts"][0]["line_count"] == 2
    assert payload["artifacts"][0]["storage_path"].startswith(f"{conversation_id}/")

    conversation_response = await async_client.get(f"/api/conversations/{conversation_id}")
    assert conversation_response.status_code == 200
    conversation_payload = conversation_response.json()
    assert conversation_payload["session_type"] == "code_review"
    assert len(conversation_payload["primary_artifacts"]) == 1
    assert conversation_payload["primary_artifacts"][0]["kind"] == "code"

    saved_path = tmp_path / "artifacts_temp" / conversation_payload["primary_artifacts"][0]["storage_path"]
    assert saved_path.exists()

    app.dependency_overrides = {}
