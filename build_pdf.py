"""Generate Edwin_Tony_CV.pdf — strict 1-page layout with feedback applied."""
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

def strip_html(s):
    return re.sub(r"<[^>]+>", "", s).strip() if s else ""

def build():
    data = json.loads(DATA.read_text(encoding="utf-8-sig"))
    page = data["pages"]["cv"]
    cv = data["cv"]
    styles = getSampleStyleSheet()

    # Tightened styles for 1-page fit
    name_style = ParagraphStyle("Name", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=22, leading=24, textColor=NAVY, spaceAfter=2)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=NAVY, spaceAfter=2)
    contact_style = ParagraphStyle("Contact", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=4)
    h1_style = ParagraphStyle("H1", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=11, textColor=NAVY, spaceBefore=8, spaceAfter=1)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=2)
    bullet_style = ParagraphStyle("Bullet", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.black, leftIndent=8, spaceAfter=2)
    h2_style = ParagraphStyle("H2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.black, spaceBefore=4, spaceAfter=1)

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=12*mm, bottomMargin=12*mm)
    story = []

    def add_h1(text):
        story.append(Paragraph(text.upper(), h1_style))
        rule = Table([[""]], colWidths=[doc.width], rowHeights=[0.5])
        rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.8, NAVY), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        story.append(rule)
        story.append(Spacer(1, 2))

    # Header
    story.append(Paragraph(page["heading"], name_style))
    story.append(Paragraph("WEB DESIGNER &amp; DEVELOPER — AVAILABLE WEEKDAYS FROM 3 PM (15–20 HRS/WEEK); WEEKENDS FLEXIBLE", subtitle_style))
    story.append(Paragraph(page["contact_line"], contact_style))
    
    # Profile
    add_h1("Profile")
    story.append(Paragraph(page["summary"], body_style))

    # Technical Interests (New Section)
    if page.get("technical_interests"):
        add_h1("Technical Interests")
        story.append(Paragraph(page["technical_interests"], body_style))

    # Projects
    add_h1("Projects")
    for item in cv["projects"]:
        title = strip_html(item.get("title", ""))
        href = item.get("href", "")
        
        # Ensure link is clickable, use display text "Source" if needed
        link_text = f'<link href="{href}" color="#1a2332"><b>{title}</b></link>' if href else f"<b>{title}</b>"
        tags = " · ".join(strip_html(t) for t in item.get("tags", []))
        
        header_line = f"{link_text} <font color='#5a5a5a' size='8'>({tags})</font>"
        story.append(Paragraph(header_line, h2_style))
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

    # Certifications (New Section)
    if page.get("certifications"):
        add_h1("Certifications")
        for item in page["certifications"]:
            story.append(Paragraph(f"• {strip_html(item)}", bullet_style))

    # Achievements (Decluttered)
    if page.get("achievements"):
        add_h1("Achievements")
        for item in page["achievements"]:
            story.append(Paragraph(f"• {strip_html(item)}", bullet_style))

    doc.build(story)
    print(f"  ok Edwin_Tony_CV.pdf ({OUT.stat().st_size} bytes)")

if __name__ == "__main__":
    build()