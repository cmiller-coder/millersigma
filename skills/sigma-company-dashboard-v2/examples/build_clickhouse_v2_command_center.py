#!/usr/bin/env python3
"""ClickHouse Inc. Command Center -- runs through company.py's real
config/calibration path (CFG["products"]/["alerts"], products_cards_sql,
notifications_sql, geo_sql), NOT the raw-BigBuys-table approach from
build_clickhouse_command_center.py. Reshapes data via custom SQL, same as
the standard v2 flow -- just against the ClickHouse connection instead of
Snowflake, since build_sofi.py's own SQL templates (loan_book.sql etc.) use
Snowflake-only functions (SEQ4, DATEADD, HASH, GENERATOR) with no ClickHouse
equivalent wired up. The product x month time series is computed in pure
Python (same technique company.py's own geo_sql() already uses for its
state x product grid) and emitted as literal SELECT/UNION ALL rows, so no
vendor-specific SQL function is needed at all -- this is what makes it
portable to ClickHouse without a full dialect port of the Snowflake
templates.

Usage:
    python3 build_clickhouse_v2_command_center.py > /tmp/spec.json
"""
import json
import math
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import brand as B          # noqa: E402
import company as CO        # noqa: E402

CFG = CO.COMPANIES["clickhouse"]
B.apply(CFG)

CONN_CLICKHOUSE = "8d37c8d6-5516-48f3-9749-b2c81dcc944e"
CONN_DATABRICKS_AI = "21868d1e-38c7-4847-9992-f31ba060478e"  # PSE Serverless
AI_ENDPOINT = "databricks-claude-sonnet-4"
FOLDER_ID = "4cbae364-629c-460b-b06d-4a2bfac7b31a"

LB = CFG["base_table"]           # "Revenue Book"
PC = "Product Cards"
NT = "Notifications"
GEO = "Geo Footprint"
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


def title(text, size=14):
    return {"text": text, "color": B.TEXT_DARK, "fontWeight": "bold", "fontSize": size}


def ch_types(sql_text):
    """Shim company.py's Snowflake CAST types to ClickHouse's. Every literal-
    value generator in company.py (product_cards_sql, notifications_sql,
    geo_sql) wraps its output in CAST(...AS VARCHAR/NUMBER(a,b)) -- neither
    type name exists in ClickHouse (String/Decimal instead). This is the only
    change needed to make those generators' OUTPUT ClickHouse-compatible;
    their generation logic is pure Python string formatting, not SQL, so it
    was already dialect-agnostic."""
    sql_text = re.sub(r"\bVARCHAR\b", "String", sql_text)
    sql_text = re.sub(r"\bNUMBER\((\d+),\s*(\d+)\)", r"Decimal(\1,\2)", sql_text)
    sql_text = re.sub(r"\bNUMBER\b", "Float64", sql_text)
    return sql_text


# ---------------------------------------------------------------------------
# Product x month revenue grid, computed in pure Python (same technique as
# company.py's own geo_sql -- deterministic, no RANDOM, no vendor SQL
# functions) and emitted as literal rows. bal_base per product is back-solved
# so month 12-23 sums hit the real $250M ARR target exactly (see company.py
# comment for the calibration). Customers is a company-wide (not per-
# product) monthly count, repeated on every row so a MaxIf per period still
# returns the right snapshot value without double-counting.
# ---------------------------------------------------------------------------
def _customers(month_idx):
    return 500.0 * (4000.0 / 500.0) ** (month_idx / 23.0)


