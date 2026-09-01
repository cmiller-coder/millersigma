#!/usr/bin/env python3
"""ClickHouse Cloud usage invoice -- pixel-perfect PDF report companion to
build_clickhouse_v2_command_center.py. Reuses build_statement.py's layout
code verbatim (page geometry, header/footer panels, page-1 band layout,
page-2 grouped activity table) but:
  * sources the three tables from CONN_CLICKHOUSE instead of
    S.CONN_SNOWFLAKE (build_statement.py's Custom SQL is already portable --
    _union() never wraps values in Snowflake-only CAST(...AS VARCHAR/NUMBER)
    types, unlike product_cards_sql()/notifications_sql()/geo_sql())
  * doesn't import sigmaapi (it's hardcoded to a different org --
    api.staging.sigmacomputing.io -- than sigma-psa/aws-api); prints the
    spec JSON on stdout instead, to be pushed with a direct curl call using
    .env.clickhouse credentials, same as every workbook build in this POV.

Usage:
    python3 build_clickhouse_statement.py > /tmp/statement_spec.json
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import brand as B          # noqa: E402
import company as CO        # noqa: E402

CFG = CO.COMPANIES["clickhouse"]
B.apply(CFG)
ST_ = lambda k: CO.statement(CFG, k)

CONN_CLICKHOUSE = "8d37c8d6-5516-48f3-9749-b2c81dcc944e"
FOLDER_ID = "4cbae364-629c-460b-b06d-4a2bfac7b31a"

PAGE_W, PAGE_H = 816, 1056        # US Letter portrait @ 96dpi
MARGIN = 30
HEADER_H, FOOTER_H = 104, 62
CW = PAGE_W - 2 * MARGIN          # 756 usable width

MONEY = {"kind": "number", "formatString": "$,.2f", "decimalSymbol": ".",
         "digitGroupingSymbol": ",", "digitGroupingSize": [3], "currencySymbol": "$"}
NUM0 = {"kind": "number", "formatString": ",.0f", "digitGroupingSymbol": ",",
        "digitGroupingSize": [3]}
DATE = {"kind": "datetime", "formatString": "%m/%d/%Y"}

ST = "Statement Activity"
ST_COLS = ["Transaction Date", "Post Date",
           "Merchant Name or Transaction Description", "Category", "Amount",
           "Points Earned"]

elements = []
rows = {"p1": [], "p2": [], "pdata": [], "global-header": [], "global-footer": []}


def add(el, where, x, y, w, h):
    elements.append(el)
    rows[where].append((el["id"], x, y, w, h))
    return el["id"]


def txt(eid, body, color=B.TEXT_DARK, align=None, valign=None):
    el = {"id": eid, "kind": "text", "body": body,
          "style": {"color": color, "backgroundColor": "transparent", "padding": "none"}}
    if align:
        el["align"] = align
    if valign:
        el["verticalAlign"] = valign
    return el


# ---------------------------------------------------------------- data source

add({"id": "src", "kind": "table", "name": ST,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql",
                "statement": CO.statement_activity_sql(CFG)},
     "columns": [{"id": "s%d" % i, "formula": "[Custom SQL/%s]" % n, "name": n}
                 for i, n in enumerate(ST_COLS)]},
    # Every element must be placed in layout, so data plumbing lives on a hidden page.
    "pdata", MARGIN, 0, CW, 400)


RW = "Rewards Summary"
AS_ = "Account Summary"

add({"id": "src-rw", "kind": "table", "name": RW,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql",
                "statement": CO.rewards_summary_sql(CFG)},
     "columns": [{"id": "rw0", "formula": "[Custom SQL/Line Order]", "name": "Line Order"},
                 {"id": "rw1", "formula": "[Custom SQL/Description]", "name": "Description"},
                 {"id": "rw2", "formula": "[Custom SQL/Points]", "name": "Points"}]},
    "pdata", MARGIN, 410, CW, 200)

add({"id": "src-as", "kind": "table", "name": AS_,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql",
                "statement": CO.account_summary_sql(CFG)},
     "columns": [{"id": "as0", "formula": "[Custom SQL/Line Order]", "name": "Line Order"},
                 {"id": "as1", "formula": "[Custom SQL/Metric]", "name": "Metric"},
                 {"id": "as2", "formula": "[Custom SQL/Value]", "name": "Value"}]},
    "pdata", MARGIN, 620, CW, 200)


# -------------------------------------------------------------- page furniture

# Header columns are laid out left-to-right from computed positions, not
# hardcoded offsets -- fixed offsets silently drift out of sync with column
# widths and overflow the page on the right.
H_GAP = 12
# service_phone here is an email address (support@clickhouse.com), longer
# than a phone number -- widened that column, taking the difference from the
# logo box (fit:contain scales by height, so a narrower box doesn't shrink
# the rendered logo) rather than manage-url (its label already nearly fills
# 230px and wraps to two lines below that).
H_COL_W = [160, 230, 190, 140]   # logo, manage-url, service, period
assert MARGIN + sum(H_COL_W) + H_GAP * (len(H_COL_W) - 1) <= PAGE_W - MARGIN, \
    "header columns overflow the page margin"
h_col_x = [MARGIN]
for w in H_COL_W[:-1]:
    h_col_x.append(h_col_x[-1] + w + H_GAP)

add({"id": "h-logo", "kind": "image",
     "source": {"kind": "url", "url": B.logo_navy()},
     # backgroundColor on an image element's style is rejected by the reports
     # API (masked behind a misleading "Invalid kind: image" error) -- omit it.
     "style": {"fit": "contain", "align": "start", "padding": "none"}},
    "global-header", h_col_x[0], 20, H_COL_W[0], 38)

add(txt("h-manage",
        "**Manage your account online at:**  \n" + ST_("manage_url"),
        B.TEXT_DARK),
    "global-header", h_col_x[1], 16, H_COL_W[1], 54)

add(txt("h-service",
        "**%s:**  \n%s" % (ST_("service_label"), ST_("service_phone")),
        B.TEXT_DARK),
    "global-header", h_col_x[2], 16, H_COL_W[2], 54)

add(txt("h-period",
        "**Statement period**  \n" + ST_("period"),
        B.TEXT_MUTED),
    "global-header", h_col_x[3], 16, H_COL_W[3], 58)

add({"id": "h-rule", "kind": "divider", "style": {"color": B.NAVY}},
    "global-header", MARGIN, 86, CW, 2)

add({"id": "f-rule", "kind": "divider", "style": {"color": B.BORDER}},
    "global-footer", MARGIN, 6, CW, 1)
add(txt("f-note", ST_("footer"), B.TEXT_MUTED),
    "global-footer", MARGIN, 14, CW, 44)


# ====================================================================== page 1

# ClickHouse's brand "primary" is a light yellow (#FCFF74, ~1.1:1 contrast on
# white -- fails WCAG even for large bold text) and "secondary" gold
# (#D9B400) only reaches ~2:1, still short of the 3:1 floor. Section captions
# use navy instead, unlike the other companies' statements which use their
# (much darker) brand primary for this same role.
SECT = '<span style="color: %s; font-size: 13px">**%%s**</span>' % B.NAVY
LBL = '<span style="color: %s; font-size: 11px">%%s</span>' % B.TEXT_MUTED
BIG = '<span style="color: %s; font-size: 27px">**%%s**</span>' % B.NAVY

MONEY0 = {"kind": "number", "formatString": "$,.0f", "currencySymbol": "$"}
_FMT = {"MONEY": MONEY, "MONEY0": MONEY0, "NUM0": NUM0}
_HF = ST_("h_formulas")

COL2_X = MARGIN + 396          # right column origin
COL_W = 360                    # right column width
LEFT_W = 366

# ---- top band: donut (left) | headline figures (middle) | usage (right)
add({"id": "p1-donut", "kind": "donut-chart",
     "source": {"elementId": "src", "kind": "table"},
     "columns": [
         {"id": "dn-c", "formula": "[%s/Category]" % ST, "name": "Category"},
         {"id": "dn-v", "formula": "Sum([%s/Amount])" % ST, "name": "Amount",
          "format": MONEY}],
     "value": {"id": "dn-v"},
     "color": {"id": "dn-c"},
     "name": {"visibility": "hidden"},
     "legend": {"visibility": "hidden"},
     "style": {"backgroundColor": "#FFFFFF", "padding": "none"}},
    "p1", MARGIN, 4, 178, 178)

hx = MARGIN + 190
add(txt("p1-l-bal", LBL % ST_("headline")[0][0], B.TEXT_MUTED), "p1", hx, 4, 190, 22)
add({"id": "p1-k-bal", "kind": "kpi-chart",
     "source": {"elementId": _HF[0][0], "kind": "table"},
     "columns": [{"id": "p1v-bal", "formula": _HF[0][1],
                  "name": ST_("headline")[0][0], "format": _FMT[_HF[0][2]]}],
     "value": {"columnId": "p1v-bal", "color": B.NAVY, "fontSize": 27},
     "name": {"visibility": "hidden"},
     "style": {"backgroundColor": "#FFFFFF", "padding": "none"},
     "layout": {"anchor": "start"}},
    "p1", hx, 22, 190, 40)

add(txt("p1-l-min", LBL % ST_("headline")[1][0], B.TEXT_MUTED), "p1", hx, 66, 190, 22)
add({"id": "p1-k-min", "kind": "kpi-chart",
     "source": {"elementId": _HF[1][0], "kind": "table"},
     "columns": [{"id": "p1v-min", "formula": _HF[1][1],
                  "name": ST_("headline")[1][0], "format": _FMT[_HF[1][2]]}],
     "value": {"columnId": "p1v-min", "color": B.NAVY, "fontSize": 27},
     "name": {"visibility": "hidden"},
     "style": {"backgroundColor": "#FFFFFF", "padding": "none"},
     "layout": {"anchor": "start"}},
    "p1", hx, 84, 190, 40)

add(txt("p1-l-due", LBL % ST_("headline")[2][0], B.TEXT_MUTED), "p1", hx, 128, 190, 22)
add(txt("p1-due", BIG % ST_("headline")[2][1], B.NAVY), "p1", hx, 146, 190, 40)

# ---- usage summary, right column
add(txt("p1-h-rw", SECT % ST_("sect_rewards")), "p1", COL2_X, 4, COL_W, 20)
add({"id": "p1-rw", "kind": "table",
     "source": {"elementId": "src-rw", "kind": "table"},
     "columns": [
         {"id": "rwd", "formula": "[%s/Description]" % RW, "name": "Description"},
         {"id": "rwp", "formula": "[%s/Points]" % RW, "name": "CHU-Hours", "format": NUM0}],
     "tableComponents": {"summaryBar": "hidden"},
     "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
     "name": {"visibility": "hidden"},
     "style": {"backgroundColor": "#FFFFFF", "borderColor": B.BORDER,
               "borderWidth": 1, "borderRadius": "round"}},
    "p1", COL2_X, 26, COL_W, 252)

add({"id": "p1-rw-rule", "kind": "divider", "style": {"color": B.NAVY}},
    "p1", COL2_X, 284, COL_W, 2)
add(txt("p1-rw-lbl",
        '<span style="color: %s; font-size: 13px">**%s**</span>'
        % (B.NAVY, ST_("rewards_total"))),
    "p1", COL2_X, 290, 200, 26)
add({"id": "p1-rw-tot", "kind": "kpi-chart",
     "source": {"elementId": "src-rw", "kind": "table"},
     "columns": [{"id": "rwt", "formula": "Sum([%s/Points])" % RW,
                  "name": "Total CHU-hours", "format": NUM0}],
     "value": {"columnId": "rwt", "color": B.NAVY, "fontSize": 20},
     "name": {"visibility": "hidden"},
     "style": {"backgroundColor": "#FFFFFF", "padding": "none"},
     "layout": {"anchor": "middle", "horizontalAlign": "end"}},
    "p1", COL2_X + 200, 288, COL_W - 200, 28)

y = 330
add({"id": "p1-rule1", "kind": "divider", "style": {"color": B.BORDER}},
    "p1", MARGIN, y, CW, 1)
y += 14

# ---- account summary (left) | spend chart (right)
add(txt("p1-h-as", SECT % ST_("sect_summary")), "p1", MARGIN, y, LEFT_W, 20)
add({"id": "p1-as", "kind": "table",
     "source": {"elementId": "src-as", "kind": "table"},
     "columns": [
         {"id": "asm", "formula": "[%s/Metric]" % AS_, "name": "Metric"},
         {"id": "asv", "formula": "[%s/Value]" % AS_, "name": "Value"}],
     "tableComponents": {"summaryBar": "hidden"},
     "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
     "name": {"visibility": "hidden"},
     "style": {"backgroundColor": "#FFFFFF", "borderColor": B.BORDER,
               "borderWidth": 1, "borderRadius": "round"}},
    "p1", MARGIN, y + 22, LEFT_W, 246)

add(txt("p1-h-cat", SECT % ST_("sect_category")), "p1", COL2_X, y, COL_W, 20)
add({"id": "p1-cat", "kind": "bar-chart",
     "source": {"elementId": "src", "kind": "table"},
     "columns": [
         {"id": "pc-cat", "formula": "[%s/Category]" % ST, "name": "Category "},
         {"id": "pc-x", "formula": "[%s/Category]" % ST, "name": "Category"},
         {"id": "pc-y", "formula": "Sum([%s/Amount])" % ST, "name": "Amount",
          "format": MONEY}],
     "yAxis": {"columnIds": ["pc-y"]},
     "xAxis": {"columnId": "pc-x", "sort": {"by": "pc-y", "direction": "descending"}},
     "color": {"by": "category", "column": "pc-cat", "scheme": B.CATEGORICAL},
     "name": {"visibility": "hidden"}, "legend": {"visibility": "hidden"},
     "style": {"backgroundColor": "#FFFFFF", "borderColor": B.BORDER,
               "borderWidth": 1, "borderRadius": "round"}},
    "p1", COL2_X, y + 22, COL_W, 246)
y += 284

add({"id": "p1-rule2", "kind": "divider", "style": {"color": B.BORDER}},
    "p1", MARGIN, y, CW, 1)
y += 14

# ---- the blocks a real invoice carries
add(txt("p1-h-msg", SECT % ST_("sect_messages")), "p1", MARGIN, y, CW, 20)
y += 24
add(txt("p1-msg", ST_("msg_body"), B.TEXT_DARK),
    "p1", MARGIN, y, CW, 68)
y += 76

add(txt("p1-warn1", ST_("warn1"), B.TEXT_DARK),
    "p1", MARGIN, y, LEFT_W, 100)
add(txt("p1-warn2", ST_("warn2"), B.TEXT_DARK),
    "p1", COL2_X, y, COL_W, 100)
y += 108

add(txt("p1-note",
        '<span style="color: %s">Continued on the next page — full usage detail '
        'for this billing period.</span>' % B.TEXT_MUTED),
    "p1", MARGIN, y, CW, 22)


# ====================================================================== page 2

y = 0
# An H1 needs more box than its font size or the glyphs clip and the next
# element sits on top of it.
add(txt("p2-h1", "# Usage activity", B.NAVY), "p2", MARGIN, y, CW, 54)
y += 62

add({"id": "p2-tbl", "kind": "table",
     "source": {"elementId": "src", "kind": "table"},
     "columns": [
         {"id": "t-date", "formula": "[%s/Transaction Date]" % ST,
          "name": "Date", "format": DATE},
         {"id": "t-merch", "formula": "[%s/Merchant Name or Transaction Description]" % ST,
          "name": "Usage Line Item"},
         {"id": "t-cat", "formula": "[%s/Category]" % ST, "name": "Category"},
         {"id": "t-amt", "formula": "[%s/Amount]" % ST, "name": "$ Amount",
          "format": MONEY},
         # group subtotals have to be their OWN aggregate columns -- listing the
         # row-level columns in `calculations` renders "multiple values"
         {"id": "t-pts-sum", "formula": "Sum([%s/Points Earned])" % ST,
          "name": "CHU-Hours", "format": NUM0},
         {"id": "t-amt-sum", "formula": "Sum([%s/Amount])" % ST,
          "name": "Total", "format": MONEY}],
     # Reads as a grouped LIST rather than a grid: usage lines collapse under
     # their spend category with a per-category subtotal, matching how a real
     # cloud usage invoice organizes activity.
     "groupings": [{"id": "t-catg", "groupBy": ["t-cat"],
                    "calculations": ["t-pts-sum", "t-amt-sum"],
                    "sort": [{"columnId": "t-amt-sum", "direction": "descending"}]}],
     "order": ["t-date", "t-merch", "t-amt"],
     "tableComponents": {"summaryBar": "hidden"},
     "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
     "name": {"visibility": "hidden"},
     "style": {"backgroundColor": "#FFFFFF", "borderColor": B.BORDER, "borderWidth": 1,
               "borderRadius": "round"}},
    "p2", MARGIN, y, CW, 700)
y += 712

add(txt("p2-note",
        "Every element, page dimension and margin on this invoice is declared in a "
        "report specification and created with `POST /v2/reports/spec` — nothing was "
        "placed by hand in the report builder.",
        B.TEXT_MUTED),
    "p2", MARGIN, y, CW, 54)


# =================================================================== assemble

def render_layout():
    out = ['<?xml version="1.0" encoding="utf-8"?>']
    for pid in ("p1", "p2", "pdata"):
        out.append('<Page id="%s">' % pid)
        for eid, x, yy, w, h in rows[pid]:
            out.append('  <Element elementId="%s" x="%s" y="%s" width="%s" height="%s"/>'
                       % (eid, x, yy, w, h))
        out.append("</Page>")
    for pid, ptype in (("global-header", "header"), ("global-footer", "footer")):
        out.append('<Panel id="%s" type="%s">' % (pid, ptype))
        for eid, x, yy, w, h in rows[pid]:
            out.append('  <Element elementId="%s" x="%s" y="%s" width="%s" height="%s"/>'
                       % (eid, x, yy, w, h))
        out.append("</Panel>")
    return "\n".join(out)


PAGES = [{"id": "p1", "name": ST_("page_name")},
         {"id": "p2", "name": "Usage Activity"},
         {"id": "pdata", "name": "Data", "visibility": "hidden"}]

DOCUMENT = {
    "schemaVersion": 1,
    "kind": "report",
    "elements": elements,
    "pages": PAGES,
    "panels": [
        {"id": "global-header", "type": "header", "title": "Invoice header",
         "config": {"height": HEADER_H, "backgroundColor": ""}, "pages": ["p1", "p2"]},
        {"id": "global-footer", "type": "footer", "title": "Invoice footer",
         "config": {"height": FOOTER_H, "backgroundColor": ""}, "pages": ["p1", "p2"]},
    ],
    "settings": {"theme": {"overrides": {
        "colors": {"text": B.TEXT_DARK, "highlight": B.SOFI_BRIGHT, "success": B.GOOD,
                   "warning": B.WARN, "danger": B.BAD, "darkMode": "hidden"},
        "colorOverrides": [],  # TEMP: live colorOverrides regression, see schema-2026-08-breaking-changes.md
        "categoricalScheme": B.CATEGORICAL,
        "space": {"unit": "small", "showElementPadding": "shown"},
    }}},
    "config": {"margin": MARGIN, "pageHeight": PAGE_H, "pageWidth": PAGE_W},
    "layout": render_layout(),
}

SPEC = {"name": ST_("spec_name"),
        "folderId": FOLDER_ID,
        "document": DOCUMENT}

if __name__ == "__main__":
    import json
    print(json.dumps(SPEC, indent=2))
