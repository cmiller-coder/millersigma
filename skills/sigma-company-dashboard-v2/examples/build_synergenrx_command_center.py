#!/usr/bin/env python3
"""SynergenRx Command Center -- LIGHTWEIGHT build.

Runs through company.py's real config/calibration path (CFG["products"]/
["alerts"], product_cards_sql, notifications_sql) exactly like the
ClickHouse v2 build, but deliberately smaller: single dashboard page, no
map/geo, no bespoke plugin, no AI-insight CallText, no chat agent, no
product-card modal/drill-through. Just header, KPI row, live alerts,
therapy-line cards, and one chart.

Targets the sigma-psa org's Databricks "PSE Serverless" connection (no
Snowflake on this org) -- product_cards_sql()/notifications_sql() emit
Snowflake-dialect CAST(...AS VARCHAR/NUMBER), so db_types() shims those to
Databricks SQL (STRING/DECIMAL/DOUBLE) the same way ch_types() did for
ClickHouse. The product x month revenue grid is computed in pure Python and
emitted as literal SELECT/UNION ALL rows -- no vendor SQL functions needed.

Usage:
    python3 build_synergenrx_command_center.py > /tmp/spec.json
"""
import json
import math
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import brand as B          # noqa: E402
import company as CO        # noqa: E402

CFG = CO.COMPANIES["synergenrx"]
B.apply(CFG)

CONN_DB = "21868d1e-38c7-4847-9992-f31ba060478e"  # PSE Serverless (Databricks)
FOLDER_ID = "4cbae364-629c-460b-b06d-4a2bfac7b31a"

LB = CFG["base_table"]           # "Dispensing Book"
PC = "Therapy Line Cards"
NT = "Notifications"
PRODUCT_NAMES = ", ".join(p[0] for p in CFG["products"])

MONEY_M = {"kind": "number", "formatString": "$,.1f", "currencySymbol": "$"}
PCT1 = {"kind": "number", "formatString": ".1%"}
NUM0 = {"kind": "number", "formatString": ",.0f"}

elements, overlays, agents = [], [], []


def add(el):
    elements.append(el)
    return el["id"]


def panel():
    return {"backgroundColor": B.CARD, "borderRadius": "round",
            "borderColor": B.BORDER, "borderWidth": 1}


def db_types(sql_text):
    """Shim company.py's Snowflake-dialect SQL to Databricks SQL. Every
    literal-value generator (product_cards_sql, notifications_sql) wraps its
    output in CAST(...AS VARCHAR/NUMBER(a,b)) -- neither type name exists in
    Databricks SQL (STRING/DECIMAL instead). It also aliases columns with
    double quotes (AS "Product") -- Spark SQL's default (non-ANSI) dialect
    parses a double-quoted alias as a STRING LITERAL, not an identifier,
    which is a syntax error in that position ("Syntax error at or near
    '[REDACTED]'" -- confirmed live, position landed exactly on the opening
    quote). Databricks identifiers are backtick-quoted instead. Generation
    logic is pure Python string formatting, not SQL, so these are the only
    changes needed."""
    sql_text = re.sub(r"\bVARCHAR\b", "STRING", sql_text)
    sql_text = re.sub(r"\bNUMBER\((\d+),\s*(\d+)\)", r"DECIMAL(\1,\2)", sql_text)
    sql_text = re.sub(r'AS "([^"]+)"', r"AS `\1`", sql_text)
    sql_text = re.sub(r"\bNUMBER\b", "DOUBLE", sql_text)
    return sql_text


# ---------------------------------------------------------------------------
# Patient x month dispensing grid, computed in pure Python (same technique
# as the ClickHouse v2 build) and emitted as literal rows -- portable to any
# SQL dialect with no vendor-specific function needed. bal_base per therapy
# line is back-solved so month 12-23 sums hit the real annual $M target
# exactly (see _ANNUAL_TARGETS below).
# ---------------------------------------------------------------------------
def _patients(month_idx):
    return 500.0 * (1850.0 / 500.0) ** (month_idx / 23.0)


