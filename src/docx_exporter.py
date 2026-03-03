"""
DOCX Export Module

Generates a formatted Word document from a Timeline object.
Each message entry includes the date, source image (if available), and extracted text.
"""

import logging
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from src.models import Timeline

logger = logging.getLogger(__name__)

# Image formats that python-docx can embed
EMBEDDABLE_FORMATS = {'.jpg', '.jpeg', '.png'}

# Max image width in the document (inches)
IMAGE_WIDTH = Inches(5)


def export_timeline(timeline: Timeline, output_dir: Path) -> Path:
    """
    Export a Timeline to a formatted DOCX file.

    Args:
        timeline: Timeline object with sorted messages
        output_dir: Directory to write the output file

    Returns:
        Path to the generated DOCX file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f"timeline_{timestamp}.docx"
    output_path = output_dir / filename

    doc = Document()

    _add_title(doc, timeline)

    for index, message in enumerate(timeline.messages):
        if index > 0:
            _add_separator(doc)
        _add_message_entry(doc, message, index + 1)

    doc.save(str(output_path))
    logger.info(f"Timeline exported to: {output_path}")

    return output_path


def _add_title(doc: Document, timeline: Timeline) -> None:
    """Add the document title and date range header."""
    title = doc.add_heading('Text Message Timeline', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Date range
    dated = [m for m in timeline.messages if m.date is not None]
    if dated:
        first = dated[0].date.strftime('%B %d, %Y')
        last = dated[-1].date.strftime('%B %d, %Y')
        if first == last:
            range_text = f"Date: {first}"
        else:
            range_text = f"Date Range: {first} to {last}"
        range_para = doc.add_paragraph(range_text)
        range_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    generated = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    gen_para = doc.add_paragraph(f"Generated: {generated}")
    gen_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    gen_para.runs[0].font.size = Pt(9)
    gen_para.runs[0].font.italic = True


def _add_separator(doc: Document) -> None:
    """Add a horizontal rule between message entries."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run('_' * 60)
    run.font.color.rgb = None  # Use default color


def _add_message_entry(doc: Document, message, index: int) -> None:
    """Add a single message entry to the document."""
    # Date heading
    if message.date:
        date_text = message.date.strftime('%B %d, %Y  %I:%M %p')
    else:
        date_text = "Date Unknown"

    doc.add_heading(date_text, level=2)

    # Source file reference
    source_para = doc.add_paragraph()
    source_run = source_para.add_run(f"Source: {message.source_file}")
    source_run.font.size = Pt(9)
    source_run.font.italic = True

    # Embed source image if available and supported
    if message.source_path and message.source_path.exists():
        ext = message.source_path.suffix.lower()
        if ext in EMBEDDABLE_FORMATS:
            try:
                doc.add_picture(str(message.source_path), width=IMAGE_WIDTH)
                # Center the image
                last_paragraph = doc.paragraphs[-1]
                last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception as e:
                logger.warning(f"Could not embed image {message.source_file}: {e}")
        else:
            note = doc.add_paragraph(f"[Source file: {message.source_file} "
                                     f"({ext} format — cannot embed in document)]")
            note.runs[0].font.size = Pt(9)
            note.runs[0].font.italic = True

    # Extracted text
    doc.add_paragraph()  # Spacing
    doc.add_paragraph(message.text)
