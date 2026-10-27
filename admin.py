"""
Local admin server for Edwin Tony's portfolio — password protected.
Serves public/ + admin page, JSON API to edit site.json, triggers rebuilds.

Auth: HTTP Basic (browser popup). Credentials from admin_auth.json.
If admin_auth.json doesn't exist, the server warns and refuses admin access.

First-time setup:
    python set-password.py

Then run:
    python admin.py
"""

import base64
import hashlib
import hmac
import json
import secrets
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"
ADMIN = ROOT / "admin"
DATA_FILE = ROOT / "data" / "site.json"
AUTH_FILE = ROOT / "admin_auth.json"

AUTH_REALM = "Edwin Portfolio Admin"


def load_auth():
    """Return {user: password_hash} dict, or None if not configured."""
    if not AUTH_FILE.exists():
        return None
    try:
        return json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def verify_password(username, password, auth_data):
    if not auth_data or "users" not in auth_data:
        return False
    stored = auth_data["users"].get(username)
    if not stored:
        return False
    # stored is {"salt": "...", "hash": "..."}
    salt = bytes.fromhex(stored["salt"])
    expected = bytes.fromhex(stored["hash"])
    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(expected, computed)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    # ---------- Auth ----------
    def _requires_auth(self):
        p = self.path.split("?", 1)[0]
        return (
            p in ("/admin", "/admin/", "/admin.html")
            or p.startswith("/admin/")
            or p.startswith("/api/")
        )

    def _check_auth(self):
        """Return True if authenticated. Sends 401 if not."""
        auth_data = load_auth()
        if auth_data is None:
            # No password file — refuse access
            body = b"No admin password configured.\n\nRun: python set-password.py"
            self.send_response(503)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return False

        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            self._send_401()
            return False
        try:
            decoded = base64.b64decode(header[6:]).decode("utf-8")
            username, _, password = decoded.partition(":")
        except Exception:
            self._send_401()
            return False

        if verify_password(username, password, auth_data):
            return True
        self._send_401()
        return False

    def _send_401(self):
        body = b"Authentication required."
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{AUTH_REALM}"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- Route /admin/* to admin folder ----------
    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean in ("/admin", "/admin/", "/admin.html"):
            return str(ADMIN / "index.html")
        if clean.startswith("/admin/"):
            return str(ADMIN / clean[len("/admin/"):])
        return super().translate_path(path)

    # ---------- JSON API ----------
    def do_GET(self):
        if self._requires_auth() and not self._check_auth():
            return

        if self.path == "/api/site":
            try:
                data = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        super().do_GET()

    def do_POST(self):
        if self._requires_auth() and not self._check_auth():
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if self.path == "/api/site":
            try:
                data = json.loads(body.decode("utf-8"))
                DATA_FILE.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(400, {"error": str(e)})
            return

        if self.path == "/api/build":
            try:
                result = subprocess.run(
                    [sys.executable, "build.py"],
                    cwd=ROOT, capture_output=True, text=True, timeout=60,
                )
                self._json(200, {
                    "ok": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                })
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

    def log_message(self, fmt, *args):
        pass


def main():
    port = 8000
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])

    if not PUBLIC.exists():
        print("public/ not found. Run: python build.py")
        sys.exit(1)

    if not AUTH_FILE.exists():
        print("!" * 60)
        print("  WARNING: admin_auth.json not found.")
        print("  Admin page will refuse access until you run:")
        print("     python set-password.py")
        print("!" * 60)
        print()

    print(f"Public : http://localhost:{port}/")
    print(f"Admin  : http://localhost:{port}/admin  (password required)")
    print("Ctrl+C to stop.\n")
    HTTPServer(("", port), Handler).serve_forever()


if __name__ == "__main__":
    main()