
import asyncio
import os
import sys

# Ensure we can import backend
sys.path.append("/Users/ashwath/LocalRepo/GitHub/llm-council")

# Mock environment to ensure NO DATABASE_URL
os.environ["DATABASE_URL"] = ""

from backend import storage

async def test_file_storage():
    print("Testing File Storage Fallback...")
    
    user_id = "test_user_file"
    conv_id = "test_conv_file"
    
    # 1. Create
    print("Creating conversation...")
    conv = await storage.create_conversation(conv_id, user_id, "standard", [], "gpt-4")
    assert conv["id"] == conv_id
    assert conv["origin"] == "local" # Default fallback
    print("Created.")

    # 2. Get
    print("Fetching conversation...")
    fetched = await storage.get_conversation(conv_id, user_id)
    assert fetched["id"] == conv_id
    print("Fetched.")

    # 3. Add Message
    print("Adding message...")
    await storage.add_user_message(conv_id, user_id, "Hello File World")
    fetched_after = await storage.get_conversation(conv_id, user_id)
    assert len(fetched_after["messages"]) == 1
    print("Message added.")

    print("FILE STORAGE TEST PASSED")

if __name__ == "__main__":
    asyncio.run(test_file_storage())
