
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
