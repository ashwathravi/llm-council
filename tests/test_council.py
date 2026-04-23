
import pytest
from unittest.mock import patch, AsyncMock
from backend import council

@pytest.mark.asyncio
async def test_stage1_standard():
    # We need to mock query_model since stage1 calls it individually in parallel
    with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
        # Mock side effects based on input messages or just return generic
        mock_query.side_effect = [
            {"content": "Response A"},
            {"content": "Response B"}
        ]
        
        results = []
        async for res in council.stage1_collect_responses(
            [{"role": "user", "content": "What is AI?"}],
            council_models=["gpt-4", "claude-3"]
        ):
            results.append(res)
        
        # stage1_collect_responses returns List[Dict] with 'model' and 'response' keys
        assert len(results) == 2
        
        # Verify content mapping (order might vary due to async)
        models_found = sorted([r['model'] for r in results])
        assert models_found == ["claude-3", "gpt-4"]
        
        assert mock_query.call_count == 2


@pytest.mark.asyncio
async def test_stage3_synthesis():
    # stage3 uses query_model_stream
    async def mock_stream(*args, **kwargs):
        yield "Final "
        yield "Answer"

    with patch("backend.council.query_model_stream", side_effect=mock_stream) as mock_stream_fn:
        
        full_response = ""
        async for token in council.stage3_synthesize_final(
            "Query",
            [{"model": "gpt-4", "response": "Resp"}], # stage1 results format
            [], # stage2 results
            "chairman-model"
        ):
            full_response += token
        
        assert full_response == "Final Answer"


@pytest.mark.asyncio
async def test_stage3_synthesis_uses_template_deliverable_format():
    async def mock_stream(*args, **kwargs):
        yield "Final"

    with patch("backend.council.query_model_stream", side_effect=mock_stream) as mock_stream_fn:
        full_response = ""
        async for token in council.stage3_synthesize_final(
            "Review this patch",
            [{"model": "gpt-4", "response": "Looks risky"}],
            [{"model": "claude-3", "ranking": "Response A has an auth bug"}],
            "chairman-model",
            session_type="code_review",
            specialist_template_id="code_security_review",
        ):
            full_response += token

    assert full_response == "Final"
    prompt = mock_stream_fn.call_args.args[1][0]["content"]
    assert "FINAL DELIVERABLE FORMAT" in prompt
    assert "Bug triage summary" in prompt
    assert "Security Findings" in prompt
    assert "Do not return a generic essay" in prompt


@pytest.mark.asyncio
async def test_stage3_synthesis_uses_session_default_deliverable_format():
    async def mock_stream(*args, **kwargs):
        yield "Final"

    with patch("backend.council.query_model_stream", side_effect=mock_stream) as mock_stream_fn:
        async for _token in council.stage3_synthesize_final(
            "Summarize the spec",
            [{"model": "gpt-4", "response": "Here is the plan"}],
            [],
            "chairman-model",
            session_type="build_spec",
        ):
            pass

    prompt = mock_stream_fn.call_args.args[1][0]["content"]
    assert "Patch plan or implementation handoff" in prompt
    assert "Implementation Plan" in prompt


@pytest.mark.asyncio
async def test_stage3_synthesis_design_studio_uses_design_handoff_format():
    async def mock_stream(*args, **kwargs):
        yield "Final"

    with patch("backend.council.query_model_stream", side_effect=mock_stream) as mock_stream_fn:
        async for _token in council.stage3_synthesize_final(
            "Design a new workflow",
            [{"model": "gpt-4", "response": "Direction A"}],
            [],
            "chairman-model",
            session_type="design_studio",
            specialist_template_id="design_cross_platform_studio",
        ):
            pass

    prompt = mock_stream_fn.call_args.args[1][0]["content"]
    assert "FINAL DELIVERABLE FORMAT" in prompt
    assert "Design Studio handoff" in prompt
    assert "Candidate Directions" in prompt
    assert "Recommended Direction" in prompt
    assert "Handoff Notes" in prompt


@pytest.mark.asyncio
async def test_stage3_synthesis_includes_rubric_summary():
    async def mock_stream(*args, **kwargs):
        yield "Final"

    with patch("backend.council.query_model_stream", side_effect=mock_stream) as mock_stream_fn:
        async for _token in council.stage3_synthesize_final(
            "Review this patch",
            [{"model": "gpt-4", "response": "Resp"}],
            [{"model": "claude-3", "ranking": "Feedback"}],
            "chairman-model",
            session_type="code_review",
            aggregate_rubrics=[
                {
                    "model": "gpt-4",
                    "overall_score": 4.2,
                    "criteria": [
                        {"key": "correctness", "label": "Correctness", "average_score": 4.8, "spread": 1.0},
                        {"key": "performance", "label": "Performance", "average_score": 3.1, "spread": 2.0},
                    ],
                }
            ],
        ):
            pass

    prompt = mock_stream_fn.call_args.args[1][0]["content"]
    assert "RUBRIC SUMMARY" in prompt
    assert "overall rubric 4.2/5" in prompt
    assert "Performance spread 2.0" in prompt


