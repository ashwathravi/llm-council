
import os
import ssl
from datetime import datetime
from typing import List, Optional, Any, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON, text, Integer, Text
from .config import DATABASE_URL

# --- Database Setup ---

# Declarative Base
class Base(DeclarativeBase):
    pass

# Schema Definition
class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, default="New Conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    framework: Mapped[str] = mapped_column(String, default="standard")
    
    # JSONB columns for flexible storage
    council_models: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    chairman_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    messages: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    
    # Origin tracking
    origin: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="processing")
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DocumentChunkModel(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    conversation_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[List[float]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Engine and Session
# Only create engine if DATABASE_URL is set
engine = None
AsyncSessionLocal = None

from sqlalchemy.engine.url import make_url

if DATABASE_URL:
    # Handle Render's postgres:// format
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Parse the URL
    url_obj = make_url(DATABASE_URL)
    
    # Clean up sslmode in query params (asyncpg doesn't support it in DSN)
    query_params = dict(url_obj.query)
    
    # Disable prepared statement caching for connection poolers (PgBouncer/Supabase)
    connect_args = {"statement_cache_size": 0}
    
    if "sslmode" in query_params:
        ssl_mode = query_params.pop("sslmode")
        if ssl_mode == "require" or ssl_mode == "verify-full":
            # Create a custom SSL context to avoid certificate verification errors
            # which are common in some deployment environments
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ssl_context
    
    # Reconstruct URL without the incompatible query params
    url_obj = url_obj._replace(query=query_params)
    
    engine = create_async_engine(
        url_obj, 
        echo=False,
        connect_args=connect_args,
        pool_pre_ping=True
    )
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    """Create tables if they don't exist."""
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

async def get_db_session():
    """Dependency for getting async session."""
    if not AsyncSessionLocal:
        yield None
        return
        
    async with AsyncSessionLocal() as session:
        yield session
