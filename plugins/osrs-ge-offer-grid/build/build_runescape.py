#!/usr/bin/env python3
"""
Grand Exchange Merchanting Desk — a RuneScape-themed Sigma workbook.

Org        demeng      (https://aws-api.sigmacomputing.com)
Connection CXA, snowflake, write access
Data       LIVE Old School RuneScape Grand Exchange prices, captured at build time
Plugin     OSRS Grand Exchange Offer Grid (bespoke; 240 real item sprites)

Verified shapes this build relies on (probed against this org, not guessed):
  * inline custom SQL      source {kind:"sql", connectionId, statement}
                           columns reference [Custom SQL/<OUTPUT_ALIAS>]
  * element titles         name {text, color, fontWeight}  -- survives round-trip,
                           which is the only way to get light text on a dark card
                           (a text element's `style` is silently dropped)
  * images                 source {kind:"url", url:<https or data uri>}
  * linked input table     source {kind:"linked", from:<pivot elementId>}
  * plugin bindings        bare columnId strings

Usage:
  python3 build_runescape.py create
  python3 build_runescape.py update <workbookId>
  python3 build_runescape.py spec   <workbookId>
"""
import json, pathlib, sys, urllib.error, urllib.request

RS     = pathlib.Path(__file__).parent
BASE   = "https://aws-api.sigmacomputing.com"
CONN   = "40384a8d-94f7-409d-8486-33c799bc6ac6"
FOLDER = "3a773978-c8b2-426c-b678-bdaf3f6a9ec6"
PLUGIN = "7fa7ca6f-f33b-404b-874a-f62813d742de"
TOKEN  = (RS.parent / "awsapi_token.txt").read_text().strip()

# ----------------------------------------------------------------- palette
# Old School RuneScape: dark leather chrome, parchment ledgers, gold lettering.
LEATHER   = "#3E3529"
LEATHER_D = "#241F1A"
GOLD      = "#FFC65B"
PARCH     = "#EDE0C0"
INK       = "#2B2620"
BORDER    = "#6F634E"
CREAM     = "#C9BCA0"
GOOD      = "#2E7D32"
BAD       = "#B3261E"
RS_GREEN  = "#4BE04B"
RS_RED    = "#FF5B4A"
ENTERED   = "#FBF0D3"

# metal and gem tiers, in RuneScape's own progression order
SCHEME = ["#FFC65B", "#CD7F32", "#4A6E9E", "#3E7A4E",
          "#5DBFC4", "#B33C32", "#8B6FA8", "#A8A29A"]

GP    = {"kind": "number", "formatString": ",.0f"}
GPBIG = {"kind": "number", "formatString": ".3~s"}
PCT   = {"kind": "number", "formatString": ".2%"}
PCT0  = {"kind": "number", "formatString": ".0%"}
NUM   = {"kind": "number", "formatString": ",.0f"}

LOGO     = (RS / "logo_b64.txt").read_text().strip()
MARKET   = (RS / "market_layer.sql").read_text()
PLAN     = (RS / "plan_base.sql").read_text()
CAPTURED = json.load(open(RS / "meta.json"))["snapshot"]

PANEL_DARK  = {"backgroundColor": LEATHER, "borderColor": BORDER,
               "borderWidth": 1, "borderRadius": "round"}
PANEL_PARCH = {"backgroundColor": PARCH, "borderColor": BORDER,
               "borderWidth": 1, "borderRadius": "round"}

AXIS_DARK = {"labels": {"color": CREAM}, "marks": "grid"}

# ----------------------------------------------------------------- helpers
def col(cid, formula, name=None, fmt=None, **kw):
    c = {"id": cid, "formula": formula}
    if name: c["name"] = name
    if fmt:  c["format"] = fmt
    c.update(kw)
    return c

def title(text, color=GOLD):
    return {"text": text, "color": color, "fontWeight": "bold"}

def sql_table(eid, name, statement, cols, style=None, **kw):
    el = {"id": eid, "kind": "table", "name": name,
          "source": {"kind": "sql", "connectionId": CONN, "statement": statement},
          "columns": cols, "order": [c["id"] for c in cols],
          "style": style or PANEL_PARCH}
    el.update(kw)
    return el

def kpi(eid, label, source, formula, fmt, color=GOLD):
    return {"id": eid, "kind": "kpi-chart",
            "source": {"kind": "table", "elementId": source},
            "columns": [col(eid + "-v", formula, "Value", fmt)],
            "value": {"columnId": eid + "-v", "color": color, "fontSize": 30},
            "name": title(label),
            "style": PANEL_DARK,
            "layout": {"anchor": "center"}}