def build_revenue_rows():
    rows = []
    for p in CFG["products"]:
        name, order, _btype, bal_base, margin, _fund, _fee, _prov, _delinq, \
            _opex, growth, _units, phase = p[:13]
        status = p[16]  # "Ahead"/"Behind" -- same field product_cards_sql() reads
        for m in range(24):
            trend = (1 + growth / 12) ** m
            seasonal = 1 + 0.035 * math.sin(2 * math.pi * (m / 12.0) + phase)
            revenue = round(bal_base * trend * seasonal, 4)
            cogs = round(revenue * (1 - margin), 4)
            period_name = "Current Period" if m >= 12 else "Prior Period"
            # 2024-08-01 + m months, day-of-month fixed (no calendar lib
            # needed for a fixed day)
            year = 2024 + (8 - 1 + m) // 12
            month = (8 - 1 + m) % 12 + 1
            period = "%04d-%02d-01" % (year, month)
            quarter = "%04d-Q%d" % (year, (month - 1) // 3 + 1)
            rows.append((name, order, period, period_name, quarter, status,
                         revenue, cogs, round(_customers(m), 0)))
    return rows


def revenue_sql():
    rows = build_revenue_rows()
    lines = []
    for i, (name, order, period, pname, quarter, status, revenue, cogs,
            customers) in enumerate(rows):
        lead = "SELECT" if i == 0 else "UNION ALL SELECT"
        if i == 0:
            lines.append(
                "    %s '%s' AS product, %d AS product_order, "
                "toDate('%s') AS period, '%s' AS period_name, "
                "'%s' AS quarter, '%s' AS status, "
                "%s AS revenue, %s AS cogs, %s AS customers"
                % (lead, name, order, period, pname, quarter, status,
                   revenue, cogs, customers))
        else:
            lines.append(
                "    %s '%s', %d, toDate('%s'), '%s', '%s', '%s', %s, %s, %s"
                % (lead, name, order, period, pname, quarter, status,
                   revenue, cogs, customers))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------
add({"id": "tbl-base", "kind": "table", "name": LB,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql", "statement": revenue_sql()},
     "columns": [
         {"id": "b-product", "formula": "[Custom SQL/product]", "name": "Product"},
         {"id": "b-order", "formula": "[Custom SQL/product_order]", "name": "Product Order"},
         {"id": "b-date", "formula": "[Custom SQL/period]", "name": "Period"},
         {"id": "b-pname", "formula": "[Custom SQL/period_name]", "name": "Period Name"},
         {"id": "b-quarter", "formula": "[Custom SQL/quarter]", "name": "Quarter"},
         {"id": "b-status", "formula": "[Custom SQL/status]", "name": "Status"},
         {"id": "b-rev", "formula": "[Custom SQL/revenue]", "name": "Revenue"},
         {"id": "b-cogs", "formula": "[Custom SQL/cogs]", "name": "COGS"},
         {"id": "b-cust", "formula": "[Custom SQL/customers]", "name": "Customers"},
         {"id": "b-margin", "formula": "[Revenue] - [COGS]", "name": "Gross Profit"},
     ]})

# Card-scoped clone, same reason build_clickhouse_command_center.py needed
# one: ctrl-card filtering the shared tbl-base would blank every other KPI.
add({"id": "tbl-base-card", "kind": "table", "name": "%s (Card)" % LB,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql", "statement": revenue_sql()},
     "columns": [
         {"id": "z-product", "formula": "[Custom SQL/product]", "name": "Product"},
         {"id": "z-date", "formula": "[Custom SQL/period]", "name": "Period"},
         {"id": "z-quarter", "formula": "[Custom SQL/quarter]", "name": "Quarter"},
         {"id": "z-status", "formula": "[Custom SQL/status]", "name": "Status"},
         {"id": "z-rev", "formula": "[Custom SQL/revenue]", "name": "Revenue"},
         {"id": "z-cogs", "formula": "[Custom SQL/cogs]", "name": "COGS"},
         {"id": "z-margin", "formula": "[Revenue] - [COGS]", "name": "Gross Profit"},
     ]})

# product_cards_sql() and geo_sql() both read product[3] (bal) as a
# STANDALONE point-in-time scale figure (bal/1000 -> "$B") -- neither knows
# about the 24-month growth/seasonal compounding the revenue grid above
# uses, so feeding them the tiny month-1 bal_base (1.057 etc.) renders as
# "$0.0" (confirmed live). Both need a config whose product[3] is the real
# ANNUAL target instead.
_ANNUAL_TARGETS = {"ClickHouse Cloud": 162.5, "Enterprise & Support": 62.5,
                   "Training & Services": 25.0}


def _cfg_with_bal(scale):
    return json.loads(json.dumps({"key": CFG["key"], "products": [
        [_ANNUAL_TARGETS[p[0]] * scale if i == 3 else v for i, v in enumerate(p)]
        for p in CFG["products"]]}))


# product_cards_sql() does round(bal / 1000.0, 2) -- feeding it the real
# annual $M value directly (25.0) loses precision at that rounding step
# (round(0.025, 2) -> 0.03 -> displays as $30.0 instead of $25.0, confirmed
# live on the smallest segment). Pre-scaling by 1000 makes the division
# exact (round(25000/1000, 2) = 25.0) with zero precision loss, so the
# display formula can read "Balances $B" directly with no further scaling.
CFG_CARDS = _cfg_with_bal(1000)
CFG_GEO = _cfg_with_bal(1)

add({"id": "tbl-pc", "kind": "table", "name": PC,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql",
                "statement": ch_types(CO.product_cards_sql(CFG_CARDS))},
     "columns": [{"id": p, "name": n, "formula": "[Custom SQL/%s]" % n} for p, n in [
         ("p0", "Product"), ("p1", "Product Order"), ("p2", "Tagline"), ("p3", "Balances $B"),
         ("p4", "Rate Label"), ("p5", "Rate Value"), ("p6", "Members M"), ("p7", "Goal Pct"),
         ("p8", "Status")]]})

