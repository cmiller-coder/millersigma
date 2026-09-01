"""Build a pixel-perfect SoFi member statement as a Sigma REPORT, from code.

The interactive workbook and this statement are generated from the same spec
harness and the same warehouse SQL — one is an app, one is a print deliverable.

Report specifics that differ from a workbook:
  * `document.kind` is "report"; page setup lives in `document.config`
    ({margin, pageHeight, pageWidth}) — 816x1056 is US Letter portrait at 96dpi.
  * Repeating furniture is `document.panels` (`header` / `footer`), each listing
    the page ids it applies to.
  * Layout is ABSOLUTE: `<Element x y width height/>` inside `<Page>`, with
    `<Panel>` blocks as siblings at the root of the layout XML.

Usage:  python3 build_statement.py [create|update <reportId>|dump]
"""

import json
import os
import pathlib
import sys

import brand as B
import company as CO
import sigmaapi as S

CFG = CO.COMPANIES[os.environ.get("COMPANY", "sofi")]
B.apply(CFG)
ST_ = lambda k: CO.statement(CFG, k)

SQL = pathlib.Path(__file__).resolve().parent.parent / "sql"
SPECS = pathlib.Path(__file__).resolve().parent.parent / "specs"
SPECS.mkdir(parents=True, exist_ok=True)

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
     "source": {"connectionId": S.CONN_SNOWFLAKE, "kind": "sql",
                "statement": (CO.statement_activity_sql(CFG)
                              or (SQL / "statement_activity.sql").read_text())},
     "columns": [{"id": "s%d" % i, "formula": "[Custom SQL/%s]" % n, "name": n}
                 for i, n in enumerate(ST_COLS)]},
    # Every element must be placed in layout, so data plumbing lives on a hidden page.
    "pdata", MARGIN, 0, CW, 400)


RW = "Rewards Summary"
AS_ = "Account Summary"

add({"id": "src-rw", "kind": "table", "name": RW,
     "source": {"connectionId": S.CONN_SNOWFLAKE, "kind": "sql",
                "statement": (CO.rewards_summary_sql(CFG)
                              or (SQL / "rewards_summary.sql").read_text())},
     "columns": [{"id": "rw0", "formula": "[Custom SQL/Line Order]", "name": "Line Order"},
                 {"id": "rw1", "formula": "[Custom SQL/Description]", "name": "Description"},
                 {"id": "rw2", "formula": "[Custom SQL/Points]", "name": "Points"}]},
    "pdata", MARGIN, 410, CW, 200)

add({"id": "src-as", "kind": "table", "name": AS_,
     "source": {"connectionId": S.CONN_SNOWFLAKE, "kind": "sql",
                "statement": (CO.account_summary_sql(CFG)
                              or (SQL / "account_summary.sql").read_text())},
     "columns": [{"id": "as0", "formula": "[Custom SQL/Line Order]", "name": "Line Order"},
                 {"id": "as1", "formula": "[Custom SQL/Metric]", "name": "Metric"},
                 {"id": "as2", "formula": "[Custom SQL/Value]", "name": "Value"}]},
    "pdata", MARGIN, 620, CW, 200)


# -------------------------------------------------------------- page furniture

# Header columns are laid out left-to-right from computed positions, not
# hardcoded offsets -- fixed offsets (previously +230/+470/+630) silently
# drift out of sync with column widths and overflow the page on the right.
H_GAP = 12
H_COL_W = [190, 230, 150, 150]   # logo, manage-url, member-service, period
assert MARGIN + sum(H_COL_W) + H_GAP * (len(H_COL_W) - 1) <= PAGE_W - MARGIN, \
    "header columns overflow the page margin"
h_col_x = [MARGIN]
for w in H_COL_W[:-1]:
    h_col_x.append(h_col_x[-1] + w + H_GAP)

add({"id": "h-logo", "kind": "image",
     "source": {"kind": "url", "url": B.logo_navy()},
     # "backgroundColor": "transparent" on an image element's style is rejected
     # by the reports API as of 2026-08-18 (masked behind a misleading
     # "Invalid kind: image" error) -- text elements still accept it fine, only
     # image does not. Omit it; the report canvas is already white.
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

add({"id": "h-rule", "kind": "divider", "style": {"color": B.SOFI_BRIGHT}},
    "global-header", MARGIN, 86, CW, 2)

add({"id": "f-rule", "kind": "divider", "style": {"color": B.BORDER}},
    "global-footer", MARGIN, 6, CW, 1)
add(txt("f-note", ST_("footer"), B.TEXT_MUTED),
    "global-footer", MARGIN, 14, CW, 44)


# ====================================================================== page 1
# Modelled on a real card statement: dense, two-column, banded tables, a chart
# carrying visual weight top-left, and the legal blocks a statement actually has.
# Headings are small blue caps (section markers), not big display type -- the
# numbers are what should be large.

SECT = '<span style="color: %s; font-size: 13px">**%%s**</span>' % B.SOFI_BRIGHT
LBL = '<span style="color: %s; font-size: 11px">%%s</span>' % B.TEXT_MUTED
BIG = '<span style="color: %s; font-size: 27px">**%%s**</span>' % B.NAVY

MONEY0 = {"kind": "number", "formatString": "$,.0f", "currencySymbol": "$"}
_FMT = {"MONEY": MONEY, "MONEY0": MONEY0, "NUM0": NUM0}
_HF = ST_("h_formulas")

COL2_X = MARGIN + 396          # right column origin
COL_W = 360                    # right column width
LEFT_W = 366

# ---- top band: donut (left) | headline figures (middle) | rewards (right)
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

# ---- rewards summary, right column
add(txt("p1-h-rw", SECT % ST_("sect_rewards")), "p1", COL2_X, 4, COL_W, 20)
add({"id": "p1-rw", "kind": "table",
     "source": {"elementId": "src-rw", "kind": "table"},
     "columns": [
         {"id": "rwd", "formula": "[%s/Description]" % RW, "name": "Description"},
         {"id": "rwp", "formula": "[%s/Points]" % RW, "name": "Points", "format": NUM0}],
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
                  "name": "Total points", "format": NUM0}],
     "value": {"columnId": "rwt", "color": B.SOFI_BRIGHT, "fontSize": 20},
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

# ---- the blocks a real statement carries
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
        '<span style="color: %s">Continued on the next page — full transaction '
        'detail for this statement period.</span>' % B.TEXT_MUTED),
    "p1", MARGIN, y, CW, 22)


