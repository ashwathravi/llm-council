
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

def test_design_handoff_markdown_export_uses_approved_direction():
    conversation = {
        "id": "conv-design",
        "title": "Checkout Redesign",
        "created_at": "2026-04-24",
        "session_type": "design_studio",
        "session_config": {
            "design_target": "mixed",
            "studio_goal": "iterate",
            "approved_direction_id": "direction-b",
        },
        "primary_artifacts": [
            {"label": "checkout.png", "kind": "image", "status": "ready"},
        ],
        "messages": [
            {
                "role": "assistant",
                "metadata": {
                    "design_studio": {
                        "candidate_directions": [
                            {
                                "id": "direction-b",
                                "label": "Direction B",
                                "source_model": "model-b",
                                "summary": "Calmer checkout hierarchy.",
                            }
                        ],
                        "comparison": {
                            "ranked_directions": [
                                {"direction_id": "direction-b", "rank": 1, "average_rank": 1.0}
                            ]
                        },
                        "handoff": {
                            "status": "ready",
                            "selected_direction_id": "direction-b",
                            "selected_direction_ref": {
                                "id": "direction-b",
                                "label": "Direction B",
                                "source_model": "model-b",
                                "summary": "Calmer checkout hierarchy.",
                            },
                            "selected_direction": {
                                "label": "Selected Direction",
                                "content": "Direction B is approved.",
                                "items": [],
                            },
                            "rationale": {
                                "label": "Rationale",
                                "content": "- Stronger purchase clarity.",
                                "items": ["Stronger purchase clarity."],
                            },
                            "component_map": {
                                "label": "Component Map",
                                "content": "- Order summary: sticky confirmation module.",
                                "items": ["Order summary: sticky confirmation module."],
                            },
                            "state_notes": {
                                "label": "State Notes",
                                "content": "- Preserve totals during loading.",
                                "items": ["Preserve totals during loading."],
                            },
                            "platform_constraints": {
                                "label": "Platform Constraints",
                                "content": "- iOS actions stay thumb-reachable.",
                                "items": ["iOS actions stay thumb-reachable."],
                            },
                            "handoff_notes": {
                                "label": "Handoff Notes",
                                "content": "Use existing checkout primitives.",
                                "items": [],
                            },
                            "open_questions": {
                                "label": "Open Questions",
                                "content": "- Confirm promo code placement.",
                                "items": ["Confirm promo code placement."],
                            },
                        },
                    },
                },
            }
        ],
    }

    md = export.export_design_handoff_to_markdown(conversation)

    assert md.startswith("# DESIGN.md")
    assert "**Approved Direction:** direction-b" in md
    assert "## Chosen Direction" in md
    assert "Direction B is approved." in md
    assert "## Why This Direction Won" in md
    assert "- Stronger purchase clarity." in md
    assert "## Component Map" in md
    assert "## State Notes" in md
    assert "- Preserve totals during loading." in md
    assert "## Platform Constraints" in md
    assert "- iOS actions stay thumb-reachable." in md
    assert "## Decision Trace" in md

def test_design_handoff_markdown_export_ignores_stale_selected_handoff():
    conversation = {
        "id": "conv-design-stale",
        "title": "Checkout Redesign",
        "session_type": "design_studio",
        "session_config": {
            "design_target": "web_app",
            "studio_goal": "iterate",
            "approved_direction_id": "direction-a",
        },
        "messages": [
            {
                "role": "assistant",
                "metadata": {
                    "design_studio": {
                        "candidate_directions": [
                            {
                                "id": "direction-a",
                                "label": "Direction A",
                                "source_model": "model-a",
                                "summary": "Dense operational dashboard.",
                            },
                            {
                                "id": "direction-b",
                                "label": "Direction B",
                                "source_model": "model-b",
                                "summary": "Calmer editorial layout.",
                            },
                        ],
                        "handoff": {
                            "status": "ready",
                            "selected_direction_id": "direction-b",
                            "selected_direction_ref": {
                                "id": "direction-b",
                                "label": "Direction B",
                                "summary": "Calmer editorial layout.",
                            },
                            "selected_direction": {
                                "label": "Selected Direction",
                                "content": "Direction B is recommended.",
                                "items": [],
                            },
                        },
                    },
                },
            }
        ],
    }

    md = export.export_design_handoff_to_markdown(conversation)

    assert "**Approved Direction:** direction-a" in md
    assert "Direction A" in md
    assert "Dense operational dashboard." in md
    assert "Direction B is recommended." not in md

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