def build_revenue_rows():
    rows = []
    for p in CFG["products"]:
        name, order, _btype, bal_base, margin, _fund, _fee, _prov, _delinq, \
            _opex, growth, _units, phase = p[:13]
        for m in range(24):
            trend = (1 + growth / 12) ** m
            seasonal = 1 + 0.035 * math.sin(2 * math.pi * (m / 12.0) + phase)
            revenue = round(bal_base * trend * seasonal, 4)
            cogs = round(revenue * (1 - margin), 4)
            period_name = "Current Period" if m >= 12 else "Prior Period"
            year = 2024 + (8 - 1 + m) // 12
            month = (8 - 1 + m) % 12 + 1
            period = "%04d-%02d-01" % (year, month)
            rows.append((name, order, period, period_name,
                         revenue, cogs, round(_patients(m), 0)))
    return rows


def revenue_sql():
    rows = build_revenue_rows()
    lines = []
    for i, (name, order, period, pname, revenue, cogs, patients) in enumerate(rows):
        lead = "SELECT" if i == 0 else "UNION ALL SELECT"
        if i == 0:
            lines.append(
                "    %s '%s' AS product, %d AS product_order, "
                "CAST('%s' AS DATE) AS period, '%s' AS period_name, "
                "%s AS revenue, %s AS cogs, %s AS patients"
                % (lead, name, order, period, pname, revenue, cogs, patients))
        else:
            lines.append(
                "    %s '%s', %d, CAST('%s' AS DATE), '%s', %s, %s, %s"
                % (lead, name, order, period, pname, revenue, cogs, patients))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------
add({"id": "tbl-base", "kind": "table", "name": LB,
     "source": {"connectionId": CONN_DB, "kind": "sql", "statement": revenue_sql()},
     "columns": [
         {"id": "b-product", "formula": "[Custom SQL/product]", "name": "Product"},
         {"id": "b-order", "formula": "[Custom SQL/product_order]", "name": "Product Order"},
         {"id": "b-date", "formula": "[Custom SQL/period]", "name": "Period"},
         {"id": "b-pname", "formula": "[Custom SQL/period_name]", "name": "Period Name"},
         {"id": "b-rev", "formula": "[Custom SQL/revenue]", "name": "Revenue"},
         {"id": "b-cogs", "formula": "[Custom SQL/cogs]", "name": "COGS"},
         {"id": "b-cust", "formula": "[Custom SQL/patients]", "name": "Patients"},
         {"id": "b-margin", "formula": "[Revenue] - [COGS]", "name": "Gross Profit"},
     ]})

# product_cards_sql() reads product[3] (bal) as a STANDALONE point-in-time
# scale figure (bal/1000 -> "$B") -- feeding it the tiny monthly bal_base
# renders near-zero (confirmed on the ClickHouse build). Feed it the real
# annual target instead, pre-scaled by 1000 so product_cards_sql()'s own
# round(bal/1000.0, 2) divides losslessly.
_ANNUAL_TARGETS = {"Oncology & Hematology": 14.4, "Rare & Orphan Disease": 9.6,
                   "Autoimmune & Rheumatology": 8.0}


def _cfg_with_bal(scale):
    return json.loads(json.dumps({"key": CFG["key"], "products": [
        [_ANNUAL_TARGETS[p[0]] * scale if i == 3 else v for i, v in enumerate(p)]
        for p in CFG["products"]]}))


CFG_CARDS = _cfg_with_bal(1000)

add({"id": "tbl-pc", "kind": "table", "name": PC,
     "source": {"connectionId": CONN_DB, "kind": "sql",
                "statement": db_types(CO.product_cards_sql(CFG_CARDS))},
     "columns": [{"id": p, "name": n, "formula": "[Custom SQL/%s]" % n} for p, n in [
         ("p0", "Product"), ("p1", "Product Order"), ("p2", "Tagline"), ("p3", "Balances $B"),
         ("p4", "Rate Label"), ("p5", "Rate Value"), ("p6", "Members M"), ("p7", "Goal Pct"),
         ("p8", "Status")]]})