def container(eid, bg=LEATHER):
    return {"id": eid, "kind": "container", "style": {"backgroundColor": bg}}

def heading(eid, body):
    # text-element `style` is dropped on save, so colour lives inline in the body
    return {"id": eid, "kind": "text", "body": body, "verticalAlign": "center"}

def gold_text(text, size=30):
    # a text-element <span> only accepts color / background-color / font-size /
    # font-family -- weight has to come from markdown, not CSS
    # no markdown bold: Sigma rewrites `**...**` to sit INSIDE the span, where
    # it renders literally. Size + colour carry the emphasis instead.
    return f'<span style="color:{GOLD};font-size:{size}px">{text}</span>' 

def cream_text(text, size=12):
    return f'<span style="color:{CREAM};font-size:{size}px">{text}</span>'

def list_ctrl(cid, control_id, label, src, column_id):
    return {"id": cid, "kind": "control", "controlId": control_id, "name": label,
            "controlType": "list", "mode": "include", "selectionMode": "multiple",
            "values": [],
            "filters": [{"source": {"kind": "table", "elementId": src},
                         "columnId": column_id}],
            "source": {"kind": "source",
                       "source": {"kind": "table", "elementId": src},
                       "columnId": column_id}}

def segmented(cid, control_id, label, values, default):
    return {"id": cid, "kind": "control", "controlId": control_id, "name": label,
            "controlType": "segmented", "value": default,
            "source": {"kind": "manual", "valueType": "text", "values": values}}

def number_ctrl(cid, control_id, label, default):
    """An unbound NUMBER parameter DOES work on this org (it is rejected on
    others, where the workaround is a text control coerced with Number())."""
    return {"id": cid, "kind": "control", "controlId": control_id, "name": label,
            "controlType": "number", "mode": "=", "value": default,
            "includeNulls": "always"}

def text_ctrl(cid, control_id, label):
    # includeNulls is a STRING enum here, not a boolean
    return {"id": cid, "kind": "control", "controlId": control_id, "name": label,
            "controlType": "text", "mode": "equals", "case": "insensitive",
            "includeNulls": "when-no-value-is-selected", "showOperators": False}

def button(eid, text, effects, fill=GOLD, font=INK):
    return {"id": eid, "kind": "button", "text": text, "appearance": "filled",
            "align": "stretch", "size": "large", "fillColor": fill, "fontColor": font,
            "actions": [{"id": f"act-{eid}", "trigger": "on-click", "effects": effects}]}

def cf(column_ids, condition, style, value=None, formula=None):
    """Conditional format. `type:"single"` is REQUIRED (omitting it fails as a
    masked Invalid kind), and the styling key is `style`, not `format` —
    a `format` block is silently dropped."""
    r = {"type": "single", "columnIds": column_ids, "condition": condition, "style": style}
    if value is not None:   r["value"] = value
    if formula is not None: r["formula"] = formula
    return r

FILL_FORMULA = 'Switch([FillRate],"Conservative",0.4,"Aggressive",1,0.7)'