add({"id": "tbl-pc-card", "kind": "table", "name": "%s (Card)" % PC,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql",
                "statement": ch_types(CO.product_cards_sql(CFG_CARDS))},
     "columns": [{"id": "y" + p[1:], "name": n, "formula": "[Custom SQL/%s]" % n} for p, n in [
         ("p0", "Product"), ("p1", "Product Order"), ("p2", "Tagline"), ("p3", "Balances $B"),
         ("p4", "Rate Label"), ("p5", "Rate Value"), ("p6", "Members M"), ("p7", "Goal Pct"),
         ("p8", "Status")]]})

add({"id": "tbl-notif", "kind": "table", "name": NT,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql",
                "statement": ch_types(CO.notifications_sql(CFG))},
     "columns": [{"id": p, "name": n, "formula": "[Custom SQL/%s]" % n} for p, n in [
         ("q0", "Alert Key"), ("q1", "Alert Order"), ("q2", "Severity"), ("q3", "Title"),
         ("q4", "Body"), ("q5", "Age"), ("q6", "Owner"), ("q7", "Impact")]]})

add({"id": "tbl-geo", "kind": "table", "name": GEO,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql",
                "statement": ch_types(CO.geo_sql(CFG_GEO))},
     "columns": [
         {"id": "g0", "name": "State", "formula": "[Custom SQL/State]"},
         {"id": "g1", "name": "Product", "formula": "[Custom SQL/Product]"},
         {"id": "g2", "name": "Volume", "formula": "[Custom SQL/Volume]"},
         {"id": "g3", "name": "Performance Index", "formula": "[Custom SQL/Performance Index]"},
         {"id": "g4", "name": "Spread Pct", "formula": "[Custom SQL/Spread Pct]"},
     ]})

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


def list_control(eid, cid, name, element_id, column_id):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "list", "mode": "include", "selectionMode": "multiple",
            "values": [],
            "filters": [{"source": {"kind": "table", "elementId": element_id}, "columnId": column_id}],
            "source": {"kind": "source",
                       "source": {"kind": "table", "elementId": element_id},
                       "columnId": column_id}}


def date_control(eid, cid, name, element_id, column_id):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "date-range", "mode": "between",
            "includeNulls": "when-no-value-is-selected",
            "filters": [{"source": {"kind": "table", "elementId": element_id}, "columnId": column_id}]}


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


# ============================================================ PAGE 1 content

header(CFG["title"],
       "Revenue, gross profit and customer growth &middot; trailing twelve months vs prior year")

REPORT_URL = "https://app.sigmacomputing.com/sigma-psa/report/2gW3KmNfXGol8Xa2waKifz"
add({"id": "btn-invoice", "kind": "button", "text": "Usage invoice ↗", "appearance": "outline",
     "actions": [{"id": "act-invoice", "trigger": "on-click",
                  "effects": [{"effect": "open-url", "openTarget": "_blank", "url": REPORT_URL}]}]})

add({"kind": "control", "id": "ctrl-card", "controlId": "cardProduct",
     "name": "Product", "controlType": "list", "selectionMode": "single",
     "mode": "include", "values": [],
     "filters": [{"source": {"kind": "table", "elementId": "tbl-base-card"}, "columnId": "z-product"},
                 {"source": {"kind": "table", "elementId": "tbl-pc-card"}, "columnId": "y0"}],
     "source": {"kind": "source", "source": {"kind": "table", "elementId": "tbl-pc"}, "columnId": "p0"}})

overlays.append({"id": "modalCard", "type": "modal", "name": "Product Card",
                 "modal": {"width": "large",
                           "header": {"title": " ", "showCloseIcon": "shown"},
                           "footer": {"primaryCta": {"visible": "hidden"},
                                      "secondaryCta": {"visible": "hidden"}}}})

add({"id": "mc-band", "kind": "container",
     "style": {"backgroundColor": B.NAVY, "borderRadius": "round", "padding": "none"},
     "backgroundImage": {"source": {"kind": "url", "url": B.header_bg()}, "style": {"fit": "cover"}}})
add({"id": "mc-logo", "kind": "image", "source": {"kind": "url", "url": B.logo_white()},
     "style": {"fit": "contain", "align": "start", "padding": "none"}})
