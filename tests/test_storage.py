
import pytest
import os
import shutil
from backend import storage, config

# Use a temporary directory for test data
TEST_DATA_DIR = "tests/data_temp"

@pytest.fixture(autouse=True)
def setup_teardown_storage(monkeypatch):
    """Setup and teardown test data directory."""
    # Force file mode
    monkeypatch.setenv("DATABASE_URL", "")

    # Use monkeypatch.setattr for clean state management
    monkeypatch.setattr(config, "DATA_DIR", TEST_DATA_DIR)
    monkeypatch.setattr(config, "DOCUMENTS_DIR", os.path.join(TEST_DATA_DIR, "documents"))
    monkeypatch.setattr(config, "DATABASE_URL", "")
    
    monkeypatch.setattr(storage, "DATA_DIR", TEST_DATA_DIR)
    monkeypatch.setattr(storage, "DOCUMENTS_DIR", os.path.join(TEST_DATA_DIR, "documents"))
    
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    os.makedirs(TEST_DATA_DIR)
    os.makedirs(os.path.join(TEST_DATA_DIR, "documents"))
    
    yield
    
    # Teardown
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)

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