# ================================================================= page 1
MARKET_COLS = [
    ("m-item",    "ITEM_NAME",               "Item",                None),
    ("m-cat",     "CATEGORY",                "Category",            None),
    ("m-access",  "ACCESS_TIER",             "Access",              None),
    ("m-ib",      "INSTA_BUY",               "Insta Buy",           GP),
    ("m-is",      "INSTA_SELL",              "Insta Sell",          GP),
    ("m-tax",     "GE_TAX",                  "GE Tax",              GP),
    ("m-gross",   "GROSS_MARGIN",            "Gross Margin",        GP),
    ("m-net",     "NET_MARGIN",              "Net Margin",          GP),
    ("m-roi",     "ROI_PCT",                 "ROI",                 PCT),
    ("m-lim",     "BUY_LIMIT",               "Buy Limit",           NUM),
    ("m-vol",     "VOLUME_24H",              "Volume 24h",          NUM),
    ("m-cap",     "CAPITAL_PER_CYCLE",       "Capital per Cycle",   GPBIG),
    ("m-ppc",     "PROFIT_PER_CYCLE",        "Profit per Cycle",    GPBIG),
    ("m-pday",    "PROFIT_PER_DAY_FILLABLE", "Fillable Profit 24h", GPBIG),
    ("m-tv",      "TRADED_VALUE_24H",        "Traded Value 24h",    GPBIG),
    ("m-taxpaid", "TAX_PAID_24H",            "Tax Paid 24h",        GPBIG),
    ("m-verdict", "SPREAD_VERDICT",          "Spread Verdict",      None),
    ("m-liq",     "LIQUIDITY_BAND",          "Liquidity",           None),
    ("m-killed",  "TAX_KILLED",              "Tax Killed",          NUM),
    ("m-prof",    "IS_PROFITABLE",           "Profitable",          NUM),
    ("m-anet",    "AVG_NET_MARGIN",          "Net Margin 24h Avg",  GP),
    ("m-aroi",    "AVG_ROI_PCT",             "ROI 24h Avg",         PCT),
    ("m-appc",    "AVG_PROFIT_PER_CYCLE",    "Profit per Cycle 24h Avg", GPBIG),
    ("m-averd",   "AVG_VERDICT",             "Verdict 24h Avg",     None),
    ("m-aprof",   "AVG_IS_PROFITABLE",       "Profitable 24h Avg",  NUM),
    ("m-works",   "FLIP_WORKS",              "Flip Works",          None),
]

