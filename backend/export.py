
import io
import html
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib import colors
from .session_context import (
    get_design_target_label,
    get_session_type_label,
    get_studio_goal_label,
    normalize_primary_artifacts,
    normalize_session_config,
)


DESIGN_MD_SECTION_KEYS = [
    ("selected_direction", "Chosen Direction"),
    ("rationale", "Why This Direction Won"),
    ("component_map", "Component Map"),
    ("state_notes", "State Notes"),
    ("platform_constraints", "Platform Constraints"),
    ("handoff_notes", "Implementation Notes"),
    ("open_questions", "Open Questions"),
]


def _clean_markdown_value(value) -> str:
    return str(value or "").strip()


def _latest_design_studio_metadata(conversation: dict) -> dict:
    for message in reversed(conversation.get("messages") or []):
        if not isinstance(message, dict):
            continue
        metadata = message.get("metadata")
        if not isinstance(metadata, dict):
            continue
        design_studio = metadata.get("design_studio")
        if isinstance(design_studio, dict):
            return design_studio
    return {}


def _latest_ready_design_handoff(conversation: dict, approved_direction_id: str) -> dict:
    fallback = {}
    for message in reversed(conversation.get("messages") or []):
        if not isinstance(message, dict):
            continue
        metadata = message.get("metadata")
        if not isinstance(metadata, dict):
            continue
        design_studio = metadata.get("design_studio")
        if not isinstance(design_studio, dict):
            continue
        handoff = design_studio.get("handoff")
        if not isinstance(handoff, dict) or handoff.get("status") != "ready":
            continue
        if not fallback:
            fallback = handoff
        if approved_direction_id and handoff.get("selected_direction_id") == approved_direction_id:
            return handoff
    return {} if approved_direction_id else fallback


def _section_from_handoff(handoff: dict, key: str) -> dict:
    direct = handoff.get(key)
    if isinstance(direct, dict):
        return {
            "content": _clean_markdown_value(direct.get("content")),
            "items": direct.get("items") if isinstance(direct.get("items"), list) else [],
        }

    for item in handoff.get("sections") or []:
        if isinstance(item, dict) and item.get("key") == key:
            return {
                "content": _clean_markdown_value(item.get("content")),
                "items": item.get("items") if isinstance(item.get("items"), list) else [],
            }
    return {"content": "", "items": []}


def _append_design_section(lines: list[str], title: str, section: dict, fallback: str = "") -> None:
    content = _clean_markdown_value(section.get("content")) or fallback
    items = [
        _clean_markdown_value(item)
        for item in (section.get("items") or [])
        if _clean_markdown_value(item)
    ]

    lines.append(f"## {title}\n\n")
    if items:
        for item in items:
            lines.append(f"- {item}\n")
        lines.append("\n")
    elif content:
        lines.append(f"{content}\n\n")
    else:
        lines.append("_Not captured._\n\n")


def _selected_direction_ref(design_studio: dict, handoff: dict, approved_direction_id: str) -> dict:
    if approved_direction_id:
        for direction in design_studio.get("candidate_directions") or []:
            if isinstance(direction, dict) and direction.get("id") == approved_direction_id:
                return direction

    selected_ref = handoff.get("selected_direction_ref")
    if (
        isinstance(selected_ref, dict)
        and selected_ref
        and (not approved_direction_id or selected_ref.get("id") == approved_direction_id)
    ):
        return selected_ref

    for direction in design_studio.get("candidate_directions") or []:
        if isinstance(direction, dict) and direction.get("id") == approved_direction_id:
            return direction
    return {}


