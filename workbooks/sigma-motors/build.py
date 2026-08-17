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
CONN = os.environ.get("SIGMA_CONNECTION_ID", "e0a14c77-3b70-453b-b8a3-00dd6974aebc")
TOKEN_CACHE = pathlib.Path("/tmp/.sigma_token")
HERE = pathlib.Path(__file__).resolve().parent

NAVY = "#0B1B3A"
NAVY_DEEP = "#071226"
BLUE = "#1B4FD6"
BLUE_SOFT = "#E8F1FF"
BLUE_MID = "#4C7DFF"
CANVAS = "#F3F5F8"
CARD = "#FFFFFF"
BORDER = "#E2E6EE"
TEXT = "#0B1B3A"
MUTED = "#5B6B7F"
GREEN = "#0F9F6E"
RED = "#E11D48"
GOLD = "#C9971A"
HYBRID = "#94A3B8"

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

APPROVAL_SQL = """
SELECT 'REQ-1841' AS "Request", 'Southwest' AS "Region", 268 AS "Units",
       'Pending' AS "Status", 'A. Chen' AS "Owner", DATE '2025-06-24' AS "Submitted"
UNION ALL SELECT 'REQ-1837', 'West', 240, 'Pending', 'J. Patel', DATE '2025-06-23'
UNION ALL SELECT 'REQ-1822', 'Northeast', -38, 'Approved', 'M. Ortiz', DATE '2025-06-18'
UNION ALL SELECT 'REQ-1811', 'South', -30, 'Approved', 'M. Ortiz', DATE '2025-06-16'
UNION ALL SELECT 'REQ-1794', 'Midwest', -20, 'Rejected', 'S. Kim', DATE '2025-06-12'
"""


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
            "borderColor": BORDER, "borderWidth": 1, "padding": "medium"}


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
sql_table("tbl-approvals", "Approval Queue", APPROVAL_SQL,
          ["Request", "Region", "Units", "Status", "Owner", "Submitted"], "q")

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
        {"source": {"kind": "table", "elementId": "tbl-approvals"}, "columnId": "q1"},
    ],
    "source": {"kind": "source",
               "source": {"kind": "table", "elementId": "tbl-region"},
               "columnId": "r0"},
})

# ---- title
add({"id": "c-title", "kind": "container", "spacing": "small"})
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
               "borderColor": "#C9DBFF", "borderWidth": 1, "padding": "medium"}})
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
md("txt-qq-h", f'<span style="color: {TEXT}">**Quick Questions**</span>')
md("txt-qq-list",
   f'<span style="color: {MUTED}">'
   f'Which regions have the highest EV or hybrid backlogs?  \n'
   f'Where is margin most at risk right now?  \n'
   f'How has the EV waitlist changed over the last 6 months?  \n'
   f'What should we reallocate away from the South?</span>')
add({"id": "chat1", "kind": "chat", "agentId": "ag-signal"})

# ---- regional pulse (bespoke split-ring plugin — matches the mockup donuts)
add({"id": "c-pulse", "kind": "container", "spacing": "small", "style": card()})
md("txt-pulse",
   f'<span style="color: {TEXT}">**Regional Demand Pulse**</span>  \n'
   f'<span style="color: {MUTED}">EV share of regional backlog · weeks of wait</span>')
PLUGIN_ID = os.environ.get("SIGMA_PLUGIN_ID")  # filled at create if unset
add({
    "id": "plg-pulse", "kind": "plugin",
    "pluginId": PLUGIN_ID or "00000000-0000-0000-0000-000000000000",
    "displayName": "Regional Demand Pulse",
    "config": {
        "source": {"kind": "element", "elementId": "tbl-region"},
        "region": "r0",
        "ev_backlog": "r2",
        "hybrid_backlog": "r3",
        "growth_pct": "r8",
        "backlog_weeks": "r5",
    },
    "style": {"backgroundColor": CARD},
})

