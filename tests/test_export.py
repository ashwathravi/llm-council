
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

def test_export_empty_conversation():
    """Test exporting an empty conversation dictionary."""
    conv = {}
    # Markdown
    md = export.export_to_markdown(conv)
    assert "# Conversation" in md
    # PDF
    pdf = export.export_to_pdf(conv)
    assert pdf.startswith(b"%PDF")

def test_export_messages_none():
    """Test exporting when messages is None."""
    conv = {"messages": None}
    # Should not raise TypeError anymore
    md = export.export_to_markdown(conv)
    assert "# Conversation" in md

    pdf = export.export_to_pdf(conv)
    assert pdf.startswith(b"%PDF")

def test_export_missing_message_fields():
    """Test exporting messages with missing fields."""
    conv = {
        "messages": [
            {"role": "user"}, # missing content
            {"role": "assistant"}, # missing stages
            {"role": "invalid"}, # unknown role
        ]
    }
    md = export.export_to_markdown(conv)
    assert "## User" in md

    pdf = export.export_to_pdf(conv)
    assert pdf.startswith(b"%PDF")

def test_export_none_stages():
    """Test assistant messages with None stages."""
    conv = {
        "messages": [
            {
                "role": "assistant",
                "stage1": None,
                "stage2": None,
                "stage3": None
            }
        ]
    }
    # Should handle None stages gracefully
    md = export.export_to_markdown(conv)
    assert "## LLM Council" in md

    pdf = export.export_to_pdf(conv)
    assert pdf.startswith(b"%PDF")

def test_export_malformed_stages():
    """Test assistant messages with malformed stage data (wrong types)."""
    conv = {
        "messages": [
            {
                "role": "assistant",
                "stage1": [{"model": None, "response": None}],
                "stage2": [None],
                "stage3": "not a dict"
            }
        ]
    }
    # Should not raise AttributeError or other crashes
    md = export.export_to_markdown(conv)
    assert "## LLM Council" in md

    pdf = export.export_to_pdf(conv)
    assert pdf.startswith(b"%PDF")

def test_export_invalid_input_types():
    """Test with completely invalid input types."""
    # Should handle None or non-dict conversation gracefully
    for invalid_input in [None, [], "not a dict"]:
        md = export.export_to_markdown(invalid_input)
        assert "# Conversation" in md

        pdf = export.export_to_pdf(invalid_input)
        assert pdf.startswith(b"%PDF")