add({"id": "mc-title", "kind": "text",
     "body": '## **<span style="color: #FFFFFF">{{[%s (Card)/Product]}}</span>**' % PC,
     "verticalAlign": "middle"})

for _k, _lab, _f, _fmt in [
        ("bal", "Revenue ($M)", "Sum([%s (Card)/Revenue])" % LB, MONEY_M),
        ("mem", "Gross Profit ($M)", "Sum([%s (Card)/Gross Profit])" % LB, MONEY_M),
        ("rate", "Gross Margin",
         "Sum([%s (Card)/Gross Profit]) / NullIf(Sum([%s (Card)/Revenue]), 0)" % (LB, LB), PCT1)]:
    add({"id": "mck-%s" % _k, "kind": "kpi-chart",
         "source": {"elementId": "tbl-base-card", "kind": "table"},
         "columns": [{"id": "mcv-%s" % _k, "formula": _f, "name": _lab, "format": _fmt}],
         "value": {"columnId": "mcv-%s" % _k, "color": B.NAVY, "fontSize": 26},
         "name": {"text": _lab, "color": B.TEXT_MUTED, "fontSize": 12},
         "layout": {"anchor": "middle"}, "style": panel()})

add({"id": "mc-trend", "kind": "line-chart", "name": "Revenue trend",
     "source": {"elementId": "tbl-base-card", "kind": "table"},
     "columns": [{"id": "mct-x", "formula": "[%s (Card)/Period]" % LB, "name": "Month"},
                 {"id": "mct-rev", "formula": "Sum([%s (Card)/Revenue])" % LB,
                  "name": "Revenue ($M)", "format": MONEY_M}],
     "xAxis": {"columnId": "mct-x"},
     "yAxis": {"columnIds": ["mct-rev"]},
     "legend": {"visibility": "hidden"},
     "lineAreaStyle": {"interpolation": "monotone"},
     "style": panel()})

add({"id": "mc-close", "kind": "button", "text": "Close", "appearance": "outline",
     "actions": [{"id": "a-mc-close", "trigger": "on-click", "effects": [{"effect": "close-overlay"}]}]})

add({"id": "tc-persona", "kind": "tabbed-container",
     "tabs": [{"name": "Category Performance"}, {"name": "Product Detail"}],
     "tabBar": {"alignment": "start"}})

# ticker slot: native marker strip (no bespoke plugin)
add({"id": "plg-ticker", "kind": "text",
     "body": '<span style="color: %s">**%s** &middot; trailing twelve months vs prior year</span>'
             % (B.NAVY, CFG["name"].upper()),
     "verticalAlign": "middle"})

# --- notification rail
add({"id": "c-prodwrap", "kind": "container", "spacing": "small", "style": panel()})
add({"id": "c-secn", "kind": "container", "spacing": "small", "style": panel()})
add({"id": "ico-notif", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_SPARK)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "notif-heading", "kind": "text",
     "body": '<span style="color: %s">**LIVE ALERTS**</span>' % B.NAVY,
     "verticalAlign": "middle"})

# "info" used SOFI_BRIGHT (ClickHouse's #FCFF74, ~1.1:1 contrast on white) for
# its severity label/title/KPI color -- unreadable on its own light-blue tint,
# same bug as the section headings below. Reuse the tuple's own dark-blue
# meta color (#0C447C, already proven readable) instead.
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

# --- KPI row
kpi_card("rev", "Revenue ($M)", cur_("Revenue"), pri_("Revenue"), MONEY_M,
         B.NAVY, B.SOFI_BRIGHT, "Sum([%s/Revenue])" % LB)
kpi_card("cp", "Gross Profit ($M)", cur_("Gross Profit"), pri_("Gross Profit"), MONEY_M,
         B.NAVY_DEEP, B.SOFI_CYAN, "Sum([%s/Gross Profit])" % LB)
kpi_card("bal", "Customers", curmax_("Customers"), primax_("Customers"), NUM0,
         B.NAVY_DEEP, B.SOFI_BLUE, "Max([%s/Customers])" % LB)
kpi_card("mem", "Gross Margin",
         "%s / NullIf(%s, 0)" % (cur_("Gross Profit"), cur_("Revenue")),
         "%s / NullIf(%s, 0)" % (pri_("Gross Profit"), pri_("Revenue")),
         PCT1, B.NAVY_DEEP, B.SOFI_MINT, "Sum([%s/Gross Profit]) / NullIf(Sum([%s/Revenue]), 0)" % (LB, LB))

