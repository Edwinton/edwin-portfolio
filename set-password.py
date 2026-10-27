"""
Set or change the admin password.

Usage:
    python set-password.py
    python set-password.py --username edwin

Writes admin_auth.json with a PBKDF2-SHA256 hashed password.
Never stores the plaintext password.
"""

import argparse
import getpass
import hashlib
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).parent
AUTH_FILE = ROOT / "admin_auth.json"
ITERATIONS = 200_000


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="edwin", help="Admin username (default: edwin)")
    args = parser.parse_args()

    print(f"Setting admin password for user '{args.username}'")
    pw1 = getpass.getpass("New password: ")
    if not pw1:
        print("Password cannot be empty.")
        return
    pw2 = getpass.getpass("Confirm password: ")
    if pw1 != pw2:
        print("Passwords do not match.")
        return

    salt = secrets.token_bytes(16)
    hashed = hash_password(pw1, salt)

    # Preserve other users if the file already exists
    data = {"users": {}}
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {"users": {}}
    data.setdefault("users", {})

    data["users"][args.username] = {
        "salt": salt.hex(),
        "hash": hashed.hex(),
        "iterations": ITERATIONS,
    }

    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved to {AUTH_FILE}")
    print(f"Log in as: {args.username}")


if __name__ == "__main__":
    main()