@pytest.mark.asyncio
async def test_stage3_synthesis_visual_review_requests_visual_findings_json():
    async def mock_stream(*args, **kwargs):
        yield "Final"

    with patch("backend.council.query_model_stream", side_effect=mock_stream) as mock_stream_fn:
        async for _token in council.stage3_synthesize_final(
            "Review this mockup",
            [{"model": "gpt-4", "response": "Resp"}],
            [{"model": "claude-3", "ranking": "Feedback"}],
            "chairman-model",
            session_type="visual_review",
        ):
            pass

    prompt = mock_stream_fn.call_args.args[1][0]["content"]
    assert "VISUAL FINDINGS JSON" in prompt
    assert "artifact_label" in prompt
    assert "Coordinates must be normalized percentages" in prompt


def test_parse_confidence_from_text():
    assert council.parse_confidence_from_text("FINAL RANKING:\n1. Response A\nCONFIDENCE: 82") == 82
    assert council.parse_confidence_from_text("confidence: 150") == 100
    assert council.parse_confidence_from_text("No explicit confidence provided") is None


def test_calculate_aggregate_rankings_uses_ballot_weights():
    stage2_results = [
        {
            "model": "judge-a",
            "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
            "parsed_ranking": ["Response A", "Response B"],
            "ballot_weight": 1.5,
        },
        {
            "model": "judge-b",
            "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
            "parsed_ranking": ["Response B", "Response A"],
            "ballot_weight": 0.5,
        },
    ]
    label_to_model = {"Response A": "model-a", "Response B": "model-b"}

    aggregate = council.calculate_aggregate_rankings(stage2_results, label_to_model)

    assert aggregate[0]["model"] == "model-a"
    assert aggregate[0]["average_rank"] == 1.25
    assert aggregate[0]["rankings_count"] == 2
    assert aggregate[0]["total_weight"] == 2.0
    assert aggregate[0]["weighted"] is True
    assert aggregate[1]["model"] == "model-b"
    assert aggregate[1]["average_rank"] == 1.75


def test_calculate_aggregate_rubrics_summarizes_scores():
    stage2_results = [
        {
            "model": "judge-a",
            "rubric_scores": {
                "Response A": {"correctness": 5, "maintainability": 4, "security": 4},
                "Response B": {"correctness": 3, "maintainability": 2, "security": 3},
            },
        },
        {
            "model": "judge-b",
            "rubric_scores": {
                "Response A": {"correctness": 4, "maintainability": 3, "security": 5},
                "Response B": {"correctness": 2, "maintainability": 2, "security": 2},
            },
        },
    ]
    label_to_model = {"Response A": "model-a", "Response B": "model-b"}

    aggregate = council.calculate_aggregate_rubrics(
        stage2_results,
        label_to_model,
        session_type="code_review",
    )

    assert aggregate[0]["model"] == "model-a"
    assert aggregate[0]["overall_score"] == 4.17
    assert aggregate[0]["evaluation_count"] == 2
    correctness = next(item for item in aggregate[0]["criteria"] if item["key"] == "correctness")
    assert correctness["average_score"] == 4.5
    assert correctness["spread"] == 1


def test_extract_visual_findings_from_response_strips_json_appendix():
    response = """Summary of the design issues.

VISUAL FINDINGS JSON:
```json
[
  {
    "artifact_label": "mockup-a.png",
    "title": "CTA lacks contrast",
    "comment": "The primary button blends into the card background.",
    "severity": "high",
    "x": 62,
    "y": 18,
    "w": 20,
    "h": 12
  }
]
```"""

    cleaned, findings = council.extract_visual_findings_from_response(
        response,
        primary_artifacts=[
            {"id": "img-a", "kind": "image", "label": "mockup-a.png"},
        ],
    )

    assert cleaned == "Summary of the design issues."
    assert findings == [
        {
            "id": "visual-finding-1",
            "artifact_id": "img-a",
            "artifact_label": "mockup-a.png",
            "title": "CTA lacks contrast",
            "comment": "The primary button blends into the card background.",
            "severity": "high",
            "x": 62.0,
            "y": 18.0,
            "w": 20.0,
            "h": 12.0,
        }
    ]


