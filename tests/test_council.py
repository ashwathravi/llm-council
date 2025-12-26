
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
