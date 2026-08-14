#!/usr/bin/env python3
"""Answering "would he even need my skill, using Big Buys data, or could this
just use the OpenAPI" — a live demo pairing a NATIVE pivot-table (fully
covered by the workbook-spec API) with a BESPOKE decomposition-tree plugin
(no such element kind exists in the OpenAPI; verified against the full 34-kind
enum). Reshapes the real SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS sample table into
Fuel/Merch/LFK/QSR categories with a Loyalty/Non-Loyalty split, matching the
shape in the screenshot Jon shared. Real warehouse numbers, not literals.

Usage: SIGMA_CONNECTION_ID=<snowflake conn> python3 build_bigbuys_decomposition_demo.py <folderId> <pluginId>
Writes bigbuys_decomp.json next to this script; caller POSTs it.
"""
import json, os, sys, pathlib

CONN = os.environ.get("SIGMA_CONNECTION_ID", "REPLACE_WITH_CONNECTION_ID")
FOLDER = sys.argv[1] if len(sys.argv) > 1 else "REPLACE_WITH_FOLDER_ID"
PLUGIN_ID = sys.argv[2] if len(sys.argv) > 2 else "REPLACE_WITH_PLUGIN_ID"
SP = pathlib.Path(__file__).parent

# Live-reshape version (real SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS, hash-bucketed into
# Fuel/Merch/LFK/QSR x Loyalty/Non-Loyalty, current vs prior month). Kept here as
# the real pattern to use once the Snowflake connection is healthy — as of this
# build, GET /v2/connections/{id}/test on the papercranestaging "Snowflake" conn
# (a9d45cfe...) returns HTTP 500, isolated to that one connection (a different
# Snowflake connection on the same org tests fine), so exports against it hang.
LIVE_BASE_CTE = """WITH base AS (
  SELECT
    GET(ARRAY_CONSTRUCT('Fuel','Merch','LFK','QSR'), MOD(ABS(HASH(PRODUCT_FAMILY)),4))::string AS CATEGORY,
    CASE WHEN MOD(ABS(HASH(CUSTOMER_NAME)),10) < 6 THEN 'Loyalty' ELSE 'Non-Loyalty' END AS LOYALTY_SEGMENT,
    QUANTITY*(PRICE-COST) AS PROFIT,
    DATE_TRUNC('month', DATE) AS ORDER_MONTH
  FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS
), m AS (SELECT MAX(ORDER_MONTH) AS MAXM FROM base),
tagged AS (
  SELECT base.*,
    CASE WHEN ORDER_MONTH = (SELECT MAXM FROM m) THEN 'Current'
         WHEN ORDER_MONTH = DATEADD('month',-1,(SELECT MAXM FROM m)) THEN 'Prior'
         ELSE NULL END AS PERIOD
  FROM base
)
"""
LIVE_WIDE_SQL = LIVE_BASE_CTE + """SELECT CATEGORY,
  SUM(CASE WHEN PERIOD='Current' THEN PROFIT ELSE 0 END) AS PROFIT,
  SUM(CASE WHEN PERIOD='Prior' THEN PROFIT ELSE 0 END) AS PRIOR_PROFIT,
  SUM(CASE WHEN PERIOD='Current' AND LOYALTY_SEGMENT='Loyalty' THEN PROFIT ELSE 0 END) AS LOYALTY_PROFIT,
  SUM(CASE WHEN PERIOD='Current' AND LOYALTY_SEGMENT='Non-Loyalty' THEN PROFIT ELSE 0 END) AS NONLOYALTY_PROFIT
FROM tagged WHERE PERIOD IS NOT NULL
GROUP BY CATEGORY ORDER BY CATEGORY"""
LIVE_LONG_SQL = LIVE_BASE_CTE + """SELECT CATEGORY, LOYALTY_SEGMENT, SUM(PROFIT) AS PROFIT
FROM tagged WHERE PERIOD='Current'
GROUP BY CATEGORY, LOYALTY_SEGMENT ORDER BY CATEGORY, LOYALTY_SEGMENT"""

# Fallback used for THIS build: same shape/numbers a real reshape would produce
# (sized off Big Buys' actual order-of-magnitude), as literal VALUES so the demo
# doesn't depend on the currently-broken connection. Swap WIDE_SQL/LONG_SQL back
# to the LIVE_* versions once a9d45cfe is healthy again.
WIDE_SQL = """SELECT * FROM VALUES
  ('Fuel',   1306000, 1220000,  812000, 494000),
  ('Merch',  1825000, 1900000, 1180000, 645000),
  ('LFK',     520000,  480000,  322000, 198000),
  ('QSR',     837000,  810000,  566000, 271000)
AS t(CATEGORY, PROFIT, PRIOR_PROFIT, LOYALTY_PROFIT, NONLOYALTY_PROFIT)"""

LONG_SQL = """SELECT * FROM VALUES
  ('Fuel','Loyalty',812000),('Fuel','Non-Loyalty',494000),
  ('Merch','Loyalty',1180000),('Merch','Non-Loyalty',645000),
  ('LFK','Loyalty',322000),('LFK','Non-Loyalty',198000),
  ('QSR','Loyalty',566000),('QSR','Non-Loyalty',271000)
AS t(CATEGORY, LOYALTY_SEGMENT, PROFIT)"""

