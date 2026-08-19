#!/usr/bin/env python3
"""Add Assignment Pipeline Forecast scenario page to Barton POC Test workbook."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKBOOK_ID = "3b65aa5b-c908-4b8d-bcb6-f177d74bb5ef"
CONN = "f45a23e2-7b17-41d4-aa34-f2ed38483a53"
LOGO_URI = (REPO / "workbooks/barton/logo.datauri.txt").read_text().strip()

TEAL = "#00A5A2"
TEAL_DARK = "#007A78"
NAVY = "#1E3A4C"
NAVY_DEEP = "#0F2A3A"
SLATE = "#41454D"
WHITE = "#FFFFFF"
CARD = "#FFFFFF"
BORDER = "#D4E8E7"
GOOD = "#0EA5A0"
BAD = "#D64545"
CANVAS = "#EEF4F4"
TINT = "#F4FAFA"
TEXT_MUTED = "#6B7B85"
KPI_LIGHT = "#F7FAFA"

CARD_STYLE = {
    "backgroundColor": CARD,
    "borderColor": BORDER,
    "borderWidth": 1,
    "borderRadius": "round",
}
TINT_STYLE = {
    "backgroundColor": TINT,
    "borderColor": BORDER,
    "borderWidth": 1,
    "borderRadius": "round",
}

CUR = {"kind": "number", "formatString": "$.3~s", "currencySymbol": "$"}
PCT1 = {"kind": "number", "formatString": "+,.1%"}
PCT0 = {"kind": "number", "formatString": ",.1%"}
NUM = {"kind": "number", "formatString": ",.3~s"}

BASE_SQL = """
SELECT
  "Main Specialty" AS SPECIALTY,
  COUNT(DISTINCT "Assignment Number") AS BASE_BOOKINGS,
  AVG("Bill Rate") AS AVG_BILL,
  AVG("Pay Rate") AS AVG_PAY,
  AVG("Assignment LOA") AS AVG_LOA,
  SUM("Bill Rate" * "Assignment LOA" * 8) AS BASE_CONTRACT_VALUE,
  SUM("Pay Rate" * "Assignment LOA" * 8) AS BASE_COST,
  SUM("Bill Rate" * "Assignment LOA" * 8)
    - SUM("Pay Rate" * "Assignment LOA" * 8) AS BASE_MARGIN,
  SUM(CASE WHEN "Assignment Status" IN ('Pending', 'Confirmed') THEN 1 ELSE 0 END) AS PIPELINE
FROM BARTONDB.GOLD.ASSIGNMENT_POC_TEST
WHERE "prod_assignment" = 'Yes'
  AND "Assignment Status" NOT IN ('Cancelled', 'Withdrawn')