def page1():
    els = []
    els.append(sql_table("tbl-market", "Market", MARKET,
        [col(c, f"[Custom SQL/{a}]", n, f) for c, a, n, f in MARKET_COLS]))

    els.append(container("hdr-1"))
    els.append({"id": "img-logo", "kind": "image",
                "source": {"kind": "url", "url": LOGO},
                "alt": "Old School RuneScape", "style": {"fit": "scale-down"}})
    els.append(heading("txt-title", gold_text("Grand Exchange &mdash; Merchanting Desk", 30)))
    els.append(heading("txt-scope", cream_text(
        f"Live Grand Exchange capture &middot; {CAPTURED} &middot; 240 liquid items "
        "&middot; 2% sale tax, 5m cap and 4-hour buy limits modelled exactly", 12)))

    els.append(container("ctl-1", PARCH))
    els.append(list_ctrl("ctrl-cat",     "Category",  "Category",       "tbl-market", "m-cat"))
    els.append(list_ctrl("ctrl-access",  "Access",    "Access",         "tbl-market", "m-access"))
    els.append(list_ctrl("ctrl-liq",     "Liquidity", "Liquidity",      "tbl-market", "m-liq"))
    els.append(list_ctrl("ctrl-verdict", "Verdict",   "Spread verdict", "tbl-market", "m-verdict"))

    els.append(kpi("kpi-items",  "Liquid items",          "tbl-market",
                   "CountDistinct([Market/Item])", NUM))
    els.append(kpi("kpi-value",  "24h traded value",      "tbl-market",
                   "Sum([Market/Traded Value 24h])", GPBIG))
    els.append(kpi("kpi-tax",    "GE tax paid, 24h",      "tbl-market",
                   "Sum([Market/Tax Paid 24h])", GPBIG, color=RS_RED))
    els.append(kpi("kpi-killed", "Spreads killed by tax", "tbl-market",
                   "Sum([Market/Tax Killed])", NUM, color=RS_RED))

    els.append({"id": "plg-grid", "kind": "plugin", "pluginId": PLUGIN,
                "displayName": "Grand Exchange Offer Grid",
                "config": {"source": {"kind": "element", "elementId": "tbl-market"},
                           "itemName": "m-item", "instaBuy": "m-ib", "instaSell": "m-is",
                           "netMargin": "m-net", "roiPct": "m-roi", "buyLimit": "m-lim",
                           "volume": "m-vol", "geTax": "m-tax", "maxSlots": "40"},
                "style": {"backgroundColor": "transparent"}})

    # return against liquidity. scatter-chart aggregates by x-value, so the y
    # measure is an Avg and therefore cannot silently sum on a collision.
    els.append({"id": "chart-flipmap", "kind": "scatter-chart",
        "name": title("Does the spread survive the tax?"),
        "source": {"kind": "table", "elementId": "tbl-market"},
        "columns": [col("fm-x", "[Market/Volume 24h]", "Volume 24h", NUM),
                    col("fm-y", "Avg([Market/ROI])", "ROI", PCT),
                    col("fm-c", "[Market/Flip Works]", "Flip Works")],
        # 24h volume spans four orders of magnitude, so a linear x-axis piles
        # every item against the left edge; log spreads them out.
        "xAxis": {"columnId": "fm-x",
                  "format": {"labels": {"color": CREAM}, "marks": "grid",
                             "scale": {"type": "log"}}},
        "yAxis": {"columnIds": ["fm-y"], "format": AXIS_DARK},
        # two categories, not sixteen -- a 16-item legend ate half the chart
        "color": {"by": "category", "column": "fm-c", "scheme": [GOOD, BAD]},
        "style": PANEL_DARK})

    els.append({"id": "chart-cat", "kind": "bar-chart",
        "name": title("Workable profit per full cycle, by category"),
        "source": {"kind": "table", "elementId": "tbl-market"},
        "columns": [col("cc-x", "[Market/Category]", "Category"),
                    col("cc-y", "SumIf([Market/Profit per Cycle],[Market/Profitable]=1)",
                        "Workable profit per cycle", GPBIG)],
        "xAxis": {"columnId": "cc-x",
                  "sort": {"by": "cc-y", "aggregation": "sum", "direction": "descending"},
                  "format": {"labels": {"color": CREAM}, "marks": "none"}},
        "yAxis": {"columnIds": ["cc-y"], "format": AXIS_DARK},
        "orientation": "horizontal", "stacking": "none",
        "style": PANEL_DARK})

    els.append({"id": "tbl-top", "kind": "table", "name": title("Offer Book", INK),
        "source": {"kind": "table", "elementId": "tbl-market"},
        "columns": [
            col("t-item",    "[Market/Item]",             "Item"),
            col("t-cat",     "[Market/Category]",         "Category"),
            col("t-is",      "[Market/Insta Sell]",       "Buy at",          GP),
            col("t-ib",      "[Market/Insta Buy]",        "Sell at",         GP),
            col("t-tax",     "[Market/GE Tax]",           "Tax",             GP),
            col("t-net",     "[Market/Net Margin]",       "Net margin",      GP),
            col("t-roi",     "[Market/ROI]",              "ROI",             PCT),
            col("t-lim",     "[Market/Buy Limit]",        "4h limit",        NUM),
            col("t-vol",     "[Market/Volume 24h]",       "Volume 24h",      NUM),
            col("t-cap",     "[Market/Capital per Cycle]","Capital / cycle", GPBIG),
            col("t-ppc",     "[Market/Profit per Cycle]", "Profit / cycle",  GPBIG),
            col("t-verdict", "[Market/Spread Verdict]",   "Verdict"),
            col("t-anet",    "[Market/Net Margin 24h Avg]","Net margin 24h avg", GP),
            col("t-aroi",    "[Market/ROI 24h Avg]",       "ROI 24h avg",        PCT),
        ],
        "order": ["t-item","t-cat","t-is","t-ib","t-tax","t-net","t-roi",
                  "t-anet","t-aroi","t-lim","t-vol","t-cap","t-ppc","t-verdict"],
        "sort": [{"columnId": "t-ppc", "direction": "descending", "nulls": "last"}],
        "conditionalFormats": [
            cf(["t-net"], "<", {"color": BAD}, value=0),
            cf(["t-roi"], ">", {"color": GOOD}, value=0.05),
            cf(["t-verdict"], "formula", {"backgroundColor": "#F6DCD8", "color": BAD},
               formula='Contains([Market/Spread Verdict],"Tax eats")'),
        ],
        "tableStyle": {"banding": "shown", "cellSpacing": "medium"},
        "style": PANEL_PARCH})

    els.append({"id": "chat-market", "kind": "chat", "agentId": "ag-market",
                "name": "Market Copilot"})
    return els

