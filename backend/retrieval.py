"""Retrieval helpers for document context."""

from __future__ import annotations

import numpy as np
from typing import List, Dict, Any, Tuple
from starlette.concurrency import run_in_threadpool

from . import storage, documents
from .config import RETRIEVAL_TOP_K, RETRIEVAL_MAX_TOTAL_CHARS, RETRIEVAL_MAX_CHARS_PER_CHUNK


def _build_context(citations: List[Dict[str, Any]]) -> str:
    if not citations:
        return ""
    lines = [
        "You have access to the following document excerpts.",
        "Use them to answer the user's question and cite sources as [filename p.#].",
        ""
    ]
    for item in citations:
        lines.append(f"Source: {item['filename']} (p. {item['page_number']})")
        lines.append(item["snippet"])
        lines.append("")
    return "\n".join(lines).strip()


async def build_retrieval_context(
    conversation_id: str,
    user_id: str,
    query: str
) -> Tuple[str | None, List[Dict[str, Any]]]:
    try:
        if not query.strip():
            return None, []

        # ⚡ Bolt: Fetch minimal embedding data first to save bandwidth/memory
        chunks_meta = await storage.list_document_embeddings(conversation_id, user_id)
        if not chunks_meta:
            return None, []

        documents_list = await storage.list_documents(conversation_id, user_id)
        document_name_map = {doc.get("id"): doc.get("filename") for doc in documents_list}

        # Offload embedding inference so retrieval does not block the async event loop.
        query_embedding = (await run_in_threadpool(documents.embed_texts, [query]))[0]

        # ⚡ Bolt: Use numpy for vectorized similarity calculation
        # Convert list of embeddings to numpy matrix (N x D)
        # Handle potential None or empty embeddings gracefully
        valid_chunks = [c for c in chunks_meta if c.get("embedding")]
        if not valid_chunks:
            return None, []

        embeddings_matrix = np.array([c["embedding"] for c in valid_chunks], dtype=np.float32)
        query_vec = np.array(query_embedding, dtype=np.float32)

        # Compute dot products (scores)
        scores = np.dot(embeddings_matrix, query_vec)

        # Get top K indices
        # If we have many chunks, argpartition is O(N) vs sort O(N log N)
        k = min(RETRIEVAL_TOP_K, len(scores))
        if k == 0:
             return None, []

        if len(scores) > k:
            top_indices = np.argpartition(scores, -k)[-k:]
            # Sort the top k explicitly
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
        else:
            top_indices = np.argsort(scores)[::-1]

        # Get IDs of top chunks
        top_chunks_meta = [valid_chunks[i] for i in top_indices]
        top_scores = [float(scores[i]) for i in top_indices]

        top_chunk_ids = [c["id"] for c in top_chunks_meta]

        # Fetch full text for top chunks only
        full_chunks = await storage.get_document_chunks_by_ids(conversation_id, user_id, top_chunk_ids)

        # Re-attach scores and sort (as get_document_chunks_by_ids doesn't guarantee order)
        chunk_map = {c["id"]: c for c in full_chunks}
        scored_chunks = []
        for meta, score in zip(top_chunks_meta, top_scores):
            chunk = chunk_map.get(meta["id"])
            if chunk:
                scored_chunks.append({**chunk, "score": score})

        citations: List[Dict[str, Any]] = []
        total_chars = 0
        for chunk in scored_chunks:
            snippet = documents.truncate_text(
                chunk.get("text", ""),
                RETRIEVAL_MAX_CHARS_PER_CHUNK
            )
            if not snippet:
                continue
            if total_chars + len(snippet) > RETRIEVAL_MAX_TOTAL_CHARS and citations:
                break
            total_chars += len(snippet)
            citations.append({
                "document_id": chunk.get("document_id"),
                "filename": document_name_map.get(chunk.get("document_id"), "document"),
                "page_number": chunk.get("page_number"),
                "snippet": snippet,
                "score": round(chunk.get("score", 0.0), 4),
            })

        context = _build_context(citations)
        return (context if context else None), citations
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Retrieval error: {e}")
        return None, []
