from backend import code_artifacts
from backend.retrieval import _build_context, _build_code_chunks

def test_build_context_empty():
    assert _build_context([]) == ""

def test_build_context_single():
    citations = [
        {
            "filename": "test.pdf",
            "page_number": 1,
            "snippet": "This is a test snippet."
        }
    ]
    expected = (
        "You have access to the following document excerpts.\n"
        "Use them to answer the user's question and cite sources as [filename p.#].\n\n"
        "Source: test.pdf (p. 1)\n"
        "This is a test snippet."
    )
    assert _build_context(citations) == expected

def test_build_context_multiple():
    citations = [
        {
            "filename": "test1.pdf",
            "page_number": 1,
            "snippet": "Snippet 1"
        },
        {
            "filename": "test2.pdf",
            "page_number": 5,
            "snippet": "Snippet 2"
        }
    ]
    expected = (
        "You have access to the following document excerpts.\n"
        "Use them to answer the user's question and cite sources as [filename p.#].\n\n"
        "Source: test1.pdf (p. 1)\n"
        "Snippet 1\n\n"
        "Source: test2.pdf (p. 5)\n"
        "Snippet 2"
    )
    assert _build_context(citations) == expected


def test_build_context_code_source_uses_symbol_and_line_range():
    citations = [
        {
            "artifact_type": "code",
            "filename": "src/app.py",
            "line_start": 10,
            "line_end": 18,
            "symbol": "build_context",
            "chunk_type": "symbol",
            "snippet": "Snippet",
        }
    ]

    context = _build_context(citations)
    assert "Source: src/app.py::build_context (lines 10-18)" in context


def test_build_code_chunks_include_file_overview_and_symbol_chunks():
    chunks = _build_code_chunks(
        "class Foo:\n    pass\n\n\ndef bar():\n    return 1\n",
        "src/app.py",
    )

    assert chunks[0]["chunk_type"] == "file_overview"
    assert "Foo" in chunks[0]["symbols"]
    assert "bar" in chunks[0]["symbols"]
    symbol_chunks = [chunk for chunk in chunks if chunk["chunk_type"] == "symbol"]
    assert len(symbol_chunks) == 2
    assert any(chunk["symbol_name"] == "Foo" and chunk["line_start"] == 1 for chunk in symbol_chunks)
    assert any(chunk["symbol_name"] == "bar" and chunk["line_start"] == 5 for chunk in symbol_chunks)


def test_format_code_context_uses_absolute_line_numbers():
    formatted = code_artifacts.format_code_context(
        "alpha\nbeta",
        max_lines=10,
        max_chars=200,
        line_start=10,
    )

    assert formatted.startswith("  10 | alpha")
    assert "\n  11 | beta" in formatted
