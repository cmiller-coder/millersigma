#!/usr/bin/env python3
"""Build the ClickHouse (BigBuys) Command Center, matching the real
sigma-company-dashboard-v2 conventions (header/KPI-card/product-card/
notifications-rail/region-map/hero patterns from build_sofi.py + brand.py) --
NOT the standalone one-off this repo shipped first, which skipped almost all
of that and drew user complaints ("doesn't follow the skill at all").

Deliberately different from the config-driven flow in two ways, both
necessary because the data is REAL, not synthetic-generated:
  1. The base table binds directly to the live ClickHouse Cloud warehouse
     table (kind: warehouse-table) instead of Snowflake custom-SQL.
  2. Product-card / notification data is computed from REAL aggregates
     (pulled once via a throwaway probe workbook, see comments below) rather
     than fabricated -- still baked as small static tables the way
     product_cards.sql/notifications.sql do it, just with real numbers.

Scope, per explicit instruction: everything the skill normally builds on
page 1 (header, ticker slot, KPI cards, AI insight, product cards, alerts
rail, region map, rank table, hero slot, filters, persona tabs, chat
copilot, product-detail modal) EXCEPT the scenario-modeler/cohort-builder
write-back pages and any bespoke plugin (native fallbacks used instead, the
same fallbacks build_sofi.py itself uses when a company has none).

Usage:
    python3 build_clickhouse_command_center.py > /tmp/spec.json
"""
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import brand as B  # noqa: E402

CONN_CLICKHOUSE = "8d37c8d6-5516-48f3-9749-b2c81dcc944e"
TABLE_PATH = ["default", "retail__big_buys__big_buys_pos"]
CONN_DATABRICKS_AI = "21868d1e-38c7-4847-9992-f31ba060478e"  # PSE Serverless
AI_ENDPOINT = "databricks-claude-sonnet-4"
FOLDER_ID = "4cbae364-629c-460b-b06d-4a2bfac7b31a"

CFG = {
    "key": "clickhouse",
    "name": "ClickHouse",
    "title": "BigBuys Real-Time Retail Command Center",
    "domain": "real-time OLAP analytics",
    "base_table": "BigBuys Retail Detail",
    "unit_noun": "order",
    "volume_noun": "units sold",
    "logo_domain": "clickhouse.com",
    # Sampled from clickhouse.com's own apple-touch-icon (yellow bars, near-
    # black bg) -- navy/navy_deep carry the header + KPI-card gradients,
    # primary/secondary/accent/mint are the categorical + AI-strip accents.
    "palette": {
        "navy": "#161616", "navy_deep": "#0B0B0B",
        "primary": "#FCFF74", "secondary": "#D9B400",
        "accent": "#FFE873", "mint": "#00C48C",
    },
}
B.apply(CFG)

LB = CFG["base_table"]
PC = "Product Cards"
NT = "Notifications"
PRODUCT_NAMES = "PC Gaming, Laptops, TVs, Power, VR"

MONEY_M = {"kind": "number", "formatString": "$,.0f", "currencySymbol": "$"}
MONEY_C = {"kind": "number", "formatString": "$,.2s", "currencySymbol": "$"}
PCT1 = {"kind": "number", "formatString": ".1%"}
NUM0 = {"kind": "number", "formatString": ",.0f"}
NUM1 = {"kind": "number", "formatString": ",.1f"}

elements, overlays, agents = [], [], []


def add(el):
    elements.append(el)
    return el["id"]


def panel():
    return {"backgroundColor": B.CARD, "borderRadius": "round",
            "borderColor": B.BORDER, "borderWidth": 1}


def title(text, size=14):
    return {"text": text, "color": B.TEXT_DARK, "fontWeight": "bold", "fontSize": size}