@pytest.mark.asyncio
async def test_stage2_collect_rankings_adds_rubric_scores_for_code_review():
    mocked_responses = {
        "reviewer-a": {
            "content": """Good depth on architecture.

RUBRIC SCORES:
Response A
- Correctness: 5
- Maintainability: 4
- Security: 3
- Performance: 4
- Testability: 5
- Effort: 4
- Confidence: 4
Response B
- Correctness: 3
- Maintainability: 2
- Security: 4
- Performance: 3
- Testability: 2
- Effort: 2
- Confidence: 3

FINAL RANKING:
1. Response A
2. Response B"""
        }
    }

    with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
        mock_parallel.return_value = mocked_responses

        stage2_results, label_to_model = await council.stage2_collect_rankings(
            "Which review is stronger?",
            [
                {"model": "model-a", "response": "Answer A"},
                {"model": "model-b", "response": "Answer B"},
            ],
            council_models=["reviewer-a"],
            session_type="code_review",
        )

    assert label_to_model == {"Response A": "model-a", "Response B": "model-b"}
    assert stage2_results[0]["rubric_scores"]["Response A"]["correctness"] == 5
    assert stage2_results[0]["rubric_scores"]["Response A"]["testability"] == 5
    assert stage2_results[0]["rubric_scores"]["Response B"]["maintainability"] == 2


@pytest.mark.asyncio
async def test_stage2_collect_rankings_adds_rubric_scores_for_design_studio():
    mocked_responses = {
        "reviewer-a": {
            "content": """Strong ideas.

RUBRIC SCORES:
Response A
- Task Clarity: 5
- Hierarchy: 4
- Platform Fit: 5
- Accessibility: 3
- Implementation Realism: 4
- Effort: 4
- Confidence: 5
Response B
- Task Clarity: 3
- Hierarchy: 3
- Platform Fit: 2
- Accessibility: 4
- Implementation Realism: 3
- Effort: 2
- Confidence: 3

FINAL RANKING:
1. Response A
2. Response B"""
        }
    }

    with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
        mock_parallel.return_value = mocked_responses

        stage2_results, label_to_model = await council.stage2_collect_rankings(
            "Which design direction is stronger?",
            [
                {"model": "model-a", "response": "Answer A"},
                {"model": "model-b", "response": "Answer B"},
            ],
            council_models=["reviewer-a"],
            session_type="design_studio",
        )

    assert label_to_model == {"Response A": "model-a", "Response B": "model-b"}
    assert stage2_results[0]["rubric_scores"]["Response A"]["task_clarity"] == 5
    assert stage2_results[0]["rubric_scores"]["Response A"]["platform_fit"] == 5
    assert stage2_results[0]["rubric_scores"]["Response B"]["implementation_realism"] == 3


def test_build_model_weight_profile_tracks_prior_rounds():
    conversation_messages = [
        {
            "role": "assistant",
            "metadata": {
                "responded_council_models": ["model-a", "model-b"],
                "aggregate_rankings": [
                    {"model": "model-a", "average_rank": 1.0},
                    {"model": "model-b", "average_rank": 2.0},
                ],
            },
        },
    ]

    profiles = council.build_model_weight_profile(
        conversation_messages,
        ["model-a", "model-b", "model-c"],
    )

    assert profiles["model-a"]["rounds_observed"] == 1
    assert profiles["model-a"]["average_performance"] == 1.0
    assert profiles["model-a"]["dynamic_weight"] == 1.5
    assert profiles["model-b"]["average_performance"] == 0.0
    assert profiles["model-b"]["dynamic_weight"] == 0.5
    assert profiles["model-c"]["rounds_observed"] == 0
    assert profiles["model-c"]["dynamic_weight"] == 1.0


@pytest.mark.asyncio
async def test_stage2_collect_rankings_heterogeneous_adds_confidence_and_weights():
    mocked_responses = {
        "model-a": {
            "content": "Analysis\nFINAL RANKING:\n1. Response A\n2. Response B\nCONFIDENCE: 80"
        },
        "model-b": {
            "content": "Analysis\nFINAL RANKING:\n1. Response B\n2. Response A\nCONFIDENCE: 60"
        },
    }

    with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel:
        mock_parallel.return_value = mocked_responses

        stage2_results, label_to_model = await council.stage2_collect_rankings(
            "Which answer is best?",
            [
                {"model": "model-a", "response": "Answer A"},
                {"model": "model-b", "response": "Answer B"},
            ],
            council_models=["model-a", "model-b"],
            framework="heterogeneous",
            model_profiles={
                "model-a": {"dynamic_weight": 1.4},
                "model-b": {"dynamic_weight": 0.8},
            },
        )

    assert label_to_model == {"Response A": "model-a", "Response B": "model-b"}
    assert stage2_results[0]["confidence_score"] == 80
    assert stage2_results[0]["historical_weight"] == 1.4
    assert stage2_results[0]["ballot_weight"] == 1.12
    assert stage2_results[1]["confidence_score"] == 60
    assert stage2_results[1]["historical_weight"] == 0.8
    assert stage2_results[1]["ballot_weight"] == 0.48
