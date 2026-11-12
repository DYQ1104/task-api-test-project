import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
DB_PATH = ROOT / "data" / "self_test.sqlite3"
BASE_URL = "http://127.0.0.1:18765"

def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw) if raw else None

def check(condition, label):
    if not condition:
        raise AssertionError(f"FAIL: {label}")
    print(f"PASS: {label}")

def main():
    if not PYTHON.exists():
        raise SystemExit(f"Virtualenv Python not found: {PYTHON}")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    env = os.environ.copy()
    env["TASK_API_DB"] = str(DB_PATH)
    process = subprocess.Popen([str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18765", "--log-level", "warning"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            if process.poll() is not None:
                raise RuntimeError(f"Service exited early with code {process.returncode}")
            try:
                status, payload = request("GET", "/health")
                if status == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Service did not become healthy within 10 seconds")
        check(payload == {"status": "ok"}, "health check returns ok")
        username = f"selftest_{int(time.time())}"
        password = "ExamplePass123"
        status, created = request("POST", "/api/v1/auth/register", {"username": username, "password": password})
        check(status == 201 and created["username"] == username, "register returns 201 and user profile")
        check("password" not in created and "password_hash" not in created, "register response excludes password")
        status, result = request("POST", "/api/v1/auth/register", {"username": username, "password": password})
        check(status == 409 and result["detail"]["code"] == "USERNAME_EXISTS", "duplicate username returns 409")
        status, login = request("POST", "/api/v1/auth/login", {"username": username, "password": password})
        check(status == 200 and login["token_type"] == "Bearer" and login["access_token"], "valid login returns bearer token")
        status, result = request("POST", "/api/v1/auth/login", {"username": username, "password": "WrongPass123"})
        check(status == 401 and result["detail"]["code"] == "INVALID_CREDENTIALS", "wrong password returns 401")
        conn = sqlite3.connect(DB_PATH)
        try:
            stored = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()[0]
        finally:
            conn.close()
        from app.auth import verify_password
        check(stored != password and stored.startswith("pbkdf2_sha256$"), "database stores PBKDF2 hash, not plaintext")
        check(verify_password(password, stored), "stored hash verifies correct password")
        check(not verify_password("WrongPass123", stored), "stored hash rejects incorrect password")
        print("\nSelf-test completed: all checks passed.")
    finally:
        process.kill()
        process.wait(timeout=10)
        # The self-test database is intentionally retained at data/self_test.sqlite3 for inspection.

if __name__ == "__main__":
    main()
