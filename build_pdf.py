"""Generate Edwin_Tony_CV.pdf — from site.json."""
import json
import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "site.json"
OUT = ROOT / "public" / "Edwin_Tony_CV.pdf"

NAVY = colors.HexColor("#1a2332")
MUTED = colors.HexColor("#5a5a5a")
LIGHT_RULE = colors.HexColor("#e8e8e8")

def strip_html(s):
    return re.sub(r"<[^>]+>", "", s).strip() if s else ""

def build():
    data = json.loads(DATA.read_text(encoding="utf-8-sig"))
    page = data["pages"]["cv"]
    cv = data["cv"]
    styles = getSampleStyleSheet()

    # Styles
    name_style = ParagraphStyle("Name", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=NAVY, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5, leading=14, textColor=NAVY, spaceAfter=2)
    contact_style = ParagraphStyle("Contact", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED, spaceAfter=6)
    h1_style = ParagraphStyle("H1", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=NAVY, spaceBefore=12, spaceAfter=2)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14, textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=4)
    h2_style = ParagraphStyle("H2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=colors.black, spaceBefore=6, spaceAfter=2)
    h3_style = ParagraphStyle("H3", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=9, leading=12, textColor=MUTED, spaceAfter=2)
    bullet_style = ParagraphStyle("Bullet", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14, textColor=colors.black, leftIndent=12, spaceAfter=2)

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    story = []

    def add_h1(text):
        story.append(Paragraph(text.upper(), h1_style))
        rule = Table([[""]], colWidths=[doc.width], rowHeights=[1])
        rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.8, NAVY), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        story.append(rule)
        story.append(Spacer(1, 4))

    # Header
    story.append(Paragraph(page["heading"], name_style))
    story.append(Paragraph("WEB DESIGNER &amp; DEVELOPER — AVAILABLE WEEKDAYS FROM 3 PM (15–20 HRS/WEEK); WEEKENDS FLEXIBLE", subtitle_style))
    story.append(Paragraph(page["contact_line"], contact_style))
    
    # Summary
    add_h1("Profile")
    story.append(Paragraph(page["summary"], body_style))

    # Projects
    add_h1("Projects")
    for item in cv["projects"]:
        title = strip_html(item.get("title", ""))
        href = item.get("href", "")
        title_html = f'<link href="{href}" color="#1a2332"><b>{title}</b></link>' if href else f"<b>{title}</b>"
        tags = " · ".join(strip_html(t) for t in item.get("tags", []))
        
        story.append(Paragraph(title_html, h2_style))
        if tags:
            story.append(Paragraph(tags, h3_style))
        story.append(Paragraph(strip_html(item.get("description", "")), body_style))

    # Skills
    add_h1("Skills")
    for item in cv["skills"]:
        label = strip_html(item.get("title", ""))
        tags = " · ".join(strip_html(t) for t in item.get("tags", []))
        story.append(Paragraph(f"<b>{label}</b> — {tags}", body_style))

    # Education
    add_h1("Education")
    for item in cv["education"]:
        title = strip_html(item.get("title", ""))
        place = strip_html(item.get("place", ""))
        story.append(Paragraph(f"<b>{title}</b> — {place}", body_style))

    # Achievements
    add_h1("Achievements")
    for item in page.get("achievements", []):
        story.append(Paragraph(f"• {strip_html(item)}", bullet_style))

    # Languages
    add_h1("Languages")
    story.append(Paragraph(page.get("languages", ""), body_style))

    doc.build(story)
    print(f"  ok Edwin_Tony_CV.pdf ({OUT.stat().st_size} bytes)")

if __name__ == "__main__":
    build()