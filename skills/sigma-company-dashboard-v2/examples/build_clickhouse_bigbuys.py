#!/usr/bin/env python3
"""
build_clickhouse_bigbuys.py — standalone one-off builder for the ClickHouse
POV (sigma-psa org, aws-api host). NOT part of the company.py/build_sofi.py
config-driven flow: this workbook binds directly to a real, already-connected
ClickHouse Cloud warehouse table (BigBuys retail POS data) instead of
generating synthetic SQL, which company.py/build_sofi.py have no support for
(see examples/README.md's "closer to what these demonstrate" carve-out).

Read-only dashboard: no write-back, no scenario modeler/cohort page.

Usage:
    python3 build_clickhouse_bigbuys.py > /tmp/clickhouse_spec.json
    # then POST via scripts/api/publish-workbook.sh post <file>  (or PUT to update)
"""
import json
import base64

CONN_CLICKHOUSE = "8d37c8d6-5516-48f3-9749-b2c81dcc944e"
TABLE_PATH = ["default", "retail__big_buys__big_buys_pos"]
FOLDER_ID = "4cbae364-629c-460b-b06d-4a2bfac7b31a"  # Connor's My Documents
PLUGIN_PULSE_ID = "86c8c5b8-9090-4ee6-b1b6-9fa3f2335712"  # ClickHouse Regional Pulse

# ---- Aurora Glass theme tokens + ClickHouse brand accent ------------------
CANVAS = "#080B1E"
CARD = "#14193B"
BORDER = "#353B68"
TEXT = "#F5F7FF"
TEXT_MUTED = "#AAB1D2"
YELLOW = "#FCFF74"   # sampled from clickhouse.com's real brand mark
BLUE = "#40D7FF"
PINK = "#FF72D0"
GREEN = "#4DE2AE"
CATEGORICAL = [YELLOW, BLUE, PINK, GREEN, "#8B7CFF"]

with open("/private/tmp/claude-502/-Users-cmiller-Desktop/6126914d-201c-47e5-889b-0205b8bd1c58/scratchpad/header_gradient_uri.txt") as f:
    HEADER_GRADIENT_URI = f.read().strip()
with open("/private/tmp/claude-502/-Users-cmiller-Desktop/6126914d-201c-47e5-889b-0205b8bd1c58/scratchpad/logo_uri.txt") as f:
    LOGO_URI = f.read().strip()

elements = []
def add(e):
    elements.append(e)

def text(eid, body, valign=None):
    # `text` elements have no `style` field (verified against the OpenAPI) —
    # color/size must be inline markdown/HTML in `body` itself.
    e = {"id": eid, "kind": "text", "body": body}
    if valign:
        e["verticalAlign"] = valign
    return e

NUM0 = {"kind": "number", "formatString": ",.0f"}
USD0 = {"kind": "number", "formatString": "$,.0f"}
PCT1 = {"kind": "number", "formatString": ".1%"}

# ---------------------------------------------------------------------------
# Base table (hidden Data page) — the ONE physical source everything filters
# through. Raw pass-through columns bind to the live ClickHouse table;
# derived columns (Revenue/COGS/Margin/Month) are formulas over siblings.
# ---------------------------------------------------------------------------
RAW = [
    ("col-order-number", "Order Number"),
    ("col-date", "Date"),
    ("col-quantity", "Quantity"),
    ("col-price", "Price"),
    ("col-cost", "Cost"),
    ("col-product-family", "Product Family"),
    ("col-product-type", "Product Type"),
    ("col-brand", "Brand"),
    ("col-store-name", "Store Name"),
    ("col-store-key", "Store Key"),
    ("col-store-region", "Store Region"),
    ("col-store-state", "Store State"),
]
base_cols = [{"id": cid, "formula": "[retail__big_buys__big_buys_pos/%s]" % disp}
             for cid, disp in RAW]
base_cols += [
    {"id": "col-revenue", "formula": "[Price] * [Quantity]", "name": "Revenue"},
    {"id": "col-cogs", "formula": "[Cost] * [Quantity]", "name": "COGS"},
    {"id": "col-margin", "formula": "[Revenue] - [COGS]", "name": "Margin"},
    {"id": "col-margin-pct", "formula": 'If([Revenue] = 0, 0, [Margin] / [Revenue])', "name": "Margin %"},
    {"id": "col-month", "formula": 'DateTrunc("month", [Date])', "name": "Month"},
]
add({"id": "tbl-bigbuys", "kind": "table", "name": "BigBuys Retail Detail",
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "warehouse-table", "path": TABLE_PATH},
     "columns": base_cols,
     "style": {"backgroundColor": CANVAS}})