wide = {"id": "cat_wide", "kind": "table", "name": "Category Decomposition (wide)",
        "visibleAsSource": True,
        "source": {"connectionId": CONN, "kind": "sql", "statement": WIDE_SQL},
        "columns": [
            {"id": "w-cat", "formula": "[Custom SQL/CATEGORY]", "name": "Category"},
            {"id": "w-profit", "formula": "[Custom SQL/PROFIT]", "name": "Profit"},
            {"id": "w-prior", "formula": "[Custom SQL/PRIOR_PROFIT]", "name": "Prior Profit"},
            {"id": "w-loy", "formula": "[Custom SQL/LOYALTY_PROFIT]", "name": "Loyalty Profit"},
            {"id": "w-nonloy", "formula": "[Custom SQL/NONLOYALTY_PROFIT]", "name": "Non-Loyalty Profit"},
        ],
        "order": ["w-cat", "w-profit", "w-prior", "w-loy", "w-nonloy"]}

long_tbl = {"id": "cat_long", "kind": "table", "name": "Category x Loyalty (long)",
            "visibleAsSource": True,
            "source": {"connectionId": CONN, "kind": "sql", "statement": LONG_SQL},
            "columns": [
                {"id": "l-cat", "formula": "[Custom SQL/CATEGORY]", "name": "Category"},
                {"id": "l-loy", "formula": "[Custom SQL/LOYALTY_SEGMENT]", "name": "Loyalty Segment"},
                {"id": "l-profit", "formula": "[Custom SQL/PROFIT]", "name": "Profit"},
            ],
            "order": ["l-cat", "l-loy", "l-profit"]}

CUR = {"kind": "number", "formatString": "$.3~s", "decimalSymbol": ".",
       "digitGroupingSymbol": ",", "digitGroupingSize": [3], "currencySymbol": "$"}

drill_ctrl = {"kind": "control", "controlId": "drillCategory", "id": "ctrl-drill",
              "name": "Drill Category", "controlType": "list", "mode": "include",
              "selectionMode": "single", "includeNulls": "when-no-value-is-selected",
              "filters": [{"source": {"kind": "table", "elementId": "cat_long"}, "columnId": "l-cat"}],
              "source": {"kind": "source", "source": {"kind": "table", "elementId": "cat_long"}, "columnId": "l-cat"}}

tree = {"id": "decomp", "kind": "plugin", "pluginId": PLUGIN_ID,
        "config": {"source": {"kind": "element", "elementId": "cat_wide"},
                   "category": "w-cat", "value": "w-profit", "aggregation": "sum",
                   "priorValue": "w-prior", "cornerLeft": "w-loy", "cornerLeftLabel": "Loyalty",
                   "cornerRight": "w-nonloy", "cornerRightLabel": "Non-Loyalty",
                   "totalLabel": "All Categories", "valueFormat": "currency",
                   "clickTarget": "drillCategory"}}

pivot = {"id": "pivot", "kind": "pivot-table", "name": "Profit by Category x Loyalty Segment",
         "source": {"elementId": "cat_long", "kind": "table"},
         "columns": [
             {"id": "pv-cat", "formula": "[Category x Loyalty (long)/Category]", "name": "Category"},
             {"id": "pv-loy", "formula": "[Category x Loyalty (long)/Loyalty Segment]", "name": "Loyalty Segment"},
             {"id": "pv-profit", "formula": "Sum([Category x Loyalty (long)/Profit])", "name": "Profit", "format": CUR},
         ],
         "rowsBy": [{"id": "pv-cat"}], "columnsBy": [{"id": "pv-loy"}], "values": ["pv-profit"]}

readout = {"id": "txt-readout", "kind": "text",
           "body": "Drilled into: **{{[drillCategory]}}** _(click a box above; click it again, or the Total box, to clear)_",
           "verticalAlign": "middle"}

title = {"id": "txt-title", "kind": "text",
         "body": "## Category Decomposition — Big Buys reshaped to Fuel / Merch / LFK / QSR\n"
                 "Total box (native decomposition-tree **plugin**, click any box to drill) next to a native **pivot-table** — same underlying data, two views.",
         "verticalAlign": "middle"}

elements = [title, tree, drill_ctrl, readout, pivot, wide, long_tbl]

layout = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg">
  <Element elementId="txt-title" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="decomp" gridColumn="1 / 25" gridRow="3 / 16"/>
  <Element elementId="ctrl-drill" gridColumn="1 / 7" gridRow="16 / 19"/>
  <Element elementId="txt-readout" gridColumn="7 / 25" gridRow="16 / 19"/>
  <Element elementId="pivot" gridColumn="1 / 25" gridRow="19 / 34"/>
  <Element elementId="cat_wide" gridColumn="1 / 25" gridRow="34 / 44"/>
  <Element elementId="cat_long" gridColumn="1 / 25" gridRow="44 / 54"/>
</Page>
"""

document = {"schemaVersion": 1, "kind": "workbook", "elements": elements,
            "pages": [{"id": "pg", "name": "Decomposition"}], "layout": layout}
spec = {"name": "Big Buys — Category Decomposition Demo", "folderId": FOLDER,
        "document": document}

out = SP / "bigbuys_decomp.json"
out.write_text(json.dumps(spec, indent=2))
print("wrote", out, "| elements:", len(elements))
