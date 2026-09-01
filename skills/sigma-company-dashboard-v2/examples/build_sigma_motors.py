"""Build the "Sigma Motors" 3-page workbook in papercranestaging.

Page 1 (pg1) Production overview -- gradient hero header (real Sigma logo,
in-page navigation, Live badge), 5 icon-badged KPI cards with live Site/Shift/
Period filters, a 4-tab tabbed container (Plant performance data-bar table /
Defect trend / Plant detail / Quality holds), and a FULL-HEIGHT agent rail.

Page 2 (pg2) EV & Hybrid reallocation -- a real control-driven scenario lever
(NOT update-rows -- a button's update-rows formula has no row context, so the
BEV-shift math lives in hidden computed columns on a linked input table,
exactly the pattern proven in build_honda_ev_allocation.py), KPI comparison
cards, a baseline-vs-scenario bar chart, and a Submit-for-approval button that
writes into the same registry page 3 reads.

Page 3 (pg3) Approvals -- an append-only registry input table (starts empty --
Sigma has no way to seed static rows into a `kind:"empty"` input table at
create time; submit a scenario on page 2 to populate it), status pills, and a
real Approve action (row on-select sets a control, an Approve button applies
update-rows against it).

Usage: python3 build_sigma_motors.py [verify|create|update <id>]
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import sigmaapi as S

PAPERCRANE_ORG_ID = "8c99818a-90b3-4cae-bdb7-cf69a741171a"
CONN = "a9d45cfe-ff65-4515-8193-a7072602a1ee"

# ---------------------------------------------------------------- palette
CANVAS = "#F7F7F8"
CARD = "#FFFFFF"
BORDER = "#E5E5E9"
INK = "#111114"
MUTED = "#5F5F66"
BLUE = "#1A70F1"
BLUE_DEEP = "#0A2E70"
BLUE_DEEPER = "#06205E"
BLUE_TINT = "#EEF3FF"
ORANGE = "#C77A0A"
GOOD = "#1F9D55"
BAD = "#D14343"
STATUS_COLOR = {"Watch": ORANGE, "Recall risk": BAD, "On target": MUTED}

NUM0 = {"kind": "number", "formatString": ",.0f"}
NUM1 = {"kind": "number", "formatString": ",.1f"}
MONEYK = {"kind": "number", "formatString": "$,.3s", "currencySymbol": "$"}
PCT1 = {"kind": "number", "formatString": ".1%"}

elements, overlays, agents = [], [], []


def add(el):
    elements.append(el)
    return el["id"]


def panel(pad=None):
    s = {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1, "borderRadius": "round"}
    if pad:
        s["padding"] = pad
    return s


def title(text, size=13):
    return {"text": text, "color": INK, "fontSize": size}


def disp(c):
    return " ".join(w.capitalize() for w in c.split("_"))


def split_exact(total, weights):
    total = int(round(total))
    s = sum(weights) or 1
    raw = [total * w / s for w in weights]
    floors = [int(x) for x in raw]
    remainder = total - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: -(raw[i] - floors[i]))
    for i in range(max(remainder, 0)):
        floors[order[i % len(order)]] += 1
    return floors


def sql_values(rows):
    return ",\n    ".join(
        "(" + ", ".join("'%s'" % v.replace("'", "''") if isinstance(v, str) else str(v) for v in row) + ")"
        for row in rows)


def sql_table(eid, name, statement, colnames):
    add({"id": eid, "kind": "table", "name": name,
         "source": {"connectionId": CONN, "kind": "sql", "statement": statement},
         "columns": [{"id": "%s-%d" % (eid, i), "formula": "[Custom SQL/%s]" % c, "name": disp(c)}
                     for i, c in enumerate(colnames)]})


def icon_uri(path_d, color, bg="#FFFFFF", size=15):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 24 24" '
           'fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           '%s</svg>') % (size, size, color, path_d)
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


ICON = {
    "car": '<path d="M3 13l1.5-4.5A2 2 0 016.4 7h11.2a2 2 0 011.9 1.5L21 13"/><path d="M3 13h18v4a1 1 0 01-1 1h-1a1 1 0 01-1-1v-1H6v1a1 1 0 01-1 1H4a1 1 0 01-1-1v-4z"/><circle cx="7.5" cy="17" r="1.5"/><circle cx="16.5" cy="17" r="1.5"/>',
    "alert": '<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "dollar": '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
    "truck": '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>',
    "bolt": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "check": '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "trend": '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    "clipboard": '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>',
    "leaf": '<path d="M11 20A7 7 0 019.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    "gear": ('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 '
              '1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 '
              '2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 '
              '0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 '
              '1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 '
              '001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>'),
    "signal": '<path d="M12 20v-6M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 14 0"/><circle cx="12" cy="20" r="1.6"/>',
}


def gradient_header_bg():
    # Plain gradient + radial glow only -- the earlier car/wheel line-art was
    # drawn for a 230px-tall banner and now renders cropped/awkward against
    # the much shorter compact header. The mockup's hero was a plain gradient
    # plus a separate small watermark mark (see HEADER_WATERMARK_URI below),
    # not an illustration baked into the background itself.
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="120" viewBox="0 0 1600 120">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0.35">
      <stop offset="0%%" stop-color="%s"/>
      <stop offset="45%%" stop-color="%s"/>
      <stop offset="100%%" stop-color="%s"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.85" cy="0.15" r="0.7">
      <stop offset="0%%" stop-color="#6FA8FF" stop-opacity="0.30"/>
      <stop offset="60%%" stop-color="#6FA8FF" stop-opacity="0.08"/>
      <stop offset="100%%" stop-color="%s" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1600" height="120" fill="url(#g)"/>
  <rect width="1600" height="120" fill="url(#glow)"/>
</svg>""" % (BLUE_DEEPER, BLUE_DEEP, BLUE, BLUE)
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def header_watermark_uri():
    # Large, faded echo of the Sigma Motors bolt+road mark -- matches the
    # mockup's hero watermark (14% opacity, top-right of the banner).
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180" viewBox="0 0 100 100">
  <path d="M20,74 Q50,60 80,74" stroke="#FFFFFF" stroke-width="5" fill="none" stroke-linecap="round" opacity=".35"/>
  <path d="M32,64 L52,30 L60,30 L48,52 L64,52 L40,82 L45,60 L32,60 Z" fill="#FFFFFF" opacity=".35"/>
