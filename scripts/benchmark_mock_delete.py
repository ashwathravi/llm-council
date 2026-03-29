
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Mocking the models for the benchmark using SQLAlchemy DeclarativeBase
class Base(DeclarativeBase):
    pass

class DocumentModel(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column()
    user_id: Mapped[str] = mapped_column()

class DocumentChunkModel(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column()
    conversation_id: Mapped[str] = mapped_column()
    user_id: Mapped[str] = mapped_column()

LATENCY = 0.01  # 10ms simulated latency per DB roundtrip

async def simulated_delay(*args, **kwargs):
    await asyncio.sleep(LATENCY)

async def mock_execute(statement, *args, **kwargs):
    await asyncio.sleep(LATENCY)
    mock_result = MagicMock()
    # If it's a select, return a mock object
    if "SELECT" in str(statement).upper():
        mock_result.scalar_one_or_none.return_value = MagicMock()
    # If it's a delete, return rowcount = 1
    elif "DELETE" in str(statement).upper():
        mock_result.rowcount = 1
    return mock_result

async def current_logic(conversation_id, document_id, user_id, session):
    # Roundtrip 1: Select
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

    # Roundtrip 2: Delete Chunks
    await session.execute(
        delete(DocumentChunkModel)
        .where(
            DocumentChunkModel.document_id == document_id,
            DocumentChunkModel.conversation_id == conversation_id,
            DocumentChunkModel.user_id == user_id
        )
    )

    # Roundtrip 3: Delete Document
    await session.delete(doc)
    # Roundtrip 4: Commit
    await session.commit()

async def optimized_logic(conversation_id, document_id, user_id, session):
    # Roundtrip 1: Delete Chunks
    await session.execute(
        delete(DocumentChunkModel)
        .where(
            DocumentChunkModel.document_id == document_id,
            DocumentChunkModel.conversation_id == conversation_id,
            DocumentChunkModel.user_id == user_id
        )
    )

    # Roundtrip 2: Delete Document with rowcount check
    result = await session.execute(
        delete(DocumentModel)
        .where(
            DocumentModel.id == document_id,
            DocumentModel.conversation_id == conversation_id,
            DocumentModel.user_id == user_id
        )
    )

    if result.rowcount == 0:
        await session.rollback()
        raise ValueError("Unauthorized or not found")

    # Roundtrip 3: Commit
    await session.commit()

async def run_benchmark():
    num_iterations = 50
    print(f"Benchmarking with {LATENCY*1000}ms simulated latency...")

    # Benchmark Current
    start = time.perf_counter()
    for _ in range(num_iterations):
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=mock_execute)
        session.commit = AsyncMock(side_effect=simulated_delay)
        session.delete = AsyncMock(side_effect=simulated_delay)
        await current_logic("conv", "doc", "user", session)
    end = time.perf_counter()
    avg_current = (end - start) / num_iterations
    print(f"Current logic avg time: {avg_current:.4f}s")

    # Benchmark Optimized
    start = time.perf_counter()
    for _ in range(num_iterations):
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=mock_execute)
        session.commit = AsyncMock(side_effect=simulated_delay)
        await optimized_logic("conv", "doc", "user", session)
    end = time.perf_counter()
    avg_optimized = (end - start) / num_iterations
    print(f"Optimized logic avg time: {avg_optimized:.4f}s")

    improvement = (avg_current - avg_optimized) / avg_current * 100
    print(f"Improvement: {improvement:.2f}%")
    print(f"Roundtrips saved: {round((avg_current - avg_optimized) / LATENCY)}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
