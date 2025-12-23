
import pytest
import os
import json
import shutil
from backend import storage, config

# Use a temporary directory for test data
TEST_DATA_DIR = "tests/data_temp"

@pytest.fixture(autouse=True)
def setup_teardown_storage():
    """Setup and teardown test data directory."""
    # Setup
    original_data_dir = config.DATA_DIR
    original_db_url = config.DATABASE_URL
    
    # Force file mode
    config.DATA_DIR = TEST_DATA_DIR
    config.DATABASE_URL = "" 
    # Note: modifying config.DATABASE_URL at runtime might not switch `storage.py` logic 
    # if `storage.py` imported `DATABASE_URL` directly using `from .config import DATABASE_URL`.
    # Let's check storage.py imports.
    # It does: `from .config import DATA_DIR, DATABASE_URL, APP_ORIGIN`
    # So we need to patch `backend.storage.DATABASE_URL` directly.
    
    storage.DATA_DIR = TEST_DATA_DIR
    storage.DATABASE_URL = ""
    
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    os.makedirs(TEST_DATA_DIR)
    
    yield
    
    # Teardown
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    
    # Restore (optional if process dies anyway, but good practice)
    config.DATA_DIR = original_data_dir
    config.DATABASE_URL = original_db_url
    storage.DATA_DIR = original_data_dir
    storage.DATABASE_URL = original_db_url

@pytest.mark.asyncio
async def test_create_and_get_conversation_file():
    user_id = "user_123"
    conv_id = "conv_1"
    
    # Create
    created = await storage.create_conversation(conv_id, user_id, "standard", [], "gpt-4")
    assert created["id"] == conv_id
    assert created["user_id"] == user_id
    assert created["origin"] == "local" # or whatever default
    
    # Verify file exists
    assert os.path.exists(os.path.join(TEST_DATA_DIR, f"{conv_id}.json"))
    
    # Get
    fetched = await storage.get_conversation(conv_id, user_id)
    assert fetched is not None
    assert fetched["id"] == conv_id

@pytest.mark.asyncio
async def test_add_message_file():
    user_id = "user_123"
    conv_id = "conv_2"
    await storage.create_conversation(conv_id, user_id)
    
    await storage.add_user_message(conv_id, user_id, "Hello Test")
    
    fetched = await storage.get_conversation(conv_id, user_id)
    assert len(fetched["messages"]) == 1
    assert fetched["messages"][0]["content"] == "Hello Test"
    assert fetched["messages"][0]["role"] == "user"

@pytest.mark.asyncio
async def test_get_conversation_wrong_user():
    user_1 = "user_1"
    user_2 = "user_2"
    conv_id = "conv_3"
    await storage.create_conversation(conv_id, user_1)
    
    # User 2 tries to get User 1's conversation
    fetched = await storage.get_conversation(conv_id, user_2)
    assert fetched is None
