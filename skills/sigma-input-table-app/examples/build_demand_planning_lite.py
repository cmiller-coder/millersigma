# Demand Planning — Lite (workbooks-as-code EXAMPLE).
# Usage: python3 build_demand_planning_lite.py <SIGMA_BASE_URL> <TOKEN> <CONNECTION_ID> <FOLDER_ID>
#
# Case study: one-shot recreation of a real, complex production Sigma app (a
# multi-plan Demand Planning tool: plan lifecycle, AI panel, linked input
# tables, ~3,200-line spec) DISTILLED to its core scenario-modeling mechanic —
# actuals vs. statistical forecast vs. an editable demand plan — using the
# verified linked-input-table pattern in ../reference/scenario-modeler-pattern.md.
#
# The goal of a "lite" recreation isn't full fidelity — it's proving you can
# look at any Sigma app and rebuild its ESSENTIAL interaction loop from code in
# one pass. Drop everything that isn't that loop (multi-plan management, AI
# summarization, submit/approve workflow) rather than trying to clone the
# whole spec 1:1.
import json, os, sys, urllib.request, urllib.error

BASE, TOKEN, CONN, FOLDER = sys.argv[1:5]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def call(url, payload, method="POST"):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=H, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


NUM2S = {"kind": "number", "formatString": ",.2s"}
PCT1 = {"kind": "number", "formatString": ",.1%"}

SQL = """
WITH months AS (
  SELECT SEQ4() - 6 AS relative_month
  FROM TABLE(GENERATOR(ROWCOUNT => 19))
),
calc AS (
  SELECT
    relative_month,
    DATEADD('month', relative_month, DATE_TRUNC('month', CURRENT_DATE())) AS month_start,
    12000 AS demand_base,
    ROUND(1500 * SIN((relative_month + 3) * 3.14159265 / 6), 0) AS demand_season,
    relative_month * 120 AS demand_growth,
    (MOD(ABS(HASH(relative_month)), 700) - 350) AS noise
  FROM months
)
SELECT
  relative_month,
  month_start,
  demand_base + demand_season + demand_growth AS demand_fcst,
  CASE WHEN relative_month <= 0
    THEN demand_base + demand_season + demand_growth + noise
    ELSE NULL
  END AS sales
FROM calc
ORDER BY relative_month
""".strip()