# ====================================================================== page 2

y = 0
# An H1 needs more box than its font size or the glyphs clip and the next
# element sits on top of it -- 34px was cropping the descenders and colliding
# with the table's top border.
add(txt("p2-h1", CO.STATEMENTS.get(CFG["key"], {}).get("page2_title", "# Account activity"),
        B.NAVY), "p2", MARGIN, y, CW, 54)
y += 62

add({"id": "p2-tbl", "kind": "table",
     "source": {"elementId": "src", "kind": "table"},
     "columns": [
         {"id": "t-date", "formula": "[%s/Transaction Date]" % ST,
          "name": "Date of Transaction", "format": DATE},
         {"id": "t-merch", "formula": "[%s/Merchant Name or Transaction Description]" % ST,
          "name": "Merchant Name or Transaction Description"},
         {"id": "t-cat", "formula": "[%s/Category]" % ST, "name": "Category"},
         {"id": "t-amt", "formula": "[%s/Amount]" % ST, "name": "$ Amount",
          "format": MONEY},
         # group subtotals have to be their OWN aggregate columns -- listing the
         # row-level columns in `calculations` renders "multiple values"
         {"id": "t-pts-sum", "formula": "Sum([%s/Points Earned])" % ST,
          "name": "Points", "format": NUM0},
         {"id": "t-amt-sum", "formula": "Sum([%s/Amount])" % ST,
          "name": "Total", "format": MONEY}],
     # Reads as a grouped LIST rather than a grid: transactions collapse under
     # their spend category with a per-category subtotal, which is how a real
     # card statement organises activity.
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
        "Every element, page dimension and margin on this statement is declared in a "
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
         {"id": "p2", "name": "Account Activity"},
         {"id": "pdata", "name": "Data", "visibility": "hidden"}]

DOCUMENT = {
    "schemaVersion": 1,
    "kind": "report",
    "elements": elements,
    "pages": PAGES,
    "panels": [
        {"id": "global-header", "type": "header", "title": "Statement header",
         "config": {"height": HEADER_H, "backgroundColor": ""}, "pages": ["p1", "p2"]},
        {"id": "global-footer", "type": "footer", "title": "Statement footer",
         "config": {"height": FOOTER_H, "backgroundColor": ""}, "pages": ["p1", "p2"]},
    ],
    "settings": {"theme": {"overrides": {
        "colors": {"text": B.TEXT_DARK, "highlight": B.SOFI_BRIGHT, "success": B.GOOD,
                   "warning": B.WARN, "danger": B.BAD, "darkMode": "hidden"},
        "colorOverrides": {"backgroundCanvas": "#FFFFFF"},
        "categoricalScheme": B.CATEGORICAL,
        "space": {"unit": "small", "showElementPadding": "shown"},
    }}},
    "config": {"margin": MARGIN, "pageHeight": PAGE_H, "pageWidth": PAGE_W},
    "layout": render_layout(),
}

SPEC = {"name": ST_("spec_name"),
        "folderId": S.FOLDER_CLAUDE_BUILDER,
        "document": DOCUMENT}


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "dump"
    if action == "dump":
        print(DOCUMENT["layout"])
        print("\nelements:", len(elements))
        return
    try:
        if action == "create":
            r = S.create_report(SPEC)
            rid = r.get("reportId")
            print("✅ created report", rid)
            (SPECS / ("report_id_%s.txt" % CFG["key"])).write_text(rid or "")
        elif action == "update":
            S.update_report(sys.argv[2], SPEC)
            print("✅ updated", sys.argv[2])
    except S.SigmaError as exc:
        msg = exc.body
        try:
            msg = json.loads(exc.body).get("message", msg)
        except ValueError:
            pass
        print("❌ %s failed:\n%s" % (action, msg[:2500]))


if __name__ == "__main__":
    main()
