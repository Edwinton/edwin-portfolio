"""One-time migration: add brand / footer / section_templates to site.json.
Idempotent — safe to run multiple times.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "site.json"

data = json.loads(DATA.read_text(encoding="utf-8-sig"))

if "brand" not in data:
    data["brand"] = {"wordmark": "ET", "wordmark_accent": "."}

if "footer" not in data:
    data["footer"] = {
        "copyright": "© {year} Edwin Tony",
        "back_to_top_label": "Back to top ↑",
    }

tmpl_dir = ROOT / "templates"
templates = {}
for name, file in [
    ("hero", "home.html"),
    ("about", "about.html"),
    ("skills", "skills.html"),
    ("projects", "projects.html"),
    ("timeline", "education.html"),
    ("cv", "cv.html"),
    ("contact", "contact.html"),
]:
    p = tmpl_dir / file
    if p.exists():
        templates[name] = p.read_text(encoding="utf-8")

if "rich_text" not in templates:
    templates["rich_text"] = (
        '<section class="section page-section"><div class="container">'
        '<div class="section-head"><p class="eyebrow">{{ page.eyebrow }}</p>'
        '<h2>{{ page.heading }}</h2></div>'
        '<div class="rich-text">{{ page.body_html }}</div></div></section>'
    )

data["section_templates"] = templates

defaults = {
    "home": ["hero"],
    "about": ["about"],
    "skills": ["skills"],
    "projects": ["projects"],
    "education": ["timeline"],
    "cv": ["cv"],
    "contact": ["contact"],
}
for key, page in data["pages"].items():
    if "sections" not in page:
        page["sections"] = defaults.get(key, [])

DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Migrated site.json — {len(data['pages'])} pages, "
      f"{len(templates)} section templates, "
      f"brand wordmark='{data['brand']['wordmark']}'")