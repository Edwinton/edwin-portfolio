"""
Generate Edwin_Tony_CV.pdf — hierarchical layout with clear headings + subheadings.
Each section has:
  - A main heading (H1, navy, uppercase)
  - Subheadings under it (H2, bold, body color)
  - Content (body text, bullets, or skill lists)
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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "site.json"
OUT = ROOT / "public" / "Edwin_Tony_CV.pdf"

NAVY = colors.HexColor("#1a2332")
CHARCOAL = colors.HexColor("#2c2c2c")
BODY = colors.HexColor("#1f1f1f")
MUTED = colors.HexColor("#5a5a5a")
HAIRLINE = colors.HexColor("#c8c8c8")
LIGHT_RULE = colors.HexColor("#e8e8e8")


def strip_html(s):
    if not s:
        return ""
    return re.sub(r"<[^>]+>", "", s).strip()


def build():
    data = json.loads(DATA.read_text(encoding="utf-8-sig"))
    page = data["pages"]["cv"]
    cv = data["cv"]

    styles = getSampleStyleSheet()

    # ============ H1 — Main section headings ============
    h1_style = ParagraphStyle(
        "H1", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=11, leading=13,
        textColor=NAVY, spaceBefore=14, spaceAfter=2,
        letterSpacing=0.3,
    )

    # ============ H2 — Subheadings under sections ============
    h2_style = ParagraphStyle(
        "H2", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=BODY, spaceBefore=8, spaceAfter=2,
    )

    # ============ H3 — Meta / subtitles ============
    h3_style = ParagraphStyle(
        "H3", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=9, leading=12,
        textColor=MUTED, spaceBefore=0, spaceAfter=4,
    )

    name_style = ParagraphStyle(
        "Name", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=26, leading=30,
        textColor=NAVY, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=11, leading=14,
        textColor=CHARCOAL, spaceAfter=3,
    )
    contact_style = ParagraphStyle(
        "Contact", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9.5, leading=12,
        textColor=CHARCOAL, spaceAfter=0,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10.5, leading=14,
        textColor=BODY, alignment=TA_JUSTIFY, spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10.5, leading=14,
        textColor=BODY, leftIndent=14, spaceAfter=2,
    )

    # ============ Document ============
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Edwin Tony — Curriculum Vitae",
        author=data.get("name", "Edwin Tony"),
    )

    story = []

    # ---- Helper: H1 with thin rule underneath ----
    def add_h1(text):
        story.append(Paragraph(text.upper(), h1_style))
        rule = Table([[""]], colWidths=[doc.width], rowHeights=[1])
        rule.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.8, NAVY),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(rule)
        story.append(Spacer(1, 4))

    # ---- Helper: H2 with thin rule underneath ----
    def add_h2(text):
        story.append(Paragraph(text, h2_style))
        rule = Table([[""]], colWidths=[doc.width], rowHeights=[0.5])
        rule.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.4, LIGHT_RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(rule)
        story.append(Spacer(1, 3))

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
    story.append(Spacer(1, 6))

    # ============ PROFILE ============
    add_h1("Profile")
    story.append(Paragraph(page["summary"], body_style))

    # ============ TECHNICAL SKILLS ============
    add_h1("Technical Skills")
    for item in cv["skills"]:
        label = strip_html(item.get("title", ""))
        tags = ", ".join(strip_html(t) for t in item.get("tags", []))
        add_h2(label)                              # Subheading
        story.append(Paragraph(tags, body_style))  # Content

    # ============ PROJECTS ============
    add_h1("Projects")
    for item in cv["projects"]:
        title = strip_html(item.get("title", ""))
        tags = " · ".join(strip_html(t) for t in item.get("tags", []))
        href = item.get("href", "")
        desc = strip_html(item.get("description", ""))

        # H2: project name (bold navy, clickable)
        if href:
            name_html = (
                f'<link href="{href}" color="#1a2332"><b>{title}</b></link>'
            )
        else:
            name_html = f"<b>{title}</b>"
        add_h2(name_html)

        # H3: technologies (italic muted)
        if tags:
            story.append(Paragraph(tags, h3_style))

        # Content: description
        if desc:
            story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 4))

    # ============ EDUCATION ============
    add_h1("Education")
    for item in cv["education"]:
        title = strip_html(item.get("title", ""))
        place = strip_html(item.get("place", ""))
        period = strip_html(item.get("period", ""))
        desc = strip_html(item.get("description", ""))

        # H2: qualification
        add_h2(title)

        # H3: place · period
        meta_parts = [p for p in (place, period) if p]
        if meta_parts:
            story.append(Paragraph("  ·  ".join(meta_parts), h3_style))

        # Content: description
        if desc:
            story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 4))

    # ============ ADDITIONAL EXPERIENCE (optional) ============
    additional = page.get("additional_experience", [])
    visible = [strip_html(i) for i in additional if strip_html(i)]
    if visible:
        add_h1("Additional Experience")
        for entry in visible:
            story.append(Paragraph(f"• {entry}", bullet_style))

    # ============ INTERESTS ============
    interests = page.get("interests", [])
    visible = [strip_html(i) for i in interests if strip_html(i)]
    if visible:
        add_h1("Interests")
        story.append(Paragraph(", ".join(visible), body_style))

    doc.build(story)
    print(f"  ok Edwin_Tony_CV.pdf ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    build()