LAYOUT_P1 = """<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="p-market">
  <Container elementId="hdr-1" type="grid" gridColumn="1 / 25" gridRow="1 / 8" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="img-logo"  gridColumn="1 / 7"  gridRow="1 / 7"/>
    <Element elementId="txt-title" gridColumn="7 / 25" gridRow="1 / 5"/>
    <Element elementId="txt-scope" gridColumn="7 / 25" gridRow="5 / 7"/>
  </Container>
  <Container elementId="ctl-1" type="grid" gridColumn="1 / 25" gridRow="8 / 12" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-cat"     gridColumn="1 / 7"   gridRow="1 / 4"/>
    <Element elementId="ctrl-access"  gridColumn="7 / 13"  gridRow="1 / 4"/>
    <Element elementId="ctrl-liq"     gridColumn="13 / 19" gridRow="1 / 4"/>
    <Element elementId="ctrl-verdict" gridColumn="19 / 25" gridRow="1 / 4"/>
  </Container>
  <Element elementId="kpi-items"     gridColumn="1 / 7"   gridRow="12 / 18"/>
  <Element elementId="kpi-value"     gridColumn="7 / 13"  gridRow="12 / 18"/>
  <Element elementId="kpi-tax"       gridColumn="13 / 19" gridRow="12 / 18"/>
  <Element elementId="kpi-killed"    gridColumn="19 / 25" gridRow="12 / 18"/>
  <Element elementId="plg-grid"      gridColumn="1 / 17"  gridRow="18 / 40"/>
  <Element elementId="chat-market"   gridColumn="17 / 25" gridRow="18 / 40"/>
  <Element elementId="chart-flipmap" gridColumn="1 / 13"  gridRow="40 / 53"/>
  <Element elementId="chart-cat"     gridColumn="13 / 25" gridRow="40 / 53"/>
  <Element elementId="tbl-top"       gridColumn="1 / 25"  gridRow="53 / 71"/>
  <Element elementId="tbl-market"    gridColumn="1 / 25"  gridRow="71 / 83"/>
</Page>"""

# ================================================================= page 2
PLAN_COLS = [
    ("b-item", "ITEM_NAME",             "Item",            None),
    ("b-is",   "INSTA_SELL",            "Buy At",          GP),
    ("b-net",  "NET_MARGIN",            "Net Margin",      GP),
    ("b-lim",  "BUY_LIMIT",             "Buy Limit",       NUM),
    ("b-vol",  "VOLUME_24H",            "Volume 24h",      NUM),
    ("b-sug",  "SUGGESTED_UNITS",       "Suggested Units", NUM),
    ("b-capf", "CAPITAL_AT_FULL_LIMIT", "Capital at Limit", GPBIG),
    ("b-proff","PROFIT_AT_FULL_LIMIT",  "Profit at Limit",  GPBIG),
]

