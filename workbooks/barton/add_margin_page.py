#!/usr/bin/env python3
"""Add Placement Margin & Bill-Rate Tracker page to Barton POC Test workbook."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from barton_formulas import DT_PERIOD, KPI_PERIOD, PERIOD, PERIOD_COMPARISON

REPO = Path(__file__).resolve().parents[2]
WORKBOOK_ID = "3b65aa5b-c908-4b8d-bcb6-f177d74bb5ef"
CONN = "f45a23e2-7b17-41d4-aa34-f2ed38483a53"
LOGO_URI = (REPO / "workbooks/barton/logo.datauri.txt").read_text().strip()
ASGN = "Assignments"
MB = "Margin Book"

TEAL = "#00A5A2"
TEAL_DARK = "#007A78"
NAVY = "#1E3A4C"
NAVY_DEEP = "#0F2A3A"
SLATE = "#41454D"
WHITE = "#FFFFFF"
BORDER = "#D4E8E7"
GOOD = "#0EA5A0"
BAD = "#D64545"
TINT = "#F4FAFA"
TEXT_MUTED = "#6B7B85"
KPI_LIGHT = "#F7FAFA"

CARD_STYLE = {
    "backgroundColor": "#FFFFFF",
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
RATE = {"kind": "number", "formatString": "$,.0f", "currencySymbol": "$"}
NUM = {"kind": "number", "formatString": ",.3~s"}

MARGIN_PCT = (
    f"[{ASGN}/Estimated Margin] / NullIf([{ASGN}/Estimated Contract Value], 0)"
)
IS_LOW = (
    f'If({MARGIN_PCT} < Number([MarginThreshold]) / 100, "Low", "OK")'
)
LOW_FLAG = f"If({MARGIN_PCT} < Number([MarginThreshold]) / 100, 1, 0)"
LOW_COUNT = f"SumIf(1, {MARGIN_PCT} < Number([MarginThreshold]) / 100)"
MB_MPCT = "Margin Pct"
SRC = "tbl-assignments"


def passthrough_cols(prefix: str) -> list[dict]:
    """Filter passthrough columns — KPIs/charts must include these when sourcing tbl-assignments."""
    fields = [
        ("assignment-number", "Assignment Number"),
        ("assignment-loa", "Assignment LOA"),
        ("listing-loa", "Listing LOA"),
        ("start-date", "Start Date"),
        ("worksite-state", "Worksite State"),
        ("main-specialty", "Main Specialty"),
        ("sub-specialty", "Sub Specialty"),
        ("bill-rate", "Bill Rate"),
        ("pay-rate", "Pay Rate"),
        ("assignment-status", "Assignment Status"),
        ("provider-type", "Provider Type"),
        ("assignment-type", "Assignment Type"),
        ("reassignment", "Reassignment"),
        ("created-date", "Assignment Created Date"),
        ("cancelled-date", "Assignment Cancelled Date"),
        ("prod-assignment", "Prod Assignment"),
        ("contract-value", "Estimated Contract Value"),
        ("cost-value", "Estimated Cost"),
        ("margin-value", "Estimated Margin"),
        ("rate-spread", "Rate Spread"),
        ("cancelled-flag", "Is Cancelled Or Withdrawn"),
        ("worksite-state-display", "Worksite State (Display)"),
    ]
    col_map = {
        "assignment-number": f"[{ASGN}/Assignment Number]",
        "assignment-loa": f"[{ASGN}/Assignment LOA]",
        "listing-loa": f"[{ASGN}/Listing LOA]",
        "start-date": f"[{ASGN}/Start Date]",
        "worksite-state": f"[{ASGN}/Worksite State]",
        "main-specialty": f"[{ASGN}/Main Specialty]",
        "sub-specialty": f"[{ASGN}/Sub Specialty]",
        "bill-rate": f"[{ASGN}/Bill Rate]",
        "pay-rate": f"[{ASGN}/Pay Rate]",
        "assignment-status": f"[{ASGN}/Assignment Status]",
        "provider-type": f"[{ASGN}/Provider Type]",
        "assignment-type": f"[{ASGN}/Assignment Type]",
        "reassignment": f"[{ASGN}/Reassignment]",
        "created-date": f"[{ASGN}/Assignment Created Date]",
        "cancelled-date": f"[{ASGN}/Assignment Cancelled Date]",
        "prod-assignment": f"[{ASGN}/Prod Assignment]",
        "contract-value": f"[{ASGN}/Estimated Contract Value]",
        "cost-value": f"[{ASGN}/Estimated Cost]",
        "margin-value": f"[{ASGN}/Estimated Margin]",
        "rate-spread": f"[{ASGN}/Rate Spread]",
        "cancelled-flag": f"[{ASGN}/Is Cancelled Or Withdrawn]",
        "worksite-state-display": f"[{ASGN}/Worksite State (Display)]",
    }
    return [
        {"id": f"{prefix}-col-{slug}", "formula": col_map[slug], "name": label}
        for slug, label in fields
    ]


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


def kpi_card(
    eid: str,
    title: str,
    val: str,
    fmt: dict,
    src: str = SRC,
    *,
    pt_prefix: str | None = None,
    hero: bool = False,
    muted: bool = False,
    period: bool = False,
    comp: str | None = None,
) -> dict:
    if hero:
        val_color, name_color, val_size, name_size = WHITE, "#E8F7F6", 32, 14
        style: dict = {"backgroundColor": TEAL_DARK}
    elif muted:
        val_color, name_color, val_size, name_size = SLATE, TEXT_MUTED, 22, 12
        style = {**CARD_STYLE, "backgroundColor": KPI_LIGHT}
    else:
        val_color, name_color, val_size, name_size = NAVY, TEXT_MUTED, 26, 12
        style = dict(CARD_STYLE)

    cols = [{"id": f"{eid}-v", "formula": val, "name": title, "format": fmt}]
    if period:
        cols.insert(
            0,
            {"id": f"{eid}-p", "formula": KPI_PERIOD, "name": "Period", "format": DT_PERIOD},
        )
    if pt_prefix:
        cols.extend(passthrough_cols(pt_prefix))
    el: dict = {
        "id": eid,
        "kind": "kpi-chart",
        "source": {"elementId": src, "kind": "table"},
        "columns": cols,
        "value": {"columnId": f"{eid}-v", "color": val_color, "fontSize": val_size},
        "name": {"text": title, "color": name_color, "fontSize": name_size},
        "layout": {"anchor": "middle"},
        "style": style,
    }
    if period:
        el["timeline"] = {"columnId": f"{eid}-p"}
        el["periodComparison"] = "month"
        el["comparison"] = dict(PERIOD_COMPARISON)
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


def build_margin_elements(header_bg: str) -> tuple[list[dict], str]:
    mg_book = {
        "id": "mg-book",
        "kind": "table",
        "name": MB,
        "visibleAsSource": True,
        "source": {"elementId": "tbl-assignments", "kind": "table"},
        "columns": [
            {"id": "mg-num", "formula": f"[{ASGN}/Assignment Number]", "name": "Assignment Number"},
            {"id": "mg-spec", "formula": f"[{ASGN}/Main Specialty]", "name": "Specialty"},
            {"id": "mg-state", "formula": f"[{ASGN}/Worksite State (Display)]", "name": "State"},
            {"id": "mg-status", "formula": f"[{ASGN}/Assignment Status]", "name": "Status"},
            {"id": "mg-bill", "formula": f"[{ASGN}/Bill Rate]", "name": "Bill Rate", "format": RATE},
            {"id": "mg-pay", "formula": f"[{ASGN}/Pay Rate]", "name": "Pay Rate", "format": RATE},
            {"id": "mg-spread", "formula": f"[{ASGN}/Rate Spread]", "name": "Rate Spread", "format": RATE},
            {"id": "mg-rev", "formula": f"[{ASGN}/Estimated Contract Value]", "name": "Contract Value", "format": CUR},
            {"id": "mg-cost", "formula": f"[{ASGN}/Estimated Cost]", "name": "Cost", "format": CUR},
            {"id": "mg-mar", "formula": f"[{ASGN}/Estimated Margin]", "name": "Margin", "format": CUR},
            {"id": "mg-mpct", "formula": MARGIN_PCT, "name": MB_MPCT, "format": PCT0},
            {"id": "mg-low", "formula": LOW_FLAG, "name": "Low Margin Flag", "format": NUM},
            {
                "id": "mg-pill",
                "formula": IS_LOW,
                "name": "Margin Status",
            },
        ],
        "order": [
            "mg-num", "mg-spec", "mg-state", "mg-status", "mg-bill", "mg-pay", "mg-spread",
            "mg-rev", "mg-cost", "mg-mar", "mg-mpct", "mg-low", "mg-pill",
        ],
    }

    mg_adj = {
        "id": "mg-adj",
        "kind": "input-table",
        "name": "Rate Adjustments",
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": CONN},
        "columns": [
            {"id": "mg-adj-num", "type": "text", "name": "Assignment Number"},
            {
                "id": "mg-adj-field",
                "type": "text",
                "name": "Field",
                "values": ["Bill Rate", "Pay Rate"],
                "pills": "color-by-option",
            },
            {"id": "mg-adj-orig", "type": "number", "name": "Original Rate"},
            {"id": "mg-adj-new", "type": "number", "name": "Adjusted Rate"},
            {"id": "mg-adj-reason", "type": "text", "name": "Reason"},
            {"id": "CREATED_AT", "name": "Logged At"},
            {"id": "CREATED_BY", "name": "Logged By"},
        ],
        "style": dict(CARD_STYLE),
        "tableComponents": {"summaryBar": "hidden"},
    }

    mg_split = {
        "id": "mg-split",
        "kind": "input-table",
        "name": "Commission Splits",
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": CONN},
        "columns": [
            {"id": "mg-sp-num", "type": "text", "name": "Assignment Number"},
            {"id": "mg-sp-recip", "type": "text", "name": "Recipient"},
            {"id": "mg-sp-pct", "type": "number", "name": "Split %"},
            {
                "id": "mg-sp-status",
                "type": "text",
                "name": "Status",
                "values": ["Draft", "Approved"],
                "pills": "color-by-option",
            },
            {"id": "CREATED_AT", "name": "Submitted At"},
            {"id": "CREATED_BY", "name": "Submitted By"},
        ],
        "style": dict(CARD_STYLE),
        "tableComponents": {"summaryBar": "hidden"},
    }

    thresh_ctrl = {
        "kind": "control",
        "controlId": "MarginThreshold",
        "id": "mg-ctrl-thresh",
        "name": "Low-margin threshold",
        "controlType": "segmented",
        "source": {
            "kind": "manual",
            "valueType": "text",
            "values": ["10", "15", "20"],
            "labels": ["10%", "15%", "20%"],
        },
        "value": "15",
    }

    low_only_ctrl = {
        "kind": "control",
        "controlId": "ShowLowMarginOnly",
        "id": "mg-ctrl-lowonly",
        "name": "Placement filter",
        "controlType": "segmented",
        "source": {
            "kind": "manual",
            "valueType": "text",
            "values": ["All", "Low margin only"],
        },
        "value": "All",
    }

    spec_ctrl = {
        "kind": "control",
        "controlId": "MarginSpecialty",
        "id": "mg-ctrl-spec",
        "name": "Specialty",
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [],
        "source": {"kind": "manual", "valueType": "text"},
        "filters": [
            {"source": {"kind": "table", "elementId": "mg-book"}, "columnId": "mg-spec"},
            {"source": {"kind": "table", "elementId": "mg-detail"}, "columnId": "mgd-spec"},
            {"source": {"kind": "table", "elementId": "mg-kpi-margin"}, "columnId": "mgkm-col-main-specialty"},
            {"source": {"kind": "table", "elementId": "mg-kpi-gross"}, "columnId": "mgkg-col-main-specialty"},
            {"source": {"kind": "table", "elementId": "mg-kpi-bill"}, "columnId": "mgkb-col-main-specialty"},
            {"source": {"kind": "table", "elementId": "mg-kpi-pay"}, "columnId": "mgkp-col-main-specialty"},
            {"source": {"kind": "table", "elementId": "mg-kpi-spread"}, "columnId": "mgks-col-main-specialty"},
            {"source": {"kind": "table", "elementId": "mg-kpi-low"}, "columnId": "mgkl-col-main-specialty"},
            {"source": {"kind": "table", "elementId": "mg-chart-trend"}, "columnId": "mct-col-main-specialty"},
            {"source": {"kind": "table", "elementId": "mg-chart-margin-spec"}, "columnId": "mc-spec"},
            {"source": {"kind": "table", "elementId": "mg-chart-bill-pay"}, "columnId": "bp-spec"},
            {"source": {"kind": "table", "elementId": "mg-chart-spread-spec"}, "columnId": "cs-spec"},
        ],
    }

    mg_detail = {
        "id": "mg-detail",
        "kind": "table",
        "source": {"elementId": "mg-book", "kind": "table"},
        "columns": [
            {"id": "mgd-num", "formula": f"[{MB}/Assignment Number]", "name": "Assignment Number"},
            {"id": "mgd-spec", "formula": f"[{MB}/Specialty]", "name": "Specialty"},
            {"id": "mgd-state", "formula": f"[{MB}/State]", "name": "State"},
            {"id": "mgd-bill", "formula": f"[{MB}/Bill Rate]", "name": "Bill Rate", "format": RATE},
            {"id": "mgd-pay", "formula": f"[{MB}/Pay Rate]", "name": "Pay Rate", "format": RATE},
            {"id": "mgd-spread", "formula": f"[{MB}/Rate Spread]", "name": "Spread", "format": RATE},
            {"id": "mgd-rev", "formula": f"[{MB}/Contract Value]", "name": "Contract Value", "format": CUR},
            {"id": "mgd-mar", "formula": f"[{MB}/Margin]", "name": "Margin", "format": CUR},
            {"id": "mgd-mpct", "formula": f"[{MB}/{MB_MPCT}]", "name": "Margin %", "format": PCT0},
            {"id": "mgd-pill", "formula": f"[{MB}/Margin Status]", "name": "Margin Status"},
            {"id": "mgd-low", "formula": f"[{MB}/Low Margin Flag]", "name": "Low Margin Flag", "format": NUM},
        ],
        "order": [
            "mgd-num", "mgd-spec", "mgd-state", "mgd-bill", "mgd-pay",
            "mgd-spread", "mgd-rev", "mgd-mar", "mgd-mpct", "mgd-pill",
        ],
        "style": dict(CARD_STYLE),
        "name": {"text": "Placement margin detail", "fontWeight": "bold", "fontSize": 15, "color": SLATE},
    }

    kpi_margin = kpi_card(
        "mg-kpi-margin",
        "Avg Placement Margin %",
        f"Avg({MARGIN_PCT})",
        PCT0,
        pt_prefix="mgkm",
        hero=True,
        period=True,
    )
    kpi_gross = kpi_card(
        "mg-kpi-gross",
        "Total Gross Margin",
        f"Sum([{ASGN}/Estimated Margin])",
        CUR,
        pt_prefix="mgkg",
        period=True,
    )
    kpi_bill = kpi_card(
        "mg-kpi-bill",
        "Avg Bill Rate",
        f"Avg([{ASGN}/Bill Rate])",
        RATE,
        pt_prefix="mgkb",
        period=True,
    )
    kpi_pay = kpi_card(
        "mg-kpi-pay",
        "Avg Pay Rate",
        f"Avg([{ASGN}/Pay Rate])",
        RATE,
        pt_prefix="mgkp",
        period=True,
    )
    kpi_spread = kpi_card(
        "mg-kpi-spread",
        "Avg Rate Spread",
        f"Avg([{ASGN}/Rate Spread])",
        RATE,
        pt_prefix="mgks",
        muted=True,
    )
    kpi_low = kpi_card(
        "mg-kpi-low",
        "Low-Margin Placements",
        LOW_COUNT,
        NUM,
        pt_prefix="mgkl",
        muted=True,
    )

    chart_margin_spec = {
        "id": "mg-chart-margin-spec",
        "kind": "bar-chart",
        "source": {"elementId": SRC, "kind": "table"},
        "columns": [
            {"id": "mc-spec", "formula": f"[{ASGN}/Main Specialty]", "name": "Specialty"},
            {"id": "mc-cat", "formula": '"Avg margin %"', "name": "Series"},
            {"id": "mc-val", "formula": f"Avg({MARGIN_PCT})", "name": "Margin %", "format": PCT0},
            *passthrough_cols("mcm"),
        ],
        "xAxis": {"columnId": "mc-spec", "sort": {"by": "mc-val", "direction": "ascending"}},
        "yAxis": {"columnIds": ["mc-val"]},
        "color": {"by": "category", "column": "mc-cat", "scheme": [TEAL_DARK]},
        "legend": {"visibility": "hidden"},
        "name": {"text": "Avg margin % by specialty", "fontWeight": "bold", "fontSize": 15, "color": SLATE},
        "style": dict(CARD_STYLE),
    }

    chart_bill_pay = {
        "id": "mg-chart-bill-pay",
        "kind": "bar-chart",
        "source": {"elementId": SRC, "kind": "table"},
        "columns": [
            {"id": "bp-spec", "formula": f"[{ASGN}/Main Specialty]", "name": "Specialty"},
            {"id": "bp-cat", "formula": '"Avg bill rate"', "name": "Series"},
            {"id": "bp-bill", "formula": f"Avg([{ASGN}/Bill Rate])", "name": "Bill Rate", "format": RATE},
            *passthrough_cols("mcb"),
        ],
        "xAxis": {"columnId": "bp-spec", "sort": {"by": "bp-bill", "direction": "descending"}},
        "yAxis": {"columnIds": ["bp-bill"]},
        "color": {"by": "category", "column": "bp-cat", "scheme": [NAVY]},
        "legend": {"visibility": "hidden"},
        "name": {"text": "Avg bill rate by specialty", "fontWeight": "bold", "fontSize": 15, "color": SLATE},
        "style": dict(CARD_STYLE),
    }

    chart_spread = {
        "id": "mg-chart-spread-spec",
        "kind": "bar-chart",
        "source": {"elementId": SRC, "kind": "table"},
        "columns": [
            {"id": "cs-spec", "formula": f"[{ASGN}/Main Specialty]", "name": "Specialty"},
            {"id": "cs-cat", "formula": '"Avg rate spread"', "name": "Series"},
            {"id": "cs-sp", "formula": f"Avg([{ASGN}/Rate Spread])", "name": "Spread", "format": RATE},
            *passthrough_cols("mcs"),
        ],
        "xAxis": {"columnId": "cs-spec", "sort": {"by": "cs-sp", "direction": "descending"}},
        "yAxis": {"columnIds": ["cs-sp"]},
        "color": {"by": "category", "column": "cs-cat", "scheme": [TEAL]},
        "legend": {"visibility": "hidden"},
        "name": {"text": "Avg bill − pay spread by specialty", "fontWeight": "bold", "fontSize": 15, "color": SLATE},
        "style": dict(CARD_STYLE),
    }

    chart_trend = {
        "id": "mg-chart-trend",
        "kind": "bar-chart",
        "source": {"elementId": SRC, "kind": "table"},
        "columns": [
            {"id": "mt-per", "formula": PERIOD, "name": "Period", "format": DT_PERIOD},
            {"id": "mt-cat", "formula": '"Gross margin"', "name": "Series"},
            {"id": "mt-mar", "formula": f"Sum([{ASGN}/Estimated Margin])", "name": "Gross Margin", "format": CUR},
            *passthrough_cols("mct"),
        ],
        "xAxis": {"columnId": "mt-per"},
        "yAxis": {"columnIds": ["mt-mar"]},
        "color": {"by": "category", "column": "mt-cat", "scheme": [TEAL_DARK]},
        "legend": {"visibility": "hidden"},
        "name": {"text": "Gross margin trend", "fontWeight": "bold", "fontSize": 15, "color": SLATE},
        "style": dict(CARD_STYLE),
    }

    hdr = {
        "id": "mg-hdr",
        "kind": "container",
        "style": {"borderRadius": "round", "borderWidth": 0},
        "backgroundImage": {"source": {"kind": "url", "url": header_bg}, "style": {"fit": "cover"}},
    }
    logo = {
        "id": "mg-logo",
        "kind": "image",
        "source": {"kind": "url", "url": LOGO_URI},
        "style": {"fit": "contain"},
    }
    title = {
        "id": "mg-title",
        "kind": "text",
        "body": "## Placement Margin & Bill-Rate Tracker",
        "verticalAlign": "middle",
        "style": {"color": WHITE},
    }
    subtitle = {
        "id": "mg-subtitle",
        "kind": "text",
        "body": "Bill vs pay spread, margin by placement, low-margin flags, and governed rate adjustments",
        "verticalAlign": "middle",
        "style": {"color": "#C8E8E7"},
    }
    toolbar = {"id": "mg-toolbar", "kind": "container", "style": dict(CARD_STYLE)}
    instr_c = {"id": "mg-instr-c", "kind": "container", "style": dict(TINT_STYLE)}
    instr = {
        "id": "mg-instr",
        "kind": "text",
        "body": (
            "**Margin %** = (Bill − Pay) × LOA × 8 ÷ Contract Value. "
            "Adjust **Low-margin threshold** to flag placements; review flagged rows on the detail tab. "
            "Log **rate corrections** and **commission splits** in the writeback tabs — audit trail included."
        ),
        "verticalAlign": "middle",
        "style": {"color": SLATE},
    }
    mg_tabs = {
        "id": "mg-tc",
        "kind": "tabbed-container",
        "tabs": [
            {"name": "Margin overview"},
            {"name": "Low-margin placements"},
            {"name": "Rate adjustments"},
            {"name": "Commission splits"},
        ],
        "tabBar": {"alignment": "start"},
    }

    elements = [
        mg_book, mg_adj, mg_split, mg_detail,
        hdr, logo, title, subtitle, toolbar, mg_tabs,
        spec_ctrl, thresh_ctrl, low_only_ctrl,
        kpi_margin, kpi_gross, kpi_bill, kpi_pay, kpi_spread, kpi_low,
        chart_margin_spec, chart_bill_pay, chart_spread, chart_trend,
        instr_c, instr,
        section_label("mg-sec-overview", "Margin overview"),
        section_label("mg-sec-detail", "Flagged placements"),
        section_label("mg-sec-adj", "Rate adjustment log"),
        section_label("mg-sec-split", "Commission splits"),
    ]

    page_layout = """
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-margin">
  <Container elementId="mg-hdr" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="mg-logo" gridColumn="1 / 6" gridRow="1 / 5"/>
    <Element elementId="mg-title" gridColumn="6 / 18" gridRow="1 / 3"/>
    <Element elementId="mg-subtitle" gridColumn="6 / 22" gridRow="3 / 5"/>
  </Container>
  <Container elementId="mg-toolbar" type="grid" gridColumn="1 / 25" gridRow="5 / 8" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="mg-ctrl-spec" gridColumn="1 / 9" gridRow="1 / 4"/>
    <Element elementId="mg-ctrl-thresh" gridColumn="9 / 16" gridRow="1 / 4"/>
    <Element elementId="mg-ctrl-lowonly" gridColumn="16 / 25" gridRow="1 / 4"/>
  </Container>
  <Element elementId="mg-kpi-margin" gridColumn="1 / 10" gridRow="8 / 15"/>
  <Element elementId="mg-kpi-gross" gridColumn="10 / 16" gridRow="8 / 15"/>
  <Element elementId="mg-kpi-bill" gridColumn="16 / 20" gridRow="8 / 15"/>
  <Element elementId="mg-kpi-pay" gridColumn="20 / 25" gridRow="8 / 15"/>
  <Element elementId="mg-kpi-spread" gridColumn="1 / 7" gridRow="15 / 20"/>
  <Element elementId="mg-kpi-low" gridColumn="7 / 13" gridRow="15 / 20"/>
  <Container elementId="mg-instr-c" type="grid" gridColumn="13 / 25" gridRow="15 / 20" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="mg-instr" gridColumn="1 / 25" gridRow="1 / 4"/>
  </Container>
  <TabbedContainer elementId="mg-tc" type="tabbed-container" gridColumn="1 / 25" gridRow="20 / 68">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="mg-sec-overview" gridColumn="1 / 25" gridRow="1 / 2"/>
      <Element elementId="mg-chart-trend" gridColumn="1 / 25" gridRow="2 / 14"/>
      <Element elementId="mg-chart-margin-spec" gridColumn="1 / 13" gridRow="14 / 26"/>
      <Element elementId="mg-chart-bill-pay" gridColumn="13 / 25" gridRow="14 / 26"/>
      <Element elementId="mg-chart-spread-spec" gridColumn="1 / 25" gridRow="26 / 38"/>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="mg-sec-detail" gridColumn="1 / 25" gridRow="1 / 2"/>
      <Element elementId="mg-detail" gridColumn="1 / 25" gridRow="2 / 30"/>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="mg-sec-adj" gridColumn="1 / 25" gridRow="1 / 2"/>
      <Element elementId="mg-adj" gridColumn="1 / 25" gridRow="2 / 28"/>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="mg-sec-split" gridColumn="1 / 25" gridRow="1 / 2"/>
      <Element elementId="mg-split" gridColumn="1 / 25" gridRow="2 / 28"/>
    </Tab>
  </TabbedContainer>
  <Element elementId="mg-book" gridColumn="1 / 2" gridRow="68 / 69"/>
