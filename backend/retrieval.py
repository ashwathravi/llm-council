"""Retrieval helpers for artifact-aware context."""

from __future__ import annotations

import numpy as np
import logging
import re
from typing import List, Dict, Any, Tuple
from starlette.concurrency import run_in_threadpool

from . import storage, documents, code_artifacts
from .config import RETRIEVAL_TOP_K, RETRIEVAL_MAX_TOTAL_CHARS, RETRIEVAL_MAX_CHARS_PER_CHUNK
from .session_context import normalize_primary_artifacts

logger = logging.getLogger(__name__)
TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")
SYMBOL_RE = re.compile(r"^\s*(?:def|class|function|func|fn|interface|type|struct|enum)\s+([A-Za-z0-9_]+)", re.MULTILINE)

def _build_context(citations: List[Dict[str, Any]]) -> str:
    if not citations:
        return ""
    uses_non_document_sources = any(item.get("artifact_type") not in (None, "document") for item in citations)
    if uses_non_document_sources:
        lines = [
            "You have access to the following artifact excerpts.",
            "Use them to answer the user's question and cite the provided file, page, or line references.",
            ""
        ]
    else:
        lines = [
            "You have access to the following document excerpts.",
            "Use them to answer the user's question and cite sources as [filename p.#].",
            ""
        ]
    for item in citations:
        if item.get("artifact_type") == "code":
            line_start = item.get("line_start")
            line_end = item.get("line_end")
            if line_start and line_end and line_start != line_end:
                source_label = f"Source: {item['filename']} (lines {line_start}-{line_end})"
            elif line_start:
                source_label = f"Source: {item['filename']} (line {line_start})"
            else:
                source_label = f"Source: {item['filename']}"
        elif item.get("artifact_type") == "image":
            source_label = f"Source: {item['filename']} (visual artifact)"
        else:
            source_label = f"Source: {item['filename']} (p. {item['page_number']})"
        lines.append(source_label)
        lines.append(item["snippet"])
        lines.append("")
    return "\n".join(lines).strip()


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if len(token) > 1
    }


def _extract_symbol_names(content: str) -> List[str]:
    return SYMBOL_RE.findall(content or "")


def _chunk_code_artifact(content: str, filename: str, *, chunk_lines: int = 40, overlap_lines: int = 10) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    if not lines:
        return []

    chunks: List[Dict[str, Any]] = []
    step = max(1, chunk_lines - overlap_lines)
    for start in range(0, len(lines), step):
        selected = lines[start:start + chunk_lines]
        if not selected:
            continue
        line_start = start + 1
        line_end = start + len(selected)
        text = "\n".join(selected)
        chunks.append({
            "filename": filename,
            "line_start": line_start,
            "line_end": line_end,
            "text": text,
            "symbols": _extract_symbol_names(text),
        })
        if line_end >= len(lines):
            break
    return chunks


