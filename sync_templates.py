cd "C:\Users\User\OneDrive\Desktop\html page\edwin-portfolio"
$py = @'
"""
Sync templates/*.html -> site.json section_templates.
Run this after editing any template file, before building.

Usage:
    python sync_templates.py
    python sync_templates.py --check    # exit 1 if drift detected
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "site.json"
TEMPLATES = ROOT / "templates"

MAP = {
    "hero":     "home.html",
    "about":    "about.html",
    "skills":   "skills.html",
    "projects": "projects.html",
    "timeline": "education.html",
    "cv":       "cv.html",
    "contact":  "contact.html",
}

def main():
    check_only = "--check" in sys.argv
    data = json.loads(DATA.read_text(encoding="utf-8-sig"))
    templates = data.setdefault("section_templates", {})

    drift = []
    changed = 0
    for key, fname in MAP.items():
        f = TEMPLATES / fname
        if not f.exists():
            continue
        disk = f.read_text(encoding="utf-8")
        stored = templates.get(key, "")
        if disk != stored:
            drift.append(key)
            if not check_only:
                templates[key] = disk
                changed += 1

    if check_only:
        if drift:
            print(f"DRIFT in: {', '.join(drift)}")
            sys.exit(1)
        print("No drift — site.json matches templates/")
        return

    if changed == 0:
        print("All templates already in sync.")
        return

    DATA.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Synced {changed} template(s): {', '.join(drift)}")

if __name__ == "__main__":
    main()
'@
[System.IO.File]::WriteAllText("$PWD\sync_templates.py", $py, (New-Object System.Text.UTF8Encoding $false))
Write-Host "Created sync_templates.py" -ForegroundColor Green