SRC = "BigBuys Retail Detail"  # cross-element formula prefix (base table's `name`)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
add({"id": "c-header", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": "#0B0B26"},
     "backgroundImage": {"source": {"kind": "url", "url": HEADER_GRADIENT_URI}, "style": {"fit": "cover"}}})
add({"id": "wm-icon", "kind": "image", "source": {"kind": "url", "url": LOGO_URI},
     "style": {"fit": "contain"}})
add(text("wm-word", '**<span style="font-size: 22px; color: %s">ClickHouse</span>**' % TEXT,
         valign="middle"))
add(text("eyebrow", '<span style="font-size: 11px; color: %s">CLICKHOUSE &middot; REAL-TIME ANALYTICS FOR BIGBUYS RETAIL</span>' % YELLOW,
         valign="end"))
add(text("title", '# **<span style="color: %s">Command Center</span>**' % TEXT,
         valign="middle"))
add(text("subtitle", '<span style="font-size: 13px; color: %s">Live BigBuys point-of-sale data, queried straight out of ClickHouse Cloud.</span>' % TEXT_MUTED,
         valign="start"))

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
add({"kind": "control", "id": "ctrl-region", "controlId": "StoreRegion", "name": "Store Region",
     "controlType": "list", "mode": "include", "selectionMode": "multiple", "values": [],
     "filters": [{"source": {"kind": "table", "elementId": "tbl-bigbuys"}, "columnId": "col-store-region"}],
     "source": {"kind": "source", "source": {"kind": "table", "elementId": "tbl-bigbuys"}, "columnId": "col-store-region"}})
add({"kind": "control", "id": "ctrl-family", "controlId": "ProductFamily", "name": "Product Family",
     "controlType": "list", "mode": "include", "selectionMode": "multiple", "values": [],
     "filters": [{"source": {"kind": "table", "elementId": "tbl-bigbuys"}, "columnId": "col-product-family"}],
     "source": {"kind": "source", "source": {"kind": "table", "elementId": "tbl-bigbuys"}, "columnId": "col-product-family"}})
add({"kind": "control", "id": "ctrl-date", "controlId": "DateRange", "name": "Date",
     "controlType": "date-range", "mode": "between", "includeNulls": "when-no-value-is-selected",
     "filters": [{"source": {"kind": "table", "elementId": "tbl-bigbuys"}, "columnId": "col-date"}]})

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
def kpi(eid, name, formula, fmt=USD0):
    add({"id": eid, "kind": "kpi-chart", "name": name,
         "source": {"kind": "table", "elementId": "tbl-bigbuys"},
         "columns": [{"id": eid + "-value", "name": name, "formula": formula, "format": fmt}],
         "value": {"columnId": eid + "-value"},
         "style": {"backgroundColor": CARD}})

kpi("kpi-revenue", "Total Revenue", "Sum([%s/Revenue])" % SRC, USD0)
kpi("kpi-orders", "Orders", "CountDistinct([%s/Order Number])" % SRC, NUM0)
kpi("kpi-stores", "Active Stores", "CountDistinct([%s/Store Key])" % SRC, NUM0)
kpi("kpi-aov", "Avg Order Value",
    "Sum([%s/Revenue]) / CountDistinct([%s/Order Number])" % (SRC, SRC), USD0)

# ---------------------------------------------------------------------------
# Bespoke plugin — ClickHouse Regional Pulse
# ---------------------------------------------------------------------------
add({"id": "plg-pulse", "kind": "plugin", "pluginId": PLUGIN_PULSE_ID,
     "displayName": "Regional Pulse",
     "config": {"source": {"kind": "element", "elementId": "tbl-bigbuys"},
                "category": "col-store-region", "size": "col-revenue",
                "velocity": "col-quantity", "colorMetric": "col-margin-pct"},
     "style": {"backgroundColor": CARD}})

# ---------------------------------------------------------------------------
# Monthly revenue trend
# ---------------------------------------------------------------------------
add({"id": "ch-trend", "kind": "line-chart", "name": "Monthly Revenue Trend",
     "source": {"kind": "table", "elementId": "tbl-bigbuys"},
     "columns": [
         {"id": "tt-month", "formula": "[%s/Month]" % SRC, "name": "Month"},
         {"id": "tt-revenue", "formula": "Sum([%s/Revenue])" % SRC, "name": "Revenue", "format": USD0}],
     "xAxis": {"columnId": "tt-month", "sort": {"direction": "ascending"}},
     "yAxis": {"columnIds": ["tt-revenue"]},
     "legend": {"visibility": "hidden"},
     "style": {"backgroundColor": CARD}})

