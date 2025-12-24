
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

async def test_multiturn_flow():
    """
    Verify that run_full_council receives message history.
    """
    from backend import council
    
    # Mock query_models_parallel to verify inputs
    mock_responses = {"test-model": {"content": "I am a test model response."}}
    
    council.query_models_parallel = AsyncMock(return_value=mock_responses)
    council.stage2_collect_rankings = AsyncMock(return_value=([], {}))
    # Mock stage2_collect_critiques just in case
    council.stage2_collect_critiques = AsyncMock(return_value=([], {}))
    # Mock stage3_synthesize_final
    council.stage3_synthesize_final = AsyncMock(return_value={"model": "chairman", "response": "Final Answer"})

    # define history 
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "What did I just say?"}
    ]
    
    print("Running run_full_council with history...")
    await council.run_full_council(
        messages,
        framework="standard",
        council_models=["test-model"],
        chairman_model="chairman"
    )
    
    # Check if query_models_parallel was called with full history
    call_args = council.query_models_parallel.call_args
    if call_args:
        models, msgs = call_args[0]
        print(f"Called with messages: {msgs}")
        if len(msgs) == 3 and msgs[0]['content'] == "Hello":
             print("SUCCESS: Full history passed to Council!")
        else:
             print("FAILURE: History mismatch.")
    else:
        print("FAILURE: query_models_parallel not called.")

if __name__ == "__main__":
    asyncio.run(test_multiturn_flow())