async def _build_document_citations(
    conversation_id: str,
    user_id: str,
    query: str,
) -> List[Dict[str, Any]]:
    chunks_meta = await storage.list_document_embeddings(conversation_id, user_id)
    if not chunks_meta:
        return []

    documents_list = await storage.list_documents(conversation_id, user_id)
    document_name_map = {doc.get("id"): doc.get("filename") for doc in documents_list}

    query_embedding = (await run_in_threadpool(documents.embed_texts, [query]))[0]
    valid_chunks = [c for c in chunks_meta if c.get("embedding")]
    if not valid_chunks:
        return []

    embeddings_matrix = np.array([c["embedding"] for c in valid_chunks], dtype=np.float32)
    query_vec = np.array(query_embedding, dtype=np.float32)
    scores = np.dot(embeddings_matrix, query_vec)

    k = min(RETRIEVAL_TOP_K, len(scores))
    if k == 0:
        return []

    if len(scores) > k:
        top_indices = np.argpartition(scores, -k)[-k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
    else:
        top_indices = np.argsort(scores)[::-1]

    top_chunks_meta = [valid_chunks[i] for i in top_indices]
    top_scores = [float(scores[i]) for i in top_indices]
    top_chunk_ids = [c["id"] for c in top_chunks_meta]

    full_chunks = await storage.get_document_chunks_by_ids(conversation_id, user_id, top_chunk_ids)
    chunk_map = {c["id"]: c for c in full_chunks}
    citations: List[Dict[str, Any]] = []

    for meta, score in zip(top_chunks_meta, top_scores):
        chunk = chunk_map.get(meta["id"])
        if not chunk:
            continue
        snippet = documents.truncate_text(chunk.get("text", ""), RETRIEVAL_MAX_CHARS_PER_CHUNK)
        if not snippet:
            continue
        citations.append({
            "artifact_type": "document",
            "document_id": chunk.get("document_id"),
            "filename": document_name_map.get(chunk.get("document_id"), "document"),
            "page_number": chunk.get("page_number"),
            "snippet": snippet,
            "score": round(score, 4),
        })

    return citations


async def _build_code_citations(
    conversation: Dict[str, Any],
    query: str,
) -> List[Dict[str, Any]]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    citations: List[Dict[str, Any]] = []
    for artifact in normalize_primary_artifacts(conversation.get("primary_artifacts")):
        if artifact.get("kind") != "code" or artifact.get("status") != "ready":
            continue
        storage_path = artifact.get("storage_path")
        if not storage_path:
            continue

        try:
            content = await run_in_threadpool(code_artifacts.load_code_file, storage_path)
        except Exception:
            logger.warning("Failed to load code artifact for retrieval", extra={"artifact_id": artifact.get("id")})
            continue

        for chunk in _chunk_code_artifact(content, artifact.get("label") or artifact.get("filename") or "code"):
            chunk_tokens = _tokenize(chunk["text"])
            filename_tokens = _tokenize(chunk["filename"])
            symbol_tokens = {symbol.lower() for symbol in chunk.get("symbols", [])}
            overlap = len(query_tokens & (chunk_tokens | filename_tokens | symbol_tokens))
            if overlap == 0:
                continue
            snippet = documents.truncate_text(
                code_artifacts.format_code_context(
                    chunk["text"],
                    max_lines=25,
                    max_chars=RETRIEVAL_MAX_CHARS_PER_CHUNK,
                ),
                RETRIEVAL_MAX_CHARS_PER_CHUNK,
            )
            if not snippet:
                continue
            citations.append({
                "artifact_type": "code",
                "artifact_id": artifact.get("id"),
                "filename": chunk["filename"],
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"],
                "symbol": chunk.get("symbols", [None])[0],
                "snippet": snippet,
                "score": float(overlap),
            })

    citations.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return citations[:RETRIEVAL_TOP_K]


def _build_image_citations(conversation: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    query_tokens = _tokenize(query)
    citations: List[Dict[str, Any]] = []

    for artifact in normalize_primary_artifacts(conversation.get("primary_artifacts")):
        if artifact.get("kind") != "image" or artifact.get("status") != "ready":
            continue

        filename = artifact.get("label") or artifact.get("filename") or "image"
        summary = artifact.get("summary") or "Visual artifact available for review."
        metadata_text = f"{filename} {summary}"
        score = len(query_tokens & _tokenize(metadata_text))
        if score == 0:
            score = 0.1

        citations.append({
            "artifact_type": "image",
            "artifact_id": artifact.get("id"),
            "filename": filename,
            "snippet": summary,
            "score": float(score),
        })

    citations.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return citations[:RETRIEVAL_TOP_K]


async def build_retrieval_context(
    conversation_id: str,
    user_id: str,
    query: str
) -> Tuple[str | None, List[Dict[str, Any]]]:
    try:
        if not query.strip():
            return None, []
        conversation = await storage.get_conversation(conversation_id, user_id)
        if not conversation:
            return None, []

        document_citations = await _build_document_citations(conversation_id, user_id, query)
        code_citations = await _build_code_citations(conversation, query)
        image_citations = _build_image_citations(conversation, query)

        all_citations = sorted(
            [*document_citations, *code_citations, *image_citations],
            key=lambda item: item.get("score", 0.0),
            reverse=True,
        )

        citations: List[Dict[str, Any]] = []
        total_chars = 0
        for citation in all_citations:
            snippet = citation.get("snippet") or ""
            if not snippet:
                continue
            if total_chars + len(snippet) > RETRIEVAL_MAX_TOTAL_CHARS and citations:
                break
            total_chars += len(snippet)
            citations.append(citation)

        context = _build_context(citations)
        return (context if context else None), citations
    except Exception:
        logger.error("Retrieval error", exc_info=False)
        return None, []
