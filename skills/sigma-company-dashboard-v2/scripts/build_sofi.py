"""Build the SoFi three-page workbook from code.

Exercises the August 2026 code-rep surface, including the kinds that shipped on
2026-08-07 and had never been built from code before:

  * `waterfall-chart`      — net revenue -> contribution profit bridge
  * `repeated-container`   — a card per product (content children only)
  * `progress`             — goal-attainment rings
  * a registered plugin that fetches LIVE US Treasury yields client-side
  * drawer + modal overlays, navigate / select-tab / update-rows / delete-rows /
    open-document, conditional triggers, success toasts, agents with tools

Usage:  python3 build_sofi.py [verify|create|update <workbookId>]
"""

import json
import os
import pathlib
import sys

import brand as B
import company as CO

# The active prospect. Everything company-specific lives in company.py; this is
# the only line that changes to retarget the whole build.
CFG = CO.COMPANIES[os.environ.get("COMPANY", "sofi")]
# Modeler driver column names. Used as BOTH the display label and the formula
# reference key inside the assumptions input table -- see the comment there.
C_VOL = CO.lab(CFG, "col_volume")
C_GROW = CO.lab(CFG, "col_growth")
C_YLD = CO.lab(CFG, "col_yield")
C_CST = CO.lab(CFG, "col_cost")
PRODUCT_NAMES = ", ".join(p[0] for p in CFG["products"])
B.apply(CFG)
import sigmaapi as S

SQL = pathlib.Path(__file__).resolve().parent.parent / "sql"
SPECS = pathlib.Path(__file__).resolve().parent.parent / "specs"
# a fresh git clone has no specs/ (it is gitignored, per-session output) --
# a genuinely new SE hit FileNotFoundError here on the very first cold
# clone-and-build test. Create it once, here, rather than at every write site.
SPECS.mkdir(parents=True, exist_ok=True)
TICKER_PLUGIN_ID = "646412eb-228a-4bb0-850b-9d251c07c404"
FLYWHEEL_PLUGIN_ID = "2119eea0-d740-4ad5-8307-09e452392bb3"
REPORT_ID_FILE = SPECS / ("report_id_%s.txt" % CFG["key"])
# legacy single-file location, kept so SoFi keeps working
REPORT_ID_LEGACY = SPECS / "report_id.txt"
if not REPORT_ID_FILE.exists() and CFG["key"] == "sofi":
    REPORT_ID_FILE = REPORT_ID_LEGACY

MONEY_B = {"kind": "number", "formatString": "$,.2f", "decimalSymbol": ".",
           "digitGroupingSymbol": ",", "digitGroupingSize": [3], "currencySymbol": "$"}
MONEY_M = {"kind": "number", "formatString": "$,.0f", "currencySymbol": "$"}
PCT = {"kind": "number", "formatString": ".2%"}
PCT1 = {"kind": "number", "formatString": ".1%"}
# compact currency: 123092071 -> $123.1M
MONEY_C = {"kind": "number", "formatString": "$,.3s", "currencySymbol": "$"}
NUM0 = {"kind": "number", "formatString": ",.0f", "digitGroupingSymbol": ",",
        "digitGroupingSize": [3]}
NUM1 = {"kind": "number", "formatString": ",.1f"}

LB = CFG.get("base_table", "Loan Book")
RH = "Rate History"
MP = "Member Population"
PC = "Product Cards"
NB = "NIM Bridge"

elements, overlays, agents = [], [], []


def add(el):
    elements.append(el)
    return el["id"]


def cols(names, prefix):
    return [{"id": "%s%d" % (prefix, i), "formula": "[Custom SQL/%s]" % n, "name": n}
            for i, n in enumerate(names)]


def sql_text(filename):
    """Read a SQL file and inject the config's product constants. Two files are
    generated outright (cards, alerts) because they are pure config."""
    if filename == "product_cards.sql":
        return CO.product_cards_sql(CFG)
    if filename == "notifications.sql":
        return CO.notifications_sql(CFG)
    if filename == "product_skus.sql":
        return CO.product_skus_sql(CFG)
    if filename == "geo.sql":
        return CO.geo_sql(CFG)
    if filename == "hub_banks.sql":
        return CO.hub_banks_sql(CFG)
    if filename == "branch_performance.sql":
        return CO.branch_performance_sql(CFG)
    if filename == "daypart_ratings.sql":
        return CO.daypart_ratings_sql(CFG)
    raw = (SQL / filename).read_text()
    if filename == "member_population.sql":
        return CO.population_sql(CFG, raw)
    return (raw.replace("__PRODUCTS__", CO.products_cte(CFG))
               .replace("__STATES__", CO.states_cte(CFG)))


def sql_table(eid, name, filename, colnames, prefix):
    add({"id": eid, "kind": "table", "name": name,
         "source": {"connectionId": S.CONN_SNOWFLAKE, "kind": "sql",
                    "statement": sql_text(filename)},
         "columns": cols(colnames, prefix)})


# ------------------------------------------------------------ data sources

LB_COLS = ["Product", "Product Order", "Balance Type", "State",
           "Performance Index", "Period", "Year", "Quarter",
           "Period Name", "Members (K)", "Originations", "Avg Balances",
           "Interest Income", "Interest Expense", "Net Interest Income", "Fee Income",
           "Net Revenue", "Provision", "Opex", "Contribution Profit",
           "Delinquency Rate", "Yield Pct", "Funding Cost Pct", "Spread Pct"]
RH_COLS = ["Benchmark", "Benchmark Order", "Period", "Rate Pct", "Period Name"]
MP_COLS = ["Member ID", "Primary Product", "Age Band", "Region", "Credit Band",
           "Credit Order", "Products Held", "Tenure Years", "Direct Deposit",
           "Engagement", "Engagement Order", "Total Balances", "Annual Revenue",
           "Attrition Propensity"]
PC_COLS = ["Product", "Product Order", "Tagline", "Balances $B", "Rate Label",
           "Rate Value", "Members M", "Goal Pct", "Status"]
NB_COLS = ["Step", "Step Order", "Amount", "Step Type"]
NT_COLS = ["Alert Key", "Alert Order", "Severity", "Title", "Body", "Age",
           "Owner", "Impact"]

sql_table("tbl-lb", LB, "loan_book.sql", LB_COLS, "a")
sql_table("tbl-rh", RH, "rate_history.sql", RH_COLS, "r")
sql_table("tbl-mp", MP, "member_population.sql", MP_COLS, "m")
sql_table("tbl-pc", PC, "product_cards.sql", PC_COLS, "p")
sql_table("tbl-nb", NB, "nim_bridge.sql", NB_COLS, "n")

# Some hero plugins need a shape the product-card table can't give them (Delta's
# connection banks are hour-of-day). Those declare their own source table in
# PLUGINS[key]["hero_table"] and it gets built here.
HERO_TBL = CO.PLUGINS.get(CFG["key"], {}).get("hero_table")
if HERO_TBL:
    sql_table("tbl-hero", HERO_TBL["name"], HERO_TBL["file"],
              HERO_TBL["cols"], HERO_TBL["prefix"])

SK = "Product SKUs"
SK_COLS = ["Product", "Sub-Product", "Sub-Product Order", "Balances $B",
           "Members K", "Rate Pct", "QoQ Growth Pct", "Status"]
sql_table("tbl-sku", SK, "product_skus.sql", SK_COLS, "k")
# card-scoped clone of the loan book -- same SQL, separate element, so the
# baseball-card control filters this and nothing else
LBC = "%s (Card)" % LB
sql_table("tbl-lbc", LBC, "loan_book.sql", LB_COLS, "z")


# ------------------------------------------------------------------ helpers

def panel():
    return {"backgroundColor": B.CARD, "borderRadius": "round",
            "borderColor": B.BORDER, "borderWidth": 1}


def tight(style):
    """Container style + small spacing. Applied to every layout container so the
    gutters read app-tight instead of report-loose."""
    return dict(style)


def title(text, size=14):
    return {"text": text, "color": B.TEXT_DARK, "fontWeight": "bold", "fontSize": size}


def stmt_button(idx):
    """The statement-report button, for a header's `buttons` list. Was page-1
    only; every page gets it now so the report is reachable regardless of
    which page a viewer lands on. Element/action ids are suffixed by page
    index -- ids are workbook-unique, so "btn-stmt" can't be reused as-is."""
    if not (CO.has_statement(CFG) and REPORT_ID_FILE.exists()
            and REPORT_ID_FILE.read_text().strip()):
        return []
    return [{"id": "btn-stmt%d" % idx, "kind": "button",
             "text": CO.statement(CFG, "button_label"), "appearance": "filled",
             "actions": [{"id": "a-stmt%d" % idx, "trigger": "on-click",
                          "effects": [{"effect": "open-document",
                                       "documentId": REPORT_ID_FILE.read_text().strip(),
                                       "documentType": "report",
                                       "openTarget": "_blank"}]}]}]


def header(idx, head, subtitle, buttons, titles=True):
    """Brand band. `titles=False` gives the compact chrome-only variant --
    logo + navigation + actions, with the page name carried by the nav pill
    instead of an H1. That is what leaves room for the live ticker inside the
    band rather than as a separate strip under it."""
    cid = "c-hdr%d" % idx
    add({"id": cid, "kind": "container", "spacing": "small",
         "style": {"backgroundColor": B.NAVY, "borderRadius": "round", "padding": "none"},
         "backgroundImage": {"source": {"kind": "url", "url": B.header_bg()},
                             "style": {"fit": "cover"}}})
    # The published skill documents a bare `url` on image, but the deployed API
    # requires the `source` envelope. Verified against staging 2026-08-08.
    add({"id": "logo%d" % idx, "kind": "image",
         "source": {"kind": "url", "url": B.logo_white()},
         # "backgroundColor": "transparent" is invalid on an image element's
         # style (same restriction as plugin.style -- must be a real hex or
         # omitted). Verified against staging 2026-08-14: "Invalid kind:
         # 'image'" is the misleading error for this.
         "style": B.logo_img_style()})
    # element-level style.color is ignored on text -- colour has to be inline
    # HTML inside the markdown body, or the text renders theme-dark on the
    # dark header and disappears.
    if titles:
        add({"id": "ttl%d" % idx, "kind": "text",
             "body": '# **<span style="color: #FFFFFF">%s</span>**' % head,
             "style": {"backgroundColor": "transparent", "padding": "none"},
             "verticalAlign": "end"})
        add({"id": "sub%d" % idx, "kind": "text",
             "body": '<span style="color: #C7E4F7">%s</span>' % subtitle,
             "style": {"backgroundColor": "transparent", "padding": "none"},
             "verticalAlign": "start"})
    for b in buttons:
        add(b)


def nav_el(idx):
    """A real `navigation` element instead of one button per page. `manual`
    keeps the order curated and leaves out the hidden Data page. One instance
    per page -- element ids are workbook-unique, so the nav can't be shared."""
    return {"id": "nav-main%d" % idx, "kind": "navigation", "mode": "manual",
            "showIcons": False,
            # `backgroundColor: "transparent"` is invalid on a navigation
            # element's style (same restriction as image/plugin). Verified
            # against staging 2026-08-14: "Invalid kind: 'navigation'" is the
            # misleading error. Omitting the field renders transparent anyway.
            "optionStyle": {"textColor": "#C7E4F7", "selectedColor": "#FFFFFF",
                            "style": "pill", "orientation": "horizontal"},
            "options": [
                {"label": "Command Center", "destination": {"type": "page", "pageId": "pg1"}},
                {"label": CO.lab(CFG, "modeler_page"), "destination": {"type": "page", "pageId": "pg2"}},
                {"label": CO.lab(CFG, "cohort_page"), "destination": {"type": "page", "pageId": "pg3"}}]}


def nav_button(bid, text, page, appearance="filled"):
    # `outline` renders as dark-on-dark against the gradient header; give the
    # nav buttons an explicit fill/font colour instead.
    return {"id": bid, "kind": "button", "text": text, "appearance": appearance,
            "fillColor": "#FFFFFF", "fontColor": "#0B2740",
            "actions": [{"id": "a-" + bid, "trigger": "on-click",
                         "effects": [{"effect": "navigate",
                                      "target": {"type": "page", "page": page}}]}]}


