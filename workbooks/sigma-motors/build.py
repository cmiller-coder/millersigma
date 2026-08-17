#!/usr/bin/env python3
"""Build the Sigma Motors Market Signal workbook.

Visual target: the light, card-based EV/hybrid intelligence mockups
(navy chrome, white KPI tiles with icon + delta + sparkline, tinted AI
band, quick-questions rail, regional donuts + ranked bar + trend).

Usage:
  python3 workbooks/sigma-motors/build.py verify
  python3 workbooks/sigma-motors/build.py create
  python3 workbooks/sigma-motors/build.py update <workbookId>
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------------------
# Auth / org — this token's org is sigma-on-sigma (not papercranestaging).
# Folder is Maximus Redman's home folder; connection is Sigma Sample Database
# (the only Snowflake conn that resolved custom SQL in this environment).
# ---------------------------------------------------------------------------

BASE = os.environ.get("SIGMA_BASE_URL") or os.environ.get("SIGMA_API_HOST")
if not BASE:
    raise SystemExit("SIGMA_BASE_URL is required")
FOLDER = os.environ.get("SIGMA_FOLDER_ID", "5fc0b75e-b736-4389-b7b1-0a265f0db5cc")
# Snowflake connection used by the original Sigma Motors app (input tables + VALUES SQL).
CONN = os.environ.get("SIGMA_CONNECTION_ID", "a9d45cfe-ff65-4515-8193-a7072602a1ee")
TOKEN_CACHE = pathlib.Path("/tmp/.sigma_token")
HERE = pathlib.Path(__file__).resolve().parent

NAVY = "#0B1B3A"
NAVY_DEEP = "#071226"
BLUE = "#1B4FD6"
BLUE_SOFT = "#E8F1FF"
BLUE_MID = "#4C7DFF"
CANVAS = "#F3F5F8"
CARD = "#FFFFFF"
SURFACE = "#F8FAFC"
BORDER = "#E2E6EE"
TEXT = "#0B1B3A"
MUTED = "#5B6B7F"
GREEN = "#0F9F6E"
RED = "#E11D48"
GOLD = "#C9971A"
HYBRID = "#94A3B8"
EV_COLOR = BLUE
HY_COLOR = "#64748B"

NUM0 = {"kind": "number", "formatString": ",.0f",
        "digitGroupingSymbol": ",", "digitGroupingSize": [3]}
NUM1 = {"kind": "number", "formatString": ",.1f"}
PCT0 = {"kind": "number", "formatString": ".0%"}
MONEY_M = {"kind": "number", "formatString": "$,.2s", "currencySymbol": "$"}


def datauri_svg(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def header_bg(width=1600, height=160) -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0.35">
      <stop offset="0%" stop-color="{NAVY_DEEP}"/>
      <stop offset="55%" stop-color="{NAVY}"/>
      <stop offset="100%" stop-color="#12306A"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.86" cy="0.2" r="0.55">
      <stop offset="0%" stop-color="{BLUE_MID}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{NAVY}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#g)"/>
  <rect width="{width}" height="{height}" fill="url(#glow)"/>
  <rect y="{height-3}" width="{width}" height="3" fill="{BLUE}"/>
</svg>"""
    return datauri_svg(svg)


def wordmark() -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="56" viewBox="0 0 320 56">
  <rect x="0" y="8" width="40" height="40" rx="10" fill="{BLUE}"/>
  <path d="M12 36 L20 16 L28 36 Z" fill="#FFFFFF"/>
  <rect x="17" y="28" width="6" height="3" fill="{BLUE}"/>
  <text x="52" y="26" fill="#FFFFFF" font-family="Arial,Helvetica,sans-serif" font-size="16" font-weight="700" letter-spacing="2.4">SIGMA MOTORS</text>
  <text x="52" y="44" fill="#9DB4D8" font-family="Arial,Helvetica,sans-serif" font-size="9" letter-spacing="1.6">SUSTAINABLE. SCALABLE. AHEAD.</text>
</svg>"""
    return datauri_svg(svg)


def icon_badge(path_d: str, fill="#E8F1FF", stroke=BLUE, size=48) -> str:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">'
        f'<circle cx="{size/2}" cy="{size/2}" r="{size/2}" fill="{fill}"/>'
        f'<g transform="translate({size/4},{size/4}) scale({size/48})" fill="none" '
        f'stroke="{stroke}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        f'{path_d}</g></svg>'
    )
    return datauri_svg(svg)


ICO_ZAP = '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
ICO_LEAF = ('<path d="M11 20A7 7 0 0 1 9.8 6.8C15.5 5 19 2 20 2c0 1-3.5 4.5-4.8 10.2'
            'A7 7 0 0 1 11 20z"/><path d="M12 12c-3-3-6-4-9-4"/>')
ICO_CLOCK = ('<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>')
ICO_DOLLAR = ('<line x1="12" y1="1" x2="12" y2="23"/>'
              '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>')
ICO_PIN = ('<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/>'
           '<circle cx="12" cy="10" r="3"/>')
ICO_SPARK = ('<path d="M12 3l1.6 4.8L18.5 9.5 13.6 11.2 12 16 10.4 11.2 5.5 9.5 10.4 7.8z"/>'
             '<path d="M19 14l.8 2.4L22 17.2l-2.2.8L19 20.4l-.8-2.4L16 17.2l2.2-.8z"/>')
ICO_BATTERY = ('<rect x="2" y="7" width="16" height="10" rx="2"/><line x1="22" y1="11" x2="22" y2="13"/>'
               '<line x1="6" y1="11" x2="6" y2="13"/><line x1="10" y1="11" x2="10" y2="13"/>')
ICO_CHECK = '<polyline points="20 6 9 17 4 12"/>'
ICO_X = '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
ICO_PERCENT = ('<circle cx="12" cy="12" r="9"/><path d="M8 16l8-8"/>'
               '<circle cx="9" cy="9" r="1.5" fill="currentColor"/>'
               '<circle cx="15" cy="15" r="1.5" fill="currentColor"/>')


def token() -> str:
    if TOKEN_CACHE.exists() and time.time() - TOKEN_CACHE.stat().st_mtime < 55 * 60:
        cached = TOKEN_CACHE.read_text().strip()
        if cached:
            return cached
    cid = os.environ["SIGMA_CLIENT_ID"]
    csec = os.environ["SIGMA_CLIENT_SECRET"]
    cred = base64.b64encode(f"{cid}:{csec}".encode()).decode()
    req = urllib.request.Request(
        BASE + "/v2/auth/token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={"Authorization": "Basic " + cred,
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        tok = json.load(resp)["access_token"]
    TOKEN_CACHE.write_text(tok)
    os.chmod(TOKEN_CACHE, 0o600)
    return tok


def call(method: str, path: str, body=None, retry=True):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Authorization": "Bearer " + token(), "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        if exc.code == 401 and retry:
            TOKEN_CACHE.unlink(missing_ok=True)
            return call(method, path, body, retry=False)
        try:
            pretty = json.dumps(json.loads(raw), indent=2)
        except ValueError:
            pretty = raw
        raise RuntimeError(f"HTTP {exc.code} {method} {path}\n{pretty}") from None
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Data — one monthly grain + one regional grain + per-region donut slices.
# Numbers are the mockup's: 4,120 EV / 610 hybrid / 6.2 wk / $1.80M / 2 regions.
# Regional EV units sum to 4,120 so the ranked bar and the headline KPI agree.
# ---------------------------------------------------------------------------

MONTH_SQL = """
SELECT DATE '2025-01-01' AS "Month", 2140 AS "EV Waitlist", 380 AS "Hybrid Waitlist",
       4.1 AS "Longest Backlog Wks", 950000 AS "Margin at Risk", 1 AS "Regions at Risk",
       'History' AS "Period Name"
UNION ALL SELECT DATE '2025-02-01', 2480, 420, 4.4, 1100000, 1, 'History'
UNION ALL SELECT DATE '2025-03-01', 2860, 470, 4.8, 1250000, 1, 'History'
UNION ALL SELECT DATE '2025-04-01', 3280, 520, 5.3, 1450000, 2, 'History'
UNION ALL SELECT DATE '2025-05-01', 3720, 570, 5.8, 1620000, 2, 'Prior'
UNION ALL SELECT DATE '2025-06-01', 4120, 610, 6.2, 1800000, 2, 'Current'
"""

REGION_SQL = """
SELECT 'Southwest' AS "Region", 1 AS "Region Order", 1412 AS "EV Backlog", 74 AS "Hybrid Backlog",
       0.95 AS "EV Share", 5.1 AS "Backlog Weeks", 3.2 AS "Delta Weeks", 1 AS "At Risk",
       51 AS "EV Growth Pct"
UNION ALL SELECT 'West', 2, 1120, 110, 0.91, 6.2, 2.1, 1, 42
UNION ALL SELECT 'Midwest', 3, 780, 148, 0.84, 3.8, 0.8, 0, 18
UNION ALL SELECT 'Northeast', 4, 468, 140, 0.77, 2.9, -0.3, 0, 9
UNION ALL SELECT 'South', 5, 340, 138, 0.71, 2.4, -0.6, 0, 6
"""

REALLOC_SQL = """
SELECT 'Southwest' AS "Region", 1412 AS "Current EV", 1680 AS "Recommended EV",
       268 AS "Units to Shift", 'Raise allocation — 5.1 wk backlog, 95% EV mix' AS "Rationale"