</svg>"""
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


LOGO_WHITE = (pathlib.Path(__file__).with_name("assets") / "sigma_logo_white.datauri.txt")
if not LOGO_WHITE.exists():
    LOGO_WHITE.write_text(
        pathlib.Path("/private/tmp/claude-502/-Users-cmiller-Desktop/43ead704-6da3-4aa0-ba20-96cb8094d67d/scratchpad/sigma_logo_white_datauri.txt").read_text().strip())
LOGO_WHITE_URI = LOGO_WHITE.read_text().strip()
HEADER_BG_URI = gradient_header_bg()
HEADER_WATERMARK_URI = header_watermark_uri()

# Sigma Motors' own emblem (not the real Sigma Computing logo) -- a lightning-
# bolt "speed mark" over a road swoosh, reused as the small badge on the
# demand-pulse plugin section too so the brand mark and the bespoke viz share
# one visual language.
SIGMA_MOTORS_LOGO = pathlib.Path(__file__).with_name("assets") / "sigma_motors_logo.datauri.txt"
SIGMA_MOTORS_LOGO_URI = SIGMA_MOTORS_LOGO.read_text().strip()


def button(eid, label, effects, fill=BLUE, font="#FFFFFF", appearance="filled"):
    return add({"id": eid, "kind": "button", "text": label, "appearance": appearance,
                "align": "stretch", "fillColor": fill, "fontColor": font, "fontWeight": "bold",
                "actions": [{"id": "a-" + eid, "trigger": "on-click", "effects": effects}]})


def page_header(page_id, page_title, page_subtitle):
    """Slim gradient nav strip: no logo, no title, no subtitle -- just the
    gradient band, the faint watermark, and the nav pills. The user hand-
    deleted the logo/title/subtitle on page 1 (kept only band+watermark+nav)
    and confirmed it looked better with less text; this now applies that
    same treatment to all three pages instead of leaving page 1 alone as an
    inconsistent exception. page_title/page_subtitle args are unused now but
    kept so call sites don't need to change if text ever comes back."""
    hdr = "hdr-" + page_id
    add({"id": hdr + "-band", "kind": "container",
         "style": {"backgroundColor": BLUE_DEEP, "borderRadius": "round", "padding": "none"},
         "backgroundImage": {"source": {"kind": "url", "url": HEADER_BG_URI}, "style": {"fit": "cover"}}})
    add({"id": hdr + "-mark", "kind": "image", "source": {"kind": "url", "url": HEADER_WATERMARK_URI},
         "style": {"fit": "contain", "align": "end", "padding": "none"}})
    add({"id": hdr + "-nav", "kind": "navigation", "mode": "manual", "showIcons": False,
         "style": {"padding": "none"},
         "optionStyle": {"textColor": {"kind": "theme", "ref": "colors-borderNeutral"}, "selectedColor": "#1a70f1",
                          "style": "pill", "orientation": "horizontal"},
         "options": [
             {"label": "Market Signal", "destination": {"type": "page", "pageId": "pg1"}},
             {"label": "EV & Hybrid reallocation", "destination": {"type": "page", "pageId": "pg2"}},
             {"label": "Approvals", "destination": {"type": "page", "pageId": "pg3"}}]})
    return hdr


HEADER_XML = """  <Container elementId="%(h)s-band" type="grid" gridColumn="1 / 25" gridRow="1 / 2" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="%(h)s-mark" gridColumn="20 / 25" gridRow="1 / 2"/>
    <Element elementId="%(h)s-nav" gridColumn="9 / 25" gridRow="1 / 2"/>
  </Container>
"""

# ==================================================================== PAGE 1 data: Market Signal
# The narrative bridge: the narrator LEARNS something here (regional EV demand
# is outpacing Hybrid and outpacing capacity to fulfill it), then ACTS on it on
# the reallocation page. A bespoke registered plugin (car icons, sized by
# backlog, glowing where growth is fastest) makes the signal visceral instead
# of another KPI table.
PLUGIN_DEMAND_PULSE_ID = "f996fb4f-db88-4f46-b481-a94cab16f9f1"  # Sigma Motors -- Regional Demand Pulse

DEMAND_REGIONS = [
    # region,       ev_backlog, hybrid_backlog, ev_prior, hybrid_prior, growth_pct, backlog_weeks, urgent
    ("West",         1135, 110, 799, 115, 42, 6.2, 1),
    ("Southwest",    1373,  73, 909,  76, 51, 5.1, 1),
    ("Midwest",       657, 122, 557, 127, 18, 2.4, 0),
    ("South",         418, 146, 394, 152,  6, 1.1, 0),
    ("Northeast",     537, 159, 493, 166,  9, 1.6, 0),
]
demand_sql = ("SELECT * FROM VALUES\n    %s\n  AS d(region, ev_backlog, hybrid_backlog, ev_backlog_prior, "
              "hybrid_backlog_prior, growth_pct, backlog_weeks, urgent_flag)" % sql_values(DEMAND_REGIONS))
add({"id": "sql-demand", "kind": "table", "name": "Regional Demand",
     "source": {"connectionId": CONN, "kind": "sql", "statement": demand_sql},
     "columns": [{"id": "dm-region", "formula": "[Custom SQL/region]", "name": "Region"},
                 {"id": "dm-ev", "formula": "[Custom SQL/ev_backlog]", "name": "EV Backlog"},
                 {"id": "dm-hy", "formula": "[Custom SQL/hybrid_backlog]", "name": "Hybrid Backlog"},
                 {"id": "dm-evp", "formula": "[Custom SQL/ev_backlog_prior]", "name": "EV Backlog Prior"},
                 {"id": "dm-hyp", "formula": "[Custom SQL/hybrid_backlog_prior]", "name": "Hybrid Backlog Prior"},
                 {"id": "dm-growth", "formula": "[Custom SQL/growth_pct]", "name": "Growth Pct"},
                 {"id": "dm-weeks", "formula": "[Custom SQL/backlog_weeks]", "name": "Backlog Weeks"},
                 {"id": "dm-urgent", "formula": "[Custom SQL/urgent_flag]", "name": "Urgent Flag"}]})

add({"id": "kd-evwait", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-evwait-v", "formula": "Sum([Regional Demand/EV Backlog])", "name": "EV waitlist (fleet-wide)", "format": NUM0},
                 {"id": "kd-evwait-c", "formula": "Sum([Regional Demand/EV Backlog Prior])", "name": "Prior", "format": NUM0}],
     "value": {"columnId": "kd-evwait-v", "color": INK, "fontSize": 26},
     "comparisonColumn": {"columnId": "kd-evwait-c"},
     "comparison": {"display": "delta", "fontSize": 11, "colorGood": GOOD, "colorBad": BAD},
     "name": title("EV WAITLIST (FLEET-WIDE)", 11), "style": panel(), "layout": {"anchor": "start"}})
add({"id": "kd-hywait", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-hywait-v", "formula": "Sum([Regional Demand/Hybrid Backlog])", "name": "Hybrid waitlist", "format": NUM0},
                 {"id": "kd-hywait-c", "formula": "Sum([Regional Demand/Hybrid Backlog Prior])", "name": "Prior", "format": NUM0}],
     "value": {"columnId": "kd-hywait-v", "color": INK, "fontSize": 26},
     "comparisonColumn": {"columnId": "kd-hywait-c"},
     "comparison": {"display": "delta", "fontSize": 11, "colorGood": GOOD, "colorBad": BAD},
     "name": title("HYBRID WAITLIST", 11), "style": panel(), "layout": {"anchor": "start"}})
add({"id": "kd-backlog", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-backlog-v", "formula": "Max([Regional Demand/Backlog Weeks])", "name": "Longest regional backlog", "format": NUM1}],
     "value": {"columnId": "kd-backlog-v", "color": BAD, "fontSize": 26},
     "name": title("LONGEST BACKLOG (WKS)", 11), "style": panel(), "layout": {"anchor": "start"}})
add({"id": "kd-margin", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-margin-v", "formula": "Sum([Regional Demand/EV Backlog]) * 437", "name": "Margin left on the table", "format": MONEYK}],
     "value": {"columnId": "kd-margin-v", "color": BAD, "fontSize": 26},
     "name": title("EST. MARGIN LEFT ON TABLE", 11), "style": panel(), "layout": {"anchor": "start"}})
add({"id": "kd-regions", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-regions-v", "formula": "Sum([Regional Demand/Urgent Flag])", "name": "Regions past threshold", "format": NUM0}],
     "value": {"columnId": "kd-regions-v", "color": BAD, "fontSize": 26},
     "name": title("REGIONS PAST THRESHOLD", 11), "style": panel(), "layout": {"anchor": "start"}})

add({"id": "c-demand-panel", "kind": "container", "style": panel()})
add({"id": "demand-badge", "kind": "image", "source": {"kind": "url", "url": icon_uri(
    '<path d="M12 20v-6M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 14 0" stroke-width="2.4"/>', "#FFFFFF", bg=BLUE, size=15)},
    "style": {"fit": "contain", "backgroundColor": BLUE, "padding": "none"}})