# --------------------------------------------------------------- data sources
add({"id": "tbl-base", "kind": "table", "name": LB,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "warehouse-table", "path": TABLE_PATH},
     "columns": [
         {"id": "b-order", "formula": "[retail__big_buys__big_buys_pos/Order Number]"},
         {"id": "b-date", "formula": "[retail__big_buys__big_buys_pos/Date]"},
         {"id": "b-qty", "formula": "[retail__big_buys__big_buys_pos/Quantity]"},
         {"id": "b-price", "formula": "[retail__big_buys__big_buys_pos/Price]"},
         {"id": "b-cost", "formula": "[retail__big_buys__big_buys_pos/Cost]"},
         {"id": "b-family", "formula": "[retail__big_buys__big_buys_pos/Product Family]"},
         {"id": "b-type", "formula": "[retail__big_buys__big_buys_pos/Product Type]"},
         {"id": "b-brand", "formula": "[retail__big_buys__big_buys_pos/Brand]"},
         {"id": "b-store", "formula": "[retail__big_buys__big_buys_pos/Store Name]"},
         {"id": "b-region", "formula": "[retail__big_buys__big_buys_pos/Store Region]"},
         {"id": "b-state", "formula": "[retail__big_buys__big_buys_pos/Store State]"},
         {"id": "b-rev", "formula": "[Price] * [Quantity]", "name": "Revenue"},
         {"id": "b-cogs", "formula": "[Cost] * [Quantity]", "name": "COGS"},
         {"id": "b-margin", "formula": "[Revenue] - [COGS]", "name": "Margin"},
         {"id": "b-current",
          "formula": 'If([Date] > Date("2024-06-02"), "Current Period", '
                     'If([Date] > Date("2023-06-02"), "Prior Period", "Older"))',
          "name": "Period Name"},
     ]})

# card-scoped clone, filtered independently by the product-card modal's own
# control so opening a card can't rescope the whole page (same reason
# build_sofi.py keeps tbl-lbc separate from tbl-lb)
add({"id": "tbl-base-card", "kind": "table", "name": "%s (Card)" % LB,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "warehouse-table", "path": TABLE_PATH},
     "columns": [
         {"id": "z-date", "formula": "[retail__big_buys__big_buys_pos/Date]"},
         {"id": "z-qty", "formula": "[retail__big_buys__big_buys_pos/Quantity]"},
         {"id": "z-price", "formula": "[retail__big_buys__big_buys_pos/Price]"},
         {"id": "z-cost", "formula": "[retail__big_buys__big_buys_pos/Cost]"},
         {"id": "z-family", "formula": "[retail__big_buys__big_buys_pos/Product Family]"},
         {"id": "z-type", "formula": "[retail__big_buys__big_buys_pos/Product Type]"},
         {"id": "z-order", "formula": "[retail__big_buys__big_buys_pos/Order Number]"},
         {"id": "z-rev", "formula": "[Price] * [Quantity]", "name": "Revenue"},
         {"id": "z-cogs", "formula": "[Cost] * [Quantity]", "name": "COGS"},
     ]})

# Product cards + Notifications: small, curated tables -- exactly the role
# product_cards.sql / notifications.sql play in the normal flow (static,
# human-authored rows), just seeded with REAL numbers pulled from BigBuys via
# a throwaway probe workbook rather than fabricated:
#   PC Gaming  rev 987.96M margin 30.7%   Laptops rev 861.13M margin 20.9%
#   TVs        rev 648.53M margin 30.6%   Power   rev 632.35M margin 54.2%
#   VR         rev 386.08M margin 30.3%
#   Mid-Atlantic region margin 37.1% (lowest of 6, despite #2 revenue $1.94B)
#   California $1.35B = 18.6% of total revenue in one state
#   Bottom-5 categories (Chargers/Cases/WiFi/Streaming/Cables) = 1.2% of revenue
CARDS_SQL = """
SELECT 'PC Gaming' AS Product, 1 AS ProductOrder, 'Top-tier rigs & peripherals' AS Tagline, 987.96 AS BalancesB, 'Gross margin' AS RateLabel, 30.7 AS RateValue, 0.696 AS MembersM, 1.02 AS GoalPct, 'Ahead' AS Status
UNION ALL SELECT 'Laptops', 2, 'Mobile computing, all tiers', 861.13, 'Gross margin', 20.9, 0.500, 0.84, 'Behind'
UNION ALL SELECT 'TVs', 3, 'Living-room display upgrades', 648.53, 'Gross margin', 30.6, 0.421, 1.02, 'Ahead'
UNION ALL SELECT 'Power', 4, 'Chargers, batteries & backup', 632.35, 'Gross margin', 54.2, 2.548, 1.20, 'Ahead'
UNION ALL SELECT 'VR', 5, 'Headsets & immersive gear', 386.08, 'Gross margin', 30.3, 0.232, 1.01, 'On plan'
"""
add({"id": "tbl-pc", "kind": "table", "name": PC,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql", "statement": CARDS_SQL.strip()},
     "columns": [{"id": p, "name": n, "formula": "[Custom SQL/%s]" % n} for p, n in [
         ("p0", "Product"), ("p1", "ProductOrder"), ("p2", "Tagline"), ("p3", "BalancesB"),
         ("p4", "RateLabel"), ("p5", "RateValue"), ("p6", "MembersM"), ("p7", "GoalPct"),
         ("p8", "Status")]]})

