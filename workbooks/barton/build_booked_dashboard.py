#!/usr/bin/env python3
"""Build the Barton 'Assignment Booked Last 5 Weeks' dashboard.

Source: BARTONDB.GOLD.ASSIGNMENT_PROD on the Snowflake POC connection.

Row scoping note: Sigma's spec API silently drops element-level `where`/`filter`
fields, so the 5-week production-assignment window is enforced by a list control
whose default value is "Last 5 Weeks". Every chart is a child of the base table,
and control filters cascade to children.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sigma_api import REPO, render_page_png

CONN = "f45a23e2-7b17-41d4-aa34-f2ed38483a53"
FOLDER = "dc487f89-30a6-48b7-8de8-e0cce0315e1b"
TABLE_PATH = ["BARTONDB", "GOLD", "ASSIGNMENT_PROD"]
WORKBOOK_NAME = "Assignment Booked Last 5 Weeks"
META_PATH = Path(__file__).resolve().parent / "booked-dashboard.json"
PAGE_ID = "page-booked"
# Relative to the current Sigma app origin. This works across host migrations
# and avoids hard-coding the vendor hostname in the spec snapshot.
REPORT_URL = "/barton/report/3Q5VvIAvLorcakIRTuFKgX"

A = "Assignments"          # base element name used in child formulas
SRC_TBL = "ASSIGNMENT_PROD"  # warehouse table name used in base-table formulas

TEAL = "#00A5A2"
TEAL_DARK = "#007A78"
TEAL_LIGHT = "#5BBFB8"
NAVY = "#1E3A4C"
NAVY_DEEP = "#0F2A3A"
SLATE = "#41454D"
BORDER = "#D4E8E7"
CANVAS = "#EEF4F4"
WHITE = "#FFFFFF"
TEXT_MUTED = "#6B7B85"
AMBER = "#E1A32D"

CATEGORICAL = [TEAL, NAVY, AMBER, TEAL_LIGHT, "#2D6B6A", "#7A8E99", "#8FD4D2", "#1A5050"]

CARD = {
    "backgroundColor": WHITE,
    "borderColor": BORDER,
    "borderWidth": 1,
    "borderRadius": "round",
}

INT = {"kind": "number", "formatString": ",.0f"}
NUM2 = {"kind": "number", "formatString": ",.2f"}
CUR = {"kind": "number", "formatString": "$,.0f"}
CUR_S = {"kind": "number", "formatString": "$.4~s"}
RATE = {"kind": "number", "formatString": "$,.2f"}
PCT = {"kind": "number", "formatString": ",.2%"}
DATE = {"kind": "datetime", "formatString": "%Y-%m-%d"}

# Worksite State holds two-letter codes. These are dropped from the map tile
# only, to keep the auto-fitted frame on the lower 48; blank covers the rows
# with no worksite captured, which otherwise render as a "1 missing" badge.
OFF_MAP_STATES = ["AK", "HI", "PR", "VI", "GU", "AS", "MP", "", None]

# Flexible window selector. The hidden scope control still does the actual row
# filtering; this visible parameter changes which rows calculate as Included.
WINDOW_LABEL = "5W"
WINDOW_OPTIONS = ["5W", "13W", "26W", "52W", "All"]
SCOPE_FORMULA = (
    'If([Prod Assignment] != "Yes", "Excluded", '
    'Switch([BookedWindow], '
    '"All", "Included", '
    '"52W", If([Weeks Back] >= 0 and [Weeks Back] <= 51, "Included", "Excluded"), '
    '"26W", If([Weeks Back] >= 0 and [Weeks Back] <= 25, "Included", "Excluded"), '
    '"13W", If([Weeks Back] >= 0 and [Weeks Back] <= 12, "Included", "Excluded"), '
    'If([Weeks Back] >= 0 and [Weeks Back] <= 4, "Included", "Excluded")))'
)


def title(text: str) -> dict:
    return {"text": text, "fontWeight": "bold", "fontSize": 14, "color": SLATE}


def base_table() -> dict:
    """Warehouse table carrying every raw + derived column the page needs."""
    raw = [
        ("an", "Assignment Number", "Assignment Number"),
        ("main-spec", "Main Specialty", "Main Specialty"),
        ("sub-spec", "Sub Specialty", "Sub Specialty"),
        # Barton's "Assignment Type" reporting label is the Reassignment field
        # (Extension / New Assignment / Reassignment), not the SF Assignment Type.
        ("asgn-type", "Reassignment", "Assignment Type"),
        ("provider-type", "SF Long Provider Type", "Provider Type"),
        ("ae", "AE", "AE"),
        ("ae-entity", "AE Company", "AE Entity"),
        ("recruiter", "Recruiter", "Recruiter"),
        ("state", "Worksite State", "Worksite State"),
        ("loa", "Assignment LOA", "Assignment LOA"),
        ("bill", "Bill Rate", "Bill Rate"),
        ("pay", "Pay Rate", "Pay Rate"),
        ("created", "Assignment Created Date", "Assignment Created Date"),
        ("prod", "prod_assignment", "Prod Assignment"),
    ]
    columns = [
        {"id": f"col-{slug}", "formula": f"[{SRC_TBL}/{src}]", "name": name}
        for slug, src, name in raw
    ]
    # ~500 rows carry a blank provider type; Barton reports those as "Other".
    for col in columns:
        if col["id"] == "col-provider-type":
            col["formula"] = (
                f'If(IsNull([{SRC_TBL}/SF Long Provider Type]) '
                f'or [{SRC_TBL}/SF Long Provider Type] = "", "Other", '
                f'[{SRC_TBL}/SF Long Provider Type])'
            )
    columns += [
        {
            "id": "col-week-ending",
            "formula": 'DateAdd("day", 5, DateTrunc("week", [Assignment Created Date]))',
            "name": "Week Ending",
            "format": DATE,
        },
        {
            # Charts key off the text label so all six weekly charts share one
            # categorical axis — a datetime axis makes line charts auto-rebucket.
            "id": "col-week-label",
            "formula": 'DateFormat(DateAdd("day", 5, DateTrunc("week", [Assignment Created Date])), "%Y-%m-%d")',
            "name": "Week Label",
        },
        {
            "id": "col-chart-period",
            "formula": (
                'Switch([BookedGrain], '
                '"Quarter", DateTrunc("quarter", [Assignment Created Date]), '
                '"Month", DateTrunc("month", [Assignment Created Date]), '
                'DateAdd("day", 5, DateTrunc("week", [Assignment Created Date])))'
            ),
            "name": "Chart Period",
            "format": DATE,
        },
        {
            "id": "col-chart-label",
            "formula": (
                'Switch([BookedGrain], '
                '"Quarter", DateFormat(DateTrunc("quarter", [Assignment Created Date]), "%Y-%m"), '
                '"Month", DateFormat(DateTrunc("month", [Assignment Created Date]), "%Y-%m"), '
                'DateFormat(DateAdd("day", 5, DateTrunc("week", [Assignment Created Date])), "%Y-%m-%d"))'
            ),
            "name": "Chart Label",
        },
        {
            "id": "col-weeks-back",
            "formula": 'DateDiff("week", DateTrunc("week", [Assignment Created Date]), DateTrunc("week", Today()))',
            "name": "Weeks Back",
            "format": INT,
        },
        {"id": "col-scope", "formula": SCOPE_FORMULA, "name": "Booking Scope"},
        {
            "id": "col-projected-billing",
            "formula": "[Bill Rate] * [Assignment LOA] * 8",
            "name": "Projected Billing",
            "format": CUR,
        },
        {
            "id": "col-gm-dollars",
            "formula": "([Bill Rate] - [Pay Rate]) * [Assignment LOA] * 8",
            "name": "GM Dollars",
            "format": CUR,
        },
        {
            "id": "col-gm-pct",
            "formula": "[GM Dollars] / NullIf([Projected Billing], 0)",
            "name": "GM Percent",
            "format": PCT,
        },
    ]
    return {
        "id": "tbl-assignments",
        "kind": "table",
        "name": A,
        "visibleAsSource": True,
        "source": {"kind": "warehouse-table", "connectionId": CONN, "path": TABLE_PATH},
        "columns": columns,
        "order": [c["id"] for c in columns],
        "style": dict(CARD),
    }


def list_control(el_id: str, control_id: str, name: str, column_id: str) -> dict:
    """List control sourced from the base table — filters cascade to every child element."""
    return {
        "id": el_id,
        "kind": "control",
        "controlId": control_id,
        "name": name,
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [],
        "source": {
            "kind": "source",
            "source": {"kind": "table", "elementId": "tbl-assignments"},
            "columnId": column_id,
        },
        "includeNulls": "never",
        "filters": [
            {"source": {"kind": "table", "elementId": "tbl-assignments"}, "columnId": column_id}
        ],
    }


def scope_control() -> dict:
    """Hidden include/exclude control; visible preset changes its calculated input."""
    return {
        "id": "ctrl-scope",
        "kind": "control",
        "controlId": "BookingScope",
        "name": "Booking scope",
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": ["Included"],
        "source": {"kind": "manual", "valueType": "text", "values": ["Included", "Excluded"]},
        "includeNulls": "never",
        "filters": [
            {"source": {"kind": "table", "elementId": "tbl-assignments"}, "columnId": "col-scope"}
        ],
    }


def window_control() -> dict:
    return {
        "id": "ctrl-window",
        "kind": "control",
        "controlId": "BookedWindow",
        "name": "Date window",
        "controlType": "segmented",
        "source": {"kind": "manual", "valueType": "text", "values": WINDOW_OPTIONS},
        "value": WINDOW_LABEL,
    }


def grain_control() -> dict:
    return {
        "id": "ctrl-grain",
        "kind": "control",
        "controlId": "BookedGrain",
        "name": "Trend grain",
        "controlType": "segmented",
        "source": {
            "kind": "manual",
            "valueType": "text",
            "values": ["Week", "Month", "Quarter"],
        },
        "value": "Week",
    }


def custom_date_control() -> dict:
    """Optional exact range layered on top of the preset; blank means no extra filter."""
    return {
        "id": "ctrl-date-range",
        "kind": "control",
        "controlId": "BookedDateRange",
        "name": "Fine-tune dates",
        "controlType": "date-range",
        "mode": "between",
        "includeNulls": "when-no-value-is-selected",
        "filters": [{
            "source": {"kind": "table", "elementId": "tbl-assignments"},
            "columnId": "col-created",
        }],
    }


def weekly_chart(el_id: str, label: str, kind: str, value_id: str, formula: str,
                 fmt: dict, color: str, *, series: tuple[str, str] | None = None,
                 stacking: str | None = None, trend_line: bool = False) -> dict:
    """Week-ending trend chart; `series` adds a stacked categorical breakout.

    A `trend_line` chart is Sigma's own linear regression overlay, not a second
    copy of the metric. Sigma only fits a regression when the x-axis carries a
    continuous (time) scale and the chart has no color encoding and no stacking,
    so those charts plot the datetime Week Ending and drop the single-color
    category trick — their series takes the theme's first categorical color.
    """
    x_id = f"{el_id}-x"
    columns = [
        {"id": value_id, "formula": formula, "name": label, "format": fmt},
    ]
    el: dict = {
        "id": el_id,
        "kind": kind,
        "name": title(label),
        "source": {"kind": "table", "elementId": "tbl-assignments"},
        "columns": columns,
        "xAxis": {"columnId": x_id},
        "yAxis": {"columnIds": [value_id]},
        "style": dict(CARD),
    }
    if trend_line:
        columns.insert(0, {"id": x_id, "formula": f"[{A}/Chart Period]",
                           "name": "Period", "format": DATE})
        el["stacking"] = "none"
        el["legend"] = {"visibility": "hidden"}
        el["dataLabel"] = {"labels": "shown", "fontSize": 11}
        el["trendlines"] = [{
            "columnId": value_id,
            "model": "linear",
            "line": {"style": "dashed", "width": 2, "color": NAVY_DEEP},
            "label": {"visibility": "shown", "text": "Linear regression"},
        }]
        return el

    columns.insert(0, {"id": x_id, "formula": f"[{A}/Chart Label]", "name": "Period"})
    if series:
        series_id, series_formula = series
        columns.append({"id": series_id, "formula": series_formula, "name": "Series"})
        el["color"] = {"by": "category", "column": series_id, "scheme": CATEGORICAL}
        el["legend"] = {"position": "bottom"}
        if stacking:
            el["stacking"] = stacking
    else:
        columns.append({"id": f"{el_id}-s", "formula": f'"{label}"', "name": "Series"})
        el["color"] = {"by": "category", "column": f"{el_id}-s", "scheme": [color]}
        el["legend"] = {"visibility": "hidden"}
        el["dataLabel"] = {"labels": "shown", "fontSize": 11}
    return el


def region_map(count_formula: str) -> dict:
    """US-state choropleth of Worksite State, with the count printed on each state.

    The label needs its own column: Sigma rejects a column that is already on the
    color channel, so the same count is declared twice under different ids.
    """
    return {
        "id": "chart-state",
        "kind": "region-map",
        "name": title("Assignment Booked by State — Contiguous US"),
        "source": {"kind": "table", "elementId": "tbl-assignments"},
        "columns": [
            {"id": "cs-x", "formula": f"[{A}/Worksite State]", "name": "State"},
            {"id": "cs-v", "formula": count_formula, "name": "Assignments", "format": INT},
            {"id": "cs-lbl", "formula": count_formula, "name": "Booked", "format": INT},
        ],
        "region": {"id": "cs-x", "regionType": "us-state"},
        "color": {
            "by": "scale",
            "column": "cs-v",
            "scheme": [TEAL_LIGHT, TEAL, NAVY_DEEP],
        },
        "label": [{"id": "cs-lbl"}],
        # Sigma auto-fits the map to whatever regions are present and the spec
        # exposes no center/zoom, so a handful of Alaska rows drag the frame out
        # far enough to fill it with Canada — the exact thing Megh objected to.
        # Excluding the non-contiguous states pins it to the lower 48; the
        # element title says so, and every other tile still counts them.
        "filters": [{
            "id": "cs-filter-contiguous",
            "columnId": "cs-x",
            "kind": "list",
            "mode": "exclude",
            "values": OFF_MAP_STATES,
        }],
        # The printed values carry the number, so the color scale legend is just
        # furniture — and it overlaps the element title. Maps take `visibility`;
        # `position` is rejected on this kind.
        "legend": {"visibility": "hidden"},
        "style": dict(CARD),
    }


def analyst_agent() -> dict:
    return {
        "id": "ag-barton",
        "name": "Barton Analyst",
        "description": "Ad hoc questions on assignment bookings beyond the predefined KPIs.",
        "instructions": (
            "You are an analyst for Barton Associates staffing assignments. "
            "Use the Assignments base table and the charts on this workbook. "
            "The reader controls the production-assignment window (5W, 13W, 26W, 52W, "
            "or All), trend grain (Week, Month, Quarter), and an optional exact date range. "
            "Metrics: assignment count; projected billing = Bill Rate * LOA * 8; "
            "GM$ = (Bill Rate - Pay Rate) * LOA * 8; GM% = GM$ / projected billing; average LOA. "
            "Dashboard 'Assignment Type' is Extension / New Assignment / Reassignment. "
            "Provider Type is Physician / Advanced Practice Nurse / Physician Assistant / Other. "
            "Answer ad hoc requests even when the metric is not on a chart. Be concise and quantitative."
        ),
        "greeting": {
            "mode": "static",
            "message": (
                "Ask me about bookings, GM, specialty, recruiter, or state — "
                "including questions that go beyond the charts. I can also focus a specialty."
            ),
        },
        "dataSources": [
            {"kind": "table", "elementId": "tbl-assignments"},
            {"kind": "table", "elementId": "tbl-detail"},
            {"kind": "table", "elementId": "chart-booked"},
            {"kind": "table", "elementId": "chart-state"},
        ],
        "tools": [
            {
                "toolId": "t-specialty",
                "kind": "action",
                "name": "Focus a specialty",
                "description": "Filter the dashboard to one main specialty.",
                "steps": [
                    {
                        "kind": "effect",
                        "effect": "set-control-value",
                        "control": "MainSpecialty",
                        "value": {
                            "type": "agent-input",
                            "inputName": "Main specialty to focus on",
                        },
                    }
                ],
            }
        ],
    }


def pie(el_id: str, label: str, dim_formula: str) -> dict:
    return {
        "id": el_id,
        "kind": "pie-chart",
        "name": title(label),
        "source": {"kind": "table", "elementId": "tbl-assignments"},
        "columns": [
            {"id": f"{el_id}-c", "formula": dim_formula, "name": "Category"},
            {
                "id": f"{el_id}-v",
                "formula": f"CountDistinct([{A}/Assignment Number])",
                "name": "Assignments",
                "format": INT,
            },
        ],
        "color": {"id": f"{el_id}-c"},
        "value": {"id": f"{el_id}-v"},
        "legend": {"position": "bottom"},
        "style": dict(CARD),
    }


def summary_kpi(el_id: str, name: str, formula: str, fmt: dict) -> dict:
    """Hidden aggregate feeding the narrative text via {{[Name/Value]}} bindings."""
    return {
        "id": el_id,
        "kind": "kpi-chart",
        "name": name,
        "source": {"kind": "table", "elementId": "tbl-assignments"},
        "columns": [{"id": f"{el_id}-v", "formula": formula, "name": "Value", "format": fmt}],
        "value": {"columnId": f"{el_id}-v", "color": NAVY, "fontSize": 22},
        "layout": {"anchor": "middle"},
        "style": {**CARD, "backgroundColor": "#F7FAFA"},
    }


def detail_table() -> dict:
    cols = [
        (
            "d-link",
            '"Click to view file"',
            "File Links",
            None,
        ),
        ("d-main", f"[{A}/Main Specialty]", "Main Specialty", None),
        ("d-sub", f"[{A}/Sub Specialty]", "Sub Specialty", None),
        ("d-an", f"[{A}/Assignment Number]", "Assn #", None),
        ("d-entity", f"[{A}/AE Entity]", "AE Entity", None),
        ("d-ae", f"[{A}/AE]", "AE", None),
        ("d-rec", f"[{A}/Recruiter]", "Recruiter", None),
        ("d-loa", f"[{A}/Assignment LOA]", "Assn LOA", NUM2),
        ("d-bill", f"[{A}/Bill Rate]", "Bill Rate", RATE),
        ("d-pay", f"[{A}/Pay Rate]", "Pay Rate", RATE),
        ("d-pb", f"[{A}/Projected Billing]", "Projected Billing", CUR_S),
        ("d-gm", f"[{A}/GM Dollars]", "GM $$", CUR_S),
        ("d-gmp", f"[{A}/GM Percent]", "GM % (GM$$ / Projected Billing)", PCT),
    ]
    columns = []
    for cid, formula, name, fmt in cols:
        col = {"id": cid, "formula": formula, "name": name}
        if fmt:
            col["format"] = fmt
        if cid == "d-link":
            col["link"] = {
                "kind": "formula",
                "formula": (
                    'Concat("https://bartonassociates.lightning.force.com/lightning/r/'
                    f'Assignment__c/", Text([{A}/Assignment Number]), "/view")'
                ),
            }
        columns.append(col)
    return {
        "id": "tbl-detail",
        "kind": "table",
        "name": title("Assignment Detail"),
        "source": {"kind": "table", "elementId": "tbl-assignments"},
        "columns": columns,
        "order": [c["id"] for c in columns],
        "sort": [
            {"columnId": "d-main", "direction": "ascending"},
            {"columnId": "d-gmp", "direction": "descending"},
        ],
        "style": dict(CARD),
    }


def report_button() -> dict:
    return {
        "id": "btn-report",
        "kind": "button",
        "text": "Open client-ready report ↗",
        "appearance": "filled",
        "actions": [{
            "id": "a-open-report",
            "trigger": "on-click",
            "effects": [{
                # Barton rejects `open-document` with a masked Invalid kind on
                # this button. The report's stable URL gives identical behavior
                # without relying on that workspace-gated action.
                "effect": "open-url",
                "url": REPORT_URL,
                "openTarget": "_blank",
            }],
        }],
    }


def build_elements() -> tuple[list[dict], str]:
    count_formula = f"CountDistinct([{A}/Assignment Number])"

    elements: list[dict] = [
        base_table(),
        list_control("ctrl-specialty", "MainSpecialty", "Main Specialty", "col-main-spec"),
        list_control("ctrl-sub", "SubSpecialty", "Sub Specialty", "col-sub-spec"),
        list_control("ctrl-type", "AssignmentType", "Assignment Type", "col-asgn-type"),
        list_control("ctrl-ae", "AccountExecutive", "AE", "col-ae"),
        list_control("ctrl-recruiter", "RecruiterName", "Recruiter", "col-recruiter"),
        scope_control(),
        window_control(),
        grain_control(),
        custom_date_control(),
        {"id": "container-filters", "kind": "container", "style": dict(CARD)},
        {"id": "container-ai", "kind": "container",
         "style": {**CARD, "borderColor": TEAL, "borderWidth": 2,
                   "backgroundColor": "#F4FBFA"}},
        # Area, not bar: Sigma will not fit a regression on a bar chart's
        # categorical axis, so the booked tile trades bars for a filled trend
        # that can carry the regression Megh asked for.
        weekly_chart("chart-booked", "Assignments Booked Trend", "area-chart",
                     "cb-v", count_formula, INT, TEAL, trend_line=True),
        weekly_chart("chart-type", "Bookings by Assignment Type", "bar-chart",
                     "ct-v", count_formula, INT, TEAL,
                     series=("ct-s", f"[{A}/Assignment Type]"), stacking="stacked"),
        weekly_chart("chart-provider", "Bookings by Provider Type", "bar-chart",
                     "cp-v", count_formula, INT, TEAL,
                     series=("cp-s", f"[{A}/Provider Type]"), stacking="stacked"),
        weekly_chart("chart-gm", "GM$ Trend", "line-chart",
                     "cg-v", f"Sum([{A}/GM Dollars])", CUR_S, TEAL_DARK, trend_line=True),
        weekly_chart("chart-gmpct", "GM% Trend", "line-chart",
                     "cgp-v",
                     f"Sum([{A}/GM Dollars]) / NullIf(Sum([{A}/Projected Billing]), 0)",
                     PCT, NAVY, trend_line=True),
        weekly_chart("chart-loa", "Average LOA Trend", "line-chart",
                     "cl-v", f"Avg([{A}/Assignment LOA])", NUM2, AMBER, trend_line=True),
        pie("pie-specialty", "Bookings by Specialty", f"[{A}/Main Specialty]"),
        pie("pie-sub", "Bookings by Sub Specialty", f"[{A}/Sub Specialty]"),
        region_map(count_formula),
        {"id": "chat-ask", "kind": "chat", "agentId": "ag-barton"},
        {
            "id": "txt-chat",
            "kind": "text",
            "body": "**Ask beyond the charts** — ad hoc questions against the assignment dataset.",
            "verticalAlign": "middle",
            "style": {"color": NAVY},
        },
        {
            "id": "txt-ai-prompt",
            "kind": "text",
            "body": (
                "**Try asking**\n\n"
                "• Which specialties gained momentum?\n\n"
                "• Where is GM% deteriorating?\n\n"
                "• Compare recruiters by bookings and GM$."
            ),
            "verticalAlign": "start",
            "style": {"color": SLATE, "backgroundColor": "#EAF8F6",
                      "borderRadius": "round"},
        },
        summary_kpi("kpi-total", "Booked Total", count_formula, INT),
        summary_kpi("kpi-avg-gm", "Avg GM", f"Avg([{A}/GM Percent])", PCT),
        summary_kpi("kpi-max-gm", "High GM", f"Max([{A}/GM Percent])", PCT),
        summary_kpi("kpi-min-gm", "Low GM", f"Min([{A}/GM Percent])", PCT),
        summary_kpi("kpi-avg-loa", "Avg LOA", f"Avg([{A}/Assignment LOA])", NUM2),
        summary_kpi("kpi-gm-dollars", "GM Dollars", f"Sum([{A}/GM Dollars])", CUR),
        {
            "id": "txt-summary",
            "kind": "text",
            "body": (
                "**{{[Booked Total/Value]}}** Total Assignment Booked with Avg GM of "
                "**{{[Avg GM/Value]}}**. Highest GM was {{[High GM/Value]}} and lowest GM was "
                "{{[Low GM/Value]}}. The Avg Assignment LOA was {{[Avg LOA/Value]}}. "
                "Assignment GM$ was **{{[GM Dollars/Value]}}**."
            ),
            "verticalAlign": "middle",
            "style": {"color": SLATE},
        },
        {
            "id": "txt-title",
            "kind": "text",
            "body": "## Assignment Performance",
            "verticalAlign": "middle",
            "style": {"color": NAVY},
        },
        {
            "id": "txt-subtitle",
            "kind": "text",
            "body": (
                "Production assignments · live Snowflake data · "
                "choose a preset, then optionally fine-tune an exact date range"
            ),
            "verticalAlign": "middle",
            "style": {"color": TEXT_MUTED},
        },
        report_button(),
        detail_table(),
    ]

    layout = f"""<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{PAGE_ID}">
  <Element elementId="txt-title" gridColumn="1 / 18" gridRow="1 / 3"/>
  <Element elementId="txt-subtitle" gridColumn="1 / 18" gridRow="3 / 5"/>
  <Element elementId="btn-report" gridColumn="19 / 25" gridRow="2 / 5"/>
  <Container elementId="container-filters" type="grid" gridColumn="1 / 25" gridRow="5 / 12" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-specialty" gridColumn="1 / 6" gridRow="1 / 4"/>
    <Element elementId="ctrl-sub" gridColumn="6 / 11" gridRow="1 / 4"/>
    <Element elementId="ctrl-type" gridColumn="11 / 16" gridRow="1 / 4"/>
    <Element elementId="ctrl-ae" gridColumn="16 / 21" gridRow="1 / 4"/>
    <Element elementId="ctrl-recruiter" gridColumn="21 / 25" gridRow="1 / 4"/>
    <Element elementId="ctrl-window" gridColumn="1 / 9" gridRow="4 / 7"/>
    <Element elementId="ctrl-grain" gridColumn="9 / 17" gridRow="4 / 7"/>
    <Element elementId="ctrl-date-range" gridColumn="17 / 25" gridRow="4 / 7"/>
  </Container>
  <Element elementId="kpi-total" gridColumn="1 / 5" gridRow="12 / 17"/>
  <Element elementId="kpi-avg-gm" gridColumn="5 / 9" gridRow="12 / 17"/>
  <Element elementId="kpi-max-gm" gridColumn="9 / 13" gridRow="12 / 17"/>
  <Element elementId="kpi-min-gm" gridColumn="13 / 17" gridRow="12 / 17"/>
  <Element elementId="kpi-avg-loa" gridColumn="17 / 21" gridRow="12 / 17"/>
  <Element elementId="kpi-gm-dollars" gridColumn="21 / 25" gridRow="12 / 17"/>
  <Element elementId="chart-booked" gridColumn="1 / 10" gridRow="17 / 31"/>
  <Element elementId="chart-type" gridColumn="10 / 18" gridRow="17 / 31"/>
  <Element elementId="chart-gm" gridColumn="1 / 10" gridRow="31 / 45"/>
  <Element elementId="chart-gmpct" gridColumn="10 / 18" gridRow="31 / 45"/>
  <Container elementId="container-ai" type="grid" gridColumn="18 / 25" gridRow="17 / 45" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-chat" gridColumn="1 / 13" gridRow="1 / 3"/>
    <Element elementId="txt-ai-prompt" gridColumn="1 / 13" gridRow="3 / 10"/>
    <Element elementId="chat-ask" gridColumn="1 / 13" gridRow="10 / 28"/>
  </Container>
  <Element elementId="chart-provider" gridColumn="1 / 13" gridRow="45 / 59"/>
  <Element elementId="chart-loa" gridColumn="13 / 25" gridRow="45 / 59"/>
  <Element elementId="pie-specialty" gridColumn="1 / 7" gridRow="59 / 75"/>
  <Element elementId="pie-sub" gridColumn="7 / 13" gridRow="59 / 75"/>
  <Element elementId="chart-state" gridColumn="13 / 25" gridRow="59 / 75"/>
  <Element elementId="txt-summary" gridColumn="1 / 25" gridRow="75 / 78"/>
  <Element elementId="tbl-detail" gridColumn="1 / 25" gridRow="78 / 105"/>
  <Element elementId="ctrl-scope" gridColumn="1 / 7" gridRow="105 / 108"/>
  <Element elementId="tbl-assignments" gridColumn="7 / 25" gridRow="105 / 108"/>
