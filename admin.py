"""
Local admin server for Edwin Tony's portfolio.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import urllib.request
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from datetime import datetime

# Load .env file if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"
ADMIN = ROOT / "admin"
DATA_FILE = ROOT / "data" / "site.json"
MESSAGES_FILE = ROOT / "data" / "messages.json"
AUTH_FILE = ROOT / "admin_auth.json"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean.startswith("/edwin-portfolio/"):
            clean = clean.replace("/edwin-portfolio/", "/", 1)
        if clean in ("/admin", "/admin/", "/admin.html"):
            return str(ADMIN / "index.html")
        if clean.startswith("/admin/"):
            return str(ADMIN / clean[len("/admin/"):])
        return super().translate_path(clean)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        # SERVER-MAINTENANCE: Serve maintenance page directly without 302 redirect
        _p = self.path.split("?", 1)[0].split("#", 1)[0]
        if _p.startswith("/edwin-portfolio/"):
            _p = _p.replace("/edwin-portfolio/", "/", 1)
        
        if _p not in ("/maintenance.html", "/admin", "/admin/", "/api/site", "/api/messages",
                      "/api/analytics", "/api/uptime", "/api/server-status") and not _p.startswith("/static/"):
            try:
                _cfg = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
                if _cfg.get("site_config", {}).get("maintenance_mode") or _cfg.get("maintenance_mode"):
                    self.path = "/maintenance.html"
                    super().do_GET()
                    return
            except Exception:
                pass

        # 1. API: Messages


        if self.path == "/api/messages":
            try:
                if not MESSAGES_FILE.exists():
                    self._json(200, [])
                else:
                    self._json(200, json.loads(MESSAGES_FILE.read_text(encoding="utf-8")))
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        # 2. API: Analytics (GoatCounter)
        if self.path == "/api/analytics":
            try:
                token = os.environ.get("GOATCOUNTER_API_TOKEN")
                if not token:
                    self._json(500, {"error": "GOATCOUNTER_API_TOKEN is not set. Check your .env file."})
                    return

                base_url = "https://edwinton.goatcounter.com/api/v0/stats"
                
                def fetch(endpoint, key):
                    url = f"{base_url}/{endpoint}?limit=10"
                    req = urllib.request.Request(url)
                    req.add_header("Authorization", f"Bearer {token}")
                    req.add_header("Content-Type", "application/json")
                    try:
                        with urllib.request.urlopen(req) as response:
                            data = json.loads(response.read().decode())
                            return data.get(key, [])
                    except Exception as e:
                        print(f"API Error for {endpoint}: {e}")
                        return []

                hits = fetch("hits", "hits")
                locations = fetch("locations", "stats")
                browsers = fetch("browsers", "stats")
                systems = fetch("systems", "stats")
                referrers = fetch("refs", "stats")
                sizes = fetch("sizes", "stats")
                languages = fetch("languages", "stats")
                
                # Fetch daily hits for the chart
                daily_req = urllib.request.Request(f"{base_url}/hits?daily=true&limit=7")
                daily_req.add_header("Authorization", f"Bearer {token}")
                daily_req.add_header("Content-Type", "application/json")
                try:
                    with urllib.request.urlopen(daily_req) as response:
                        daily_data = json.loads(response.read().decode()).get("hits", [])
                except:
                    daily_data = []

                # Merge Screen Sizes
                size_map = {0: "Desktop", 1: "Mobile", 2: "Tablet", 3: "Desktop (Large)", 4: "Mobile (Small)", 5: "Tablet (Large)", 6: "Unknown", "0": "Desktop", "1": "Mobile", "2": "Tablet"}
                merged_sizes = {}
                for s in sizes:
                    raw_id = s.get("path", s.get("name", 0))
                    label = size_map.get(raw_id, "Desktop")
                    count = s.get("count", 0)
                    merged_sizes[label] = merged_sizes.get(label, 0) + count
                sizes = [{"name": k, "count": v} for k, v in merged_sizes.items()]
                sizes.sort(key=lambda x: x["count"], reverse=True)

                # Map languages
                for l in languages:
                    lang = l.get("name", "")
                    if not lang or lang == "(unknown)" or lang == "Unknown":
                        l["name"] = "English / Unknown"
                    else:
                        l["name"] = lang.split("-")[0].upper()

                self._json(200, {
                    "hits": hits,
                    "locations": locations,
                    "browsers": browsers,
                    "systems": systems,
                    "referrers": referrers,
                    "sizes": sizes,
                    "languages": languages,
                    "daily": daily_data
                })
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        # 3. API: Uptime (UptimeRobot)
        if self.path == "/api/uptime":
            try:
                api_key = os.environ.get("UPTIMEROBOT_API_KEY", "YOUR_UPTIMEROBOT_API_KEY")
                if api_key == "YOUR_UPTIMEROBOT_API_KEY":
                    self._json(200, {"status": "unconfigured", "uptime_ratio": "N/A", "avg_response": "N/A"})
                    return

                url = "https://api.uptimerobot.com/v2/getMonitors"
                data = urllib.parse.urlencode({"api_key": api_key, "format": "json"}).encode()
                req = urllib.request.Request(url, data=data, method="POST")
                
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode())
                    if result.get("stat") == "ok" and result.get("monitors"):
                        monitor = result["monitors"][0]
                        self._json(200, {
                            "status": "up" if monitor.get("status") == 2 else "down",
                            "uptime_ratio": monitor.get("custom_uptime_ratio", "100%"),
                            "avg_response": monitor.get("average_response_time", "0")
                        })
                    else:
                        self._json(500, {"error": "UptimeRobot API error"})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        # 4. API: Server Status (GitHub Actions)
        if self.path == "/api/server-status":
            try:
                gh_token = "YOUR_GITHUB_TOKEN"
                req = urllib.request.Request("https://api.github.com/repos/Edwinton/edwin-portfolio/actions/runs?per_page=3")
                req.add_header("User-Agent", "Python-Admin-Dashboard")
                if gh_token and gh_token != "YOUR_GITHUB_TOKEN":
                    req.add_header("Authorization", f"Bearer {gh_token}")

                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    runs = data.get("workflow_runs", [])
                    status_list = []
                    for run in runs:
                        status_list.append({
                            "name": run.get("name", "Deploy"),
                            "status": "Success" if run.get("conclusion") == "success" else "Failed",
                            "date": run.get("created_at", "")[:10],
                            "url": run.get("html_url", "")
                        })
                    self._json(200, {"runs": status_list})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        # 5. API: Get site data
        if self.path == "/api/site":
            try:
                self._json(200, json.loads(DATA_FILE.read_text(encoding="utf-8-sig")))
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
            
        super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if self.path == "/api/hire":
            try:
                data = json.loads(body.decode("utf-8"))
                messages = []
                if MESSAGES_FILE.exists():
                    messages = json.loads(MESSAGES_FILE.read_text(encoding="utf-8"))
                
                messages.insert(0, {
                    "id": str(int(datetime.now().timestamp())),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "name": data.get("name", "Unknown"),
                    "email": data.get("email", "Unknown"),
                    "message": data.get("message", "")
                })
                MESSAGES_FILE.write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding="utf-8")
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(400, {"error": str(e)})
            return

        if self.path == "/api/site":
            try:
                data = json.loads(body.decode("utf-8"))
                DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(400, {"error": str(e)})
            return

        if self.path == "/api/build":
            try:
                result = subprocess.run([sys.executable, "build.py"], cwd=ROOT, capture_output=True, text=True, timeout=60)
                self._json(200, {"ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        self._json(404, {"error": "not found"})

    def _json(self, status, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args): pass

def main():
    port = 8000
    if not PUBLIC.exists():
        print("public/ not found. Run: python build.py")
        sys.exit(1)
    print(f"Public : http://localhost:{port}/")
    print(f"Admin  : http://localhost:{port}/admin")
    print("Ctrl+C to stop.\n")
    HTTPServer(("", port), Handler).serve_forever()

if __name__ == "__main__":
    main()