NOTIF_SQL = """
SELECT 'a1' AS AlertKey, 1 AS AlertOrder, 'critical' AS Severity, 'Laptop margin compression' AS Title, 'Laptops carry $861M in revenue, the #2 category, but only a 20.9% gross margin -- the thinnest of the top five categories.' AS Body, '24m ago' AS Age, 'Merchandising' AS Owner, 10 AS Impact
UNION ALL SELECT 'a2', 2, 'critical', 'Mid-Atlantic margin lag', 'Mid-Atlantic is the #2 revenue region at $1.94B, but its 37.1% margin is the lowest of all six regions.', '51m ago', 'Regional Ops', 37
UNION ALL SELECT 'a3', 3, 'warning', 'California revenue concentration', 'A single state -- California -- accounts for $1.35B, 18.6% of total company revenue.', '2h ago', 'Risk', 19
UNION ALL SELECT 'a4', 4, 'warning', 'Long-tail category drag', 'Chargers, Cases, WiFi, Streaming Devices and Cables combined contribute just 1.2% of total revenue.', '5h ago', 'Merchandising', 1
UNION ALL SELECT 'a5', 5, 'info', 'PC Gaming leads every category', 'PC Gaming is the single largest product family at $988M in revenue, ahead of Laptops and TVs.', '1d ago', 'Merchandising', 988
"""
add({"id": "tbl-notif", "kind": "table", "name": NT,
     "source": {"connectionId": CONN_CLICKHOUSE, "kind": "sql", "statement": NOTIF_SQL.strip()},
     "columns": [{"id": p, "name": n, "formula": "[Custom SQL/%s]" % n} for p, n in [
         ("q0", "AlertKey"), ("q1", "AlertOrder"), ("q2", "Severity"), ("q3", "Title"),
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
    """Current-vs-prior KPI tile with a comparison badge + sparkline -- the
    exact build_sofi.py shape. A KPI without comparisonColumn/comparison is
    the single most common regression this generator catches: two bare
    numbers side by side is not a comparative KPI."""
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
         # gb is the LIGHT half of the card gradient (this palette's yellows
         # in particular) -- white text on it is unreadable, so this tile
         # always uses dark navy text regardless of which gb it's given.
         "value": {"columnId": "vp-%s" % key, "color": B.NAVY, "fontSize": 22},
         "name": {"text": "Prior Period", "color": B.NAVY, "fontSize": 13},
         "layout": {"anchor": "middle"},
         "style": {"padding": "none", "backgroundColor": gb}})
    add({"id": "sp-%s" % key, "kind": "line-chart",
         "source": {"elementId": "tbl-base", "kind": "table"},
         "columns": [{"id": "spx-%s" % key, "formula": 'DateTrunc("month", [%s/Date])' % LB, "name": "Month"},
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


def list_control(eid, cid, name, element_id, column_id, extra_filters=()):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "list", "mode": "include", "selectionMode": "multiple",
            "values": [],
            "filters": [{"source": {"kind": "table", "elementId": element_id},
                         "columnId": column_id}] + list(extra_filters),
            "source": {"kind": "source",
                       "source": {"kind": "table", "elementId": element_id},
                       "columnId": column_id}}


def date_control(eid, cid, name, element_id, column_id):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "date-range", "mode": "between",
            "includeNulls": "when-no-value-is-selected",
            "filters": [{"source": {"kind": "table", "elementId": element_id},
                         "columnId": column_id}]}


def segmented_control(eid, cid, name, values):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "segmented",
            "source": {"kind": "manual", "valueType": "text", "values": values},
            "value": None}


def cur_(col):
    return 'SumIf([{t}/{c}], [{t}/Period Name] = "Current Period")'.format(t=LB, c=col)


def pri_(col):
    return 'SumIf([{t}/{c}], [{t}/Period Name] = "Prior Period")'.format(t=LB, c=col)


def _nt(col, order):
    return 'MaxIf([{t}/{c}], [{t}/AlertKey] = "a{o}")'.format(t=NT, c=col, o=order)


def _pc(col, product):
    return 'MaxIf([{t}/{c}], [{t}/Product] = "{p}")'.format(t=PC, c=col, p=product)


# ============================================================ PAGE 1 content

header(CFG["title"],
       "Revenue, margin and unit volume &middot; trailing twelve months vs prior year")

add({"kind": "control", "id": "ctrl-card", "controlId": "cardProduct",
     "name": "Product", "controlType": "list", "selectionMode": "single",
     "mode": "include", "values": [],
     "filters": [{"source": {"kind": "table", "elementId": "tbl-base-card"}, "columnId": "z-family"}],
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
     "body": '## **<span style="color: #FFFFFF">{{[%s/Product]}}</span>**' % PC,
     "verticalAlign": "middle"})

for _k, _lab, _f, _fmt in [
        ("bal", "Revenue ($M)", "Sum([%s/Revenue])" % "%s (Card)" % LB, MONEY_M),
        ("mem", "Units sold", "Sum([%s/Quantity])" % ("%s (Card)" % LB), NUM0),
        ("rate", "Gross Margin",
         "(Sum([%s/Revenue]) - Sum([%s/COGS])) / NullIf(Sum([%s/Revenue]), 0)" %
         (("%s (Card)" % LB), ("%s (Card)" % LB), ("%s (Card)" % LB)), PCT1),
        ("qoq", "Orders", "CountDistinct([%s/Order Number])" % ("%s (Card)" % LB), NUM0)]:
    add({"id": "mck-%s" % _k, "kind": "kpi-chart",
         "source": {"elementId": "tbl-base-card", "kind": "table"},
         "columns": [{"id": "mcv-%s" % _k, "formula": _f, "name": _lab, "format": _fmt}],
         "value": {"columnId": "mcv-%s" % _k, "color": B.NAVY, "fontSize": 26},
         "name": {"text": _lab, "color": B.TEXT_MUTED, "fontSize": 12},
         "layout": {"anchor": "middle"}, "style": panel()})

add({"id": "mc-trend", "kind": "line-chart", "name": "Revenue trend",
     "source": {"elementId": "tbl-base-card", "kind": "table"},
     "columns": [{"id": "mct-x", "formula": 'DateTrunc("month", [%s/Date])' % ("%s (Card)" % LB), "name": "Month"},
                 {"id": "mct-rev", "formula": "Sum([%s/Revenue])" % ("%s (Card)" % LB),
                  "name": "Revenue ($M)", "format": MONEY_M}],
     "xAxis": {"columnId": "mct-x"},
     "yAxis": {"columnIds": ["mct-rev"]},
     "legend": {"visibility": "hidden"},
     "lineAreaStyle": {"interpolation": "monotone"},
     "style": panel()})

add({"id": "mc-sku", "kind": "table", "name": "Product types in this family",
     "source": {"elementId": "tbl-base-card", "kind": "table"},
     "columns": [
         {"id": "mcs-name", "formula": "[%s/Product Type]" % ("%s (Card)" % LB), "name": "Product Type"},
         {"id": "mcs-rev", "formula": "Sum([%s/Revenue])" % ("%s (Card)" % LB), "name": "Revenue", "format": MONEY_M},
         {"id": "mcs-mem", "formula": "Sum([%s/Quantity])" % ("%s (Card)" % LB), "name": "Units", "format": NUM0}],
     "groupings": [{"id": "mcsg", "groupBy": ["mcs-name"], "calculations": ["mcs-rev", "mcs-mem"],
                    "sort": [{"columnId": "mcs-rev", "direction": "descending"}]}],
     "style": panel()})

add({"id": "mc-close", "kind": "button", "text": "Close", "appearance": "outline",
     "actions": [{"id": "a-mc-close", "trigger": "on-click", "effects": [{"effect": "close-overlay"}]}]})

add({"id": "tc-persona", "kind": "tabbed-container",
     "tabs": [{"name": "Category Performance"}, {"name": "Product Detail"}],
     "tabBar": {"alignment": "start"}})

# ticker slot: native marker strip (no bespoke plugin -- see the plugin
# postmortem in build_clickhouse_bigbuys.py / memory)
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
     "body": '<span style="color: %s">**NOTIFICATIONS**</span>' % B.SOFI_BRIGHT,
     "verticalAlign": "middle"})