elements = [
    {
        "id": "hdr",
        "kind": "text",
        "body": "<span style=\"font-size: 18px\">**Demand Planning — lightweight rebuild.** "
        "One-shot recreation of the core scenario-modeling mechanic: actuals vs. "
        "statistical forecast vs. an editable demand plan.</span>",
        "verticalAlign": "middle",
    },
    # 1. Base — one row per month, straight off a synthetic SQL source.
    #    ⚠ TWO gotchas live in this one element:
    #    (a) A bare `formula:"[demand_fcst]"` does NOT reach the raw SQL
    #        output when the element also hand-authors its own `columns`
    #        array — it must be qualified as `[Custom SQL/demand_fcst]` (the
    #        raw query result has an implicit source name "Custom SQL", even
    #        referenced from within the very element that IS the SQL source).
    #        Omitting the qualifier renders every cell as the literal string
    #        `Unknown column "[demand_fcst]"`, which cascades into every
    #        downstream linked-input-table/chart as "Join key contains type
    #        error" — a confusing error pointing at the wrong element.
    #    (b) Give declared passthrough columns a DISPLAY NAME that differs
    #        from the raw column the formula references, e.g.
    #        name:"StatForecast" for formula:"[Custom SQL/demand_fcst]" —
    #        naming it "demand_fcst" too makes the bare bracket resolve to
    #        ITSELF (a sibling column of the same name) instead of the
    #        qualified target, which Sigma rejects as "Circular column
    #        reference to [demand_fcst]".
    {
        "id": "srcTbl",
        "kind": "table",
        "source": {"connectionId": CONN, "statement": SQL, "kind": "sql"},
        "name": "Demand Source",
        "visibleAsSource": True,
        "columns": [
            {"id": "c_relmonth", "formula": "[Custom SQL/relative_month]", "name": "RelMonth"},
            {"id": "c_month", "formula": "[Custom SQL/month_start]", "name": "MonthStart"},
            {"id": "c_fcst", "formula": "[Custom SQL/demand_fcst]", "name": "StatForecast"},
            {"id": "c_sales", "formula": "[Custom SQL/sales]", "name": "ActualSalesRaw"},
        ],
    },
    # 2. Linked input table — the editable demand-plan grid (verified pattern:
    #    ../reference/scenario-modeler-pattern.md §4). inputMode "view" so
    #    it's editable once PUBLISHED, not just in the draft editor.
    # ⚠ Element id has a stray "3" (bumped twice): once a linked input
    # table's columns have materialized with a type (e.g. inferred as "text"
    # while its upstream source was erroring), a later PUT that fixes the
    # upstream and would change that column's real type to "number" is
    # rejected — "type change is not supported... Drop and re-add the column
    # to change its type." Give the WHOLE input-table element a fresh id
    # (forcing a real drop-and-recreate) rather than trying to patch types in
    # place. A from-scratch build wouldn't hit this; it only bites when
    # iterating on a spec that's already been PUT once with a bug upstream —
    # or when a stale open browser tab overwrites your fix with an old
    # snapshot (see ../reference/recreating-existing-apps.md) and you have to
    # redo the fix, bumping the id again.
    {
        "id": "assum3",
        "kind": "input-table",
        "source": {"kind": "linked", "from": "srcTbl"},
        "inputMode": "view",
        "name": "Assumptions",
        "columns": [
            {"id": "ia-relmonth3", "key": "c_relmonth"},
            {"id": "ia-month3", "key": "c_month"},
            {"id": "ia-fcst3", "key": "c_fcst"},
            {"id": "ia-sales3", "key": "c_sales"},
            {"id": "ia-season3", "type": "number", "name": "Season Adj %"},
            {"id": "ia-growth3", "type": "number", "name": "Growth Adj %"},
            {"id": "ia-events3", "type": "number", "name": "Events Bump"},
            {
                "id": "ia-adj3",
                "formula": "[StatForecast] * (1 + Coalesce([Season Adj %], 0) / 100.0) "
                "* (1 + Coalesce([Growth Adj %], 0) / 100.0) + Coalesce([Events Bump], 0)",
                "name": "AdjustedDemandPlan",
            },
        ],
        "sort": [{"columnId": "ia-relmonth3", "direction": "ascending", "nulls": "last"}],
        "tableComponents": {"summaryBar": "hidden"},
    },
    # 3. Book — the single downstream read surface every chart/KPI uses.
    {
        "id": "book",
        "kind": "table",
        "source": {"elementId": "assum3", "kind": "table"},
        "name": "Book",
        "visibleAsSource": True,
        "columns": [
            {"id": "bk-relmonth", "formula": "[Assumptions/RelMonth]", "name": "relmonth"},
            {"id": "bk-month", "formula": "[Assumptions/MonthStart]", "name": "monthdt"},
            {"id": "bk-fcst", "formula": "[Assumptions/StatForecast]", "name": "statfcst"},
            {"id": "bk-sales", "formula": "[Assumptions/ActualSalesRaw]", "name": "actsales"},
            {"id": "bk-adj", "formula": "[Assumptions/AdjustedDemandPlan]", "name": "adjplan"},
        ],
    },
    {
        "kind": "control",
        # ⚠ controlId must match ^[a-zA-Z0-9_-]{1,64}$ on POST-create — a
        # dotted id like "c.horizon" (seen in some UI-built GET-backs) is
        # rejected fresh: "Invalid id format".
        "controlId": "ctrl_horizon",
        "id": "ctrlHorizon",
        "name": "Horizon",
        "controlType": "number-range",
        "includeNulls": "when-no-value-is-selected",
        "min": -6,
        "max": 12,
        "filters": [{"source": {"kind": "table", "elementId": "book"}, "columnId": "bk-relmonth"}],
    },
    {
        "id": "btnReset",
        "kind": "button",
        "text": "Reset assumptions",
        "appearance": "outline",
        "align": "stretch",
        "fillColor": "#333333",
        "fontColor": "#333333",
        "actions": [
            {
                "id": "actReset",
                "trigger": "on-click",
                "effects": [
                    {
                        "effect": "update-rows",
                        "table": "assum3",
                        "whichRows": {"type": "formula", "formula": "True"},
                        "values": {
                            "ia-season3": {"type": "constant", "value": {"type": "number", "value": None}},
                            "ia-growth3": {"type": "constant", "value": {"type": "number", "value": None}},
                            "ia-events3": {"type": "constant", "value": {"type": "number", "value": None}},
                        },
                    }
                ],
            }
        ],
    },
    {
        "id": "btnLift",
        "kind": "button",
        "text": "Apply +10% market lift (future months)",
        "appearance": "filled",
        "align": "stretch",
        "fillColor": "#0099ff",
        "fontColor": "#ffffff",
        "actions": [
            {
                "id": "actLift",
                "trigger": "on-click",
                "effects": [
                    {
                        "effect": "update-rows",
                        "table": "assum3",
                        "whichRows": {"type": "formula", "formula": "[RelMonth] >= 0"},
                        "values": {"ia-growth3": {"type": "constant", "value": {"type": "number", "value": 10}}},
                    }
                ],
            }
        ],
    },
    {
        "id": "chart1",
        "kind": "line-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [
            {"id": "chM", "formula": "DateTrunc(\"day\", [Book/monthdt])", "name": "Month", "format": {"kind": "datetime", "formatString": "%b %Y"}},
            {"id": "chFcstStat", "formula": "Sum([Book/statfcst])", "name": "Statistical forecast", "format": NUM2S},
            {"id": "chSales", "formula": "Sum([Book/actsales])", "name": "Actual sales", "format": NUM2S},
            {"id": "chAdj", "formula": "Sum([Book/adjplan])", "name": "Adjusted demand plan", "format": NUM2S},
        ],
        "yAxis": {"columnIds": ["chFcstStat", "chSales", "chAdj"], "format": {"scale": {"type": "linear", "zero": True}}},
        "xAxis": {"columnId": "chM", "format": {"scale": {"type": "time", "zero": False}}},
        "name": {"text": "Actuals vs statistical forecast vs adjusted demand plan"},
        "legend": {"position": "top-left"},
        "stacking": "none",
        "lineAreaStyle": {"interpolation": "monotone", "missing": "hide"},
    },
    {
        "id": "kpiFcst",
        "kind": "kpi-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [{"id": "kv", "formula": "Sum([Book/statfcst])", "format": NUM2S}],
        "value": {"columnId": "kv"},
        "name": {"text": "Total statistical demand", "fontSize": 16},
        "style": {"backgroundColor": "#FFFFFF", "borderColor": "#333333", "borderWidth": 1},
    },
    {
        "id": "kpiAdj",
        "kind": "kpi-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [{"id": "kv", "formula": "Sum([Book/adjplan])", "format": NUM2S}],
        "value": {"columnId": "kv"},
        "name": {"text": "Total adjusted demand plan", "fontSize": 16},
        "style": {"backgroundColor": "#FFFFFF", "borderColor": "#333333", "borderWidth": 1},
    },
    {
        "id": "kpiDelta",
        "kind": "kpi-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [{"id": "kv", "formula": "(Sum([Book/adjplan]) - Sum([Book/statfcst])) / NullIf(Sum([Book/statfcst]), 0)", "format": PCT1}],
        "value": {"columnId": "kv"},
        "name": {"text": "Δ plan vs statistical", "fontSize": 16},
        "style": {"backgroundColor": "#FFFFFF", "borderColor": "#333333", "borderWidth": 1},
    },
    {
        "id": "kpiAccuracy",
        "kind": "kpi-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [{"id": "kv", "formula": "1 - Sum(Abs([Book/actsales] - [Book/statfcst])) / NullIf(Sum([Book/actsales]), 0)", "format": PCT1}],
        "value": {"columnId": "kv"},
        "name": {"text": "Forecast accuracy (historical)", "fontSize": 16},
        "style": {"backgroundColor": "#FFFFFF", "borderColor": "#333333", "borderWidth": 1},
    },
]

