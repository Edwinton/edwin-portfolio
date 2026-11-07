import json
import re
import shutil
import sys
import os
import importlib
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent
TEMPLATES = ROOT / "templates"
PARTIALS = TEMPLATES / "partials"
STATIC = ROOT / "static"
DATA_FILE = ROOT / "data" / "site.json"
OUT = ROOT / "public"

# Force the base_url for GitHub Pages deployment
is_ci = os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("CI") == "true"
BASE_URL = "/edwin-portfolio" if is_ci else ""

PAGES = {
    "home.html": "index.html",
    "about.html": "about.html",
    "skills.html": "skills.html",
    "projects.html": "projects.html",
    "education.html": "education.html",
    "cv.html": "cv.html",
    "achievements.html": "achievements.html",
    "contact.html": "contact.html",
}

TOKEN = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")

ICON_SVG = {
    "mail": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 6l-10 7L2 6"/></svg>',
    "github": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>',
    "linkedin": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>',
    "doc": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
    "link": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
}

def icon(name):
    return ICON_SVG.get(name, ICON_SVG["doc"])

def lookup(path, ctx):
    value = ctx
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list):
            try:
                value = value[int(part)]
            except (ValueError, IndexError):
                return ""
        else:
            return ""
    return str(value)

def render(template, ctx):
    return TOKEN.sub(lambda m: str(lookup(m.group(1), ctx)), template)

def render_partials(partial_file, items):
    tpl = (PARTIALS / partial_file).read_text(encoding="utf-8")
    return "\n".join(render(tpl, {"item": item}) for item in items)

def tags_html(tags):
    return "\n          ".join(f"<li>{t}</li>" for t in tags)

def links_html(links):
    out = []
    for link in links:
        cls = "link disabled" if link.get("disabled") else "link"
        attrs = f' class="{cls}"'
        if link.get("external"):
            attrs += ' target="_blank" rel="noopener"'
        if link.get("disabled"):
            out.append(f'<span{attrs}>{link["label"]}</span>')
        else:
            out.append(f'<a href="{link["href"]}"{attrs}>{link["label"]}</a>')
    return "\n          ".join(out)

def actions_html(actions):
    out = []
    for a in actions:
        if "contact" in a.get("label", "").lower():
            continue
        style = a.get("style", "primary")
        href = a.get("href", "#")
        label = a.get("label", "Link")
        external = ' target="_blank"' if a.get("external") else ""
        out.append(f'<a href="{href}" class="btn btn-{style}"{external}>{label}</a>')
    return "\n          ".join(out)

def meta_html(meta):
    return "\n          ".join(f'<li><span class="icon">{icon(m.get("icon", ""))}</span> {m["text"]}</li>' for m in meta)

def paragraphs_html(paragraphs):
    return "\n          ".join(f"<p>{p}</p>" for p in paragraphs)

def facts_html(facts):
    return "\n          ".join(f'<li><strong>{f["label"]}</strong><span>{f["value"]}</span></li>' for f in facts)

def prepare(site):
    pages = site["pages"]
    
    home = pages.get("home", {})
    if "actions" in home: home["actions_html"] = actions_html(home["actions"])
    if "meta" in home: home["meta_html"] = meta_html(home["meta"])

    about = pages.get("about", {})
    if "paragraphs" in about: about["paragraphs_html"] = paragraphs_html(about["paragraphs"])
    if "facts" in about: about["facts_html"] = facts_html(about["facts"])

    prof = about.get("profile", {})
    if prof:
        facts = [f'<div class="profile-card-fact"><dt>{f["label"]}</dt><dd>{f["value"]}</dd></div>' for f in prof.get("facts", [])]
        prof["facts_html"] = "\n".join(facts)
        links = []
        for l in prof.get("links", []):
            target = ' target="_blank" rel="noopener"' if l["href"].startswith("http") else ""
            icon_key = l.get("icon", "doc")
            if "github" in l.get("href", "").lower(): icon_key = "github"
            if "linkedin" in l.get("href", "").lower(): icon_key = "linkedin"
            if "mailto" in l.get("href", "").lower(): icon_key = "mail"
            links.append(f'<a class="profile-card-link" href="{l["href"]}"{target}><span style="display:inline-block; margin-bottom: 4px;">{icon(icon_key)}</span><span>{l["label"]}</span></a>')
        prof["links_html"] = "\n".join(links)

    for page_data in pages.values():
        if "body" in page_data: page_data["body_html"] = paragraphs_html(page_data["body"])

    for skill in site.get("skills", []): skill["tags_html"] = tags_html(skill["tags"])

    for project in site.get("projects", []):
        project["tags_html"] = tags_html(project["tags"])
        project["links_html"] = links_html(project["links"])
        project["placeholder_class"] = "project-placeholder" if project.get("placeholder") else ""
        project["status_attr"] = f'data-status="{project["status"]}"' if project.get("status") else ""

    for contact in site.get("contacts", []):
        contact["target_attr"] = ' target="_blank" rel="noopener"' if contact.get("external") else ""
        icon_key = contact.get("icon", "doc")
        if "github" in contact.get("href", "").lower(): icon_key = "github"
        if "linkedin" in contact.get("href", "").lower(): icon_key = "linkedin"
        if "mailto" in contact.get("href", "").lower(): icon_key = "mail"
        contact["icon_svg"] = icon(icon_key)

    cv = site.get("cv", {})
    for skill in cv.get("skills", []): skill["tags_html"] = tags_html(skill["tags"])
    for project in cv.get("projects", []):
        project["tags_html"] = tags_html(project["tags"])
        if project.get("href"): project["title_html"] = f'<a href="{project["href"]}" target="_blank" rel="noopener">{project["title"]}</a>'
        else: project["title_html"] = project["title"]
    
    if "cv" in pages and "interests" in pages["cv"]:
        pages["cv"]["interests_html"] = "".join(f"<li>{item}</li>" for item in pages["cv"]["interests"])

    footer = site.get("footer", {})
    footer["copyright_html"] = footer.get("copyright", "").replace("{year}", str(__import__('datetime').datetime.now().year))

    # Generate Event Cards for Achievements page
    achv = pages.get("achievements", {})
    if "events" in achv:
        cards = []
        for ev in achv["events"]:
            cards.append(f"""
            <article class="project-card">
              <div class="project-top"><span class="project-badge">{ev.get("badge", "Event")}</span></div>
              <h3>{ev.get("title", "")}</h3>
              <p style="font-size: 0.85rem; color: var(--green-700); font-weight: 600; margin-bottom: 4px;">{ev.get("date", "")} · {ev.get("time", "")}</p>
              <p style="font-size: 0.85rem; color: var(--ink-mute); margin-bottom: 12px;">{ev.get("venue", "")}</p>
              <p>{ev.get("summary", "")}</p>
              <div class="project-links" style="margin-top: auto;">
                <a href="{ev.get("link", "#")}" class="link">Read Case Study →</a>
              </div>
            </article>
            """)
        achv["events_html"] = "\n".join(cards)

    return site