def page2():
    els = []

    # 1. physical base at the modelling grain, then a pivot so the input table
    #    can link to it (a linked input table needs a pivot as its `from`).
    els.append(sql_table("tbl-plan", "Shortlist", PLAN,
        [col(c, f"[Custom SQL/{a}]", n, f) for c, a, n, f in PLAN_COLS]))

    els.append({"id": "pvt-plan", "kind": "pivot-table", "name": title("Shortlist pivot", INK),
        "source": {"kind": "table", "elementId": "tbl-plan"},
        "columns": [
            col("pv-item", "[Shortlist/Item]", "Item"),
            col("pv-is",   "Sum([Shortlist/Buy At])", "Buy At", GP),
            col("pv-net",  "Sum([Shortlist/Net Margin])", "Net Margin", GP),
            col("pv-lim",  "Sum([Shortlist/Buy Limit])", "Buy Limit", NUM),
            col("pv-vol",  "Sum([Shortlist/Volume 24h])", "Volume 24h", NUM),
            col("pv-sug",  "Sum([Shortlist/Suggested Units])", "Suggested Units", NUM),
        ],
        "rowsBy": [{"columnId": "pv-item"}],
        "values": ["pv-is", "pv-net", "pv-lim", "pv-vol", "pv-sug"],
        "style": PANEL_PARCH})

    # 2. parameters, declared before anything whose formulas reference them
    els.append(container("ctl-2", PARCH))
    # 3b gp: the shortlist at suggested size needs ~2.8b, so a 500m default
    # opened with a red "capital left over" and read like a broken KPI.
    els.append(number_ctrl("ctrl-capital", "CapitalGp", "Capital available (gp)", 3000000000))
    els.append(segmented("ctrl-fill", "FillRate", "Fill assumption",
                         ["Conservative", "Base", "Aggressive"], "Base"))
    els.append(text_ctrl("ctrl-note", "PlanNote", "Note for the ticket"))

    # 3. the editable plan. Rows arrive from the pivot, so the grid is populated
    #    on load; only "Units to Buy" is typed.
    els.append({"id": "it-plan", "kind": "input-table", "name": "Flip Plan",
        "source": {"kind": "linked", "from": "pvt-plan"}, "inputMode": "edit",
        "columns": [
            {"id": "ip-item", "key": "pv-item"},
            {"id": "ip-is",   "key": "pv-is"},
            {"id": "ip-net",  "key": "pv-net"},
            {"id": "ip-lim",  "key": "pv-lim"},
            {"id": "ip-sug",  "key": "pv-sug"},
            {"id": "ip-units", "type": "number", "name": "Units to Buy"},
            col("ip-eff",  "Coalesce([Units to Buy],[Suggested Units])", "Effective Units", NUM),
            col("ip-pct",  "[Effective Units] / [Buy Limit]", "Share of 4h Limit", PCT0),
            col("ip-cap",  "[Effective Units] * [Buy At]", "Capital", GPBIG),
            col("ip-fill", FILL_FORMULA, "Fill Rate", PCT0),
            col("ip-prof", "[Effective Units] * [Net Margin] * [Fill Rate]",
                "Expected Profit", GPBIG),
        ],
        "conditionalFormats": [
            cf(["ip-pct"], ">", {"color": BAD}, value=1),
            cf(["ip-units"], "IsNotNull", {"backgroundColor": ENTERED}),
        ],
        "tableStyle": {"banding": "shown", "cellSpacing": "medium"},
        "style": PANEL_PARCH})

    # 4. append-only ticket log
    els.append({"id": "it-log", "kind": "input-table", "name": "Ticket History",
        "source": {"kind": "empty", "connectionId": CONN}, "inputMode": "edit",
        "columns": [
            {"id": "lg-note",   "type": "text",   "name": "Note"},
            {"id": "lg-scen",   "type": "text",   "name": "Scenario"},
            {"id": "lg-cap",    "type": "number", "name": "Capital Committed"},
            {"id": "lg-prof",   "type": "number", "name": "Expected Profit"},
            {"id": "lg-status", "type": "multi-select", "name": "Status",
             "values": ["Submitted", "Approved", "Rejected"], "pills": "color-by-option"},
            {"id": "CREATED_AT"},
            {"id": "CREATED_BY"},
        ],
        "sort": [{"columnId": "CREATED_AT", "direction": "descending", "nulls": "last"}],
        "tableStyle": {"banding": "shown", "cellSpacing": "medium"},
        "style": PANEL_PARCH})

    # 5. KPIs off the editable plan
    els.append(kpi("kpi-deployed", "Capital deployed", "it-plan",
                   "Sum([Flip Plan/Capital])", GPBIG))
    els.append(kpi("kpi-profit", "Expected profit per cycle", "it-plan",
                   "Sum([Flip Plan/Expected Profit])", GPBIG, color=RS_GREEN))
    els.append(kpi("kpi-roi", "Blended return on capital", "it-plan",
                   "Sum([Flip Plan/Expected Profit]) / Sum([Flip Plan/Capital])", PCT,
                   color=RS_GREEN))
    els.append(kpi("kpi-left", "Capital left over", "it-plan",
                   "[CapitalGp] - Sum([Flip Plan/Capital])", GPBIG))

    els.append({"id": "chart-plan", "kind": "bar-chart",
        "name": title("Expected profit by offer"),
        "source": {"kind": "table", "elementId": "it-plan"},
        "columns": [col("cp-x", "[Flip Plan/Item]", "Item"),
                    col("cp-y", "Sum([Flip Plan/Expected Profit])", "Expected Profit", GPBIG)],
        "xAxis": {"columnId": "cp-x",
                  "sort": {"by": "cp-y", "aggregation": "sum", "direction": "descending"},
                  "format": {"labels": {"color": CREAM}, "marks": "none"}},
        "yAxis": {"columnIds": ["cp-y"], "format": AXIS_DARK},
        "orientation": "horizontal", "stacking": "none",
        "style": PANEL_DARK})

    # 6. the ticket: submit then approve, both writing an auditable row
    def ticket(status):
        return [
            # field renames live since 2026-08-26: table -> tableElementId,
            # clear-control.control -> controlId
            {"effect": "insert-rows", "tableElementId": "it-log", "values": {
                "lg-note":   {"type": "control", "control": "PlanNote"},
                "lg-scen":   {"type": "control", "control": "FillRate"},
                "lg-cap":    {"type": "formula", "formula": "Sum([Flip Plan/Capital])"},
                "lg-prof":   {"type": "formula", "formula": "Sum([Flip Plan/Expected Profit])"},
                "lg-status": {"type": "constant", "value": {"type": "text", "value": status}},
            }},
            # clear-control rejects every field shape probed on this schema
            # version (control / controlId / controlIds / scope / targets), so
            # the note is left in place rather than cleared after logging.
        ]
    els.append(button("btn-submit",  "Submit plan",  ticket("Submitted")))
    els.append(button("btn-approve", "Approve plan", ticket("Approved"),
                      fill="#3E7A4E", font="#FFFFFF"))

    # 7. header last; nothing depends on it
    els.append(container("hdr-2"))
    els.append({"id": "img-logo2", "kind": "image",
                "source": {"kind": "url", "url": LOGO},
                "alt": "Old School RuneScape", "style": {"fit": "scale-down"}})
    els.append(heading("txt-title2", gold_text("Merch Desk &mdash; Size the Trade", 30)))
    els.append(heading("txt-scope2", cream_text(
        "Type units against a 4-hour buy limit. Capital, tax-adjusted profit and "
        "return recompute on the row, then the ticket is logged with a user and a "
        "timestamp.", 12)))
    els.append({"id": "chat-merch", "kind": "chat", "agentId": "ag-merch",
                "name": "Merch Copilot"})
    return els