# ⚠ Every element must be placed in the layout — including "backend" tables
# (srcTbl/book) that are only there as sources for other elements. Omitting
# one is a hard error here ("element 'X' is not placed in layout"), even
# though some other Sigma environments auto-stack unplaced elements.
layout = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pgMain">
  <Element elementId="hdr" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="ctrlHorizon" gridColumn="1 / 7" gridRow="3 / 5"/>
  <Element elementId="btnReset" gridColumn="7 / 13" gridRow="3 / 5"/>
  <Element elementId="btnLift" gridColumn="13 / 19" gridRow="3 / 5"/>
  <Element elementId="chart1" gridColumn="1 / 17" gridRow="5 / 21"/>
  <Element elementId="kpiFcst" gridColumn="17 / 25" gridRow="5 / 10"/>
  <Element elementId="kpiAdj" gridColumn="17 / 25" gridRow="10 / 15"/>
  <Element elementId="kpiDelta" gridColumn="17 / 25" gridRow="15 / 18"/>
  <Element elementId="kpiAccuracy" gridColumn="17 / 25" gridRow="18 / 21"/>
  <Element elementId="assum3" gridColumn="1 / 25" gridRow="21 / 32"/>
  <Element elementId="srcTbl" gridColumn="1 / 13" gridRow="32 / 40"/>
  <Element elementId="book" gridColumn="13 / 25" gridRow="32 / 40"/>
</Page>
"""

body = {
    "name": "Demand Planning — Lite",
    "folderId": FOLDER,
    "document": {
        "schemaVersion": 1,
        "kind": "workbook",
        "elements": elements,
        "pages": [{"id": "pgMain", "name": "Demand Planning"}],
        "layout": layout,
        "settings": {"navigation": {"pageHeader": "enabled"}},
    },
}

status, text = call(f"{BASE}/v2/workbooks/spec", body)
print(status)
print(text[:4000])