def export_design_handoff_to_markdown(conversation: dict) -> str:
    """Export the approved Design Studio direction as a compact DESIGN.md handoff."""
    if not isinstance(conversation, dict):
        conversation = {}

    session_config = normalize_session_config(
        conversation.get("session_config"),
        session_type=conversation.get("session_type"),
    )
    approved_direction_id = session_config.get("approved_direction_id") or ""
    design_studio = _latest_design_studio_metadata(conversation)
    handoff = _latest_ready_design_handoff(conversation, approved_direction_id)
    selected_ref = _selected_direction_ref(design_studio, handoff, approved_direction_id)
    selected_direction_id = approved_direction_id or handoff.get("selected_direction_id") or selected_ref.get("id") or ""

    lines = []
    lines.append("# DESIGN.md\n\n")
    lines.append(f"**Conversation:** {conversation.get('title') or 'Conversation'}\n")
    lines.append(f"**Generated From:** {conversation.get('id') or ''}\n")
    lines.append(f"**Date:** {conversation.get('created_at') or ''}\n")
    lines.append(f"**Design Target:** {get_design_target_label(session_config.get('design_target'))}\n")
    lines.append(f"**Studio Goal:** {get_studio_goal_label(session_config.get('studio_goal'))}\n")
    if selected_direction_id:
        lines.append(f"**Approved Direction:** {selected_direction_id}\n")
    lines.append("\n")

    primary_artifacts = normalize_primary_artifacts(conversation.get("primary_artifacts"))
    lines.append("## Source Artifacts\n\n")
    if primary_artifacts:
        for artifact in primary_artifacts:
            label = artifact.get("label") or artifact.get("filename") or "Artifact"
            kind = artifact.get("kind") or "artifact"
            status = artifact.get("status") or "ready"
            lines.append(f"- {label} ({kind}, {status})\n")
        lines.append("\n")
    else:
        lines.append("_No primary artifacts attached._\n\n")

    selected_summary = _clean_markdown_value(selected_ref.get("summary"))
    if selected_ref:
        ref_lines = []
        label = _clean_markdown_value(selected_ref.get("label"))
        source_model = _clean_markdown_value(selected_ref.get("source_model"))
        if label:
            ref_lines.append(label)
        if source_model:
            ref_lines.append(f"Source model: {source_model}")
        if selected_summary:
            ref_lines.append(selected_summary)
        fallback_selected = "\n\n".join(ref_lines)
    else:
        fallback_selected = selected_direction_id

    for key, title in DESIGN_MD_SECTION_KEYS:
        fallback = fallback_selected if key == "selected_direction" else ""
        _append_design_section(lines, title, _section_from_handoff(handoff, key), fallback=fallback)

    comparison = design_studio.get("comparison") if isinstance(design_studio, dict) else {}
    ranked_directions = comparison.get("ranked_directions") if isinstance(comparison, dict) else []
    if isinstance(ranked_directions, list) and ranked_directions:
        lines.append("## Decision Trace\n\n")
        for item in ranked_directions[:5]:
            if not isinstance(item, dict):
                continue
            direction_id = item.get("direction_id") or "direction"
            rank = item.get("rank") or "n/a"
            average_rank = item.get("average_rank")
            suffix = f", average rank {average_rank}" if average_rank is not None else ""
            lines.append(f"- Rank {rank}: {direction_id}{suffix}\n")
        lines.append("\n")

    return "".join(lines)

def export_to_markdown(conversation: dict) -> str:
    """
    Export conversation to Markdown format.
    """
    if not isinstance(conversation, dict):
        conversation = {}
    lines = []
    lines.append(f"# {conversation.get('title') or 'Conversation'}\n\n")
    lines.append(f"**Date:** {conversation.get('created_at') or ''}\n")
    lines.append(f"**Framework:** {conversation.get('framework') or 'Standard'}\n")
    lines.append(f"**Session Type:** {get_session_type_label(conversation.get('session_type'))}\n")
    session_config = normalize_session_config(
        conversation.get("session_config"),
        session_type=conversation.get("session_type"),
    )
    if conversation.get("session_type") == "design_studio":
        lines.append(f"**Design Target:** {get_design_target_label(session_config.get('design_target'))}\n")
        lines.append(f"**Studio Goal:** {get_studio_goal_label(session_config.get('studio_goal'))}\n")
        if session_config.get("approved_direction_id"):
            lines.append(f"**Approved Direction:** {session_config.get('approved_direction_id')}\n")

    primary_artifacts = normalize_primary_artifacts(conversation.get("primary_artifacts"))
    if primary_artifacts:
        lines.append("**Primary Artifacts:**\n")
        for artifact in primary_artifacts:
            lines.append(f"- {artifact.get('label')} ({artifact.get('kind')})\n")
        lines.append("\n")
    else:
        lines.append("**Primary Artifacts:** None\n\n")

    for msg in (conversation.get('messages') or []):
        if not isinstance(msg, dict):
            continue
        role = msg.get('role')
        if role == 'user':
            lines.append(f"## User\n\n{msg.get('content') or ''}\n\n")
        elif role == 'assistant':
            lines.append("## LLM Council\n\n")

            # Stage 1
            stage1 = msg.get('stage1')
            if isinstance(stage1, list) and stage1:
                lines.append("### Stage 1: Individual Responses\n\n")
                for res in stage1:
                    if isinstance(res, dict):
                        lines.append(f"**{res.get('model') or 'Model'}**:\n\n{res.get('response') or ''}\n\n")

            # Stage 2
            stage2 = msg.get('stage2')
            if isinstance(stage2, list) and stage2:
                lines.append("### Stage 2: Peer Review\n\n")
                for res in stage2:
                    if isinstance(res, dict):
                        lines.append(f"**{res.get('model') or 'Model'}**:\n\n{res.get('ranking') or ''}\n\n")

            # Stage 3
            stage3 = msg.get('stage3')
            if isinstance(stage3, dict):
                lines.append("### Stage 3: Final Synthesis\n\n")
                lines.append(f"{stage3.get('response') or ''}\n\n")

        lines.append("---\n\n")

    return "".join(lines)