add({"id": "tbl-notif", "kind": "table", "name": NT,
     "source": {"connectionId": CONN_DB, "kind": "sql",
                "statement": db_types(CO.notifications_sql(CFG))},
     "columns": [{"id": p, "name": n, "formula": "[Custom SQL/%s]" % n} for p, n in [
         ("q0", "Alert Key"), ("q1", "Alert Order"), ("q2", "Severity"), ("q3", "Title"),
         ("q4", "Body"), ("q5", "Age"), ("q6", "Owner"), ("q7", "Impact")]]})

# ------------------------------------------------------------------ helpers

def header(head, subtitle):
    add({"id": "c-hdr1", "kind": "container", "spacing": "small",
         "style": {"backgroundColor": B.NAVY, "borderRadius": "round", "padding": "none"},
         "backgroundImage": {"source": {"kind": "url", "url": B.header_bg()},
                             "style": {"fit": "cover"}}})
    add({"id": "logo1", "kind": "image", "source": {"kind": "url", "url": B.logo_white()},
         "style": {"fit": "contain", "align": "start", "padding": "none"}})
    add({"id": "ttl1", "kind": "text",
         "body": '# **<span style="color: #FFFFFF">%s</span>**' % head,
         "verticalAlign": "end"})
    add({"id": "sub1", "kind": "text",
         "body": '<span style="color: %s">%s</span>' % (B.SOFI_CYAN, subtitle),
         "verticalAlign": "start"})


def kpi_card(key, label, cur, pri, fmt, ga, gb, spark):
    add({"id": "c-%s" % key, "kind": "container", "spacing": "small",
         "style": {"borderRadius": "round", "padding": "none"},
         "backgroundImage": {"source": {"kind": "url", "url": B.card_gradient(ga, gb)},
                             "style": {"fit": "cover"}}})
    add({"id": "kc-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-base", "kind": "table"},
         "columns": [{"id": "vc-%s" % key, "formula": cur, "name": label, "format": fmt},
                     {"id": "vk-%s" % key, "formula": pri, "name": "Prior Period", "format": fmt}],
         "value": {"columnId": "vc-%s" % key, "color": "#FFFFFF", "fontSize": 26},
         "comparisonColumn": {"columnId": "vk-%s" % key},
         "comparison": {"display": "delta", "colorGood": "#CDEBB8", "colorBad": "#FFCFC7", "fontSize": 13},
         "name": {"text": label, "color": "#FFFFFF", "fontSize": 12},
         "layout": {"anchor": "middle"},
         "style": {"padding": "none", "backgroundColor": ga}})
    add({"id": "kp-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-base", "kind": "table"},
         "columns": [{"id": "vp-%s" % key, "formula": pri, "name": "Prior Period", "format": fmt}],
         "value": {"columnId": "vp-%s" % key, "color": B.NAVY, "fontSize": 22},
         "name": {"text": "Prior Period", "color": B.NAVY, "fontSize": 13},
         "layout": {"anchor": "middle"},
         "style": {"padding": "none", "backgroundColor": gb}})
    add({"id": "sp-%s" % key, "kind": "line-chart",
         "source": {"elementId": "tbl-base", "kind": "table"},
         "columns": [{"id": "spx-%s" % key, "formula": 'DateTrunc("month", [%s/Period])' % LB, "name": "Month"},
                     {"id": "spy-%s" % key, "formula": spark, "name": "Trend"},
                     {"id": "spc-%s" % key, "formula": '"Trend"', "name": "Series"}],
         "xAxis": {"columnId": "spx-%s" % key, "format": {"labels": "hidden", "marks": "none"}},
         "yAxis": {"columnIds": ["spy-%s" % key],
                   "format": {"labels": "hidden", "marks": "none",
                              "scale": {"type": "linear", "zero": False, "hideZeroLine": True}}},
         "color": {"by": "category", "column": "spc-%s" % key, "scheme": ["#FFFFFF"]},
         "name": {"visibility": "hidden"}, "legend": {"visibility": "hidden"},
         "style": {"padding": "none"},
         "lineAreaStyle": {"interpolation": "monotone"}})


