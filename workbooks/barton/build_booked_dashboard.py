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

# Production assignments booked within the trailing 5 week-ending buckets.
WINDOW_LABEL = "Last 5 Weeks"
SCOPE_FORMULA = (
    f'If([Weeks Back] >= 0 and [Weeks Back] <= 4 and [Prod Assignment] = "Yes", '
    f'"{WINDOW_LABEL}", "Excluded")'
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
    """Drives the 5-week production-assignment window. Default value does the filtering."""
    return {
        "id": "ctrl-window",
        "kind": "control",
        "controlId": "BookingWindow",
        "name": "Booking window",
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [WINDOW_LABEL],
        "source": {"kind": "manual", "valueType": "text", "values": [WINDOW_LABEL, "Excluded"]},
        "includeNulls": "never",
        "filters": [
            {"source": {"kind": "table", "elementId": "tbl-assignments"}, "columnId": "col-scope"}
        ],
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
        columns.insert(0, {"id": x_id, "formula": f"[{A}/Week Ending]",
                           "name": "Week Ending", "format": DATE})
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

    columns.insert(0, {"id": x_id, "formula": f"[{A}/Week Label]", "name": "Week Ending"})
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
        "name": title("Assignment Booked by State Last 5 Weeks"),
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
            "Default scope is production assignments in the last five week-ending buckets. "
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
                "including questions that go beyond the charts on this page."
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
        "name": title("Total Assignment Booked Last 5 Weeks"),
        "source": {"kind": "table", "elementId": "tbl-assignments"},
        "columns": columns,
        "order": [c["id"] for c in columns],
        "sort": [
            {"columnId": "d-main", "direction": "ascending"},
            {"columnId": "d-gmp", "direction": "descending"},
        ],
        "style": dict(CARD),
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
        {"id": "container-filters", "kind": "container", "style": dict(CARD)},
        # Area, not bar: Sigma will not fit a regression on a bar chart's
        # categorical axis, so the booked tile trades bars for a filled trend
        # that can carry the regression Megh asked for.
        weekly_chart("chart-booked", "Assignment Booked Last 5 Weeks", "area-chart",
                     "cb-v", count_formula, INT, TEAL, trend_line=True),
        weekly_chart("chart-type", "Assignment Booked Assignment Type Last 5 Weeks", "bar-chart",
                     "ct-v", count_formula, INT, TEAL,
                     series=("ct-s", f"[{A}/Assignment Type]"), stacking="stacked"),
        weekly_chart("chart-provider", "Assignment Booked Provider Type Last 5 Weeks", "bar-chart",
                     "cp-v", count_formula, INT, TEAL,
                     series=("cp-s", f"[{A}/Provider Type]"), stacking="stacked"),
        weekly_chart("chart-gm", "Assignment Booked GM$ Last 5 Weeks", "line-chart",
                     "cg-v", f"Sum([{A}/GM Dollars])", CUR_S, TEAL_DARK, trend_line=True),
        weekly_chart("chart-gmpct", "Assignment Booked GM% Last 5 Weeks", "line-chart",
                     "cgp-v",
                     f"Sum([{A}/GM Dollars]) / NullIf(Sum([{A}/Projected Billing]), 0)",
                     PCT, NAVY, trend_line=True),
        weekly_chart("chart-loa", "Assignment Booked Average LOA Last 5 Weeks", "line-chart",
                     "cl-v", f"Avg([{A}/Assignment LOA])", NUM2, AMBER, trend_line=True),
        pie("pie-specialty", "Assignment Booked by Specialty Last 5 Weeks", f"[{A}/Main Specialty]"),
        pie("pie-sub", "Assignment Booked by Sub Specialty Last 5 Weeks", f"[{A}/Sub Specialty]"),
        region_map(count_formula),
        {"id": "chat-ask", "kind": "chat", "agentId": "ag-barton"},
        {
            "id": "txt-chat",
            "kind": "text",
            "body": "**Ask beyond the charts** — ad hoc questions against the assignment dataset.",
            "verticalAlign": "middle",
            "style": {"color": NAVY},
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
            "body": "## Assignment Booked — Last 5 Weeks",
            "verticalAlign": "middle",
            "style": {"color": NAVY},
        },
        detail_table(),
    ]

    layout = f"""<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{PAGE_ID}">
  <Element elementId="txt-title" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Container elementId="container-filters" type="grid" gridColumn="1 / 25" gridRow="3 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-specialty" gridColumn="1 / 5" gridRow="1 / 4"/>
    <Element elementId="ctrl-sub" gridColumn="5 / 9" gridRow="1 / 4"/>
    <Element elementId="ctrl-type" gridColumn="9 / 13" gridRow="1 / 4"/>
    <Element elementId="ctrl-ae" gridColumn="13 / 17" gridRow="1 / 4"/>
    <Element elementId="ctrl-recruiter" gridColumn="17 / 21" gridRow="1 / 4"/>
    <Element elementId="ctrl-window" gridColumn="21 / 25" gridRow="1 / 4"/>
  </Container>
  <Element elementId="chart-booked" gridColumn="1 / 9" gridRow="6 / 18"/>
  <Element elementId="chart-type" gridColumn="9 / 17" gridRow="6 / 18"/>
  <Element elementId="chart-provider" gridColumn="17 / 25" gridRow="6 / 18"/>
  <Element elementId="chart-gm" gridColumn="1 / 9" gridRow="18 / 30"/>
  <Element elementId="chart-gmpct" gridColumn="9 / 17" gridRow="18 / 30"/>
  <Element elementId="chart-loa" gridColumn="17 / 25" gridRow="18 / 30"/>
  <Element elementId="pie-specialty" gridColumn="1 / 7" gridRow="30 / 46"/>
  <Element elementId="pie-sub" gridColumn="7 / 13" gridRow="30 / 46"/>
  <Element elementId="chart-state" gridColumn="13 / 25" gridRow="30 / 46"/>
  <Element elementId="txt-chat" gridColumn="1 / 25" gridRow="46 / 48"/>
  <Element elementId="chat-ask" gridColumn="1 / 25" gridRow="48 / 58"/>
  <Element elementId="txt-summary" gridColumn="1 / 25" gridRow="58 / 61"/>
  <Element elementId="tbl-detail" gridColumn="1 / 25" gridRow="61 / 85"/>
  <Element elementId="kpi-total" gridColumn="1 / 5" gridRow="85 / 90"/>
  <Element elementId="kpi-avg-gm" gridColumn="5 / 9" gridRow="85 / 90"/>
  <Element elementId="kpi-max-gm" gridColumn="9 / 13" gridRow="85 / 90"/>
  <Element elementId="kpi-min-gm" gridColumn="13 / 17" gridRow="85 / 90"/>
  <Element elementId="kpi-avg-loa" gridColumn="17 / 21" gridRow="85 / 90"/>
  <Element elementId="kpi-gm-dollars" gridColumn="21 / 25" gridRow="85 / 90"/>
  <Element elementId="tbl-assignments" gridColumn="1 / 25" gridRow="90 / 94"/>
</Page>"""
    return elements, layout


def build_document() -> dict:
    elements, layout = build_elements()
    return {
        "schemaVersion": 1,
        "kind": "workbook",
        "pages": [{"id": PAGE_ID, "name": "Assignment Booked"}],
        "elements": elements,
        "agents": [analyst_agent()],
        "layout": layout,
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