UNION ALL SELECT 'West', 1120, 1360, 240, 'Secure cells first; longest wait at 6.2 weeks'
UNION ALL SELECT 'Midwest', 780, 760, -20, 'Hold; backlog still under the 5-week threshold'
UNION ALL SELECT 'Northeast', 468, 430, -38, 'Reallocate hybrid-heavy leftover to SW / West'
UNION ALL SELECT 'South', 340, 310, -30, 'Reallocate; EV share and wait are both lowest'
"""

FLEET_SQL = """
SELECT * FROM VALUES
    ('EV', 5600, 75),
    ('Hybrid', 7300, 14)
  AS f(powertrain, baseline_units, cell_kwh_per_unit)
"""

RAMP_SQL = """
SELECT * FROM VALUES
    (0, 'M0', 0.0),
    (1, 'M1', 0.16666666666666666),
    (2, 'M2', 0.3333333333333333),
    (3, 'M3', 0.5),
    (4, 'M4', 0.6666666666666666),
    (5, 'M5', 0.8333333333333334),
    (6, 'M6', 1.0)
  AS r(month_idx, month_label, ramp_fraction)
  ORDER BY month_idx ASC
"""

FS = "Fleet Scenario"
FB = "Fleet Baseline"
RM = "Rollout Months"
SR = "Scenario Registry"

AI_PG2_BODY = (
    '{{Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", "CLAUDE-4-SONNET", '
    '"You are a manufacturing operations analyst advising an automaker\'\'s executive team. '
    'Baseline production is 5,600 EV units and 7,300 Hybrid units. A planner is evaluating a " '
    '& Text([c_ev_shift]) & "-point EV-share shift, which moves margin by roughly $" '
    '& Text(Round([c_ev_shift] * 42)) & "K and changes production to " '
    '& Text(Sum([Fleet Scenario/Units]) / 2 + 56 * [c_ev_shift]) & " EV units and " '
    '& Text(7300 - 56 * [c_ev_shift]) & " Hybrid units. At that level, battery-cell '
    'supply-contract commitment would be " & Text(Round(100 * (522200 + 3416 * [c_ev_shift]) / 581628, 1)) '
    '& "%. In 2-3 sentences, tell the executive team whether this shift is feasible given battery-cell '
    'supply, and name the binding constraint if it is at risk of being breached. If the shift is 0, '
    'just describe the baseline position."), \'"\', "")}}'
)


elements: list[dict] = []
agents: list[dict] = []


def add(el: dict) -> str:
    elements.append(el)
    return el["id"]


def sql_table(eid: str, name: str, statement: str, colnames: list[str], prefix: str) -> None:
    add({
        "id": eid, "kind": "table", "name": name,
        "source": {"connectionId": CONN, "kind": "sql", "statement": statement},
        "columns": [{"id": f"{prefix}{i}", "name": n, "formula": f"[Custom SQL/{n}]"}
                    for i, n in enumerate(colnames)],
    })


def card() -> dict:
    return {"backgroundColor": CARD, "borderRadius": "round",
            "borderColor": BORDER, "borderWidth": 1}


def panel() -> dict:
    return {"backgroundColor": SURFACE, "borderRadius": "round",
            "borderColor": BORDER, "borderWidth": 1}


def eyebrow(text: str) -> str:
    return f'<span style="color: {BLUE}; font-size: 10px">**{text}**</span>'


def section_title(text: str) -> str:
    return f'**<span style="color: {TEXT}; font-size: 15px">{text}</span>**'


def section_subtitle(text: str) -> str:
    return f'<span style="color: {MUTED}; font-size: 12px">{text}</span>'


def title(text: str, size=13) -> dict:
    return {"text": text, "color": TEXT, "fontWeight": "bold", "fontSize": size}


def img(eid: str, url: str) -> None:
    add({"id": eid, "kind": "image",
         "source": {"kind": "url", "url": url},
         "style": {"fit": "contain", "align": "start", "padding": "none"}})


def md(eid: str, body: str, **style) -> None:
    add({"id": eid, "kind": "text", "body": body,
         "style": {"backgroundColor": "transparent", "padding": "none", **style},
         "verticalAlign": "middle"})


def nav(idx: int) -> dict:
    return {
        "id": f"nav{idx}", "kind": "navigation", "mode": "manual", "showIcons": False,
        "optionStyle": {"textColor": "#C7D4EA", "selectedColor": "#FFFFFF",
                        "style": "pill", "orientation": "horizontal"},
        "options": [
            {"label": "Market Signal", "destination": {"type": "page", "pageId": "pg1"}},
            {"label": "EV & Hybrid Reallocation", "destination": {"type": "page", "pageId": "pg2"}},
            {"label": "Approvals", "destination": {"type": "page", "pageId": "pg3"}},
        ],
    }


# ---- sources
sql_table("tbl-month", "Monthly Pulse", MONTH_SQL,
          ["Month", "EV Waitlist", "Hybrid Waitlist", "Longest Backlog Wks",
           "Margin at Risk", "Regions at Risk", "Period Name"], "m")
sql_table("tbl-region", "Regional Pulse", REGION_SQL,
          ["Region", "Region Order", "EV Backlog", "Hybrid Backlog",
           "EV Share", "Backlog Weeks", "Delta Weeks", "At Risk", "EV Growth Pct"], "r")
sql_table("tbl-realloc", "Reallocation Plan", REALLOC_SQL,
          ["Region", "Current EV", "Recommended EV", "Units to Shift", "Rationale"], "x")
add({
    "id": "sql-fleet", "kind": "table", "name": FB,
    "source": {"connectionId": CONN, "kind": "sql", "statement": FLEET_SQL},
    "columns": [
        {"id": "fl-pt", "formula": "[Custom SQL/POWERTRAIN]", "name": "Powertrain"},
        {"id": "fl-base", "formula": "[Custom SQL/BASELINE_UNITS]", "name": "Baseline Units"},
        {"id": "fl-cellkwh", "formula": "[Custom SQL/CELL_KWH_PER_UNIT]", "name": "Cell Kwh Per Unit"},
    ],
})
add({
    "id": "sql-ramp", "kind": "table", "name": RM,
    "source": {"connectionId": CONN, "kind": "sql", "statement": RAMP_SQL},
    "columns": [
        {"id": "rm-idx", "formula": "[Custom SQL/MONTH_IDX]", "name": "Month Index"},
        {"id": "rm-label", "formula": "[Custom SQL/MONTH_LABEL]", "name": "Month"},
        {"id": "rm-frac", "formula": "[Custom SQL/RAMP_FRACTION]", "name": "Ramp Fraction"},
    ],
})

SHARES = [
    ("sw", "Southwest", 1412, 74, "95%", "↑ 5.1 wks"),
    ("we", "West", 1120, 110, "91%", "↑ 6.2 wks"),
    ("mw", "Midwest", 780, 148, "84%", "↑ 3.8 wks"),
    ("ne", "Northeast", 468, 140, "77%", "↓ 2.9 wks"),
    ("so", "South", 340, 138, "71%", "↓ 2.4 wks"),
]
for key, region, ev, hy, _pct, _wks in SHARES:
    sql_table(
        f"tbl-{key}", f"Share {region}",
        f"SELECT 'EV' AS \"Category\", {ev} AS \"Units\" UNION ALL SELECT 'Hybrid', {hy}",
        ["Category", "Units"], key,
    )

add({
    "id": "tbl-fleet-scenario", "kind": "table", "name": FS,
    "source": {"elementId": "sql-fleet", "kind": "table"},
    "columns": [
        {"id": "fs-pt", "formula": f"[{FB}/Powertrain]", "name": "Powertrain", "hidden": True},
        {"id": "fs-factor", "formula": (
            'If([Powertrain] = "EV", 1 + [c_ev_shift] * 56 / [Fleet Baseline/Baseline Units], '
            '1 - [c_ev_shift] * 56 / [Fleet Baseline/Baseline Units])'
        ), "name": "Factor", "hidden": True},
        {"id": "fs-units", "formula": "Round([Fleet Baseline/Baseline Units] * [Factor])",
         "name": "Units", "format": NUM0},
        {"id": "fs-cells", "formula": "[Units] * [Fleet Baseline/Cell Kwh Per Unit]",
         "name": "Row Cell Kwh", "hidden": True},
    ],
    "style": card(),
    "tableComponents": {"summaryBar": "hidden"},
})

MP = "Monthly Pulse"
RP = "Regional Pulse"


def cur(col: str) -> str:
    return f'SumIf([{MP}/{col}], [{MP}/Period Name] = "Current")'


def pri(col: str) -> str:
    return f'SumIf([{MP}/{col}], [{MP}/Period Name] = "Prior")'


def cur_max(col: str) -> str:
    return f'MaxIf([{MP}/{col}], [{MP}/Period Name] = "Current")'


def pri_max(col: str) -> str:
    return f'MaxIf([{MP}/{col}], [{MP}/Period Name] = "Prior")'


def kpi_card(key: str, label: str, current: str, prior: str, fmt: dict,
             icon_url: str, spark_col: str) -> None:
    add({"id": f"c-{key}", "kind": "container", "spacing": "small", "style": card()})
    img(f"ico-{key}", icon_url)
    add({
        "id": f"kc-{key}", "kind": "kpi-chart",
        "source": {"elementId": "tbl-month", "kind": "table"},
        "columns": [
            {"id": f"vc-{key}", "formula": current, "name": label, "format": fmt},
            {"id": f"vk-{key}", "formula": prior, "name": "Prior month", "format": fmt},
        ],
        "value": {"columnId": f"vc-{key}", "color": TEXT, "fontSize": 28},
        "comparisonColumn": {"columnId": f"vk-{key}"},
        "comparison": {"display": "delta", "colorGood": GREEN, "colorBad": RED, "fontSize": 12},
        "name": {"text": label, "color": MUTED, "fontSize": 11},
        "layout": {"anchor": "start"},
        "style": {"padding": "none", "backgroundColor": CARD},
    })
    add({
        "id": f"sp-{key}", "kind": "line-chart",
        "source": {"elementId": "tbl-month", "kind": "table"},
        "columns": [
            {"id": f"spx-{key}", "formula": f"[{MP}/Month]", "name": "Month"},
            {"id": f"spy-{key}", "formula": f"Sum([{MP}/{spark_col}])", "name": "Trend"},
            {"id": f"spc-{key}", "formula": '"Trend"', "name": "Series"},
        ],
        "xAxis": {"columnId": f"spx-{key}",
                  "format": {"labels": "hidden", "marks": "none"}},
        "yAxis": {"columnIds": [f"spy-{key}"],
                  "format": {"labels": "hidden", "marks": "none",
                             "scale": {"type": "linear", "zero": False, "hideZeroLine": True}}},
        "color": {"by": "category", "column": f"spc-{key}", "scheme": [BLUE]},
        "name": {"visibility": "hidden"},
        "legend": {"visibility": "hidden"},
        "style": {"padding": "none", "backgroundColor": CARD},
        "lineAreaStyle": {"interpolation": "monotone"},
    })


def model_kpi(key: str, label: str, formula: str, fmt: dict, icon_url: str, *,
              baseline: str | None = None, good: str = GREEN, bad: str = RED,
              value_color: str = TEXT, spark_y: str | None = None,
              spark_color: str = BLUE) -> None:
    add({"id": f"c-{key}", "kind": "container", "spacing": "small", "style": card()})
    img(f"ico-{key}", icon_url)
    cols = [{"id": f"k-{key}-v", "formula": formula, "name": label, "format": fmt}]
    kpi: dict = {
        "id": f"k-{key}", "kind": "kpi-chart",
        "source": {"elementId": "tbl-fleet-scenario", "kind": "table"},
        "columns": cols,
        "value": {"columnId": f"k-{key}-v", "color": value_color, "fontSize": 28},
        "name": {"text": label, "color": MUTED, "fontSize": 11},
        "layout": {"anchor": "start"},
        "style": {"padding": "none", "backgroundColor": CARD},
    }
    if baseline is not None:
        cols.append({"id": f"k-{key}-c", "formula": baseline, "name": "Baseline", "format": fmt})
        kpi["comparisonColumn"] = {"columnId": f"k-{key}-c"}
        kpi["comparison"] = {"display": "delta", "colorGood": good, "colorBad": bad, "fontSize": 12}
    add(kpi)
    if spark_y:
        add({
            "id": f"sp-{key}", "kind": "line-chart",
            "source": {"elementId": "sql-ramp", "kind": "table"},
            "columns": [
                {"id": f"spx-{key}", "formula": f"[{RM}/Month]", "name": "Month"},
                {"id": f"spy-{key}", "formula": spark_y, "name": "Trend"},
                {"id": f"spc-{key}", "formula": '"Trend"', "name": "Series"},
            ],
            "xAxis": {"columnId": f"spx-{key}",
                      "format": {"labels": "hidden", "marks": "none"}},
            "yAxis": {"columnIds": [f"spy-{key}"],
                      "format": {"labels": "hidden", "marks": "none",
                                 "scale": {"type": "linear", "zero": False, "hideZeroLine": True}}},
            "color": {"by": "category", "column": f"spc-{key}", "scheme": [spark_color]},
            "name": {"visibility": "hidden"},
            "legend": {"visibility": "hidden"},
            "style": {"padding": "none", "backgroundColor": CARD},
            "lineAreaStyle": {"interpolation": "monotone"},
        })
    else:
        add({"id": f"sp-{key}", "kind": "text", "body": " ",
             "style": {"backgroundColor": CARD, "padding": "none"},
             "verticalAlign": "middle"})


def status_kpi(key: str, label: str, formula: str, fmt: dict, icon_url: str, *,
               value_color: str = TEXT) -> None:
    add({"id": f"c-{key}", "kind": "container", "spacing": "small", "style": card()})
    img(f"ico-{key}", icon_url)
    add({
        "id": f"k-{key}", "kind": "kpi-chart",
        "source": {"elementId": "it-registry", "kind": "table"},
        "columns": [{"id": f"k-{key}-v", "formula": formula, "name": label, "format": fmt}],
        "value": {"columnId": f"k-{key}-v", "color": value_color, "fontSize": 28},
        "name": {"text": label, "color": MUTED, "fontSize": 11},
        "layout": {"anchor": "start"},
        "style": {"padding": "none", "backgroundColor": CARD},
    })


# ---- page chrome
for i in (1, 2, 3):
    add({"id": f"c-hdr{i}", "kind": "container", "spacing": "small",
         "style": {"backgroundColor": NAVY, "borderRadius": "round", "padding": "none"},
         "backgroundImage": {"source": {"kind": "url", "url": header_bg()},
                             "style": {"fit": "cover"}}})
    img(f"logo{i}", wordmark())
    add(nav(i))

add({
    "id": "ctrl-date", "kind": "control", "controlId": "AsOfDate", "name": "As of",
    "controlType": "date-range", "mode": "between",
    "includeNulls": "when-no-value-is-selected",
    "filters": [{"source": {"kind": "table", "elementId": "tbl-month"}, "columnId": "m0"}],
})
add({
    "id": "ctrl-region", "kind": "control", "controlId": "RegionFilter", "name": "Region",
    "controlType": "list", "mode": "include", "selectionMode": "multiple", "values": [],
    "filters": [
        {"source": {"kind": "table", "elementId": "tbl-region"}, "columnId": "r0"},
        {"source": {"kind": "table", "elementId": "tbl-realloc"}, "columnId": "x0"},
    ],
    "source": {"kind": "source",
               "source": {"kind": "table", "elementId": "tbl-region"},
               "columnId": "r0"},
})

# ---- title
add({"id": "c-title", "kind": "container", "spacing": "small"})
md("txt-eyebrow1", eyebrow("MARKET INTELLIGENCE"))
md("txt-title",
   f'# **<span style="color: {TEXT}">Regional EV &amp; Hybrid Market Intelligence</span>**')
md("txt-sub",
   f'<span style="color: {MUTED}">Waitlist, backlog weeks, and margin at risk across five U.S. regions. '
   f'Updated Jun 27, 2025 · Last 6 months.</span>')

# ---- KPI row
kpi_card("ev", "EV WAITLIST", cur("EV Waitlist"), pri("EV Waitlist"), NUM0,
         icon_badge(ICO_ZAP, "#E8F1FF", BLUE), "EV Waitlist")
kpi_card("hy", "HYBRID WAITLIST", cur("Hybrid Waitlist"), pri("Hybrid Waitlist"), NUM0,
         icon_badge(ICO_LEAF, "#E8F8F0", GREEN), "Hybrid Waitlist")
kpi_card("bk", "LONGEST BACKLOG (WKS)", cur_max("Longest Backlog Wks"),
         pri_max("Longest Backlog Wks"), NUM1,
         icon_badge(ICO_CLOCK, "#EEF0FF", "#4F46E5"), "Longest Backlog Wks")
kpi_card("mg", "MARGIN AT RISK", cur("Margin at Risk"), pri("Margin at Risk"), MONEY_M,
         icon_badge(ICO_DOLLAR, "#FFF6E0", GOLD), "Margin at Risk")
kpi_card("rk", "REGIONS AT RISK", cur_max("Regions at Risk"),
         pri_max("Regions at Risk"), NUM0,
         icon_badge(ICO_PIN, "#E8F1FF", NAVY), "Regions at Risk")

# ---- AI insight
add({"id": "c-ai", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": BLUE_SOFT, "borderRadius": "round",
               "borderColor": "#C9DBFF", "borderWidth": 1}})
img("ico-ai", icon_badge(ICO_SPARK, "#FFFFFF", BLUE, 40))
md("txt-ai",
   f'<span style="color: {BLUE}; font-size: 11px">**AI INSIGHT**</span>\n\n'
   f'<span style="color: {TEXT}">EV demand is surging — the waitlist is **4,120** (+400 vs May), '
   f'with Southwest and West absorbing most of the backlog. Battery-cell supply is the binding '
   f'constraint: two regions now sit above the 5-week risk threshold, putting **$1.80M** of '
   f'margin in play. Increase EV allocation to SW &amp; West and lock cell supply before Q3.</span>')
add({"id": "btn-scen", "kind": "button", "text": "Explore Scenarios →",
     "appearance": "filled", "fillColor": NAVY, "fontColor": "#FFFFFF",
     "actions": [{"id": "a-scen", "trigger": "on-click",
                  "effects": [{"effect": "navigate",
                               "target": {"type": "page", "page": "pg2"}}]}]})

# ---- quick questions + copilot
add({"id": "c-qq", "kind": "container", "spacing": "small", "style": card()})
img("ico-qq1", icon_badge(ICO_SPARK, BLUE_SOFT, BLUE, 40))
md("txt-qq-h", f'<span style="color: {TEXT}">**Quick Questions**</span>')
md("txt-qq-list",
   f'<span style="color: {MUTED}">'
   f'Which regions have the highest EV or hybrid backlogs?  \n'
   f'Where is margin most at risk right now?  \n'
   f'How has the EV waitlist changed over the last 6 months?  \n'
   f'What should we reallocate away from the South?</span>')
add({"id": "chat1", "kind": "chat", "agentId": "ag-signal"})

# ---- regional pulse — five native donuts (plugin is optional; this org
# cannot register plugins). Same composition as the mockup row.
add({"id": "c-pulse", "kind": "container", "spacing": "small", "style": card()})
md("txt-pulse",
   f'<span style="color: {TEXT}">**Regional Demand Pulse**</span> · '
   f'<span style="color: {MUTED}">EV share of regional backlog · weeks of wait</span>')
for key, region, ev, hy, pct, wks in SHARES:
    add({"id": f"c-dn-{key}", "kind": "container", "spacing": "small",
         "style": {"backgroundColor": CARD, "padding": "none"}})
    add({
        "id": f"dn-{key}", "kind": "donut-chart",
        "source": {"elementId": f"tbl-{key}", "kind": "table"},
        "columns": [
            {"id": f"dnc-{key}", "formula": f"[Share {region}/Category]", "name": "Category"},
            {"id": f"dnv-{key}", "formula": f"Sum([Share {region}/Units])", "name": "Units",
             "format": NUM0},
        ],
        "value": {"id": f"dnv-{key}"},
        "color": {"id": f"dnc-{key}", "scheme": [EV_COLOR, HY_COLOR]},
        "name": {"visibility": "hidden"},
        "legend": {"visibility": "hidden"},
        "style": {"backgroundColor": CARD, "padding": "none"},
    })
    md(f"cap-{key}",
       f'<span style="color: {TEXT}">**{region}**</span> · '
       f'<span style="color: {EV_COLOR}">{pct} EV</span> · '
       f'<span style="color: {MUTED}">{wks}</span>')

# ---- ranked bar + trend
add({"id": "c-bar", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "bar-ev", "kind": "bar-chart",
    "source": {"elementId": "tbl-region", "kind": "table"},
    "columns": [
        {"id": "bx", "formula": f"[{RP}/Region]", "name": "Region"},
        {"id": "by", "formula": f"Sum([{RP}/EV Backlog])", "name": "EV Backlog", "format": NUM0},
        {"id": "bo", "formula": f"Min([{RP}/Region Order])", "name": "Order"},
        {"id": "bser", "formula": '"EV Backlog"', "name": "Series"},
    ],
    "xAxis": {"columnId": "bx", "sort": {"by": "by", "direction": "descending"}},
    "yAxis": {"columnIds": ["by"]},
    "color": {"by": "category", "column": "bser", "scheme": [EV_COLOR]},
    "dataLabel": {"labels": "shown", "anchor": "end", "fontSize": 11},
    "name": title("EV Backlog by Region, Ranked"),
    "legend": {"visibility": "hidden"},
    "style": {"backgroundColor": CARD, "padding": "none"},
})
add({"id": "c-trend", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "line-trend", "kind": "line-chart",
    "source": {"elementId": "tbl-month", "kind": "table"},
    "columns": [
        {"id": "tx", "formula": f"[{MP}/Month]", "name": "Month"},
        {"id": "ty1", "formula": f"Sum([{MP}/EV Waitlist])", "name": "EV", "format": NUM0},
        {"id": "ty2", "formula": f"Sum([{MP}/Hybrid Waitlist])", "name": "Hybrid", "format": NUM0},
    ],
    "xAxis": {"columnId": "tx"},
    "yAxis": {"columnIds": ["ty1", "ty2"]},
    "name": title("Backlog Trend"),
    "legend": {"visibility": "shown"},
    "style": {"backgroundColor": CARD, "padding": "none"},
    "lineAreaStyle": {"interpolation": "monotone"},
})
md("txt-foot",
   f'<span style="color: {MUTED}">Sigma Motors · Sustainable Mobility · Smarter Supply · Stronger Margins'
   f'&nbsp;&nbsp;·&nbsp;&nbsp;Data · Insight · Action</span>')

# ---- page 2 — interactive reallocation model
add({"id": "c-title2", "kind": "container", "spacing": "small"})
md("txt-eyebrow2", eyebrow("PRODUCTION PLANNING"))
md("txt-title2",
   f'# **<span style="color: {TEXT}">EV &amp; Hybrid Reallocation</span>**')
md("txt-sub2",
   f'<span style="color: {MUTED}">Model production mix shifts against plant capacity and battery-cell '
   f'supply. Adjust the EV-share lever to see margin, rollout, and feasibility update live.</span>')

SPARK_EV = "5600 + 56 * [c_ev_shift] * [Rollout Months/Ramp Fraction]"
SPARK_HY = "7300 - 56 * [c_ev_shift] * [Rollout Months/Ramp Fraction]"
model_kpi("rev", "EV UNITS",
          f'SumIf([{FS}/Units], [{FS}/Powertrain] = "EV")', NUM0,
          icon_badge(ICO_ZAP, BLUE_SOFT, EV_COLOR), baseline="5600",
          good=GREEN, bad=RED, spark_y=SPARK_EV, spark_color=EV_COLOR)
model_kpi("rhy", "HYBRID UNITS",
          f'SumIf([{FS}/Units], [{FS}/Powertrain] = "Hybrid")', NUM0,
          icon_badge(ICO_LEAF, "#EEF2F6", HY_COLOR), baseline="7300",
          good=RED, bad=GREEN, spark_y=SPARK_HY, spark_color=HY_COLOR)
model_kpi("rmg", "MARGIN IMPACT", "42000 * [c_ev_shift]",
          {"kind": "number", "formatString": "$,.3s", "currencySymbol": "$"},
          icon_badge(ICO_DOLLAR, "#E8F8F0", GREEN), value_color=GREEN)
model_kpi("rtot", "TOTAL CAPACITY", f"Sum([{FS}/Units])", NUM0,
          icon_badge(ICO_PIN, BLUE_SOFT, NAVY))
model_kpi("rcap", "CAPACITY USED", f"Sum([{FS}/Units]) / 12900", PCT0,
          icon_badge(ICO_CLOCK, "#EEF0FF", "#4F46E5"))
model_kpi("rcel", "CELL USED", f"Sum([{FS}/Row Cell Kwh]) / 581628", PCT0,
          icon_badge(ICO_BATTERY, "#FFF6E0", GOLD), value_color=GOLD)

add({"id": "c-qq2", "kind": "container", "spacing": "small", "style": card()})
img("ico-qq2", icon_badge(ICO_SPARK, BLUE_SOFT, BLUE, 40))
md("txt-qq2-h", f'<span style="color: {TEXT}">**Reallocation Assistant**</span>')
md("txt-qq2-sub", f'<span style="color: {MUTED}">Ask about mix, margin, or cell supply</span>')
md("txt-qq2-list",
   f'<span style="color: {MUTED}">'
   f'What happens if we shift 10 points toward EV?  \n'
   f'Are we near the battery-cell supply limit?  \n'
   f'How does margin change per point of EV share?</span>')
add({"id": "chat2", "kind": "chat", "agentId": "ag-r2"})

add({"id": "c-ai2", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": BLUE_SOFT, "borderRadius": "round",
               "borderColor": "#C9DBFF", "borderWidth": 1}})
img("ico-ai2", icon_badge(ICO_SPARK, "#FFFFFF", BLUE, 40))
md("txt-ai2-label", f'<span style="color: {BLUE}; font-size: 11px">**AI INSIGHT**</span>')
add({"id": "txt-ai2", "kind": "text", "body": AI_PG2_BODY,
     "style": {"backgroundColor": "transparent", "padding": "none", "color": TEXT},
     "verticalAlign": "middle"})

add({"id": "c-workspace", "kind": "container", "spacing": "small", "style": card()})
md("txt-workspace-h", section_title("Scenario workspace"))
md("txt-workspace-sub", section_subtitle("Adjust the lever and compare rollout paths"))
add({"id": "c-slider", "kind": "container", "spacing": "small", "style": panel()})
md("txt-slider-label", f'<span style="color: {TEXT}">**Reallocate production mix**</span>')
md("txt-slider-hint", f'<span style="color: {MUTED}">EV-share shift (−20 to +20)</span>')
add({
    "id": "ctrl-ev-shift", "kind": "control", "controlId": "c_ev_shift",
    "name": "EV-share shift", "controlType": "number", "mode": "=",
    "value": 0, "includeNulls": "when-no-value-is-selected",
})
add({
    "id": "btn-reset", "kind": "button", "text": "Reset",
    "appearance": "outline", "fillColor": CARD, "fontColor": TEXT, "fontWeight": "bold",
    "actions": [{"id": "a-reset", "trigger": "on-click", "effects": [{
        "effect": "set-control-value", "control": "c_ev_shift",
        "value": {"type": "constant", "value": {"type": "number", "value": 0}},
    }]}],
})
add({
    "id": "btn-scenario", "kind": "button", "text": "+ New scenario",
    "appearance": "outline", "fillColor": CARD, "fontColor": BLUE, "fontWeight": "bold",
    "actions": [{"id": "a-scenario", "trigger": "on-click", "effects": [{
        "effect": "open-overlay", "overlayId": "m-scenarios",
    }]}],
})
add({
    "id": "btn-submit", "kind": "button", "text": "Save & submit for approval",
    "appearance": "filled", "fillColor": NAVY, "fontColor": "#FFFFFF", "fontWeight": "bold",
    "actions": [{"id": "a-submit", "trigger": "on-click", "effects": [
        {"effect": "insert-rows", "table": "it-registry", "values": {
            "reg-id": {"type": "formula",
                       "formula": '"SCN-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
            "reg-name": {"type": "formula",
                         "formula": '"Reallocation scenario – " & DateFormat(Now(), "%b %d, %H:%M")'},
            "reg-type": {"type": "formula",
                         "formula": ('"EV-Share Shift " & If([c_ev_shift] >= 0, "+" & Text([c_ev_shift]), '
                                     'Text([c_ev_shift]))')},
            "reg-shift": {"type": "control", "control": "c_ev_shift"},
            "reg-owner": {"type": "constant", "value": {"type": "text", "value": "C. Miller"}},
            "reg-status": {"type": "constant", "value": {"type": "text", "value": "Pending"}},
        }},
        {"effect": "navigate", "target": {"type": "page", "page": "pg3"}},
    ]}],
})
add({"id": "c-chart-rollout", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": CARD, "padding": "none"}})
add({
    "id": "ch-trend", "kind": "line-chart",
    "source": {"elementId": "sql-ramp", "kind": "table"},
    "columns": [
        {"id": "rt-label", "formula": f"[{RM}/Month]", "name": "Month"},
        {"id": "rt-ev", "formula": SPARK_EV, "name": "EV units", "format": NUM0},
        {"id": "rt-hy", "formula": SPARK_HY, "name": "Hybrid units", "format": NUM0},
    ],
    "xAxis": {"columnId": "rt-label"},
    "yAxis": {"columnIds": ["rt-ev", "rt-hy"]},
    "name": title("Production rollout"),
    "description": {"text": "EV vs Hybrid units, ramping to the modeled shift over 6 months"},
    "legend": {"visibility": "shown"},
    "style": {"backgroundColor": CARD, "padding": "none"},
    "lineAreaStyle": {"interpolation": "monotone"},
})

# ---- page 3 — approvals with write-back registry
add({"id": "c-title3", "kind": "container", "spacing": "small"})
md("txt-eyebrow3", eyebrow("GOVERNANCE"))
md("txt-title3", f'# **<span style="color: {TEXT}">Approvals</span>**')
md("txt-sub3",
   f'<span style="color: {MUTED}">Review submitted reallocation scenarios. Select a row to approve '
   f'or reject with comments.</span>')

status_kpi("pend", "PENDING",
           f'CountIf([{SR}/Status] = "Pending")', NUM0,
           icon_badge(ICO_CLOCK, "#FFF6E0", GOLD), value_color=GOLD)
status_kpi("appr", "APPROVED",
           f'CountIf([{SR}/Status] = "Approved")', NUM0,
           icon_badge(ICO_CHECK, "#E8F8F0", GREEN), value_color=GREEN)
status_kpi("rej", "REJECTED",
           f'CountIf([{SR}/Status] = "Rejected")', NUM0,
           icon_badge(ICO_X, "#FEE2E2", RED), value_color=RED)
status_kpi("rate", "APPROVAL RATE",
           ('If(CountIf([Scenario Registry/Status] = "Approved") + '
            'CountIf([Scenario Registry/Status] = "Rejected") = 0, 0, '
            'CountIf([Scenario Registry/Status] = "Approved") / '
            '(CountIf([Scenario Registry/Status] = "Approved") + '
            'CountIf([Scenario Registry/Status] = "Rejected")))'),
           PCT0, icon_badge(ICO_PERCENT, BLUE_SOFT, BLUE))

add({"id": "c-qq3", "kind": "container", "spacing": "small", "style": card()})
img("ico-qq3", icon_badge(ICO_SPARK, BLUE_SOFT, BLUE, 40))
md("txt-qq3-h", f'<span style="color: {TEXT}">**Approvals Assistant**</span>')
md("txt-qq3-sub", f'<span style="color: {MUTED}">Status, history, and open requests</span>')
md("txt-qq3-list",
   f'<span style="color: {MUTED}">'
   f'How many scenarios are pending review?  \n'
   f'What was the last approved shift?  \n'
   f'Summarize open requests for finance.</span>')
add({"id": "chat3", "kind": "chat", "agentId": "ag-r3"})

add({"id": "c-registry", "kind": "container", "spacing": "small", "style": card()})
md("txt-registry-h", section_title("Submission queue"))
md("txt-registry-sub", section_subtitle("Select a row to review and decide"))
add({
    "id": "it-registry", "kind": "input-table", "name": SR,
    "source": {"kind": "empty", "connectionId": CONN},
    "inputMode": "view", "style": card(),
    "tableComponents": {"summaryBar": "hidden"},
    "sort": [{"columnId": "CREATED_AT", "direction": "descending", "nulls": "last"}],
    "columns": [
        {"id": "reg-id", "type": "text", "name": "Scenario ID"},
        {"id": "reg-name", "type": "text", "name": "Scenario"},
        {"id": "reg-type", "type": "text", "name": "Type"},
        {"id": "reg-shift", "type": "number", "name": "Reg Shift"},
        {"id": "reg-owner", "type": "text", "name": "Submitted by"},
        {"id": "reg-status", "type": "text", "name": "Status",
         "values": ["Pending", "Approved", "Rejected"]},
        {"id": "reg-comments", "type": "text", "name": "Reviewer comments"},
        {"id": "ID", "name": "Row ID", "hidden": True},
        {"id": "CREATED_AT", "name": "Created At"},
        {"id": "UPDATED_AT", "name": "Updated At", "hidden": True},
        {"id": "CREATED_BY", "name": "Created By", "hidden": True},
    ],
    "conditionalFormats": [
        {"type": "single", "columnIds": ["reg-status"], "condition": "=",
         "value": "Approved", "style": {"backgroundColor": "#E3F5EC", "color": GREEN, "bold": True}},
        {"type": "single", "columnIds": ["reg-status"], "condition": "=",
         "value": "Rejected", "style": {"backgroundColor": "#FCE8E6", "color": RED, "bold": True}},
        {"type": "single", "columnIds": ["reg-status"], "condition": "=",
         "value": "Pending", "style": {"backgroundColor": "#FDF3DA", "color": GOLD, "bold": True}},
    ],
    "actions": [{
        "id": "act-select-reg", "trigger": "on-select", "effects": [
            {"effect": "set-control-value", "control": "c_selected_scenario",
             "value": {"type": "column", "column": "reg-id"}},
            {"effect": "open-overlay", "overlayId": "m-review"},
        ],
    }],
})

# ---- hidden controls + scenario overlay elements
add({
    "id": "ctrl-selected-scenario", "kind": "control", "controlId": "c_selected_scenario",
    "name": "Selected scenario", "controlType": "text", "mode": "equals",
    "case": "insensitive", "includeNulls": "when-no-value-is-selected",
    "showOperators": False,
})
img("ms-icon", icon_badge(ICO_SPARK, BLUE_SOFT, BLUE, 40))
md("ms-title", f'<span style="color: {TEXT}">**New scenario**</span>')
md("ms-sub",
   f'<span style="color: {MUTED}">Snapshot the current lever value and save it for comparison '
   f'before submitting.</span>')
add({"id": "c-ms-form", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "ctrl-scenario-name", "kind": "control", "controlId": "c_scenario_name",
    "name": "Scenario name", "controlType": "text", "mode": "contains",
    "case": "insensitive", "includeNulls": "when-no-value-is-selected",
    "showOperators": False,
})
add({
    "id": "btn-create-scenario", "kind": "button", "text": "Save scenario",
    "appearance": "filled", "fillColor": NAVY, "fontColor": "#FFFFFF",
    "actions": [{"id": "a-create-scenario", "trigger": "on-click", "effects": [
        {"effect": "insert-rows", "table": "it-scenarios", "values": {
            "sc-id": {"type": "formula", "formula": '"SC-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
            "sc-name": {"type": "formula",
                        "formula": ('Coalesce(NullIf([c_scenario_name], ""), "Scenario") & '
                                    '" (" & Text([c_ev_shift]) & ")"')},
            "sc-shift": {"type": "control", "control": "c_ev_shift"},
        }},
        {"effect": "clear-control",
         "scope": {"type": "control", "control": "c_scenario_name"}},
    ]}],
})
add({"id": "c-ms-table", "kind": "container", "spacing": "small", "style": card()})
md("ms-table-title", f'<span style="color: {TEXT}">**Saved scenarios**</span>')
add({
    "id": "it-scenarios", "kind": "input-table", "name": " ",
    "source": {"kind": "empty", "connectionId": CONN},
    "inputMode": "view", "style": {"padding": "none", "backgroundColor": CARD},
    "tableComponents": {"summaryBar": "hidden"},
    "sort": [{"columnId": "CREATED_AT", "direction": "ascending", "nulls": "last"}],
    "columns": [
        {"id": "sc-id", "type": "text", "name": "Scenario ID"},
        {"id": "sc-name", "type": "text", "name": "Scenario"},
        {"id": "sc-shift", "type": "number", "name": "EV shift"},
        {"id": "ID", "name": "Row ID", "hidden": True},
        {"id": "CREATED_AT", "name": "Created At", "hidden": True},
        {"id": "UPDATED_AT", "name": "Updated At", "hidden": True},
        {"id": "CREATED_BY", "name": "Created By", "hidden": True},
        {"id": "sc-margin", "formula": "42000 * [EV shift]", "name": "Margin impact",
         "format": {"kind": "number", "formatString": "$,.3s", "currencySymbol": "$"}},
        {"id": "sc-cellused", "formula": "(522200 + 3416 * [EV shift]) / 581628",
         "name": "Cell used", "format": PCT0},
    ],
    "conditionalFormats": [
        {"type": "dataBars", "columnIds": ["sc-margin"],
         "scheme": [BLUE_SOFT, GREEN]},
        {"type": "single", "columnIds": ["sc-cellused"], "condition": ">",
         "value": 1, "style": {"backgroundColor": "#FCE8E6", "color": RED, "bold": True}},
    ],
})
add({
    "id": "btn-close-compare", "kind": "button", "text": "Cancel",
    "appearance": "outline", "fillColor": CARD, "fontColor": MUTED,
    "actions": [{"id": "a-close-compare", "trigger": "on-click",
                 "effects": [{"effect": "close-overlay"}]}],
})

# ---- review overlay elements
add({
    "id": "review-selected", "kind": "kpi-chart",
    "source": {"elementId": "it-registry", "kind": "table"},
    "columns": [{
        "id": "rs-v",
        "formula": f'MaxIf([{SR}/Scenario], [{SR}/Scenario ID] = [c_selected_scenario])',
        "name": "Reviewing",
    }],
    "value": {"columnId": "rs-v", "color": TEXT, "fontSize": 16},
    "name": {"text": "REVIEWING", "color": MUTED, "fontSize": 11},
    "style": {"padding": "none", "backgroundColor": CARD},
})
add({"id": "c-kpi-review", "kind": "container", "spacing": "small", "style": card()})
for rid, rlabel, rform in [
    ("review-ev", "EV UNITS",
     f'5600 + 56 * MaxIf([{SR}/Reg Shift], [{SR}/Scenario ID] = [c_selected_scenario])'),
    ("review-hy", "HYBRID UNITS",
     f'7300 - 56 * MaxIf([{SR}/Reg Shift], [{SR}/Scenario ID] = [c_selected_scenario])'),
    ("review-margin", "MARGIN IMPACT",
     f'42000 * MaxIf([{SR}/Reg Shift], [{SR}/Scenario ID] = [c_selected_scenario])'),
    ("review-cell", "CELL USED",
     f'(522200 + 3416 * MaxIf([{SR}/Reg Shift], [{SR}/Scenario ID] = [c_selected_scenario])) / 581628'),
]:
    fmt = NUM0 if "UNITS" in rlabel else (
        {"kind": "number", "formatString": "$,.3s", "currencySymbol": "$"}
        if "MARGIN" in rlabel else PCT0)
    vcol = GREEN if "MARGIN" in rlabel else (GOLD if "CELL" in rlabel else TEXT)
    add({
        "id": rid, "kind": "kpi-chart",
        "source": {"elementId": "it-registry", "kind": "table"},
        "columns": [{"id": f"{rid}-v", "formula": rform, "name": rlabel, "format": fmt}],
        "value": {"columnId": f"{rid}-v", "color": vcol, "fontSize": 15},
        "name": {"text": rlabel, "color": MUTED, "fontSize": 10},
        "style": {"padding": "none", "backgroundColor": CARD},
    })
add({
    "id": "ctrl-review-decision", "kind": "control", "controlId": "c_review_decision",
    "name": "Decision", "controlType": "segmented", "value": "Approved",
    "source": {"kind": "manual", "valueType": "text", "values": ["Approved", "Rejected"]},
})
add({
    "id": "ctrl-review-comments", "kind": "control", "controlId": "c_review_comments",
    "name": "Reviewer comments", "controlType": "text", "mode": "contains",
    "case": "insensitive", "includeNulls": "when-no-value-is-selected",
    "showOperators": False,
})
add({
    "id": "btn-save-decision", "kind": "button", "text": "Save",
    "appearance": "filled", "fillColor": NAVY, "fontColor": "#FFFFFF",
    "actions": [{"id": "a-save-decision", "trigger": "on-click", "effects": [
        {"effect": "update-rows", "table": "it-registry",
         "whichRows": {"type": "formula", "formula": "[Scenario ID] = [c_selected_scenario]"},
         "values": {
             "reg-status": {"type": "control", "control": "c_review_decision"},
             "reg-comments": {"type": "control", "control": "c_review_comments"},
         }},
        {"effect": "clear-control",
         "scope": {"type": "control", "control": "c_review_comments"}},
        {"effect": "close-overlay"},
    ]}],
})
add({
    "id": "btn-cancel-review", "kind": "button", "text": "Cancel",
    "appearance": "outline", "fillColor": CARD, "fontColor": MUTED,
    "actions": [{"id": "a-cancel-review", "trigger": "on-click",
                 "effects": [{"effect": "close-overlay"}]}],
})

agents.append({
    "id": "ag-signal",
    "name": "Market Signal Copilot",
    "description": "Answers questions about Sigma Motors EV and hybrid backlog.",
    "instructions": (
        "You are the Market Signal copilot for Sigma Motors. Use only the workbook data. "
        "EV waitlist is 4,120 (June), hybrid 610. Longest backlog is 6.2 weeks in the West. "
        "Margin at risk is $1.80M. Southwest (95% EV, 5.1 weeks) and West (91% EV, 6.2 weeks) "
        "are the two regions at risk. Recommend shifting ~508 EV units into SW and West from "
        "Northeast, South, and a small Midwest trim. Be concise and quantitative. "
        "Cite region names and units."
    ),
    "greeting": {
        "mode": "static",
        "message": (
            "Ask about regional backlog, waitlist trend, or where to reallocate. "
            "Try: Which regions have the highest EV backlogs? "
            "Where is margin most at risk? "
            "How has the EV waitlist changed over the last 6 months?"
        ),
    },
    "dataSources": [
        {"kind": "table", "elementId": "tbl-month"},
        {"kind": "table", "elementId": "tbl-region"},
        {"kind": "table", "elementId": "tbl-realloc"},
    ],
    "tools": [],
})
agents.append({
    "id": "ag-r2",
    "name": "Reallocation Assistant",
    "description": "Models EV/Hybrid production mix shifts and battery-cell usage.",
    "instructions": (
        "Answer questions about the EV/Hybrid production mix, margin impact, and battery-cell "
        "supply usage using the Fleet Scenario and Rollout Months data sources. Be concise — 2-3 "
        "sentences. Whenever the user mentions a specific shift amount, in either direction — "
        "'shift 15 points toward EV', 'move 10 points toward Hybrid', 'try a 5-point shift' — "
        "ALWAYS call the Set EV-share shift tool immediately with that value (negative for a "
        "Hybrid-direction shift) before replying. Apply it, then summarize EV units, Hybrid units, "
        "margin impact, and battery-cell usage."
    ),
    "dataSources": [
        {"kind": "table", "elementId": "tbl-fleet-scenario"},
        {"kind": "table", "elementId": "sql-ramp"},
    ],
    "tools": [{
        "toolId": "t-set-shift", "kind": "action", "name": "Set EV-share shift",
        "description": (
            "Move the EV-share shift lever to a specific point value (-20 to +20)."
        ),
        "steps": [{
            "kind": "effect", "effect": "set-control-value", "control": "c_ev_shift",
            "value": {"type": "agent-input",
                      "inputName": "The EV-share shift point value, as a number from -20 to 20"},
        }],
    }],
})
agents.append({
    "id": "ag-r3",
    "name": "Approvals Assistant",
    "description": "Answers questions about submitted reallocation scenarios.",
    "instructions": (
        "Answer questions about scenario submissions, their status (Pending/Approved/Rejected), "
        "and reviewer comments using the Scenario Registry data source. Be concise — 2-3 sentences."
    ),
    "dataSources": [{"kind": "table", "elementId": "it-registry"}],
    "tools": [],
})

LAYOUT = '''<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 5"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo1" gridColumn="1 / 8" gridRow="1 / 5"/>
    <Element elementId="nav1" gridColumn="8 / 20" gridRow="2 / 5"/>
    <Element elementId="ctrl-date" gridColumn="20 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-title" type="grid" gridColumn="1 / 25" gridRow="5 / 10"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-eyebrow1" gridColumn="1 / 18" gridRow="1 / 2"/>
    <Element elementId="txt-title" gridColumn="1 / 18" gridRow="2 / 4"/>
    <Element elementId="txt-sub" gridColumn="1 / 18" gridRow="4 / 6"/>
    <Element elementId="ctrl-region" gridColumn="18 / 25" gridRow="2 / 6"/>
  </Container>
  <Container elementId="c-ev" type="grid" gridColumn="1 / 6" gridRow="10 / 21"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-ev" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-ev" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-ev" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-hy" type="grid" gridColumn="6 / 11" gridRow="10 / 21"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-hy" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-hy" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-hy" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-bk" type="grid" gridColumn="11 / 16" gridRow="10 / 21"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-bk" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-bk" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-bk" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-mg" type="grid" gridColumn="16 / 21" gridRow="10 / 21"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-mg" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-mg" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-mg" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-rk" type="grid" gridColumn="21 / 25" gridRow="10 / 21"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rk" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-rk" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-rk" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="21 / 27"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-ai" gridColumn="1 / 3" gridRow="2 / 5"/>
    <Element elementId="txt-ai" gridColumn="3 / 20" gridRow="1 / 6"/>
    <Element elementId="btn-scen" gridColumn="20 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-qq" type="grid" gridColumn="1 / 8" gridRow="27 / 53"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-qq1" gridColumn="1 / 3" gridRow="1 / 3"/>
    <Element elementId="txt-qq-h" gridColumn="3 / 13" gridRow="1 / 3"/>
    <Element elementId="txt-qq-list" gridColumn="1 / 13" gridRow="3 / 10"/>
    <Element elementId="chat1" gridColumn="1 / 13" gridRow="10 / 24"/>
  </Container>
  <Container elementId="c-pulse" type="grid" gridColumn="8 / 25" gridRow="27 / 41"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-pulse" gridColumn="1 / 25" gridRow="1 / 3"/>
    <Container elementId="c-dn-sw" type="grid" gridColumn="1 / 6" gridRow="3 / 16"
               gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
      <Element elementId="dn-sw" gridColumn="1 / 13" gridRow="1 / 9"/>
      <Element elementId="cap-sw" gridColumn="1 / 13" gridRow="9 / 13"/>
    </Container>
    <Container elementId="c-dn-we" type="grid" gridColumn="6 / 11" gridRow="3 / 16"
               gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
      <Element elementId="dn-we" gridColumn="1 / 13" gridRow="1 / 9"/>
      <Element elementId="cap-we" gridColumn="1 / 13" gridRow="9 / 13"/>
    </Container>
    <Container elementId="c-dn-mw" type="grid" gridColumn="11 / 16" gridRow="3 / 16"
               gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
      <Element elementId="dn-mw" gridColumn="1 / 13" gridRow="1 / 9"/>
      <Element elementId="cap-mw" gridColumn="1 / 13" gridRow="9 / 13"/>
    </Container>
    <Container elementId="c-dn-ne" type="grid" gridColumn="16 / 21" gridRow="3 / 16"
               gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
      <Element elementId="dn-ne" gridColumn="1 / 13" gridRow="1 / 9"/>
      <Element elementId="cap-ne" gridColumn="1 / 13" gridRow="9 / 13"/>
    </Container>
    <Container elementId="c-dn-so" type="grid" gridColumn="21 / 25" gridRow="3 / 16"
               gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
      <Element elementId="dn-so" gridColumn="1 / 13" gridRow="1 / 9"/>
      <Element elementId="cap-so" gridColumn="1 / 13" gridRow="9 / 13"/>
    </Container>
  </Container>
  <Container elementId="c-bar" type="grid" gridColumn="8 / 17" gridRow="41 / 53"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="bar-ev" gridColumn="1 / 13" gridRow="1 / 12"/>
  </Container>
  <Container elementId="c-trend" type="grid" gridColumn="17 / 25" gridRow="41 / 53"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="line-trend" gridColumn="1 / 13" gridRow="1 / 12"/>
  </Container>
  <Element elementId="txt-foot" gridColumn="1 / 25" gridRow="53 / 55"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg2">
  <Container elementId="c-hdr2" type="grid" gridColumn="1 / 25" gridRow="1 / 5"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo2" gridColumn="1 / 8" gridRow="1 / 5"/>
    <Element elementId="nav2" gridColumn="8 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-title2" type="grid" gridColumn="1 / 25" gridRow="5 / 10"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-eyebrow2" gridColumn="1 / 25" gridRow="1 / 2"/>
    <Element elementId="txt-title2" gridColumn="1 / 25" gridRow="2 / 4"/>
    <Element elementId="txt-sub2" gridColumn="1 / 25" gridRow="4 / 6"/>
  </Container>
  <Container elementId="c-rev" type="grid" gridColumn="1 / 5" gridRow="10 / 22"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rev" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-rev" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-rev" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-rhy" type="grid" gridColumn="5 / 9" gridRow="10 / 22"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rhy" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-rhy" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-rhy" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-rmg" type="grid" gridColumn="9 / 13" gridRow="10 / 22"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rmg" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-rmg" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-rmg" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-rtot" type="grid" gridColumn="13 / 17" gridRow="10 / 22"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rtot" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-rtot" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-rtot" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-rcap" type="grid" gridColumn="17 / 21" gridRow="10 / 22"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rcap" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-rcap" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-rcap" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-rcel" type="grid" gridColumn="21 / 25" gridRow="10 / 22"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rcel" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-rcel" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-rcel" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-qq2" type="grid" gridColumn="1 / 8" gridRow="22 / 48"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-qq2" gridColumn="1 / 3" gridRow="1 / 3"/>
    <Element elementId="txt-qq2-h" gridColumn="3 / 13" gridRow="1 / 3"/>
    <Element elementId="txt-qq2-sub" gridColumn="1 / 13" gridRow="3 / 4"/>
    <Element elementId="txt-qq2-list" gridColumn="1 / 13" gridRow="4 / 10"/>
    <Element elementId="chat2" gridColumn="1 / 13" gridRow="10 / 26"/>
  </Container>
  <Container elementId="c-ai2" type="grid" gridColumn="8 / 25" gridRow="22 / 30"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-ai2" gridColumn="1 / 3" gridRow="1 / 4"/>
    <Element elementId="txt-ai2-label" gridColumn="3 / 25" gridRow="1 / 2"/>
    <Element elementId="txt-ai2" gridColumn="3 / 25" gridRow="2 / 7"/>
  </Container>
  <Container elementId="c-workspace" type="grid" gridColumn="8 / 25" gridRow="30 / 48"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-workspace-h" gridColumn="1 / 25" gridRow="1 / 2"/>
    <Element elementId="txt-workspace-sub" gridColumn="1 / 25" gridRow="2 / 3"/>
    <Container elementId="c-slider" type="grid" gridColumn="1 / 8" gridRow="3 / 16"
               gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
      <Element elementId="txt-slider-label" gridColumn="1 / 13" gridRow="1 / 2"/>
      <Element elementId="txt-slider-hint" gridColumn="1 / 13" gridRow="2 / 3"/>
      <Element elementId="ctrl-ev-shift" gridColumn="1 / 13" gridRow="3 / 5"/>
      <Element elementId="btn-reset" gridColumn="1 / 13" gridRow="5 / 7"/>
      <Element elementId="btn-scenario" gridColumn="1 / 13" gridRow="7 / 9"/>
      <Element elementId="btn-submit" gridColumn="1 / 13" gridRow="9 / 11"/>
    </Container>
    <Container elementId="c-chart-rollout" type="grid" gridColumn="9 / 25" gridRow="3 / 16"
               gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
      <Element elementId="ch-trend" gridColumn="1 / 13" gridRow="1 / 13"/>
    </Container>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg3">
  <Container elementId="c-hdr3" type="grid" gridColumn="1 / 25" gridRow="1 / 5"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo3" gridColumn="1 / 8" gridRow="1 / 5"/>
    <Element elementId="nav3" gridColumn="8 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-title3" type="grid" gridColumn="1 / 25" gridRow="5 / 10"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-eyebrow3" gridColumn="1 / 25" gridRow="1 / 2"/>
    <Element elementId="txt-title3" gridColumn="1 / 25" gridRow="2 / 4"/>
    <Element elementId="txt-sub3" gridColumn="1 / 25" gridRow="4 / 6"/>
  </Container>
  <Container elementId="c-pend" type="grid" gridColumn="1 / 7" gridRow="10 / 19"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-pend" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-pend" gridColumn="1 / 13" gridRow="3 / 9"/>
  </Container>
  <Container elementId="c-appr" type="grid" gridColumn="7 / 13" gridRow="10 / 19"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-appr" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-appr" gridColumn="1 / 13" gridRow="3 / 9"/>
  </Container>
  <Container elementId="c-rej" type="grid" gridColumn="13 / 19" gridRow="10 / 19"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rej" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-rej" gridColumn="1 / 13" gridRow="3 / 9"/>
  </Container>
  <Container elementId="c-rate" type="grid" gridColumn="19 / 25" gridRow="10 / 19"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rate" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="k-rate" gridColumn="1 / 13" gridRow="3 / 9"/>
  </Container>
  <Container elementId="c-qq3" type="grid" gridColumn="1 / 8" gridRow="19 / 44"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-qq3" gridColumn="1 / 3" gridRow="1 / 3"/>
    <Element elementId="txt-qq3-h" gridColumn="3 / 13" gridRow="1 / 3"/>
    <Element elementId="txt-qq3-sub" gridColumn="1 / 13" gridRow="3 / 4"/>
    <Element elementId="txt-qq3-list" gridColumn="1 / 13" gridRow="4 / 10"/>
    <Element elementId="chat3" gridColumn="1 / 13" gridRow="10 / 26"/>
  </Container>
  <Container elementId="c-registry" type="grid" gridColumn="8 / 25" gridRow="19 / 44"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-registry-h" gridColumn="1 / 13" gridRow="1 / 2"/>
    <Element elementId="txt-registry-sub" gridColumn="1 / 13" gridRow="2 / 3"/>
    <Element elementId="it-registry" gridColumn="1 / 13" gridRow="3 / 22"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pgData">
  <Element elementId="tbl-month" gridColumn="1 / 13" gridRow="1 / 10"/>
  <Element elementId="tbl-region" gridColumn="13 / 25" gridRow="1 / 10"/>
  <Element elementId="tbl-realloc" gridColumn="1 / 13" gridRow="10 / 18"/>
  <Element elementId="sql-fleet" gridColumn="13 / 25" gridRow="10 / 18"/>
  <Element elementId="tbl-fleet-scenario" gridColumn="1 / 13" gridRow="18 / 26"/>
  <Element elementId="sql-ramp" gridColumn="13 / 25" gridRow="18 / 26"/>
  <Element elementId="ctrl-selected-scenario" gridColumn="1 / 7" gridRow="26 / 28"/>
  <Element elementId="tbl-sw" gridColumn="7 / 12" gridRow="26 / 32"/>
  <Element elementId="tbl-we" gridColumn="12 / 17" gridRow="26 / 32"/>
  <Element elementId="tbl-mw" gridColumn="17 / 22" gridRow="26 / 32"/>
  <Element elementId="tbl-ne" gridColumn="1 / 6" gridRow="32 / 38"/>
  <Element elementId="tbl-so" gridColumn="6 / 11" gridRow="32 / 38"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto" id="m-scenarios">
  <Element elementId="ms-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
  <Element elementId="ms-title" gridColumn="2 / 13" gridRow="1 / 2"/>
  <Element elementId="ms-sub" gridColumn="1 / 13" gridRow="2 / 3"/>
  <Container elementId="c-ms-form" type="grid" gridColumn="1 / 13" gridRow="4 / 7"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-scenario-name" gridColumn="1 / 8" gridRow="1 / 3"/>
    <Element elementId="btn-create-scenario" gridColumn="8 / 13" gridRow="1 / 3"/>
  </Container>
  <Container elementId="c-ms-table" type="grid" gridColumn="1 / 13" gridRow="8 / 19"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ms-table-title" gridColumn="1 / 13" gridRow="1 / 2"/>
    <Element elementId="it-scenarios" gridColumn="1 / 13" gridRow="2 / 11"/>
  </Container>
  <Element elementId="btn-close-compare" gridColumn="1 / 13" gridRow="20 / 22"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto" id="m-review">
  <Element elementId="review-selected" gridColumn="1 / 13" gridRow="1 / 3"/>
  <Container elementId="c-kpi-review" type="grid" gridColumn="1 / 13" gridRow="3 / 6"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="review-ev" gridColumn="1 / 4" gridRow="1 / 4"/>
    <Element elementId="review-hy" gridColumn="4 / 7" gridRow="1 / 4"/>
    <Element elementId="review-margin" gridColumn="7 / 10" gridRow="1 / 4"/>
    <Element elementId="review-cell" gridColumn="10 / 13" gridRow="1 / 4"/>
  </Container>
  <Element elementId="ctrl-review-decision" gridColumn="1 / 13" gridRow="6 / 8"/>
  <Element elementId="ctrl-review-comments" gridColumn="1 / 13" gridRow="8 / 10"/>
  <Element elementId="btn-save-decision" gridColumn="1 / 7" gridRow="10 / 12"/>
  <Element elementId="btn-cancel-review" gridColumn="7 / 13" gridRow="10 / 12"/>
</Page>
'''

SETTINGS = {"theme": {"overrides": {
    "colors": {"text": TEXT, "highlight": BLUE, "success": GREEN,
               "warning": GOLD, "danger": RED, "darkMode": "hidden"},
    "colorOverrides": {"backgroundCanvas": CANVAS, "canvasBackground": CANVAS},
    "categoricalScheme": [EV_COLOR, HY_COLOR, NAVY, BLUE_MID, GREEN, GOLD, "#7C9CFF", "#0A4E8B"],
    "backgroundColor": CANVAS,
    "elementBackgroundColor": CARD,
    "borderColor": BORDER,
    "borderRadius": "round",
    "pageWidth": "full",
    "space": {"unit": "medium", "showElementPadding": "shown"},
    "fonts": {"dataFont": "Inter", "textFont": "Inter"},
}}}

DOCUMENT = {
    "schemaVersion": 1,
    "kind": "workbook",
    "elements": elements,
    "pages": [
        {"id": "pg1", "name": "Market Signal", "backgroundColor": CANVAS},
        {"id": "pg2", "name": "EV & Hybrid Reallocation", "backgroundColor": CANVAS},
        {"id": "pg3", "name": "Approvals", "backgroundColor": CANVAS},
        {"id": "pgData", "name": "Data", "visibility": "hidden"},
    ],
    "overlays": [
        {
            "id": "m-scenarios", "type": "modal", "name": "Scenario studio",
            "modal": {
                "width": "large",
                "header": {"title": " ", "showCloseIcon": "shown"},
                "footer": {"primaryCta": {"visible": "hidden"},
                           "secondaryCta": {"visible": "hidden"}},
            },
        },
        {
            "id": "m-review", "type": "modal", "name": "Review scenario",
            "modal": {
                "width": "small",
                "header": {"title": " ", "showCloseIcon": "shown"},
                "footer": {"primaryCta": {"visible": "hidden"},
                           "secondaryCta": {"visible": "hidden"}},
            },
        },
    ],
    "agents": agents,
    "settings": SETTINGS,
    "layout": LAYOUT,
}

SPEC = {
    "name": "Sigma Motors — Market Signal",
    "folderId": FOLDER,
    "document": DOCUMENT,
}


def _placed_ids(layout: str) -> set[str]:
    import re
    return set(re.findall(r'elementId="([^"]+)"', layout))


def _lint() -> None:
    placed = _placed_ids(LAYOUT)
    ids = [e["id"] for e in elements]
    missing = [i for i in ids if i not in placed]
    extra = sorted(placed - set(ids))
    dupes = [i for i in ids if ids.count(i) > 1]
    if missing or extra or dupes:
        raise SystemExit(
            f"layout lint failed\n  missing={missing}\n  extra={extra}\n  dupes={sorted(set(dupes))}"
        )


def _write_iteration(tag: str, payload: dict) -> None:
    out = HERE / "iterations"
    out.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M")
    (out / f"{ts}-{tag}.json").write_text(json.dumps(payload, indent=2))


def main() -> None:
    _lint()
    action = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if action == "verify":
        try:
            call("POST", "/v2/workbooks/spec/verify", SPEC)
            print(f"verify passed — {len(elements)} elements, {len(agents)} agents")
        except RuntimeError as exc:
            print("verify failed:\n" + str(exc)[:4000])
            raise SystemExit(1)
    elif action == "create":
        r = call("POST", "/v2/workbooks/spec", SPEC)
        wid = r["workbookId"]
        print("created", wid)
        (HERE / "workbook_id.txt").write_text(wid)
        meta = call("GET", f"/v2/workbooks/{wid}")
        url = meta.get("url") or r.get("url")
        print("url", url)
        (HERE / "workbook_url.txt").write_text(url or "")
        spec = call("GET", f"/v2/workbooks/{wid}/spec")
        (HERE / "spec.json").write_text(json.dumps(spec, indent=2))
        _write_iteration("created", spec)
    elif action == "update":
        wid = sys.argv[2]
        call("PUT", f"/v2/workbooks/{wid}/spec", SPEC)
        print("updated", wid)
        spec = call("GET", f"/v2/workbooks/{wid}/spec")
        (HERE / "spec.json").write_text(json.dumps(spec, indent=2))
        _write_iteration("updated", spec)
    else:
        raise SystemExit("usage: build.py verify|create|update <id>")


if __name__ == "__main__":
    main()
