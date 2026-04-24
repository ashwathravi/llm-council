"""3-stage LLM Council orchestration."""

from collections import defaultdict
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from .code_execution import build_execution_context_block, run_code_execution_loop
from .openrouter import query_models_parallel, query_model, query_model_stream
from .config import (
    COUNCIL_MODELS,
    CHAIRMAN_MODEL,
    MAX_MODELS_PER_REQUEST,
    MODEL_TIMEOUT_SECONDS,
    STREAM_TIMEOUT_SECONDS,
    TITLE_TIMEOUT_SECONDS,
    FAST_LOCAL_TITLE,
    TITLE_MODEL,
)
from .session_templates import get_deliverable_spec, get_rubric_spec
from .session_context import normalize_execution_mode

# Pre-compiled regex patterns for parsing model rankings
NUMBERED_RESPONSE_RE = re.compile(r'\d+\.\s*Response [A-Z]', re.IGNORECASE)
RESPONSE_LABEL_RE = re.compile(r'Response\s+([A-Z])', re.IGNORECASE)
CONFIDENCE_RE = re.compile(r'^\s*CONFIDENCE\s*:\s*(\d{1,3})\s*$', re.IGNORECASE | re.MULTILINE)
RUBRIC_RESPONSE_RE = re.compile(r'^\s*(Response [A-Z])\s*:?\s*$', re.IGNORECASE)
RUBRIC_SCORE_RE = re.compile(r'^\s*-\s*([A-Za-z][A-Za-z ]*[A-Za-z])\s*:\s*(\d{1,2})\s*$')
VISUAL_FINDINGS_BLOCK_RE = re.compile(
    r'VISUAL FINDINGS JSON:\s*```(?:json)?\s*(.*?)\s*```',
    re.IGNORECASE | re.DOTALL,
)

DEFAULT_CONFIDENCE_SCORE = 50
DEFAULT_MODEL_PERFORMANCE = 0.5
MIN_CONFIDENCE_WEIGHT = 0.25


def _content_to_text(content: Any) -> str:
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, dict):
                text = text.get("value") or text.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
        return "\n".join(parts).strip()
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def _apply_retrieval_context(messages: List[Dict[str, str]], retrieval_context: Optional[str]) -> List[Dict[str, str]]:
    if not retrieval_context:
        return messages
    return [{"role": "system", "content": retrieval_context}] + list(messages)


def _limit_models(models: List[str]) -> List[str]:
    if not models:
        return models
    return models[:MAX_MODELS_PER_REQUEST]


def resolve_active_models(council_models: Optional[List[str]] = None) -> List[str]:
    selected_models = council_models if council_models and len(council_models) > 0 else COUNCIL_MODELS
    return _limit_models(selected_models)


def parse_confidence_from_text(response_text: str) -> Optional[int]:
    """Parse a trailing CONFIDENCE line from a model ranking response."""
    if not response_text:
        return None

    match = CONFIDENCE_RE.search(response_text)
    if not match:
        return None

    value = int(match.group(1))
    return max(0, min(100, value))


def _normalize_confidence_score(confidence_score: Optional[int]) -> int:
    if confidence_score is None:
        return DEFAULT_CONFIDENCE_SCORE
    return max(0, min(100, int(confidence_score)))


def _confidence_to_weight(confidence_score: Optional[int]) -> float:
    normalized = _normalize_confidence_score(confidence_score) / 100
    return round(max(MIN_CONFIDENCE_WEIGHT, normalized), 3)


def _default_model_profile(model_name: str) -> Dict[str, Any]:
    return {
        "model": model_name,
        "rounds_observed": 0,
        "average_performance": DEFAULT_MODEL_PERFORMANCE,
        "dynamic_weight": 1.0,
        "last_average_rank": None,
    }


def _normalize_rank_to_performance(rank_value: float, participant_count: int) -> float:
    if participant_count <= 1:
        return 1.0
    normalized = 1 - ((rank_value - 1) / (participant_count - 1))
    return max(0.0, min(1.0, normalized))


def _coerce_average_rank(rank_entry: Dict[str, Any], participant_count: int) -> float:
    if not isinstance(rank_entry, dict):
        return float(participant_count)

    raw_value = rank_entry.get("average_rank")
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    return float(participant_count)


