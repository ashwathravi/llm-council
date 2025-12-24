import asyncio
import uuid
from backend.storage import create_conversation, get_conversation
from backend.database import init_db

async def test_persistence():
    await init_db()
    
    cid = str(uuid.uuid4())
    user_id = "test_user_123"
    models = ["model_a", "model_b", "model_c"]
    
    print(f"Creating conversation with models: {models}")
    await create_conversation(cid, user_id, "standard", models, "chairman_x")
    
    conv = await get_conversation(cid, user_id)
    saved_models = conv.get("council_models")
    print(f"Retrieved models: {saved_models}")
    
    if saved_models == models:
        print("SUCCESS: Models persisted correctly.")
    else:
        print("FAILURE: Models mismatch.")

if __name__ == "__main__":
    asyncio.run(test_persistence())
