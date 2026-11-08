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
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from datetime import datetime

from pathlib import Path
from datetime import datetime
import os

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

    def do_GET(self):
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
                    raise RuntimeError("GOATCOUNTER_API_TOKEN is not set")
                base_url = "https://edwinton.goatcounter.com/api/v0/stats"
                
                def fetch(endpoint):
                    url = f"{base_url}/{endpoint}?limit=10"
                    req = urllib.request.Request(url)
                    req.add_header("Authorization", f"Bearer {token}")
                    req.add_header("Content-Type", "application/json")
                    with urllib.request.urlopen(req, timeout=15) as response:
                        return json.loads(response.read().decode("utf-8"))

                hits = fetch("hits")
                locations = fetch("locations")
                browsers = fetch("browsers")
                systems = fetch("systems")

                self._json(200, {
                    "hits": hits.get("hits", []),
                    "locations": locations.get("stats", []),
                    "browsers": browsers.get("stats", []),
                    "systems": systems.get("stats", [])
                })
            except Exception as e:
                self._json(502, {"error": f"GoatCounter analytics request failed: {e}"})
            return

        # 3. API: Get site data
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

        # API: Receive new hiring form message
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

        # API: Save site data (if you ever use the full admin panel again)
        if self.path == "/api/site":
            try:
                data = json.loads(body.decode("utf-8"))
                DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(400, {"error": str(e)})
            return

        # API: Trigger build
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