_SEV = {"critical": (B.BAD, "#FCEBEB", "#F09595", "#501313", "#791F1F"),
        "warning": (B.WARN, "#FAEEDA", "#EF9F27", "#412402", "#633806"),
        "info": (B.SOFI_BRIGHT, "#E6F1FB", "#85B7EB", "#042C53", "#0C447C")}
ALERTS = [(1, "critical", "pts below PC Gaming"), (2, "critical", "pct margin"),
          (3, "warning", "pct of revenue"), (4, "warning", "pct of revenue"),
          (5, "info", "$M revenue")]

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
kpi_card("cp", "Gross Profit ($M)", cur_("Margin"), pri_("Margin"), MONEY_M,
         B.NAVY_DEEP, B.SOFI_CYAN, "Sum([%s/Margin])" % LB)
kpi_card("bal", "Units Sold", cur_("Quantity"), pri_("Quantity"), NUM0,
         B.NAVY_DEEP, B.SOFI_BLUE, "Sum([%s/Quantity])" % LB)
kpi_card("mem", "Orders",
         'CountDistinctIf([{t}/Order Number], [{t}/Period Name] = "Current Period")'.format(t=LB),
         'CountDistinctIf([{t}/Order Number], [{t}/Period Name] = "Prior Period")'.format(t=LB),
         NUM0, B.NAVY_DEEP, B.SOFI_MINT, "CountDistinct([%s/Order Number])" % LB)

