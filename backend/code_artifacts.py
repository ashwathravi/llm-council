"""Helpers for storing and formatting uploaded code artifacts."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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

SYMBOL_PATTERNS = [
    ("class", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("interface", re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("type", re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("enum", re.compile(r"^\s*(?:export\s+)?enum\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("struct", re.compile(r"^\s*struct\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("function", re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("function", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)")),
    ("function", re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)")),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>")),
]

IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([A-Za-z0-9_./:-]+)\s+import|import\s+([A-Za-z0-9_./:-]+)|#include\s+[<\"]([^>\"]+)[>\"]|use\s+([A-Za-z0-9_:]+))",
    re.MULTILINE,
)
PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


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


def extract_symbol_index(content: str) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    if not lines:
        return []

    symbols: List[Dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        for kind, pattern in SYMBOL_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            symbols.append({
                "kind": kind,
                "name": match.group(1),
                "line_start": line_number,
                "signature": stripped[:200],
            })
            break

    for index, symbol in enumerate(symbols):
        next_symbol = symbols[index + 1] if index + 1 < len(symbols) else None
        line_end = (next_symbol["line_start"] - 1) if next_symbol else len(lines)
        symbol["line_end"] = max(symbol["line_start"], line_end)

    return symbols


def extract_import_paths(content: str) -> List[str]:
    imports = []
    for match in IMPORT_RE.finditer(content or ""):
        for group in match.groups():
            if group:
                imports.append(group.strip())
                break
    return imports


def extract_path_tokens(filename: Optional[str]) -> List[str]:
    if not isinstance(filename, str) or not filename.strip():
        return []
    return [token.lower() for token in PATH_TOKEN_RE.findall(filename) if token]


def build_summary(filename: Optional[str], content: str) -> str:
    line_count = count_lines(content)
    language = guess_language(filename)
    symbol_count = len(extract_symbol_index(content))
    symbol_fragment = ""
    if symbol_count:
        symbol_fragment = f" • {symbol_count} symbol{'s' if symbol_count != 1 else ''}"
    if language:
        return f"{language} • {line_count} lines{symbol_fragment}"
    return f"{line_count} lines{symbol_fragment}"


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


def format_code_context(content: str, *, max_lines: int, max_chars: int, line_start: int = 1) -> str:
    if not content:
        return ""

    lines = content.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append("... [truncated]")

    numbered_lines = [f"{line_start + index:4} | {line}" for index, line in enumerate(lines)]
    formatted = "\n".join(numbered_lines)
    if len(formatted) > max_chars:
        return f"{formatted[:max_chars].rstrip()}\n... [truncated]"
    return formatted
