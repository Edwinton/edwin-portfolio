"""
Generate Edwin_Tony_CV.pdf — minimal professional, ATS-friendly.
Based on: white background, dark navy headings, one column, selectable text.
"""
import json
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
)

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "site.json"
OUT = ROOT / "public" / "Edwin_Tony_CV.pdf"

# Minimal professional palette
NAVY = colors.HexColor("#1a2332")
CHARCOAL = colors.HexColor("#2c2c2c")
BODY = colors.HexColor("#1f1f1f")
MUTED = colors.HexColor("#5a5a5a")
HAIRLINE = colors.HexColor("#c8c8c8")


def strip_html(s):
    if not s:
        return ""
    return re.sub(r"<[^>]+>", "", s).strip()


def build():
    data = json.loads(DATA.read_text(encoding="utf-8-sig"))
    page = data["pages"]["cv"]
    cv = data["cv"]

    styles = getSampleStyleSheet()

    # ---- Typography (matches brief) ----
    name_style = ParagraphStyle(
        "Name", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=26, leading=30,
        textColor=NAVY, alignment=TA_LEFT, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=11, leading=14,
        textColor=CHARCOAL, alignment=TA_LEFT, spaceAfter=3,
    )
    contact_style = ParagraphStyle(
        "Contact", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9.5, leading=12,
        textColor=CHARCOAL, alignment=TA_LEFT, spaceAfter=0,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=11, leading=13,
        textColor=NAVY, spaceBefore=12, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10.5, leading=14,
        textColor=BODY, alignment=TA_JUSTIFY, spaceAfter=4,
    )
    cell_label = ParagraphStyle(
        "CellLabel", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=BODY,
    )
    cell_body = ParagraphStyle(
        "CellBody", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10.5, leading=14,
        textColor=BODY,
    )
    cell_place = ParagraphStyle(
        "CellPlace", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=10, leading=13,
        textColor=MUTED,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10.5, leading=14,
        textColor=BODY, leftIndent=14, bulletIndent=2, spaceAfter=2,
    )
    proj_name_style = ParagraphStyle(
        "ProjName", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10.5, leading=13,
        textColor=NAVY, spaceAfter=2,
    )
    proj_meta_style = ParagraphStyle(
        "ProjMeta", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=9.5, leading=12,
        textColor=MUTED, spaceAfter=4,
    )

    # ---- Document ----
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Edwin Tony — Curriculum Vitae",
        author=data.get("name", "Edwin Tony"),
        subject="CV",
    )

    story = []

    # ============ HEADER ============
    story.append(Paragraph(page["heading"], name_style))
    story.append(Paragraph(page["subtitle"], subtitle_style))

    contact_parts = []
    if data.get("email"):
        contact_parts.append(
            f'<link href="mailto:{data["email"]}" color="#2c2c2c">{data["email"]}</link>'
        )
    if data.get("github_short"):
        contact_parts.append(
            f'<link href="{data["github"]}" color="#2c2c2c">{data["github_short"]}</link>'
        )
    if data.get("linkedin_short"):
        contact_parts.append(
            f'<link href="{data["linkedin"]}" color="#2c2c2c">{data["linkedin_short"]}</link>'
        )
    story.append(Paragraph("  ·  ".join(contact_parts), contact_style))

    # Thin navy rule under header
    rule = Table([[""]], colWidths=[doc.width], rowHeights=[1])
    rule.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(Spacer(1, 6))
    story.append(rule)

    # ============ PROFILE ============
    # Renamed from "Summary" to "Profile" per brief
    story.append(Paragraph("PROFILE", section_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(page["summary"], body_style))

    # ============ TECHNICAL SKILLS ============
    story.append(Paragraph("TECHNICAL SKILLS", section_style))
    story.append(Spacer(1, 2))

    for item in cv["skills"]:
        label = strip_html(item.get("title", ""))
        tags = ", ".join(strip_html(t) for t in item.get("tags", []))
        line = f'<b>{label}:</b> {tags}'
        story.append(Paragraph(line, body_style))

    # ============ PROJECTS ============
    story.append(Paragraph("PROJECTS", section_style))
    story.append(Spacer(1, 2))

    for item in cv["projects"]:
        title = strip_html(item.get("title", ""))
        tags = " · ".join(strip_html(t) for t in item.get("tags", []))
        href = item.get("href", "")
        desc = strip_html(item.get("description", ""))

        # Project name (bold navy)
        name_html = (
            f'<link href="{href}" color="#1a2332"><b>{title}</b></link>'
            if href else f"<b>{title}</b>"
        )
        story.append(Paragraph(name_html, proj_name_style))
        # Technologies (italic muted)
        if tags:
            story.append(Paragraph(tags, proj_meta_style))
        # Description as paragraph
        if desc:
            story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 6))

    # ============ EDUCATION ============
    story.append(Paragraph("EDUCATION", section_style))
    story.append(Spacer(1, 2))

    for item in cv["education"]:
        title = strip_html(item.get("title", ""))
        place = strip_html(item.get("place", ""))
        period = strip_html(item.get("period", ""))
        desc = strip_html(item.get("description", ""))

        story.append(Paragraph(f"<b>{title}</b>", cell_label))
        meta = f"{place}  ·  {period}" if place and period else (place or period)
        if meta:
            story.append(Paragraph(meta, cell_place))
        if desc:
            story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 6))

    # ============ ADDITIONAL EXPERIENCE (optional) ============
    additional = page.get("additional_experience", [])
    visible = [strip_html(i) for i in additional if strip_html(i)]
    if visible:
        story.append(Paragraph("ADDITIONAL EXPERIENCE", section_style))
        story.append(Spacer(1, 2))
        bullet_items = [
            ListItem(Paragraph(v, body_style), leftIndent=12)
            for v in visible
        ]
        story.append(ListFlowable(
            bullet_items, bulletType="bullet", start="•",
            leftIndent=12, bulletFontSize=9, bulletColor=NAVY,
        ))

    # ============ INTERESTS (kept small at bottom) ============
    interests = page.get("interests", [])
    visible = [strip_html(i) for i in interests if strip_html(i)]
    if visible:
        story.append(Paragraph("INTERESTS", section_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph(", ".join(visible), body_style))

    doc.build(story)
    print(f"  ok Edwin_Tony_CV.pdf ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    build()