#!/usr/bin/env python3
"""Same Big Buys decomposition demo, but using the REAL, already-registered
"Metric Decomposition Tree" plugin (aminettosigma/sigma-decomposition-tree,
hosted at sigma-decomposition-tree.netlify.app) instead of a from-scratch
clone. That plugin aggregates each bound column ACROSS ALL ROWS of its
source (no group-by), so per-category boxes need a WIDE, single-row table
with one column per category/metric combo, not one row per category.

The plugin's own "config" field stores the full tree (Total -> 4 category
children) as JSON, authored here directly rather than through its in-app
Edit-mode UI. selectVar (a text control) is bound so clicking a box drills
the paired pivot table.

Usage: SIGMA_CONNECTION_ID=<conn> python3 build_bigbuys_decomposition_real_plugin.py <folderId> <pluginId>
"""
import json, os, sys, pathlib

CONN = os.environ.get("SIGMA_CONNECTION_ID", "REPLACE_WITH_CONNECTION_ID")
FOLDER = sys.argv[1] if len(sys.argv) > 1 else "REPLACE_WITH_FOLDER_ID"
PLUGIN_ID = sys.argv[2] if len(sys.argv) > 2 else "REPLACE_WITH_PLUGIN_ID"
SP = pathlib.Path(__file__).parent

CATS = ["fuel", "merch", "lfk", "qsr"]
LABELS = {"fuel": "Fuel", "merch": "Merch", "lfk": "LFK", "qsr": "QSR"}
# (profit, prior_profit, loyalty_profit, nonloyalty_profit) — same numbers as
# the earlier build, sized off Big Buys' real order-of-magnitude.
VALUES = {
    "fuel":  (1306000, 1220000, 812000, 494000),
    "merch": (1825000, 1900000, 1180000, 645000),
    "lfk":   (520000,  480000,  322000, 198000),
    "qsr":   (837000,  810000,  566000, 271000),
}
TOTAL_PROFIT = sum(v[0] for v in VALUES.values())
TOTAL_PRIOR = sum(v[1] for v in VALUES.values())

# ---- single-row wide table: one column per category x metric ----
select_parts = [f"{TOTAL_PROFIT} AS TOTAL_PROFIT", f"{TOTAL_PRIOR} AS TOTAL_PRIOR"]
for c in CATS:
    p, pr, loy, nonloy = VALUES[c]
    select_parts += [f"{p} AS {c.upper()}_PROFIT", f"{pr} AS {c.upper()}_PRIOR",
                      f"{loy} AS {c.upper()}_LOY", f"{nonloy} AS {c.upper()}_NONLOY"]
WIDE_SQL = "SELECT " + ", ".join(select_parts)

wide_cols = [("w-total-profit", "TOTAL_PROFIT", "Total Profit"), ("w-total-prior", "TOTAL_PRIOR", "Total Prior")]
for c in CATS:
    wide_cols += [
        (f"w-{c}-profit", f"{c.upper()}_PROFIT", f"{LABELS[c]} Profit"),
        (f"w-{c}-prior", f"{c.upper()}_PRIOR", f"{LABELS[c]} Prior"),
        (f"w-{c}-loy", f"{c.upper()}_LOY", f"{LABELS[c]} Loyalty"),
        (f"w-{c}-nonloy", f"{c.upper()}_NONLOY", f"{LABELS[c]} Non-Loyalty"),
    ]
wide = {"id": "wide_row", "kind": "table", "name": "Category Totals (single row)",
        "visibleAsSource": True,
        "source": {"connectionId": CONN, "kind": "sql", "statement": WIDE_SQL},
        "columns": [{"id": cid, "formula": f"[Custom SQL/{sqlcol}]", "name": name} for cid, sqlcol, name in wide_cols],
        "order": [c[0] for c in wide_cols]}

# ---- long table, unchanged, for the paired native pivot-table ----
LONG_SQL = """SELECT * FROM VALUES
  ('Fuel','Loyalty',812000),('Fuel','Non-Loyalty',494000),
  ('Merch','Loyalty',1180000),('Merch','Non-Loyalty',645000),
  ('LFK','Loyalty',322000),('LFK','Non-Loyalty',198000),
  ('QSR','Loyalty',566000),('QSR','Non-Loyalty',271000)
AS t(CATEGORY, LOYALTY_SEGMENT, PROFIT)"""
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
              "name": "Drill Category", "controlType": "text", "mode": "equals",
              "case": "insensitive", "includeNulls": "when-no-value-is-selected",
              "showOperators": False,
              "filters": [{"source": {"kind": "table", "elementId": "cat_long"}, "columnId": "l-cat"}]}

