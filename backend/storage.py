
import json
import os
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.future import select
from sqlalchemy import update, delete, insert
from sqlalchemy.orm.attributes import flag_modified
from .config import DATA_DIR, APP_ORIGIN, DOCUMENTS_DIR
from .database import AsyncSessionLocal, ConversationModel, DocumentModel, DocumentChunkModel, init_db

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
        # Optimization: Only select necessary columns.
        # Dropped message_count as it requires fetching the full JSON body and is unused in the frontend.
        result = await session.execute(
            select(
                ConversationModel.id,
                ConversationModel.created_at,
                ConversationModel.title,
                ConversationModel.framework
            )
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
        )
        conversations = result.all()
        return [
            {
                "id": c.id,
                "created_at": c.created_at.isoformat(),
                "title": c.title,
                "framework": c.framework,
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

        await session.execute(
            delete(DocumentChunkModel)
            .where(
                DocumentChunkModel.conversation_id == conversation_id,
                DocumentChunkModel.user_id == user_id
            )
        )
        await session.execute(
            delete(DocumentModel)
            .where(
                DocumentModel.conversation_id == conversation_id,
                DocumentModel.user_id == user_id
            )
        )
        
        await session.delete(conv)
        await session.commit()

async def db_create_document(
    conversation_id: str,
    user_id: str,
    filename: str,
    size_bytes: int
) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        doc = DocumentModel(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            user_id=user_id,
            filename=filename,
            size_bytes=size_bytes,
            status="processing",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return _document_to_dict(doc)

async def db_update_document(
    conversation_id: str,
    document_id: str,
    user_id: str,
    **updates: Any
) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentModel)
            .where(
                DocumentModel.id == document_id,
                DocumentModel.conversation_id == conversation_id,
                DocumentModel.user_id == user_id
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError("Unauthorized or not found")

        for key, value in updates.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        doc.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(doc)
        return _document_to_dict(doc)

async def db_list_documents(conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentModel)
            .where(DocumentModel.conversation_id == conversation_id, DocumentModel.user_id == user_id)
            .order_by(DocumentModel.created_at.desc())
        )
        documents = result.scalars().all()
        return [_document_to_dict(doc) for doc in documents]

async def db_add_document_chunks(chunks: List[Dict[str, Any]]):
    if not chunks:
        return

    # Pre-generate IDs and timestamps for bulk insertion
    # Using execute(insert(Model), data) is significantly more efficient than add_all(models)
    # for large bulk inserts as it avoids session object tracking overhead.
    data = [
        {
            "id": str(uuid.uuid4()),
            "document_id": chunk["document_id"],
            "conversation_id": chunk["conversation_id"],
            "user_id": chunk["user_id"],
            "chunk_index": chunk["chunk_index"],
            "page_number": chunk["page_number"],
            "text": chunk["text"],
            "embedding": chunk["embedding"],
            "created_at": datetime.utcnow()
        }
        for chunk in chunks
    ]

    async with AsyncSessionLocal() as session:
        data = [
            {
                "id": str(uuid.uuid4()),
                "document_id": chunk["document_id"],
                "conversation_id": chunk["conversation_id"],
                "user_id": chunk["user_id"],
                "chunk_index": chunk["chunk_index"],
                "page_number": chunk["page_number"],
                "text": chunk["text"],
                "embedding": chunk["embedding"],
                "created_at": datetime.utcnow()
            }
            for chunk in chunks
        ]
        await session.execute(insert(DocumentChunkModel), data)
        await session.commit()

async def db_list_document_chunks(conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.conversation_id == conversation_id, DocumentChunkModel.user_id == user_id)
        )
        chunks = result.scalars().all()
        return [_chunk_to_dict(chunk) for chunk in chunks]

async def db_list_document_embeddings(conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        # Optimization: Fetch only ID and embedding (and minimal metadata) to avoid fetching large text fields.
        # Using Core Select also bypasses ORM model instantiation overhead.
        result = await session.execute(
            select(
                DocumentChunkModel.id,
                DocumentChunkModel.document_id,
                DocumentChunkModel.embedding,
                DocumentChunkModel.page_number
            )
            .where(DocumentChunkModel.conversation_id == conversation_id, DocumentChunkModel.user_id == user_id)
        )
        return [
            {
                "id": row.id,
                "document_id": row.document_id,
                "embedding": row.embedding,
                "page_number": row.page_number
            }
            for row in result.all()
        ]

async def db_get_document_chunks_by_ids(conversation_id: str, user_id: str, chunk_ids: List[str]) -> List[Dict[str, Any]]:
    if not chunk_ids:
        return []
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentChunkModel)
            .where(
                DocumentChunkModel.conversation_id == conversation_id,
                DocumentChunkModel.user_id == user_id,
                DocumentChunkModel.id.in_(chunk_ids)
            )
        )
        chunks = result.scalars().all()
        # Note: SQL IN clause does not guarantee order.
        # The caller (retrieval) will re-sort or map by ID.
        return [_chunk_to_dict(chunk) for chunk in chunks]

