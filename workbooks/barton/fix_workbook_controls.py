#!/usr/bin/env python3
"""Patch list-control sources on a Barton workbook so filter dropdowns populate."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from barton_controls import fix_filter_control_sources

REPO = Path(__file__).resolve().parents[2]
DEFAULT_WORKBOOK_ID = "f2edaf68-e3f8-44eb-afef-3383f821423f"  # POC Test (1) url 7ooLsQk4SddzIlEr4m3nKT


def api(method: str, path: str, body: dict | None = None) -> dict:
    env = {}
    for line in (REPO / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    proc = subprocess.run(
        ["bash", str(REPO / "scripts/get-token-staging.sh")],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        check=True,
    )
    token = proc.stdout.strip().split("=", 1)[1].strip("'\"")
    base = env["SIGMA_BASE_URL"]
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base + path,
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
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code}\n{exc.read().decode()[:5000]}")


def main() -> None:
    wb_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WORKBOOK_ID
    spec = api("GET", f"/v2/workbooks/{wb_id}/spec")
    n = fix_filter_control_sources(spec["document"])
    payload = {
        "name": spec["name"],
        "folderId": spec["folderId"],
        "document": spec["document"],
    }
    api("PUT", f"/v2/workbooks/{wb_id}/spec", payload)
    print(f"Fixed {n} list controls on workbook {wb_id}")


if __name__ == "__main__":
    main()
