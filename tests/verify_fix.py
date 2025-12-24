
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock

# Add the repository root to sys.path to allow imports
sys.path.append("/Users/ashwath/LocalRepo/GitHub/llm-council")

from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import create_access_token

# Mock the OpenRouter calls to avoid real network requests and costs
def mock_openrouter_response(models, messages, *args, **kwargs):
    # Return a dummy response for each model
    results = {}
    if isinstance(models, list):
        for m in models:
            results[m] = {"content": f"Mock response from {m}"}
    else:
        # Single model call
        return {"content": f"Mock response from {models}"}
    return results

def mock_single_model_response(model, messages, *args, **kwargs):
    return {"content": f"Mock response from {model}"}

# Create a valid token for a dummy user
user_id = "test_user_123"
token = create_access_token({"sub": user_id})
headers = {"Authorization": f"Bearer {token}"}

client = TestClient(app)

print(f"Generated test token: {token[:10]}...")

# 1. Create a conversation with CUSTOM models
custom_models = ["openai/gpt-4", "anthropic/claude-3-opus"]
chairman = "google/gemini-pro"

print("\n--- Creating Conversation with Custom Models ---")
response = client.post(
    "/api/conversations",
    json={
        "framework": "standard",
        "council_models": custom_models,
        "chairman_model": chairman
    },
    headers=headers
)

if response.status_code != 200:
    print(f"FAILED to create conversation: {response.text}")
    sys.exit(1)

conversation = response.json()
conv_id = conversation["id"]
print(f"Conversation created: {conv_id}")
print(f"Stored Council Models: {conversation.get('council_models')}")
print(f"Stored Chairman Model: {conversation.get('chairman_model')}")

# Verify storage
if conversation.get("council_models") != custom_models:
    print("ERROR: Council models not saved correctly!")
    sys.exit(1)

# 2. Send a message and check if the custom models are used
# We mock utils that call the API
print("\n--- Sending Message & Verifying Mock Calls ---")

# We patch queries in backend.council, NOT main, because main imports functions from council
# references inside council.py are resolved at import time usually.
# However, run_full_council calls query_models_parallel from council.py.
# We need to patch 'backend.council.query_models_parallel' and 'backend.council.query_model'

with patch('backend.council.query_models_parallel', side_effect=mock_openrouter_response) as mock_parallel:
    with patch('backend.council.query_model', side_effect=mock_single_model_response) as mock_single:
        
        msg_response = client.post(
            f"/api/conversations/{conv_id}/message",
            json={"content": "Hello test"},
            headers=headers
        )

        if msg_response.status_code != 200:
            print(f"FAILED to send message: {msg_response.text}")
            sys.exit(1)

        result = msg_response.json()
        
        # 3. Check what models were actually called
        # mock_parallel.call_args[0] should be (models_list, messages)
        called_args = mock_parallel.call_args
        if not called_args:
             # It might be called multiple times (stage 1, stage 2)
             # Let's check call_args_list
             print("Mock was not called!")
             sys.exit(1)
        
        print("\n--- Verifying Calls ---")
        
        # Check Stage 1 call
        # The first call to parallel should be Stage 1 with our custom models
        stage1_call = mock_parallel.call_args_list[0]
        called_models = stage1_call[0][0] # first arg
        
        print(f"Stage 1 called with models: {called_models}")
        
        if sorted(called_models) == sorted(custom_models):
            print("SUCCESS: Custom models were passed to Stage 1!")
        else:
            print(f"FAILURE: Expected {custom_models}, got {called_models}")
            sys.exit(1)
            
        # Check Metadata
        meta_council = result['metadata']['council_models']
        print(f"Response Metadata Council: {meta_council}")
        
        if sorted(meta_council) == sorted(custom_models):
             print("SUCCESS: Response metadata reflects custom models!")
        else:
             print("FAILURE: Metadata mismatch.")
             sys.exit(1)

print("\nALL VERIFICATIONS PASSED")