async def db_delete_document(conversation_id: str, document_id: str, user_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DocumentModel)
            .where(
                DocumentModel.id == document_id,
                DocumentModel.conversation_id == conversation_id,
                DocumentModel.user_id == user_id
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError("Unauthorized or not found")

        await session.execute(
            delete(DocumentChunkModel)
            .where(
                DocumentChunkModel.document_id == document_id,
                DocumentChunkModel.conversation_id == conversation_id,
                DocumentChunkModel.user_id == user_id
            )
        )
        await session.delete(doc)
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

def _document_to_dict(model: DocumentModel) -> Dict[str, Any]:
    return {
        "id": model.id,
        "conversation_id": model.conversation_id,
        "user_id": model.user_id,
        "filename": model.filename,
        "size_bytes": model.size_bytes,
        "page_count": model.page_count,
        "status": model.status,
        "error_message": model.error_message,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
    }

def _chunk_to_dict(model: DocumentChunkModel) -> Dict[str, Any]:
    return {
        "id": model.id,
        "document_id": model.document_id,
        "conversation_id": model.conversation_id,
        "user_id": model.user_id,
        "chunk_index": model.chunk_index,
        "page_number": model.page_number,
        "text": model.text,
        "embedding": model.embedding,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }

# --- File Storage (Legacy Fallback) ---

def ensure_data_dir():
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

def get_conversation_path(conversation_id: str) -> str:
    # Security: Prevent path traversal
    # conversation_id should be a UUID or simple alphanumeric string
    base = os.path.basename(conversation_id)
    if base != conversation_id or ".." in conversation_id:
        raise ValueError("Invalid conversation ID")
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
    documents_path = get_documents_path(conversation_id)
    if os.path.exists(documents_path):
        os.remove(documents_path)

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
                        })
            except Exception: continue
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations

# --- File Document Storage ---

def ensure_documents_dir():
    Path(DOCUMENTS_DIR).mkdir(parents=True, exist_ok=True)

def get_documents_path(conversation_id: str) -> str:
    base = os.path.basename(conversation_id)
    if base != conversation_id or ".." in conversation_id:
        raise ValueError("Invalid conversation ID")
    return os.path.join(DOCUMENTS_DIR, f"{conversation_id}.json")

def load_documents_bundle(conversation_id: str) -> Dict[str, Any]:
    ensure_documents_dir()
    path = get_documents_path(conversation_id)
    if not os.path.exists(path):
        return {"documents": [], "chunks": []}
    with open(path, 'r') as f:
        data = json.load(f)
        if "documents" not in data or "chunks" not in data:
            return {"documents": [], "chunks": []}
        return data

def save_documents_bundle(conversation_id: str, bundle: Dict[str, Any]):
    ensure_documents_dir()
    path = get_documents_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(bundle, f, indent=2)