LAYOUT_P2 = """<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="p-desk">
  <Container elementId="hdr-2" type="grid" gridColumn="1 / 25" gridRow="1 / 8" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="img-logo2"  gridColumn="1 / 7"  gridRow="1 / 7"/>
    <Element elementId="txt-title2" gridColumn="7 / 25" gridRow="1 / 5"/>
    <Element elementId="txt-scope2" gridColumn="7 / 25" gridRow="5 / 7"/>
  </Container>
  <Container elementId="ctl-2" type="grid" gridColumn="1 / 25" gridRow="8 / 12" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-capital" gridColumn="1 / 9"   gridRow="1 / 4"/>
    <Element elementId="ctrl-fill"    gridColumn="9 / 17"  gridRow="1 / 4"/>
    <Element elementId="ctrl-note"    gridColumn="17 / 25" gridRow="1 / 4"/>
  </Container>
  <Element elementId="kpi-deployed"  gridColumn="1 / 7"   gridRow="12 / 18"/>
  <Element elementId="kpi-profit"    gridColumn="7 / 13"  gridRow="12 / 18"/>
  <Element elementId="kpi-roi"       gridColumn="13 / 19" gridRow="12 / 18"/>
  <Element elementId="kpi-left"      gridColumn="19 / 25" gridRow="12 / 18"/>
  <Element elementId="it-plan"       gridColumn="1 / 17"  gridRow="18 / 36"/>
  <Element elementId="chat-merch"    gridColumn="17 / 25" gridRow="18 / 36"/>
  <Element elementId="chart-plan"    gridColumn="1 / 25"  gridRow="36 / 49"/>
  <Element elementId="btn-submit"    gridColumn="1 / 7"   gridRow="49 / 52"/>
  <Element elementId="btn-approve"   gridColumn="7 / 13"  gridRow="49 / 52"/>
  <Element elementId="it-log"        gridColumn="1 / 25"  gridRow="52 / 66"/>
  <Element elementId="pvt-plan"      gridColumn="1 / 25"  gridRow="66 / 74"/>
  <Element elementId="tbl-plan"      gridColumn="1 / 25"  gridRow="74 / 82"/>
</Page>"""

# ================================================================= agents
TAX_RULES = (
    "Grand Exchange mechanics modelled in the data, use these exactly: the seller "
    "pays a 2% tax on the sale price, rounded DOWN, capped at 5,000,000 gp per item; "
    "there is no tax below 100 gp and none on the exempt list (Old school bond and "
    "the basic tools). Net margin = insta-buy minus insta-sell minus tax. Every item "
    "has a 4-hour buy limit, so realisable profit is net margin times units you can "
    "actually buy, six cycles a day at most. Capital per cycle = insta-sell times the "
    "buy limit; a big headline margin on a thin limit is usually worse than a small "
    "margin on a deep one."
)

