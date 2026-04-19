"""Utilities for validating, storing, and loading uploaded image artifacts."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional, Tuple

from .config import ARTIFACT_FILES_DIR

IMAGE_SIGNATURES = {
    "png": {
        "mime_type": "image/png",
        "extension": ".png",
    },
    "jpeg": {
        "mime_type": "image/jpeg",
        "extension": ".jpg",
    },
    "gif": {
        "mime_type": "image/gif",
        "extension": ".gif",
    },
    "webp": {
        "mime_type": "image/webp",
        "extension": ".webp",
    },
}


def ensure_artifact_files_dir() -> Path:
    base = Path(ARTIFACT_FILES_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return base


def detect_image_type(content: bytes) -> Optional[Tuple[str, str, str]]:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        meta = IMAGE_SIGNATURES["png"]
        return "png", meta["mime_type"], meta["extension"]

    if content.startswith(b"\xff\xd8\xff"):
        meta = IMAGE_SIGNATURES["jpeg"]
        return "jpeg", meta["mime_type"], meta["extension"]

    if content.startswith((b"GIF87a", b"GIF89a")):
        meta = IMAGE_SIGNATURES["gif"]
        return "gif", meta["mime_type"], meta["extension"]

    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        meta = IMAGE_SIGNATURES["webp"]
        return "webp", meta["mime_type"], meta["extension"]

    return None


def is_supported_image_file(filename: Optional[str], content_type: Optional[str]) -> bool:
    if content_type and content_type.lower() in {meta["mime_type"] for meta in IMAGE_SIGNATURES.values()}:
        return True
    if filename:
        lowered = filename.lower()
        return lowered.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    return False


def save_image_file(conversation_id: str, artifact_id: str, content: bytes, extension: str) -> str:
    base = ensure_artifact_files_dir()
    conversation_dir = base / conversation_id
    conversation_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{artifact_id}{extension}"
    target = conversation_dir / filename
    target.write_bytes(content)
    return f"{conversation_id}/{filename}"


def _safe_relative_path(relative_path: str) -> Path:
    base = ensure_artifact_files_dir().resolve()
    candidate = (base / relative_path).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError("Invalid artifact path")
    return candidate


def delete_image_file(relative_path: Optional[str]) -> None:
    if not isinstance(relative_path, str) or not relative_path.strip():
        return
    try:
        target = _safe_relative_path(relative_path.strip())
    except ValueError:
        return

    if target.exists():
        target.unlink()


def build_preview_url(relative_path: str) -> str:
    return f"/artifact-files/{relative_path}"


def load_image_as_data_url(relative_path: str, mime_type: str) -> str:
    target = _safe_relative_path(relative_path)
    raw = target.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
