
import time
import asyncio
import numpy as np
from typing import List, Dict, Any

# Mock implementation of current logic
def _dot_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    return sum(a * b for a, b in zip(vec_a, vec_b))

async def measure_current(n_chunks=10000, dim=384):
    print(f"Measuring current implementation with {n_chunks} chunks, {dim} dimensions...")

    # Generate mock data
    query_embedding = np.random.rand(dim).tolist()
    chunks = [
        {
            "id": f"chunk_{i}",
            "embedding": np.random.rand(dim).tolist(),
            "text": "x" * 1000, # Simulate 1KB text
        }
        for i in range(n_chunks)
    ]

    start_time = time.time()

    # Current Logic
    scored_chunks = []
    for chunk in chunks:
        embedding = chunk.get("embedding")
        if not embedding:
            continue
        score = _dot_similarity(query_embedding, embedding)
        scored_chunks.append({**chunk, "score": score})

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_k = scored_chunks[:5]

    end_time = time.time()
    print(f"Current implementation took: {end_time - start_time:.4f} seconds")
    return end_time - start_time

async def measure_optimized(n_chunks=10000, dim=384):
    print(f"Measuring optimized implementation with {n_chunks} chunks, {dim} dimensions...")

    # Generate mock data
    query_embedding = np.random.rand(dim).tolist()
    # Simulate separate fetching: embeddings first, then text
    embeddings = [
        {
            "id": f"chunk_{i}",
            "embedding": np.random.rand(dim).tolist(),
        }
        for i in range(n_chunks)
    ]
    # Dict to simulate DB lookup for text
    chunk_text_store = {
        f"chunk_{i}": "x" * 1000
        for i in range(n_chunks)
    }

    start_time = time.time()

    # Optimized Logic
    # 1. Convert to numpy
    q = np.array(query_embedding, dtype=np.float32)
    # Extract embeddings matrix
    # Note: Creating numpy array from list of lists is costly. In real app, we get list of lists from DB/JSON.
    E = np.array([c["embedding"] for c in embeddings], dtype=np.float32)

    # 2. Compute scores
    scores = E @ q

    # 3. Top K
    # using argpartition for O(N) instead of sort O(N log N)
    k = 5
    if len(scores) > k:
        # np.argpartition is significantly faster for finding top k
        top_indices = np.argpartition(scores, -k)[-k:]
        # sort the top k
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
    else:
        top_indices = np.argsort(scores)[::-1]

    top_ids = [embeddings[i]["id"] for i in top_indices]

    # 4. Fetch text (simulate DB lookup)
    # Here we simulate fetching from DB by list comprehension or batch get
    top_chunks = []
    for i, idx in enumerate(top_indices):
        chunk_id = embeddings[idx]["id"]
        # In real DB, we would do one query: SELECT * FROM chunks WHERE id IN (...)
        # Simulating overhead of result construction
        text = chunk_text_store[chunk_id]
        top_chunks.append({
            "id": chunk_id,
            "score": float(scores[idx]),
            "text": text
        })

    end_time = time.time()
    print(f"Optimized implementation took: {end_time - start_time:.4f} seconds")
    return end_time - start_time

async def main():
    await measure_current()
    await measure_optimized()

if __name__ == "__main__":
    asyncio.run(main())