</Page>"""

    return elements, page_layout


def main() -> None:
    spec = api("GET", f"/v2/workbooks/{WORKBOOK_ID}/spec")
    doc = spec["document"]

    if "page-margin" in {p["id"] for p in doc.get("pages", [])}:
        print("Margin page exists — refreshing margin elements")
    doc["elements"] = [e for e in doc["elements"] if not e["id"].startswith("mg-")]

    new_els, page_layout = build_margin_elements(header_bg_uri())
    doc["elements"].extend(new_els)

    pages = doc.get("pages", [])
    if not any(p["id"] == "page-margin" for p in pages):
        pages.append({"id": "page-margin", "name": "Margin Tracker"})
    doc["pages"] = pages

    base_layout = doc.get("layout", "")
    base_layout = re.sub(
        r'<Page[^>]*id="page-margin"[^>]*>.*?</Page>\s*',
        "",
        base_layout,
        flags=re.DOTALL,
    )
    doc["layout"] = base_layout.rstrip() + page_layout

    overrides = doc.setdefault("settings", {}).setdefault("theme", {}).setdefault("overrides", {})
    overrides.setdefault("pageWidth", "large")

    payload = {"name": spec["name"], "folderId": spec["folderId"], "document": doc}
    (REPO / "workbooks/barton/spec-margin.json").write_text(json.dumps(payload, indent=2))
    api("PUT", f"/v2/workbooks/{WORKBOOK_ID}/spec", payload)
    print("Margin Tracker page added", WORKBOOK_ID)


if __name__ == "__main__":
    main()
