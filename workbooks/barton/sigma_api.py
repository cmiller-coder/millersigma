"""Minimal Sigma REST helpers shared by the Barton build scripts."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _env() -> dict[str, str]:
    env: dict[str, str] = dict(os.environ)
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key] = value.strip("'\"")
    # A machine often holds staging credentials in SIGMA_CLIENT_ID/SECRET while the
    # Barton org needs its own. SIGMA_BARTON_* wins when present so the same
    # builders publish to Barton without editing anything.
    if not env.get("SIGMA_DISABLE_BARTON_OVERRIDES"):
        for key in ("CLIENT_ID", "CLIENT_SECRET", "BASE_URL"):
            override = env.get(f"SIGMA_BARTON_{key}")
            if override:
                env[f"SIGMA_{key}"] = override

    env.setdefault("SIGMA_TOKEN_FETCHER", str(REPO / "scripts/get-token-staging.sh"))
    missing = [k for k in ("SIGMA_BASE_URL", "SIGMA_CLIENT_ID", "SIGMA_CLIENT_SECRET")
               if not env.get(k)]
    if missing:
        raise RuntimeError(
            f"missing {', '.join(missing)} — set them (or the SIGMA_BARTON_* "
            "equivalents) for the org you are publishing to"
        )
    return env


TOKEN_TTL_S = 45 * 60


def _token(env: dict[str, str]) -> str:
    """Bearer token, cached on disk — the auth endpoint rate-limits repeat calls."""
    cache = Path(tempfile.gettempdir()) / (
        ".sigma_token_" + hashlib.sha256(env["SIGMA_BASE_URL"].encode()).hexdigest()[:12]
    )
    if cache.exists() and time.time() - cache.stat().st_mtime < TOKEN_TTL_S:
        cached = cache.read_text().strip()
        if cached:
            return cached

    fetcher = env.get("SIGMA_TOKEN_FETCHER", str(REPO / "scripts/get-token-staging.sh"))
    proc = subprocess.run(
        ["bash", fetcher],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        check=True,
    )
    token = proc.stdout.strip().split("=", 1)[1].strip("'\"")
    cache.write_text(token)
    cache.chmod(0o600)
    return token


def api(method: str, path: str, body: dict | None = None, *, raw: bool = False):
    status, payload = try_api(method, path, body, raw=raw)
    if status >= 400:
        text = payload.decode() if isinstance(payload, (bytes, bytearray)) else str(payload)
        raise SystemExit(f"HTTP {status} on {method} {path}\n{text[:4000]}")
    return payload


def try_api(method: str, path: str, body: dict | None = None, *, raw: bool = False):
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
            return resp.status, (payload if raw else json.loads(payload))
    except urllib.error.HTTPError as exc:
        raw_body = exc.read()
        try:
            parsed = json.loads(raw_body)
        except Exception:
            parsed = raw_body.decode()[:4000]
        return exc.code, parsed


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
