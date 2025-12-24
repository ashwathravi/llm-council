
import os
from datetime import datetime
from typing import List, Optional, Any, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON, text
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

# Engine and Session
# Only create engine if DATABASE_URL is set
engine = None
AsyncSessionLocal = None

if DATABASE_URL:
    # Ensure usage of asyncpg driver
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
        
    engine = create_async_engine(DATABASE_URL, echo=False)
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
