"""Helpers for storing and formatting uploaded code artifacts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .config import ARTIFACT_FILES_DIR

SUPPORTED_CODE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".diff", ".go", ".h", ".hpp",
    ".html", ".java", ".js", ".json", ".jsx", ".kt", ".md", ".mjs",
    ".php", ".py", ".rb", ".rs", ".sh", ".sql", ".swift", ".toml",
    ".ts", ".tsx", ".txt", ".yaml", ".yml",
}

LANGUAGE_BY_EXTENSION = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".diff": "Diff",
    ".go": "Go",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JSX",
    ".kt": "Kotlin",
    ".md": "Markdown",
    ".mjs": "JavaScript",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sh": "Shell",
    ".sql": "SQL",
    ".swift": "Swift",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TSX",
    ".txt": "Text",
    ".yaml": "YAML",
    ".yml": "YAML",
}


def ensure_artifact_files_dir() -> Path:
    base = Path(ARTIFACT_FILES_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return base


def is_supported_code_file(filename: Optional[str], content_type: Optional[str]) -> bool:
    if filename:
        extension = Path(filename).suffix.lower()
        if extension in SUPPORTED_CODE_EXTENSIONS:
            return True
    if isinstance(content_type, str):
        lowered = content_type.lower()
        if lowered.startswith("text/"):
            return True
        if lowered in {
            "application/json",
            "application/javascript",
            "application/x-javascript",
            "application/xml",
        }:
            return True
    return False


def decode_text_content(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Only UTF-8 text files are supported.") from exc


def guess_language(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    return LANGUAGE_BY_EXTENSION.get(Path(filename).suffix.lower())


def count_lines(content: str) -> int:
    if not content:
        return 0
    return len(content.splitlines())


def build_summary(filename: Optional[str], content: str) -> str:
    line_count = count_lines(content)
    language = guess_language(filename)
    if language:
        return f"{language} • {line_count} lines"
    return f"{line_count} lines"


def save_code_file(conversation_id: str, artifact_id: str, filename: str, content: str) -> str:
    base = ensure_artifact_files_dir()
    conversation_dir = base / conversation_id
    conversation_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = os.path.basename(filename) or "artifact.txt"
    target = conversation_dir / f"{artifact_id}-{safe_filename}"
    target.write_text(content, encoding="utf-8")
    return f"{conversation_id}/{target.name}"


def _safe_relative_path(relative_path: str) -> Path:
    base = ensure_artifact_files_dir().resolve()
    candidate = (base / relative_path).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError("Invalid artifact path")
    return candidate


def load_code_file(relative_path: str) -> str:
    target = _safe_relative_path(relative_path)
    return target.read_text(encoding="utf-8")


def delete_code_file(relative_path: Optional[str]) -> None:
    if not isinstance(relative_path, str) or not relative_path.strip():
        return
    try:
        target = _safe_relative_path(relative_path.strip())
    except ValueError:
        return

    if target.exists():
        target.unlink()


def format_code_context(content: str, *, max_lines: int, max_chars: int) -> str:
    if not content:
        return ""

    lines = content.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append("... [truncated]")

    numbered_lines = [f"{index + 1:4} | {line}" for index, line in enumerate(lines)]
    formatted = "\n".join(numbered_lines)
    if len(formatted) > max_chars:
        return f"{formatted[:max_chars].rstrip()}\n... [truncated]"
    return formatted
