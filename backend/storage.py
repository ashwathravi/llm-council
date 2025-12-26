
import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.orm.attributes import flag_modified
from .config import DATA_DIR, DATABASE_URL, APP_ORIGIN
from .database import AsyncSessionLocal, ConversationModel, init_db

# --- Database Storage Helpers ---

async def db_create_conversation(user_id: str, conversation_id: str, framework: str, council_models: list, chairman_model: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        new_conv = ConversationModel(
            id=conversation_id,
            user_id=user_id,
            framework=framework,
            council_models=council_models,
            chairman_model=chairman_model,
            origin=APP_ORIGIN,
            messages=[]
        )
        session.add(new_conv)
        await session.commit()
        await session.refresh(new_conv)
        return _model_to_dict(new_conv)

async def db_get_conversation(conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ConversationModel).where(ConversationModel.id == conversation_id))
        conv = result.scalar_one_or_none()
        if conv and conv.user_id == user_id:
            return _model_to_dict(conv)
        return None

async def db_list_conversations(user_id: str) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
        )
        conversations = result.scalars().all()
        return [
            {
                "id": c.id,
                "created_at": c.created_at.isoformat(),
                "title": c.title,
                "framework": c.framework,
                "message_count": len(c.messages) # This might be heavy if messages are huge, but fine for now
            }
            for c in conversations
        ]

async def db_add_message(conversation_id: str, user_id: str, message: Dict[str, Any]):
    async with AsyncSessionLocal() as session:
        # Fetch current to verify auth and append
        result = await session.execute(select(ConversationModel).where(ConversationModel.id == conversation_id))
        conv = result.scalar_one_or_none()
        if not conv or conv.user_id != user_id:
            raise ValueError(f"Conversation {conversation_id} not found or unauthorized")
        
        # SQLAlchemy doesn't track mutation of JSON contents automatically easily
        # We need to re-assign the list
        current_msgs = list(conv.messages)
        current_msgs.append(message)
        conv.messages = current_msgs
        
        # Explicitly flag as modified to ensure persistence
        flag_modified(conv, "messages")
        
        await session.commit()

async def db_update_title(conversation_id: str, user_id: str, title: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ConversationModel).where(ConversationModel.id == conversation_id))
        conv = result.scalar_one_or_none()
        if not conv or conv.user_id != user_id:
            raise ValueError("Unauthorized")
        
        conv.title = title
        await session.commit()

async def db_delete_conversation(conversation_id: str, user_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ConversationModel).where(ConversationModel.id == conversation_id))
        conv = result.scalar_one_or_none()
        if not conv or conv.user_id != user_id:
            raise ValueError("Unauthorized or not found")
        
        await session.delete(conv)
        await session.commit()

def _model_to_dict(model: ConversationModel) -> Dict[str, Any]:
    return {
        "id": model.id,
        "user_id": model.user_id,
        "created_at": model.created_at.isoformat(),
        "title": model.title,
        "framework": model.framework,
        "council_models": model.council_models,
        "chairman_model": model.chairman_model,
        "messages": model.messages,
        "origin": model.origin
    }

# --- File Storage (Legacy Fallback) ---

def ensure_data_dir():
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

def get_conversation_path(conversation_id: str) -> str:
    return os.path.join(DATA_DIR, f"{conversation_id}.json")

def file_create_conversation(conversation_id: str, user_id: str, framework: str, council_models: list, chairman_model: str) -> Dict[str, Any]:
    ensure_data_dir()
    conversation = {
        "id": conversation_id,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "framework": framework,
        "council_models": council_models,
        "chairman_model": chairman_model,
        "messages": [],
        "origin": APP_ORIGIN
    }
    with open(get_conversation_path(conversation_id), 'w') as f:
        json.dump(conversation, f, indent=2)
    return conversation

def file_get_conversation(conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    path = get_conversation_path(conversation_id)
    if not os.path.exists(path): return None
    with open(path, 'r') as f:
        data = json.load(f)
        if data.get("user_id") != user_id: return None
        return data

def file_save_conversation(conversation: Dict[str, Any]):
    ensure_data_dir()
    with open(get_conversation_path(conversation['id']), 'w') as f:
        json.dump(conversation, f, indent=2)

def file_delete_conversation(conversation_id: str, user_id: str):
    path = get_conversation_path(conversation_id)
    if not os.path.exists(path):
        raise ValueError("Not found")
    
    # Check ownership first
    with open(path, 'r') as f:
        data = json.load(f)
        if data.get("user_id") != user_id:
             raise ValueError("Unauthorized")
    
    os.remove(path)

def file_list_conversations(user_id: str) -> List[Dict[str, Any]]:
    ensure_data_dir()
    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(DATA_DIR, filename), 'r') as f:
                    data = json.load(f)
                    if data.get("user_id") == user_id:
                        conversations.append({
                            "id": data["id"],
                            "created_at": data["created_at"],
                            "title": data.get("title", "New Conversation"),
                            "framework": data.get("framework", "standard"),
                            "message_count": len(data["messages"])
                        })
            except Exception: continue
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations

# --- Unified Public Interface ---

# We need to handle async for DB but sync for Files. 
# To allow main.py (which calls these as synchronous/async mixed), we generally need to make
# the storage interface async-compatible.
# However, `main.py` currently calls `storage.get_conversation(...)` which was SYNC.
# If we switch to DB, we MUST make these functions async.
# This means we need to refactor `main.py` to `await` storage calls.

async def create_conversation(conversation_id: str, user_id: str, framework: str = "standard", council_models: list = None, chairman_model: str = None):
    if DATABASE_URL:
        return await db_create_conversation(user_id, conversation_id, framework, council_models, chairman_model)
    else:
        return file_create_conversation(conversation_id, user_id, framework, council_models, chairman_model)

async def get_conversation(conversation_id: str, user_id: str):
    if DATABASE_URL:
        return await db_get_conversation(conversation_id, user_id)
    else:
        return file_get_conversation(conversation_id, user_id)

async def list_conversations(user_id: str):
    if DATABASE_URL:
        return await db_list_conversations(user_id)
    else:
        return file_list_conversations(user_id)

async def add_user_message(conversation_id: str, user_id: str, content: str):
    if DATABASE_URL:
        await db_add_message(conversation_id, user_id, {"role": "user", "content": content})
    else:
        # Fallback to file - read, update, save
        conv = file_get_conversation(conversation_id, user_id)
        if not conv: raise ValueError("Not found")
        conv["messages"].append({"role": "user", "content": content})
        file_save_conversation(conv)

async def add_assistant_message(conversation_id: str, user_id: str, stage1, stage2, stage3):
    message = {
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    }
    if DATABASE_URL:
        await db_add_message(conversation_id, user_id, message)
    else:
        conv = file_get_conversation(conversation_id, user_id)
        if not conv: raise ValueError("Not found")
        conv["messages"].append(message)
        file_save_conversation(conv)

async def update_conversation_title(conversation_id: str, user_id: str, title: str):
    if DATABASE_URL:
        await db_update_title(conversation_id, user_id, title)
    else:
        conv = file_get_conversation(conversation_id, user_id)
        if not conv: raise ValueError("Not found")
        conv["title"] = title
        file_save_conversation(conv)

async def delete_conversation(conversation_id: str, user_id: str):
    if DATABASE_URL:
        await db_delete_conversation(conversation_id, user_id)
    else:
        file_delete_conversation(conversation_id, user_id)
