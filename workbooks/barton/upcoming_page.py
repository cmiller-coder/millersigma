#!/usr/bin/env python3
"""Second tab: Upcoming Assignments — everything starting in the next 90 days.

From the Aug 24 session: Megh wanted the second tab to stop being a copy of the
booked view and instead answer "what starts soon", broken out weekly or monthly
by specialty, with the expected revenue behind it.

The page carries its own warehouse table (`tbl-upcoming`). Control filters
cascade to every child of their target element, so sharing one table with the
booked page would make the two windows intersect — an assignment booked in the
last five weeks AND starting in the next 90 days — which silently guts both
pages.
"""
from __future__ import annotations

from build_booked_dashboard import (
    CARD,
    CATEGORICAL,
    CONN,
    CUR,
    CUR_S,
    DATE,
    INT,
    NAVY,
    NAVY_DEEP,
    NUM2,
    PCT,
    SLATE,
    TABLE_PATH,
    TEAL,
    title,
)

PAGE_ID = "page-upcoming"
U = "Upcoming"  # element name child formulas resolve against
SRC_TBL = "ASSIGNMENT_PROD"
WINDOW_LABEL = "Next 90 Days"
HORIZON_DAYS = 90

# Weekly is the default grain; Megh asked to be able to flip to monthly.
GRAIN_CONTROL = "UpcomingGrain"
PERIOD_FORMULA = (
    f'Switch([{GRAIN_CONTROL}], '
    f'"Monthly", DateTrunc("month", [{SRC_TBL}/Start Date]), '
    f'DateTrunc("week", [{SRC_TBL}/Start Date]))'
)


def base_table() -> dict:
    raw = [
        ("an", "Assignment Number", "Assignment Number"),
        ("main-spec", "Main Specialty", "Main Specialty"),
        ("sub-spec", "Sub Specialty", "Sub Specialty"),
        ("asgn-type", "Reassignment", "Assignment Type"),
        ("ae", "AE", "AE"),
        ("recruiter", "Recruiter", "Recruiter"),
        ("state", "Worksite State", "Worksite State"),
        ("loa", "Assignment LOA", "Assignment LOA"),
        ("bill", "Bill Rate", "Bill Rate"),
        ("pay", "Pay Rate", "Pay Rate"),
        ("start", "Start Date", "Start Date"),
        ("prod", "prod_assignment", "Prod Assignment"),
    ]
    columns = [
        {"id": f"u-col-{slug}", "formula": f"[{SRC_TBL}/{src}]", "name": name}
        for slug, src, name in raw
    ]
    columns += [
        {"id": "u-col-start-period", "formula": PERIOD_FORMULA, "name": "Start Period",
         "format": DATE},
        {"id": "u-col-days-out",
         "formula": f'DateDiff("day", Today(), [{SRC_TBL}/Start Date])',
         "name": "Days Out", "format": INT},
        {"id": "u-col-scope",
         "formula": (
             f'If([Days Out] >= 0 and [Days Out] <= {HORIZON_DAYS} '
             f'and [Prod Assignment] = "Yes", "{WINDOW_LABEL}", "Excluded")'
         ),
         "name": "Start Window"},
        {"id": "u-col-billing", "formula": "[Bill Rate] * [Assignment LOA] * 8",
         "name": "Expected Revenue", "format": CUR},
        {"id": "u-col-gm", "formula": "([Bill Rate] - [Pay Rate]) * [Assignment LOA] * 8",
         "name": "GM Dollars", "format": CUR},
        {"id": "u-col-gm-pct", "formula": "[GM Dollars] / NullIf([Expected Revenue], 0)",
         "name": "GM Percent", "format": PCT},
    ]
    return {
        "id": "tbl-upcoming",
        "kind": "table",
        "name": U,
        "visibleAsSource": True,
        "source": {"kind": "warehouse-table", "connectionId": CONN, "path": TABLE_PATH},
        "columns": columns,
        "order": [c["id"] for c in columns],
        "style": dict(CARD),
    }


def window_control() -> dict:
    return {
        "id": "u-ctrl-window",
        "kind": "control",
        "controlId": "UpcomingWindow",
        "name": "Start window",
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [WINDOW_LABEL],
        "source": {"kind": "manual", "valueType": "text",
                   "values": [WINDOW_LABEL, "Excluded"]},
        "includeNulls": "never",
        "filters": [{"source": {"kind": "table", "elementId": "tbl-upcoming"},
                     "columnId": "u-col-scope"}],
    }


def grain_control() -> dict:
    return {
        "id": "u-ctrl-grain",
        "kind": "control",
        "controlId": GRAIN_CONTROL,
        "name": "Grain",
        "controlType": "segmented",
        "source": {"kind": "manual", "valueType": "text",
                   "values": ["Weekly", "Monthly"]},
        "value": "Weekly",
    }