def apply_round_to_model_profiles(
    model_profiles: Optional[Dict[str, Dict[str, Any]]],
    aggregate_rankings: List[Dict[str, Any]],
    responded_models: List[str]
) -> Dict[str, Dict[str, Any]]:
    """
    Update model profiles using a single completed ranking round.

    The repo does not yet have a gold-answer benchmark pipeline, so the rolling
    performance signal is derived from prior council rankings within the same
    conversation.
    """
    updated_profiles: Dict[str, Dict[str, Any]] = {
        model: dict(profile)
        for model, profile in (model_profiles or {}).items()
    }

    if not responded_models:
        return updated_profiles

    ranking_by_model = {
        entry.get("model"): entry
        for entry in aggregate_rankings
        if isinstance(entry, dict) and isinstance(entry.get("model"), str)
    }
    participant_count = len(responded_models)

    for model_name in responded_models:
        profile = updated_profiles.get(model_name, _default_model_profile(model_name))
        rank_value = _coerce_average_rank(ranking_by_model.get(model_name), participant_count)
        performance = _normalize_rank_to_performance(rank_value, participant_count)
        prior_rounds = int(profile.get("rounds_observed", 0) or 0)
        prior_average = float(profile.get("average_performance", DEFAULT_MODEL_PERFORMANCE))
        next_average = (
            ((prior_average * prior_rounds) + performance) / (prior_rounds + 1)
            if prior_rounds > 0 else performance
        )
        profile.update({
            "model": model_name,
            "rounds_observed": prior_rounds + 1,
            "average_performance": round(next_average, 3),
            "dynamic_weight": round(0.5 + next_average, 3),
            "last_average_rank": round(rank_value, 2),
        })
        updated_profiles[model_name] = profile

    return updated_profiles