def kpi_card(key, label, cur, pri, fmt, ga, gb, spark):
    """Matches the reference card() in sigma-company-dashboard's
    build_company_command_center.py. The thing that makes it read as a real KPI
    card is that the CURRENT kpi carries `comparisonColumn` + `comparison`, so
    it renders a delta-vs-prior badge. Dropping that is the regression Connor
    keeps catching -- two bare numbers side by side is not a comparative KPI.
    Titles and period labels are the kpi-chart's OWN native `name` (colourable
    white), never separate text tiles or SVG images."""
    add({"id": "c-%s" % key, "kind": "container", "spacing": "small",
         "style": {"borderRadius": "round", "padding": "none"},
         "backgroundImage": {"source": {"kind": "url", "url": B.card_gradient(ga, gb)},
                             "style": {"fit": "cover"}}})
    add({"id": "kc-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-lb", "kind": "table"},
         "columns": [{"id": "vc-%s" % key, "formula": cur, "name": label, "format": fmt},
                     {"id": "vk-%s" % key, "formula": pri, "name": "Prior TTM",
                      "format": fmt}],
         "value": {"columnId": "vc-%s" % key, "color": "#FFFFFF", "fontSize": 26},
         "comparisonColumn": {"columnId": "vk-%s" % key},
         "comparison": {"display": "delta", "colorGood": "#CDEBB8",
                        "colorBad": "#FFCFC7", "fontSize": 13},
         "name": {"text": label, "color": "#FFFFFF", "fontSize": 12},
         "layout": {"anchor": "middle"},
         # kpi-chart can't be made transparent -- backgroundColor:"transparent"
         # is rejected (see build_sofi.py history), and omitting the field
         # renders OPAQUE WHITE, not see-through. That silently hid the
         # parent container's gradient behind two solid-white tiles on every
         # company built with this generator. Give the tile its own solid
         # fill instead of relying on transparency.
         "style": {"padding": "none", "backgroundColor": ga}})
    add({"id": "kp-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-lb", "kind": "table"},
         "columns": [{"id": "vp-%s" % key, "formula": pri, "name": "Prior TTM",
                      "format": fmt}],
         "value": {"columnId": "vp-%s" % key, "color": "#FFFFFF", "fontSize": 22},
         "name": {"text": "Prior TTM", "color": "#FFFFFF", "fontSize": 13},
         "layout": {"anchor": "middle"},
         "style": {"padding": "none", "backgroundColor": gb}})
    add({"id": "sp-%s" % key, "kind": "line-chart",
         "source": {"elementId": "tbl-lb", "kind": "table"},
         "columns": [{"id": "spx-%s" % key, "formula": "[%s/Period]" % LB, "name": "Period"},
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


def text_control(eid, cid, name):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "text", "mode": "equals", "case": "insensitive",
            "includeNulls": "when-no-value-is-selected", "showOperators": False}


def segmented_control(eid, cid, name, values):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "segmented",
            "source": {"kind": "manual", "valueType": "text", "values": values},
            "value": None}


def number_range_control(eid, cid, name, element_id, column_id):
    return {"kind": "control", "id": eid, "controlId": cid, "name": name,
            "controlType": "number-range",
            "filters": [{"source": {"kind": "table", "elementId": element_id},
                         "columnId": column_id}]}


def cur_(col):
    return 'SumIf([{t}/{c}], [{t}/Period Name] = "Current Period")'.format(t=LB, c=col)


def pri_(col):
    return 'SumIf([{t}/{c}], [{t}/Period Name] = "Prior Period")'.format(t=LB, c=col)


# ================================================= PAGE 1 — command center

header(1, CFG["title"],
       "Net revenue, margin and %s growth · trailing twelve months vs prior year"
       % CFG["unit_noun"],
       [nav_el(1)] + stmt_button(1),
       titles=False)

# --- the live rates ticker (registered plugin fetching Treasury yields)
# Gate the two plugin slots INDEPENDENTLY. They used to share one flag, so a
# company with a hero plugin but no sensible ticker (Nuvia — there is no
# commodity feed for dental implants) silently lost its hero too.
NO_TICKER = CO.plugin(CFG, "ticker") is None
NO_HERO = CO.plugin(CFG, "hero") is None
if NO_TICKER:
    # a native marker strip instead of the live ticker
    add({"id": "plg-ticker", "kind": "text",
         "body": '<span style="color: %s">**%s** · trailing twelve months vs prior year</span>'
                 % (B.NAVY, CFG["name"].upper()),
         "style": {"backgroundColor": "transparent", "borderRadius": "round"},
         "verticalAlign": "middle"})
else:
    add({"id": "plg-ticker", "kind": "plugin", "pluginId": CO.plugin(CFG, "ticker"),
         "displayName": "Market rates",
         "config": {"source": {"kind": "element", "elementId": "tbl-rh"},
                    "benchmark": "r0", "rate": "r3", "period": "r2"},
         # plugin style accepts backgroundColor only and must be a HEX
         "style": {"backgroundColor": B.NAVY}})


# ------------------------------------------- the product "baseball card" modal
# Clicking a product card sets a control to that product, then opens the modal.
# Every element inside reads a card-scoped source filtered by that control, so
# one modal serves all six products instead of six near-identical overlays.
add({"kind": "control", "id": "ctrl-card", "controlId": "cardProduct",
     "name": "Product", "controlType": "list", "selectionMode": "single",
     "mode": "include", "values": [],
     "filters": [{"source": {"kind": "table", "elementId": "tbl-lbc"},
                  "columnId": "z0"},
                 {"source": {"kind": "table", "elementId": "tbl-sku"},
                  "columnId": "k0"}],
     "source": {"kind": "source", "source": {"kind": "table", "elementId": "tbl-sku"},
                "columnId": "k0"}})

overlays.append({"id": "modalCard", "type": "modal", "name": "Product Card",
                 "modal": {"width": "large",
                           # no `header` key at all: an empty title string is
                           # not the same as no header and crashes the overlay
                           "header": {"title": " ", "showCloseIcon": "shown"},
                           "footer": {"primaryCta": {"visible": "hidden"},
                                      "secondaryCta": {"visible": "hidden"}}}})

add({"id": "mc-band", "kind": "container",
     "style": {"backgroundColor": B.NAVY, "borderRadius": "round", "padding": "none"},
     "backgroundImage": {"source": {"kind": "url", "url": B.header_bg()},
                         "style": {"fit": "cover"}}})
add({"id": "mc-logo", "kind": "image", "source": {"kind": "url", "url": B.logo_white()},
     "style": B.logo_img_style()})
add({"id": "mc-title", "kind": "text",
     "body": '## **<span style="color: #FFFFFF">{{[Product SKUs/Product]}}</span>**',
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

for _k, _lab, _f, _fmt in [
        ("bal", "%s ($B)" % CFG["volume_noun"].title(), 'Sum([%s/Balances $B])' % SK, MONEY_B),
        ("mem", ("%ss (K)" % CFG["unit_noun"].title()), 'Sum([%s/Members K])' % SK, NUM1),
        ("rate", "Avg Rate", 'Avg([%s/Rate Pct]) / 100' % SK, PCT1),
        ("qoq", "QoQ Growth", 'Avg([%s/QoQ Growth Pct]) / 100' % SK, PCT1)]:
    add({"id": "mck-%s" % _k, "kind": "kpi-chart",
         "source": {"elementId": "tbl-sku", "kind": "table"},
         "columns": [{"id": "mcv-%s" % _k, "formula": _f, "name": _lab, "format": _fmt}],
         "value": {"columnId": "mcv-%s" % _k, "color": B.NAVY, "fontSize": 26},
         "name": {"text": _lab, "color": B.TEXT_MUTED, "fontSize": 12},
         "layout": {"anchor": "middle"}, "style": panel()})

# trend + rate history, the analytical half of the card
add({"id": "mc-trend", "name": {"visibility": "hidden"}, "kind": "line-chart", "name": "%s & revenue trend" % CFG["volume_noun"].title(),
     "source": {"elementId": "tbl-lbc", "kind": "table"},
     "columns": [{"id": "mct-x", "formula": "[%s/Period]" % LBC, "name": "Period"},
                 {"id": "mct-bal", "formula": "Sum([%s/Avg Balances])" % LBC,
                  "name": "Avg Balances ($M)", "format": MONEY_M},
                 {"id": "mct-rev", "formula": "Sum([%s/Net Revenue])" % LBC,
                  "name": "Net Revenue ($M)", "format": MONEY_M}],
     "xAxis": {"columnId": "mct-x"},
     "yAxis": {"columnIds": ["mct-bal", "mct-rev"]},
     "stacking": "none",
     "colorAssignment": {"palette": {"scheme": [B.SOFI_BRIGHT, B.SOFI_MINT],
                                     "type": "categorical"}},
     "legend": {"visibility": "shown"},
     "lineAreaStyle": {"interpolation": "monotone"},
     "style": panel()})

add({"id": "mc-sku", "name": {"visibility": "hidden"}, "kind": "table", "name": "Sub-products",
     "source": {"elementId": "tbl-sku", "kind": "table"},
     "columns": [
         {"id": "mcs-name", "formula": "[%s/Sub-Product]" % SK, "name": "Sub-product"},
         {"id": "mcs-bal", "formula": "[%s/Balances $B]" % SK, "name": "Balances ($B)",
          "format": MONEY_B},
         {"id": "mcs-mem", "formula": "[%s/Members K]" % SK, "name": ("%ss (K)" % CFG["unit_noun"].title()),
          "format": NUM1},
         {"id": "mcs-rate", "formula": "[%s/Rate Pct]" % SK, "name": "Rate %"},
         {"id": "mcs-qoq", "formula": "[%s/QoQ Growth Pct]" % SK, "name": "QoQ %"},
         {"id": "mcs-status", "formula": "[%s/Status]" % SK, "name": "Status"}],
     "sort": [{"columnId": "mcs-bal", "direction": "descending"}],
     # status chips + signed growth, so the table is scannable instead of a
     # wall of numbers you have to read row by row
     "conditionalFormats": [
         {"type": "single", "columnIds": ["mcs-status"], "condition": "=",
          "value": "Ahead",
          "style": {"backgroundColor": "#E1F5EE", "color": "#0F6E56", "bold": True}},
         {"type": "single", "columnIds": ["mcs-status"], "condition": "=",
          "value": "On plan",
          "style": {"backgroundColor": "#E6F1FB", "color": "#185FA5"}},
         {"type": "single", "columnIds": ["mcs-status"], "condition": "=",
          "value": "Behind",
          "style": {"backgroundColor": "#FCEBEB", "color": "#A32D2D", "bold": True}},
         {"type": "single", "columnIds": ["mcs-qoq"], "condition": "<",
          "value": 0, "style": {"color": "#A32D2D", "bold": True}},
         {"type": "single", "columnIds": ["mcs-qoq"], "condition": ">=",
          "value": 5, "style": {"color": "#0F6E56", "bold": True}}],
     "style": panel()})

add({"id": "mc-close", "kind": "button", "text": "Close", "appearance": "outline",
     "actions": [{"id": "a-mc-close", "trigger": "on-click",
                  "effects": [{"effect": "close-overlay"}]}]})
add({"id": "mc-model", "kind": "button",
     "text": "Model in %s →" % CO.lab(CFG, "modeler_page"),
     "appearance": "filled",
     "actions": [{"id": "a-mc-model", "trigger": "on-click",
                  "effects": [
                      {"effect": "close-overlay"},
                      # scope the page to the product you drilled into...
                      {"effect": "set-control-value", "control": "ProductFilter",
                       "value": {"type": "control", "control": "cardProduct"}},
                      # ...then land on Finance with that row ready to edit
                      {"effect": "navigate",
                       "target": {"type": "page", "page": "pg2"}}]}]})

add({"id": "tc-persona", "kind": "tabbed-container",
     "tabs": [{"name": n} for n in CO.lab(CFG, "personas")],
     "tabBar": {"alignment": "start"}})
# NOTE: no separate persona buttons. The tabbed container renders its own tab
# bar, so a second set of select-tab buttons is a duplicate control that can
# fall out of sync with it. The tab bar IS the persona switcher -- it needs no
# "VIEW AS" label either, which only cost vertical space.


# ---------------------------------------------------------- notification rail
# Severity-driven alert cards, one per row via MaxIf -- same construction as the
# product cards, because `repeated-container` still cannot bind per-card.
NT = "Notifications"
sql_table("tbl-notif", NT, "notifications.sql", NT_COLS, "q")

_ICON_ALERT = ('<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>'
               '<line x1="12" y1="16" x2="12.01" y2="16"/>')
_ICON_WARN = ('<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86'
              'a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/>'
              '<line x1="12" y1="17" x2="12.01" y2="17"/>')
_ICON_INFO = ('<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/>'
              '<line x1="12" y1="8" x2="12.01" y2="8"/>')
ICON_BELL = ('<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
             '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>')

_SEV = {"critical": (B.BAD, _ICON_ALERT, "#FCEBEB", "#F09595", "#501313", "#791F1F"),
        "warning":  (B.WARN, _ICON_WARN, "#FAEEDA", "#EF9F27", "#412402", "#633806"),
        "info":     (B.SOFI_BRIGHT, _ICON_INFO, "#E6F1FB", "#85B7EB", "#042C53", "#0C447C")}
# (order, severity, impact caption). The impact kpi is not decoration: a `text`
# element has no `source`, so a {{...}} formula inside one only resolves when a
# SOURCED data element shares its container.
ALERTS = [(i + 1, al[0], al[6]) for i, al in enumerate(CFG["alerts"])]


def _nt(col, order):
    """Row-scoped lookup keyed on a TEXT column, exactly like the product cards."""
    return 'MaxIf([{t}/{c}], [{t}/Alert Key] = "a{o}")'.format(t=NT, c=col, o=order)


add({"id": "c-prodwrap", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": B.CARD, "borderRadius": "round",
               "borderColor": B.BORDER, "borderWidth": 1}})
add({"id": "c-secn", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": B.CARD, "borderRadius": "round",
               "borderColor": B.BORDER, "borderWidth": 1}})
add({"id": "ico-notif", "kind": "image",
     "source": {"kind": "url", "url": B.icon(ICON_BELL)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "notif-heading", "kind": "text",
     "body": '<span style="color: %s">**NOTIFICATIONS**</span>' % B.SOFI_BRIGHT,
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

for _o, _sev, _cap in ALERTS:
    _c, _g, _tint, _bd, _body, _meta = _SEV[_sev]
    _k = "n%d" % _o
    add({"id": "ncard-%s" % _k, "kind": "container",
         # borderWidth/borderColor require default padding -- pairing them with
         # padding:"none" is a hard rejection
         "style": {"backgroundColor": _tint, "borderRadius": "round",
                   "borderColor": _bd, "borderWidth": 1}})
    add({"id": "nico-%s" % _k, "kind": "image",
         "source": {"kind": "url", "url": B.icon(_g, _c, 20)},
         "style": {"fit": "contain", "align": "start", "padding": "none"}})
    # static severity chip: guarantees the card has intrinsic height, which is
    # how the product cards get theirs (their heading is static too)
    add({"id": "nsev-%s" % _k, "kind": "text",
         "body": '<span style="color: %s">%s</span>' % (_c, _sev.upper()),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "middle"})
    add({"id": "ntitle-%s" % _k, "kind": "text",
         "body": '<span style="color: %s">**{{%s}}**</span>' % (_c, _nt("Title", _o)),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "middle"})
    add({"id": "nbody-%s" % _k, "kind": "text",
         "body": '<span style="color: %s">{{%s}}</span>' % (_body, _nt("Body", _o)),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "start"})
    add({"id": "nkpi-%s" % _k, "kind": "kpi-chart",
         "source": {"elementId": "tbl-notif", "kind": "table"},
         "columns": [{"id": "nkv-%s" % _k, "formula": _nt("Impact", _o),
                      "name": _cap, "format": NUM0}],
         "value": {"columnId": "nkv-%s" % _k, "color": _c, "fontSize": 20},
         "name": {"text": _cap, "color": _meta, "fontSize": 10},
         "layout": {"anchor": "start"},
         "style": {"padding": "none"}})
    add({"id": "nmeta-%s" % _k, "kind": "text",
         "body": '<span style="color: %s">{{%s}} · {{%s}}</span>'
                 % (_meta, _nt("Owner", _o), _nt("Age", _o)),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "end"})


# --- the Cold Provisions overview pair: a map you scan for the outlier, and a
# ranked list you act on. The bar chart it replaces showed size but not
# direction, and nothing was clickable.
add({"id": "map-geo", "kind": "region-map",
     # element name hidden: it printed on top of the colour legend
     "name": {"visibility": "hidden"},
     "source": {"elementId": "tbl-lb", "kind": "table"},
     "columns": [
         {"id": "gm-st", "formula": "[%s/State]" % LB, "name": "State"},
         {"id": "gm-vol", "formula": "Sum([%s/Net Revenue])" % LB, "name": CO.lab(CFG, "kpi_revenue").split(" (")[0],
          "format": MONEY_M},
         {"id": "gm-perf", "formula": "Avg([%s/Performance Index])" % LB,
          "name": "Performance vs plan", "format": PCT1}],
     "region": {"id": "gm-st", "regionType": "us-state"},
     # shaded by performance against plan, not raw volume: a big state is not
     # news, a big state that is UNDERPERFORMING is
     # continuous scale centred on 1.0 = exactly on plan, so under-plan states
     # read red and over-plan read green without any manual banding
     "color": {"by": "scale", "column": "gm-perf",
               "scheme": [B.BAD, "#F3F6FA", B.SOFI_MINT],
               "domain": {"min": 0.85, "mid": 1.0, "max": 1.15}},
     "legend": {"visibility": "shown"},
     "actions": [{"id": "a-map-sel",
                  "trigger": {"on": "on-select",
                              "condition": {"type": "column", "columnId": "gm-st",
                                            "condition": "IsNotNull"}},
                  "effects": [{"effect": "set-control-value", "control": "StateFilter",
                               "value": {"type": "column", "columnId": "gm-st"}}]}],
     "style": panel()})

add({"kind": "control", "id": "ctrl-state", "controlId": "StateFilter",
     "name": "State", "controlType": "list", "selectionMode": "single",
     "mode": "include", "values": [],
     # filters BOTH the footprint and the loan book, so clicking a state on the
     # map rescopes the bar chart beside it rather than only the map's own table
     "filters": [{"source": {"kind": "table", "elementId": "tbl-lb"},
                  "columnId": "a3"}],
     "source": {"kind": "source", "source": {"kind": "table", "elementId": "tbl-lb"},
                "columnId": "a3"}})

add({"id": "tbl-rank", "kind": "table",
     "name": "Performance by %s" % CO.lab(CFG, "seg_product").lower(),
     "source": {"elementId": "tbl-lb", "kind": "table"},
     "columns": [
         {"id": "rk-prod", "formula": "[%s/Product]" % LB,
          "name": CO.lab(CFG, "seg_product")},
         {"id": "rk-vol", "formula": "Sum([%s/Net Revenue])" % LB, "name": CO.lab(CFG, "kpi_revenue").split(" (")[0],
          "format": MONEY_M},
         {"id": "rk-perf", "formula": "Avg([%s/Performance Index])" % LB,
          "name": "vs plan", "format": PCT1},
         {"id": "rk-spread", "formula": "Avg([%s/Spread Pct])" % LB,
          "name": "Spread %", "format": {"kind": "number", "formatString": ",.2f",
                                          "suffix": "%"}}],
     "groupings": [{"id": "rkg", "groupBy": ["rk-prod"],
                    "calculations": ["rk-vol", "rk-perf", "rk-spread"],
                    "sort": [{"columnId": "rk-vol", "direction": "descending"}]}],
     "conditionalFormats": [
         {"type": "single", "columnIds": ["rk-perf"], "condition": "<", "value": 0.98,
          "style": {"backgroundColor": "#FCEBEB", "color": "#A32D2D", "bold": True}},
         {"type": "single", "columnIds": ["rk-perf"], "condition": "Between",
          "low": 0.98, "high": 1.02,
          "style": {"backgroundColor": "#F1EFE8", "color": "#5F5E5A"}},
         {"type": "single", "columnIds": ["rk-perf"], "condition": ">", "value": 1.02,
          "style": {"backgroundColor": "#E1F5EE", "color": "#0F6E56", "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"},
     "style": panel()})


# --- the hero plugin (bespoke, bound to the product card table)
if NO_HERO:
    # native stand-in for the hero plugin: sector x hold-period contribution
    add({"id": "plg-wheel", "kind": "pivot-table",
         "name": "%s by %s and quarter" % (CO.lab(CFG, "kpi_revenue").split(" (")[0],
                                           CO.lab(CFG, "seg_product").lower()),
         "source": {"elementId": "tbl-lb", "kind": "table"},
         "columns": [
             {"id": "pw-prod", "formula": "[%s/Product]" % LB,
              "name": CO.lab(CFG, "seg_product")},
             {"id": "pw-q", "formula": "[%s/Quarter]" % LB, "name": "Quarter"},
             {"id": "pw-rev", "formula": "Sum([%s/Net Revenue])" % LB,
              "name": CO.lab(CFG, "kpi_revenue"), "format": MONEY_M}],
         "rowsBy": [{"id": "pw-prod"}], "columnsBy": [{"id": "pw-q"}],
         "values": ["pw-rev"], "style": panel()})
else:
    _hsrc = "tbl-hero" if HERO_TBL else "tbl-pc"
    _hcfg = CO.PLUGINS.get(CFG["key"], {}).get("hero_config") or {
        "product": "p0", "balance": "p3", "members": "p6", "goal": "p7"}
    add({"id": "plg-wheel", "kind": "plugin", "pluginId": CO.plugin(CFG, "hero"),
         "displayName": CO.plugin(CFG, "hero_label") or "Balance flywheel",
         "config": dict({"source": {"kind": "element", "elementId": _hsrc}},
                        **_hcfg),
         "style": {"backgroundColor": B.CARD}})

    # --- filters

add({"id": "c-filters", "kind": "container", "spacing": "small", "style": panel()})
add(date_control("ctrl-date", "Period", "Period", "tbl-lb", "a3"))
add(list_control("ctrl-product", "ProductFilter", "Product", "tbl-lb", "a0",
                 # reach the modeler spine too: sbase -> spivot -> assum -> book
                 extra_filters=[{"source": {"kind": "table", "elementId": "sbase"},
                                 "columnId": "sb-prod"},
                                {"source": {"kind": "table", "elementId": "tbl-pc"},
                                 "columnId": "p0"},
                                {"source": {"kind": "table", "elementId": "tbl-sku"},
                                 "columnId": "k0"}]))
add(dict(segmented_control("ctrl-grain", "Grain", "Date grain",
                           ["quarter", "month", "week"]), value="month"))
add(dict(segmented_control("ctrl-colorby", "ColorBy", "Color by",
                           [CO.lab(CFG, "seg_product"), "State", CO.lab(CFG, "seg_type")]),
         value=CO.lab(CFG, "seg_product")))

# --- KPI row
kpi_card("rev", CO.lab(CFG, "kpi_revenue"), cur_("Net Revenue"), pri_("Net Revenue"),
         MONEY_M, B.NAVY, B.SOFI_BRIGHT, "Sum([%s/Net Revenue])" % LB)
kpi_card("cp", CO.lab(CFG, "kpi_margin"), cur_("Contribution Profit"),
         pri_("Contribution Profit"), MONEY_M, B.NAVY_DEEP, B.SOFI_CYAN,
         "Sum([%s/Contribution Profit])" % LB)
kpi_card("bal", CO.lab(CFG, "kpi_volume"),
         'SumIf([{t}/Avg Balances], [{t}/Period Name] = "Current Period") / 12'.format(t=LB),
         'SumIf([{t}/Avg Balances], [{t}/Period Name] = "Prior Period") / 12'.format(t=LB),
         MONEY_M, B.NAVY_DEEP, B.SOFI_BLUE,
         'SumIf([{t}/Avg Balances], [{t}/Balance Type] = "Loans")'.format(t=LB))
kpi_card("mem", CO.lab(CFG, "kpi_units"),
         'MaxIf([{t}/Members (K)], [{t}/Period Name] = "Current Period")'.format(t=LB),
         'MaxIf([{t}/Members (K)], [{t}/Period Name] = "Prior Period")'.format(t=LB),
         NUM0, B.NAVY_DEEP, B.SOFI_MINT, "Sum([%s/Members (K)])" % LB)

# --- AI insight
# The AI insight lives in the rail beside the copilot -- it's an AI surface, and
# as a full-width body slab it pushed everything else down the page.
add({"id": "c-strip", "kind": "container",
     "style": {"backgroundColor": B.CARD_ALT, "borderRadius": "round",
               "borderColor": B.BORDER, "borderWidth": 1}})
add({"id": "ico-ai", "kind": "image", "source": {"kind": "url", "url": B.icon(B.ICON_SPARK)},
     "style": {"fit": "contain", "padding": "none"}})
# NOTE: never build a {{...}} body with str.format() -- `{{` is format's escape
# for a literal brace, so the dynamic-text markers collapse to `{...}` and Sigma
# stores the whole thing as escaped literal text. Use %-substitution.
# The insight is only as good as what it is handed. Feeding three totals gets
# "revenue grew, watch margin" -- true, useless, and already on screen above it.
# Give it product-level movement and it can name the thing that actually moved.
_AI_PROMPT = (
    '"You are an analyst covering ' + CFG["name"] + ' (' + CFG["domain"] + '). '
    'Write TWO sentences, 55-75 words total. First sentence: name the '
    + CO.lab(CFG, "seg_product").lower() + ' '
    'that moved most and quantify the move, and say WHY it moved given the rate and '
    'cost figures below. Second sentence: name the single biggest risk with its number, '
    'and what to do about it. Be specific and use the real names. Do NOT restate '
    'portfolio totals -- they are on screen already. Data: net revenue $" & '
    'Text(Round(SumIf([%(t)s/Net Revenue], [%(t)s/Period Name] = "Current Period") / 1000, 2)) '
    '& "B vs $" & '
    'Text(Round(SumIf([%(t)s/Net Revenue], [%(t)s/Period Name] = "Prior Period") / 1000, 2)) '
    '& "B prior. Contribution margin " & '
    'Text(Round(SumIf([%(t)s/Contribution Profit], [%(t)s/Period Name] = "Current Period") '
    '/ NullIf(SumIf([%(t)s/Net Revenue], [%(t)s/Period Name] = "Current Period"), 0) * 100, 0)) '
    '& "%%. Lines of business: ' + PRODUCT_NAMES + '. ' + CO.lab(CFG, "driver_risk").replace("%", "%%") + ' now " & '
    'Text(Round(AvgIf([%(t)s/Delinquency Rate], [%(t)s/Period Name] = "Current Period") * 100, 2)) '
    '& "%% vs " & '
    'Text(Round(AvgIf([%(t)s/Delinquency Rate], [%(t)s/Period Name] = "Prior Period") * 100, 2)) '
    '& "%% prior. ' + CO.lab(CFG, "driver_cost").replace("%", "%%") + ' " & '
    'Text(Round(AvgIf([%(t)s/Funding Cost Pct], [%(t)s/Period Name] = "Current Period"), 2)) '
    '& "%% vs " & '
    'Text(Round(AvgIf([%(t)s/Funding Cost Pct], [%(t)s/Period Name] = "Prior Period"), 2)) '
    '& "%% prior."'
) % {"t": LB}

add({"id": "txt-ai", "kind": "text",
     "body": '**AI INSIGHT** — {{Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", '
             '"CLAUDE-4-SONNET", ' + _AI_PROMPT + "), '\"', \"\")}}",
     "style": {"backgroundColor": "transparent"},
     "verticalAlign": "middle"})

# --- product cards. Six hand-built cards, one per product, each reading its own
# row via MaxIf. NOT a repeated container: `repeated-container` exposes no `name`
# field, so the repeater-qualified reference its docs require cannot be written
# from code. Taglines are deliberately short enough to stay on ONE line -- a
# wrapping subtitle makes card heights uneven and the rings stop aligning.
PRODUCTS = [("p%d" % (i + 1), pr[0], pr[13])
            for i, pr in enumerate(CFG["products"])]


def _pc(col, product):
    """Row-scoped lookup into the one-row-per-product card table."""
    return 'MaxIf([{t}/{c}], [{t}/Product] = "{p}")'.format(t=PC, c=col, p=product)


for key, product, tagline in PRODUCTS:
    add({"id": "pcard-%s" % key, "kind": "container", "spacing": "small", "style": panel()})
    add({"id": "pc-name-%s" % key, "kind": "text",
         "body": "### %s" % product,
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "middle"})
    add({"id": "pc-tag-%s" % key, "kind": "text",
         "body": '<span style="color: %s">%s</span>' % (B.TEXT_MUTED, tagline),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "start"})
    # the one hero number on the card
    _sc = CO.scale(CFG)
    add({"id": "pc-bal-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-pc", "kind": "table"},
         "columns": [{"id": "pcv-%s" % key,
                      "formula": "(%s) / %d" % (_pc("Balances $B", product),
                                                _sc["div"] // 1000 or 1),
                      "name": "%s (%s)" % (CFG["volume_noun"].title(), _sc["suffix"]),
                      "format": {"kind": "number",
                                 "formatString": "$,.%df" % _sc["dp"],
                                 "suffix": _sc["suffix"], "currencySymbol": "$"}}],
         "value": {"columnId": "pcv-%s" % key, "color": B.SOFI_BRIGHT, "fontSize": 24},
         "name": {"visibility": "hidden"},
         "style": {"padding": "none"},
         "layout": {"anchor": "start"}})
    add({"id": "pc-ring-%s" % key, "kind": "progress",
         # `progress` needs an explicit source. It resolved without one while the
         # cards sat directly on the page; once they moved inside a <Tab> the
         # formula had nothing to bind to and every ring rendered empty.
         "source": {"elementId": "tbl-pc", "kind": "table"},
         "shape": "ring",
         "value": _pc("Goal Pct", product),
         "min": "0", "max": "1",
         # `progress` has no `name`; the caption is config.label
         # VERIFIED 10 Aug 2026 (Marriott build): config.label is the ELEMENT
         # NAME, not the value -- omitting it prints "Progress ring" on every
         # card and the arc STILL renders empty, so `value` is not binding at all
         # inside the <Tab>. `label.visibility: "visible"` is not in the enum
         # either (the PUT comes back `Invalid kind: "progress"`). Kept hidden,
         # which is what every other company ships.
         "config": {"label": {"visibility": "hidden"},
                    "fillColor": B.SOFI_BRIGHT, "trackColor": "#E3EBF4"},
         "style": {"padding": "none"}})
    # one muted supporting line, not a stack of them
    add({"id": "pc-sub-%s" % key, "kind": "text",
         # inline HTML is limited to <u> <sub> <sup> <span> <a> -- <b> is
         # rejected, so emphasis has to be markdown, outside the span
         "body": ('<span style="color: %s">{{%s}}</span> **{{%s}}** '
                  '<span style="color: %s">· {{%s | ,.2f}}M · {{%s}}</span>')
                 % (B.TEXT_MUTED, _pc("Rate Label", product),
                    _pc("Rate Value", product), B.TEXT_MUTED,
                    _pc("Members M", product), _pc("Status", product)),
         "style": {"backgroundColor": "transparent", "padding": "none"},
         "verticalAlign": "end"})

add({"id": "c-secw", "kind": "container", "spacing": "small",
     "style": {"padding": "none"}})
for _k, _prod, _tag in PRODUCTS:
    add({"id": "pc-open-%s" % _k, "kind": "button", "text": "View detail →",
         "appearance": "text",
         "actions": [{"id": "a-pc-open-%s" % _k, "trigger": "on-click",
                      "effects": [
                          {"effect": "set-control-value", "control": "cardProduct",
                           "value": {"type": "constant",
                                     "value": {"type": "text", "value": _prod}}},
                          {"effect": "open-overlay", "overlayId": "modalCard"}]}]})

add({"id": "ico-wheel", "kind": "image",
     "source": {"kind": "url", "url": B.icon(B.ICON_WHEEL)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "wheel-heading", "kind": "text",
     "body": '<span style="color: %s">**%s**</span>' % (B.SOFI_BRIGHT, CO.plugin(CFG, "hero_label") or "PORTFOLIO DETAIL"),
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

add({"id": "ico-prod", "kind": "image",
     "source": {"kind": "url", "url": B.icon(B.ICON_TREND)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "pc-heading", "kind": "text",
     "body": '<span style="color: %s">**PRODUCT PERFORMANCE**</span>' % B.SOFI_BRIGHT,
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

# --- left column is one tabbed container: bridge / trend / detail
add({"id": "bar-prod", "kind": "bar-chart",
     "source": {"elementId": "tbl-lb", "kind": "table"},
     "columns": [
         # x is DateTrunc'd by the grain control, so one chart serves quarter,
         # month and week without three elements
         {"id": "bp-x", "formula": 'DateTrunc([Grain], [%s/Period])' % LB,
          "name": "Period"},
         # colour dimension switches on the Color-by control -- this is what
         # made the Ford chart feel like an app instead of a picture
         {"id": "bp-cat",
          "formula": ('Switch([ColorBy], "State", [{t}/State], '
                      '"%s", [{t}/Balance Type], [{t}/Product])' % CO.lab(CFG, "seg_type")).format(t=LB),
          "name": "Series"},
         {"id": "bp-y", "formula": "Sum([%s/Net Revenue])" % LB,
          "name": CO.lab(CFG, "kpi_revenue"), "format": MONEY_M}],
     "xAxis": {"columnId": "bp-x"},
     "yAxis": {"columnIds": ["bp-y"]},
     "color": {"by": "category", "column": "bp-cat", "scheme": B.CATEGORICAL},
     "stacking": "stacked",
     "name": title("%s by period and series" % CO.lab(CFG, "kpi_revenue").split(" (")[0]),
     "legend": {"visibility": "shown"},
     "style": panel()})

add({"id": "c-rail1", "kind": "container", "spacing": "small", "style": panel()})
add({"id": "rail-hd1", "kind": "text", "body": "**%s Copilot**" % CFG["name"],
     "style": {"color": B.TEXT_DARK, "backgroundColor": "transparent"},
     "verticalAlign": "middle"})
add({"id": "chat1", "kind": "chat", "agentId": "ag-book"})
add({"id": "btn-newscen", "kind": "button", "text": "+ New scenario",
     "appearance": "filled",
     "actions": [{"id": "a-newscen", "trigger": "on-click",
                  "effects": [{"effect": "open-overlay",
                               "overlayId": "modalScenario"}]}]})

# Finance is its own page again: the modeler needs full width, and it competed
# with the Analyst columns inside a tab.
header(2, CO.lab(CFG, "modeler_title"), "", [nav_el(2)] + stmt_button(2), titles=False)

# --- 1. base book: exactly ONE row per product.
# A cross join runs against underlying rows, so a grouped view over the 144-row
# monthly loan book would replicate each product 24 times and inflate every
# downstream sum by 24x. This SQL aggregates to one row per product up front.
add({"id": "sbase", "kind": "table", "name": "Product Base",
     "visibleAsSource": True,
     "source": {"connectionId": S.CONN_SNOWFLAKE, "kind": "sql",
                "statement": sql_text("scenario_base.sql")},
     "columns": [
         {"id": "sb-prod", "formula": "[Custom SQL/Product]", "name": "Product"},
         {"id": "sb-ord", "formula": "[Custom SQL/Product Order]", "name": "Order"},
         {"id": "sb-rev", "formula": "[Custom SQL/Revenue]", "name": "Revenue",
          "format": MONEY_M},
         {"id": "sb-bal", "formula": "[Custom SQL/Balances]", "name": "Balances",
          "format": MONEY_M}],
     "style": panel()})

# --- 2. the scenario list itself (standalone, so rows can be added)
add({"id": "scen2", "kind": "input-table",
     "source": {"kind": "empty", "connectionId": S.CONN_SNOWFLAKE},
     "inputMode": "view", "name": "Scenarios",
     "columns": [
         {"id": "sc-name", "type": "text", "name": "Scenario Name"},
         {"id": "sc-status", "type": "text", "name": "Status",
          "values": ["Draft", "Submitted", "Approved"],
          "pills": "color-by-option"}],
     "style": panel()})

# --- 3. CROSS JOIN base x scenarios. `columns:[{left:"1",right:"1"}]` joins on a
#        constant, which is how you express a cross join here. Coalesce gives a
#        "Base Case" row set when no scenario has been created yet.
add({"id": "spivot", "kind": "pivot-table", "name": "Scenario Pivot",
     "visibleAsSource": True,
     "source": {"kind": "join",
                "joins": [{"left": {"elementId": "sbase", "kind": "table"},
                           "right": {"elementId": "scen2", "kind": "table"},
                           "columns": [{"left": "1", "right": "1"}],
                           "joinType": "left-outer"}],
                "primarySource": {"elementId": "sbase", "kind": "table"}},
     "columns": [
         {"id": "pv-prod", "formula": "[Product Base/Product]", "name": "Product"},
         {"id": "pv-scen", "formula": 'Coalesce([Scenarios/Scenario Name],"Base Case")',
          "name": "Scenario"},
         {"id": "pv-rev", "formula": "Sum([Product Base/Revenue])",
          "name": "Baseline Revenue", "format": MONEY_M},
         {"id": "pv-bal", "formula": "Sum([Product Base/Balances])",
          "name": C_VOL, "format": MONEY_M}],
     "rowsBy": [{"id": "pv-prod"}], "values": ["pv-rev", "pv-bal"],
     "style": panel()})

# --- 4. the editable assumptions, one set per scenario per product.
#        Computed columns live INSIDE the input table and use bare column refs.
add({"id": "assum", "kind": "input-table",
     "source": {"kind": "linked", "from": "spivot"},
     "inputMode": "view", "name": "Assumptions",
     "columns": [
         {"id": "ia-prod", "key": "pv-prod"},
         {"id": "ia-scen", "key": "pv-scen"},
         {"id": "ia-rev", "key": "pv-rev"},
         {"id": "ia-bal", "key": "pv-bal"},
         {"id": "ia-growth", "type": "number", "name": C_GROW},
         {"id": "ia-yield", "type": "number", "name": C_YLD},
         {"id": "ia-fund", "type": "number", "name": C_CST},
         {"id": "ia-prev",
          # An input table's column NAME is its formula reference key, so these
          # interpolate the same constants used above -- renaming one without
          # the other is a "Dependency not found" at create.
          "formula": "[Baseline Revenue] * (1 + Coalesce([%s], 0) / 100) "
                     "+ [Baseline Revenue] * (Coalesce([%s], 0) "
                     "- Coalesce([%s], 0)) / 10000" % (C_GROW, C_YLD, C_CST),
          "name": "Projected Revenue", "format": MONEY_M},
         {"id": "ia-note", "type": "text", "name": "Rationale"}],
     "order": ["ia-scen", "ia-prod", "ia-rev", "ia-growth", "ia-yield", "ia-fund",
               "ia-prev", "ia-note"],
     "conditionalFormats": [
         {"type": "single", "columnIds": ["ia-growth", "ia-yield", "ia-fund"],
          "condition": "IsNotNull", "style": {"backgroundColor": "#E6F0FE"}},
         {"type": "single", "columnIds": ["ia-growth", "ia-yield", "ia-fund"],
          "condition": "IsNull", "style": {"backgroundColor": "#F3F4F6"}}],
     "style": panel()})

# --- 5. the book everything downstream reads, filtered by the scenario selector
add({"id": "book", "kind": "table", "name": "Book", "visibleAsSource": True,
     "source": {"elementId": "assum", "kind": "table"},
     "columns": [
         {"id": "bb-scen", "formula": "[Assumptions/Scenario]", "name": "Scenario"},
         {"id": "bb-prod", "formula": "[Assumptions/Product]", "name": "Product"},
         {"id": "bb-brev", "formula": "[Assumptions/Baseline Revenue]",
          "name": "Baseline Revenue", "format": MONEY_M},
         {"id": "bb-prev", "formula": "[Assumptions/Projected Revenue]",
          "name": "Projected Revenue", "format": MONEY_M}],
     "style": panel()})

add({"kind": "control", "id": "ctrl-sel", "controlId": "scenarioSelect",
     "name": "Active scenario", "controlType": "list", "selectionMode": "single",
     # no hardcoded default -- if that scenario is missing every KPI reads null
     "mode": "include", "values": [],
     "filters": [{"source": {"kind": "table", "elementId": "book"},
                  "columnId": "bb-scen"}],
     "source": {"kind": "source", "source": {"kind": "table", "elementId": "book"},
                "columnId": "bb-scen"}})

add(segmented_control("ctrl-shock", "RateShock", CO.lab(CFG, "shock_label"),
                      ["-100", "-50", "0", "+50", "+100"]))

PROJ = "Sum([Book/Projected Revenue])"
BASE = "Sum([Book/Baseline Revenue])"


def light_kpi(key, label, value, compare, fmt, primary=False):
    add({"id": "mk-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "book", "kind": "table"},
         "columns": [{"id": "mv-%s" % key, "formula": value, "name": label, "format": fmt},
                     {"id": "mc-%s" % key, "formula": compare, "name": "Baseline",
                      "format": fmt}],
         "value": {"columnId": "mv-%s" % key, "color": B.TEXT_DARK},
         "comparisonColumn": {"columnId": "mc-%s" % key},
         "comparison": {"display": "delta", "colorGood": B.GOOD, "colorBad": B.BAD},
         "name": title(label, 12),
         "style": {"backgroundColor": B.CARD, "borderRadius": "round",
                   "borderColor": B.SOFI_BRIGHT if primary else B.BORDER,
                   "borderWidth": 2 if primary else 1},
         "layout": {"anchor": "middle"}})


light_kpi("rev", "Projected Net Revenue ($M)", PROJ, BASE, MONEY_M, primary=True)
light_kpi("delta", "Revenue Uplift ($M)", "%s - %s" % (PROJ, BASE), "0", MONEY_M)
light_kpi("pct", "Uplift %",
          "Coalesce((%s - %s) / NullIf(%s, 0), 0)" % (PROJ, BASE, BASE), "0", PCT1)

add({"id": "bar-proj", "kind": "bar-chart",
     "source": {"elementId": "book", "kind": "table"},
     "columns": [
         {"id": "bj-x", "formula": "[Book/Product]", "name": "Product"},
         {"id": "bj-base", "formula": BASE, "name": "Baseline ($M)", "format": MONEY_M},
         {"id": "bj-proj", "formula": PROJ, "name": "Projected ($M)", "format": MONEY_M},
         # carry Scenario through even though it is not on an axis: an element
         # only exposes the source columns it actually references, so leaving it
         # out means hand-adding it in the UI later
         {"id": "bj-scen", "formula": "[Book/Scenario]", "name": "Scenario"}],
     "yAxis": {"columnIds": ["bj-base", "bj-proj"]},
     "xAxis": {"columnId": "bj-x"},
     # two y-series stack by default, which would render their SUM
     "stacking": "none",
     "name": title("Projected vs baseline net revenue by %s"
                   % CO.lab(CFG, "seg_product").lower()),
     "legend": {"visibility": "shown"},
     "style": panel()})

# --- 6. lifecycle: an append-only submissions log
add({"id": "subs", "kind": "input-table",
     "source": {"kind": "empty", "connectionId": S.CONN_SNOWFLAKE},
     "inputMode": "view", "name": "Submissions",
     "columns": [
         {"id": "su-scen", "type": "text", "name": "Scenario"},
         {"id": "su-status", "type": "text", "name": "Status",
          "values": ["Submitted", "Approved"], "pills": "color-by-option"},
         {"id": "su-by", "type": "text", "name": "By"}],
     "style": panel()})

# Wipes every named scenario, which restores the Coalesce fallback so the
# modeler reads Base Case again. delete-rows is only legal against a standalone
# {"kind": "empty"} table -- it is rejected on the linked assumptions grid.
add({"id": "btn-reset-scen", "kind": "button", "text": "Reset scenarios",
     "appearance": "text",
     "actions": [{"id": "a-reset-scen", "trigger": "on-click",
                  "effects": [
                      {"effect": "delete-rows", "tableElementId": "scen2",
                       "whichRows": {"type": "formula", "formula": "True"}},
                      {"effect": "delete-rows", "tableElementId": "subs",
                       "whichRows": {"type": "formula", "formula": "True"}},
                      {"effect": "set-control-value", "control": "scenarioSelect",
                       "value": {"type": "constant",
                                 "value": {"type": "text", "value": "Base Case"}}}]}]})

for bid, label, status, appearance in [
        ("btn-submit", "Submit", "Submitted", "outline"),
        ("btn-approve", "Approve", "Approved", "outline")]:
    add({"id": bid, "kind": "button", "text": label, "appearance": appearance,
         "actions": [{"id": "a-" + bid, "trigger": "on-click",
                      "successToast": {"showMessage": "shown",
                                       "title": "Scenario %s" % status.lower()},
                      "effects": [{"effect": "insert-rows", "tableElementId": "subs",
                                   "values": {
                                       "su-scen": {"type": "control",
                                                   "control": "scenarioSelect"},
                                       "su-status": {"type": "constant",
                                                     "value": {"type": "text",
                                                               "value": status}},
                                       "su-by": {"type": "formula",
                                                 "formula": "CurrentUserEmail()"}}}]}]})

header(3, "Member Cohort Builder",
       "Filter the member base into a saveable cohort",
       [nav_el(3)] + stmt_button(3), titles=False)

# the segment filters; the agent gets one set-control-value tool per dimension
COHORT_FILTERS = [
    ("s-prod", "CohortProduct", CO.lab(CFG, "seg_product"), "m1"),
    ("s-age", "CohortAge", CO.lab(CFG, "seg_age"), "m2"),
    ("s-region", "CohortRegion", "Region", "m3"),
    ("s-credit", "CohortCredit", CO.lab(CFG, "seg_credit"), "m4"),
    ("s-dd", "CohortDirectDeposit", CO.lab(CFG, "seg_dd"), "m7"),
    ("s-engage", "CohortEngagement", CO.lab(CFG, "seg_engage"), "m8"),
]
for _eid, _cid, _lab, _col in COHORT_FILTERS:
    add(list_control(_eid, _cid, _lab, "tbl-mp", _col))

add({"kind": "control", "controlId": "CohortProductsHeld", "id": "s-held",
     "name": CO.lab(CFG, "seg_held"), "controlType": "number-range",
     "includeNulls": "when-no-value-is-selected",
     "filters": [{"source": {"kind": "table", "elementId": "tbl-mp"},
                  "columnId": "m5"}]})
# free-text, and deliberately NOT a filter -- it only names the saved cohort
add({"kind": "control", "controlId": "CohortName", "id": "s-name",
     "name": CO.lab(CFG, "cohort_name"), "controlType": "text", "mode": "equals",
     "case": "insensitive", "showOperators": False,
     "includeNulls": "when-no-value-is-selected"})

# cohort KPI cards -- the reactive read-out of whatever the filters select
for key, label, formula, fmt, primary in [
        ("size", CO.lab(CFG, "kpi_cohort_size"),
         "CountDistinct([%s/Member ID])" % MP, NUM0, True),
        ("bal", CO.lab(CFG, "kpi_cohort_vol"),
         "Sum([%s/Total Balances])" % MP, MONEY_C, False),
        ("rev", CO.lab(CFG, "kpi_cohort_rev"),
         "Sum([%s/Annual Revenue]) / CountDistinct([%s/Member ID])" % (MP, MP),
         MONEY_M, False),
        ("attr", CO.lab(CFG, "kpi_cohort_risk"),
         "Avg([%s/Attrition Propensity])" % MP, PCT1, False)]:
    add({"id": "ck-%s" % key, "kind": "kpi-chart",
         "source": {"elementId": "tbl-mp", "kind": "table"},
         "columns": [{"id": "cv-%s" % key, "formula": formula, "name": label, "format": fmt}],
         "value": {"columnId": "cv-%s" % key, "color": B.TEXT_DARK},
         "name": title(label, 12),
         "style": {"backgroundColor": B.CARD, "borderRadius": "round",
                   "borderColor": B.SOFI_BRIGHT if primary else B.BORDER,
                   "borderWidth": 2 if primary else 1},
         "layout": {"anchor": "middle"}})

# col = the SQL column name (fixed contract); label = what a human reads.
# Conflating the two is what produced `Dependency not found: 'member
# population/risk band'` -- the display label is not a column reference.
for key, col, label, order_col in [
        ("credit", "Credit Band", CO.lab(CFG, "seg_credit"), "Credit Order"),
        ("engage", "Engagement", CO.lab(CFG, "seg_engage"), "Engagement Order")]:
    add({"id": "cb-%s" % key, "kind": "bar-chart",
         "source": {"elementId": "tbl-mp", "kind": "table"},
         "columns": [
             {"id": "cbx-%s" % key, "formula": "[%s/%s]" % (MP, col), "name": label},
             {"id": "cbc-%s" % key, "formula": "[%s/%s]" % (MP, col), "name": label + " "},
             {"id": "cby-%s" % key, "formula": "CountDistinct([%s/Member ID])" % MP,
              "name": "Members", "format": NUM0},
             {"id": "cbo-%s" % key, "formula": "Min([%s/%s])" % (MP, order_col),
              "name": "Order"}],
         "yAxis": {"columnIds": ["cby-%s" % key]},
         # ordinal scale -- sort by the explicit order column, not alphabetically
         "xAxis": {"columnId": "cbx-%s" % key,
                   "sort": {"by": "cbo-%s" % key, "direction": "ascending"}},
         "color": {"by": "category", "column": "cbc-%s" % key, "scheme": B.CATEGORICAL},
         "name": title("%s by %s" % (CO.lab(CFG, "cohort_page"), label)),
         "legend": {"visibility": "hidden"},
         "style": panel()})

add({"id": "it-cohorts", "kind": "input-table",
     "source": {"kind": "empty", "connectionId": S.CONN_SNOWFLAKE},
     "inputMode": "view", "name": "Saved Cohorts",
     "columns": [
         {"id": "sc-name", "type": "text", "name": "Cohort Name"},
         {"id": "sc-members", "type": "number", "name": "Members"},
         {"id": "sc-bal", "type": "number", "name": "Balances"},
         {"id": "sc-attr", "type": "number", "name": "Avg Attrition"},
         {"id": "sc-owner", "type": "text", "name": "Saved By"}],
     "style": panel()})

add({"id": "btn-save-cohort", "kind": "button", "text": "Save cohort",
     "appearance": "filled",
     "actions": [{"id": "a-save-cohort", "trigger": "on-click",
                  "successToast": {"showMessage": "shown", "title": "Cohort saved"},
                  "effects": [
                      {"effect": "insert-rows", "tableElementId": "it-cohorts",
                       "values": {
                           "sc-name": {"type": "control", "control": "CohortName"},
                           "sc-members": {"type": "formula",
                                          "formula": "CountDistinct([%s/Member ID])" % MP},
                           "sc-bal": {"type": "formula",
                                      "formula": "Sum([%s/Total Balances])" % MP},
                           "sc-attr": {"type": "formula",
                                       "formula": "Avg([%s/Attrition Propensity])" % MP},
                           "sc-owner": {"type": "formula", "formula": "CurrentUserEmail()"}}},
                      {"effect": "clear-control",
                       "scope": {"type": "control", "controlId": "CohortName"}}]}]})

# delete-rows is only legal against a standalone (non-linked) input table
add({"id": "btn-clear-cohorts", "kind": "button", "text": "Clear saved cohorts",
     "appearance": "text",
     "actions": [{"id": "a-clear-cohorts", "trigger": "on-click",
                  "successToast": {"showMessage": "shown", "title": "Saved cohorts cleared"},
                  "effects": [{"effect": "delete-rows", "tableElementId": "it-cohorts",
                               "whichRows": {"type": "formula", "formula": "True"}}]}]})

add({"id": "c-secf", "kind": "container", "spacing": "small",
     "style": {"padding": "none"}})
add({"id": "ico-filters", "kind": "image",
     "source": {"kind": "url", "url": B.icon(B.ICON_SLIDERS)},
     "style": {"fit": "contain", "padding": "none"}})
add({"id": "sec-filters", "kind": "text",
     "body": '<span style="color: %s">**SEGMENT FILTERS**</span>' % B.SOFI_BRIGHT,
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

add({"id": "tbl-members", "kind": "table", "name": "Member List",
     "source": {"elementId": "tbl-mp", "kind": "table"},
     "columns": [
         {"id": "ml-id", "formula": "[%s/Member ID]" % MP, "name": "Member"},
         {"id": "ml-prod", "formula": "[%s/Primary Product]" % MP, "name": "Primary Product"},
         {"id": "ml-credit", "formula": "[%s/Credit Band]" % MP, "name": "Credit Band"},
         {"id": "ml-eng", "formula": "[%s/Engagement]" % MP, "name": "Engagement"},
         {"id": "ml-bal", "formula": "[%s/Total Balances]" % MP, "name": "Balances",
          "format": MONEY_M},
         {"id": "ml-attr", "formula": "[%s/Attrition Propensity]" % MP,
          "name": "Attrition", "format": PCT1}],
     "style": panel()})

add({"id": "tc-cohort", "kind": "tabbed-container",
     "tabs": [{"name": "Distribution"}, {"name": "Member list"},
              {"name": "Saved cohorts"}],
     "tabBar": {"alignment": "start"}})

add({"id": "c-rail3", "kind": "container", "spacing": "small", "style": panel()})
add({"id": "rail-hd3", "kind": "text", "body": "**Cohort Copilot**",
     "style": {"color": B.TEXT_DARK, "backgroundColor": "transparent"},
     "verticalAlign": "middle"})
add({"id": "chat3", "kind": "chat", "agentId": "ag-cohort"})


# ==================================================================== overlays

# Overlay-level actions cannot resolve controls, so the footer CTAs stay hidden
# and a button element inside the modal page does the work.
overlays.append({
    "id": "modalScenario", "type": "modal", "name": "New Scenario",
    "modal": {"width": "x-small",
              "header": {"title": " ", "showCloseIcon": "shown"},
              "footer": {"primaryCta": {"visible": "hidden"},
                         "secondaryCta": {"visible": "hidden"}}}})
add({"id": "m-band", "kind": "container",
     "style": {"backgroundColor": B.NAVY, "borderRadius": "round", "padding": "none"},
     "backgroundImage": {"source": {"kind": "url", "url": B.header_bg(600, 90)},
                         "style": {"fit": "cover"}}})
add({"id": "m-logo", "kind": "image",
     "source": {"kind": "url", "url": B.logo_white()},
     "style": B.logo_img_style()})
add({"id": "m-title", "kind": "text",
     "body": '<span style="color: #FFFFFF">**New scenario**</span>',
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})
add(text_control("m-scen-name", "NewScenarioName", "Scenario name"))
add({"id": "m-scen-help", "kind": "text",
     "body": '<span style="color: %s">Creates a full set of driver rows for every '
             'product, selects it, and clears this field.</span>' % B.TEXT_MUTED,
     "style": {"color": B.TEXT_MUTED, "backgroundColor": "transparent"},
     "verticalAlign": "middle"})
add({"id": "btn-modal-create", "kind": "button", "text": "Create scenario",
     "appearance": "filled",
     "actions": [{"id": "a-modal-create", "trigger": "on-click",
                  "successToast": {"showMessage": "shown", "title": "Scenario created"},
                  # create the scenario row, make it active, clear the field
                  "effects": [
                      {"effect": "insert-rows", "tableElementId": "scen2",
                       "values": {
                           "sc-name": {"type": "control", "control": "NewScenarioName"},
                           "sc-status": {"type": "constant",
                                         "value": {"type": "text", "value": "Draft"}}}},
                      {"effect": "set-control-value", "control": "scenarioSelect",
                       "value": {"type": "control", "control": "NewScenarioName"}},
                      {"effect": "clear-control",
                       "scope": {"type": "control", "controlId": "NewScenarioName"}},
                      {"effect": "close-overlay"}]}]})
add({"id": "btn-modal-cancel", "kind": "button", "text": "Cancel", "appearance": "text",
     "actions": [{"id": "a-modal-cancel", "trigger": "on-click",
                  "effects": [{"effect": "close-overlay"}]}]})

overlays.append({
    "id": "drawerProduct", "type": "drawer", "name": "Product Detail",
    "drawer": {"width": "medium", "position": "end", "showShadow": "shown",
               "header": {"title": " ", "showCloseIcon": "shown"}}})
add({"id": "dw-tbl", "kind": "table", "name": "Product Detail",
     "source": {"elementId": "tbl-lb", "kind": "table"},
     "columns": [
         {"id": "dw-prod", "formula": "[%s/Product]" % LB, "name": "Product"},
         {"id": "dw-rev", "formula": "Sum([%s/Net Revenue])" % LB,
          "name": "Net Revenue ($M)", "format": MONEY_M},
         {"id": "dw-nii", "formula": "Sum([%s/Net Interest Income])" % LB,
          "name": "Net Interest Income ($M)", "format": MONEY_M},
         {"id": "dw-prov", "formula": "Sum([%s/Provision])" % LB,
          "name": "Provision ($M)", "format": MONEY_M},
         {"id": "dw-cp", "formula": "Sum([%s/Contribution Profit])" % LB,
          "name": "Contribution ($M)", "format": MONEY_M}],
     "groupings": [{"id": "dwg", "groupBy": ["dw-prod"],
                    "calculations": ["dw-rev", "dw-nii", "dw-prov", "dw-cp"],
                    "sort": [{"columnId": "dw-rev", "direction": "descending"}]}],
     "actions": [{"id": "a-dw-select",
                  "trigger": {"on": "on-select",
                              "condition": {"type": "column", "columnId": "dw-prod",
                                            "condition": "IsNotNull"}},
                  "successToast": {"showMessage": "shown", "title": "Filtered to product"},
                  "effects": [{"effect": "set-control-value", "control": "ProductFilter",
                               "value": {"type": "column", "columnId": "dw-prod"}},
                              {"effect": "close-overlay"}]}],
     "style": panel()})
add({"id": "dw-note", "kind": "text",
     "body": "Drawers are new to code representation — this whole panel is declared in the spec.",
     "style": {"color": B.TEXT_MUTED, "backgroundColor": "transparent"},
     "verticalAlign": "middle"})


# ====================================================================== agents

agents.append({
    "id": "ag-book", "name": ("%s Copilot" % CFG["name"]),
    "description": "Answers questions about %s product performance." % CFG["name"],
    "instructions": (
        "%s The lines of business are: %s. " % (CFG["agent"], PRODUCT_NAMES) +
        "The data covers six lines over 24 months split into current and prior "
        "trailing-twelve-month windows; amounts are in $MM. " +
        CO.vocab(CFG, "econ") + " Cite " + CO.vocab(CFG, "metrics") +
        ", and always name the " + CO.lab(CFG, "seg_product").lower()
         + ". Be concise and quantitative."),
    # `generated` lets the agent write its own opener from live data, which beats
    # hardcoded suggestion chips that go stale the moment the data moves
    "greeting": {"mode": "generated",
                 "prompt": "Greet the user in one short line, then offer exactly three "
                           "specific questions you can answer from this data. Name real "
                           "products and make one about whichever product is behind plan."},
    "dataSources": [{"kind": "table", "elementId": "tbl-lb"},
                    {"kind": "table", "elementId": "tbl-rh"}],
    "tools": [
        {"toolId": "t-focus", "kind": "action", "name": "Focus a product",
         "description": "Filter the command center to one product.",
         "steps": [{"kind": "effect", "effect": "set-control-value",
                    "control": "ProductFilter",
                    "value": {"type": "agent-input",
                              "inputName": "The product to focus on"}}]},
        {"toolId": "t-drawer", "kind": "action", "name": "Open the product drawer",
         "description": "Open the product detail side panel.",
         "steps": [{"kind": "effect", "effect": "open-overlay",
                    "overlayId": "drawerProduct"}]},
    ]})

agents.append({
    "id": "ag-scenario", "name": "Scenario Copilot",
    "description": "Builds and edits rate and growth scenarios.",
    "instructions": (
        "You help %s model scenarios for: %s. Drivers are per product: " % (CFG["name"], PRODUCT_NAMES) +
        "%s, %s, %s. " % (C_GROW, C_YLD, C_CST) +
        "Projected revenue = baseline * (1 + growth/100) + baseline * (yield - funding) "
        "/ 10000. Translate the user's description into drivers and explain the revenue "
        "impact in $M."),
    "greeting": {"mode": "static",
                 "message": "Describe a rate or growth scenario and I will set the drivers."},
    "dataSources": [{"kind": "table", "elementId": "book"}],
    "tools": [
        {"toolId": "t-shock", "kind": "action", "name": "Set the rate shock",
         "description": "Set the parallel rate shock in basis points.",
         "steps": [{"kind": "effect", "effect": "set-control-value", "control": "RateShock",
                    "value": {"type": "agent-input",
                              "inputName": CO.lab(CFG, "shock_label")}}]},
        {"toolId": "t-growth", "kind": "action", "name": "Set balance growth",
         "description": "Write a balance-growth percentage into every assumption row.",
         "steps": [{"kind": "effect", "effect": "update-rows", "tableElementId": "assum",
                    "whichRows": {"type": "formula", "formula": "True"},
                    "values": {"ia-growth": {"type": "agent-input",
                                             "inputName": "Balance growth percentage to apply"}}}]},
        {"toolId": "t-newscen", "kind": "action", "name": "Create a scenario",
         "description": "Add a named scenario and make it the active one.",
         "steps": [{"kind": "effect", "effect": "insert-rows", "tableElementId": "scen2",
                    "values": {"sc-name": {"type": "agent-input",
                                           "inputName": "Name for the new scenario"},
                               "sc-status": {"type": "constant",
                                             "value": {"type": "text", "value": "Draft"}}}}]},
    ]})

agents.append({
    "id": "ag-cohort", "name": "Cohort Copilot",
    "description": "Builds a member cohort by setting the filter controls.",
    "instructions": (
        "You build %s cohorts for %s. Translate the user's description into filter " % (CFG["unit_noun"], CFG["name"]) +
        "settings by calling one tool per dimension, then report " +
        CO.vocab(CFG, "cohort_report") + ". " + CO.vocab(CFG, "bands") +
        " Age bands: 18-27, 28-37, 38-47, 48-57, 58+. Regions: West, Southwest, "
        "Midwest, Southeast, Northeast."),
    "greeting": {"mode": "static",
                 "message": "Describe the %ss you want and I will build the %s." % (CFG["unit_noun"], CO.lab(CFG, "cohort_page").lower())},
    "dataSources": [{"kind": "table", "elementId": "tbl-mp"}],
    "tools": [
        {"toolId": "t-c-%s" % cid, "kind": "action", "name": "Set %s" % label,
         "description": "Filter the member population by %s." % label,
         "steps": [{"kind": "effect", "effect": "set-control-value", "control": cid,
                    "value": {"type": "agent-input",
                              "inputName": "The %s value(s) to select" % label}}]}
        for _, cid, label, _ in COHORT_FILTERS
    ] + [
        {"toolId": "t-c-save", "kind": "action", "name": "Save the cohort",
         "description": "Persist the current cohort to the Saved Cohorts table.",
         "steps": [{"kind": "effect", "effect": "insert-rows", "tableElementId": "it-cohorts",
                    "values": {
                        "sc-name": {"type": "agent-input", "inputName": "Name for this cohort"},
                        "sc-members": {"type": "formula",
                                       "formula": "CountDistinct([%s/Member ID])" % MP},
                        "sc-bal": {"type": "formula",
                                   "formula": "Sum([%s/Total Balances])" % MP},
                        "sc-attr": {"type": "formula",
                                    "formula": "Avg([%s/Attrition Propensity])" % MP}}}]},
    ]})


# ------------------------------------------- make every source column available
# An element only exposes the source columns its own `columns` array references,
# so the "Source columns" picker shows everything else unchecked and each has to
# be added by hand in the UI. This pass appends a passthrough column for every
# unreferenced column of the element's source table.
#
# Scoped to charts and pivots on purpose: a `table` element RENDERS every column
# it carries, so doing this to tables would dump 22 columns on screen.
_SRC_COLS = {
    "tbl-lb": (LB, LB_COLS, "a"), "tbl-lbc": (LBC, LB_COLS, "z"),
    "tbl-rh": (RH, RH_COLS, "r"), "tbl-mp": (MP, MP_COLS, "m"),
    "tbl-pc": (PC, PC_COLS, "p"), "tbl-nb": (NB, NB_COLS, "n"),
    "tbl-sku": (SK, SK_COLS, "k"), "tbl-notif": (NT, NT_COLS, "q"),
}
_EXPAND = {"bar-chart", "line-chart", "pivot-table", "donut-chart",
           "waterfall-chart", "scatter-chart", "combo-chart", "area-chart"}

for _el in elements:
    if _el.get("kind") not in _EXPAND:
        continue
    _src = (_el.get("source") or {}).get("elementId")
    if _src not in _SRC_COLS:
        continue
    _tname, _cols, _pfx = _SRC_COLS[_src]
    _have = " ".join(c.get("formula", "") for c in _el.get("columns", []))
    for _i, _cname in enumerate(_cols):
        _ref = "[%s/%s]" % (_tname, _cname)
        if _ref in _have:
            continue
        _el["columns"].append({"id": "%s-x%s%d" % (_el["id"], _pfx, _i),
                               "formula": _ref, "name": _cname})


# ====================================================================== layout

LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo1" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="nav-main1" gridColumn="13 / 20" gridRow="2 / 6"/>
__STMT_BUTTON1__
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
      <Element elementId="bar-prod" gridColumn="12 / 25" gridRow="1 / 19"/>
      <Element elementId="tbl-rank" gridColumn="1 / 25" gridRow="19 / 33"/>
      <Container elementId="c-secw" type="grid" gridColumn="1 / 25" gridRow="33 / 55" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="ico-wheel" gridColumn="1 / 2" gridRow="1 / 3"/>
        <Element elementId="wheel-heading" gridColumn="2 / 25" gridRow="1 / 3"/>
        <Element elementId="plg-wheel" gridColumn="1 / 25" gridRow="3 / 21"/>
      </Container>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Container elementId="c-prodwrap" type="grid" gridColumn="1 / 16" gridRow="1 / 34" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="ico-prod" gridColumn="1 / 2" gridRow="1 / 3"/>
        <Element elementId="pc-heading" gridColumn="2 / 25" gridRow="1 / 3"/>
__PRODUCT_CARDS__
      </Container>
      <Container elementId="c-secn" type="grid" gridColumn="16 / 25" gridRow="1 / 34" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
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
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg2">
  <Container elementId="c-hdr2" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo2" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="nav-main2" gridColumn="13 / 20" gridRow="2 / 6"/>
__STMT_BUTTON2__
  </Container>
  <Element elementId="ctrl-sel" gridColumn="1 / 7" gridRow="6 / 9"/>
  <Element elementId="ctrl-shock" gridColumn="7 / 15" gridRow="6 / 9"/>
  <Element elementId="btn-submit" gridColumn="15 / 18" gridRow="6 / 9"/>
  <Element elementId="btn-approve" gridColumn="18 / 21" gridRow="6 / 9"/>
  <Element elementId="btn-newscen" gridColumn="21 / 25" gridRow="6 / 9"/>
  <Element elementId="mk-rev" gridColumn="1 / 9" gridRow="9 / 15"/>
  <Element elementId="mk-delta" gridColumn="9 / 17" gridRow="9 / 15"/>
  <Element elementId="mk-pct" gridColumn="17 / 25" gridRow="9 / 15"/>
  <Element elementId="bar-proj" gridColumn="1 / 25" gridRow="15 / 33"/>
  <Element elementId="btn-reset-scen" gridColumn="20 / 25" gridRow="33 / 35"/>
  <Element elementId="assum" gridColumn="1 / 25" gridRow="35 / 57"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg3">
  <Container elementId="c-hdr3" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo3" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="nav-main3" gridColumn="13 / 20" gridRow="2 / 6"/>
__STMT_BUTTON3__
  </Container>
  <Container elementId="c-secf" type="grid" gridColumn="1 / 25" gridRow="6 / 8" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ico-filters" gridColumn="1 / 2" gridRow="1 / 3"/>
    <Element elementId="sec-filters" gridColumn="2 / 25" gridRow="1 / 3"/>
  </Container>
  <Element elementId="s-prod" gridColumn="1 / 5" gridRow="8 / 11"/>
  <Element elementId="s-age" gridColumn="5 / 9" gridRow="8 / 11"/>
  <Element elementId="s-region" gridColumn="9 / 13" gridRow="8 / 11"/>
  <Element elementId="s-credit" gridColumn="13 / 17" gridRow="8 / 11"/>
  <Element elementId="s-dd" gridColumn="17 / 21" gridRow="8 / 11"/>
  <Element elementId="s-engage" gridColumn="21 / 25" gridRow="8 / 11"/>
  <Element elementId="s-held" gridColumn="1 / 7" gridRow="11 / 14"/>
  <Element elementId="s-name" gridColumn="7 / 13" gridRow="11 / 14"/>
  <Element elementId="btn-save-cohort" gridColumn="13 / 18" gridRow="11 / 14"/>
  <Element elementId="btn-clear-cohorts" gridColumn="18 / 25" gridRow="11 / 14"/>
  <Element elementId="ck-size" gridColumn="1 / 7" gridRow="14 / 20"/>
  <Element elementId="ck-bal" gridColumn="7 / 13" gridRow="14 / 20"/>
  <Element elementId="ck-rev" gridColumn="13 / 19" gridRow="14 / 20"/>
  <Element elementId="ck-attr" gridColumn="19 / 25" gridRow="14 / 20"/>
  <TabbedContainer elementId="tc-cohort" type="tabbed-container" gridColumn="1 / 18" gridRow="20 / 42">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="cb-credit" gridColumn="1 / 13" gridRow="1 / 21"/>
      <Element elementId="cb-engage" gridColumn="13 / 25" gridRow="1 / 21"/>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="tbl-members" gridColumn="1 / 25" gridRow="1 / 21"/>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="it-cohorts" gridColumn="1 / 25" gridRow="1 / 21"/>
    </Tab>
  </TabbedContainer>
  <Container elementId="c-rail3" type="grid" gridColumn="18 / 25" gridRow="20 / 42" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="rail-hd3" gridColumn="1 / 13" gridRow="1 / 3"/>
    <Element elementId="chat3" gridColumn="1 / 13" gridRow="3 / 22"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="modalCard">
  <Container elementId="mc-band" type="grid" gridColumn="1 / 25" gridRow="1 / 4" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="mc-logo" gridColumn="1 / 5" gridRow="1 / 3"/>
    <Element elementId="mc-title" gridColumn="5 / 25" gridRow="1 / 3"/>
  </Container>
  <Element elementId="mck-bal" gridColumn="1 / 7" gridRow="4 / 8"/>
  <Element elementId="mck-mem" gridColumn="7 / 13" gridRow="4 / 8"/>
  <Element elementId="mck-rate" gridColumn="13 / 19" gridRow="4 / 8"/>
  <Element elementId="mck-qoq" gridColumn="19 / 25" gridRow="4 / 8"/>
  <Element elementId="mc-trend" gridColumn="1 / 25" gridRow="8 / 19"/>
  <Element elementId="mc-sku" gridColumn="1 / 25" gridRow="19 / 33"/>
  <Element elementId="mc-model" gridColumn="15 / 21" gridRow="33 / 35"/>
  <Element elementId="mc-close" gridColumn="21 / 25" gridRow="33 / 35"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto" id="modalScenario">
  <Container elementId="m-band" type="grid" gridColumn="1 / 13" gridRow="1 / 4" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="m-logo" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="m-title" gridColumn="4 / 13" gridRow="1 / 3"/>
  </Container>
  <Element elementId="m-scen-name" gridColumn="1 / 13" gridRow="4 / 6"/>
  <Element elementId="m-scen-help" gridColumn="1 / 13" gridRow="6 / 8"/>
  <Element elementId="btn-modal-create" gridColumn="1 / 8" gridRow="8 / 10"/>
  <Element elementId="btn-modal-cancel" gridColumn="8 / 13" gridRow="8 / 10"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto" id="drawerProduct">
  <Element elementId="dw-tbl" gridColumn="1 / 13" gridRow="1 / 17"/>
  <Element elementId="dw-note" gridColumn="1 / 13" gridRow="17 / 20"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pgData">
  <Element elementId="tbl-lb" gridColumn="1 / 13" gridRow="1 / 13"/>
  <Element elementId="tbl-rh" gridColumn="13 / 25" gridRow="1 / 13"/>
  <Element elementId="tbl-mp" gridColumn="1 / 13" gridRow="13 / 25"/>
  <Element elementId="tbl-pc" gridColumn="13 / 19" gridRow="13 / 25"/>
  <Element elementId="tbl-nb" gridColumn="19 / 25" gridRow="13 / 25"/>
  <Element elementId="sbase" gridColumn="1 / 9" gridRow="25 / 37"/>
  <Element elementId="spivot" gridColumn="9 / 17" gridRow="25 / 37"/>
  <Element elementId="book" gridColumn="17 / 25" gridRow="25 / 37"/>
  <Element elementId="tbl-notif" gridColumn="9 / 17" gridRow="49 / 61"/>
  <Element elementId="ctrl-state" gridColumn="9 / 17" gridRow="73 / 76"/>

  <Element elementId="scen2" gridColumn="17 / 25" gridRow="49 / 61"/>
  <Element elementId="subs" gridColumn="1 / 9" gridRow="61 / 73"/>
  <Element elementId="tbl-sku" gridColumn="1 / 9" gridRow="37 / 49"/>
  <Element elementId="tbl-lbc" gridColumn="9 / 17" gridRow="37 / 49"/>
  <Element elementId="ctrl-card" gridColumn="17 / 25" gridRow="37 / 40"/>
__HERO_TBL_SLOT__
</Page>
"""

# product cards: 3 across x 2 rows, generated so the grid stays consistent
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
        '        </Container>' % (_k, _col, _col + 12, _top, _top + 10,
                                  _k, _k, _k, _k, _k, _k))
# Always substitute this, even to empty: an unreplaced __PLACEHOLDER__ in the
# layout XML comes back as a masked 500, not a useful error.
LAYOUT = LAYOUT.replace("__HERO_TBL_SLOT__",
                        ('  <Element elementId="tbl-hero" gridColumn="17 / 25"'
                         ' gridRow="61 / 73"/>') if HERO_TBL else "")

LAYOUT = LAYOUT.replace("__PRODUCT_CARDS__", "\n".join(_CARD_ROWS))

# notification cards stack down the Analyst rail, 5 rows deep inside c-secn
_NOTIF_ROWS = []
for _i, (_o, _sev, _cap) in enumerate(ALERTS):
    _k = "n%d" % _o
    _t = 3 + _i * 6
    _NOTIF_ROWS.append(
        '        <Container elementId="ncard-%s" type="grid" gridColumn="1 / 25" gridRow="%d / %d" '
        'gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">\n'
        # a card's INTERNAL row count must not exceed the span it is given in the
        # parent grid, or it is allotted less height than it needs and silently
        # renders as nothing -- no error, no empty box
        '          <Element elementId="nico-%s" gridColumn="1 / 4" gridRow="1 / 2"/>\n'
        '          <Element elementId="nsev-%s" gridColumn="4 / 25" gridRow="1 / 2"/>\n'
        '          <Element elementId="ntitle-%s" gridColumn="1 / 25" gridRow="2 / 3"/>\n'
        '          <Element elementId="nbody-%s" gridColumn="1 / 25" gridRow="3 / 4"/>\n'
        '          <Element elementId="nkpi-%s" gridColumn="1 / 13" gridRow="4 / 6"/>\n'
        '          <Element elementId="nmeta-%s" gridColumn="13 / 25" gridRow="4 / 6"/>\n'
        '        </Container>' % (_k, _t, _t + 6, _k, _k, _k, _k, _k, _k))
LAYOUT = LAYOUT.replace("__NOTIF_CARDS__", "\n".join(_NOTIF_ROWS))

# The statement button only exists once the report has been created, so its
# layout slot has to appear and disappear with it -- a layout line referencing a
# missing element is a hard rejection at create. One button per page now
# (was page-1 only), each with its own element id.
for _pg in (1, 2, 3):
    LAYOUT = LAYOUT.replace(
        "__STMT_BUTTON%d__" % _pg,
        '    <Element elementId="btn-stmt%d" gridColumn="21 / 25" gridRow="2 / 6"/>' % _pg
        if any(e["id"] == "btn-stmt%d" % _pg for e in elements) else "")

SETTINGS = {"theme": {"overrides": {
    "colors": {"text": B.TEXT_DARK, "highlight": B.SOFI_BRIGHT, "success": B.GOOD,
               "warning": B.WARN, "danger": B.BAD, "darkMode": "hidden"},
    "colorOverrides": {"backgroundCanvas": B.CANVAS, "canvasBackground": B.CANVAS},
    "categoricalScheme": B.CATEGORICAL,
            "backgroundColor": B.CANVAS,
            "elementBackgroundColor": B.CARD,
            "borderColor": B.BORDER,
    "borderRadius": "round",
    "space": {"unit": "small", "showElementPadding": "shown"},
    "fonts": {"dataFont": "Inter", "textFont": "Inter"},
}}}


# ------------------------------------------------------------------ surfaces
# SURFACES lets a caller build only the pieces they want:
#   SURFACES=command                  command center only
#   SURFACES=command,model            + the scenario modeler
#   SURFACES=command,cohort           + the cohort builder
#   SURFACES=command,model,cohort     everything (the default)
#
# The LAYOUT is the source of truth for what is placed, so gating deletes whole
# <Page> blocks and then removes anything left dangling. Dangling references are
# a hard rejection at create, and they come in three flavours: elements no longer
# placed, action effects that navigate to a dropped page, and action effects that
# set a control which lived on one. Iterate until stable rather than trying to
# order the fixes by hand.
import json as _json
import re as _re

_SURF = {x.strip() for x in os.environ.get(
    "SURFACES", "command,model,cohort").split(",") if x.strip()}
_PAGE_OF = {"model": "pg2", "cohort": "pg3"}
_DROP_PAGES = {pid for surf, pid in _PAGE_OF.items() if surf not in _SURF}

if _DROP_PAGES:
    for _pid in _DROP_PAGES:
        LAYOUT = _re.sub(r'<Page[^>]*id="%s".*?</Page>\s*' % _pid, "",
                         LAYOUT, flags=_re.S)

    _AGENT_OF = {"pg2": "ag-scenario", "pg3": "ag-cohort"}
    _drop_agents = {_AGENT_OF[p] for p in _DROP_PAGES if p in _AGENT_OF}
    agents = [a for a in agents if a.get("id") not in _drop_agents]

    for _el in elements:
        if _el.get("kind") == "navigation":
            _el["options"] = [o for o in _el.get("options", [])
                              if o.get("destination", {}).get("pageId")
                              not in _DROP_PAGES]

    _before = len(elements)
    for _pass in range(6):
        _placed = set(_re.findall(r'elementId="([^"]+)"', LAYOUT))
        elements = [e for e in elements if e["id"] in _placed]
        _live = ({e.get("controlId") for e in elements if e.get("controlId")}
                 | _placed)

        def _keeps(effect):
            toks = set(_re.findall(r'"([^"]+)"', _json.dumps(effect)))
            if toks & _DROP_PAGES:
                return False
            ctrl = effect.get("control")
            if ctrl and ctrl not in _live:
                return False
            tbl = effect.get("table")
            return not (tbl and tbl not in _live)

        _changed = False
        for _el in elements:
            for _a in (_el.get("actions") or []):
                if "effects" in _a:
                    _keep = [e for e in _a["effects"] if _keeps(e)]
                    if len(_keep) != len(_a["effects"]):
                        _a["effects"] = _keep
                        _changed = True
            if _el.get("actions") is not None:
                _acts = [a for a in _el["actions"] if a.get("effects")]
                if len(_acts) != len(_el["actions"]):
                    _changed = True
                if _acts:
                    _el["actions"] = _acts
                else:
                    del _el["actions"]

        # dependency closure: the modeler's data chain spans pg2 (assum) and
        # pgData (sbase/spivot/book/scen2), so dropping the page orphans the rest.
        # Walk source references and drop anything whose source is gone.
        _ids = {e["id"] for e in elements}
        _orphans = set()
        for _el in elements:
            _src = _el.get("source") or {}
            _ref = _src.get("elementId") or _src.get("from")
            if _ref and _ref not in _ids:
                _orphans.add(_el["id"])
        if _orphans:
            for _o in _orphans:
                LAYOUT = _re.sub(
                    r'\s*<Element[^>]*elementId="%s"[^>]*/>' % _re.escape(_o),
                    "", LAYOUT)
            elements = [e for e in elements if e["id"] not in _orphans]
            _changed = True

        # a button whose only job was a drill-through is now dead
        _dead = {e["id"] for e in elements
                 if e.get("kind") == "button" and not e.get("actions")}
        if _dead:
            for _d in _dead:
                LAYOUT = _re.sub(
                    r'\s*<Element[^>]*elementId="%s"[^>]*/>' % _re.escape(_d),
                    "", LAYOUT)
            _changed = True
        if not _changed:
            break

    # agents can reference dropped tables as data sources
    _ids = {e["id"] for e in elements}
    for _a in agents:
        _a["dataSources"] = [d for d in _a.get("dataSources", [])
                             if d.get("elementId") in _ids]
    print("surfaces=%s  dropped=%s  elements %d -> %d  agents=%d"
          % (",".join(sorted(_SURF)), ",".join(sorted(_DROP_PAGES)),
             _before, len(elements), len(agents)))

DOCUMENT = {
    "schemaVersion": 1,
    "kind": "workbook",
    "elements": elements,
    "pages": [pg for pg in (
        {"id": "pg1", "name": "Command Center"},
        {"id": "pg2", "name": CO.lab(CFG, "modeler_page")},
        {"id": "pg3", "name": CO.lab(CFG, "cohort_page")},
        {"id": "pgData", "name": "Data", "visibility": "hidden"},
    ) if pg["id"] not in _DROP_PAGES],
    "overlays": overlays,
    "agents": agents,
    "settings": SETTINGS,
    "layout": LAYOUT,
}

SPEC = {"name": "%s — %s" % (CFG["name"], CFG["title"]),
        "folderId": S.FOLDER_CLAUDE_BUILDER,
        "document": DOCUMENT}


def _state_file(key):
    return SPECS / ("wb_state_%s.json" % key)


def _save_state(workbook_id, version):
    _state_file(CFG["key"]).write_text(
        json.dumps({"workbookId": workbook_id, "lastVersion": version}))


def _check_not_edited_since_last_push(workbook_id):
    """Refuse a silent overwrite if someone touched this workbook in the UI
    since our last push. `update` always sends a COMPLETE spec (Sigma has no
    partial-update endpoint), so pushing blind means every UI edit since --
    a resized column, a hidden column, a manually added filter -- gets wiped
    with no warning. This can't merge those edits back in (that would need a
    real diff/merge across layout XML + JSON elements, which isn't built and
    would be risky to ship half-working); it can only stop and ask first.
    Cheap check: GET /v2/workbooks/{id} (no /spec) returns latestVersion
    without paying for the full spec body -- that's the metadata call, not
    the workbook's real edit history."""
    meta = S.get_workbook_meta(workbook_id)
    live_version = meta.get("latestVersion")
    state_path = _state_file(CFG["key"])
    force = os.environ.get("FORCE") == "1"

    if not state_path.exists():
        if not force:
            print("⚠️  No local baseline for this workbook (never pushed from "
                  "this checkout, or state file was cleared).")
            print("    Live version: %d, last edited by %s at %s"
                  % (live_version, meta.get("updatedBy"), meta.get("updatedAt")))
            print("    Re-run with FORCE=1 to push anyway and establish a "
                  "baseline for future runs.")
            sys.exit(1)
        print("⚠️  FORCE=1 set, no baseline yet — pushing and recording v%d "
              "as the new baseline." % live_version)
        return

    known = json.loads(state_path.read_text())
    last_known = known.get("lastVersion")
    if live_version > last_known:
        if not force:
            print("⚠️  This workbook was edited since the last push — v%d -> v%d, "
                  "by %s at %s." % (last_known, live_version,
                                     meta.get("updatedBy"), meta.get("updatedAt")))
            print("    Pushing now will silently overwrite those edits (Sigma's "
                  "spec API has no partial update / merge). Open the workbook "
                  "and re-apply anything important in company.py first, or "
                  "re-run with FORCE=1 to overwrite anyway.")
            sys.exit(1)
        print("⚠️  FORCE=1 set — overwriting v%d despite edits since v%d."
              % (live_version, last_known))


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if action == "verify":
        try:
            S.verify_workbook(SPEC)
            print("✅ verify passed — %d elements, %d overlays, %d agents"
                  % (len(elements), len(overlays), len(agents)))
        except S.SigmaError as exc:
            msg = exc.body
            try:
                msg = json.loads(exc.body).get("message", msg)
            except ValueError:
                pass
            print("❌ verify failed:\n" + msg[:2500])
    elif action == "create":
        r = S.create_workbook(SPEC)
        print("✅ created", r["workbookId"])
        (SPECS / "workbook_id.txt").write_text(r["workbookId"])
        meta = S.get_workbook_meta(r["workbookId"])
        _save_state(r["workbookId"], meta.get("latestVersion", 1))
    elif action == "update":
        workbook_id = sys.argv[2]
        _check_not_edited_since_last_push(workbook_id)
        S.update_workbook(workbook_id, SPEC)
        meta = S.get_workbook_meta(workbook_id)
        _save_state(workbook_id, meta.get("latestVersion"))
        print("✅ updated", workbook_id, "(now v%d)" % meta.get("latestVersion", 0))


if __name__ == "__main__":
    main()