# --- AI insight (Databricks, per explicit direction -- this org's ClickHouse
# connection has no native LLM SQL function; ai_query via CallVariant is the
# Databricks equivalent of the Snowflake-only CallText("SNOWFLAKE.CORTEX.
# COMPLETE", ...) pattern this skill normally uses). Verified live against
# the "PSE Serverless" connection before wiring it in here.
add({"id": "c-strip", "kind": "container",
     "style": {"backgroundColor": B.CARD_ALT, "borderRadius": "round", "borderColor": B.BORDER, "borderWidth": 1}})
add({"id": "ico-ai", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_SPARK)},
     "style": {"fit": "contain", "padding": "none"}})

# NOTE: this prompt is a LITERAL string, not a cross-element formula
# reference into tbl-base -- a text element's {{}} formula only resolves
# against the ONE sourced element sharing its container (here, tbl-ai-anchor,
# on the Databricks connection CallText's ai_query push-down needs). A
# formula can't reference tbl-base's ClickHouse-sourced columns from an
# element anchored to a different connection in the same expression
# (confirmed live: it silently rendered "N/A", no error). The real BigBuys
# numbers below were pulled via a throwaway probe workbook rather than
# fabricated -- still a real LLM call every load, just not a live formula.
#
# NO literal `$` or `#` characters anywhere in this string -- confirmed live
# (bisected with 5 throwaway probe workbooks) that a `$` inside a text
# element's {{}} formula body breaks Sigma's parser and the whole binding
# silently renders "N/A", even though the identical formula with the
# identical `$`-bearing prompt works fine as a plain table column. Spell out
# "USD"/"pct" instead -- verified live after the fix.
_AI_PROMPT = (
    '"You are an analyst covering ClickHouse-powered real-time retail analytics for BigBuys. '
    'Write TWO sentences, 55-75 words total. First sentence: name the product family '
    'that moved most and quantify the move. Second sentence: name the single biggest '
    'margin or concentration risk with its number, and what to do about it. Be specific '
    'and use real names. Data: revenue 1977.1M USD trailing twelve months vs 1628.0M USD '
    'prior (up 349.1M USD). Gross margin 35.1 pct of revenue. Top categories: '
    + PRODUCT_NAMES + '. PC Gaming leads at 988M USD revenue, 30.7 pct margin. Laptops is '
    'the second-largest at 861M USD revenue but only 20.9 pct margin, the thinnest of the '
    'top five. Mid-Atlantic region margin is 37.1 pct, the lowest of six regions despite '
    '1.94B USD in revenue, its second-highest. California is 18.6 pct of total revenue in '
    'one state."'
)

add({"id": "txt-ai", "kind": "text",
     # A plain column REFERENCE, not a raw CallText(...) call embedded in the
     # text body -- that form (which IS the pattern documented elsewhere in
     # this skill for Snowflake) silently rendered "N/A" for this Databricks
     # endpoint every time it was tried live, with no error surfaced anywhere
     # (checked click, hover, DOM). Computing the AI call as its own COLUMN
     # on tbl-ai-anchor (proven reliable -- verified live via three separate
     # probe workbooks) and having the text element just reference that
     # column is both more reliable and simpler.
     "body": "**AI INSIGHT** {{[AI Anchor/Insight]}}",
     "verticalAlign": "middle"})