def list_control(el_id: str, control_id: str, name: str, column_id: str) -> dict:
    return {
        "id": el_id,
        "kind": "control",
        "controlId": control_id,
        "name": name,
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [],
        "source": {"kind": "source",
                   "source": {"kind": "table", "elementId": "tbl-upcoming"},
                   "columnId": column_id},
        "includeNulls": "never",
        "filters": [{"source": {"kind": "table", "elementId": "tbl-upcoming"},
                     "columnId": column_id}],
    }


def trend(el_id: str, label: str, kind: str, value_id: str, formula: str,
          fmt: dict) -> dict:
    """Start-period trend with Sigma's linear regression.

    Same constraints as the booked page: continuous axis, no stacking, no color
    encoding, or Sigma keeps the field and draws nothing.
    """
    return {
        "id": el_id,
        "kind": kind,
        "name": title(label),
        "source": {"kind": "table", "elementId": "tbl-upcoming"},
        "columns": [
            {"id": f"{el_id}-x", "formula": f"[{U}/Start Period]", "name": "Starting",
             "format": DATE},
            {"id": value_id, "formula": formula, "name": label, "format": fmt},
        ],
        "xAxis": {"columnId": f"{el_id}-x"},
        "yAxis": {"columnIds": [value_id]},
        "stacking": "none",
        "legend": {"visibility": "hidden"},
        "dataLabel": {"labels": "shown", "fontSize": 11},
        "trendlines": [{
            "columnId": value_id,
            "model": "linear",
            "line": {"style": "dashed", "width": 2, "color": NAVY_DEEP},
            "label": {"visibility": "shown", "text": "Linear regression"},
        }],
        "style": dict(CARD),
    }


def kpi(el_id: str, name: str, formula: str, fmt: dict) -> dict:
    return {
        "id": el_id,
        "kind": "kpi-chart",
        "name": name,
        "source": {"kind": "table", "elementId": "tbl-upcoming"},
        "columns": [{"id": f"{el_id}-v", "formula": formula, "name": "Value",
                     "format": fmt}],
        "value": {"columnId": f"{el_id}-v", "color": NAVY, "fontSize": 22},
        "layout": {"anchor": "middle"},
        "style": {**CARD, "backgroundColor": "#F7FAFA"},
    }


def detail_table() -> dict:
    cols = [
        ("ud-link", '"Click to view file"', "File Links", None),
        ("ud-start", f"[{U}/Start Date]", "Start Date", DATE),
        ("ud-days", f"[{U}/Days Out]", "Days Out", INT),
        ("ud-main", f"[{U}/Main Specialty]", "Main Specialty", None),
        ("ud-sub", f"[{U}/Sub Specialty]", "Sub Specialty", None),
        ("ud-an", f"[{U}/Assignment Number]", "Assn #", None),
        ("ud-ae", f"[{U}/AE]", "AE", None),
        ("ud-rec", f"[{U}/Recruiter]", "Recruiter", None),
        ("ud-state", f"[{U}/Worksite State]", "State", None),
        ("ud-loa", f"[{U}/Assignment LOA]", "Assn LOA", NUM2),
        ("ud-rev", f"[{U}/Expected Revenue]", "Expected Revenue", CUR_S),
        ("ud-gmp", f"[{U}/GM Percent]", "GM %", PCT),
    ]
    columns = []
    for cid, formula, name, fmt in cols:
        col = {"id": cid, "formula": formula, "name": name}
        if fmt:
            col["format"] = fmt
        if cid == "ud-link":
            col["link"] = {
                "kind": "formula",
                "formula": (
                    'Concat("https://bartonassociates.lightning.force.com/lightning/r/'
                    f'Assignment__c/", Text([{U}/Assignment Number]), "/view")'
                ),
            }
        columns.append(col)
    return {
        "id": "tbl-upcoming-detail",
        "kind": "table",
        "name": title(f"Assignments Starting in the Next {HORIZON_DAYS} Days"),
        "source": {"kind": "table", "elementId": "tbl-upcoming"},
        "columns": columns,
        "order": [c["id"] for c in columns],
        "sort": [{"columnId": "ud-days", "direction": "ascending"}],
        "style": dict(CARD),
    }