def build_model_weight_profile(
    conversation_messages: Optional[List[Dict[str, Any]]],
    active_models: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Build rolling model profiles from prior assistant messages in a conversation.
    """
    profiles: Dict[str, Dict[str, Any]] = {}
    for model_name in active_models or []:
        profiles[model_name] = _default_model_profile(model_name)

    for message in conversation_messages or []:
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue

        metadata = message.get("metadata")
        if not isinstance(metadata, dict):
            continue

        aggregate_rankings = metadata.get("aggregate_rankings")
        if not isinstance(aggregate_rankings, list) or not aggregate_rankings:
            continue

        responded_models = metadata.get("responded_council_models")
        if not isinstance(responded_models, list) or not responded_models:
            responded_models = [
                entry.get("model")
                for entry in aggregate_rankings
                if isinstance(entry, dict) and isinstance(entry.get("model"), str)
            ]

        profiles = apply_round_to_model_profiles(profiles, aggregate_rankings, responded_models)

    return profiles


def serialize_model_weight_profile(
    model_profiles: Optional[Dict[str, Dict[str, Any]]],
    model_order: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    if not model_profiles:
        return []

    ordered_models = list(model_order or [])
    for model_name in model_profiles.keys():
        if model_name not in ordered_models:
            ordered_models.append(model_name)

    return [
        dict(model_profiles[model_name], model=model_name)
        for model_name in ordered_models
        if model_name in model_profiles
    ]


def _normalize_rubric_score(value: Any) -> Optional[int]:
    if not isinstance(value, (int, float)):
        return None
    return max(1, min(5, int(value)))


def _build_rubric_prompt_block(
    rubric_spec: Optional[Dict[str, Any]],
    response_labels: List[str],
) -> str:
    if not rubric_spec:
        return ""

    criteria = rubric_spec.get("criteria") or []
    if not isinstance(criteria, list) or not criteria:
        return ""

    criteria_lines = "\n".join(
        f"- {criterion['label']}: [score]"
        for criterion in criteria
        if isinstance(criterion, dict) and criterion.get("label")
    )
    first_response = response_labels[0] if response_labels else "Response A"
    second_response = response_labels[1] if len(response_labels) > 1 else "Response B"

    return f"""2. Score every response using the {rubric_spec['label']} before the final ranking.
- Use integer scores from {rubric_spec['score_range']} where 5 is strongest.
- {rubric_spec['effort_note']}
- {rubric_spec['confidence_note']}
- Include a section titled "RUBRIC SCORES:" using EXACTLY this structure:

RUBRIC SCORES:
{first_response}
{criteria_lines}
{second_response}
{criteria_lines}
...
"""


def parse_rubric_scores_from_text(
    ranking_text: str,
    response_labels: List[str],
    rubric_spec: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    if not ranking_text or not rubric_spec:
        return {}

    criteria = rubric_spec.get("criteria") or []
    if not isinstance(criteria, list) or not criteria:
        return {}

    label_lookup = {
        label.lower(): label
        for label in response_labels
        if isinstance(label, str) and label
    }
    criterion_lookup = {
        str(criterion["label"]).strip().lower(): str(criterion["key"]).strip()
        for criterion in criteria
        if isinstance(criterion, dict) and criterion.get("label") and criterion.get("key")
    }

    marker = "RUBRIC SCORES:"
    upper_text = ranking_text.upper()
    marker_idx = upper_text.find(marker)
    if marker_idx == -1:
        return {}

    final_ranking_idx = upper_text.find("FINAL RANKING:", marker_idx)
    if final_ranking_idx == -1:
        rubric_text = ranking_text[marker_idx + len(marker):]
    else:
        rubric_text = ranking_text[marker_idx + len(marker):final_ranking_idx]

    scores_by_response: Dict[str, Dict[str, int]] = {}
    current_label: Optional[str] = None
    for raw_line in rubric_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        response_match = RUBRIC_RESPONSE_RE.match(line)
        if response_match:
            matched_label = response_match.group(1).strip().lower()
            current_label = label_lookup.get(matched_label)
            if current_label:
                scores_by_response.setdefault(current_label, {})
            continue

        score_match = RUBRIC_SCORE_RE.match(line)
        if not current_label or not score_match:
            continue

        criterion_key = criterion_lookup.get(score_match.group(1).strip().lower())
        if not criterion_key:
            continue

        normalized_score = _normalize_rubric_score(int(score_match.group(2)))
        if normalized_score is None:
            continue
        scores_by_response[current_label][criterion_key] = normalized_score

    return {
        label: scores
        for label, scores in scores_by_response.items()
        if scores
    }


def _select_rubric_extremes(
    criteria: List[Dict[str, Any]],
    *,
    reverse: bool,
) -> List[Dict[str, Any]]:
    populated = [item for item in criteria if isinstance(item.get("average_score"), (int, float))]
    populated.sort(
        key=lambda item: (
            float(item["average_score"]),
            str(item.get("label") or ""),
        ),
        reverse=reverse,
    )
    return populated[:2]


def _build_rubric_summary_block(aggregate_rubrics: Optional[List[Dict[str, Any]]]) -> str:
    if not aggregate_rubrics:
        return ""

    lines = []
    for entry in aggregate_rubrics:
        if not isinstance(entry, dict):
            continue
        criteria = entry.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            continue

        strongest = ", ".join(
            f"{item['label']} {item['average_score']}"
            for item in _select_rubric_extremes(criteria, reverse=True)
        )
        weakest = ", ".join(
            f"{item['label']} {item['average_score']}"
            for item in _select_rubric_extremes(criteria, reverse=False)
        )
        spread_items = sorted(
            [
                item for item in criteria
                if isinstance(item.get("spread"), (int, float)) and float(item["spread"]) > 0
            ],
            key=lambda item: float(item["spread"]),
            reverse=True,
        )[:2]
        disagreement = ", ".join(
            f"{item['label']} spread {item['spread']}"
            for item in spread_items
        ) or "low rubric disagreement"

        lines.append(
            f"- {entry.get('model', 'unknown')}: overall rubric {entry.get('overall_score', 'n/a')}/5; "
            f"strongest {strongest or 'n/a'}; weakest {weakest or 'n/a'}; disagreement {disagreement}"
        )

    if not lines:
        return ""

    return (
        "RUBRIC SUMMARY:\n"
        + "\n".join(lines)
        + "\nUse rubric strengths, weak areas, and disagreement hotspots when they materially change the conclusion.\n"
    )


def _normalize_visual_percent(
    value: Any,
    *,
    fallback: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    if not isinstance(value, (int, float)):
        return fallback
    return max(minimum, min(maximum, float(value)))


def extract_visual_findings_from_response(
    response_text: str,
    primary_artifacts: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    if not isinstance(response_text, str) or not response_text.strip():
        return "", []

    match = VISUAL_FINDINGS_BLOCK_RE.search(response_text)
    if not match:
        return response_text.strip(), []

    try:
        payload = json.loads(match.group(1))
    except Exception:
        return response_text.strip(), []

    if not isinstance(payload, list):
        return response_text.strip(), []

    image_artifacts = [
        artifact
        for artifact in (primary_artifacts or [])
        if isinstance(artifact, dict) and artifact.get("kind") == "image"
    ]
    artifact_by_label = {}
    for artifact in image_artifacts:
        for key in ("label", "filename"):
            value = artifact.get(key)
            if isinstance(value, str) and value.strip():
                artifact_by_label[value.strip().lower()] = artifact

    findings: List[Dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue

        artifact_label_value = item.get("artifact_label") or item.get("image") or item.get("artifact")
        artifact = None
        if isinstance(artifact_label_value, str):
            artifact = artifact_by_label.get(artifact_label_value.strip().lower())
        if artifact is None:
            continue

        title = str(item.get("title") or item.get("issue") or "").strip()
        comment = str(item.get("comment") or item.get("description") or "").strip()
        if not title and not comment:
            continue

        severity = str(item.get("severity") or "medium").strip().lower()
        if severity not in {"low", "medium", "high"}:
            severity = "medium"

        width = _normalize_visual_percent(
            item.get("w") if item.get("w") is not None else item.get("width"),
            fallback=12.0,
            minimum=6.0,
        )
        height = _normalize_visual_percent(
            item.get("h") if item.get("h") is not None else item.get("height"),
            fallback=10.0,
            minimum=6.0,
        )
        x = _normalize_visual_percent(item.get("x"), fallback=50.0, maximum=100.0 - width)
        y = _normalize_visual_percent(item.get("y"), fallback=50.0, maximum=100.0 - height)

        findings.append({
            "id": f"visual-finding-{index}",
            "artifact_id": artifact.get("id"),
            "artifact_label": artifact.get("label") or artifact.get("filename") or "Image",
            "title": title or comment[:80] or f"Finding {index}",
            "comment": comment or title,
            "severity": severity,
            "x": round(x, 2),
            "y": round(y, 2),
            "w": round(width, 2),
            "h": round(height, 2),
        })

    cleaned_response = (
        response_text[:match.start()] + response_text[match.end():]
    ).strip()
    return cleaned_response or response_text.strip(), findings


def _fallback_title_from_query(user_query: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in user_query).strip()
    words = [w for w in cleaned.split() if w]
    if not words:
        return "New Conversation"
    title = " ".join(words[:5])
    return title[:50].strip() or "New Conversation"


async def stage1_collect_responses(
    messages: List[Dict[str, str]],
    council_models: List[str] = None,
    retrieval_context: Optional[str] = None
):
    """
    Stage 1: Collect individual responses from all council models.
    Yields dicts with 'model' and 'response' keys as they complete.
    """
    active_models = resolve_active_models(council_models)
    import asyncio

    messages_with_context = _apply_retrieval_context(messages, retrieval_context)

    # Wrapper to attach model name to the task result
    async def query_with_name(model_name, msgs):
        response = await query_model(model_name, msgs, timeout=MODEL_TIMEOUT_SECONDS)
        return model_name, response

    # Create tasks
    tasks = [query_with_name(model, messages_with_context) for model in active_models]

    # Yield results as they complete
    for completed_task in asyncio.as_completed(tasks):
        model, response = await completed_task
        if response and response.get("error"):
            yield {
                "model": model,
                "error": response.get("error")
            }
        elif response:
            yield {
                "model": model,
                "response": response.get('content', '')
            }


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    council_models: List[str] = None,
    chairman_model: str = None,
    retrieval_context: Optional[str] = None,
    session_type: Optional[str] = None,
    framework: str = "standard",
    model_profiles: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        council_models: Optional list of models to use. Defaults to config COUNCIL_MODELS.
        chairman_model: Unused here but kept for consistency if needed later.

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    active_models = resolve_active_models(council_models)
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }
    response_labels = list(label_to_model.keys())
    rubric_spec = get_rubric_spec(session_type)

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    retrieval_block = ""
    if retrieval_context:
        retrieval_block = f"\n\nRelevant document excerpts:\n{retrieval_context}\n"

    rubric_instructions = _build_rubric_prompt_block(rubric_spec, response_labels)
    ranking_step = "3" if rubric_instructions else "2"

    if framework == "heterogeneous":
        ranking_instructions = f"""{ranking_step}. Then, at the very end of your response, provide a final ranking and a confidence score.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- After the ranking, add one final line in the form "CONFIDENCE: 78"
- Use an integer confidence score from 0 to 100 based on how confident you are in your ranking
- Do not add any other text or explanations after the confidence line

Example of the correct ending:

FINAL RANKING:
1. Response C
2. Response A
3. Response B
CONFIDENCE: 78"""
    else:
        ranking_instructions = f"""{ranking_step}. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B"""

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

{retrieval_block}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
{rubric_instructions}
{ranking_instructions}

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(active_models, messages, timeout=MODEL_TIMEOUT_SECONDS)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None and not response.get("error"):
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_entry = {
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            }
            if rubric_spec:
                stage2_entry["rubric_scores"] = parse_rubric_scores_from_text(
                    full_text,
                    response_labels,
                    rubric_spec,
                )
            if framework == "heterogeneous":
                confidence_score = _normalize_confidence_score(parse_confidence_from_text(full_text))
                historical_weight = 1.0
                if model_profiles and isinstance(model_profiles.get(model), dict):
                    historical_weight = float(model_profiles[model].get("dynamic_weight", 1.0))
                stage2_entry.update({
                    "confidence_score": confidence_score,
                    "historical_weight": round(historical_weight, 3),
                    "ballot_weight": round(historical_weight * _confidence_to_weight(confidence_score), 3),
                })
            stage2_results.append(stage2_entry)

    return stage2_results, label_to_model


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    # Look for "FINAL RANKING:" section (case-insensitive)
    marker = "FINAL RANKING:"
    upper_text = ranking_text.upper()
    marker_idx = upper_text.find(marker)

    if marker_idx != -1:
        # Extract everything after "FINAL RANKING:"
        ranking_section = ranking_text[marker_idx + len(marker):]
        # Try to extract numbered list format (e.g., "1. Response A")
        # This pattern looks for: number, period, optional space, "Response X"
        numbered_matches = NUMBERED_RESPONSE_RE.findall(ranking_section)
        if numbered_matches:
            # Extract and normalize the "Response X" part
            results = []
            for m in numbered_matches:
                inner = RESPONSE_LABEL_RE.search(m)
                if inner:
                    results.append(f"Response {inner.group(1).upper()}")
            return results

        # Fallback: Extract all "Response X" patterns in order from the section
        matches = RESPONSE_LABEL_RE.findall(ranking_section)
        return [f"Response {m.upper()}" for m in matches]

    # Fallback: try to find any "Response X" patterns in order in full text
    matches = RESPONSE_LABEL_RE.findall(ranking_text)
    return [f"Response {m.upper()}" for m in matches]


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    model_positions = defaultdict(list)
    model_weighted_positions = defaultdict(list)
    ballot_counts = defaultdict(int)
    uses_weighted_ballots = False

    for ranking in stage2_results:
        ranking_text = ranking["ranking"]
        parsed_ranking = ranking.get("parsed_ranking")
        if not isinstance(parsed_ranking, list):
            parsed_ranking = parse_ranking_from_text(ranking_text)
        ballot_weight = ranking.get("ballot_weight", 1.0)
        if not isinstance(ballot_weight, (int, float)):
            ballot_weight = 1.0
        ballot_weight = float(ballot_weight)
        if abs(ballot_weight - 1.0) > 1e-9:
            uses_weighted_ballots = True

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)
                model_weighted_positions[model_name].append((position, ballot_weight))
                ballot_counts[model_name] += 1

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            weighted_positions = model_weighted_positions[model]
            total_weight = sum(weight for _, weight in weighted_positions) or float(len(positions))
            weighted_sum = sum(position * weight for position, weight in weighted_positions)
            avg_rank = weighted_sum / total_weight if total_weight else (sum(positions) / len(positions))
            entry = {
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": ballot_counts[model],
            }
            if uses_weighted_ballots:
                entry["total_weight"] = round(total_weight, 3)
                entry["weighted"] = True
            aggregate.append(entry)

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


def calculate_aggregate_rubrics(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    session_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    rubric_spec = get_rubric_spec(session_type)
    if not rubric_spec:
        return []

    criteria = rubric_spec.get("criteria") or []
    if not isinstance(criteria, list) or not criteria:
        return []

    score_buckets: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))
    evaluation_counts: Dict[str, int] = defaultdict(int)

    for entry in stage2_results:
        rubric_scores = entry.get("rubric_scores")
        if not isinstance(rubric_scores, dict):
            continue

        for response_label, response_scores in rubric_scores.items():
            model_name = label_to_model.get(response_label)
            if not model_name or not isinstance(response_scores, dict):
                continue

            has_score = False
            for criterion in criteria:
                if not isinstance(criterion, dict):
                    continue
                key = criterion.get("key")
                if not isinstance(key, str) or not key:
                    continue
                normalized_score = _normalize_rubric_score(response_scores.get(key))
                if normalized_score is None:
                    continue
                score_buckets[model_name][key].append(normalized_score)
                has_score = True
            if has_score:
                evaluation_counts[model_name] += 1

    aggregate = []
    for response_label, model_name in label_to_model.items():
        model_scores = score_buckets.get(model_name)
        if not model_scores:
            continue

        criterion_rows = []
        overall_values: List[int] = []
        for criterion in criteria:
            if not isinstance(criterion, dict):
                continue
            key = criterion.get("key")
            label = criterion.get("label")
            if not isinstance(key, str) or not isinstance(label, str):
                continue

            values = model_scores.get(key, [])
            if not values:
                continue

            average_score = round(sum(values) / len(values), 2)
            overall_values.extend(values)
            criterion_rows.append({
                "key": key,
                "label": label,
                "average_score": average_score,
                "spread": round(max(values) - min(values), 2),
                "evaluation_count": len(values),
            })

        if not criterion_rows:
            continue

        criterion_rows.sort(key=lambda item: item["label"])
        aggregate.append({
            "response_label": response_label,
            "model": model_name,
            "overall_score": round(sum(overall_values) / len(overall_values), 2),
            "evaluation_count": evaluation_counts.get(model_name, 0),
            "criteria": criterion_rows,
        })

    aggregate.sort(key=lambda item: item["overall_score"], reverse=True)
    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    fallback = _fallback_title_from_query(user_query)
    if FAST_LOCAL_TITLE:
        return fallback

    response = await query_model(TITLE_MODEL, messages, timeout=TITLE_TIMEOUT_SECONDS)

    if response is None or response.get("error"):
        # Fallback to a generic title
        return fallback

    title = response.get('content', fallback).strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title or fallback


async def run_full_council(
    messages: List[Dict[str, str]],
    framework: str = "standard",
    council_models: list = None,
    chairman_model: str = None,
    session_type: Optional[str] = None,
    specialist_template_id: Optional[str] = None,
    execution_mode: Optional[str] = None,
    primary_artifacts: Optional[List[Dict[str, Any]]] = None,
    retrieval_context: Optional[str] = None,
    retrieval_citations: Optional[List[Dict[str, Any]]] = None,
    conversation_messages: Optional[List[Dict[str, Any]]] = None,
    visual_findings_enabled: Optional[bool] = None,
):
    """
    Orchestrates the selected council process.
    """
    # Extract latest user query for Stage 2/3 context
    # Assuming the last message is from the user
    latest_query = (
        _content_to_text(messages[-1].get("content"))
        if messages and messages[-1]["role"] == "user"
        else "Unknown Query"
    )

    # Use provided models or fallback to config defaults
    requested_council_models = list(council_models) if council_models else []
    active_council_models = resolve_active_models(council_models)
    active_chairman_model = chairman_model if chairman_model else CHAIRMAN_MODEL
    model_profiles = (
        build_model_weight_profile(conversation_messages, active_council_models)
        if framework == "heterogeneous" else {}
    )

    # Stage 1: Collect responses
    # We need to pass the full messages to stage 1 functions
    stage1_errors = []
    if framework == "six_hats":
        stage1_results, stage1_errors = await stage1_collect_responses_six_hats(
            messages,
            active_council_models,
            retrieval_context=retrieval_context
        )
    else:
        stage1_results = []
        async for result in stage1_collect_responses(messages, active_council_models, retrieval_context=retrieval_context):
            if result.get("error"):
                stage1_errors.append(result)
            else:
                stage1_results.append(result)

    if not stage1_results:
        stage3_result = {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }
        return [], [], stage3_result, {"stage1_errors": stage1_errors}

    # Stage 2: Rank or Critique
    if framework == "debate":
        stage2_results, label_to_model = await stage2_collect_critiques(
            latest_query,
            stage1_results,
            active_council_models,
            retrieval_context=retrieval_context
        )
    elif framework == "ensemble":
         # Ensemble doesn't use Stage 2 for logic, but we need to return something
         stage2_results = []
         # Create label mapping for synthesis even if no ranking
         labels = [chr(65 + i) for i in range(len(stage1_results))]
         label_to_model = {
             f"Response {label}": result['model']
             for label, result in zip(labels, stage1_results)
         }
    else:
        # Standard and Six Hats use ranking
        stage2_results, label_to_model = await stage2_collect_rankings(
            latest_query,
            stage1_results,
            active_council_models,
            active_chairman_model,
            retrieval_context=retrieval_context,
            session_type=session_type,
            framework=framework,
            model_profiles=model_profiles
        )

    # Calculate aggregate rankings if applicable
    aggregate_rankings = []
    if framework in ["standard", "six_hats"] and stage2_results:
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
    elif framework == "heterogeneous" and stage2_results:
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
    aggregate_rubrics = calculate_aggregate_rubrics(
        stage2_results,
        label_to_model,
        session_type=session_type,
    )

    updated_model_profiles = (
        apply_round_to_model_profiles(
            model_profiles,
            aggregate_rankings,
            [result["model"] for result in stage1_results]
        )
        if framework == "heterogeneous" and aggregate_rankings else model_profiles
    )

    execution_report = await run_code_execution_loop(
        session_type=session_type,
        execution_mode=execution_mode,
        user_query=latest_query,
        stage1_results=stage1_results,
        stage2_results=stage2_results,
        chairman_model=active_chairman_model,
        primary_artifacts=primary_artifacts,
        retrieval_context=retrieval_context,
    )
    execution_context = build_execution_context_block(execution_report)

    # Stage 3: Synthesize
    stage3_text = ""
    async for chunk in stage3_synthesize_final(
        latest_query,
        stage1_results,
        stage2_results,
        active_chairman_model,
        mode=framework,
        session_type=session_type,
        specialist_template_id=specialist_template_id,
        retrieval_context=retrieval_context,
        execution_context=execution_context,
        aggregate_rankings=aggregate_rankings,
        aggregate_rubrics=aggregate_rubrics,
        visual_findings_enabled=visual_findings_enabled,
    ):
        stage3_text += chunk

    visual_findings: List[Dict[str, Any]] = []
    should_extract_visual_findings = (
        session_type == "visual_review"
        if visual_findings_enabled is None
        else visual_findings_enabled
    )
    if should_extract_visual_findings:
        stage3_text, visual_findings = extract_visual_findings_from_response(
            stage3_text,
            primary_artifacts=primary_artifacts,
        )

    stage3_result = {
        "model": active_chairman_model,
        "response": stage3_text,
    }

    metadata = {
        "framework": framework,
        "requested_council_models": requested_council_models,
        "effective_council_models": active_council_models,
        "responded_council_models": [r['model'] for r in stage1_results],
        "council_models": [r['model'] for r in stage1_results],
        "chairman_model": active_chairman_model,
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "aggregate_rubrics": aggregate_rubrics,
        "execution_mode": normalize_execution_mode(execution_mode, session_type=session_type),
        "execution": execution_report,
        "visual_findings": visual_findings,
        "stage1_errors": stage1_errors,
        "retrieval": {"citations": retrieval_citations or []},
    }
    if framework == "heterogeneous":
        metadata["model_weight_profile"] = serialize_model_weight_profile(
            updated_model_profiles,
            active_council_models
        )
        metadata["ballot_weighting"] = {
            "mode": "confidence_x_rolling_performance",
            "confidence_source": "stage2_self_report",
            "history_source": "prior_conversation_rankings",
        }

    return stage1_results, stage2_results, stage3_result, metadata


async def stage1_collect_responses_six_hats(
    messages: List[Dict[str, str]],
    council_models: List[str] = None,
    retrieval_context: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Stage 1 for Six Hats: Assign prompts to models."""
    active_models = resolve_active_models(council_models)
    hats = [
        ("White Hat", "Focus on available data and facts. Be neutral and objective."),
        ("Red Hat", "Focus on intuition, feelings, and hunches. No need to justify them."),
        ("Black Hat", "Focus on caution, risks, and potential problems. Be critical."),
        ("Yellow Hat", "Focus on benefits, optimism, and value. Be positive."),
        ("Green Hat", "Focus on creativity, alternatives, and new ideas."),
        ("Blue Hat", "Focus on process control, organization, and next steps.")
    ]
    
    # Assign hats to available models
    # If more models than hats, repeat/cycle hats. If fewer, some hats are missed.
    model_tasks = []
    assigned_hats = []
    
    for i, model in enumerate(active_models):
        hat_name, hat_prompt = hats[i % len(hats)]
        
        system_prompt = f"You are wearing the {hat_name}. {hat_prompt}"
        if retrieval_context:
            system_prompt = f"{system_prompt}\n\n{retrieval_context}"
        
        # Prepend system prompt to the FULL history
        current_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # We need to query models individually since they have different prompts
        # But we can still run them in parallel if we restructure query_models_parallel
        # For now, let's use a gathered list of coroutines
        model_tasks.append(query_model(model, current_messages, timeout=MODEL_TIMEOUT_SECONDS))
        assigned_hats.append(hat_name)

    import asyncio
    responses = await asyncio.gather(*model_tasks)
    
    results = []
    errors = []
    for i, response in enumerate(responses):
        if response:
            model = active_models[i]
            hat = assigned_hats[i]
            model_label = f"{model} ({hat})"
            if response.get("error"):
                errors.append({
                    "model": model_label,
                    "error": response.get("error")
                })
            else:
                results.append({
                    "model": model_label,
                    "response": response.get('content', '')
                })

    return results, errors


async def stage2_collect_critiques(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    council_models: List[str] = None,
    retrieval_context: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Stage 2 for Debate: Critiques instead of rankings."""
    active_models = resolve_active_models(council_models)
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {f"Response {label}": result['model'] for label, result in zip(labels, stage1_results)}

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    retrieval_block = ""
    if retrieval_context:
        retrieval_block = f"\nRelevant document excerpts:\n{retrieval_context}\n"

    critique_prompt = f"""You are participating in a debate about: "{user_query}"
{retrieval_block}

Here are the arguments from other participants (anonymized):

{responses_text}

Your task:
1. Critically analyze each response. identifying weak points, logical fallacies, or missing information.
2. Highlight the strongest counter-arguments.
3. Be direct and constructive.

Provide your critique for each response."""

    messages = [{"role": "user", "content": critique_prompt}]
    
    responses = await query_models_parallel(active_models, messages, timeout=MODEL_TIMEOUT_SECONDS)
    
    results = []
    for model, response in responses.items():
        if response and not response.get("error"):
            results.append({
                "model": model,
                "ranking": response.get('content', ''), # Reuse 'ranking' field for specific critique text
                "parsed_ranking": [] # No ranking in debate
            })
            
    return results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    chairman_model: str = None,
    mode: str = "standard",
    session_type: Optional[str] = None,
    specialist_template_id: Optional[str] = None,
    retrieval_context: Optional[str] = None,
    execution_context: Optional[str] = None,
    aggregate_rankings: Optional[List[Dict[str, Any]]] = None,
    aggregate_rubrics: Optional[List[Dict[str, Any]]] = None,
    visual_findings_enabled: Optional[bool] = None,
):
    """
    Stage 3: Chairman synthesizes final response (streaming).
    Yields content chunks.
    """
    
    # Use provided chairman model or fallback
    active_chairman_model = chairman_model or CHAIRMAN_MODEL
    
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_entries = []
    for result in stage2_results:
        stage2_lines = [f"Model: {result['model']}"]
        if mode == "heterogeneous":
            if "confidence_score" in result:
                stage2_lines.append(f"Confidence Score: {result['confidence_score']}")
            if "historical_weight" in result:
                stage2_lines.append(f"Historical Weight: {result['historical_weight']}")
            if "ballot_weight" in result:
                stage2_lines.append(f"Ballot Weight: {result['ballot_weight']}")
        stage2_lines.append(f"Feedback: {result['ranking']}")
        stage2_entries.append("\n".join(stage2_lines))
    stage2_text = "\n\n".join(stage2_entries)
    
    if mode == "debate":
        instruction = "Synthesize a final answer by weighing the original arguments and the peer critiques. Resolve the conflicts and find the strongest truth."
        stage2_label = "STAGE 2 - Peer Critiques:"
    elif mode == "six_hats":
        instruction = "Synthesize a final answer that integrates these diverse perspectives (Hats). Ensure the final decision considers facts, feelings, risks, benefits, and creativity."
        stage2_label = "STAGE 2 - Perspective Review:"
    elif mode == "ensemble":
        stage2_text = "(Stage 2 skipped for Ensemble mode)"
        instruction = "Synthesize the provided responses into a single, high-quality answer. Identify the consensus and best insights from the ensemble."
        stage2_label = "STAGE 2 - Skipped"
    elif mode == "heterogeneous":
        instruction = "Synthesize a final answer by prioritizing responses that earned the strongest weighted support from confident voters with stronger recent council performance."
        stage2_label = "STAGE 2 - Weighted Peer Rankings:"
    else: # standard
        instruction = "Synthesize all of this information into a single, comprehensive, accurate answer. Consider the individual responses and the peer rankings."
        stage2_label = "STAGE 2 - Peer Rankings:"

    retrieval_block = ""
    if retrieval_context:
        retrieval_block = f"\nRETRIEVED DOCUMENT EXCERPTS:\n{retrieval_context}\n"
    execution_block = ""
    if execution_context:
        execution_block = f"\n{execution_context}\n"

    weighted_consensus_block = ""
    if mode == "heterogeneous" and aggregate_rankings:
        summary_lines = []
        for entry in aggregate_rankings:
            model_name = entry.get("model", "unknown")
            average_rank = entry.get("average_rank")
            rankings_count = entry.get("rankings_count")
            total_weight = entry.get("total_weight")
            if total_weight is not None:
                summary_lines.append(
                    f"- {model_name}: weighted average rank {average_rank} across {rankings_count} ballots (total weight {total_weight})"
                )
            else:
                summary_lines.append(
                    f"- {model_name}: average rank {average_rank} across {rankings_count} ballots"
                )
        weighted_consensus_block = "WEIGHTED CONSENSUS SUMMARY:\n" + "\n".join(summary_lines) + "\n"
    rubric_summary_block = _build_rubric_summary_block(aggregate_rubrics)
    visual_findings_requested = (
        session_type == "visual_review"
        if visual_findings_enabled is None
        else visual_findings_enabled
    )
    visual_findings_block = ""
    if visual_findings_requested:
        visual_findings_block = """VISUAL FINDINGS APPENDIX:
- After the main answer, append a fenced JSON block introduced by the exact heading "VISUAL FINDINGS JSON:".
- Return an array of up to 6 findings.
- Each finding must include: artifact_label, title, comment, severity, x, y, w, h.
- Use the exact image labels from the PRIMARY ARTIFACTS list.
- Coordinates must be normalized percentages from 0 to 100. x/y are the top-left corner. w/h are region size percentages.
- Severity must be one of low, medium, or high.
- If there are no concrete visual findings, return an empty array.
"""
    citation_guidance_block = ""
    if session_type == "code_review":
        citation_guidance_block = """CODE CITATION RULES:
- When you call out a concrete issue, reference the provided filename and line range whenever one is available.
- If only a file-level overview citation is available, cite the filename and explain that the concern spans the broader module.
"""

    deliverable_spec = get_deliverable_spec(session_type, specialist_template_id)
    deliverable_block = (
        "FINAL DELIVERABLE FORMAT:\n"
        f"- Deliverable: {deliverable_spec['label']}\n"
        f"- Structure: {deliverable_spec['instruction']}\n"
        "- Do not return a generic essay. Follow the requested structure explicitly.\n"
    )

    chairman_prompt = f"""You are the Chairman of an LLM Council.
    
Original Question: {user_query}
{retrieval_block}

STAGE 1 - Individual Responses:
{stage1_text}

{stage2_label}
{stage2_text}

{weighted_consensus_block}
{rubric_summary_block}
{execution_block}
{visual_findings_block}
{citation_guidance_block}
{deliverable_block}

Your task: {instruction}

Provide a clear, well-reasoned final answer:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Stream the response
    async for chunk in query_model_stream(active_chairman_model, messages, timeout=STREAM_TIMEOUT_SECONDS):
        yield chunk