GROUP BY 1
HAVING COUNT(DISTINCT "Assignment Number") >= 200
ORDER BY BASE_CONTRACT_VALUE DESC
LIMIT 10
""".strip()

# Short names for formulas
SB = "Specialty Base"
SC = "Scenarios"
AS = "Assumptions"
BK = "Forecast Book"
SU = "Submissions"


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


def header_bg_uri() -> str:
    import base64

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
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def section_label(eid: str, text: str) -> dict:
    return {
        "id": eid,
        "kind": "text",
        "body": f"### {text}",
        "verticalAlign": "middle",
        "style": {"color": NAVY},
    }


def section_divider(eid: str) -> dict:
    return {"id": eid, "kind": "divider", "style": {"color": BORDER}}


def kpi_card(
    eid: str,
    title: str,
    val: str,
    fmt: dict,
    *,
    hero: bool = False,
    muted: bool = False,
    comp: str | None = None,
) -> dict:
    if hero:
        bg, val_color, name_color, val_size, name_size = TEAL_DARK, WHITE, "#E8F7F6", 32, 14
        style: dict = {"backgroundColor": bg}
    elif muted:
        bg, val_color, name_color, val_size, name_size = KPI_LIGHT, SLATE, TEXT_MUTED, 22, 12
        style = {**CARD_STYLE, "backgroundColor": bg}
    else:
        bg, val_color, name_color, val_size, name_size = CARD, NAVY, TEXT_MUTED, 26, 12
        style = dict(CARD_STYLE)

    cols = [{"id": f"{eid}-v", "formula": val, "name": title, "format": fmt}]
    el: dict = {
        "id": eid,
        "kind": "kpi-chart",
        "source": {"elementId": "fc-book", "kind": "table"},
        "columns": cols,
        "value": {"columnId": f"{eid}-v", "color": val_color, "fontSize": val_size},
        "name": {"text": title, "color": name_color, "fontSize": name_size},
        "layout": {"anchor": "middle"},
        "style": style,
    }
    if comp:
        cols.append({"id": f"{eid}-c", "formula": comp, "name": "Comparison", "format": fmt})
        el["comparisonColumn"] = {"columnId": f"{eid}-c"}
        el["comparison"] = {
            "display": "delta",
            "colorGood": "#C8F7F6" if hero else GOOD,
            "colorBad": "#FFD1C7" if hero else BAD,
            "fontSize": 13,
        }
    return el


def build_forecast_elements(header_bg: str) -> tuple[list[dict], dict, str, str]:
    """Return (new elements, overlay modal spec, page layout, modal layout)."""

    sbase = {
        "id": "fc-base",
        "kind": "table",
        "name": SB,
        "visibleAsSource": True,
        "source": {"connectionId": CONN, "kind": "sql", "statement": BASE_SQL},
        "columns": [
            {"id": "sb-spec", "formula": "[Custom SQL/SPECIALTY]", "name": "Specialty"},
            {"id": "sb-book", "formula": "[Custom SQL/BASE_BOOKINGS]", "name": "Base Bookings", "format": NUM},
            {"id": "sb-bill", "formula": "[Custom SQL/AVG_BILL]", "name": "Avg Bill Rate", "format": CUR},
            {"id": "sb-pay", "formula": "[Custom SQL/AVG_PAY]", "name": "Avg Pay Rate", "format": CUR},
            {"id": "sb-loa", "formula": "[Custom SQL/AVG_LOA]", "name": "Avg LOA Days", "format": NUM},
            {"id": "sb-rev", "formula": "[Custom SQL/BASE_CONTRACT_VALUE]", "name": "Base Contract Value", "format": CUR},
            {"id": "sb-cost", "formula": "[Custom SQL/BASE_COST]", "name": "Base Cost", "format": CUR},
            {"id": "sb-mar", "formula": "[Custom SQL/BASE_MARGIN]", "name": "Base Margin", "format": CUR},
            {"id": "sb-pipe", "formula": "[Custom SQL/PIPELINE]", "name": "Pipeline Count", "format": NUM},
        ],
        "order": ["sb-spec", "sb-book", "sb-bill", "sb-pay", "sb-loa", "sb-rev", "sb-cost", "sb-mar", "sb-pipe"],
    }

    scenarios = {
        "id": "fc-scenarios",
        "kind": "input-table",
        "name": SC,
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": CONN},
        "columns": [
            {"id": "sc-name", "type": "text", "name": "Scenario Name"},
            {
                "id": "sc-status",
                "type": "text",
                "name": "Status",
                "values": ["Draft", "Submitted", "Approved"],
                "pills": "color-by-option",
            },
        ],
    }

    spivot = {
        "id": "fc-pivot",
        "kind": "pivot-table",
        "name": "Scenario Pivot",
        "visibleAsSource": True,
        "source": {
            "kind": "join",
            "joins": [
                {
                    "left": {"elementId": "fc-base", "kind": "table"},
                    "right": {"elementId": "fc-scenarios", "kind": "table"},
                    "columns": [{"left": "1", "right": "1"}],
                    "joinType": "left-outer",
                }
            ],
            "primarySource": {"elementId": "fc-base", "kind": "table"},
        },
        "columns": [
            {"id": "pv-spec", "formula": f"[{SB}/Specialty]", "name": "Specialty"},
            {"id": "pv-scen", "formula": f'Coalesce([{SC}/Scenario Name], "Base Case")', "name": "Scenario"},
            {"id": "pv-book", "formula": f"Sum([{SB}/Base Bookings])", "name": "Base Bookings", "format": NUM},
            {"id": "pv-rev", "formula": f"Sum([{SB}/Base Contract Value])", "name": "Base Contract Value", "format": CUR},
            {"id": "pv-mar", "formula": f"Sum([{SB}/Base Margin])", "name": "Base Margin", "format": CUR},
            {"id": "pv-cost", "formula": f"Sum([{SB}/Base Cost])", "name": "Base Cost", "format": CUR},
            {"id": "pv-pipe", "formula": f"Sum([{SB}/Pipeline Count])", "name": "Pipeline", "format": NUM},
        ],
        "rowsBy": [{"id": "pv-spec"}],
        "values": ["pv-book", "pv-rev", "pv-mar", "pv-cost", "pv-pipe"],
    }

    bc_book = "If([Pipeline] > 500, 4, If([Pipeline] > 200, 2, 0))"

    assum = {
        "id": "fc-assum",
        "kind": "input-table",
        "name": AS,
        "inputMode": "view",
        "source": {"kind": "linked", "from": "fc-pivot"},
        "columns": [
            {"id": "ia-spec", "key": "pv-spec"},
            {"id": "ia-scen", "key": "pv-scen"},
            {"id": "ia-book", "key": "pv-book"},
            {"id": "ia-rev", "key": "pv-rev"},
            {"id": "ia-mar", "key": "pv-mar"},
            {"id": "ia-cost", "key": "pv-cost"},
            {"id": "ia-pipe", "key": "pv-pipe"},
            {"id": "ia-bc-book", "formula": bc_book, "name": "Base Case Booking Growth %", "format": PCT0},
            {"id": "ia-book-g", "type": "number", "name": "Booking Growth %"},
            {"id": "ia-bill-g", "type": "number", "name": "Bill Rate Change %"},
            {"id": "ia-pay-g", "type": "number", "name": "Pay Rate Change %"},
            {"id": "ia-cancel-g", "type": "number", "name": "Cancel Rate Change %"},
            {
                "id": "ia-eff-book",
                "formula": "Coalesce([Booking Growth %], [Base Case Booking Growth %])",
                "name": "Eff Booking Growth %",
                "format": PCT0,
            },
            {
                "id": "ia-eff-bill",
                "formula": "Coalesce([Bill Rate Change %], 0)",
                "name": "Eff Bill Rate %",
                "format": PCT0,
            },
            {
                "id": "ia-eff-pay",
                "formula": "Coalesce([Pay Rate Change %], 0)",
                "name": "Eff Pay Rate %",
                "format": PCT0,
            },
            {
                "id": "ia-eff-cancel",
                "formula": "Coalesce([Cancel Rate Change %], 0)",
                "name": "Eff Cancel Rate %",
                "format": PCT0,
            },
            {
                "id": "ia-proj-rev",
                "formula": (
                    "[Base Contract Value] * (1 + [Eff Booking Growth %] / 100) "
                    "* (1 + [Eff Bill Rate %] / 100) * (1 - [Eff Cancel Rate %] / 100)"
                ),
                "name": "Projected Contract Value",
                "format": CUR,
            },
            {
                "id": "ia-proj-cost",
                "formula": (
                    "[Base Cost] * (1 + [Eff Booking Growth %] / 100) "
                    "* (1 + [Eff Pay Rate %] / 100) * (1 - [Eff Cancel Rate %] / 100)"
                ),
                "name": "Projected Cost",
                "format": CUR,
            },
            {
                "id": "ia-proj-mar",
                "formula": "[Projected Contract Value] - [Projected Cost]",
                "name": "Projected Margin",
                "format": CUR,
            },
            {
                "id": "ia-d-rev",
                "formula": "[Projected Contract Value] - [Base Contract Value]",
                "name": "Δ Contract Value",
                "format": CUR,
            },
            {
                "id": "ia-d-mar",
                "formula": "[Projected Margin] - [Base Margin]",
                "name": "Δ Margin",
                "format": CUR,
            },
        ],
        "order": [
            "ia-scen", "ia-spec", "ia-pipe", "ia-book", "ia-rev", "ia-mar",
            "ia-bc-book", "ia-book-g", "ia-bill-g", "ia-pay-g", "ia-cancel-g",
            "ia-proj-rev", "ia-proj-mar", "ia-d-rev", "ia-d-mar",
        ],
        "name": AS,
        "style": dict(CARD_STYLE),
        "tableComponents": {"summaryBar": "hidden"},
    }

    book = {
        "id": "fc-book",
        "kind": "table",
        "name": BK,
        "visibleAsSource": True,
        "source": {"elementId": "fc-assum", "kind": "table"},
        "columns": [
            {"id": "bk-scen", "formula": f"[{AS}/Scenario]", "name": "Scenario"},
            {"id": "bk-spec", "formula": f"[{AS}/Specialty]", "name": "Specialty"},
            {"id": "bk-brev", "formula": f"[{AS}/Base Contract Value]", "name": "Base Contract Value", "format": CUR},
            {"id": "bk-bmar", "formula": f"[{AS}/Base Margin]", "name": "Base Margin", "format": CUR},
            {"id": "bk-prev", "formula": f"[{AS}/Projected Contract Value]", "name": "Projected Contract Value", "format": CUR},
            {"id": "bk-pmar", "formula": f"[{AS}/Projected Margin]", "name": "Projected Margin", "format": CUR},
            {"id": "bk-drev", "formula": f"[{AS}/Δ Contract Value]", "name": "Δ Contract Value", "format": CUR},
            {"id": "bk-dmar", "formula": f"[{AS}/Δ Margin]", "name": "Δ Margin", "format": CUR},
        ],
        "order": ["bk-scen", "bk-spec", "bk-brev", "bk-bmar", "bk-prev", "bk-pmar", "bk-drev", "bk-dmar"],
    }

    subs = {
        "id": "fc-subs",
        "kind": "input-table",
        "name": SU,
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": CONN},
        "columns": [
            {"id": "su-scen", "type": "text", "name": "Scenario"},
            {
                "id": "su-status",
                "type": "text",
                "name": "Status",
                "values": ["Submitted", "Approved"],
                "pills": "color-by-option",
            },
            {"id": "CREATED_AT", "name": "Submitted At"},
            {"id": "CREATED_BY", "name": "Submitted By"},
        ],
        "name": SU,
        "style": dict(CARD_STYLE),
        "tableComponents": {"summaryBar": "hidden"},
    }

    sel_ctrl = {
        "kind": "control",
        "controlId": "ForecastScenario",
        "id": "fc-ctrl-scen",
        "name": "Active scenario",
        "controlType": "list",
        "selectionMode": "single",
        "mode": "include",
        "value": "Base Case",
        "filters": [{"source": {"kind": "table", "elementId": "fc-book"}, "columnId": "bk-scen"}],
        "source": {
            "kind": "source",
            "source": {"kind": "table", "elementId": "fc-book"},
            "columnId": "bk-scen",
        },
    }

    name_ctrl = {
        "kind": "control",
        "controlId": "NewForecastScenario",
        "id": "fc-ctrl-name",
        "name": "Scenario name",
        "controlType": "text",
        "mode": "equals",
        "case": "insensitive",
        "includeNulls": "when-no-value-is-selected",
        "showOperators": False,
    }

    create_btn = {
        "id": "fc-btn-create",
        "kind": "button",
        "text": "Create scenario",
        "appearance": "filled",
        "actions": [{
            "id": "fc-act-open",
            "trigger": "on-click",
            "effects": [{"effect": "open-overlay", "overlayId": "fc-modal-create"}],
        }],
    }

    create_confirm = {
        "id": "fc-btn-create-ok",
        "kind": "button",
        "text": "Create",
        "appearance": "filled",
        "actions": [{
            "id": "fc-act-create",
            "trigger": "on-click",
            "effects": [
                {
                    "effect": "insert-rows",
                    "table": "fc-scenarios",
                    "values": {
                        "sc-name": {"type": "control", "control": "NewForecastScenario"},
                        "sc-status": {"type": "constant", "value": {"type": "text", "value": "Draft"}},
                    },
                },
                {"effect": "set-control-value", "control": "ForecastScenario",
                 "value": {"type": "control", "control": "NewForecastScenario"}},
                {"effect": "clear-control", "scope": {"type": "control", "control": "NewForecastScenario"}},
                {"effect": "close-overlay"},
            ],
        }],
    }

    cancel_btn = {
        "id": "fc-btn-cancel",
        "kind": "button",
        "text": "Cancel",
        "appearance": "outline",
        "actions": [{"id": "fc-act-cancel", "trigger": "on-click",
                     "effects": [{"effect": "close-overlay"}]}],
    }

    submit_btn = {
        "id": "fc-btn-submit",
        "kind": "button",
        "text": "Submit for approval",
        "appearance": "outline",
        "actions": [{
            "id": "fc-act-submit",
            "trigger": "on-click",
            "effects": [
                {
                    "effect": "insert-rows",
                    "table": "fc-subs",
                    "values": {
                        "su-scen": {"type": "control", "control": "ForecastScenario"},
                        "su-status": {"type": "constant", "value": {"type": "text", "value": "Submitted"}},
                    },
                },
                {
                    "effect": "insert-rows",
                    "table": "fc-scenarios",
                    "values": {
                        "sc-name": {"type": "control", "control": "ForecastScenario"},
                        "sc-status": {"type": "constant", "value": {"type": "text", "value": "Submitted"}},
                    },
                },
            ],
        }],
    }

    approve_btn = {
        "id": "fc-btn-approve",
        "kind": "button",
        "text": "Approve",
        "appearance": "outline",
        "actions": [{
            "id": "fc-act-approve",
            "trigger": "on-click",
            "effects": [
                {
                    "effect": "insert-rows",
                    "table": "fc-subs",
                    "values": {
                        "su-scen": {"type": "control", "control": "ForecastScenario"},
                        "su-status": {"type": "constant", "value": {"type": "text", "value": "Approved"}},
                    },
                },
                {
                    "effect": "insert-rows",
                    "table": "fc-scenarios",
                    "values": {
                        "sc-name": {"type": "control", "control": "ForecastScenario"},
                        "sc-status": {"type": "constant", "value": {"type": "text", "value": "Approved"}},
                    },
                },
            ],
        }],
    }

    scen_filter = '[Forecast Book/Scenario] = [ForecastScenario]'

    kpi_prev = kpi_card(
        "fc-kpi-prev",
        "Projected Contract Value",
        f"SumIf([{BK}/Projected Contract Value], {scen_filter})",
        CUR,
        hero=True,
        comp=f"SumIf([{BK}/Projected Contract Value], {scen_filter}) - SumIf([{BK}/Base Contract Value], {scen_filter})",
    )
    kpi_mar = kpi_card(
        "fc-kpi-mar",
        "Projected Margin",
        f"SumIf([{BK}/Projected Margin], {scen_filter})",
        CUR,
        comp=f"SumIf([{BK}/Projected Margin], {scen_filter}) - SumIf([{BK}/Base Margin], {scen_filter})",
    )
    kpi_uplift = kpi_card(
        "fc-kpi-uplift",
        "Revenue Uplift",
        f"SumIf([{BK}/Projected Contract Value], {scen_filter}) / SumIf([{BK}/Base Contract Value], {scen_filter}) - 1",
        PCT1,
    )
    kpi_base = kpi_card(
        "fc-kpi-base",
        "Baseline Contract Value",
        f"SumIf([{BK}/Base Contract Value], {scen_filter})",
        CUR,
        muted=True,
    )

    compare_chart = {
        "id": "fc-chart-compare",
        "kind": "bar-chart",
        "source": {"elementId": "fc-book", "kind": "table"},
        "columns": [
            {"id": "cc-spec", "formula": f"[{BK}/Specialty]", "name": "Specialty"},
            {"id": "cc-cat", "formula": '"Projected contract value"', "name": "Series"},
            {"id": "cc-proj", "formula": f"SumIf([{BK}/Projected Contract Value], {scen_filter})", "name": "Projected", "format": CUR},
        ],
        "xAxis": {"columnId": "cc-spec", "sort": {"by": "cc-proj", "direction": "descending"}},
        "yAxis": {"columnIds": ["cc-proj"]},
        "color": {"by": "category", "column": "cc-cat", "scheme": [TEAL]},
        "legend": {"visibility": "hidden"},
        "name": {
            "text": "Projected contract value",
            "fontWeight": "bold",
            "fontSize": 15,
            "color": SLATE,
        },
        "style": dict(CARD_STYLE),
    }

    baseline_chart = {
        "id": "fc-chart-base-bar",
        "kind": "bar-chart",
        "source": {"elementId": "fc-book", "kind": "table"},
        "columns": [
            {"id": "cb-spec", "formula": f"[{BK}/Specialty]", "name": "Specialty"},
            {"id": "cb-cat", "formula": '"Baseline contract value"', "name": "Series"},
            {"id": "cb-base", "formula": f"SumIf([{BK}/Base Contract Value], {scen_filter})", "name": "Baseline", "format": CUR},
        ],
        "xAxis": {"columnId": "cb-spec", "sort": {"by": "cb-base", "direction": "descending"}},
        "yAxis": {"columnIds": ["cb-base"]},
        "color": {"by": "category", "column": "cb-cat", "scheme": [TEXT_MUTED]},
        "legend": {"visibility": "hidden"},
        "name": {
            "text": "Baseline contract value",
            "fontWeight": "bold",
            "fontSize": 15,
            "color": SLATE,
        },
        "style": dict(CARD_STYLE),
    }

    variance_chart = {
        "id": "fc-chart-var",
        "kind": "bar-chart",
        "source": {"elementId": "fc-book", "kind": "table"},
        "columns": [
            {"id": "cv-spec", "formula": f"[{BK}/Specialty]", "name": "Specialty"},
            {"id": "cv-cat", "formula": '"Δ Contract Value"', "name": "Measure"},
            {"id": "cv-d", "formula": f"SumIf([{BK}/Δ Contract Value], {scen_filter})", "name": "Δ Contract Value", "format": CUR},
        ],
        "xAxis": {"columnId": "cv-spec", "sort": {"by": "cv-d", "direction": "descending"}},
        "yAxis": {"columnIds": ["cv-d"]},
        "color": {"by": "category", "column": "cv-cat", "scheme": [TEAL]},
        "legend": {"visibility": "hidden"},
        "name": {
            "text": "Variance vs baseline",
            "fontWeight": "bold",
            "fontSize": 15,
            "color": SLATE,
        },
        "style": dict(CARD_STYLE),
    }

    hdr = {
        "id": "fc-hdr",
        "kind": "container",
        "style": {"borderRadius": "round", "borderWidth": 0},
        "backgroundImage": {"source": {"kind": "url", "url": header_bg}, "style": {"fit": "cover"}},
    }
    logo = {
        "id": "fc-logo",
        "kind": "image",
        "source": {"kind": "url", "url": LOGO_URI},
        "style": {"fit": "contain"},
    }
    title = {
        "id": "fc-title",
        "kind": "text",
        "body": "## Assignment Pipeline Forecast",
        "verticalAlign": "middle",
        "style": {"color": WHITE},
    }
    subtitle = {
        "id": "fc-subtitle",
        "kind": "text",
        "body": "Model booking growth, rate changes & attrition by specialty — submit scenarios for leadership approval",
        "verticalAlign": "middle",
        "style": {"color": "#C8E8E7"},
    }
    toolbar = {"id": "fc-toolbar", "kind": "container", "style": dict(CARD_STYLE)}
    sec_impact = section_label("fc-sec-impact", "Impact by specialty")
    sec_drivers = section_label("fc-sec-drivers", "Scenario drivers")
    sec_approval = section_label("fc-sec-approval", "Approval workflow")
    div_kpi = section_divider("fc-div-kpi")
    div_charts = section_divider("fc-div-charts")
    div_drivers = section_divider("fc-div-drivers")
    instr_c = {"id": "fc-instr-c", "kind": "container", "style": dict(TINT_STYLE)}
    instr_hd = {
        "id": "fc-instr-hd",
        "kind": "text",
        "body": "**How to model a scenario**",
        "verticalAlign": "middle",
        "style": {"color": NAVY},
    }
    instr = {
        "id": "fc-instr",
        "kind": "text",
        "body": (
            "**1** — Select **Base Case** or **Create scenario**. "
            "**2** — Adjust **Booking Growth %**, **Bill Rate %**, **Pay Rate %**, and **Cancel Rate %** per specialty. "
            "**3** — Review KPIs and charts, then **Submit for approval** → **Approve** to lock the plan."
        ),
        "verticalAlign": "middle",
        "style": {"color": SLATE},
    }
    modal_title = {
        "id": "fc-modal-title",
        "kind": "text",
        "body": "### Name your forecast scenario\nClone the base book for all top specialties, then adjust drivers in the grid.",
        "verticalAlign": "middle",
        "style": {"color": SLATE},
    }

    elements = [
        sbase, scenarios, spivot, assum, book, subs,
        hdr, logo, title, subtitle, toolbar,
        sel_ctrl, name_ctrl, create_btn, submit_btn, approve_btn,
        kpi_prev, kpi_mar, kpi_uplift, kpi_base,
        div_kpi, sec_impact, baseline_chart, compare_chart, variance_chart,
        div_charts, sec_drivers, instr_c, instr_hd, instr,
        div_drivers, sec_approval,
        create_confirm, cancel_btn, modal_title,
    ]

    overlay = {
        "id": "fc-modal-create",
        "type": "modal",
        "name": "Create Forecast Scenario",
        "modal": {
            "width": "small",
            "header": {"title": "New forecast scenario", "showCloseIcon": "hidden"},
            "footer": {"primaryCta": {"visible": "hidden"}, "secondaryCta": {"visible": "hidden"}},
        },
    }

    modal_layout = """
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="fc-modal-create">
  <Element elementId="fc-modal-title" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="fc-ctrl-name" gridColumn="1 / 25" gridRow="3 / 5"/>
  <Element elementId="fc-btn-cancel" gridColumn="13 / 19" gridRow="5 / 7"/>
  <Element elementId="fc-btn-create-ok" gridColumn="19 / 25" gridRow="5 / 7"/>