def build_nav(nav, current_file):
    out = []
    for item in nav:
        classes = []
        if item.get("cta"): classes.append("nav-cta")
        if item.get("file") == current_file: classes.append("active")
        cls = f' class="{" ".join(classes)}"' if classes else ""
        out.append(f'<li><a href="{BASE_URL}/{item["href"]}"{cls}>{item["label"]}</a></li>')
    return "\n        ".join(out)

def render_section(section_id, site, page_data):
    templates = site.get("section_templates", {})
    tpl = templates.get(section_id)
    if not tpl: return f"<!-- unknown section: {section_id} -->"
    ctx = {"site": site, "page": page_data}
    if section_id == "skills": ctx["skill_cards"] = render_partials("skill_card.html", site["skills"])
    elif section_id == "projects": ctx["project_cards"] = render_partials("project_card.html", site["projects"])
    elif section_id == "timeline": ctx["timeline_items"] = render_partials("timeline_item.html", site["education"])
    elif section_id == "contact": ctx["contact_cards"] = render_partials("contact_card.html", site["contacts"])
    elif section_id == "cv":
        ctx["cv_education_items"] = render_partials("cv_education_item.html", site["cv"]["education"])
        ctx["cv_skill_items"] = render_partials("cv_skill_item.html", site["cv"]["skills"])
        ctx["cv_project_items"] = render_partials("cv_project_item.html", site["cv"]["projects"])
        ctx["cv"] = site["cv"]
    return render(tpl, ctx)

def build_page(page_key, page_data, site):
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    sections = page_data.get("sections", [])
    parts = [render_section(sid, site, page_data) for sid in sections]
    content = "\n".join(parts)
    out_file = page_data.get("file", f"{page_key}.html")
    
    final = render(base, {
        "site": site,
        "page": page_data,
        "cv": site.get("cv", {}),
        "content": content,
        "nav_items": build_nav(site["nav"], out_file),
    })
    
    (OUT / out_file).parent.mkdir(parents=True, exist_ok=True)
    (OUT / out_file).write_text(final, encoding="utf-8")
    print(f"  ok {out_file}")
    return out_file

def build_all():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = DATA_FILE.read_text(encoding="utf-8-sig")
    site = prepare(json.loads(raw))

    print(f"Building: {site['title']}")
    outputs = set()
    for page_key, page_data in site["pages"].items():
        outputs.add(build_page(page_key, page_data, site))

    for existing in OUT.glob("*.html"):
        if existing.name not in outputs:
            try: existing.unlink()
            except: pass

    print("Copying static assets...")
    shutil.copytree(STATIC, OUT / "static", dirs_exist_ok=True)

    print("Generating CV PDF...")
    try:
        import build_pdf
        importlib.reload(build_pdf)
        build_pdf.build()
    except Exception as e:
        print(f"  WARN: PDF generation failed: {e}")

    print(f"\nDone -> {OUT}")

if __name__ == "__main__":
    if "--serve" in sys.argv:
        build_all()
        os.chdir(OUT)
        print("\nServing http://localhost:8000 (Ctrl+C to stop)")
        HTTPServer(("", 8000), SimpleHTTPRequestHandler).serve_forever()
    else:
        build_all()