</Page>"""
    return elements, layout


def build_document() -> dict:
    # Imported here, not at module scope: the upcoming page pulls this module's
    # palette and warehouse constants, so a top-level import would be circular.
    import upcoming_page

    elements, layout = build_elements()
    return {
        "schemaVersion": 1,
        "kind": "workbook",
        "pages": [
            {"id": PAGE_ID, "name": "Assignment Booked"},
            {"id": upcoming_page.PAGE_ID, "name": "Upcoming Assignments"},
        ],
        "elements": elements + upcoming_page.elements(),
        "agents": [analyst_agent()],
        "layout": layout + "\n" + upcoming_page.LAYOUT,
        "settings": {
            "theme": {
                "overrides": {
                    "colors": {
                        "text": SLATE,
                        "highlight": TEAL,
                        "success": TEAL_DARK,
                        "warning": AMBER,
                        "danger": "#D64545",
                        "darkMode": "hidden",
                    },
                    "colorOverrides": {"backgroundCanvas": CANVAS, "canvasBackground": CANVAS},
                    "categoricalScheme": CATEGORICAL,
                    "backgroundColor": CANVAS,
                    "elementBackgroundColor": WHITE,
                    "pageWidth": "large",
                }
            }
        },
    }


def load_meta() -> dict:
    return json.loads(META_PATH.read_text()) if META_PATH.exists() else {}


def main() -> None:
    doc = build_document()
    meta = load_meta()
    workbook_id = meta.get("workbookId")

    payload = {"name": WORKBOOK_NAME, "folderId": FOLDER, "document": doc}
    (Path(__file__).resolve().parent / "spec-booked-dashboard.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    from sigma_api import try_api

    if workbook_id:
        status, body = try_api("PUT", f"/v2/workbooks/{workbook_id}/spec", payload)
        print("PUT", status, str(body)[:300] if status >= 400 else workbook_id)
    else:
        status, created = try_api("POST", "/v2/workbooks/spec", payload)
        print("POST", status, str(created)[:300])
        if status < 400:
            workbook_id = created.get("workbookId") or created.get("id")

    if not workbook_id or (isinstance(workbook_id, str) is False):
        return
    if status >= 400:
        return

    info_status, info = try_api("GET", f"/v2/workbooks/{workbook_id}")
    url = info.get("url", "") if isinstance(info, dict) else ""
    META_PATH.write_text(
        json.dumps(
            {
                "workbookId": workbook_id,
                "workbookUrlId": url.rstrip("/").split("/")[-1] if url else None,
                "folderId": FOLDER,
                "pageId": PAGE_ID,
            },
            indent=2,
        )
        + "\n"
    )
    print("workbookUrlId", url.rstrip("/").split("/")[-1] if url else None)

    shot = render_page_png(workbook_id, PAGE_ID, REPO / "artifacts/booked-dashboard.png")
    print("rendered", shot)


if __name__ == "__main__":
    main()
