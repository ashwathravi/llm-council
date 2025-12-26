
import io
import pytest
from backend import export

def test_pdf_generation_with_special_chars():
    """Verify PDF generation handles special characters correctly."""
    conversation = {
        "title": "Test <Conversation> & More",
        "created_at": "2025-01-01",
        "framework": "standard",
        "messages": [
            {
                "role": "user",
                "content": "Here is some code: if x < y: print('Hello & Goodbye')"
            },
            {
                "role": "assistant",
                "stage1": [
                    {"model": "Model <A>", "response": "Response with <tags>"}
                ],
                "stage2": [],
                "stage3": {"response": "Final <answer>"}
            }
        ]
    }

    # This should not raise an error
    pdf_bytes = export.export_to_pdf(conversation)

    # Basic verification
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 0

def test_markdown_export():
    conversation = {
        "title": "Test Conversation",
        "created_at": "2025-01-01",
        "framework": "standard",
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }
    md = export.export_to_markdown(conversation)
    assert "# Test Conversation" in md
    assert "## User" in md
    assert "Hello" in md