def date_control(eid, cid, name, element_id, column_id):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "date-range", "mode": "between",
            "includeNulls": "when-no-value-is-selected",
            "filters": [{"source": {"kind": "table", "elementId": element_id}, "columnId": column_id}]}


def list_control(eid, cid, name, element_id, column_id):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "list", "mode": "include", "selectionMode": "multiple",
            "values": [],
            "filters": [{"source": {"kind": "table", "elementId": element_id}, "columnId": column_id}],
            "source": {"kind": "source",
                       "source": {"kind": "table", "elementId": element_id},
                       "columnId": column_id}}


def segmented_control(eid, cid, name, values):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "segmented",
            "source": {"kind": "manual", "valueType": "text", "values": values},
            "value": None}


def cur_(col):
    return 'SumIf([{t}/{c}], [{t}/Period Name] = "Current Period")'.format(t=LB, c=col)


def pri_(col):
    return 'SumIf([{t}/{c}], [{t}/Period Name] = "Prior Period")'.format(t=LB, c=col)


def curmax_(col):
    return 'MaxIf([{t}/{c}], [{t}/Period Name] = "Current Period")'.format(t=LB, c=col)


def primax_(col):
    return 'MaxIf([{t}/{c}], [{t}/Period Name] = "Prior Period")'.format(t=LB, c=col)


def _nt(col, order):
    return 'MaxIf([{t}/{c}], [{t}/Alert Key] = "a{o}")'.format(t=NT, c=col, o=order)


def _pc(col, product):
    return 'MaxIf([{t}/{c}], [{t}/Product] = "{p}")'.format(t=PC, c=col, p=product)


# ================================================================ page content

header(CFG["title"],
       "Therapy-line revenue, gross profit and patient growth &middot; trailing twelve months vs prior year")

add({"id": "c-filters", "kind": "container", "spacing": "small", "style": panel()})
add(date_control("ctrl-date", "Period", "Period", "tbl-base", "b-date"))
add(list_control("ctrl-product", "ProductFilter", "Therapy Line", "tbl-base", "b-product"))
add(dict(segmented_control("ctrl-grain", "Grain", "Date grain", ["quarter", "month"]), value="month"))

# --- KPI row
kpi_card("rev", "Revenue ($M)", cur_("Revenue"), pri_("Revenue"), MONEY_M,
         B.NAVY, B.SOFI_BRIGHT, "Sum([%s/Revenue])" % LB)
kpi_card("cp", "Gross Profit ($M)", cur_("Gross Profit"), pri_("Gross Profit"), MONEY_M,
         B.NAVY_DEEP, B.SOFI_CYAN, "Sum([%s/Gross Profit])" % LB)
kpi_card("bal", "Patients Served", curmax_("Patients"), primax_("Patients"), NUM0,
         B.NAVY_DEEP, B.SOFI_BLUE, "Max([%s/Patients])" % LB)
kpi_card("mem", "Gross Margin",
         "%s / NullIf(%s, 0)" % (cur_("Gross Profit"), cur_("Revenue")),
         "%s / NullIf(%s, 0)" % (pri_("Gross Profit"), pri_("Revenue")),
         PCT1, B.NAVY_DEEP, B.SOFI_MINT, "Sum([%s/Gross Profit]) / NullIf(Sum([%s/Revenue]), 0)" % (LB, LB))

# --- chart: revenue by period and therapy line
add({"id": "c-chartwrap", "kind": "container", "spacing": "small", "style": {"padding": "none"}})
add({"id": "ico-chart", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_TREND)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "chart-heading", "kind": "text",
     "body": '<span style="color: %s">**REVENUE BY THERAPY LINE**</span>' % B.NAVY,
     "verticalAlign": "middle"})