# --- AI insight (Databricks ai_query via CallText -- confirmed live that
# CallVariant type-checks as a variant and Replace() rejects it, and that a
# literal `$` inside a text element's {{}} formula body breaks Sigma's
# parser and silently renders "N/A" even though the identical formula works
# fine as a plain table column. No `$` or apostrophes anywhere below.)
add({"id": "c-strip", "kind": "container",
     "style": {"backgroundColor": B.CARD_ALT, "borderRadius": "round", "borderColor": B.BORDER, "borderWidth": 1}})
add({"id": "ico-ai", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_SPARK)},
     "style": {"fit": "contain", "padding": "none"}})

_AI_PROMPT = (
    '"You are ClickHouse analytics engine narrating what it just computed for ClickHouse Inc. '
    'itself -- this summary comes from a live sub-second aggregation running on ClickHouse Cloud. '
    'Write TWO sentences, 55-75 words total. First sentence: name the revenue line that moved '
    'most and quantify the move. Second sentence: name the single biggest margin or '
    'concentration risk with its number, and what to do about it. Be specific and use real '
    'names. Data: revenue 250.0M USD trailing twelve months vs 84.6M USD prior. Gross margin '
    '69.1 pct of revenue. Lines: ' + PRODUCT_NAMES + '. ClickHouse Cloud is the largest line at '
    '162.5M USD revenue, 65 pct margin, the thinnest of the three. Enterprise and Support is '
    '62.5M USD revenue at 78 pct margin. Training and Services is 25.0M USD revenue at 55 pct '
    'margin, the only line behind its own target. Customers grew from about 500 to 4000 over '
    'the same window."'
)

add({"id": "txt-ai", "kind": "text",
     "body": "**AI INSIGHT** {{[AI Anchor/Insight]}}",
     "verticalAlign": "middle"})
add({"id": "tbl-ai-anchor", "kind": "table", "name": "AI Anchor",
     "source": {"connectionId": CONN_DATABRICKS_AI, "kind": "sql", "statement": "SELECT 1 AS one"},
     "columns": [
         {"id": "ai-one", "formula": "[Custom SQL/one]"},
         {"id": "ai-insight", "name": "Insight",
          "formula": 'Replace(CallText("ai_query", "%s", %s), \'"\', "")' % (AI_ENDPOINT, _AI_PROMPT)},
     ]})

# --- filters
add({"id": "c-filters", "kind": "container", "spacing": "small", "style": panel()})
add(date_control("ctrl-date", "Period", "Period", "tbl-base", "b-date"))
add(list_control("ctrl-product", "ProductFilter", "Product", "tbl-base", "b-product"))
add(dict(segmented_control("ctrl-grain", "Grain", "Date grain", ["quarter", "month"]), value="month"))

# --- product cards
PRODUCTS = [("p%d" % (i + 1), pr[0], pr[13]) for i, pr in enumerate(CFG["products"])]
add({"id": "ico-prod", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_TREND)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "pc-heading", "kind": "text",
     "body": '<span style="color: %s">**LIVE PRODUCT PERFORMANCE**</span>' % B.NAVY,
     "verticalAlign": "middle"})

for key, product, tagline in PRODUCTS:
    add({"id": "pcard-%s" % key, "kind": "container", "spacing": "small", "style": panel()})
    add({"id": "pc-name-%s" % key, "kind": "text", "body": "### %s" % product, "verticalAlign": "middle"})
    add({"id": "pc-tag-%s" % key, "kind": "text",
         "body": '<span style="color: %s">%s</span>' % (B.TEXT_MUTED, tagline), "verticalAlign": "start"})
    add({"id": "pc-bal-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-pc", "kind": "table"},
         # CFG_CARDS pre-scaled product[3] by 1000 so this "Balances $B"
         # value is already the correct $M figure with no precision loss --
         # see CFG_CARDS/_cfg_with_bal comment above.
         "columns": [{"id": "pcv-%s" % key, "formula": _pc("Balances $B", product),
                      "name": "Revenue ($M)",
                      "format": {"kind": "number", "formatString": "$,.1f", "currencySymbol": "$"}}],
         "value": {"columnId": "pcv-%s" % key, "color": B.NAVY, "fontSize": 24},
         "name": {"visibility": "hidden"}, "style": {"padding": "none"}, "layout": {"anchor": "start"}})
    add({"id": "pc-ring-%s" % key, "kind": "progress",
         "source": {"elementId": "tbl-pc", "kind": "table"},
         "shape": "ring", "value": _pc("Goal Pct", product), "min": "0", "max": "1.3",
         "config": {"label": {"visibility": "hidden"}, "fillColor": B.SOFI_BRIGHT, "trackColor": "#E3EBF4"},
         "style": {"padding": "none"}})
    add({"id": "pc-sub-%s" % key, "kind": "text",
         "body": ('<span style="color: %s">{{%s}}</span> **{{%s | .1f}}%%** '
                  '<span style="color: %s">&middot; {{%s | ,.2f}}K customers &middot; {{%s}}</span>')
                 % (B.TEXT_MUTED, _pc("Rate Label", product), _pc("Rate Value", product), B.TEXT_MUTED,
                    _pc("Members M", product), _pc("Status", product)),
         "verticalAlign": "end"})

