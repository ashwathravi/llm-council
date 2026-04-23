"""Structured metadata helpers for Design Studio sessions."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .session_context import normalize_session_type

HANDOFF_SECTION_SPECS = [
    {
        "key": "selected_direction",
        "label": "Selected Direction",
        "aliases": ("selected direction", "recommended direction", "recommendation"),
    },
    {
        "key": "rationale",
        "label": "Rationale",
        "aliases": ("rationale", "why this direction", "decision rationale"),
    },
    {
        "key": "component_map",
        "label": "Component Map",
        "aliases": ("component map", "component mapping", "implementation map", "screens and components"),
    },
    {
        "key": "handoff_notes",
        "label": "Handoff Notes",
        "aliases": ("handoff notes", "handoff", "implementation notes"),
    },
    {
        "key": "open_questions",
        "label": "Open Questions",
        "aliases": ("open questions", "questions", "risks and open questions"),
    },
]


def _direction_suffix(index: int) -> str:
    if 0 <= index < 26:
        return chr(97 + index)
    return str(index + 1)


def _direction_label(index: int) -> str:
    if 0 <= index < 26:
        return f"Direction {chr(65 + index)}"
    return f"Direction {index + 1}"


def _response_label(index: int) -> str:
    if 0 <= index < 26:
        return f"Response {chr(65 + index)}"
    return f"Response {index + 1}"


def _clean_summary_line(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    for line in text.splitlines():
        cleaned = line.strip()
        cleaned = re.sub(r"^#{1,6}\s+", "", cleaned)
        cleaned = re.sub(r"^[-*]\s+", "", cleaned)
        cleaned = re.sub(r"^\d+[.)]\s+", "", cleaned)
        if cleaned:
            return cleaned[:180]
    return text[:180]


def _normalize_heading(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[*_`:#]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _split_markdown_sections(text: str) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {}
    current_heading = ""

    for line in text.splitlines():
        heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        bold_heading_match = re.match(r"^\s{0,3}\*\*(.+?)\*\*:?\s*$", line)
        plain_heading_match = re.match(
            r"^\s{0,3}(Selected Direction|Recommended Direction|Recommendation|Rationale|Why This Direction|Decision Rationale|Component Map|Component Mapping|Implementation Map|Screens and Components|Handoff Notes|Handoff|Implementation Notes|Open Questions|Questions|Risks and Open Questions):?\s*$",
            line,
            flags=re.IGNORECASE,
        )
        match = heading_match or bold_heading_match or plain_heading_match
        if match:
            current_heading = _normalize_heading(match.group(1))
            sections.setdefault(current_heading, [])
            continue

        if current_heading:
            sections[current_heading].append(line)

    return {
        heading: "\n".join(lines).strip()
        for heading, lines in sections.items()
        if "\n".join(lines).strip()
    }


def _extract_list_items(content: str) -> List[str]:
    items: List[str] = []
    for line in content.splitlines():
        match = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.+?)\s*$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def _section_content_by_alias(markdown_sections: Dict[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        normalized_alias = _normalize_heading(alias)
        for heading, content in markdown_sections.items():
            if heading == normalized_alias or normalized_alias in heading:
                return content
    return ""


def build_candidate_directions(stage1_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    directions: List[Dict[str, Any]] = []
    for index, result in enumerate(stage1_results or []):
        if not isinstance(result, dict):
            continue
        source_model = result.get("model")
        if not isinstance(source_model, str) or not source_model.strip():
            source_model = f"model-{index + 1}"
        response_label = _response_label(index)
        directions.append({
            "id": f"direction-{_direction_suffix(index)}",
            "label": _direction_label(index),
            "response_label": response_label,
            "source_model": source_model,
            "summary": _clean_summary_line(result.get("response")),
        })
    return directions


def _direction_lookup(directions: List[Dict[str, Any]]) -> tuple[Dict[str, str], Dict[str, str]]:
    by_response_label: Dict[str, str] = {}
    by_model: Dict[str, str] = {}
    for direction in directions:
        direction_id = direction.get("id")
        response_label = direction.get("response_label")
        source_model = direction.get("source_model")
        if isinstance(direction_id, str):
            if isinstance(response_label, str):
                by_response_label[response_label] = direction_id
            if isinstance(source_model, str):
                by_model.setdefault(source_model, direction_id)
    return by_response_label, by_model


def _ranked_direction_entries(
    aggregate_rankings: Optional[List[Dict[str, Any]]],
    model_to_direction_id: Dict[str, str],
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for index, item in enumerate(aggregate_rankings or []):
        if not isinstance(item, dict):
            continue
        model = item.get("model")
        direction_id = model_to_direction_id.get(model) if isinstance(model, str) else None
        if not direction_id:
            continue
        entry = {
            "direction_id": direction_id,
            "rank": index + 1,
            "source_model": model,
        }
        for key in ("average_rank", "rankings_count", "total_weight", "weighted"):
            if key in item:
                entry[key] = item[key]
        ranked.append(entry)
    return ranked


def _rubric_entries(
    aggregate_rubrics: Optional[List[Dict[str, Any]]],
    model_to_direction_id: Dict[str, str],
) -> List[Dict[str, Any]]:
    rubrics: List[Dict[str, Any]] = []
    for item in aggregate_rubrics or []:
        if not isinstance(item, dict):
            continue
        model = item.get("model")
        direction_id = model_to_direction_id.get(model) if isinstance(model, str) else None
        if not direction_id:
            continue
        rubrics.append({
            "direction_id": direction_id,
            "source_model": model,
            "overall_score": item.get("overall_score"),
            "criteria": item.get("criteria") if isinstance(item.get("criteria"), list) else [],
        })
    return rubrics


def _judge_result_entries(
    stage2_results: Optional[List[Dict[str, Any]]],
    response_label_to_direction_id: Dict[str, str],
) -> List[Dict[str, Any]]:
    judge_results: List[Dict[str, Any]] = []
    for result in stage2_results or []:
        if not isinstance(result, dict):
            continue
        parsed_ranking = result.get("parsed_ranking")
        ranked_labels = parsed_ranking if isinstance(parsed_ranking, list) else []
        ranked_directions = []
        for rank_index, response_label in enumerate(ranked_labels):
            if not isinstance(response_label, str):
                continue
            direction_id = response_label_to_direction_id.get(response_label)
            if not direction_id:
                continue
            ranked_directions.append({
                "direction_id": direction_id,
                "response_label": response_label,
                "rank": rank_index + 1,
            })

        rubric_scores = result.get("rubric_scores")
        rubric_by_direction: Dict[str, Any] = {}
        if isinstance(rubric_scores, dict):
            for response_label, scores in rubric_scores.items():
                direction_id = response_label_to_direction_id.get(response_label)
                if direction_id:
                    rubric_by_direction[direction_id] = scores

        judge_results.append({
            "judge_model": result.get("model"),
            "ranked_directions": ranked_directions,
            "confidence": result.get("confidence"),
            "rubric_scores": rubric_by_direction,
        })
    return judge_results


def _selected_direction_details(
    directions: List[Dict[str, Any]],
    selected_direction_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    for direction in directions:
        if direction.get("id") == selected_direction_id:
            return {
                "id": direction.get("id"),
                "label": direction.get("label"),
                "source_model": direction.get("source_model"),
                "summary": direction.get("summary"),
            }
    return None


def _build_handoff_metadata(
    *,
    stage3_result: Optional[Dict[str, Any]],
    directions: List[Dict[str, Any]],
    selected_direction_id: Optional[str],
) -> Dict[str, Any]:
    response = ""
    if isinstance(stage3_result, dict) and isinstance(stage3_result.get("response"), str):
        response = stage3_result["response"].strip()

    selected_direction = _selected_direction_details(directions, selected_direction_id)
    status = "ready" if response else "pending"
    markdown_sections = _split_markdown_sections(response) if response else {}
    section_records: List[Dict[str, Any]] = []

    for spec in HANDOFF_SECTION_SPECS:
        content = _section_content_by_alias(markdown_sections, spec["aliases"])
        if not content and spec["key"] == "selected_direction" and selected_direction:
            content = selected_direction.get("summary") or selected_direction.get("label") or ""
        record = {
            "key": spec["key"],
            "label": spec["label"],
            "content": content,
            "items": _extract_list_items(content),
        }
        section_records.append(record)

    handoff = {
        "status": status,
        "selected_direction_id": selected_direction_id,
        "selected_direction_ref": selected_direction,
        "sections": section_records,
    }
    for record in section_records:
        handoff[record["key"]] = {
            "label": record["label"],
            "content": record["content"],
            "items": record["items"],
        }
    return handoff


def build_design_studio_metadata(
    *,
    session_type: Optional[str],
    stage1_results: List[Dict[str, Any]],
    stage2_results: Optional[List[Dict[str, Any]]] = None,
    stage3_result: Optional[Dict[str, Any]] = None,
    aggregate_rankings: Optional[List[Dict[str, Any]]] = None,
    aggregate_rubrics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if normalize_session_type(session_type) != "design_studio":
        return {}

    directions = build_candidate_directions(stage1_results)
    response_label_to_direction_id, model_to_direction_id = _direction_lookup(directions)
    ranked_directions = _ranked_direction_entries(aggregate_rankings, model_to_direction_id)
    rubric_summaries = _rubric_entries(aggregate_rubrics, model_to_direction_id)
    judge_results = _judge_result_entries(stage2_results, response_label_to_direction_id)
    selected_direction_id = (
        ranked_directions[0]["direction_id"]
        if ranked_directions
        else (directions[0]["id"] if directions else None)
    )
    handoff = _build_handoff_metadata(
        stage3_result=stage3_result,
        directions=directions,
        selected_direction_id=selected_direction_id,
    )

    return {
        "schema_version": 1,
        "candidate_directions": directions,
        "comparison": {
            "status": "complete" if stage2_results is not None else "pending",
            "ranked_directions": ranked_directions,
            "rubric_summaries": rubric_summaries,
            "judge_results": judge_results,
        },
        "selected_direction_id": selected_direction_id,
        "handoff": handoff,
    }