AGENTS = [
  {"id": "ag-market", "name": "Market Copilot",
   "description": "Questions about the live Grand Exchange book, spreads, tax drag and liquidity.",
   "instructions":
     "You are a merchanting analyst for the Old School RuneScape Grand Exchange. The "
     "Market table is a live capture of 240 liquid items. " + TAX_RULES +
     " Spread verdict buckets an item as High ROI, Workable, Thin, No spread, or "
     "'Tax eats the spread' when the 2% tax is bigger than the whole bid-ask spread — "
     "that last group is the most interesting finding in the data and it clusters in "
     "high-unit-price gear like rune and dragon armour and in bones. Liquidity bands "
     "run Very liquid, Liquid, Moderate, Thin book. Answer in gp, use k/m/b shorthand, "
     "be quantitative and short. Name specific items. If asked what to flip, weigh ROI "
     "against the buy limit and the 24h volume rather than the raw margin, and say what "
     "capital the trade needs.",
   "greeting": {"mode": "static", "message":
     "Ask me about the live book. Good openers: 'Which items does the 2% tax make "
     "unprofitable?', 'Best return per gp of capital under 10m?', or 'Why is a rune "
     "platebody a bad flip right now?'"},
   "dataSources": [{"kind": "table", "elementId": "tbl-market"},
                   {"kind": "table", "elementId": "tbl-top"}]},

  {"id": "ag-merch", "name": "Merch Copilot",
   "description": "Sizing the plan: capital, buy limits, fill assumptions and the ticket.",
   "instructions":
     "You help size a merchanting plan on the Flip Plan table, a shortlist of 14 live "
     "Grand Exchange offers. " + TAX_RULES +
     " The reader types Units to Buy per row; blank rows fall back to Suggested Units, "
     "which is the buy limit capped at a twelfth of 24h volume so a plan cannot assume "
     "it moves more than the market will bear. Fill assumption scales expected profit: "
     "Conservative 40%, Base 70%, Aggressive 100%. Share of 4h Limit above 100% is "
     "impossible and shows red. Capital available is a parameter; Capital left over "
     "going negative means the plan is not fundable. Submitting or approving writes a "
     "row to the Ticket History with user, timestamp, scenario and the committed amounts. "
     "Be concrete about gp and about which row to change.",
   "greeting": {"mode": "static", "message":
     "Ask me to size the plan. Try 'Which row uses the most capital for the least "
     "profit?', 'What happens to profit if I switch to Conservative?', or 'Am I over "
     "any buy limit?'"},
   "dataSources": [{"kind": "table", "elementId": "it-plan"},
                   {"kind": "table", "elementId": "tbl-plan"},
                   {"kind": "table", "elementId": "it-log"}]},
]

SETTINGS = {"theme": {"overrides": {
    "colors": {"text": INK, "highlight": GOLD, "success": GOOD,
               "warning": "#C4551F", "danger": BAD, "darkMode": "hidden"},
    "colorOverrides": [{"name": "backgroundCanvas", "color": LEATHER_D},
                       {"name": "canvasBackground", "color": LEATHER_D}],
    "categoricalScheme": SCHEME,
}}}

# ================================================================= driver
def build(pages=2):
    els = page1() + (page2() if pages > 1 else [])
    pg  = [{"id": "p-market", "name": "1 · Market"}]
    lay = LAYOUT_P1
    if pages > 1:
        pg.append({"id": "p-desk", "name": "2 · Merch Desk"})
        lay = LAYOUT_P1 + "\n" + LAYOUT_P2
    ags = AGENTS if pages > 1 else [AGENTS[0]]
    return {"schemaVersion": 1, "kind": "workbook", "pages": pg, "elements": els,
            "agents": ags, "settings": SETTINGS,
            "layout": '<?xml version="1.0" encoding="utf-8"?>\n' + lay}

def api(path, method="GET", payload=None, accept_json=True):
    hdrs = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}
    if accept_json: hdrs["Accept"] = "application/json"
    r = urllib.request.Request(BASE + path, method=method,
        data=(json.dumps(payload).encode() if payload is not None else None), headers=hdrs)
    try:
        return urllib.request.urlopen(r, timeout=240).read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}\n{body[:2000]}")
        sys.exit(1)

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "create"
    pages = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    if cmd == "create":
        out = api("/v2/workbooks/spec", "POST",
                  {"name": "Grand Exchange — Merchanting Desk",
                   "folderId": FOLDER, "document": build(pages)})
        print(out.strip())
    elif cmd == "update":
        wb = sys.argv[2]
        cur = json.loads(api(f"/v2/workbooks/{wb}/spec"))
        ver = cur.get("documentVersion")
        print("current documentVersion:", ver)
        out = api(f"/v2/workbooks/{wb}/spec", "PUT",
                  {"document": build(pages), "expectedVersion": ver})
        print(out.strip())
    elif cmd == "spec":
        print(api(f"/v2/workbooks/{sys.argv[2]}/spec")[:4000])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
