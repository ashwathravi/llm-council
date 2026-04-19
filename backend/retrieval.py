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
ARCHITECTURE_QUERY_TOKENS = {
    "architecture", "architectural", "module", "modules", "boundary", "boundaries",
    "dependency", "dependencies", "layer", "layers", "structure", "structural",
    "refactor", "design", "integration", "flow", "cross", "multi", "system",
}

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
            symbol_name = item.get("symbol")
            chunk_type = item.get("chunk_type")
            if line_start and line_end and line_start != line_end:
                line_fragment = f"lines {line_start}-{line_end}"
            elif line_start:
                line_fragment = f"line {line_start}"
            else:
                line_fragment = None

            if chunk_type == "file_overview" and line_fragment:
                source_label = f"Source: {item['filename']} (overview, {line_fragment})"
            elif symbol_name and line_fragment:
                source_label = f"Source: {item['filename']}::{symbol_name} ({line_fragment})"
            elif line_fragment:
                source_label = f"Source: {item['filename']} ({line_fragment})"
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


def _is_architecture_query(query_tokens: set[str]) -> bool:
    return bool(query_tokens & ARCHITECTURE_QUERY_TOKENS)


def _build_file_overview_chunk(content: str, filename: str) -> Dict[str, Any]:
    lines = content.splitlines()
    symbol_index = code_artifacts.extract_symbol_index(content)
    import_paths = code_artifacts.extract_import_paths(content)
    max_lines = min(len(lines), 80)
    overview_text = "\n".join(lines[:max_lines])
    symbol_outline = ", ".join(
        f"{item['kind']} {item['name']}"
        for item in symbol_index[:8]
    ) or "None"
    import_outline = ", ".join(import_paths[:8]) or "None"
    search_text = "\n".join([
        filename,
        f"Imports: {import_outline}",
        f"Symbols: {symbol_outline}",
        overview_text,
    ])
    return {
        "filename": filename,
        "line_start": 1,
        "line_end": max_lines,
        "text": overview_text,
        "search_text": search_text,
        "symbols": [item["name"] for item in symbol_index],
        "imports": import_paths,
        "path_tokens": code_artifacts.extract_path_tokens(filename),
        "chunk_type": "file_overview",
        "symbol_kind": None,
        "symbol_name": None,
    }


def _chunk_symbol_span(
    lines: List[str],
    filename: str,
    symbol: Dict[str, Any],
    import_paths: List[str],
    *,
    chunk_lines: int = 80,
    overlap_lines: int = 20,
) -> List[Dict[str, Any]]:
    start_index = max(0, int(symbol["line_start"]) - 1)
    end_index = min(len(lines), int(symbol["line_end"]))
    selected_lines = lines[start_index:end_index]
    if not selected_lines:
        return []

    chunks: List[Dict[str, Any]] = []
    step = max(1, chunk_lines - overlap_lines)
    for offset in range(0, len(selected_lines), step):
        window = selected_lines[offset:offset + chunk_lines]
        if not window:
            continue
        line_start = start_index + offset + 1
        line_end = line_start + len(window) - 1
        text = "\n".join(window)
        chunks.append({
            "filename": filename,
            "line_start": line_start,
            "line_end": line_end,
            "text": text,
            "search_text": "\n".join([
                filename,
                symbol.get("kind") or "",
                symbol.get("name") or "",
                symbol.get("signature") or "",
                " ".join(import_paths),
                text,
            ]),
            "symbols": [symbol.get("name")] if symbol.get("name") else [],
            "imports": import_paths,
            "path_tokens": code_artifacts.extract_path_tokens(filename),
            "chunk_type": "symbol",
            "symbol_kind": symbol.get("kind"),
            "symbol_name": symbol.get("name"),
        })
        if line_end >= end_index:
            break
    return chunks


