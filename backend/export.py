
import io
import html
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib import colors

def export_to_markdown(conversation: dict) -> str:
    """
    Export conversation to Markdown format.
    """
    md = f"# {conversation.get('title', 'Conversation')}\n\n"
    md += f"**Date:** {conversation.get('created_at', '')}\n"
    md += f"**Framework:** {conversation.get('framework', 'Standard')}\n\n"

    for msg in conversation.get('messages', []):
        role = msg.get('role')
        if role == 'user':
            md += f"## User\n\n{msg.get('content', '')}\n\n"
        elif role == 'assistant':
            md += "## LLM Council\n\n"

            # Stage 1
            if msg.get('stage1'):
                md += "### Stage 1: Individual Responses\n\n"
                for res in msg['stage1']:
                    md += f"**{res.get('model', 'Model')}**:\n\n{res.get('response', '')}\n\n"

            # Stage 2
            if msg.get('stage2'):
                md += "### Stage 2: Peer Review\n\n"
                for res in msg['stage2']:
                    md += f"**{res.get('model', 'Model')}**:\n\n{res.get('ranking', '')}\n\n"

            # Stage 3
            if msg.get('stage3'):
                md += "### Stage 3: Final Synthesis\n\n"
                md += f"{msg['stage3'].get('response', '')}\n\n"

        md += "---\n\n"

    return md

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

    # Title
    story.append(Paragraph(safe_text(conversation.get('title', 'Conversation')), styles["Title"]))
    story.append(Spacer(1, 12))

    # Metadata
    story.append(Paragraph(f"<b>Date:</b> {safe_text(conversation.get('created_at', ''))}", styles["Normal"]))
    story.append(Paragraph(f"<b>Framework:</b> {safe_text(conversation.get('framework', 'Standard'))}", styles["Normal"]))
    story.append(Spacer(1, 24))

    for msg in conversation.get('messages', []):
        role = msg.get('role')

        if role == 'user':
            story.append(Paragraph("User", styles["UserHeader"]))
            content = safe_text(msg.get('content', ''))
            story.append(Paragraph(content, styles["Normal"]))
            story.append(Spacer(1, 12))

        elif role == 'assistant':
            story.append(Paragraph("LLM Council", styles["CouncilHeader"]))

            # Stage 1
            if msg.get('stage1'):
                story.append(Paragraph("Stage 1: Individual Responses", styles["StageHeader"]))
                for res in msg['stage1']:
                    model = safe_text(res.get('model', 'Model'))
                    story.append(Paragraph(f"<b>{model}</b>", styles["ModelName"]))
                    response = safe_text(res.get('response', ''))
                    story.append(Paragraph(response, styles["NormalSmall"]))
                    story.append(Spacer(1, 6))

            # Stage 2
            if msg.get('stage2'):
                story.append(Paragraph("Stage 2: Peer Review", styles["StageHeader"]))
                for res in msg['stage2']:
                    model = safe_text(res.get('model', 'Model'))
                    story.append(Paragraph(f"<b>{model}</b>", styles["ModelName"]))
                    ranking = safe_text(res.get('ranking', ''))
                    story.append(Paragraph(ranking, styles["NormalSmall"]))
                    story.append(Spacer(1, 6))

            # Stage 3
            if msg.get('stage3'):
                story.append(Paragraph("Stage 3: Final Synthesis", styles["StageHeader"]))
                response = safe_text(msg['stage3'].get('response', ''))
                story.append(Paragraph(response, styles["Normal"]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("_" * 50, styles["Normal"])) # Separator
        story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