add({"id": "demand-title", "kind": "text", "body": "**Regional demand pulse**",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none"}, "verticalAlign": "middle"})
add({"id": "demand-sub", "kind": "text",
     "body": '<span style="color:%s">Ring size = total backlog, center %% = EV share, glow = growing fast &mdash; ranked by EV backlog at right</span>' % MUTED,
     "style": {"backgroundColor": CARD, "padding": "none"}, "verticalAlign": "middle"})
add({"id": "plg-demand", "kind": "plugin", "pluginId": PLUGIN_DEMAND_PULSE_ID,
     "displayName": "Regional Demand Pulse",
     "config": {"source": {"kind": "element", "elementId": "sql-demand"},
                "region": "dm-region", "ev_backlog": "dm-ev", "hybrid_backlog": "dm-hy",
                "growth_pct": "dm-growth", "backlog_weeks": "dm-weeks"},
     "style": {"backgroundColor": CARD}})

# Dashboard best practice: pair the illustrative pulse with a precise,
# scannable view of the SAME data -- ranked bars let you read exact numbers
# in seconds instead of eyeballing ring sizes.
add({"id": "bar-demand", "kind": "bar-chart", "name": "EV backlog by region, ranked",
     "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [
         {"id": "bd-region", "formula": "[Regional Demand/Region]", "name": "Region"},
         {"id": "bd-ev", "formula": "Sum([Regional Demand/EV Backlog])", "name": "EV Backlog", "format": NUM0}],
     "xAxis": {"columnId": "bd-region"}, "yAxis": {"columnIds": ["bd-ev"]},
     "sortBy": {"columnId": "bd-ev", "direction": "descending"},
     "orientation": "horizontal",
     "colorAssignment": {"palette": {"scheme": [BLUE], "type": "categorical"}},
     "legend": {"visibility": "hidden"}, "style": {"backgroundColor": CARD, "padding": "none"}})

DEMAND_AI_PROMPT = (
    '"You are a demand-planning analyst at an automaker. Fleet-wide EV order backlog is "'
    ' & Text(Sum([Regional Demand/EV Backlog])) & '
    '" units, up from " & Text(Sum([Regional Demand/EV Backlog Prior])) & '
    '" 30 days ago, while Hybrid backlog is " & Text(Sum([Regional Demand/Hybrid Backlog])) & '
    '" units (roughly flat). The worst-hit region is backlogged " & Text(Round(Max([Regional Demand/Backlog Weeks]),1)) & '
    '" weeks, and " & Text(Sum([Regional Demand/Urgent Flag])) & " of 5 regions are growing over 25% per month. '
    'Unclaimed margin from this gap is roughly $" & Text(Round(Sum([Regional Demand/EV Backlog])*437/1000000,1)) & '
    '"M. In 2-3 sentences, tell a plant operations leader what is happening and why they should consider shifting '
    'production mix toward EV to respond."'
)
add({"id": "c-ai-signal", "kind": "container",
     "style": {"backgroundColor": BLUE_TINT, "borderColor": BLUE, "borderWidth": 1, "borderRadius": "round"}})
add({"id": "ai-signal-icon", "kind": "image",
     "source": {"kind": "url", "url": icon_uri(ICON["bolt"], BLUE_DEEP, bg=BLUE_TINT, size=13)},
     "style": {"fit": "contain", "backgroundColor": BLUE_TINT, "padding": "none"}})
add({"id": "ai-signal-title", "kind": "text", "body": "**AI INSIGHT**",
     "style": {"color": BLUE_DEEP, "backgroundColor": BLUE_TINT, "padding": "none"}, "verticalAlign": "middle"})
add({"id": "txt-ai-signal", "kind": "text",
     "body": '{{ Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", "CLAUDE-4-SONNET", %s), \'"\', \'\') }}' % DEMAND_AI_PROMPT,
     "style": {"color": INK, "backgroundColor": BLUE_TINT, "padding": "none"}, "verticalAlign": "middle"})

add({"id": "cta-msg", "kind": "text",
     "body": "**You've seen the signal. Now model the response.**  \nShift production toward EV to chase this demand — without breaking a plant's battery-cell contract.",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none"}, "verticalAlign": "middle"})
button("btn-model-response", "Model a production response →", [
    {"effect": "set-control-value", "control": "c_ev_shift",
     "value": {"type": "constant", "value": {"type": "number", "value": 14}}},
    {"effect": "navigate", "target": {"type": "page", "page": "pg2"}}], fill=BLUE)

# ==================================================================== PAGE 2 data (EV & Hybrid reallocation)
# The story: shifting toward EV isn't free. EVs draw ~5x the battery kWh per
# unit that a Hybrid does, and every plant has both a physical assembly
# capacity ceiling and a contracted battery-cell supply ceiling. Baseline is
# tuned so Austin/Detroit/Monterrey are already running tight against one or
# both constraints -- so a real EV push forces a real tradeoff, not a free
# lunch.
PLANT_SHARE = {"Detroit": 0.40, "Austin": 0.31, "Monterrey": 0.17, "Columbus": 0.06, "Greenville": 0.06}
PLANT_CAPACITY = {"Detroit": 5400, "Austin": 4200, "Monterrey": 2500, "Columbus": 900, "Greenville": 1000}
CELL_TARGET_UTIL = {"Detroit": 0.90, "Austin": 0.90, "Monterrey": 0.92, "Columbus": 0.85, "Greenville": 0.85}
CELL_KWH = {"EV": 75, "Hybrid": 14}
EV_BASELINE_TOTAL = 5600
HY_BASELINE_TOTAL = 7300

alloc_rows = []
TOTAL_CELL_CONTRACT = 0
for plant, share in PLANT_SHARE.items():
    ev_u = round(EV_BASELINE_TOTAL * share)
    hy_u = round(HY_BASELINE_TOTAL * share)
    baseline_cell = ev_u * CELL_KWH["EV"] + hy_u * CELL_KWH["Hybrid"]
    contract = round(baseline_cell / CELL_TARGET_UTIL[plant])
    cap = PLANT_CAPACITY[plant]
    TOTAL_CELL_CONTRACT += contract
    alloc_rows.append((plant, "EV", ev_u, CELL_KWH["EV"], cap, contract))
    alloc_rows.append((plant, "Hybrid", hy_u, CELL_KWH["Hybrid"], cap, contract))
TOTAL_CAPACITY = sum(PLANT_CAPACITY.values())
FLEET_TOTAL = EV_BASELINE_TOTAL + HY_BASELINE_TOTAL
# Closed form (holds exactly -- every plant's EV:Hybrid baseline ratio equals
# the fleet ratio, so a shift never changes any single plant's total volume):
#   EV units       = 5600 + 56*shift          Hybrid units = 7300 - 56*shift
#   Margin impact  = (EV units - 5600) * 750  = 42000*shift
#   Cell kWh total = EV*75 + Hybrid*14        = 522200 + 3416*shift
#   Capacity used  = 12900 / TOTAL_CAPACITY   (constant -- volume never moves)
EV_SLOPE = round(EV_BASELINE_TOTAL / 100.0)  # 56
CELL_KWH_BASE = EV_BASELINE_TOTAL * CELL_KWH["EV"] + HY_BASELINE_TOTAL * CELL_KWH["Hybrid"]
CELL_KWH_SLOPE = EV_SLOPE * (CELL_KWH["EV"] - CELL_KWH["Hybrid"])

alloc_sql = ("SELECT * FROM VALUES\n    %s\n  AS a(plant, powertrain, baseline_units, "
             "cell_kwh_per_unit, plant_capacity, cell_kwh_contracted)" % sql_values(alloc_rows))
add({"id": "sql-alloc", "kind": "table", "name": "Allocation Baseline",
     "source": {"connectionId": CONN, "kind": "sql", "statement": alloc_sql},
     "columns": [{"id": "ab-plant", "formula": "[Custom SQL/plant]", "name": "Plant"},
                 {"id": "ab-pt", "formula": "[Custom SQL/powertrain]", "name": "Powertrain"},
                 {"id": "ab-base", "formula": "[Custom SQL/baseline_units]", "name": "Baseline Units"},
                 {"id": "ab-cellkwh", "formula": "[Custom SQL/cell_kwh_per_unit]", "name": "Cell Kwh Per Unit"},
                 {"id": "ab-cap", "formula": "[Custom SQL/plant_capacity]", "name": "Plant Capacity"},
                 {"id": "ab-cellcap", "formula": "[Custom SQL/cell_kwh_contracted]", "name": "Cell Kwh Contracted"}]})

add({"id": "ctrl-ev-shift", "kind": "control", "controlId": "c_ev_shift", "name": "EV share shift",
     "controlType": "number", "mode": "=", "includeNulls": "when-no-value-is-selected", "value": 0})

add({"id": "it-alloc", "kind": "input-table", "name": "Allocation Plan",
     "inputMode": "view", "source": {"kind": "linked", "from": "sql-alloc"},
     "columns": [
         {"id": "al-plant", "key": "ab-plant", "name": "Plant"},
         {"id": "al-pt", "key": "ab-pt", "name": "Powertrain"},
         {"id": "al-base", "key": "ab-base", "name": "Baseline Units"},
         {"id": "al-prop", "type": "number", "name": "Manual Override"},
         {"id": "al-factor", "name": "Scenario Factor", "hidden": True,
          "formula": 'If([Powertrain] = "EV", 1 + [c_ev_shift] / 100, '
                     '1 - [c_ev_shift] / 100 * (5600.0 / 7300.0))'},
         {"id": "al-scen", "name": "Scenario Units", "hidden": True,
          "formula": "Round([Baseline Units] * [Scenario Factor])", "format": NUM0},
         {"id": "al-eff", "formula": "Coalesce([Manual Override], [Scenario Units])",
          "name": "Effective Units", "format": NUM0},
     ],
     "sort": [{"columnId": "al-plant", "direction": "ascending"}],
     "conditionalFormats": [{"type": "dataBars", "columnIds": ["al-eff"], "scheme": [BLUE_TINT, BLUE]}],
     "tableComponents": {"summaryBar": "hidden"}, "style": panel()})

# ---------------------------------------------------------------- capacity & battery-cell commitment (the tension)
# Sourced straight from the baseline SQL table (not the linked input-table --
# key columns on an existing linked input-table are locked after creation) and
# recomputes the same scenario-factor math independently.
add({"id": "tbl-capacity", "kind": "table", "name": "Capacity & Battery Commitment",
     "description": {"visibility": "shown", "text": "Physical assembly capacity and contracted battery-cell supply, by plant"},
     "source": {"elementId": "sql-alloc", "kind": "table"},
     "columns": [
         {"id": "cp-plant", "formula": "[Allocation Baseline/Plant]", "name": "Plant"},
         {"id": "cp-pt", "formula": "[Allocation Baseline/Powertrain]", "name": "Powertrain", "hidden": True},
         {"id": "cp-factor", "hidden": True, "name": "Factor",
          "formula": 'If([Powertrain] = "EV", 1 + [c_ev_shift] / 100, '
                     '1 - [c_ev_shift] / 100 * (5600.0 / 7300.0))'},
         {"id": "cp-rowunits", "hidden": True, "name": "Row Units",
          "formula": "Round([Allocation Baseline/Baseline Units] * [Factor])"},
         {"id": "cp-rowcells", "hidden": True, "name": "Row Cell Kwh",
          "formula": "[Row Units] * [Allocation Baseline/Cell Kwh Per Unit]"},
         {"id": "cp-eff", "formula": "Sum([Row Units])", "name": "Units", "format": NUM0},
         {"id": "cp-cap", "formula": "Max([Allocation Baseline/Plant Capacity])", "name": "Capacity", "format": NUM0, "hidden": True},
         {"id": "cp-util", "formula": "[Units] / [Capacity]", "name": "Capacity Used", "format": PCT1},
         {"id": "cp-cells", "formula": "Sum([Row Cell Kwh])", "name": "Cell kWh", "format": NUM0, "hidden": True},
         {"id": "cp-cellcap", "formula": "Max([Allocation Baseline/Cell Kwh Contracted])", "name": "Cell Contract", "format": NUM0, "hidden": True},
         {"id": "cp-cellutil", "formula": "[Cell kWh] / [Cell Contract]", "name": "Cell Commitment", "format": PCT1},
         {"id": "cp-flag", "formula": 'If([Capacity Used] > 1, "Over capacity", "Within capacity")', "name": "Capacity Status", "hidden": True},
         {"id": "cp-cellflag", "formula": 'If([Cell Commitment] > 1, "Over contract", "Within contract")', "name": "Cell Status", "hidden": True},
     ],
     "groupings": [{"id": "cpg", "groupBy": ["cp-plant"],
                    "calculations": ["cp-eff", "cp-cap", "cp-util", "cp-cells", "cp-cellcap", "cp-cellutil",
                                     "cp-flag", "cp-cellflag"],
                    "sort": [{"columnId": "cp-cellutil", "direction": "descending"}]}],
     "conditionalFormats": [
         {"type": "dataBars", "columnIds": ["cp-cellutil"], "scheme": [BLUE_TINT, ORANGE]},
         {"type": "single", "columnIds": ["cp-util"], "condition": ">", "value": 1.0,
          "style": {"backgroundColor": "#FCEBEB", "color": BAD, "bold": True}},
         {"type": "single", "columnIds": ["cp-cellutil"], "condition": ">", "value": 1.0,
          "style": {"backgroundColor": "#FCEBEB", "color": BAD, "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"}, "style": panel()})

add({"id": "kr-capused", "kind": "kpi-chart", "source": {"elementId": "tbl-capacity", "kind": "table"},
     "columns": [{"id": "kc-v",
                  "formula": "Sum([Capacity & Battery Commitment/Units]) / Sum([Capacity & Battery Commitment/Capacity])",
                  "name": "Plant capacity used", "format": PCT1},
                 {"id": "kc-c", "formula": "1.0", "name": "Ceiling", "format": PCT1}],
     "value": {"columnId": "kc-v", "color": INK, "fontSize": 22},
     "comparisonColumn": {"columnId": "kc-c"},
     "comparison": {"display": "delta", "direction": "none", "colorNeutral": MUTED},
     "name": title("PLANT CAPACITY USED", 10), "style": panel(), "layout": {"anchor": "start"}})
add({"id": "kr-cellused", "kind": "kpi-chart", "source": {"elementId": "tbl-capacity", "kind": "table"},
     "columns": [{"id": "kl-v",
                  "formula": "Sum([Capacity & Battery Commitment/Cell kWh]) / Sum([Capacity & Battery Commitment/Cell Contract])",
                  "name": "Battery cell used", "format": PCT1},
                 {"id": "kl-c", "formula": "1.0", "name": "Ceiling", "format": PCT1}],
     "value": {"columnId": "kl-v", "color": INK, "fontSize": 22},
     "comparisonColumn": {"columnId": "kl-c"},
     "comparison": {"display": "delta", "direction": "none", "colorNeutral": MUTED},
     "name": title("BATTERY CELL USED", 10), "style": panel(), "layout": {"anchor": "start"}})

# ---------------------------------------------------------------- live AI insight (real LLM call over real data)
AI_PROMPT = (
    '"You are a manufacturing operations analyst advising an automaker\'\'s executive team on how to grow margin. Current baseline production is 5,600 EV units and 7,300 Hybrid units. A planner is evaluating a "'
    ' & Text([c_ev_shift]) & '
    '"% shift of production mix toward EV (positive number) or Hybrid (negative number), which would move margin by roughly $"'
    ' & Text(Round([c_ev_shift] * 42)) & '
    '"K (EVs carry a higher per-unit margin than Hybrids) and change production to "'
    ' & Text(SumIf([Allocation Plan/Effective Units], [Allocation Plan/Powertrain] = "EV")) & '
    '" EV units and "'
    ' & Text(SumIf([Allocation Plan/Effective Units], [Allocation Plan/Powertrain] = "Hybrid")) & '
    '" Hybrid units. At that level, fleet-wide plant capacity utilization would be "'
    ' & Text(Round(100*Sum([Capacity & Battery Commitment/Units])/Sum([Capacity & Battery Commitment/Capacity]),1)) & '
    '"%, and battery-cell supply-contract commitment would be "'
    ' & Text(Round(100*Sum([Capacity & Battery Commitment/Cell kWh])/Sum([Capacity & Battery Commitment/Cell Contract]),1)) & '
    '"%. In 2-3 sentences, tell the executive team whether this shift is achievable given plant capacity and battery-cell supply, and name the binding constraint if either is at risk of being breached. If the shift is 0%, just describe the current baseline position instead of a change."'
)
# NOTE: the "Responding to" banner and the live mini-echo of the demand-pulse
# plugin (tbl-demand-live/plg-demand-live/demand-live-label) were hand-deleted
# from the live workbook -- removed here too so a future `update` doesn't
# resurrect them.

add({"id": "c-ai", "kind": "container",
     "style": {"backgroundColor": BLUE_TINT, "borderColor": BLUE, "borderWidth": 1, "borderRadius": "round"}})
add({"id": "ai-title-icon", "kind": "image",
     "source": {"kind": "url", "url": icon_uri(ICON["bolt"], BLUE_DEEP, bg=BLUE_TINT, size=13)},
     "style": {"fit": "contain", "backgroundColor": BLUE_TINT, "padding": "none"}})
add({"id": "ai-title", "kind": "text", "body": "**AI INSIGHT**",
     "style": {"color": BLUE_DEEP, "backgroundColor": BLUE_TINT, "padding": "none"}, "verticalAlign": "middle"})
add({"id": "txt-ai", "kind": "text",
     "body": '{{ Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", "CLAUDE-4-SONNET", %s), \'"\', \'\') }}' % AI_PROMPT,
     "style": {"color": INK, "backgroundColor": BLUE_TINT, "padding": "none"}, "verticalAlign": "middle"})

EFF = "[Allocation Plan/Effective Units]"
add({"id": "kr-ev", "kind": "kpi-chart", "source": {"elementId": "it-alloc", "kind": "table"},
     "columns": [{"id": "kr-ev-v", "formula": 'SumIf(%s, [Allocation Plan/Powertrain] = "EV")' % EFF,
                  "name": "EV units", "format": NUM0},
                 {"id": "kr-ev-c", "formula": 'SumIf([Allocation Plan/Baseline Units], [Allocation Plan/Powertrain] = "EV")',
                  "name": "Baseline", "format": NUM0}],
     "value": {"columnId": "kr-ev-v", "color": INK, "fontSize": 24},
     "comparisonColumn": {"columnId": "kr-ev-c"},
     "comparison": {"display": "delta", "colorGood": GOOD, "colorBad": BAD},
     "name": title("EV UNITS", 11), "style": panel(), "layout": {"anchor": "start"}})
add({"id": "kr-hy", "kind": "kpi-chart", "source": {"elementId": "it-alloc", "kind": "table"},
     "columns": [{"id": "kr-hy-v", "formula": 'SumIf(%s, [Allocation Plan/Powertrain] = "Hybrid")' % EFF,
                  "name": "Hybrid units", "format": NUM0},
                 {"id": "kr-hy-c", "formula": 'SumIf([Allocation Plan/Baseline Units], [Allocation Plan/Powertrain] = "Hybrid")',
                  "name": "Baseline", "format": NUM0}],
     "value": {"columnId": "kr-hy-v", "color": INK, "fontSize": 24},
     "comparisonColumn": {"columnId": "kr-hy-c"},
     "comparison": {"display": "delta", "colorGood": BAD, "colorBad": GOOD},
     "name": title("HYBRID UNITS", 11), "style": panel(), "layout": {"anchor": "start"}})
add({"id": "kr-margin", "kind": "kpi-chart", "source": {"elementId": "it-alloc", "kind": "table"},
     "columns": [{"id": "kr-margin-v",
                  "formula": '(SumIf(%s, [Allocation Plan/Powertrain] = "EV") - 5600) * 750' % EFF,
                  "name": "Margin impact", "format": MONEYK}],
     "value": {"columnId": "kr-margin-v", "color": GOOD, "fontSize": 24},
     "name": title("MARGIN IMPACT", 11), "style": panel(), "layout": {"anchor": "start"}})
add({"id": "kr-total", "kind": "kpi-chart", "source": {"elementId": "it-alloc", "kind": "table"},
     "columns": [{"id": "kr-total-v", "formula": "Sum(%s)" % EFF, "name": "Total capacity", "format": NUM0}],
     "value": {"columnId": "kr-total-v", "color": INK, "fontSize": 24},
     "name": title("TOTAL CAPACITY", 11),
     "style": panel(),
     "layout": {"anchor": "start"}})

add({"id": "c-slider", "kind": "container", "style": panel()})
add({"id": "slider-label", "kind": "text", "body": "**Reallocate production mix**",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none"}})
add({"id": "ctrl-ev-shift-ui", "kind": "control", "controlId": "c_ev_shift_ui", "name": "EV share",
     "controlType": "number-range", "mode": "between",
     "filters": []})

# ---------------------------------------------------------------- production trend (the rollout, not just the endpoint)
# A shift like this isn't flipped on overnight -- plants ramp toward the new
# mix over months. This turns the lever into a forecast: "if I commit today,
# here's how EV vs Hybrid output actually ramps over the next 2 quarters."
RAMP_MONTHS = [(0, "Mo 0 - now"), (1, "Mo 1"), (2, "Mo 2"), (3, "Mo 3"), (4, "Mo 4"), (5, "Mo 5"), (6, "Mo 6")]
ramp_rows = [(m, label, m / 6.0) for m, label in RAMP_MONTHS]
ramp_sql = "SELECT * FROM VALUES\n    %s\n  AS r(month_idx, month_label, ramp_fraction)" % sql_values(ramp_rows)
add({"id": "sql-ramp", "kind": "table", "name": "Rollout Months",
     "source": {"connectionId": CONN, "kind": "sql", "statement": ramp_sql},
     "columns": [{"id": "rm-idx", "formula": "[Custom SQL/month_idx]", "name": "Month Index"},
                 {"id": "rm-label", "formula": "[Custom SQL/month_label]", "name": "Month"},
                 {"id": "rm-frac", "formula": "[Custom SQL/ramp_fraction]", "name": "Ramp Fraction"}]})
add({"id": "ch-trend", "kind": "line-chart", "name": "Production rollout",
     "description": {"visibility": "shown", "text": "EV vs Hybrid output as the plant ramps toward your scenario over the next 6 months"},
     "source": {"elementId": "sql-ramp", "kind": "table"},
     "columns": [
         {"id": "rt-idx", "formula": "[Rollout Months/Month Index]", "name": "Month Order", "hidden": True},
         {"id": "rt-label", "formula": "[Rollout Months/Month]", "name": "Month"},
         {"id": "rt-ev", "formula": "%d + %d * [c_ev_shift] * [Rollout Months/Ramp Fraction]" % (EV_BASELINE_TOTAL, EV_SLOPE),
          "name": "EV units", "format": NUM0},
         {"id": "rt-hy", "formula": "%d - %d * [c_ev_shift] * [Rollout Months/Ramp Fraction]" % (HY_BASELINE_TOTAL, EV_SLOPE),
          "name": "Hybrid units", "format": NUM0}],
     "xAxis": {"columnId": "rt-label"},
     "yAxis": {"columnIds": ["rt-ev", "rt-hy"]},
     "colorAssignment": {"palette": {"scheme": [BLUE, MUTED], "type": "categorical"}},
     "legend": {"visibility": "shown"}, "style": panel()})
add({"id": "c-trend-col", "kind": "container", "style": {"backgroundColor": CANVAS, "padding": "none"}})

button("btn-reset", "Reset to baseline", [
    {"effect": "set-control-value", "control": "c_ev_shift",
     "value": {"type": "constant", "value": {"type": "number", "value": 0}}},
    {"effect": "update-rows", "tableElementId": "it-alloc",
     "whichRows": {"type": "formula", "formula": "True"},
     "values": {"al-prop": {"type": "constant", "value": {"type": "number", "value": None}}}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-alloc"}}],
    fill=CARD, font=INK, appearance="outline")
button("btn-submit", "Save & submit for approval", [
    {"effect": "insert-rows", "tableElementId": "it-registry", "values": {
        "reg-id": {"type": "formula", "formula": '"SCN-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
        "reg-name": {"type": "formula",
                     "formula": '"EV/Hybrid mix – " & DateFormat(Now(), "%b %d, %H:%M")'},
        "reg-type": {"type": "constant", "value": {"type": "text", "value": "Reallocation"}},
        "reg-owner": {"type": "constant", "value": {"type": "text", "value": "C. Miller"}},
        "reg-status": {"type": "constant", "value": {"type": "text", "value": "Submitted"}}}},
    {"effect": "navigate", "target": {"type": "page", "page": "pg3"}}], fill=BLUE)

# ---------------------------------------------------------------- scenario studio (create -> save -> compare -> decide)
# The profit story: every scenario is a bet on which powertrain mix earns the
# most margin without breaching a plant's capacity or battery-cell contract.
# Name a scenario, the lever position is captured as a frozen snapshot (not
# live-linked), and every saved scenario lines up in one dense comparison
# table so the best (and worst) bets are obvious side by side.
add({"id": "it-scenarios", "kind": "input-table", "name": "Scenario Studio",
     "inputMode": "view", "source": {"kind": "empty", "connectionId": CONN},
     "columns": [
         {"id": "sc-id", "name": "Scenario ID", "type": "text", "hidden": True},
         {"id": "sc-name", "name": "Scenario", "type": "text"},
         {"id": "sc-shift", "name": "EV shift", "type": "number", "format": NUM0},
         {"id": "sc-ev", "name": "EV units", "hidden": True,
          "formula": "%d + %d * [EV shift]" % (EV_BASELINE_TOTAL, EV_SLOPE), "format": NUM0},
         {"id": "sc-hy", "name": "Hybrid units", "hidden": True,
          "formula": "%d - %d * [EV shift]" % (HY_BASELINE_TOTAL, EV_SLOPE), "format": NUM0},
         {"id": "sc-margin", "name": "Margin impact",
          "formula": "%d * [EV shift]" % (EV_SLOPE * 750), "format": MONEYK},
         {"id": "sc-capused", "name": "Capacity used",
          "formula": "%d / %d" % (FLEET_TOTAL, TOTAL_CAPACITY), "format": PCT1},
         {"id": "sc-cellused", "name": "Cell used",
          "formula": "(%d + %d * [EV shift]) / %d" % (CELL_KWH_BASE, CELL_KWH_SLOPE, TOTAL_CELL_CONTRACT), "format": PCT1},
         {"id": "sc-feasible", "name": "Feasible?", "hidden": True,
          "formula": 'If([Cell used] <= 1, "Feasible", "Breaches battery-cell contract")'},
         {"id": "ID", "name": "Row ID", "hidden": True},
         {"id": "CREATED_AT", "name": "Created At", "hidden": True},
         {"id": "UPDATED_AT", "name": "Updated At", "hidden": True},
         {"id": "CREATED_BY", "name": "Created By", "hidden": True}],
     "sort": [{"columnId": "CREATED_AT", "direction": "ascending", "nulls": "last"}],
     "conditionalFormats": [
         {"type": "dataBars", "columnIds": ["sc-margin"], "scheme": [BLUE_TINT, GOOD]},
         {"type": "single", "columnIds": ["sc-cellused"], "condition": ">", "value": 1.0,
          "style": {"backgroundColor": "#FCEBEB", "color": BAD, "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"}, "style": panel()})
add({"id": "ctrl-scenario-name", "kind": "control", "controlId": "c_scenario_name", "name": "Scenario name",
     "controlType": "text", "case": "insensitive", "mode": "contains",
     "includeNulls": "when-no-value-is-selected", "showOperators": False})
button("btn-create-scenario", "Create scenario", [
    {"effect": "insert-rows", "tableElementId": "it-scenarios", "values": {
        "sc-id": {"type": "formula", "formula": '"SC-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
        "sc-name": {"type": "formula",
                    "formula": 'Coalesce(NullIf([c_scenario_name], ""), "Scenario") & " (" & Text([c_ev_shift]) & "%)"'},
        "sc-shift": {"type": "control", "control": "c_ev_shift"}}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-scenarios"}},
    {"effect": "clear-control", "scope": {"type": "control", "controlId": "c_scenario_name"}}], fill=BLUE)
button("btn-open-compare", "+ New scenario", [{"effect": "open-overlay", "overlayId": "m-scenarios"}],
       fill=CARD, font=BLUE, appearance="outline")

overlays.append({
    "id": "m-scenarios", "type": "modal", "name": "Scenario studio",
    "modal": {"width": "large", "header": {"title": " ", "showCloseIcon": "shown"},
              "footer": {"primaryCta": {"visible": "hidden"}, "secondaryCta": {"visible": "hidden"}}}})
add({"id": "ms-band", "kind": "container",
     "style": {"backgroundColor": BLUE_DEEP, "borderRadius": "round", "padding": "none"},
     "backgroundImage": {"source": {"kind": "url", "url": HEADER_BG_URI}, "style": {"fit": "cover"}}})
add({"id": "ms-logo", "kind": "image", "source": {"kind": "url", "url": SIGMA_MOTORS_LOGO_URI},
     "style": {"fit": "contain", "align": "start", "padding": "none"}})
add({"id": "ms-title", "kind": "text",
     "body": '<span style="color:#FFFFFF">**Scenario studio**</span>',
     "style": {"padding": "none"}, "verticalAlign": "middle"})
add({"id": "ms-sub", "kind": "text",
     "body": "Every scenario keeps its own frozen snapshot of the lever, so you can create several bets and compare which one wins on margin without breaching a constraint.",
     "style": {"color": MUTED, "backgroundColor": CANVAS, "padding": "none"}})
add({"id": "ms-create-label", "kind": "text", "body": "**Create a new scenario**",
     "style": {"color": INK, "backgroundColor": CANVAS, "padding": "none"}, "verticalAlign": "middle"})
add({"id": "ms-create-hint", "kind": "text",
     "body": '<span style="color:%s">Captures the EV share shift you currently have set on the reallocation page.</span>' % MUTED,
     "style": {"backgroundColor": CANVAS, "padding": "none"}, "verticalAlign": "middle"})
add({"id": "ms-saved-label", "kind": "text", "body": "**Saved scenarios**",
     "style": {"color": INK, "backgroundColor": CANVAS, "padding": "none"}, "verticalAlign": "middle"})
button("btn-close-compare", "Done", [{"effect": "close-overlay"}], fill=CARD, font=MUTED, appearance="outline")

# ==================================================================== PAGE 3 data (Approvals)
add({"id": "it-registry", "kind": "input-table", "name": "Scenario Registry",
     "inputMode": "view", "source": {"kind": "empty", "connectionId": CONN},
     "columns": [
         {"id": "reg-id", "name": "Scenario ID", "type": "text", "hidden": True},
         {"id": "reg-name", "name": "Scenario", "type": "text"},
         {"id": "reg-type", "name": "Type", "type": "text"},
         {"id": "reg-owner", "name": "Submitted by", "type": "text"},
         {"id": "reg-status", "name": "Status", "type": "text",
          "values": ["Draft", "Submitted", "Approved", "Rejected"]},
         {"id": "reg-comments", "name": "Reviewer comments", "type": "text"},
         {"id": "ID", "name": "Row ID", "hidden": True},
         {"id": "CREATED_AT", "name": "Created At"},
         {"id": "UPDATED_AT", "name": "Updated At", "hidden": True},
         {"id": "CREATED_BY", "name": "Created By", "hidden": True}],
     "actions": [{"id": "act-select-reg", "trigger": "on-select", "effects": [
         {"effect": "set-control-value", "control": "c_selected_scenario",
          "value": {"type": "column", "columnId": "reg-id"}},
         {"effect": "open-overlay", "overlayId": "m-review"}]}],
     "sort": [{"columnId": "CREATED_AT", "direction": "descending", "nulls": "last"}],
     "conditionalFormats": [
         {"type": "single", "columnIds": ["reg-status"], "condition": "=", "value": "Approved",
          "style": {"backgroundColor": "#E6F4EA", "color": GOOD, "bold": True}},
         {"type": "single", "columnIds": ["reg-status"], "condition": "=", "value": "Rejected",
          "style": {"backgroundColor": "#FCEBEB", "color": BAD, "bold": True}},
         {"type": "single", "columnIds": ["reg-status"], "condition": "=", "value": "Submitted",
          "style": {"backgroundColor": BLUE_TINT, "color": BLUE, "bold": True}},
         {"type": "single", "columnIds": ["reg-status"], "condition": "=", "value": "Draft",
          "style": {"backgroundColor": "#F0F0F1", "color": MUTED, "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"}, "style": panel()})
add({"id": "ctrl-selected-scenario", "kind": "control", "controlId": "c_selected_scenario",
     "name": "Selected scenario", "controlType": "text", "case": "insensitive", "mode": "equals",
     "includeNulls": "when-no-value-is-selected", "showOperators": False})
add({"id": "txt-approvals-sub", "kind": "text",
     "body": "Select a row above to review and decide. Starts empty — submit a scenario on the reallocation page to populate it.",
     "style": {"color": MUTED, "backgroundColor": CANVAS, "padding": "none"}})

# ---------------------------------------------------------------- review modal
overlays.append({
    "id": "m-review", "type": "modal", "name": "Review decision",
    "modal": {"width": "small", "header": {"title": " ", "showCloseIcon": "shown"},
              "footer": {"primaryCta": {"visible": "hidden"}, "secondaryCta": {"visible": "hidden"}}}})
add({"id": "m-band", "kind": "container",
     "style": {"backgroundColor": BLUE_DEEP, "borderRadius": "round", "padding": "none"},
     "backgroundImage": {"source": {"kind": "url", "url": HEADER_BG_URI}, "style": {"fit": "cover"}}})
add({"id": "m-logo", "kind": "image", "source": {"kind": "url", "url": SIGMA_MOTORS_LOGO_URI},
     "style": {"fit": "contain", "align": "start", "padding": "none"}})
add({"id": "m-title", "kind": "text",
     "body": '<span style="color:#FFFFFF">**Review decision**</span>',
     "style": {"padding": "none"}, "verticalAlign": "middle"})
add({"id": "review-selected", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "rs-v",
                  "formula": "MaxIf([Scenario Registry/Scenario], [Scenario Registry/Scenario ID] = [c_selected_scenario])",
                  "name": "Reviewing"}],
     "value": {"columnId": "rs-v", "color": INK, "fontSize": 20},
     "name": title("REVIEWING", 11), "style": {"backgroundColor": CARD, "padding": "none"},
     "layout": {"anchor": "start"}})
add({"id": "ctrl-review-decision", "kind": "control", "controlId": "c_review_decision",
     "name": "Decision", "controlType": "segmented",
     "source": {"kind": "manual", "valueType": "text", "values": ["Approved", "Rejected"]},
     "value": "Approved"})
add({"id": "ctrl-review-comments", "kind": "control", "controlId": "c_review_comments",
     "name": "Reviewer comments", "controlType": "text", "case": "insensitive", "mode": "contains",
     "includeNulls": "when-no-value-is-selected", "showOperators": False})
button("btn-save-decision", "Save decision", [
    {"effect": "update-rows", "tableElementId": "it-registry",
     "whichRows": {"type": "formula", "formula": "[Scenario ID] = [c_selected_scenario]"},
     "values": {"reg-status": {"type": "control", "control": "c_review_decision"},
                "reg-comments": {"type": "control", "control": "c_review_comments"}}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-registry"}},
    {"effect": "clear-control", "scope": {"type": "control", "controlId": "c_review_comments"}},
    {"effect": "close-overlay"}], fill=BLUE)
button("btn-cancel-review", "Cancel", [{"effect": "close-overlay"}], fill=CARD, font=MUTED, appearance="outline")

# ==================================================================== layout
pg1_hdr = page_header("pg1", "Market Signal", "Demand is moving faster than production &mdash; regional EV waitlists are surging while Hybrid holds flat")
pg2_hdr = page_header("pg2", "EV &amp; Hybrid reallocation", "Respond to the signal: model a volume-neutral shift before submitting it for approval")
pg3_hdr = page_header("pg3", "Approvals", "Decide on the reallocation scenarios born from the demand signal")

LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
%(hdr1)s
  <Element elementId="kd-evwait" gridColumn="1 / 6" gridRow="2 / 8"/>
  <Element elementId="kd-hywait" gridColumn="6 / 11" gridRow="2 / 8"/>
  <Element elementId="kd-backlog" gridColumn="11 / 15" gridRow="2 / 8"/>
  <Element elementId="kd-margin" gridColumn="15 / 20" gridRow="2 / 8"/>
  <Element elementId="kd-regions" gridColumn="20 / 25" gridRow="2 / 8"/>

  <Container elementId="c-demand-panel" type="grid" gridColumn="1 / 25" gridRow="9 / 22" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="demand-badge" gridColumn="1 / 2" gridRow="1 / 2"/>
    <Element elementId="demand-title" gridColumn="2 / 8" gridRow="1 / 2"/>
    <Element elementId="demand-sub" gridColumn="8 / 25" gridRow="1 / 2"/>
    <Element elementId="plg-demand" gridColumn="1 / 15" gridRow="2 / 13"/>
    <Element elementId="bar-demand" gridColumn="15 / 25" gridRow="2 / 13"/>
  </Container>

  <Container elementId="c-ai-signal" type="grid" gridColumn="1 / 25" gridRow="23 / 29" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ai-signal-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
    <Element elementId="ai-signal-title" gridColumn="2 / 25" gridRow="1 / 2"/>
    <Element elementId="txt-ai-signal" gridColumn="1 / 25" gridRow="2 / 6"/>
  </Container>

  <Element elementId="cta-msg" gridColumn="1 / 18" gridRow="30 / 32"/>
  <Element elementId="btn-model-response" gridColumn="18 / 25" gridRow="30 / 32"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg2">
%(hdr2)s
  <Element elementId="kr-ev" gridColumn="1 / 5" gridRow="3 / 8"/>
  <Element elementId="kr-hy" gridColumn="5 / 9" gridRow="3 / 8"/>
  <Element elementId="kr-margin" gridColumn="9 / 13" gridRow="3 / 8"/>
  <Element elementId="kr-total" gridColumn="13 / 17" gridRow="3 / 8"/>
  <Element elementId="kr-capused" gridColumn="17 / 21" gridRow="3 / 8"/>
  <Element elementId="kr-cellused" gridColumn="21 / 25" gridRow="3 / 8"/>

  <Container elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="9 / 15" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ai-title-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
    <Element elementId="ai-title" gridColumn="2 / 25" gridRow="1 / 2"/>
    <Element elementId="txt-ai" gridColumn="1 / 25" gridRow="2 / 6"/>
  </Container>

  <Container elementId="c-slider" type="grid" gridColumn="1 / 9" gridRow="16 / 24" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="slider-label" gridColumn="1 / 13" gridRow="1 / 2"/>
    <Element elementId="ctrl-ev-shift" gridColumn="1 / 13" gridRow="2 / 4"/>
    <Element elementId="btn-reset" gridColumn="1 / 7" gridRow="4 / 6"/>
    <Element elementId="btn-open-compare" gridColumn="7 / 13" gridRow="4 / 6"/>
    <Element elementId="btn-submit" gridColumn="1 / 13" gridRow="6 / 8"/>
  </Container>
  <Container elementId="c-trend-col" type="grid" gridColumn="9 / 25" gridRow="16 / 24" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ch-trend" gridColumn="1 / 25" gridRow="1 / 16"/>
  </Container>

</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg3">
%(hdr3)s
  <Element elementId="txt-approvals-sub" gridColumn="1 / 25" gridRow="2 / 3"/>
  <Element elementId="it-registry" gridColumn="1 / 25" gridRow="3 / 13"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto" id="m-review">
  <Container elementId="m-band" type="grid" gridColumn="1 / 13" gridRow="1 / 4" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="m-logo" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="m-title" gridColumn="4 / 13" gridRow="1 / 3"/>
  </Container>
  <Element elementId="review-selected" gridColumn="1 / 13" gridRow="4 / 7"/>
  <Element elementId="ctrl-review-decision" gridColumn="1 / 13" gridRow="7 / 9"/>
  <Element elementId="ctrl-review-comments" gridColumn="1 / 13" gridRow="9 / 11"/>
  <Element elementId="btn-save-decision" gridColumn="1 / 7" gridRow="11 / 13"/>
  <Element elementId="btn-cancel-review" gridColumn="7 / 13" gridRow="11 / 13"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto" id="m-scenarios">
  <Container elementId="ms-band" type="grid" gridColumn="1 / 13" gridRow="1 / 4" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ms-logo" gridColumn="1 / 4" gridRow="1 / 3"/>
    <Element elementId="ms-title" gridColumn="4 / 13" gridRow="1 / 3"/>
  </Container>
  <Element elementId="ms-sub" gridColumn="1 / 13" gridRow="4 / 6"/>
  <Element elementId="ms-create-label" gridColumn="1 / 13" gridRow="6 / 7"/>
  <Element elementId="ctrl-scenario-name" gridColumn="1 / 7" gridRow="7 / 9"/>
  <Element elementId="btn-create-scenario" gridColumn="7 / 13" gridRow="7 / 9"/>
  <Element elementId="ms-create-hint" gridColumn="1 / 13" gridRow="9 / 10"/>
  <Element elementId="ms-saved-label" gridColumn="1 / 13" gridRow="11 / 12"/>
  <Element elementId="it-scenarios" gridColumn="1 / 13" gridRow="12 / 22"/>
  <Element elementId="btn-close-compare" gridColumn="1 / 13" gridRow="22 / 24"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pgData">
  <Element elementId="sql-alloc" gridColumn="1 / 9" gridRow="1 / 13"/>
  <Element elementId="ctrl-ev-shift-ui" gridColumn="9 / 17" gridRow="1 / 3"/>
  <Element elementId="ctrl-selected-scenario" gridColumn="17 / 25" gridRow="1 / 3"/>
  <Element elementId="sql-ramp" gridColumn="1 / 9" gridRow="13 / 25"/>
  <Element elementId="sql-demand" gridColumn="9 / 17" gridRow="13 / 25"/>
  <Element elementId="it-alloc" gridColumn="1 / 13" gridRow="25 / 41"/>
  <Element elementId="tbl-capacity" gridColumn="13 / 25" gridRow="25 / 41"/>
</Page>""" % {"hdr1": HEADER_XML % {"h": pg1_hdr}, "hdr2": HEADER_XML % {"h": pg2_hdr},
              "hdr3": HEADER_XML % {"h": pg3_hdr}}

SPEC = {
    "name": "Sigma Motors",
    "folderId": "00000000-0000-0000-0000-000000000000",
    "document": {
        "schemaVersion": 1,
        "kind": "workbook",
        "elements": elements,
        "pages": [{"id": "pg1", "name": "Market Signal"},
                  {"id": "pg2", "name": "EV & Hybrid reallocation"},
                  {"id": "pg3", "name": "Approvals"},
                  {"id": "pgData", "name": "Data", "visibility": "hidden"}],
        "layout": LAYOUT,
        "overlays": overlays,
        "agents": agents,
        # NOTE: no global colors.text override -- it forces EVERY native text
        # element to that color regardless of its own explicit style.color,
        # which is exactly what made the white header title/subtitle render
        # dark. Every text element in this build already sets its own color.
        # fonts.textFont: was hand-set to Advercase_Bold in the Sigma UI at
        # one point, which applies that heavy display font to EVERY text
        # element (labels, body copy, KPI captions -- not just headlines),
        # producing the uniformly heavy/serif look that drifted furthest from
        # the approved HTML mockup (which used clean Inter for body/labels and
        # reserved a serif display face for big headlines only). Reset to
        # Inter to match. pageWidth: "full" to match the mockup's edge-to-edge
        # layout instead of the inset/framed "medium" look.
        "settings": {"theme": {"overrides": {
            "colors": {"surface": CANVAS, "highlight": BLUE,
                       "success": GOOD, "warning": ORANGE, "danger": BAD},
            "fonts": {"textFont": "Inter", "dataFont": "Inter"},
            "pageWidth": "full"}}},
    },
}


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "verify"
    who = S.call("GET", "/v2/whoami")
    if who.get("organizationId") != PAPERCRANE_ORG_ID:
        print("Refusing to write: not papercranestaging (org=%s)" % who.get("organizationId"))
        sys.exit(1)
    if action == "verify":
        try:
            S.verify_workbook(SPEC)
            print("verify passed —", len(elements), "elements,", len(DEMAND_REGIONS), "demand-region rows")
        except S.SigmaError as exc:
            print("verify failed:", str(exc.body)[:2500])
    elif action == "create":
        r = S.create_workbook(SPEC)
        print("created", r["workbookId"])
        meta = S.get_workbook_meta(r["workbookId"])
        print("urlId:", meta.get("workbookUrlId") or meta.get("url"))
        pathlib.Path(__file__).with_name("sigma_motors_id.txt").write_text(r["workbookId"])
    elif action == "update":
        workbook_id = sys.argv[2]
        S.update_workbook(workbook_id, SPEC)
        print("updated", workbook_id)


if __name__ == "__main__":
    main()