add({"id": "bar-prod", "kind": "bar-chart",
     "source": {"elementId": "tbl-base", "kind": "table"},
     "columns": [
         {"id": "bp-color", "formula": "[%s/Product]" % LB, "name": "Product"},
         {"id": "bp-x", "formula": 'DateTrunc([Grain], [%s/Period])' % LB, "name": "Period"},
         {"id": "bp-y", "formula": "Sum([%s/Revenue])" % LB, "name": "Revenue", "format": MONEY_M},
     ],
     "yAxis": {"columnIds": ["bp-y"]},
     "xAxis": {"columnId": "bp-x", "format": {"kind": "datetime", "formatString": "%b %Y"}},
     "color": {"by": "category", "column": "bp-color", "scheme": B.CATEGORICAL},
     "stacking": "stacked",
     "name": {"visibility": "hidden"},
     "style": {"backgroundColor": B.CARD, "borderRadius": "round", "borderColor": B.BORDER, "borderWidth": 1}})

# --- therapy-line cards (no modal/drill -- lightweight build)
PRODUCTS = [("p%d" % (i + 1), pr[0], pr[13]) for i, pr in enumerate(CFG["products"])]
add({"id": "c-prodwrap", "kind": "container", "spacing": "small", "style": {"padding": "none"}})
add({"id": "ico-prod", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_USERS)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "pc-heading", "kind": "text",
     "body": '<span style="color: %s">**THERAPY LINE PERFORMANCE**</span>' % B.NAVY,
     "verticalAlign": "middle"})

for key, product, tagline in PRODUCTS:
    add({"id": "pcard-%s" % key, "kind": "container", "spacing": "small", "style": panel()})
    add({"id": "pc-name-%s" % key, "kind": "text", "body": "### %s" % product, "verticalAlign": "middle"})
    add({"id": "pc-tag-%s" % key, "kind": "text",
         "body": '<span style="color: %s">%s</span>' % (B.TEXT_MUTED, tagline), "verticalAlign": "start"})
    add({"id": "pc-bal-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-pc", "kind": "table"},
         "columns": [{"id": "pcv-%s" % key, "formula": _pc("Balances $B", product),
                      "name": "Revenue ($M)",
                      "format": {"kind": "number", "formatString": "$,.1f", "currencySymbol": "$"}}],
         "value": {"columnId": "pcv-%s" % key, "color": B.NAVY, "fontSize": 24},
         "name": {"visibility": "hidden"}, "style": {"padding": "none"}, "layout": {"anchor": "start"}})
    add({"id": "pc-ring-%s" % key, "kind": "progress",
         "source": {"elementId": "tbl-pc", "kind": "table"},
         "shape": "ring", "value": _pc("Goal Pct", product), "min": "0", "max": "1.3",
         "config": {"label": {"visibility": "hidden"}, "fillColor": B.SOFI_BLUE, "trackColor": "#E3EBF4"},
         "style": {"padding": "none"}})
    add({"id": "pc-sub-%s" % key, "kind": "text",
         "body": ('<span style="color: %s">{{%s}}</span> **{{%s | .1f}}%%** '
                  '<span style="color: %s">&middot; {{%s | ,.2f}}K patients &middot; {{%s}}</span>')
                 % (B.TEXT_MUTED, _pc("Rate Label", product), _pc("Rate Value", product), B.TEXT_MUTED,
                    _pc("Members M", product), _pc("Status", product)),
         "verticalAlign": "end"})

# --- live alerts rail
add({"id": "c-secn", "kind": "container", "spacing": "small", "style": panel()})
add({"id": "ico-notif", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_SPARK)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "notif-heading", "kind": "text",
     "body": '<span style="color: %s">**LIVE ALERTS**</span>' % B.NAVY,
     "verticalAlign": "middle"})