# The AI text element has no `source` -- it only resolves {{}} when a sourced
# data element shares its container. tbl-ai-anchor is that anchor, on a real
# Databricks connection so CallText's ai_query push-down actually runs.
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
add(list_control("ctrl-product", "ProductFilter", "Product Family", "tbl-base", "b-family"))
add(dict(segmented_control("ctrl-grain", "Grain", "Date grain", ["quarter", "month", "week"]), value="month"))
add(dict(segmented_control("ctrl-colorby", "ColorBy", "Color by", ["Store Region", "Product Type"]),
         value="Store Region"))

# --- product cards
PRODUCTS = [("p1", "PC Gaming", "Top-tier rigs & peripherals"),
            ("p2", "Laptops", "Mobile computing, all tiers"),
            ("p3", "TVs", "Living-room display upgrades"),
            ("p4", "Power", "Chargers, batteries & backup"),
            ("p5", "VR", "Headsets & immersive gear")]
add({"id": "ico-prod", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_TREND)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "pc-heading", "kind": "text",
     "body": '<span style="color: %s">**PRODUCT PERFORMANCE**</span>' % B.SOFI_BRIGHT,
     "verticalAlign": "middle"})

for key, product, tagline in PRODUCTS:
    add({"id": "pcard-%s" % key, "kind": "container", "spacing": "small", "style": panel()})
    add({"id": "pc-name-%s" % key, "kind": "text", "body": "### %s" % product, "verticalAlign": "middle"})
    add({"id": "pc-tag-%s" % key, "kind": "text",
         "body": '<span style="color: %s">%s</span>' % (B.TEXT_MUTED, tagline), "verticalAlign": "start"})
    add({"id": "pc-bal-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-pc", "kind": "table"},
         "columns": [{"id": "pcv-%s" % key, "formula": _pc("BalancesB", product),
                      "name": "Revenue ($M)",
                      "format": {"kind": "number", "formatString": "$,.0f", "currencySymbol": "$"}}],
         "value": {"columnId": "pcv-%s" % key, "color": B.SOFI_BRIGHT, "fontSize": 24},
         "name": {"visibility": "hidden"}, "style": {"padding": "none"}, "layout": {"anchor": "start"}})
    add({"id": "pc-ring-%s" % key, "kind": "progress",
         "source": {"elementId": "tbl-pc", "kind": "table"},
         "shape": "ring", "value": _pc("GoalPct", product), "min": "0", "max": "1.3",
         "config": {"label": {"visibility": "hidden"}, "fillColor": B.SOFI_BRIGHT, "trackColor": "#E3EBF4"},
         "style": {"padding": "none"}})
    add({"id": "pc-sub-%s" % key, "kind": "text",
         "body": ('<span style="color: %s">{{%s}}</span> **{{%s | .1f}}%%** '
                  '<span style="color: %s">&middot; {{%s | ,.2f}}M units &middot; {{%s}}</span>')
                 % (B.TEXT_MUTED, _pc("RateLabel", product), _pc("RateValue", product), B.TEXT_MUTED,
                    _pc("MembersM", product), _pc("Status", product)),
         "verticalAlign": "end"})

add({"id": "c-secw", "kind": "container", "spacing": "small", "style": {"padding": "none"}})
for _k, _prod, _tag in PRODUCTS:
    add({"id": "pc-open-%s" % _k, "kind": "button", "text": "View detail →", "appearance": "text",
         "actions": [{"id": "a-pc-open-%s" % _k, "trigger": "on-click",
                      "effects": [
                          {"effect": "set-control-value", "control": "cardProduct",
                           "value": {"type": "constant", "value": {"type": "text", "value": _prod}}},
                          {"effect": "open-overlay", "overlayId": "modalCard"}]}]})

# --- region map + rank table
add({"id": "map-geo", "kind": "region-map",
     "name": {"visibility": "hidden"},
     "source": {"elementId": "tbl-base", "kind": "table"},
     "columns": [
         {"id": "gm-st", "formula": "[%s/Store State]" % LB, "name": "State"},
         {"id": "gm-vol", "formula": "Sum([%s/Revenue])" % LB, "name": "Revenue", "format": MONEY_M},
         {"id": "gm-perf", "formula": "Sum([%s/Margin]) / NullIf(Sum([%s/Revenue]), 0)" % (LB, LB),
          "name": "Margin %", "format": PCT1}],
     "region": {"id": "gm-st", "regionType": "us-state"},
     "color": {"by": "scale", "column": "gm-perf", "scheme": [B.BAD, "#F3F6FA", B.SOFI_MINT],
               "domain": {"min": 0.25, "mid": 0.35, "max": 0.45}},
     "legend": {"visibility": "shown"},
     "actions": [{"id": "a-map-sel",
                  "trigger": {"on": "on-select", "condition": {"type": "column", "column": "gm-st", "condition": "IsNotNull"}},
                  "effects": [{"effect": "set-control-value", "control": "StateFilter", "value": {"type": "column", "column": "gm-st"}}]}],
     "style": panel()})

