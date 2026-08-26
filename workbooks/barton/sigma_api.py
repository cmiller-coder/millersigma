"""Minimal Sigma REST helpers shared by the Barton build scripts."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (REPO / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key] = value.strip("'\"")
    return env


def _token(env: dict[str, str]) -> str:
    fetcher = env.get("SIGMA_TOKEN_FETCHER", str(REPO / "scripts/get-token-staging.sh"))
    proc = subprocess.run(
        ["bash", fetcher],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        check=True,
    )
    return proc.stdout.strip().split("=", 1)[1].strip("'\"")


def api(method: str, path: str, body: dict | None = None, *, raw: bool = False):
    env = _env()
    token = _token(env)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        env["SIGMA_BASE_URL"] + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = resp.read()
            return payload if raw else json.loads(payload)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} on {method} {path}\n{exc.read().decode()[:4000]}")


def render_page_png(workbook_id: str, page_id: str, out_path: Path, timeout_s: int = 180) -> Path:
    """Export a workbook page as PNG — the only way to visually verify a build headlessly."""
    job = api("POST", f"/v2/workbooks/{workbook_id}/export",
              {"pageId": page_id, "format": {"type": "png"}})
    query_id = job["queryId"]
    env = _env()
    token = _token(env)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        req = urllib.request.Request(
            f"{env['SIGMA_BASE_URL']}/v2/query/{query_id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(data)
                return out_path
        except urllib.error.HTTPError:
            pass
        time.sleep(2)
    raise SystemExit(f"PNG export timed out after {timeout_s}s (queryId={query_id})")
