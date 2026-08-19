#!/usr/bin/env python3
"""Apply Barton Associates brand theming to the POC Test workbook."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKBOOK_ID = "3b65aa5b-c908-4b8d-bcb6-f177d74bb5ef"
LOGO_URI = (REPO / "workbooks/barton/logo.datauri.txt").read_text().strip()

# Barton brand — pulled from bartonassociates.com logo (#00A5A2 teal, #41454D slate)
TEAL = "#00A5A2"
TEAL_DARK = "#007A78"
TEAL_LIGHT = "#5BBFB8"
NAVY = "#1E3A4C"
NAVY_DEEP = "#0F2A3A"
SLATE = "#41454D"
CANVAS = "#EEF4F4"
CARD = "#FFFFFF"
BORDER = "#D4E8E7"
TEXT_MUTED = "#6B7B85"
WHITE = "#FFFFFF"
CATEGORICAL = [TEAL, TEAL_DARK, NAVY, TEAL_LIGHT, "#2D6B6A", "#7A8E99", "#8FD4D2", "#1A5050"]

KPI_GRADIENTS = [
    (NAVY_DEEP, TEAL_DARK),
    (NAVY, TEAL),
    (NAVY_DEEP, NAVY),
    (TEAL_DARK, TEAL_LIGHT),
    (NAVY, TEAL_DARK),
    (NAVY_DEEP, TEAL),
]

CARD_STYLE = {
    "backgroundColor": CARD,
    "borderColor": BORDER,
    "borderWidth": 1,
    "borderRadius": "round",
}


def b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def grad_uri(a: str, b: str, w: int = 520, h: int = 300) -> str:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="xMidYMid slice"><defs><linearGradient id="g" '
        f'x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/>'
        f'<stop offset="1" stop-color="{b}"/></linearGradient></defs>'
        f'<rect width="{w}" height="{h}" fill="url(#g)"/></svg>'
    )
    return "data:image/svg+xml;base64," + b64(svg)


def header_uri() -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 220" preserveAspectRatio="xMidYMid slice">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0.35">
      <stop offset="0%" stop-color="{NAVY_DEEP}"/>
      <stop offset="45%" stop-color="{NAVY}"/>
      <stop offset="100%" stop-color="{TEAL_DARK}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.82" cy="0.25" r="0.55">
      <stop offset="0%" stop-color="{TEAL}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{NAVY_DEEP}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1600" height="220" fill="url(#g)"/>
  <rect width="1600" height="220" fill="url(#glow)"/>
  <rect y="217" width="1600" height="3" fill="{TEAL}"/>
</svg>"""
    return "data:image/svg+xml;base64," + b64(svg)


def _env_token() -> tuple[str, str]:
    env = {}
    for line in (REPO / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k] = v
    base = env["SIGMA_BASE_URL"]
    proc = subprocess.run(
        ["bash", str(REPO / "scripts/get-token-staging.sh")],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        check=True,
    )
    token = proc.stdout.strip().split("=", 1)[1].strip("'\"")
    return base, token


def api(method: str, path: str, body: dict | None = None) -> dict:
    base, token = _env_token()
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
        raw = exc.read().decode()
        raise SystemExit(f"HTTP {exc.code} on {path}\n{raw[:4000]}")


def elem_by_id(elements: list[dict], eid: str) -> dict:
    for e in elements:
        if e.get("id") == eid:
            return e
    raise KeyError(eid)