CUR_FMT = {"type": "compact", "decimals": 1, "prefix": "$", "suffix": ""}
PCT_FMT = {"type": "percent", "decimals": 1, "prefix": "", "suffix": ""}


def box(node_id, title, profit_col, prior_col, loy_col=None, nonloy_col=None, children=None):
    n = {
        "id": node_id, "title": title,
        "valueCol": profit_col, "valueAgg": "sum", "valueFmt": CUR_FMT,
        "varMode": "pct", "varianceCol": "", "varianceAgg": "avg",
        "comparisonCol": prior_col, "comparisonAgg": "sum",
        "varFmt": PCT_FMT, "higherIsBetter": True,
        "c1Label": "Loyalty" if loy_col else "", "c1Col": loy_col or "", "c1Agg": "sum", "c1Fmt": CUR_FMT,
        "c2Label": "Non-Loyalty" if nonloy_col else "", "c2Col": nonloy_col or "", "c2Agg": "sum", "c2Fmt": CUR_FMT,
        "selectValue": title, "children": children or [],
    }
    return n


children = [box(c, LABELS[c], f"w-{c}-profit", f"w-{c}-prior", f"w-{c}-loy", f"w-{c}-nonloy") for c in CATS]
root = box("total", "Total", "w-total-profit", "w-total-prior", children=children)
root["selectValue"] = ""  # clicking Total clears the selection, matches the plugin's own breadcrumb "root" convention
TREE_CONFIG = {"version": 1, "scaleToFit": True, "roots": [root]}

all_col_ids = [c[0] for c in wide_cols]
tree = {"id": "decomp", "kind": "plugin", "pluginId": PLUGIN_ID,
        "config": {"source": {"kind": "element", "elementId": "wide_row"},
                   "columns": all_col_ids,
                   "config": json.dumps(TREE_CONFIG),
                   "selectVar": "drillCategory"}}

readout = {"id": "txt-readout", "kind": "text",
           "body": "Drilled into: **{{[drillCategory]}}** _(click a box above; click Total, or its breadcrumb, to clear)_",
           "verticalAlign": "middle"}

title = {"id": "txt-title", "kind": "text",
         "body": "## Category Decomposition — Big Buys reshaped to Fuel / Merch / LFK / QSR\n"
                 "Total box (the **real, already-registered** Metric Decomposition Tree plugin) next to a native **pivot-table** — same underlying data, two views.",
         "verticalAlign": "middle"}

pivot = {"id": "pivot", "kind": "pivot-table", "name": "Profit by Category x Loyalty Segment",
         "source": {"elementId": "cat_long", "kind": "table"},
         "columns": [
             {"id": "pv-cat", "formula": "[Category x Loyalty (long)/Category]", "name": "Category"},
             {"id": "pv-loy", "formula": "[Category x Loyalty (long)/Loyalty Segment]", "name": "Loyalty Segment"},
             {"id": "pv-profit", "formula": "Sum([Category x Loyalty (long)/Profit])", "name": "Profit", "format": CUR},
         ],
         "rowsBy": [{"id": "pv-cat"}], "columnsBy": [{"id": "pv-loy"}], "values": ["pv-profit"]}

elements = [title, tree, drill_ctrl, readout, pivot, wide, long_tbl]

layout = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg">
  <Element elementId="txt-title" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="decomp" gridColumn="1 / 25" gridRow="3 / 18"/>
  <Element elementId="ctrl-drill" gridColumn="1 / 7" gridRow="18 / 21"/>
  <Element elementId="txt-readout" gridColumn="7 / 25" gridRow="18 / 21"/>
  <Element elementId="pivot" gridColumn="1 / 25" gridRow="21 / 36"/>
  <Element elementId="wide_row" gridColumn="1 / 25" gridRow="36 / 44"/>
  <Element elementId="cat_long" gridColumn="1 / 25" gridRow="44 / 54"/>
</Page>
"""

document = {"schemaVersion": 1, "kind": "workbook", "elements": elements,
            "pages": [{"id": "pg", "name": "Decomposition"}], "layout": layout}
spec = {"name": "Big Buys - Category Decomposition (real plugin)", "folderId": FOLDER, "document": document}

out = SP / "bigbuys_decomp_realplugin.json"
out.write_text(json.dumps(spec, indent=2))
print("wrote", out, "| elements:", len(elements))