# ---------------------------------------------------------------------------
# Revenue by product family
# ---------------------------------------------------------------------------
add({"id": "ch-family", "kind": "bar-chart", "name": "Revenue by Product Family",
     "source": {"kind": "table", "elementId": "tbl-bigbuys"},
     "columns": [
         {"id": "bf-family", "formula": "[%s/Product Family]" % SRC, "name": "Product Family"},
         {"id": "bf-revenue", "formula": "Sum([%s/Revenue])" % SRC, "name": "Revenue", "format": USD0}],
     "xAxis": {"columnId": "bf-family", "sort": {"direction": "descending", "columnId": "bf-revenue"}},
     "yAxis": {"columnIds": ["bf-revenue"]},
     "orientation": "horizontal",
     "legend": {"visibility": "hidden"},
     "style": {"backgroundColor": CARD}})

# ---------------------------------------------------------------------------
# Detail table — grouped by region / store
# ---------------------------------------------------------------------------
add({"id": "tbl-detail", "kind": "table", "name": "Store Detail",
     "source": {"kind": "table", "elementId": "tbl-bigbuys"},
     "columns": [
         {"id": "dt-region", "formula": "[%s/Store Region]" % SRC, "name": "Region"},
         {"id": "dt-store", "formula": "[%s/Store Name]" % SRC, "name": "Store"},
         {"id": "dt-revenue", "formula": "Sum([%s/Revenue])" % SRC, "name": "Revenue", "format": USD0},
         {"id": "dt-orders", "formula": "CountDistinct([%s/Order Number])" % SRC, "name": "Orders", "format": NUM0},
         {"id": "dt-margin-pct", "formula": "Avg([%s/Margin %%])" % SRC, "name": "Margin %", "format": PCT1},
     ],
     "groupings": [{"id": "grp-store", "groupBy": ["dt-region", "dt-store"],
                    "calculations": ["dt-revenue", "dt-orders", "dt-margin-pct"],
                    "sort": [{"columnId": "dt-revenue", "direction": "descending"}]}],
     "style": {"backgroundColor": CARD}})

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
# tbl-bigbuys is placed on the SAME page as the plugin (not a hidden Data
# page): plugin `useElementData` is a live client-side subscription scoped to
# the rendered page, unlike formula-based elements (kpi/chart/table), which
# resolve cross-page via the backend query engine regardless of page
# visibility. A hidden-page source table left the plugin with no live feed.
COMMAND_LAYOUT = """<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-command">
  <Container elementId="c-header" type="grid" gridColumn="1 / 25" gridRow="1 / 8"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="wm-icon" gridColumn="1 / 2" gridRow="1 / 3"/>
    <Element elementId="wm-word" gridColumn="2 / 6" gridRow="1 / 3"/>
    <Element elementId="eyebrow" gridColumn="18 / 25" gridRow="1 / 2"/>
    <Element elementId="title" gridColumn="1 / 13" gridRow="3 / 5"/>
    <Element elementId="subtitle" gridColumn="1 / 18" gridRow="5 / 6"/>
  </Container>
  <Element elementId="ctrl-region" gridColumn="1 / 9" gridRow="9 / 13"/>
  <Element elementId="ctrl-family" gridColumn="9 / 17" gridRow="9 / 13"/>
  <Element elementId="ctrl-date" gridColumn="17 / 25" gridRow="9 / 13"/>
  <Element elementId="kpi-revenue" gridColumn="1 / 7" gridRow="14 / 21"/>
  <Element elementId="kpi-orders" gridColumn="7 / 13" gridRow="14 / 21"/>
  <Element elementId="kpi-stores" gridColumn="13 / 19" gridRow="14 / 21"/>
  <Element elementId="kpi-aov" gridColumn="19 / 25" gridRow="14 / 21"/>
  <Element elementId="plg-pulse" gridColumn="1 / 13" gridRow="22 / 40"/>
  <Element elementId="ch-trend" gridColumn="13 / 25" gridRow="22 / 40"/>
  <Element elementId="ch-family" gridColumn="1 / 13" gridRow="41 / 59"/>
  <Element elementId="tbl-detail" gridColumn="13 / 25" gridRow="41 / 59"/>
  <Element elementId="tbl-bigbuys" gridColumn="1 / 25" gridRow="60 / 61"/>
</Page>"""

LAYOUT = '<?xml version="1.0" encoding="utf-8"?>\n' + COMMAND_LAYOUT

spec = {
    "name": "ClickHouse — BigBuys Real-Time Retail Analytics",
    "folderId": FOLDER_ID,
    "document": {
        "schemaVersion": 1,
        "kind": "workbook",
        "elements": elements,
        "pages": [
            {"id": "page-command", "name": "Command Center", "backgroundColor": CANVAS},
        ],
        "layout": LAYOUT,
        "settings": {
            "theme": {
                "name": "Dark",
                "overrides": {
                    "categoricalScheme": CATEGORICAL,
                    "colors": {"text": TEXT, "highlight": YELLOW, "surface": CARD},
                },
            }
        },
    },
}

print(json.dumps(spec, indent=2))