def file_create_document(conversation_id: str, user_id: str, filename: str, size_bytes: int) -> Dict[str, Any]:
    bundle = load_documents_bundle(conversation_id)
    now = datetime.utcnow().isoformat()
    document = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "user_id": user_id,
        "filename": filename,
        "size_bytes": size_bytes,
        "page_count": None,
        "status": "processing",
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }
    bundle["documents"].append(document)
    save_documents_bundle(conversation_id, bundle)
    return document

def file_update_document(conversation_id: str, document_id: str, user_id: str, **updates: Any) -> Dict[str, Any]:
    bundle = load_documents_bundle(conversation_id)
    documents = bundle.get("documents", [])
    for doc in documents:
        if doc.get("id") == document_id and doc.get("user_id") == user_id:
            for key, value in updates.items():
                if key in doc:
                    doc[key] = value
            doc["updated_at"] = datetime.utcnow().isoformat()
            save_documents_bundle(conversation_id, bundle)
            return doc
    raise ValueError("Unauthorized or not found")

def file_list_documents(conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
    bundle = load_documents_bundle(conversation_id)
    documents = [
        doc for doc in bundle.get("documents", [])
        if doc.get("user_id") == user_id
    ]
    documents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return documents

def file_add_document_chunks(conversation_id: str, user_id: str, chunks: List[Dict[str, Any]]):
    if not chunks:
        return
    bundle = load_documents_bundle(conversation_id)
    for chunk in chunks:
        if chunk.get("user_id") != user_id:
            continue
        bundle["chunks"].append(chunk)
    save_documents_bundle(conversation_id, bundle)

def file_list_document_chunks(conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
    bundle = load_documents_bundle(conversation_id)
    return [
        chunk for chunk in bundle.get("chunks", [])
        if chunk.get("user_id") == user_id
    ]

def file_list_document_embeddings(conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
    bundle = load_documents_bundle(conversation_id)
    return [
        {
            "id": chunk.get("id"),
            "document_id": chunk.get("document_id"),
            "embedding": chunk.get("embedding"),
            "page_number": chunk.get("page_number")
        }
        for chunk in bundle.get("chunks", [])
        if chunk.get("user_id") == user_id
    ]

def file_get_document_chunks_by_ids(conversation_id: str, user_id: str, chunk_ids: List[str]) -> List[Dict[str, Any]]:
    bundle = load_documents_bundle(conversation_id)
    chunk_ids_set = set(chunk_ids)
    return [
        chunk for chunk in bundle.get("chunks", [])
        if chunk.get("user_id") == user_id and chunk.get("id") in chunk_ids_set
    ]

def file_delete_document(conversation_id: str, document_id: str, user_id: str):
    bundle = load_documents_bundle(conversation_id)
    documents = bundle.get("documents", [])
    chunks = bundle.get("chunks", [])
    new_documents = [doc for doc in documents if not (doc.get("id") == document_id and doc.get("user_id") == user_id)]
    if len(new_documents) == len(documents):
        raise ValueError("Unauthorized or not found")
    bundle["documents"] = new_documents
    bundle["chunks"] = [chunk for chunk in chunks if chunk.get("document_id") != document_id]
    save_documents_bundle(conversation_id, bundle)

# --- Unified Public Interface ---

# We need to handle async for DB but sync for Files. 
# To allow main.py (which calls these as synchronous/async mixed), we generally need to make
# the storage interface async-compatible.
# However, `main.py` currently calls `storage.get_conversation(...)` which was SYNC.
# If we switch to DB, we MUST make these functions async.
# This means we need to refactor `main.py` to `await` storage calls.

async def create_conversation(conversation_id: str, user_id: str, framework: str = "standard", council_models: list = None, chairman_model: str = None):
    if os.getenv("DATABASE_URL"):
        return await db_create_conversation(user_id, conversation_id, framework, council_models, chairman_model)
    else:
        return file_create_conversation(conversation_id, user_id, framework, council_models, chairman_model)

async def get_conversation(conversation_id: str, user_id: str):
    if os.getenv("DATABASE_URL"):
        return await db_get_conversation(conversation_id, user_id)
    else:
        return file_get_conversation(conversation_id, user_id)

async def list_conversations(user_id: str):
    if os.getenv("DATABASE_URL"):
        return await db_list_conversations(user_id)
    else:
        return file_list_conversations(user_id)

async def add_user_message(conversation_id: str, user_id: str, content: str):
    if os.getenv("DATABASE_URL"):
        await db_add_message(conversation_id, user_id, {"role": "user", "content": content})
    else:
        # Fallback to file - read, update, save
        conv = file_get_conversation(conversation_id, user_id)
        if not conv: raise ValueError("Not found")
        conv["messages"].append({"role": "user", "content": content})
        file_save_conversation(conv)

async def add_assistant_message(conversation_id: str, user_id: str, stage1, stage2, stage3, metadata: Optional[Dict[str, Any]] = None):
    message = {
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    }
    if metadata is not None:
        message["metadata"] = metadata
    if os.getenv("DATABASE_URL"):
        await db_add_message(conversation_id, user_id, message)
    else:
        conv = file_get_conversation(conversation_id, user_id)
        if not conv: raise ValueError("Not found")
        conv["messages"].append(message)
        file_save_conversation(conv)

async def update_conversation_title(conversation_id: str, user_id: str, title: str):
    if os.getenv("DATABASE_URL"):
        await db_update_title(conversation_id, user_id, title)
    else:
        conv = file_get_conversation(conversation_id, user_id)
        if not conv: raise ValueError("Not found")
        conv["title"] = title
        file_save_conversation(conv)

async def delete_conversation(conversation_id: str, user_id: str):
    if os.getenv("DATABASE_URL"):
        await db_delete_conversation(conversation_id, user_id)
    else:
        file_delete_conversation(conversation_id, user_id)

async def create_document(conversation_id: str, user_id: str, filename: str, size_bytes: int):
    if os.getenv("DATABASE_URL"):
        return await db_create_document(conversation_id, user_id, filename, size_bytes)
    else:
        return file_create_document(conversation_id, user_id, filename, size_bytes)

async def update_document(conversation_id: str, document_id: str, user_id: str, **updates: Any):
    if os.getenv("DATABASE_URL"):
        return await db_update_document(conversation_id, document_id, user_id, **updates)
    else:
        return file_update_document(conversation_id, document_id, user_id, **updates)

async def list_documents(conversation_id: str, user_id: str):
    if os.getenv("DATABASE_URL"):
        return await db_list_documents(conversation_id, user_id)
    else:
        return file_list_documents(conversation_id, user_id)

async def add_document_chunks(conversation_id: str, user_id: str, chunks: List[Dict[str, Any]]):
    if os.getenv("DATABASE_URL"):
        await db_add_document_chunks(chunks)
    else:
        file_add_document_chunks(conversation_id, user_id, chunks)

async def list_document_chunks(conversation_id: str, user_id: str):
    if os.getenv("DATABASE_URL"):
        return await db_list_document_chunks(conversation_id, user_id)
    else:
        return file_list_document_chunks(conversation_id, user_id)

async def list_document_embeddings(conversation_id: str, user_id: str):
    if os.getenv("DATABASE_URL"):
        return await db_list_document_embeddings(conversation_id, user_id)
    else:
        return file_list_document_embeddings(conversation_id, user_id)

async def get_document_chunks_by_ids(conversation_id: str, user_id: str, chunk_ids: List[str]):
    if os.getenv("DATABASE_URL"):
        return await db_get_document_chunks_by_ids(conversation_id, user_id, chunk_ids)
    else:
        return file_get_document_chunks_by_ids(conversation_id, user_id, chunk_ids)

async def delete_document(conversation_id: str, document_id: str, user_id: str):
    if os.getenv("DATABASE_URL"):
        await db_delete_document(conversation_id, document_id, user_id)
    else:
        file_delete_document(conversation_id, document_id, user_id)
