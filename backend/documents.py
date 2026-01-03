"""PDF extraction, chunking, and embedding helpers."""

from __future__ import annotations

from typing import List, Dict, Any
import io
import re
import threading

from pypdf import PdfReader

from .config import CHUNK_WORDS, CHUNK_OVERLAP_WORDS, EMBEDDING_MODEL_NAME

_EMBEDDING_MODEL = None
_EMBEDDING_LOCK = threading.Lock()


def is_pdf_file(filename: str | None, content_type: str | None) -> bool:
    if content_type and "pdf" in content_type.lower():
        return True
    if filename and filename.lower().endswith(".pdf"):
        return True
    return False


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf_text(content_bytes: bytes) -> List[str]:
    reader = PdfReader(io.BytesIO(content_bytes))
    if reader.is_encrypted:
        raise ValueError("Encrypted PDF files are not supported.")

    pages: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(normalize_text(text))
    return pages


def chunk_pages(
    page_texts: List[str],
    chunk_words: int = CHUNK_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    overlap = max(0, min(overlap_words, chunk_words - 1))

    for page_number, text in enumerate(page_texts, start=1):
        if not text:
            continue
        words = text.split()
        if not words:
            continue

        start = 0
        while start < len(words):
            end = min(len(words), start + chunk_words)
            chunk_text = " ".join(words[start:end])
            chunks.append({
                "chunk_index": chunk_index,
                "page_number": page_number,
                "text": chunk_text
            })
            chunk_index += 1
            if end >= len(words):
                break
            start = max(0, end - overlap)

    return chunks


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars].rsplit(" ", 1)[0]
    return f"{trimmed}..."


def _get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        with _EMBEDDING_LOCK:
            if _EMBEDDING_MODEL is None:
                from sentence_transformers import SentenceTransformer
                _EMBEDDING_MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _EMBEDDING_MODEL


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = _get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return [embedding.tolist() for embedding in embeddings]