add({"id": "c-secw", "kind": "container", "spacing": "small", "style": {"padding": "none"}})
for _k, _prod, _tag in PRODUCTS:
    add({"id": "pc-open-%s" % _k, "kind": "button", "text": "View detail →", "appearance": "text",
         "actions": [{"id": "a-pc-open-%s" % _k, "trigger": "on-click",
                      "effects": [
                          {"effect": "set-control-value", "control": "cardProduct",
                           "value": {"type": "constant", "value": {"type": "text", "value": _prod}}},
                          {"effect": "open-overlay", "overlayId": "modalCard"}]}]})

# --- geo footprint map + rank table
add({"id": "map-geo", "kind": "region-map",
     "name": {"visibility": "hidden"},
     "source": {"elementId": "tbl-geo", "kind": "table"},
     "columns": [
         {"id": "gm-st", "formula": "[%s/State]" % GEO, "name": "State"},
         {"id": "gm-vol", "formula": "Sum([%s/Volume])" % GEO, "name": "Revenue", "format": MONEY_M},
         {"id": "gm-perf", "formula": "Avg([%s/Performance Index])" % GEO,
          "name": "Performance vs plan", "format": PCT1}],
     "region": {"id": "gm-st", "regionType": "us-state"},
     "color": {"by": "scale", "column": "gm-perf", "scheme": [B.BAD, "#F3F6FA", B.SOFI_MINT],
               "domain": {"min": 0.85, "mid": 1.0, "max": 1.15}},
     "legend": {"visibility": "shown"},
     "style": panel()})