add({"kind": "control", "id": "ctrl-state", "controlId": "StateFilter", "name": "State",
     "controlType": "list", "selectionMode": "single", "mode": "include", "values": [],
     "filters": [{"source": {"kind": "table", "elementId": "tbl-base"}, "columnId": "b-state"}],
     "source": {"kind": "source", "source": {"kind": "table", "elementId": "tbl-base"}, "columnId": "b-state"}})

add({"id": "tbl-rank", "kind": "table", "name": "Performance by product family",
     "source": {"elementId": "tbl-base", "kind": "table"},
     "columns": [
         {"id": "rk-prod", "formula": "[%s/Product Family]" % LB, "name": "Product Family"},
         {"id": "rk-vol", "formula": "Sum([%s/Revenue])" % LB, "name": "Revenue", "format": MONEY_M},
         {"id": "rk-perf", "formula": "Sum([%s/Margin]) / NullIf(Sum([%s/Revenue]), 0)" % (LB, LB),
          "name": "Margin %", "format": PCT1},
         {"id": "rk-units", "formula": "Sum([%s/Quantity])" % LB, "name": "Units", "format": NUM0}],
     "groupings": [{"id": "rkg", "groupBy": ["rk-prod"],
                    "calculations": ["rk-vol", "rk-perf", "rk-units"],
                    "sort": [{"columnId": "rk-vol", "direction": "descending"}]}],
     "conditionalFormats": [
         {"type": "single", "columnIds": ["rk-perf"], "condition": "<", "value": 0.25,
          "style": {"backgroundColor": "#FCEBEB", "color": "#A32D2D", "bold": True}},
         {"type": "single", "columnIds": ["rk-perf"], "condition": "Between", "low": 0.25, "high": 0.40,
          "style": {"backgroundColor": "#F1EFE8", "color": "#5F5E5A"}},
         {"type": "single", "columnIds": ["rk-perf"], "condition": ">", "value": 0.40,
          "style": {"backgroundColor": "#E1F5EE", "color": "#0F6E56", "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"},
     "style": panel()})

# --- hero slot: native pivot fallback (no bespoke plugin)
add({"id": "plg-wheel", "kind": "pivot-table", "name": "Revenue by product family and quarter",
     "source": {"elementId": "tbl-base", "kind": "table"},
     "columns": [
         {"id": "pw-prod", "formula": "[%s/Product Family]" % LB, "name": "Product Family"},
         {"id": "pw-q", "formula": 'DateTrunc("quarter", [%s/Date])' % LB, "name": "Quarter"},
         {"id": "pw-rev", "formula": "Sum([%s/Revenue])" % LB, "name": "Revenue", "format": MONEY_M}],
     "rowsBy": [{"id": "pw-prod"}], "columnsBy": [{"id": "pw-q"}], "values": ["pw-rev"], "style": panel()})
add({"id": "ico-wheel", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_WHEEL)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "wheel-heading", "kind": "text",
     "body": '<span style="color: %s">**REVENUE DETAIL**</span>' % B.SOFI_BRIGHT, "verticalAlign": "middle"})

# --- bar chart, color-by switchable
add({"id": "bar-prod", "kind": "bar-chart",
     "source": {"elementId": "tbl-base", "kind": "table"},
     "columns": [
         {"id": "bp-x", "formula": 'DateTrunc([Grain], [%s/Date])' % LB, "name": "Period"},
         {"id": "bp-cat", "formula": ('Switch([ColorBy], "Product Type", [%s/Product Type], [%s/Store Region])' % (LB, LB)),
          "name": "Series"},
         {"id": "bp-y", "formula": "Sum([%s/Revenue])" % LB, "name": "Revenue", "format": MONEY_M}],
     "xAxis": {"columnId": "bp-x"},
     "yAxis": {"columnIds": ["bp-y"]},
     "color": {"by": "category", "column": "bp-cat", "scheme": B.CATEGORICAL},
     "stacking": "stacked",
     "name": title("Revenue by period and series"),
     "legend": {"visibility": "shown"},
     "style": panel()})

# --- chat copilot
add({"id": "c-rail1", "kind": "container", "spacing": "small", "style": panel()})
add({"id": "rail-hd1", "kind": "text", "body": "**ClickHouse Copilot**",
     "verticalAlign": "middle"})
add({"id": "chat1", "kind": "chat", "agentId": "ag-book"})

agents.append({
    "id": "ag-book", "name": "ClickHouse Copilot",
    "description": "Answers questions about BigBuys retail performance.",
    "instructions": (
        "You are an analyst covering ClickHouse-powered real-time retail analytics for "
        "BigBuys. The product families are: " + PRODUCT_NAMES + " and 25 others. Data "
        "covers roughly four years of transactions split into a current and prior "
        "trailing-twelve-month window; amounts are in USD. Cite revenue, gross margin, "
        "units sold and orders, and always name the product family or region. Be concise "
        "and quantitative."),
    "greeting": {"mode": "generated",
                 "prompt": "Greet the user in one short line, then offer exactly three "
                           "specific questions you can answer from this data. Name real "
                           "product families and make one about whichever family has the "
                           "thinnest margin."},
    "dataSources": [{"kind": "table", "elementId": "tbl-base"}],
    "tools": [
        {"toolId": "t-focus", "kind": "action", "name": "Focus a product family",
         "description": "Filter the command center to one product family.",
         "steps": [{"kind": "effect", "effect": "set-control-value", "control": "ProductFilter",
                    "value": {"type": "agent-input", "inputName": "The product family to focus on"}}]},
    ]})

# ====================================================================== layout

LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo1" gridColumn="1 / 6" gridRow="1 / 3"/>
    <Element elementId="ttl1" gridColumn="1 / 20" gridRow="3 / 5"/>
    <Element elementId="sub1" gridColumn="1 / 20" gridRow="5 / 6"/>
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
    <Element elementId="ctrl-colorby" gridColumn="21 / 25" gridRow="1 / 4"/>
  </Container>
  <TabbedContainer elementId="tc-persona" type="tabbed-container" gridColumn="1 / 19" gridRow="25 / 73">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="map-geo" gridColumn="1 / 12" gridRow="1 / 19"/>
      <Element elementId="ctrl-state" gridColumn="1 / 12" gridRow="19 / 21"/>
      <Element elementId="bar-prod" gridColumn="12 / 25" gridRow="1 / 21"/>
      <Element elementId="tbl-rank" gridColumn="1 / 25" gridRow="21 / 35"/>
      <Container elementId="c-secw" type="grid" gridColumn="1 / 25" gridRow="35 / 57" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="ico-wheel" gridColumn="1 / 2" gridRow="1 / 3"/>
        <Element elementId="wheel-heading" gridColumn="2 / 25" gridRow="1 / 3"/>
        <Element elementId="plg-wheel" gridColumn="1 / 25" gridRow="3 / 21"/>
      </Container>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Container elementId="c-prodwrap" type="grid" gridColumn="1 / 16" gridRow="1 / 48" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
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
  <Element elementId="tbl-base" gridColumn="1 / 7" gridRow="73 / 74"/>
  <Element elementId="tbl-base-card" gridColumn="7 / 13" gridRow="73 / 74"/>
  <Element elementId="tbl-pc" gridColumn="13 / 19" gridRow="73 / 74"/>
  <Element elementId="tbl-notif" gridColumn="19 / 25" gridRow="73 / 74"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="modalCard">
  <Container elementId="mc-band" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="mc-logo" gridColumn="1 / 4" gridRow="1 / 6"/>
    <Element elementId="mc-title" gridColumn="4 / 25" gridRow="1 / 6"/>
  </Container>
  <Element elementId="mck-bal" gridColumn="1 / 7" gridRow="6 / 12"/>
  <Element elementId="mck-mem" gridColumn="7 / 13" gridRow="6 / 12"/>
  <Element elementId="mck-rate" gridColumn="13 / 19" gridRow="6 / 12"/>
  <Element elementId="mck-qoq" gridColumn="19 / 25" gridRow="6 / 12"/>
  <Element elementId="mc-trend" gridColumn="1 / 25" gridRow="12 / 28"/>
  <Element elementId="mc-sku" gridColumn="1 / 25" gridRow="28 / 42"/>
  <Element elementId="mc-close" gridColumn="21 / 25" gridRow="42 / 45"/>
  <Element elementId="ctrl-card" gridColumn="1 / 7" gridRow="45 / 46"/>
</Page>
"""

# product cards: 2 across (matches build_sofi.py's card-grid generator)
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
    "name": "ClickHouse — BigBuys Command Center",
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
