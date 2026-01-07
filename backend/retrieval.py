"""Retrieval helpers for document context."""

from __future__ import annotations

from typing import List, Dict, Any, Tuple

from . import storage, documents
from .config import RETRIEVAL_TOP_K, RETRIEVAL_MAX_TOTAL_CHARS, RETRIEVAL_MAX_CHARS_PER_CHUNK


def _dot_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    return sum(a * b for a, b in zip(vec_a, vec_b))


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

        chunks = await storage.list_document_chunks(conversation_id, user_id)
        if not chunks:
            return None, []

        documents_list = await storage.list_documents(conversation_id, user_id)
        document_name_map = {doc.get("id"): doc.get("filename") for doc in documents_list}

        query_embedding = documents.embed_texts([query])[0]
        scored_chunks = []
        for chunk in chunks:
            embedding = chunk.get("embedding")
            if not embedding:
                continue
            score = _dot_similarity(query_embedding, embedding)
            scored_chunks.append({**chunk, "score": score})

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)

        citations: List[Dict[str, Any]] = []
        total_chars = 0
        for chunk in scored_chunks[:RETRIEVAL_TOP_K]:
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
        print(f"Retrieval error: {e}")
        return None, []
