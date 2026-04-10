from backend.retrieval import _build_context

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
