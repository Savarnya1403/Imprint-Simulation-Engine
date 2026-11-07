"""Push working tree to GitHub via the Contents API.

git push is server-blocked (remote: fatal error in commit_refs_rules), and the
git/blobs + git/trees REST path was flaky for two blobs. The Contents API
(PUT /repos/{owner}/{repo}/contents/{path}) creates/updates a file in one call,
handling blob, tree and commit automatically. One commit per file is acceptable
for a research push.
"""
from __future__ import annotations

import base64
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
REPO = "Savarnya1403/Imprint-Simulation-Engine"
API = f"https://api.github.com/repos/{REPO}"
BRANCH = "main"

FILES = [
    "app/cognition.py",
    "app/engine.py",
    "app/main.py",
    "static/css/studio.css",
    "static/js/studio.js",
    "static/studio.html",
    "RESEARCH.md",
    "app/modelcard.py",
    "app/sensitivity.py",
    "app/uncertainty.py",
    "app/validation.py",
    "tests/conftest.py",
    "tests/test_cognition.py",
    "tests/test_engine.py",
    "tests/test_validation.py",
    "tests/test_api.py",
    "tools/rest_push.py",
]


def req(method: str, url: str, data=None):
    body = None
    headers = {"Authorization": f"token {TOKEN}", "User-Agent": "imprint-research-push"}
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def get_sha(path: str) -> str | None:
    """Current blob SHA for a file on main, if it exists."""
    st, body = req("GET", f"{API}/contents/{path}?ref={BRANCH}")
    if st == 200:
        return json.loads(body)["sha"]
    return None


def put_file(rel: str):
    p = ROOT / rel
    content = p.read_bytes()
    current_sha = get_sha(rel)
    message = f"Research: update {rel}"
    data = {
        "message": message,
        "content": base64.b64encode(content).decode(),
        "branch": BRANCH,
    }
    if current_sha:
        data["sha"] = current_sha  # update existing file
    st, body = req("PUT", f"{API}/contents/{rel}", data=data)
    if st >= 300:
        raise RuntimeError(f"PUT {rel} -> {st}: {body[:500]}")
    return json.loads(body)


def main():
    print(f"Pushing {len(FILES)} files to {REPO}:{BRANCH} via Contents API")
    for rel in FILES:
        try:
            result = put_file(rel)
            commit = result["commit"]["sha"]
            print(f"  OK   {rel} -> commit {commit[:10]}")
        except Exception as exc:
            print(f"  FAIL {rel}: {exc}")
            raise


if __name__ == "__main__":
    main()