_SEV = {"critical": (B.BAD, "#FCEBEB", "#F09595", "#501313", "#791F1F"),
        "warning": (B.WARN, "#FAEEDA", "#EF9F27", "#412402", "#633806"),
        "info": ("#0C447C", "#E6F1FB", "#85B7EB", "#042C53", "#0C447C")}
ALERTS = [(i + 1, al[0], al[6]) for i, al in enumerate(CFG["alerts"])]

for _o, _sev, _cap in ALERTS:
    _c, _tint, _bd, _body, _meta = _SEV[_sev]
    _k = "n%d" % _o
    add({"id": "ncard-%s" % _k, "kind": "container",
         "style": {"backgroundColor": _tint, "borderRadius": "round", "borderColor": _bd, "borderWidth": 1}})
    add({"id": "nsev-%s" % _k, "kind": "text",
         "body": '<span style="color: %s">%s</span>' % (_c, _sev.upper()),
         "verticalAlign": "middle"})
    add({"id": "ntitle-%s" % _k, "kind": "text",
         "body": '<span style="color: %s">**{{%s}}**</span>' % (_c, _nt("Title", _o)),
         "verticalAlign": "middle"})
    add({"id": "nbody-%s" % _k, "kind": "text",
         "body": '<span style="color: %s">{{%s}}</span>' % (_body, _nt("Body", _o)),
         "verticalAlign": "start"})
    add({"id": "nkpi-%s" % _k, "kind": "kpi-chart",
         "source": {"elementId": "tbl-notif", "kind": "table"},
         "columns": [{"id": "nkv-%s" % _k, "formula": _nt("Impact", _o), "name": _cap, "format": NUM0}],
         "value": {"columnId": "nkv-%s" % _k, "color": _c, "fontSize": 20},
         "name": {"text": _cap, "color": _meta, "fontSize": 10},
         "layout": {"anchor": "start"}, "style": {"padding": "none"}})
    add({"id": "nmeta-%s" % _k, "kind": "text",
         "body": '<span style="color: %s">{{%s}} &middot; {{%s}}</span>' % (_meta, _nt("Owner", _o), _nt("Age", _o)),
         "verticalAlign": "end"})


# ==================================================================== layout

_CARD_ROWS = []
for _i, (_k, _prod, _tag) in enumerate(PRODUCTS):
    _col = 1 + _i * 8
    _CARD_ROWS.append(
        '        <Container elementId="pcard-%s" type="grid" gridColumn="%d / %d" gridRow="1 / 10" '
        'gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">\n'
        '          <Element elementId="pc-name-%s" gridColumn="1 / 9" gridRow="1 / 2"/>\n'
        '          <Element elementId="pc-ring-%s" gridColumn="9 / 13" gridRow="1 / 4"/>\n'
        '          <Element elementId="pc-tag-%s" gridColumn="1 / 9" gridRow="2 / 3"/>\n'
        '          <Element elementId="pc-bal-%s" gridColumn="1 / 9" gridRow="3 / 6"/>\n'
        '          <Element elementId="pc-sub-%s" gridColumn="1 / 13" gridRow="6 / 9"/>\n'
        '        </Container>' % (_k, _col, _col + 8, _k, _k, _k, _k, _k))

_NOTIF_ROWS = []
for _i, (_o, _sev, _cap) in enumerate(ALERTS):
    _k = "n%d" % _o
    _t = 3 + _i * 8
    _NOTIF_ROWS.append(
        '        <Container elementId="ncard-%s" type="grid" gridColumn="1 / 25" gridRow="%d / %d" '
        'gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">\n'
        '          <Element elementId="nsev-%s" gridColumn="1 / 25" gridRow="1 / 2"/>\n'
        '          <Element elementId="ntitle-%s" gridColumn="1 / 25" gridRow="2 / 3"/>\n'
        '          <Element elementId="nbody-%s" gridColumn="1 / 25" gridRow="3 / 5"/>\n'
        '          <Element elementId="nkpi-%s" gridColumn="1 / 13" gridRow="5 / 7"/>\n'
        '          <Element elementId="nmeta-%s" gridColumn="13 / 25" gridRow="5 / 7"/>\n'
        '        </Container>' % (_k, _t, _t + 8, _k, _k, _k, _k, _k))

LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo1" gridColumn="1 / 6" gridRow="1 / 3"/>
    <Element elementId="ttl1" gridColumn="1 / 20" gridRow="3 / 5"/>
    <Element elementId="sub1" gridColumn="1 / 20" gridRow="5 / 6"/>
  </Container>
  <Container elementId="c-filters" type="grid" gridColumn="1 / 25" gridRow="6 / 9" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-date" gridColumn="1 / 9" gridRow="1 / 4"/>
    <Element elementId="ctrl-product" gridColumn="9 / 17" gridRow="1 / 4"/>
    <Element elementId="ctrl-grain" gridColumn="17 / 21" gridRow="1 / 4"/>
  </Container>
  <Container elementId="c-rev" type="grid" gridColumn="1 / 7" gridRow="9 / 19" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-rev" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-rev" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="sp-rev" gridColumn="1 / 13" gridRow="8 / 11"/>
  </Container>
  <Container elementId="c-cp" type="grid" gridColumn="7 / 13" gridRow="9 / 19" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-cp" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-cp" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="sp-cp" gridColumn="1 / 13" gridRow="8 / 11"/>
  </Container>
  <Container elementId="c-bal" type="grid" gridColumn="13 / 19" gridRow="9 / 19" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-bal" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-bal" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="sp-bal" gridColumn="1 / 13" gridRow="8 / 11"/>
  </Container>
  <Container elementId="c-mem" type="grid" gridColumn="19 / 25" gridRow="9 / 19" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-mem" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-mem" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="sp-mem" gridColumn="1 / 13" gridRow="8 / 11"/>
  </Container>
  <Container elementId="c-chartwrap" type="grid" gridColumn="1 / 17" gridRow="19 / 37" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-chart" gridColumn="1 / 2" gridRow="1 / 3"/>
    <Element elementId="chart-heading" gridColumn="2 / 25" gridRow="1 / 3"/>
    <Element elementId="bar-prod" gridColumn="1 / 25" gridRow="3 / 18"/>
  </Container>
  <Container elementId="c-prodwrap" type="grid" gridColumn="1 / 17" gridRow="37 / 49" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-prod" gridColumn="1 / 2" gridRow="1 / 3"/>
    <Element elementId="pc-heading" gridColumn="2 / 25" gridRow="1 / 3"/>
__PRODUCT_CARDS__
  </Container>
  <Container elementId="c-secn" type="grid" gridColumn="17 / 25" gridRow="19 / 49" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-notif" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="notif-heading" gridColumn="4 / 25" gridRow="1 / 3"/>
__NOTIF_CARDS__
  </Container>
  <Element elementId="tbl-base" gridColumn="1 / 5" gridRow="49 / 50"/>
  <Element elementId="tbl-pc" gridColumn="5 / 9" gridRow="49 / 50"/>
  <Element elementId="tbl-notif" gridColumn="9 / 13" gridRow="49 / 50"/>
</Page>
"""
LAYOUT = LAYOUT.replace("__PRODUCT_CARDS__", "\n".join(_CARD_ROWS))
LAYOUT = LAYOUT.replace("__NOTIF_CARDS__", "\n".join(_NOTIF_ROWS))

spec = {
    "name": "SynergenRx — Patient Access & Therapy Performance Command Center",
    "folderId": FOLDER_ID,
    "document": {
        "schemaVersion": 1,
        "kind": "workbook",
        "elements": elements,
        "pages": [{"id": "pg1", "name": "Command Center"}],
        "overlays": overlays,
        "agents": agents,
        "layout": LAYOUT,
    },
}

print(json.dumps(spec, indent=2))
