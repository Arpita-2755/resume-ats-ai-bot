from __future__ import annotations

import textwrap
import uuid
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from .resume_parser import parse_resume_text

TEMPLATE_STYLES = {
    "classic": {
        "font": "Calibri",
        "name_size": 20,
        "body_size": 11,
        "heading_color": RGBColor(0x22, 0x22, 0x22),
        "pdf_font": "Helvetica",
    },
    "modern": {
        "font": "Cambria",
        "name_size": 22,
        "body_size": 11,
        "heading_color": RGBColor(0x00, 0x5A, 0x9C),
        "pdf_font": "Times-Roman",
    },
    "minimal": {
        "font": "Arial",
        "name_size": 19,
        "body_size": 10,
        "heading_color": RGBColor(0x33, 0x33, 0x33),
        "pdf_font": "Courier",
    },
}


def export_resume_file(
    resume_text: str,
    style: str,
    output_format: str,
    output_dir: Path,
    base_filename: str = "fixed_resume",
) -> Path:
    style = style.lower()
    output_format = output_format.lower()
    if style not in TEMPLATE_STYLES:
        raise ValueError(f"Unknown style '{style}'. Choose from: {', '.join(TEMPLATE_STYLES)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{base_filename}_{style}_{uuid.uuid4().hex[:8]}"
    output_path = output_dir / f"{safe_name}.{output_format}"

    data = parse_resume_text(resume_text)
    if output_format == "docx":
        _export_docx(data, style, output_path)
    elif output_format == "pdf":
        _export_pdf(data, style, output_path)
    else:
        raise ValueError("output_format must be 'docx' or 'pdf'")
    return output_path


def _export_docx(data, style: str, output_path: Path) -> None:
    style_cfg = TEMPLATE_STYLES[style]
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = style_cfg["font"]
    normal_style.font.size = Pt(style_cfg["body_size"])

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(3)
    title_run = title.add_run(data.name)
    title_run.bold = True
    title_run.font.size = Pt(style_cfg["name_size"])

    contact_bits = [bit for bit in [data.email, data.phone] if bit]
    contact_bits.extend(data.links[:2])
    if contact_bits:
        contact = doc.add_paragraph(" | ".join(contact_bits))
        contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact.runs[0].italic = True
        contact.paragraph_format.space_after = Pt(6)

    divider = doc.add_paragraph("-" * 90)
    divider.alignment = WD_ALIGN_PARAGRAPH.CENTER
    divider.paragraph_format.space_after = Pt(8)

    for section_name, lines in data.sections.items():
        cleaned_lines = _clean_lines(lines)
        if not cleaned_lines:
            continue

        heading = doc.add_paragraph()
        heading.paragraph_format.space_before = Pt(6)
        heading.paragraph_format.space_after = Pt(4)
        heading_run = heading.add_run(section_name.upper())
        heading_run.bold = True
        heading_run.font.color.rgb = style_cfg["heading_color"]
        heading_run.font.size = Pt(style_cfg["body_size"] + 1)

        if section_name == "summary":
            paragraph = doc.add_paragraph(" ".join(cleaned_lines))
            paragraph.paragraph_format.space_after = Pt(4)
        elif section_name == "skills":
            skill_parts = []
            for line in cleaned_lines:
                skill_parts.extend([part.strip() for part in line.split(",") if part.strip()])
            paragraph = doc.add_paragraph(" | ".join(dict.fromkeys(skill_parts)))
            paragraph.paragraph_format.space_after = Pt(4)
        else:
            for line in cleaned_lines:
                bullet = doc.add_paragraph(line, style="List Bullet")
                bullet.paragraph_format.space_after = Pt(2)

    doc.save(str(output_path))


def _export_pdf(data, style: str, output_path: Path) -> None:
    style_cfg = TEMPLATE_STYLES[style]
    c = canvas.Canvas(str(output_path), pagesize=LETTER)
    _, height = LETTER
    x = 50
    y = height - 50

    c.setFont(style_cfg["pdf_font"], 18)
    c.drawString(x, y, data.name)
    y -= 18

    contact_bits = [bit for bit in [data.email, data.phone] if bit]
    contact_bits.extend(data.links[:2])
    if contact_bits:
        c.setFont(style_cfg["pdf_font"], 10)
        c.drawString(x, y, " | ".join(contact_bits))
        y -= 14

    c.line(x, y, 560, y)
    y -= 12

    for section_name, lines in data.sections.items():
        cleaned_lines = _clean_lines(lines)
        if not cleaned_lines:
            continue

        if y < 90:
            c.showPage()
            y = height - 50

        c.setFont(style_cfg["pdf_font"], 12)
        c.drawString(x, y, section_name.upper())
        y -= 12
        c.line(x, y, 560, y)
        y -= 10

        c.setFont(style_cfg["pdf_font"], 10)
        if section_name == "summary":
            y = _draw_wrapped(c, " ".join(cleaned_lines), x, y, prefix="", width=92)
            y -= 4
        elif section_name == "skills":
            skill_parts = []
            for line in cleaned_lines:
                skill_parts.extend([part.strip() for part in line.split(",") if part.strip()])
            y = _draw_wrapped(c, ", ".join(dict.fromkeys(skill_parts)), x, y, prefix="", width=92)
            y -= 4
        else:
            for line in cleaned_lines:
                y = _draw_wrapped(c, line, x + 6, y, prefix="- ", width=88)
            y -= 3

    c.save()


def _draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x: int,
    y: int,
    prefix: str,
    width: int,
) -> int:
    wrapped = textwrap.wrap(text, width=width)
    for index, chunk in enumerate(wrapped):
        c.drawString(x, y, (prefix if index == 0 else "  ") + chunk)
        y -= 12
    return y


def _clean_lines(lines: list[str]) -> list[str]:
    output: list[str] = []
    for line in lines:
        clean = line.lstrip("-*\u2022 ").strip()
        if clean:
            output.append(clean)
    return output