def elements() -> list[dict]:
    count = f"CountDistinct([{U}/Assignment Number])"
    return [
        base_table(),
        window_control(),
        grain_control(),
        list_control("u-ctrl-specialty", "UpcomingSpecialty", "Main Specialty",
                     "u-col-main-spec"),
        list_control("u-ctrl-type", "UpcomingAssignmentType", "Assignment Type",
                     "u-col-asgn-type"),
        list_control("u-ctrl-ae", "UpcomingAE", "AE", "u-col-ae"),
        {"id": "u-container-filters", "kind": "container", "style": dict(CARD)},
        trend("u-chart-starts", f"Assignments Starting — Next {HORIZON_DAYS} Days",
              "area-chart", "us-v", count, INT),
        trend("u-chart-revenue", f"Expected Revenue — Next {HORIZON_DAYS} Days",
              "line-chart", "ur-v", f"Sum([{U}/Expected Revenue])", CUR_S),
        {
            "id": "u-chart-specialty",
            "kind": "bar-chart",
            "name": title("Starts by Specialty"),
            "source": {"kind": "table", "elementId": "tbl-upcoming"},
            "columns": [
                {"id": "usp-x", "formula": f"[{U}/Start Period]", "name": "Starting",
                 "format": DATE},
                {"id": "usp-v", "formula": count, "name": "Assignments", "format": INT},
                {"id": "usp-s", "formula": f"[{U}/Main Specialty]", "name": "Specialty"},
            ],
            "xAxis": {"columnId": "usp-x"},
            "yAxis": {"columnIds": ["usp-v"]},
            "color": {"by": "category", "column": "usp-s", "scheme": CATEGORICAL},
            "stacking": "stacked",
            "legend": {"position": "bottom"},
            "style": dict(CARD),
        },
        {
            "id": "u-chart-rank",
            "kind": "bar-chart",
            "name": title("Expected Revenue by Specialty"),
            "source": {"kind": "table", "elementId": "tbl-upcoming"},
            "columns": [
                {"id": "urk-x", "formula": f"[{U}/Main Specialty]", "name": "Specialty"},
                {"id": "urk-v", "formula": f"Sum([{U}/Expected Revenue])",
                 "name": "Expected Revenue", "format": CUR_S},
                {"id": "urk-s", "formula": '"Expected Revenue"', "name": "Series"},
            ],
            "xAxis": {"columnId": "urk-x",
                      "sort": {"by": "urk-v", "direction": "descending"}},
            "yAxis": {"columnIds": ["urk-v"]},
            "color": {"by": "category", "column": "urk-s", "scheme": [TEAL]},
            "legend": {"visibility": "hidden"},
            "dataLabel": {"labels": "shown", "fontSize": 10},
            "style": dict(CARD),
        },
        kpi("u-kpi-count", "Upcoming Starts", count, INT),
        kpi("u-kpi-revenue", "Expected Revenue", f"Sum([{U}/Expected Revenue])", CUR),
        kpi("u-kpi-gm", "Expected GM$", f"Sum([{U}/GM Dollars])", CUR),
        kpi("u-kpi-gm-pct", "Avg GM %", f"Avg([{U}/GM Percent])", PCT),
        kpi("u-kpi-loa", "Avg LOA", f"Avg([{U}/Assignment LOA])", NUM2),
        {
            "id": "u-txt-title",
            "kind": "text",
            "body": f"## Upcoming Assignments — Starting in the Next {HORIZON_DAYS} Days",
            "verticalAlign": "middle",
            "style": {"color": NAVY},
        },
        {
            "id": "u-txt-summary",
            "kind": "text",
            "body": (
                "**{{[Upcoming Starts/Value]}}** assignments start in the next "
                f"{HORIZON_DAYS} days, worth **{{{{[Expected Revenue/Value]}}}}** of "
                "expected revenue at **{{[Avg GM %/Value]}}** average GM. "
                "Average LOA is {{[Avg LOA/Value]}} weeks."
            ),
            "verticalAlign": "middle",
            "style": {"color": SLATE},
        },
        detail_table(),
    ]


LAYOUT = f"""<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{PAGE_ID}">
  <Element elementId="u-txt-title" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Container elementId="u-container-filters" type="grid" gridColumn="1 / 25" gridRow="3 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="u-ctrl-specialty" gridColumn="1 / 6" gridRow="1 / 4"/>
    <Element elementId="u-ctrl-type" gridColumn="6 / 11" gridRow="1 / 4"/>
    <Element elementId="u-ctrl-ae" gridColumn="11 / 16" gridRow="1 / 4"/>
    <Element elementId="u-ctrl-window" gridColumn="16 / 21" gridRow="1 / 4"/>
    <Element elementId="u-ctrl-grain" gridColumn="21 / 25" gridRow="1 / 4"/>
  </Container>
  <Element elementId="u-kpi-count" gridColumn="1 / 6" gridRow="6 / 11"/>
  <Element elementId="u-kpi-revenue" gridColumn="6 / 11" gridRow="6 / 11"/>
  <Element elementId="u-kpi-gm" gridColumn="11 / 16" gridRow="6 / 11"/>
  <Element elementId="u-kpi-gm-pct" gridColumn="16 / 21" gridRow="6 / 11"/>
  <Element elementId="u-kpi-loa" gridColumn="21 / 25" gridRow="6 / 11"/>
  <Element elementId="u-txt-summary" gridColumn="1 / 25" gridRow="11 / 14"/>
  <Element elementId="u-chart-starts" gridColumn="1 / 13" gridRow="14 / 28"/>
  <Element elementId="u-chart-revenue" gridColumn="13 / 25" gridRow="14 / 28"/>
  <Element elementId="u-chart-specialty" gridColumn="1 / 13" gridRow="28 / 44"/>
  <Element elementId="u-chart-rank" gridColumn="13 / 25" gridRow="28 / 44"/>
  <Element elementId="tbl-upcoming-detail" gridColumn="1 / 25" gridRow="44 / 68"/>
  <Element elementId="tbl-upcoming" gridColumn="1 / 25" gridRow="68 / 72"/>
</Page>"""
