"""
Static site generator — dynamic sections, Lucide icons via CDN.

Usage:
    python build.py
    python build.py --serve
    python build.py --clean
"""

import json
import re
import shutil
import sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent
TEMPLATES = ROOT / "templates"
PARTIALS = TEMPLATES / "partials"
STATIC = ROOT / "static"
DATA_FILE = ROOT / "data" / "site.json"
OUT = ROOT / "public"

TOKEN = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def icon(name):
    if not name:
        return ""
    return f'<i data-lucide="{name}"></i>'


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
    return value


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
    return "\n          ".join(
        f'<a href="{a["href"]}" class="btn btn-{a.get("style", "primary")}">{a["label"]}</a>'
        for a in actions
    )


def meta_html(meta):
    out = []
    for m in meta:
        out.append(f'<li><span class="icon">{icon(m.get("icon", ""))}</span> {m["text"]}</li>')
    return "\n          ".join(out)


def paragraphs_html(paragraphs):
    return "\n          ".join(f"<p>{p}</p>" for p in paragraphs)


def facts_html(facts):
    return "\n          ".join(
        f'<li><strong>{f["label"]}</strong><span>{f["value"]}</span></li>'
        for f in facts
    )


def prepare(site):
    pages = site["pages"]
    year = datetime.now().year

    home = pages.get("home", {})
    if "actions" in home:
        home["actions_html"] = actions_html(home["actions"])
    if "meta" in home:
        home["meta_html"] = meta_html(home["meta"])

    about = pages.get("about", {})
    if "paragraphs" in about:
        about["paragraphs_html"] = paragraphs_html(about["paragraphs"])
    if "facts" in about:
        about["facts_html"] = facts_html(about["facts"])


    prof = about.get("profile", {})
    if prof:
        facts = []
        for f in prof.get("facts", []):
            facts.append(
                f'<div class="profile-card-fact">'
                f'<dt>{f["label"]}</dt><dd>{f["value"]}</dd></div>'
            )
        prof["facts_html"] = "\n".join(facts)

        links = []
        for l in prof.get("links", []):
            target = ' target="_blank" rel="noopener"' if l["href"].startswith("http") else ""
            links.append(
                f'<a class="profile-card-link" href="{l["href"]}"{target}>'
                f'<i data-lucide="{l.get("icon", "link")}"></i>'
                f'<span>{l["label"]}</span></a>'
            )
        prof["links_html"] = "\n".join(links)

    for page_data in pages.values():
        if "body" in page_data:
            page_data["body_html"] = paragraphs_html(page_data["body"])

    for skill in site.get("skills", []):
        skill["tags_html"] = tags_html(skill["tags"])

    for project in site.get("projects", []):
        project["tags_html"] = tags_html(project["tags"])
        project["links_html"] = links_html(project["links"])
        project["placeholder_class"] = (
            "project-placeholder" if project.get("placeholder") else ""
        )
        project["status_attr"] = (
            f'data-status="{project["status"]}"' if project.get("status") else ""
        )

    for contact in site.get("contacts", []):
        contact["target_attr"] = (
            'target="_blank" rel="noopener"' if contact.get("external") else ""
        )
        contact["icon_svg"] = icon(contact.get("icon", ""))

    cv = site.get("cv", {})
    for skill in cv.get("skills", []):
        skill["tags_html"] = tags_html(skill["tags"])
    for project in cv.get("projects", []):
        project["tags_html"] = tags_html(project["tags"])
        if project.get("href"):
            project["title_html"] = (
                f'<a href="{project["href"]}" target="_blank" rel="noopener">{project["title"]}</a>'
            )
        else:
            project["title_html"] = project["title"]
    if "cv" in pages and "interests" in pages["cv"]:
        pages["cv"]["interests_html"] = "".join(
            f"<li>{item}</li>" for item in pages["cv"]["interests"]
        )

    # Hide References section if references_show is false
    cv_page = pages.get("cv", {})
    if not cv_page.get("references_show", False):
        tpl = site.get("section_templates", {}).get("cv", "")
        if "references_heading" in tpl:
            tpl = re.sub(
                r"\s*<section class=\"cv-section\">\s*"
                r"<h2 class=\"cv-section-title\">\{\{\s*page\.references_heading\s*\}\}</h2>"
                r".*?</section>",
                "", tpl, flags=re.DOTALL,
            )
            site["section_templates"]["cv"] = tpl

    footer = site.get("footer", {})
    footer["copyright_html"] = footer.get("copyright", "").replace("{year}", str(year))

    return site


def build_nav(nav, current_file):
    out = []
    for item in nav:
        classes = []
        if item.get("cta"):
            classes.append("nav-cta")
        if item.get("file") == current_file:
            classes.append("active")
        cls = f' class="{" ".join(classes)}"' if classes else ""
        out.append(f'<li><a href="{item["href"]}"{cls}>{item["label"]}</a></li>')
    return "\n        ".join(out)


def render_section(section_id, site, page_data):
    templates = site.get("section_templates", {})
    tpl = templates.get(section_id)
    if not tpl:
        return f"<!-- unknown section: {section_id} -->"
    ctx = {"site": site, "page": page_data}
    if section_id == "skills":
        ctx["skill_cards"] = render_partials("skill_card.html", site["skills"])
    elif section_id == "projects":
        ctx["project_cards"] = render_partials("project_card.html", site["projects"])
    elif section_id == "timeline":
        ctx["timeline_items"] = render_partials("timeline_item.html", site["education"])
    elif section_id == "contact":
        ctx["contact_cards"] = render_partials("contact_card.html", site["contacts"])
    elif section_id == "cv":
        ctx["cv_education_items"] = render_partials(
            "cv_education_item.html", site["cv"]["education"]
        )
        ctx["cv_skill_items"] = render_partials(
            "cv_skill_item.html", site["cv"]["skills"]
        )
        ctx["cv_project_items"] = render_partials(
            "cv_project_item.html", site["cv"]["projects"]
        )
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
    (OUT / out_file).write_text(final, encoding="utf-8")
    print(f"  ok {out_file}")
    return out_file


def build_all():
    if not OUT.exists():
        OUT.mkdir(parents=True)
    raw = DATA_FILE.read_text(encoding="utf-8-sig")
    site = prepare(json.loads(raw))
    print(f"Building: {site['title']}")
    outputs = set()
    for page_key, page_data in site["pages"].items():
        outputs.add(build_page(page_key, page_data, site))
    for existing in OUT.glob("*.html"):
        if existing.name not in outputs:
            try:
                existing.unlink()
                print(f"  removed stale {existing.name}")
            except PermissionError:
                print(f"  (skipped locked {existing.name})")
    print("Copying static assets...")
    shutil.copytree(STATIC, OUT / "static", dirs_exist_ok=True)

    # Generate CV PDF from site.json
    print("Generating CV PDF...")
    try:
        import importlib, build_pdf
        importlib.reload(build_pdf)
        build_pdf.build()
    except Exception as e:
        print(f"  WARN: PDF generation failed: {e}")
    print(f"\nDone -> {OUT}")


def serve():
    build_all()
    import os
    os.chdir(OUT)
    print("\nServing http://localhost:8000 (Ctrl+C to stop)")
    HTTPServer(("", 8000), SimpleHTTPRequestHandler).serve_forever()


def clean():
    if OUT.exists():
        try:
            shutil.rmtree(OUT)
            print(f"Removed {OUT}")
        except PermissionError as e:
            print(f"Could not remove {OUT}: {e}")
    else:
        print("Nothing to clean.")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()
    elif "--clean" in sys.argv:
        clean()
    else:
        build_all()