def _build_code_chunks(content: str, filename: str) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    if not lines:
        return []

    symbol_index = code_artifacts.extract_symbol_index(content)
    import_paths = code_artifacts.extract_import_paths(content)
    chunks: List[Dict[str, Any]] = [_build_file_overview_chunk(content, filename)]

    if symbol_index:
        for symbol in symbol_index:
            chunks.extend(_chunk_symbol_span(lines, filename, symbol, import_paths))
        return chunks

    chunk_lines = 50
    overlap_lines = 10
    step = max(1, chunk_lines - overlap_lines)
    path_tokens = code_artifacts.extract_path_tokens(filename)
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
            "search_text": "\n".join([filename, " ".join(import_paths), text]),
            "symbols": [],
            "imports": import_paths,
            "path_tokens": path_tokens,
            "chunk_type": "file_window",
            "symbol_kind": None,
            "symbol_name": None,
        })
        if line_end >= len(lines):
            break
    return chunks


def _score_code_chunk(chunk: Dict[str, Any], query_tokens: set[str], *, architecture_query: bool) -> float:
    search_tokens = _tokenize(chunk.get("search_text", ""))
    symbol_tokens = {token.lower() for token in chunk.get("symbols", []) if isinstance(token, str)}
    path_tokens = {token.lower() for token in chunk.get("path_tokens", []) if isinstance(token, str)}
    import_tokens = _tokenize(" ".join(chunk.get("imports", [])))

    lexical_overlap = len(query_tokens & search_tokens)
    symbol_overlap = len(query_tokens & symbol_tokens)
    path_overlap = len(query_tokens & path_tokens)
    import_overlap = len(query_tokens & import_tokens)

    score = lexical_overlap + (symbol_overlap * 2.5) + (path_overlap * 1.75) + (import_overlap * 1.25)
    if architecture_query and chunk.get("chunk_type") == "file_overview":
        score += 2.0
    elif architecture_query and chunk.get("chunk_type") == "symbol":
        score += 0.5
    return float(score)


def _limit_code_citations(citations: List[Dict[str, Any]], *, architecture_query: bool) -> List[Dict[str, Any]]:
    if not architecture_query:
        return citations[:RETRIEVAL_TOP_K]

    selected: List[Dict[str, Any]] = []
    seen_filenames = set()

    for citation in citations:
        filename = citation.get("filename")
        if filename in seen_filenames:
            continue
        seen_filenames.add(filename)
        selected.append(citation)
        if len(selected) >= RETRIEVAL_TOP_K:
            return selected

    for citation in citations:
        if citation in selected:
            continue
        selected.append(citation)
        if len(selected) >= RETRIEVAL_TOP_K:
            break

    return selected


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
    architecture_query = _is_architecture_query(query_tokens)

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

        filename = artifact.get("label") or artifact.get("filename") or "code"
        for chunk in _build_code_chunks(content, filename):
            score = _score_code_chunk(chunk, query_tokens, architecture_query=architecture_query)
            if score <= 0:
                continue

            code_excerpt = documents.truncate_text(
                code_artifacts.format_code_context(
                    chunk["text"],
                    max_lines=25,
                    max_chars=RETRIEVAL_MAX_CHARS_PER_CHUNK,
                    line_start=chunk["line_start"],
                ),
                RETRIEVAL_MAX_CHARS_PER_CHUNK,
            )
            if not code_excerpt:
                continue

            snippet_parts = []
            if chunk.get("chunk_type") == "file_overview":
                imports = chunk.get("imports") or []
                symbols = chunk.get("symbols") or []
                snippet_parts.append(f"Imports: {', '.join(imports[:6]) or 'None'}")
                snippet_parts.append(f"Top-level symbols: {', '.join(symbols[:8]) or 'None'}")
            elif chunk.get("symbol_name"):
                snippet_parts.append(
                    f"Symbol: {chunk.get('symbol_kind') or 'symbol'} {chunk['symbol_name']}"
                )
            snippet_parts.append(code_excerpt)
            snippet = "\n".join(part for part in snippet_parts if part).strip()

            citations.append({
                "artifact_type": "code",
                "artifact_id": artifact.get("id"),
                "filename": chunk["filename"],
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"],
                "symbol": chunk.get("symbol_name"),
                "chunk_type": chunk.get("chunk_type"),
                "snippet": snippet,
                "score": score,
            })

    citations.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return _limit_code_citations(citations, architecture_query=architecture_query)


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