</Page>"""

    page_layout = """
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-forecast">
  <Container elementId="fc-hdr" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="fc-logo" gridColumn="1 / 6" gridRow="1 / 5"/>
    <Element elementId="fc-title" gridColumn="6 / 18" gridRow="1 / 3"/>
    <Element elementId="fc-subtitle" gridColumn="6 / 22" gridRow="3 / 5"/>
  </Container>
  <Container elementId="fc-toolbar" type="grid" gridColumn="1 / 25" gridRow="5 / 8" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="fc-ctrl-scen" gridColumn="1 / 8" gridRow="1 / 4"/>
    <Element elementId="fc-btn-create" gridColumn="8 / 14" gridRow="1 / 4"/>
    <Element elementId="fc-btn-submit" gridColumn="14 / 19" gridRow="1 / 4"/>
    <Element elementId="fc-btn-approve" gridColumn="19 / 25" gridRow="1 / 4"/>
  </Container>
  <Element elementId="fc-kpi-prev" gridColumn="1 / 10" gridRow="8 / 15"/>
  <Element elementId="fc-kpi-mar" gridColumn="10 / 16" gridRow="8 / 15"/>
  <Element elementId="fc-kpi-uplift" gridColumn="16 / 21" gridRow="8 / 15"/>
  <Element elementId="fc-kpi-base" gridColumn="21 / 25" gridRow="8 / 15"/>
  <Element elementId="fc-div-kpi" gridColumn="1 / 25" gridRow="15 / 16"/>
  <Element elementId="fc-sec-impact" gridColumn="1 / 25" gridRow="16 / 17"/>
  <Element elementId="fc-chart-base-bar" gridColumn="1 / 13" gridRow="17 / 29"/>
  <Element elementId="fc-chart-compare" gridColumn="13 / 25" gridRow="17 / 29"/>
  <Element elementId="fc-chart-var" gridColumn="1 / 25" gridRow="29 / 41"/>
  <Element elementId="fc-div-charts" gridColumn="1 / 25" gridRow="41 / 42"/>
  <Element elementId="fc-sec-drivers" gridColumn="1 / 25" gridRow="42 / 43"/>
  <Container elementId="fc-instr-c" type="grid" gridColumn="1 / 25" gridRow="43 / 46" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="fc-instr-hd" gridColumn="1 / 25" gridRow="1 / 2"/>
    <Element elementId="fc-instr" gridColumn="1 / 25" gridRow="2 / 4"/>
  </Container>
  <Element elementId="fc-assum" gridColumn="1 / 25" gridRow="46 / 62"/>
  <Element elementId="fc-div-drivers" gridColumn="1 / 25" gridRow="62 / 63"/>
  <Element elementId="fc-sec-approval" gridColumn="1 / 25" gridRow="63 / 64"/>
  <Element elementId="fc-subs" gridColumn="1 / 25" gridRow="64 / 70"/>
  <Element elementId="fc-base" gridColumn="1 / 2" gridRow="70 / 71"/>
  <Element elementId="fc-scenarios" gridColumn="2 / 3" gridRow="70 / 71"/>
  <Element elementId="fc-pivot" gridColumn="3 / 4" gridRow="70 / 71"/>
  <Element elementId="fc-book" gridColumn="4 / 5" gridRow="70 / 71"/>
