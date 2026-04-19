"""Helpers for session/workspace metadata and primary artifact context."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
import uuid
from .session_templates import get_session_template

DEFAULT_SESSION_TYPE = "general"
DEFAULT_EXECUTION_MODE = "disabled"

SESSION_TYPES: Dict[str, Dict[str, str]] = {
    "general": {
        "label": "General",
        "focus": "Flexible multi-model collaboration with optional supporting artifacts.",
        "guidance": "Respond normally unless the attached artifacts clearly change the task framing.",
    },
    "visual_review": {
        "label": "Visual Review",
        "focus": "Critique screenshots, mockups, and visual UX artifacts.",
        "guidance": "Ground observations in what is visibly present. Discuss hierarchy, layout, clarity, affordances, consistency, accessibility, and obvious UX friction.",
    },
    "code_review": {
        "label": "Code Review",
        "focus": "Review repositories, diffs, code files, and implementation quality.",
        "guidance": "Prioritize correctness, regressions, code structure, missing tests, and cite file paths plus line numbers whenever the attached artifacts make them available.",
    },
    "build_spec": {
        "label": "Build/Spec",
        "focus": "Plan against specs, briefs, requirements, and implementation handoffs.",
        "guidance": "Turn artifacts into an execution plan with explicit assumptions, scope boundaries, and missing requirements.",
    },
    "research_docs": {
        "label": "Research/Docs",
        "focus": "Reason over documents, notes, and supporting source material.",
        "guidance": "Cite source material explicitly and distinguish observations from inference.",
    },
}

ALLOWED_SESSION_TYPES = set(SESSION_TYPES.keys())
ALLOWED_ARTIFACT_KINDS = {"document", "image", "code", "spec", "note", "link"}
ALLOWED_ARTIFACT_SOURCES = {"manual", "upload", "derived"}
ALLOWED_ARTIFACT_STATUSES = {"draft", "processing", "ready", "failed"}
EXECUTION_MODES: Dict[str, Dict[str, str]] = {
    "disabled": {
        "label": "Disabled",
        "description": "Do not generate candidate patches or run checks.",
    },
    "safe_patch_checks": {
        "label": "Safe Patch + Checks",
        "description": "Generate a candidate diff in a temp workspace and run guarded auto-detected checks.",
    },
}
ALLOWED_EXECUTION_MODES = set(EXECUTION_MODES.keys())


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def normalize_session_type(value: Optional[str]) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in ALLOWED_SESSION_TYPES:
            return normalized
    return DEFAULT_SESSION_TYPE


def get_session_type_label(session_type: Optional[str]) -> str:
    normalized = normalize_session_type(session_type)
    return SESSION_TYPES[normalized]["label"]


def normalize_execution_mode(
    value: Optional[str],
    *,
    session_type: Optional[str] = None,
) -> str:
    normalized_session_type = normalize_session_type(session_type)
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in ALLOWED_EXECUTION_MODES:
            if normalized_session_type != "code_review" and normalized != DEFAULT_EXECUTION_MODE:
                return DEFAULT_EXECUTION_MODE
            return normalized
    return DEFAULT_EXECUTION_MODE


def get_execution_mode_label(
    execution_mode: Optional[str],
    *,
    session_type: Optional[str] = None,
) -> str:
    normalized = normalize_execution_mode(execution_mode, session_type=session_type)
    return EXECUTION_MODES[normalized]["label"]


def normalize_primary_artifact(artifact: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(artifact, dict):
        return None

    label_value = artifact.get("label") or artifact.get("filename") or artifact.get("summary")
    label = str(label_value).strip() if label_value is not None else ""
    if not label:
        return None

    kind = str(artifact.get("kind") or "note").strip().lower()
    if kind not in ALLOWED_ARTIFACT_KINDS:
        kind = "note"

    source = str(artifact.get("source") or "manual").strip().lower()
    if source not in ALLOWED_ARTIFACT_SOURCES:
        source = "manual"

    status = str(artifact.get("status") or "ready").strip().lower()
    if status not in ALLOWED_ARTIFACT_STATUSES:
        status = "ready"

    document_id = artifact.get("document_id")
    if isinstance(document_id, str):
        document_id = document_id.strip() or None
    else:
        document_id = None

    artifact_id = artifact.get("id")
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        artifact_id = f"document:{document_id}" if document_id else str(uuid.uuid4())
    else:
        artifact_id = artifact_id.strip()

    normalized: Dict[str, Any] = {
        "id": artifact_id,
        "kind": kind,
        "label": label,
        "source": source,
        "status": status,
        "created_at": artifact.get("created_at") if isinstance(artifact.get("created_at"), str) else _now_iso(),
        "updated_at": artifact.get("updated_at") if isinstance(artifact.get("updated_at"), str) else _now_iso(),
    }

    if document_id:
        normalized["document_id"] = document_id

    for key in ("filename", "mime_type", "summary", "preview_url", "storage_path", "language"):
        value = artifact.get(key)
        if isinstance(value, str) and value.strip():
            normalized[key] = value.strip()

    for key in ("size_bytes", "width", "height", "line_count"):
        value = artifact.get(key)
        if isinstance(value, int) and value >= 0:
            normalized[key] = value

    return normalized


def normalize_primary_artifacts(artifacts: Any) -> List[Dict[str, Any]]:
    if not isinstance(artifacts, list):
        return []

    normalized: List[Dict[str, Any]] = []
    seen_ids = set()

    for artifact in artifacts:
        item = normalize_primary_artifact(artifact)
        if not item:
            continue
        artifact_id = item["id"]
        if artifact_id in seen_ids:
            continue
        seen_ids.add(artifact_id)
        normalized.append(item)

    return normalized


def build_primary_artifact_from_document(document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(document, dict):
        return None

    document_id = document.get("id")
    if not isinstance(document_id, str) or not document_id.strip():
        return None

    return normalize_primary_artifact({
        "id": f"document:{document_id}",
        "kind": "document",
        "label": document.get("filename") or "Document",
        "source": "upload",
        "status": document.get("status") or "ready",
        "document_id": document_id,
        "filename": document.get("filename"),
        "mime_type": "application/pdf",
        "size_bytes": document.get("size_bytes"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    })


def upsert_primary_artifact_record(
    artifacts: Any,
    artifact: Any,
) -> List[Dict[str, Any]]:
    normalized_artifact = normalize_primary_artifact(artifact)
    if not normalized_artifact:
        return normalize_primary_artifacts(artifacts)

    updated: List[Dict[str, Any]] = []
    replaced = False

    for current in normalize_primary_artifacts(artifacts):
        same_id = current["id"] == normalized_artifact["id"]
        same_document = (
            current.get("document_id")
            and normalized_artifact.get("document_id")
            and current.get("document_id") == normalized_artifact.get("document_id")
        )
        if same_id or same_document:
            updated.append(normalized_artifact)
            replaced = True
        else:
            updated.append(current)

    if not replaced:
        updated.append(normalized_artifact)

    return updated


def remove_primary_artifact_for_document_record(
    artifacts: Any,
    document_id: Optional[str],
) -> List[Dict[str, Any]]:
    if not isinstance(document_id, str) or not document_id.strip():
        return normalize_primary_artifacts(artifacts)

    target = document_id.strip()
    return [
        artifact
        for artifact in normalize_primary_artifacts(artifacts)
        if artifact.get("document_id") != target
    ]


def build_session_context_block(
    session_type: Optional[str],
    specialist_template_id: Optional[str],
    primary_artifacts: Optional[Iterable[Dict[str, Any]]],
) -> str:
    normalized_type = normalize_session_type(session_type)
    session_meta = SESSION_TYPES[normalized_type]
    specialist_template = get_session_template(specialist_template_id, session_type=normalized_type)
    artifacts = normalize_primary_artifacts(list(primary_artifacts or []))

    artifact_lines = []
    for artifact in artifacts:
        status = artifact.get("status") or "ready"
        artifact_lines.append(
            f"- {artifact.get('kind', 'artifact')}: {artifact.get('label', 'Artifact')} [{status}]"
        )

    if not artifact_lines:
        artifact_lines = [
            "- No primary artifacts are attached yet. Fall back to the user's messages when needed."
        ]

    template_block = ""
    if specialist_template:
        council_lenses = specialist_template.get("council_lenses") or []
        evaluation_criteria = specialist_template.get("evaluation_criteria") or []
        template_block = (
            "SPECIALIST TEMPLATE:\n"
            f"- Template: {specialist_template.get('label')}\n"
            f"- Focus: {specialist_template.get('description')}\n"
            f"- Specialist Lenses: {', '.join(council_lenses)}\n"
            f"- Evaluation Criteria: {', '.join(evaluation_criteria)}\n"
            f"- Final Synthesis: {specialist_template.get('synthesis_instruction')}\n"
        )

    return (
        "SESSION WORKSPACE:\n"
        f"- Type: {session_meta['label']}\n"
        f"- Focus: {session_meta['focus']}\n"
        f"{template_block}"
        "PRIMARY ARTIFACTS:\n"
        f"{chr(10).join(artifact_lines)}\n"
        f"REVIEW GUIDANCE:\n- {session_meta['guidance']}\n"
        "Treat the workspace type and primary artifacts as the default frame for analysis."
    )


def merge_context_blocks(*blocks: Optional[str]) -> str:
    return "\n\n".join(
        block.strip()
        for block in blocks
        if isinstance(block, str) and block.strip()
    )