def apply_theme(spec: dict) -> dict:
    doc = spec["document"]
    elements = doc["elements"]
    ids = {e["id"] for e in elements}

    # --- workbook theme settings ---
    doc["settings"] = {
        "theme": {
            "overrides": {
                "colors": {
                    "text": SLATE,
                    "highlight": TEAL,
                    "success": TEAL_DARK,
                    "warning": "#E1A32D",
                    "danger": "#D64545",
                    "darkMode": "hidden",
                },
                "colorOverrides": {
                    "backgroundCanvas": CANVAS,
                    "canvasBackground": CANVAS,
                },
                "categoricalScheme": CATEGORICAL,
                "backgroundColor": CANVAS,
                "elementBackgroundColor": CARD,
                "borderColor": BORDER,
                "borderRadius": "round",
                "space": {"unit": "small", "showElementPadding": "shown"},
                "fonts": {"dataFont": "Inter", "textFont": "Inter"},
            }
        }
    }

    header_bg = header_uri()

    # --- header containers ---
    for cid in ("container-hdr-p1", "container-hdr-p2"):
        c = elem_by_id(elements, cid)
        c["style"] = {"borderRadius": "round", "borderWidth": 0}
        c["backgroundImage"] = {
            "source": {"kind": "url", "url": header_bg},
            "style": {"fit": "cover"},
        }

    # --- logos + subtitles ---
    new_elements = [
        {
            "id": "logo-p1",
            "kind": "image",
            "source": {"kind": "url", "url": LOGO_URI},
            "style": {"fit": "contain"},
        },
        {
            "id": "text-subtitle-p1",
            "kind": "text",
            "body": "Locum tenens assignment booking, pipeline & contract performance",
            "verticalAlign": "middle",
            "style": {"color": "#C8E8E7"},
        },
        {
            "id": "logo-p2",
            "kind": "image",
            "source": {"kind": "url", "url": LOGO_URI},
            "style": {"fit": "contain"},
        },
        {
            "id": "text-subtitle-p2",
            "kind": "text",
            "body": "Specialty × status volume and governed assignment detail",
            "verticalAlign": "middle",
            "style": {"color": "#C8E8E7"},
        },
        {
            "id": "container-filters-p1",
            "kind": "container",
            "style": dict(CARD_STYLE),
        },
    ]
    for ne in new_elements:
        if ne["id"] not in ids:
            elements.append(ne)
            ids.add(ne["id"])

    elem_by_id(elements, "text-title-p1")["body"] = "## Assignment Booking & Pipeline"
    elem_by_id(elements, "text-title-p1")["style"] = {"color": WHITE}
    elem_by_id(elements, "text-title-p2")["body"] = "## Assignment Pipeline & Detail"
    elem_by_id(elements, "text-title-p2")["style"] = {"color": WHITE}
    elem_by_id(elements, "text-note-p1")["style"] = {"color": SLATE, "backgroundColor": "#F4FAFA"}

    # --- KPI gradient wrappers ---
    kpi_ids = [
        "kpi-booked",
        "kpi-avg-bill",
        "kpi-avg-pay",
        "kpi-avg-spread",
        "kpi-contract-value",
        "kpi-cancelled",
    ]
    wrap_ids = []
    for i, kid in enumerate(kpi_ids):
        wid = f"kpi-wrap-{kid.replace('kpi-', '')}"
        wrap_ids.append(wid)
        if wid not in ids:
            a, b = KPI_GRADIENTS[i % len(KPI_GRADIENTS)]
            elements.append(
                {
                    "id": wid,
                    "kind": "container",
                    "style": {"borderRadius": "round", "borderWidth": 0},
                    "backgroundImage": {
                        "source": {"kind": "url", "url": grad_uri(a, b)},
                        "style": {"fit": "cover"},
                    },
                }
            )
            ids.add(wid)
        kpi = elem_by_id(elements, kid)
        kpi["value"] = {"columnId": kpi["value"]["columnId"], "color": WHITE, "fontSize": 26}
        kpi["name"] = {
            "text": kpi.get("name", kid),
            "fontSize": 13,
            "color": "#E8F7F6",
        }
        kpi.pop("style", None)
        if "style" in kpi:
            del kpi["style"]
        kpi["layout"] = {"anchor": "middle"}

    elem_by_id(elements, "container-kpi-p1").pop("style", None)

    # --- charts ---
    chart_ids = [
        "chart-trend",
        "chart-rate-by-specialty",
        "chart-by-state",
        "chart-cancel-trend",
        "pivot-specialty-status",
    ]
    for cid in chart_ids:
        ch = elem_by_id(elements, cid)
        ch["style"] = dict(CARD_STYLE)
        ch["name"] = {
            "text": ch.get("name", cid),
            "fontWeight": "bold",
            "fontSize": 15,
            "color": SLATE,
        }

    tbl = elem_by_id(elements, "tbl-detail")
    tbl["style"] = dict(CARD_STYLE)
    tbl["name"] = {"text": "Assignment Detail", "fontWeight": "bold", "fontSize": 15, "color": SLATE}

    # --- layout ---
    kpi_layout = "\n".join(
        f'    <Container elementId="{wid}" type="grid" gridColumn="{1 + i * 4} / {5 + i * 4}" '
        f'gridRow="1 / 9" gridTemplateColumns="repeat(4, 1fr)" gridTemplateRows="repeat(8, 1fr)">\n'
        f'      <Element elementId="{kid}" gridColumn="1 / 5" gridRow="1 / 9"/>\n'
        f"    </Container>"
        for i, (wid, kid) in enumerate(zip(wrap_ids, kpi_ids))
    )

    doc["layout"] = f"""<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-overview">
  <Container elementId="container-hdr-p1" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-p1" gridColumn="1 / 6" gridRow="1 / 5"/>
    <Element elementId="text-title-p1" gridColumn="6 / 16" gridRow="1 / 3"/>
    <Element elementId="text-subtitle-p1" gridColumn="6 / 20" gridRow="3 / 5"/>
  </Container>
  <Container elementId="container-filters-p1" type="grid" gridColumn="1 / 25" gridRow="5 / 8" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-specialty" gridColumn="1 / 7" gridRow="1 / 4"/>
    <Element elementId="ctrl-state" gridColumn="7 / 13" gridRow="1 / 4"/>
    <Element elementId="ctrl-type" gridColumn="13 / 19" gridRow="1 / 4"/>
    <Element elementId="ctrl-status" gridColumn="19 / 25" gridRow="1 / 4"/>
  </Container>
  <Container elementId="container-kpi-p1" type="grid" gridColumn="1 / 25" gridRow="8 / 16" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
{kpi_layout}
  </Container>
  <Element elementId="ctrl-grain" gridColumn="1 / 5" gridRow="16 / 19"/>
  <Element elementId="chart-trend" gridColumn="5 / 25" gridRow="16 / 32"/>
  <Element elementId="chart-rate-by-specialty" gridColumn="1 / 13" gridRow="32 / 48"/>
  <Element elementId="chart-by-state" gridColumn="13 / 25" gridRow="32 / 48"/>
  <Element elementId="chart-cancel-trend" gridColumn="1 / 19" gridRow="48 / 64"/>
  <Element elementId="text-note-p1" gridColumn="19 / 25" gridRow="48 / 64"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-detail">
  <Container elementId="container-hdr-p2" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-p2" gridColumn="1 / 6" gridRow="1 / 5"/>
    <Element elementId="text-title-p2" gridColumn="6 / 16" gridRow="1 / 3"/>
    <Element elementId="text-subtitle-p2" gridColumn="6 / 20" gridRow="3 / 5"/>
    <Element elementId="ctrl-status-p2" gridColumn="16 / 21" gridRow="2 / 5"/>
    <Element elementId="ctrl-specialty-p2" gridColumn="21 / 25" gridRow="2 / 5"/>
  </Container>
  <Element elementId="pivot-specialty-status" gridColumn="1 / 25" gridRow="5 / 21"/>
  <Element elementId="tbl-detail" gridColumn="1 / 25" gridRow="21 / 45"/>
  <Element elementId="tbl-assignments" gridColumn="1 / 25" gridRow="45 / 47"/>
</Page>
"""

    spec["name"] = "POC Test"
    return spec


def main() -> None:
    spec = api("GET", f"/v2/workbooks/{WORKBOOK_ID}/spec")
    themed = apply_theme(spec)
    out = REPO / "workbooks/barton/spec-themed.json"
    payload = {
        "name": themed["name"],
        "folderId": themed["folderId"],
        "document": themed["document"],
    }
    out.write_text(json.dumps(payload, indent=2))
    api("PUT", f"/v2/workbooks/{WORKBOOK_ID}/spec", payload)
    print("✅ themed workbook updated", WORKBOOK_ID)
    print("   url:", themed.get("url", ""))


if __name__ == "__main__":
    main()
