
import io
import html
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib import colors
from .session_context import get_session_type_label, normalize_primary_artifacts

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