add({"id": "tbl-rank", "kind": "table", "name": "Revenue by state",
     "source": {"elementId": "tbl-geo", "kind": "table"},
     "columns": [
         {"id": "rk-st", "formula": "[%s/State]" % GEO, "name": "State"},
         {"id": "rk-vol", "formula": "Sum([%s/Volume])" % GEO, "name": "Revenue", "format": MONEY_M},
         {"id": "rk-perf", "formula": "Avg([%s/Performance Index])" % GEO,
          "name": "vs plan", "format": PCT1}],
     "groupings": [{"id": "rkg", "groupBy": ["rk-st"], "calculations": ["rk-vol", "rk-perf"],
                    "sort": [{"columnId": "rk-vol", "direction": "descending"}]}],
     "conditionalFormats": [
         {"type": "single", "columnIds": ["rk-perf"], "condition": "<", "value": 0.98,
          "style": {"backgroundColor": "#FCEBEB", "color": "#A32D2D", "bold": True}},
         {"type": "single", "columnIds": ["rk-perf"], "condition": ">", "value": 1.02,
          "style": {"backgroundColor": "#E1F5EE", "color": "#0F6E56", "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"},
     "style": panel()})

# --- hero slot: native pivot fallback (no bespoke plugin)
add({"id": "plg-wheel", "kind": "pivot-table", "name": "Revenue by product and quarter",
     "source": {"elementId": "tbl-base", "kind": "table"},
     "columns": [
         {"id": "pw-prod", "formula": "[%s/Product]" % LB, "name": "Product"},
         {"id": "pw-q", "formula": 'DateTrunc("quarter", [%s/Period])' % LB, "name": "Quarter"},
         {"id": "pw-rev", "formula": "Sum([%s/Revenue])" % LB, "name": "Revenue", "format": MONEY_M}],
     "rowsBy": [{"id": "pw-prod"}], "columnsBy": [{"id": "pw-q"}], "values": ["pw-rev"], "style": panel()})
add({"id": "ico-wheel", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_WHEEL)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "wheel-heading", "kind": "text",
     "body": '<span style="color: %s">**REAL-TIME REVENUE DETAIL**</span>' % B.NAVY, "verticalAlign": "middle"})

# --- bar chart
add({"id": "bar-prod", "kind": "bar-chart",
     "source": {"elementId": "tbl-base", "kind": "table"},
     "columns": [
         {"id": "bp-x", "formula": 'DateTrunc([Grain], [%s/Period])' % LB, "name": "Period"},
         {"id": "bp-cat", "formula": "[%s/Product]" % LB, "name": "Product"},
         {"id": "bp-y", "formula": "Sum([%s/Revenue])" % LB, "name": "Revenue", "format": MONEY_M}],
     "xAxis": {"columnId": "bp-x"},
     "yAxis": {"columnIds": ["bp-y"]},
     "color": {"by": "category", "column": "bp-cat", "scheme": B.CATEGORICAL},
     "stacking": "stacked",
     "name": title("Revenue by period and product"),
     "legend": {"visibility": "shown"},
     "style": panel()})

# --- chat copilot
add({"id": "c-rail1", "kind": "container", "spacing": "small", "style": panel()})
add({"id": "rail-hd1", "kind": "text", "body": "**ClickHouse Copilot**", "verticalAlign": "middle"})
add({"id": "chat1", "kind": "chat", "agentId": "ag-book"})

agents.append({
    "id": "ag-book", "name": "ClickHouse Copilot",
    "description": "Answers questions about ClickHouse Inc.'s own revenue and customer performance.",
    "instructions": (
        "You are the ClickHouse Inc. analytics copilot, running directly on ClickHouse Cloud -- "
        "every number you cite is a live, sub-second aggregation, computed on demand. The revenue "
        "lines are: " + PRODUCT_NAMES + ". Data covers 24 months split into a current and prior "
        "trailing-twelve-month window; amounts are in USD millions. Cite revenue, gross profit, "
        "gross margin and customer count, and always name the revenue line or state. Be concise "
        "and quantitative."),
    "greeting": {"mode": "generated",
                 "prompt": "Greet the user in one short line, then offer exactly three specific "
                           "questions you can answer from this data. Name real revenue lines and "
                           "make one about whichever line has the thinnest margin."},
    "dataSources": [{"kind": "table", "elementId": "tbl-base"}],
    "tools": [
        {"toolId": "t-focus", "kind": "action", "name": "Focus a revenue line",
         "description": "Filter the command center to one revenue line.",
         "steps": [{"kind": "effect", "effect": "set-control-value", "control": "ProductFilter",
                    "value": {"type": "agent-input", "inputName": "The revenue line to focus on"}}]},
    ]})

# ====================================================================== layout

LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo1" gridColumn="1 / 6" gridRow="1 / 3"/>
    <Element elementId="ttl1" gridColumn="1 / 20" gridRow="3 / 5"/>
    <Element elementId="sub1" gridColumn="1 / 20" gridRow="5 / 6"/>
    <Element elementId="btn-invoice" gridColumn="20 / 25" gridRow="2 / 4"/>
  </Container>
  <Container elementId="c-rev" type="grid" gridColumn="1 / 7" gridRow="6 / 16" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-rev" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-rev" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="sp-rev" gridColumn="1 / 13" gridRow="8 / 11"/>
  </Container>
  <Container elementId="c-cp" type="grid" gridColumn="7 / 13" gridRow="6 / 16" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-cp" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-cp" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="sp-cp" gridColumn="1 / 13" gridRow="8 / 11"/>
  </Container>
  <Container elementId="c-bal" type="grid" gridColumn="13 / 19" gridRow="6 / 16" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-bal" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-bal" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="sp-bal" gridColumn="1 / 13" gridRow="8 / 11"/>
  </Container>
  <Container elementId="c-mem" type="grid" gridColumn="19 / 25" gridRow="6 / 16" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-mem" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-mem" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="sp-mem" gridColumn="1 / 13" gridRow="8 / 11"/>
  </Container>
  <Container elementId="c-strip" type="grid" gridColumn="1 / 25" gridRow="16 / 22" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="plg-ticker" gridColumn="1 / 25" gridRow="1 / 3"/>
    <Element elementId="ico-ai" gridColumn="1 / 2" gridRow="3 / 5"/>
    <Element elementId="txt-ai" gridColumn="2 / 25" gridRow="3 / 6"/>
    <Element elementId="tbl-ai-anchor" gridColumn="1 / 2" gridRow="6 / 7"/>
  </Container>
  <Container elementId="c-filters" type="grid" gridColumn="1 / 25" gridRow="22 / 25" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-date" gridColumn="1 / 9" gridRow="1 / 4"/>
    <Element elementId="ctrl-product" gridColumn="9 / 17" gridRow="1 / 4"/>
    <Element elementId="ctrl-grain" gridColumn="17 / 21" gridRow="1 / 4"/>
  </Container>
  <TabbedContainer elementId="tc-persona" type="tabbed-container" gridColumn="1 / 19" gridRow="25 / 73">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="map-geo" gridColumn="1 / 12" gridRow="1 / 19"/>
      <Element elementId="bar-prod" gridColumn="12 / 25" gridRow="1 / 19"/>
      <Element elementId="tbl-rank" gridColumn="1 / 25" gridRow="19 / 33"/>
      <Container elementId="c-secw" type="grid" gridColumn="1 / 25" gridRow="33 / 55" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="ico-wheel" gridColumn="1 / 2" gridRow="1 / 3"/>
        <Element elementId="wheel-heading" gridColumn="2 / 25" gridRow="1 / 3"/>
        <Element elementId="plg-wheel" gridColumn="1 / 25" gridRow="3 / 21"/>
      </Container>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Container elementId="c-prodwrap" type="grid" gridColumn="1 / 16" gridRow="1 / 30" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="ico-prod" gridColumn="1 / 2" gridRow="1 / 3"/>
        <Element elementId="pc-heading" gridColumn="2 / 25" gridRow="1 / 3"/>
__PRODUCT_CARDS__
      </Container>
      <Container elementId="c-secn" type="grid" gridColumn="16 / 25" gridRow="1 / 48" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="ico-notif" gridColumn="1 / 4" gridRow="1 / 3"/>
        <Element elementId="notif-heading" gridColumn="4 / 25" gridRow="1 / 3"/>
__NOTIF_CARDS__
      </Container>
    </Tab>
  </TabbedContainer>
  <Container elementId="c-rail1" type="grid" gridColumn="19 / 25" gridRow="25 / 73" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="rail-hd1" gridColumn="1 / 25" gridRow="1 / 3"/>
    <Element elementId="chat1" gridColumn="1 / 25" gridRow="3 / 30"/>
  </Container>
  <Element elementId="tbl-base" gridColumn="1 / 5" gridRow="73 / 74"/>
  <Element elementId="tbl-base-card" gridColumn="5 / 9" gridRow="73 / 74"/>
  <Element elementId="tbl-pc" gridColumn="9 / 13" gridRow="73 / 74"/>
  <Element elementId="tbl-pc-card" gridColumn="13 / 17" gridRow="73 / 74"/>
  <Element elementId="tbl-notif" gridColumn="17 / 21" gridRow="73 / 74"/>
  <Element elementId="tbl-geo" gridColumn="21 / 25" gridRow="73 / 74"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="modalCard">
  <Container elementId="mc-band" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="mc-logo" gridColumn="1 / 4" gridRow="1 / 6"/>
    <Element elementId="mc-title" gridColumn="4 / 25" gridRow="1 / 6"/>
  </Container>
  <Element elementId="mck-bal" gridColumn="1 / 9" gridRow="6 / 12"/>
  <Element elementId="mck-mem" gridColumn="9 / 17" gridRow="6 / 12"/>
  <Element elementId="mck-rate" gridColumn="17 / 25" gridRow="6 / 12"/>
  <Element elementId="mc-trend" gridColumn="1 / 25" gridRow="12 / 30"/>
  <Element elementId="mc-close" gridColumn="21 / 25" gridRow="30 / 33"/>
  <Element elementId="ctrl-card" gridColumn="1 / 7" gridRow="33 / 34"/>
</Page>
"""

_CARD_ROWS = []
for _i, _k in enumerate([_p[0] for _p in PRODUCTS]):
    _col = 1 + (_i % 2) * 12
    _top = 3 + (_i // 2) * 10
    _CARD_ROWS.append(
        '        <Container elementId="pcard-%s" type="grid" gridColumn="%d / %d" gridRow="%d / %d" '
        'gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">\n'
        '          <Element elementId="pc-name-%s" gridColumn="1 / 9" gridRow="1 / 2"/>\n'
        '          <Element elementId="pc-ring-%s" gridColumn="9 / 13" gridRow="1 / 4"/>\n'
        '          <Element elementId="pc-tag-%s" gridColumn="1 / 9" gridRow="2 / 3"/>\n'
        '          <Element elementId="pc-bal-%s" gridColumn="1 / 9" gridRow="3 / 6"/>\n'
        '          <Element elementId="pc-sub-%s" gridColumn="1 / 13" gridRow="6 / 8"/>\n'
        '          <Element elementId="pc-open-%s" gridColumn="1 / 9" gridRow="8 / 10"/>\n'
        '        </Container>' % (_k, _col, _col + 12, _top, _top + 10, _k, _k, _k, _k, _k, _k))
LAYOUT = LAYOUT.replace("__PRODUCT_CARDS__", "\n".join(_CARD_ROWS))

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
LAYOUT = LAYOUT.replace("__NOTIF_CARDS__", "\n".join(_NOTIF_ROWS))

spec = {
    "name": "ClickHouse Inc. — Revenue & Customer Command Center",
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