# ---- ranked bar + trend
add({"id": "c-bar", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "bar-ev", "kind": "bar-chart",
    "source": {"elementId": "tbl-region", "kind": "table"},
    "columns": [
        {"id": "bx", "formula": f"[{RP}/Region]", "name": "Region"},
        {"id": "by", "formula": f"Sum([{RP}/EV Backlog])", "name": "EV Backlog", "format": NUM0},
        {"id": "bo", "formula": f"Min([{RP}/Region Order])", "name": "Order"},
    ],
    "xAxis": {"columnId": "bx"},
    "yAxis": {"columnIds": ["by"]},
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

# ---- page 2 reallocation
add({"id": "c-title2", "kind": "container", "spacing": "small"})
md("txt-title2",
   f'# **<span style="color: {TEXT}">EV &amp; Hybrid Reallocation</span>**')
md("txt-sub2",
   f'<span style="color: {MUTED}">Shift units toward the two regions above the 5-week threshold. '
   f'Net move: +508 units into Southwest and West.</span>')
add({"id": "c-plan", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "tbl-plan-view", "kind": "table", "name": "Recommended shifts",
    "source": {"elementId": "tbl-realloc", "kind": "table"},
    "columns": [
        {"id": "pv0", "formula": "[Reallocation Plan/Region]", "name": "Region"},
        {"id": "pv1", "formula": "[Reallocation Plan/Current EV]", "name": "Current EV", "format": NUM0},
        {"id": "pv2", "formula": "[Reallocation Plan/Recommended EV]", "name": "Recommended EV", "format": NUM0},
        {"id": "pv3", "formula": "[Reallocation Plan/Units to Shift]", "name": "Units to Shift", "format": NUM0},
        {"id": "pv4", "formula": "[Reallocation Plan/Rationale]", "name": "Rationale"},
    ],
})
add({"id": "c-shift", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "bar-shift", "kind": "bar-chart",
    "source": {"elementId": "tbl-realloc", "kind": "table"},
    "columns": [
        {"id": "sx", "formula": "[Reallocation Plan/Region]", "name": "Region"},
        {"id": "sy1", "formula": "Sum([Reallocation Plan/Current EV])", "name": "Current", "format": NUM0},
        {"id": "sy2", "formula": "Sum([Reallocation Plan/Recommended EV])", "name": "Recommended", "format": NUM0},
    ],
    "xAxis": {"columnId": "sx"},
    "yAxis": {"columnIds": ["sy1", "sy2"]},
    "name": title("Current vs recommended EV allocation"),
    "legend": {"visibility": "shown"},
    "style": {"backgroundColor": CARD, "padding": "none"},
})

# ---- page 3 approvals
add({"id": "c-title3", "kind": "container", "spacing": "small"})
md("txt-title3", f'# **<span style="color: {TEXT}">Approvals</span>**')
md("txt-sub3",
   f'<span style="color: {MUTED}">Allocation change requests waiting on planning and finance.</span>')
add({"id": "c-pend", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "kc-pend", "kind": "kpi-chart",
    "source": {"elementId": "tbl-approvals", "kind": "table"},
    "columns": [{"id": "vc-pend",
                 "formula": 'CountIf([Approval Queue/Request], [Approval Queue/Status] = "Pending")',
                 "name": "Pending", "format": NUM0}],
    "value": {"columnId": "vc-pend", "color": TEXT, "fontSize": 28},
    "name": {"text": "PENDING REQUESTS", "color": MUTED, "fontSize": 11},
    "layout": {"anchor": "start"},
    "style": {"padding": "none", "backgroundColor": CARD},
})
add({"id": "c-units", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "kc-units", "kind": "kpi-chart",
    "source": {"elementId": "tbl-approvals", "kind": "table"},
    "columns": [{"id": "vc-units",
                 "formula": 'SumIf([Approval Queue/Units], [Approval Queue/Status] = "Pending")',
                 "name": "Units pending", "format": NUM0}],
    "value": {"columnId": "vc-units", "color": TEXT, "fontSize": 28},
    "name": {"text": "UNITS PENDING APPROVAL", "color": MUTED, "fontSize": 11},
    "layout": {"anchor": "start"},
    "style": {"padding": "none", "backgroundColor": CARD},
})
add({"id": "c-queue", "kind": "container", "spacing": "small", "style": card()})
add({
    "id": "tbl-queue-view", "kind": "table", "name": "Approval queue",
    "source": {"elementId": "tbl-approvals", "kind": "table"},
    "columns": [
        {"id": "qv0", "formula": "[Approval Queue/Request]", "name": "Request"},
        {"id": "qv1", "formula": "[Approval Queue/Region]", "name": "Region"},
        {"id": "qv2", "formula": "[Approval Queue/Units]", "name": "Units", "format": NUM0},
        {"id": "qv3", "formula": "[Approval Queue/Status]", "name": "Status"},
        {"id": "qv4", "formula": "[Approval Queue/Owner]", "name": "Owner"},
        {"id": "qv5", "formula": "[Approval Queue/Submitted]", "name": "Submitted"},
    ],
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

LAYOUT = '''<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 5"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo1" gridColumn="1 / 8" gridRow="1 / 5"/>
    <Element elementId="nav1" gridColumn="8 / 20" gridRow="2 / 5"/>
    <Element elementId="ctrl-date" gridColumn="20 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-title" type="grid" gridColumn="1 / 25" gridRow="5 / 9"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-title" gridColumn="1 / 18" gridRow="1 / 3"/>
    <Element elementId="txt-sub" gridColumn="1 / 18" gridRow="3 / 5"/>
    <Element elementId="ctrl-region" gridColumn="18 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-ev" type="grid" gridColumn="1 / 6" gridRow="9 / 20"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-ev" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-ev" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-ev" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-hy" type="grid" gridColumn="6 / 11" gridRow="9 / 20"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-hy" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-hy" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-hy" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-bk" type="grid" gridColumn="11 / 16" gridRow="9 / 20"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-bk" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-bk" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-bk" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-mg" type="grid" gridColumn="16 / 21" gridRow="9 / 20"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-mg" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-mg" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-mg" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-rk" type="grid" gridColumn="21 / 25" gridRow="9 / 20"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-rk" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="kc-rk" gridColumn="1 / 13" gridRow="3 / 8"/>
    <Element elementId="sp-rk" gridColumn="1 / 13" gridRow="8 / 12"/>
  </Container>
  <Container elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="20 / 26"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-ai" gridColumn="1 / 3" gridRow="2 / 5"/>
    <Element elementId="txt-ai" gridColumn="3 / 20" gridRow="1 / 6"/>
    <Element elementId="btn-scen" gridColumn="20 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-qq" type="grid" gridColumn="1 / 8" gridRow="26 / 52"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-qq-h" gridColumn="1 / 13" gridRow="1 / 3"/>
    <Element elementId="txt-qq-list" gridColumn="1 / 13" gridRow="3 / 10"/>
    <Element elementId="chat1" gridColumn="1 / 13" gridRow="10 / 24"/>
  </Container>
  <Container elementId="c-pulse" type="grid" gridColumn="8 / 25" gridRow="26 / 40"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-pulse" gridColumn="1 / 25" gridRow="1 / 3"/>
    <Element elementId="plg-pulse" gridColumn="1 / 25" gridRow="3 / 16"/>
  </Container>
  <Container elementId="c-bar" type="grid" gridColumn="8 / 17" gridRow="40 / 52"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="bar-ev" gridColumn="1 / 13" gridRow="1 / 12"/>
  </Container>
  <Container elementId="c-trend" type="grid" gridColumn="17 / 25" gridRow="40 / 52"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="line-trend" gridColumn="1 / 13" gridRow="1 / 12"/>
  </Container>
  <Element elementId="txt-foot" gridColumn="1 / 25" gridRow="52 / 54"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg2">
  <Container elementId="c-hdr2" type="grid" gridColumn="1 / 25" gridRow="1 / 5"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo2" gridColumn="1 / 8" gridRow="1 / 5"/>
    <Element elementId="nav2" gridColumn="8 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-title2" type="grid" gridColumn="1 / 25" gridRow="5 / 9"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-title2" gridColumn="1 / 25" gridRow="1 / 3"/>
    <Element elementId="txt-sub2" gridColumn="1 / 25" gridRow="3 / 5"/>
  </Container>
  <Container elementId="c-plan" type="grid" gridColumn="1 / 25" gridRow="9 / 22"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="tbl-plan-view" gridColumn="1 / 13" gridRow="1 / 13"/>
  </Container>
  <Container elementId="c-shift" type="grid" gridColumn="1 / 25" gridRow="22 / 40"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="bar-shift" gridColumn="1 / 13" gridRow="1 / 16"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg3">
  <Container elementId="c-hdr3" type="grid" gridColumn="1 / 25" gridRow="1 / 5"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo3" gridColumn="1 / 8" gridRow="1 / 5"/>
    <Element elementId="nav3" gridColumn="8 / 25" gridRow="2 / 5"/>
  </Container>
  <Container elementId="c-title3" type="grid" gridColumn="1 / 25" gridRow="5 / 9"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-title3" gridColumn="1 / 25" gridRow="1 / 3"/>
    <Element elementId="txt-sub3" gridColumn="1 / 25" gridRow="3 / 5"/>
  </Container>
  <Container elementId="c-pend" type="grid" gridColumn="1 / 7" gridRow="9 / 17"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-pend" gridColumn="1 / 13" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-units" type="grid" gridColumn="7 / 13" gridRow="9 / 17"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-units" gridColumn="1 / 13" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-queue" type="grid" gridColumn="1 / 25" gridRow="17 / 36"
             gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="tbl-queue-view" gridColumn="1 / 13" gridRow="1 / 16"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pgData">
  <Element elementId="tbl-month" gridColumn="1 / 13" gridRow="1 / 10"/>
  <Element elementId="tbl-region" gridColumn="13 / 25" gridRow="1 / 10"/>
  <Element elementId="tbl-realloc" gridColumn="1 / 13" gridRow="10 / 18"/>
  <Element elementId="tbl-approvals" gridColumn="13 / 25" gridRow="10 / 18"/>
</Page>
'''

SETTINGS = {"theme": {"overrides": {
    "colors": {"text": TEXT, "highlight": BLUE, "success": GREEN,
               "warning": GOLD, "danger": RED, "darkMode": "hidden"},
    "colorOverrides": {"backgroundCanvas": CANVAS, "canvasBackground": CANVAS},
    "categoricalScheme": [BLUE, HYBRID, NAVY, BLUE_MID, GREEN, GOLD, "#7C9CFF", "#0A4E8B"],
    "backgroundColor": CANVAS,
    "elementBackgroundColor": CARD,
    "borderColor": BORDER,
    "borderRadius": "round",
    "space": {"unit": "small", "showElementPadding": "shown"},
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
    "overlays": [],
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


PLUGIN_JSDELIVR = (
    "https://cdn.jsdelivr.net/gh/cmiller-coder/millersigma@"
    "{ref}/plugins/sigma-motors-demand-pulse/index.html"
)


def ensure_plugin() -> str:
    """Reuse SIGMA_PLUGIN_ID, else register the demand-pulse plugin from jsDelivr."""
    existing = os.environ.get("SIGMA_PLUGIN_ID")
    if existing:
        return existing
    listed = call("GET", "/v2/plugins") or {}
    entries = listed.get("entries") or listed.get("plugins") or []
    if isinstance(entries, list):
        for e in entries:
            if (e.get("name") or "") == "Sigma Motors Demand Pulse":
                pid = e.get("pluginId") or e.get("id")
                if pid:
                    return pid
    ref = os.environ.get("SIGMA_PLUGIN_REF", "main")
    url = PLUGIN_JSDELIVR.format(ref=ref)
    created = call("POST", "/v2/plugins", {
        "name": "Sigma Motors Demand Pulse",
        "url": url,
        "description": "Split-ring regional EV/hybrid backlog pulse for Sigma Motors.",
        "type": "element",
    })
    pid = created.get("pluginId") or created.get("id")
    print("registered plugin", pid, "from", url)
    return pid


def bind_plugin(plugin_id: str) -> None:
    for el in elements:
        if el.get("id") == "plg-pulse":
            el["pluginId"] = plugin_id


def _write_iteration(tag: str, payload: dict) -> None:
    out = HERE / "iterations"
    out.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M")
    (out / f"{ts}-{tag}.json").write_text(json.dumps(payload, indent=2))


def main() -> None:
    _lint()
    action = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if action in ("verify", "create", "update"):
        bind_plugin(ensure_plugin())
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