def export_to_pdf(conversation: dict) -> bytes:
    """
    Export conversation to PDF format using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='UserHeader', parent=styles['Heading2'], textColor=colors.blue))
    styles.add(ParagraphStyle(name='CouncilHeader', parent=styles['Heading2'], textColor=colors.darkgreen))
    styles.add(ParagraphStyle(name='StageHeader', parent=styles['Heading3'], textColor=colors.grey))
    styles.add(ParagraphStyle(name='ModelName', parent=styles['Heading4'], textColor=colors.black))
    styles.add(ParagraphStyle(name='NormalSmall', parent=styles['Normal'], fontSize=10, leading=12))

    story = []

    def safe_text(text: str) -> str:
        """Escape text for XML compatibility in ReportLab and handle newlines."""
        if not text:
            return ""
        # Escape XML chars
        escaped = html.escape(text)
        # Convert newlines to breaks
        return escaped.replace('\n', '<br/>')

    if not isinstance(conversation, dict):
        conversation = {}
    # Title
    story.append(Paragraph(safe_text(conversation.get('title') or 'Conversation'), styles["Title"]))
    story.append(Spacer(1, 12))

    # Metadata
    story.append(Paragraph(f"<b>Date:</b> {safe_text(conversation.get('created_at') or '')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Framework:</b> {safe_text(conversation.get('framework') or 'Standard')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Session Type:</b> {safe_text(get_session_type_label(conversation.get('session_type')))}", styles["Normal"]))
    session_config = normalize_session_config(
        conversation.get("session_config"),
        session_type=conversation.get("session_type"),
    )
    if conversation.get("session_type") == "design_studio":
        story.append(Paragraph(f"<b>Design Target:</b> {safe_text(get_design_target_label(session_config.get('design_target')))}", styles["Normal"]))
        story.append(Paragraph(f"<b>Studio Goal:</b> {safe_text(get_studio_goal_label(session_config.get('studio_goal')))}", styles["Normal"]))
        approved_direction = session_config.get("approved_direction_id")
        if approved_direction:
            story.append(Paragraph(f"<b>Approved Direction:</b> {safe_text(approved_direction)}", styles["Normal"]))

    primary_artifacts = normalize_primary_artifacts(conversation.get("primary_artifacts"))
    if primary_artifacts:
        artifact_text = ", ".join(
            f"{artifact.get('label', 'Artifact')} ({artifact.get('kind', 'artifact')})"
            for artifact in primary_artifacts
        )
        story.append(Paragraph(f"<b>Primary Artifacts:</b> {safe_text(artifact_text)}", styles["Normal"]))
    else:
        story.append(Paragraph("<b>Primary Artifacts:</b> None", styles["Normal"]))
    story.append(Spacer(1, 24))

    for msg in (conversation.get('messages') or []):
        if not isinstance(msg, dict):
            continue
        role = msg.get('role')

        if role == 'user':
            story.append(Paragraph("User", styles["UserHeader"]))
            content = safe_text(msg.get('content') or '')
            story.append(Paragraph(content, styles["Normal"]))
            story.append(Spacer(1, 12))

        elif role == 'assistant':
            story.append(Paragraph("LLM Council", styles["CouncilHeader"]))

            # Stage 1
            stage1 = msg.get('stage1')
            if isinstance(stage1, list) and stage1:
                story.append(Paragraph("Stage 1: Individual Responses", styles["StageHeader"]))
                for res in stage1:
                    if isinstance(res, dict):
                        model = safe_text(res.get('model') or 'Model')
                        story.append(Paragraph(f"<b>{model}</b>", styles["ModelName"]))
                        response = safe_text(res.get('response') or '')
                        story.append(Paragraph(response, styles["NormalSmall"]))
                        story.append(Spacer(1, 6))

            # Stage 2
            stage2 = msg.get('stage2')
            if isinstance(stage2, list) and stage2:
                story.append(Paragraph("Stage 2: Peer Review", styles["StageHeader"]))
                for res in stage2:
                    if isinstance(res, dict):
                        model = safe_text(res.get('model') or 'Model')
                        story.append(Paragraph(f"<b>{model}</b>", styles["ModelName"]))
                        ranking = safe_text(res.get('ranking') or '')
                        story.append(Paragraph(ranking, styles["NormalSmall"]))
                        story.append(Spacer(1, 6))

            # Stage 3
            stage3 = msg.get('stage3')
            if isinstance(stage3, dict):
                story.append(Paragraph("Stage 3: Final Synthesis", styles["StageHeader"]))
                response = safe_text(stage3.get('response') or '')
                story.append(Paragraph(response, styles["Normal"]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("_" * 50, styles["Normal"])) # Separator
        story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
