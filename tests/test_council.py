
import pytest
from unittest.mock import patch, AsyncMock
from backend import council

@pytest.mark.asyncio
async def test_stage1_standard():
    # query_models_parallel returns a Dict[model_id, response_dict]
    mock_responses = {
        "gpt-4": {"content": "Response A"},
        "claude-3": {"content": "Response B"}
    }
    
    with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_responses
        
        results = await council.stage1_collect_responses(
            "What is AI?", 
            council_models=["gpt-4", "claude-3"]
        )
        
        # stage1_collect_responses returns List[Dict] with 'model' and 'response' keys
        assert len(results) == 2
        
        # Verify content mapping
        models_found = sorted([r['model'] for r in results])
        assert models_found == ["claude-3", "gpt-4"]
        
        mock_query.assert_called_once()


@pytest.mark.asyncio
async def test_stage3_synthesis():
    mock_response = {"content": "Final Answer"}
    
    # stage3 calls query_model (singular) for the chairman
    with patch("backend.council.query_model", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_response
        
        result = await council.stage3_synthesize_final(
            "Query",
            [{"model": "gpt-4", "response": "Resp"}], # stage1 results format
            [], # stage2 results
            "chairman-model"
        )
        
        # returns Dict with 'model' and 'response'
        assert result["response"] == "Final Answer"
        mock_query.assert_called_once()
