from backend.design_studio import build_design_studio_metadata


def test_build_design_studio_metadata_maps_candidates_and_comparison():
    stage1_results = [
        {"model": "model-a", "response": "Direction A\nUse a dense operations layout."},
        {"model": "model-b", "response": "Direction B\nUse a calmer editorial layout."},
    ]
    stage2_results = [
        {
            "model": "judge",
            "parsed_ranking": ["Response B", "Response A"],
            "confidence": 88,
            "rubric_scores": {
                "Response A": {"hierarchy": 3},
                "Response B": {"hierarchy": 5},
            },
        }
    ]
    aggregate_rankings = [
        {"model": "model-b", "average_rank": 1.0, "rankings_count": 1},
        {"model": "model-a", "average_rank": 2.0, "rankings_count": 1},
    ]
    aggregate_rubrics = [
        {
            "model": "model-b",
            "overall_score": 4.8,
            "criteria": [{"key": "hierarchy", "average_score": 5.0}],
        }
    ]
    stage3_result = {"model": "chair", "response": "Ship Direction B."}

    metadata = build_design_studio_metadata(
        session_type="design_studio",
        stage1_results=stage1_results,
        stage2_results=stage2_results,
        stage3_result=stage3_result,
        aggregate_rankings=aggregate_rankings,
        aggregate_rubrics=aggregate_rubrics,
    )

    assert metadata["schema_version"] == 1
    assert metadata["candidate_directions"] == [
        {
            "id": "direction-a",
            "label": "Direction A",
            "response_label": "Response A",
            "source_model": "model-a",
            "summary": "Direction A",
        },
        {
            "id": "direction-b",
            "label": "Direction B",
            "response_label": "Response B",
            "source_model": "model-b",
            "summary": "Direction B",
        },
    ]
    assert metadata["comparison"]["status"] == "complete"
    assert metadata["comparison"]["ranked_directions"][0]["direction_id"] == "direction-b"
    assert metadata["comparison"]["rubric_summaries"][0]["direction_id"] == "direction-b"
    assert metadata["comparison"]["judge_results"][0]["ranked_directions"][0]["direction_id"] == "direction-b"
    assert metadata["comparison"]["judge_results"][0]["rubric_scores"]["direction-b"] == {"hierarchy": 5}
    assert metadata["selected_direction_id"] == "direction-b"
    assert metadata["handoff"]["status"] == "ready"
    assert metadata["handoff"]["selected_direction_id"] == "direction-b"
    assert metadata["handoff"]["selected_direction_ref"]["id"] == "direction-b"
    assert metadata["handoff"]["selected_direction"]["content"] == "Direction B"


def test_build_design_studio_metadata_normalizes_final_handoff_sections():
    stage1_results = [
        {"model": "model-a", "response": "Direction A\nUse a dense operations layout."},
        {"model": "model-b", "response": "Direction B\nUse a calmer editorial layout."},
    ]
    aggregate_rankings = [
        {"model": "model-b", "average_rank": 1.0, "rankings_count": 2},
        {"model": "model-a", "average_rank": 2.0, "rankings_count": 2},
    ]
    stage3_result = {
        "model": "chair",
        "response": """## Selected Direction
Direction B is the selected direction.

## Rationale
- Stronger hierarchy for first-time users.
- Lower implementation risk.

## Component Map
- Header: calm navigation with primary CTA.
- Workspace: editorial layout with preview pane.

## Handoff Notes
Use the existing card primitives and keep empty states explicit.

## Open Questions
- Should the workspace include saved variants in v1?""",
    }

    metadata = build_design_studio_metadata(
        session_type="design_studio",
        stage1_results=stage1_results,
        stage3_result=stage3_result,
        aggregate_rankings=aggregate_rankings,
    )

    handoff = metadata["handoff"]
    assert handoff["status"] == "ready"
    assert handoff["selected_direction_id"] == "direction-b"
    assert handoff["selected_direction_ref"]["id"] == "direction-b"
    assert handoff["selected_direction"]["content"] == "Direction B is the selected direction."
    assert handoff["rationale"]["items"] == [
        "Stronger hierarchy for first-time users.",
        "Lower implementation risk.",
    ]
    assert handoff["component_map"]["items"] == [
        "Header: calm navigation with primary CTA.",
        "Workspace: editorial layout with preview pane.",
    ]
    assert handoff["handoff_notes"]["content"] == "Use the existing card primitives and keep empty states explicit."
    assert handoff["open_questions"]["items"] == [
        "Should the workspace include saved variants in v1?",
    ]
    assert [section["key"] for section in handoff["sections"]] == [
        "selected_direction",
        "rationale",
        "component_map",
        "handoff_notes",
        "open_questions",
    ]


def test_build_design_studio_metadata_ignores_other_session_types():
    metadata = build_design_studio_metadata(
        session_type="visual_review",
        stage1_results=[{"model": "model-a", "response": "Review"}],
    )

    assert metadata == {}