</Page>"""

    return elements, overlay, page_layout, modal_layout


def main() -> None:
    spec = api("GET", f"/v2/workbooks/{WORKBOOK_ID}/spec")
    doc = spec["document"]

    import re

    if "page-forecast" in {p["id"] for p in doc.get("pages", [])}:
        print("Forecast page exists — refreshing forecast elements")
    doc["elements"] = [e for e in doc["elements"] if not e["id"].startswith("fc-")]

    new_els, overlay, page_layout, modal_layout = build_forecast_elements(header_bg_uri())
    doc["elements"].extend(new_els)

    pages = doc.get("pages", [])
    if not any(p["id"] == "page-forecast" for p in pages):
        pages.append({"id": "page-forecast", "name": "Pipeline Forecast"})
    doc["pages"] = pages

    overlays = [o for o in doc.get("overlays", []) if o.get("id") != "fc-modal-create"]
    overlays.append(overlay)
    doc["overlays"] = overlays

    base_layout = doc.get("layout", "")
    base_layout = re.sub(
        r'<Page[^>]*id="page-forecast"[^>]*>.*?</Page>\s*',
        "",
        base_layout,
        flags=re.DOTALL,
    )
    base_layout = re.sub(
        r'<Page[^>]*id="fc-modal-create"[^>]*>.*?</Page>\s*',
        "",
        base_layout,
        flags=re.DOTALL,
    )
    doc["layout"] = base_layout.rstrip() + page_layout + modal_layout

    overrides = doc.setdefault("settings", {}).setdefault("theme", {}).setdefault("overrides", {})
    overrides.setdefault("pageWidth", "large")
    space = overrides.setdefault("space", {})
    space.setdefault("unit", "small")
    space.setdefault("showElementPadding", "shown")

    payload = {"name": spec["name"], "folderId": spec["folderId"], "document": doc}
    (REPO / "workbooks/barton/spec-forecast.json").write_text(json.dumps(payload, indent=2))
    api("PUT", f"/v2/workbooks/{WORKBOOK_ID}/spec", payload)
    print("Pipeline Forecast page added", WORKBOOK_ID)


if __name__ == "__main__":
    main()
