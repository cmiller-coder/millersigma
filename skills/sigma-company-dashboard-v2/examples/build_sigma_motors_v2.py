"""Build the "Sigma Motors" 3-page workbook in papercranestaging -- v2, from scratch.

This is a ground-up rebuild, NOT an update of the prior build_sigma_motors.py
workbook. That prior build used a dark gradient hero band + logo watermark on
every page header, which reads as marketing-site chrome rather than a native
Sigma product dashboard. This version drops all of that: plain text page
titles/subtitles, native Sigma page tabs for navigation (no custom nav pill
element), and a persistent-feeling left assistant rail duplicated onto every
page (Sigma pages are independent grids -- there is no single app-shell
element that spans page navigation, so "global" here means "the same rail
content rebuilt on each page"; a conversation on one page does not carry
over to another).

Each rail hosts a real native "chat" element (kind: "chat") bound to a
document-level agent (document.agents[]) -- verified shape from
build_workforce_ops.py -- instead of a hand-rolled control+CallText fake-chat
simulation. The page-2 agent also has a real tool ("Set EV-share shift") that
calls set-control-value via agent-input, so asking it to model a shift
actually moves the lever, not just describes it.

Approvals starts EMPTY: Sigma has no way to seed static rows into a
kind:"empty" input table at create time (confirmed by the prior build). The
KPI summary row above the registry uses real CountIf formulas, so it reads
0/0/0 until real scenarios are submitted -- which is the honest state for a
freshly created workbook. (After creation, we seed a few real rows via actual
button clicks over Playwright so page 3 has real content to review.)

Usage: python3 build_sigma_motors_v2.py [verify|create|update <id>]
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import sigmaapi as S

PAPERCRANE_ORG_ID = "8c99818a-90b3-4cae-bdb7-cf69a741171a"
CONN = "a9d45cfe-ff65-4515-8193-a7072602a1ee"
PLUGIN_DEMAND_PULSE_ID = "f996fb4f-db88-4f46-b481-a94cab16f9f1"  # verified live + registered

# ---------------------------------------------------------------- palette (CM Motors app-shell direction)
CANVAS = "#F5F6F8"
CARD = "#FFFFFF"
BORDER = "#E5E5E9"
INK = "#1F2430"
MUTED = "#6B7280"
BLUE = "#1A70F1"
BLUE_TINT = "#EAF1FE"
GRAY = "#8A8F9C"
GOOD = "#12805C"
GOOD_BG = "#E3F5EC"
BAD = "#B3261E"
BAD_BG = "#FCE8E6"
WARN = "#92600C"
WARN_BG = "#FDF3DA"

# app-shell additions: dark nav sidebar + icon-badge palette
NAVY = "#16233D"
NAVY_DEEP = "#0E1830"
NAVY_LIGHT = "#22314F"
SIDEBAR_TEXT = "#C4CCDD"
AMBER_BADGE = "#E1962E"

NUM0 = {"kind": "number", "formatString": ",.0f"}
NUM1 = {"kind": "number", "formatString": ",.1f"}
MONEYK = {"kind": "number", "formatString": "$,.3s", "currencySymbol": "$"}
PCT1 = {"kind": "number", "formatString": ".1%"}

elements, overlays, agents = [], [], []


def add(el):
    elements.append(el)
    return el["id"]


def panel():
    return {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1, "borderRadius": "round"}


def flat():
    # For KPI cells grouped inside a shared panel() container -- no border of
    # their own, so the group reads as one connected strip instead of cards
    # stacked on cards.
    return {"backgroundColor": CARD, "padding": "none"}


def title(text, size=13, color=INK):
    return {"text": text, "color": color, "fontSize": size}


# ---------------------------------------------------------------- icon system
# Small inline SVGs baked into colored-circle badges, base64-encoded as data
# URIs -- the same proven technique from the prior build_sigma_motors.py
# (ICON dict + icon_uri helper), reused here for the KPI badges, section
# icons, and sidebar nav glyphs the new reference image calls for.
def icon_uri(path_d, color, bg=None, size=15, circle=True):
    # Icon paths are authored in a 24x24 viewBox. The flat (circle=False)
    # variant renders perfectly (confirmed live in the sidebar nav): one flat
    # <svg> with fill/stroke on the root, path_d as direct children. Two
    # different composite approaches for the circle-badge variant -- a <g
    # transform="translate() scale()">, then a nested <svg x y width height
    # viewBox> -- both failed identically (only the circle showed, glyph
    # invisible), which points at this renderer not supporting *any* form of
    # transform/nested-coordinate-system, not a sizing issue. Fix: stay in
    # ONE flat coordinate system. Expand the viewBox around the icon's native
    # 0-24 space instead of scaling into it, so the circle and the raw path_d
    # are both direct children of one <svg> with no nesting and no transform.
    import base64
    if not circle:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 24 24" '
               'fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
               '%s</svg>') % (size, size, color, path_d)
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    # Minimal diff from the known-working flat icon: SAME viewBox="0 0 24 24"
    # (no expansion, no negative origin -- suspected culprit in two earlier
    # failed attempts), just one circle sibling added behind the path_d.
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 24 24" '
           'fill="none" stroke="%s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
           '<circle cx="12" cy="12" r="11.5" fill="%s" stroke="none"/>'
           '%s</svg>') % (size, size, color, bg or NAVY, path_d)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


ICON = {
    "car": '<path d="M3 13l1.5-4.5A2 2 0 016.4 7h11.2a2 2 0 011.9 1.5L21 13"/><path d="M3 13h18v4a1 1 0 01-1 1h-1a1 1 0 01-1-1v-1H6v1a1 1 0 01-1 1H4a1 1 0 01-1-1v-4z"/><circle cx="7.5" cy="17" r="1.5"/><circle cx="16.5" cy="17" r="1.5"/>',
    "leaf": '<path d="M11 20A7 7 0 019.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
    "dollar": '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
    "pin": '<path d="M21 10c0 7-9 12-9 12s-9-5-9-12a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/>',
    "sparkle": '<path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6L12 3z"/>',
    "bulb": '<path d="M9 18h6M10 22h4M12 2a6 6 0 00-4 10.5c.6.6 1 1.5 1 2.5h6c0-1 .4-1.9 1-2.5A6 6 0 0012 2z"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "check": '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "signal": '<path d="M12 20v-6M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 14 0"/><circle cx="12" cy="20" r="1.6"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5"/><path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/>',
    "sliders": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    "arrow-right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "alert": '<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
}


def icon_image(eid, name, bg=None, size=15):
    # Flat icon (circle=False), colored via stroke instead of a circle badge
    # behind a white glyph -- the badge composite is valid, standards-correct
    # SVG (confirmed by rendering it directly with macOS QuickLook) but
    # Sigma's own image pipeline silently drops the glyph and shows only the
    # background circle, in every composition tried (transform, nested-svg,
    # flat-viewbox). Every icon using the flat circle=False path has rendered
    # correctly all session (sidebar nav, hero glyph) so that's the reliable
    # one. Trade a circle badge for a guaranteed-visible colored glyph.
    return add({"id": eid, "kind": "image",
                "source": {"kind": "url", "url": icon_uri(ICON[name], bg or NAVY, circle=False, size=size + 6)},
                "style": {"fit": "contain", "padding": "none"}})


def kpi_badge_cells(cells, nested_circle=False):
    """cells: list of (kpi_element_id, icon_name, badge_bg, col_start, col_end) in
    whatever nested grid the caller's own <Container> declares. Adds an icon
    badge above each existing kpi-chart element and returns the inner
    <Element>/<Container> XML fragment.

    Third attempt at a circular badge, after two failures: (1) one composite
    SVG (circle + glyph in one image) -- glyph never rendered no matter the
    composition (transform/nested-svg/flat-viewbox), though each was
    confirmed-valid SVG via direct QuickLook rendering; (2) two SIBLING
    elements overlapping at the same grid position (a circular `container` +
    a flat icon on top) -- rendered unrounded, icon missing, badges
    misaligned. This attempt uses true PARENT-CHILD nesting instead -- the
    icon as a real nested <Element> INSIDE the <Container>'s own nested grid,
    exactly the structural pattern already proven working for the sidebar
    nav pills (icon nested inside a colored/rounded container), rather than
    two independent top-level siblings sharing a position."""
    parts = []
    for kpi_id, icon, bg, c0, c1 in cells:
        if nested_circle:
            badge_id = kpi_id + "-badge"
            icon_id = kpi_id + "-icon"
            add({"id": badge_id, "kind": "container", "style": {"backgroundColor": bg, "borderRadius": "round", "padding": "none"}})
            add({"id": icon_id, "kind": "image",
                 "source": {"kind": "url", "url": icon_uri(ICON[icon], "#FFFFFF", circle=False, size=16)},
                 "style": {"fit": "contain", "padding": "none"}})
            parts.append('    <Container elementId="%s" type="grid" gridColumn="%d / %d" gridRow="1 / 4" '
                         'gridTemplateColumns="repeat(2, 1fr)" gridTemplateRows="repeat(3, 1fr)">' % (badge_id, c0, c0 + 2))
            parts.append('      <Element elementId="%s" gridColumn="1 / 3" gridRow="1 / 4"/>' % icon_id)
            parts.append('    </Container>')
            parts.append('    <Element elementId="%s" gridColumn="%d / %d" gridRow="4 / 10"/>' % (kpi_id, c0, c1))
        else:
            icon_id = kpi_id + "-icon"
            icon_image(icon_id, icon, bg=bg, size=18)
            parts.append('    <Element elementId="%s" gridColumn="%d / %d" gridRow="1 / 2"/>' % (icon_id, c0, c1))
            parts.append('    <Element elementId="%s" gridColumn="%d / %d" gridRow="2 / 8"/>' % (kpi_id, c0, c1))
    return "\n".join(parts)


def sql_values(rows):
    return ",\n    ".join(
        "(" + ", ".join("'%s'" % v.replace("'", "''") if isinstance(v, str) else str(v) for v in row) + ")"
        for row in rows)


def button(eid, label, effects, fill=BLUE, font="#FFFFFF", appearance="filled"):
    return add({"id": eid, "kind": "button", "text": label, "appearance": appearance,
                "align": "stretch", "fillColor": fill, "fontColor": font, "fontWeight": "bold",
                "actions": [{"id": "a-" + eid, "trigger": "on-click", "effects": effects}]})


def plain_header(prefix, page_title, subtitle):
    add({"id": prefix + "-title", "kind": "text", "body": "**%s**" % page_title,
         "style": {"color": INK, "backgroundColor": CANVAS, "padding": "none", "fontSize": 27},
         "verticalAlign": "middle"})
    add({"id": prefix + "-sub", "kind": "text", "body": subtitle,
         "style": {"color": MUTED, "backgroundColor": CANVAS, "padding": "none", "fontSize": 13},
         "verticalAlign": "middle"})
    # NOTE: a top-right "CM" avatar circle was attempted and dropped -- placed
    # in a lone outer-grid column with nothing below it to constrain height,
    # it stretched to fill the whole available row (a tall navy slab, not a
    # small badge) rather than sizing to its own content. Low-value
    # decorative detail; not worth a third layout attempt.
    # NOTE: a top-right date + period filter row (matching the reference image)
    # was attempted here and dropped -- "date" controlType errored ("Invalid
    # kind: control") even in its most minimal form, and debugging it further
    # wasn't worth it for a control with no real filtering logic behind it
    # anyway (the underlying data isn't a real time series). Skipped per the
    # same "no decoration without function" call made earlier this session.


# ==================================================================== app-shell sidebar
# A real Sigma page has no persistent cross-page chrome, so -- same trick as
# the old assistant rail -- this dark nav container is rebuilt once per page
# (nav1-/nav2-/nav3- prefixes) with that page's own item highlighted. The 3
# real pages get working `navigate` buttons; Scenario Studio gets a real
# `open-overlay` (it's a modal, not a 4th page -- kept as-is per Connor's
# call). No literal car photograph (copyright risk for a guessed stock-photo
# URL) -- a dark gradient + a large faint car-glyph echo instead.
def gradient_uri(top, bottom):
    import base64
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">'
           '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0%%" stop-color="%s"/><stop offset="100%%" stop-color="%s"/>'
           '</linearGradient></defs><rect width="400" height="300" fill="url(#g)"/></svg>') % (top, bottom)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


SIDEBAR_HERO_BG = gradient_uri(NAVY, NAVY_DEEP)
NAV_ITEMS = [
    ("market", "Market Signal", "chart", "pg1", None),
    ("realloc", "EV & Hybrid Reallocation", "leaf", "pg2", None),
    ("approvals", "Approvals", "check", "pg3", None),
    ("scenario", "Scenario Studio", "sliders", None, "m-scenarios"),
]


def build_sidebar(pfx, active_page):
    add({"id": pfx + "-shell", "kind": "container", "style": {"backgroundColor": NAVY, "padding": "none"}})
    add({"id": pfx + "-word", "kind": "text", "body": "**CM MOTORS**",
         "style": {"color": "#FFFFFF", "backgroundColor": NAVY, "padding": "none", "fontSize": 15}})
    add({"id": pfx + "-tag", "kind": "text", "body": "DRIVEN FORWARD.",
         "style": {"color": SIDEBAR_TEXT, "backgroundColor": NAVY, "padding": "none", "fontSize": 9.5}})

    nav_ids = []
    for key, label, icon, target, overlay in NAV_ITEMS:
        active = target == active_page
        bg = BLUE if active else NAVY
        fg = "#FFFFFF" if active else SIDEBAR_TEXT
        cid = pfx + "-nav-" + key
        add({"id": cid, "kind": "container", "style": {"backgroundColor": bg, "padding": "none", "borderRadius": "round"}})
        # flat icon glyph (no badge circle) so it reads as a nav item, not a KPI badge
        add({"id": cid + "-icon", "kind": "image",
             "source": {"kind": "url", "url": icon_uri(ICON[icon], fg, circle=False, size=15)},
             "style": {"fit": "contain", "padding": "none"}})
        effects = ([{"effect": "navigate", "target": {"type": "page", "page": target}}] if target
                   else [{"effect": "open-overlay", "overlayId": overlay}])
        button(cid + "-btn", label, effects, fill=bg, font=fg, appearance="filled")
        nav_ids.append(cid)

    add({"id": pfx + "-hero", "kind": "container", "style": {"backgroundColor": NAVY_DEEP, "padding": "none"},
         "backgroundImage": {"source": {"kind": "url", "url": SIDEBAR_HERO_BG}, "style": {"fit": "cover"}}})
    add({"id": pfx + "-hero-icon", "kind": "image",
         "source": {"kind": "url", "url": icon_uri(ICON["car"], NAVY_LIGHT, circle=False, size=90)},
         "style": {"fit": "contain", "padding": "none"}})
    add({"id": pfx + "-hero-tag", "kind": "text", "body": "**Data-driven.**\nBuilt for scale.\nAhead of demand.",
         "style": {"color": "#FFFFFF", "backgroundColor": NAVY_DEEP, "padding": "none", "fontSize": 12.5}})
    return nav_ids


SIDEBAR_XML = """  <Container elementId="%(p)s-shell" type="grid" gridColumn="1 / 6" gridRow="1 / 46" gridTemplateColumns="repeat(10, 1fr)" gridTemplateRows="repeat(46, auto)">
    <Element elementId="%(p)s-word" gridColumn="1 / 11" gridRow="1 / 2"/>
    <Element elementId="%(p)s-tag" gridColumn="1 / 11" gridRow="2 / 3"/>
    <Container elementId="%(p)s-nav-market" type="grid" gridColumn="1 / 11" gridRow="5 / 7" gridTemplateColumns="repeat(10, 1fr)" gridTemplateRows="auto">
      <Element elementId="%(p)s-nav-market-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
      <Element elementId="%(p)s-nav-market-btn" gridColumn="2 / 11" gridRow="1 / 2"/>
    </Container>
    <Container elementId="%(p)s-nav-realloc" type="grid" gridColumn="1 / 11" gridRow="7 / 9" gridTemplateColumns="repeat(10, 1fr)" gridTemplateRows="auto">
      <Element elementId="%(p)s-nav-realloc-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
      <Element elementId="%(p)s-nav-realloc-btn" gridColumn="2 / 11" gridRow="1 / 2"/>
    </Container>
    <Container elementId="%(p)s-nav-approvals" type="grid" gridColumn="1 / 11" gridRow="9 / 11" gridTemplateColumns="repeat(10, 1fr)" gridTemplateRows="auto">
      <Element elementId="%(p)s-nav-approvals-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
      <Element elementId="%(p)s-nav-approvals-btn" gridColumn="2 / 11" gridRow="1 / 2"/>
    </Container>
    <Container elementId="%(p)s-nav-scenario" type="grid" gridColumn="1 / 11" gridRow="11 / 13" gridTemplateColumns="repeat(10, 1fr)" gridTemplateRows="auto">
      <Element elementId="%(p)s-nav-scenario-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
      <Element elementId="%(p)s-nav-scenario-btn" gridColumn="2 / 11" gridRow="1 / 2"/>
    </Container>
    <Container elementId="%(p)s-hero" type="grid" gridColumn="1 / 11" gridRow="36 / 46" gridTemplateColumns="repeat(10, 1fr)" gridTemplateRows="auto">
      <Element elementId="%(p)s-hero-icon" gridColumn="7 / 11" gridRow="1 / 5"/>
      <Element elementId="%(p)s-hero-tag" gridColumn="1 / 11" gridRow="6 / 9"/>
    </Container>
  </Container>
"""

# ==================================================================== "Quick Questions" assistant card
# Lives in the main content grid (not the sidebar) -- matches the reference
# image's layout. Hosts a real native "chat" element bound to a document-
# level agent (verified shape: build_workforce_ops.py:424-437) instead of a
# hand-rolled control+CallText simulation.
def build_rail(pfx, agent_name, instructions, data_source_element_ids, tools=None):
    agent = {"id": "ag-" + pfx, "name": agent_name, "instructions": instructions,
             "dataSources": [{"elementId": eid, "kind": "table"} for eid in data_source_element_ids]}
    if tools:
        agent["tools"] = tools
    agents.append(agent)

    icon_image(pfx + "-icon", "bulb", bg=AMBER_BADGE, size=13)
    add({"id": pfx + "-title", "kind": "text", "body": "**Quick Questions**",
         "style": {"color": INK, "backgroundColor": CARD, "padding": "none", "fontSize": 13.5}})
    add({"id": pfx + "-sub", "kind": "text", "body": "Ask me anything about this page's data.",
         "style": {"color": MUTED, "backgroundColor": CARD, "padding": "none", "fontSize": 11}})
    add({"id": pfx + "-chat", "kind": "chat", "agentId": "ag-" + pfx})


RAIL_XML = """  <Element elementId="%(p)s-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
  <Element elementId="%(p)s-title" gridColumn="2 / 13" gridRow="1 / 2"/>
  <Element elementId="%(p)s-sub" gridColumn="1 / 13" gridRow="2 / 3"/>
  <Element elementId="%(p)s-chat" gridColumn="1 / 13" gridRow="3 / 24"/>
"""

# ==================================================================== PAGE 1 data: Market Signal
DEMAND_REGIONS = [
    # region,      ev_backlog, hybrid_backlog, ev_prior, hybrid_prior, growth_pct, backlog_weeks, urgent
    ("Southwest",  1373, 73,  909, 76,  51, 5.1, 1),
    ("West",       1135, 110, 799, 115, 42, 6.2, 1),
    ("Midwest",    657,  122, 557, 127, 18, 2.4, 0),
    ("Northeast",  537,  159, 493, 166, 9,  1.6, 0),
    ("South",      418,  146, 394, 152, 6,  1.1, 0),
]
# DEMAND_REGIONS is already authored in descending-EV-backlog order. A bar-chart
# xAxis only accepts a sort *direction* on its own category column (verified:
# the API silently drops an external "sort by measure" columnId), so a plain
# region-name axis sorts alphabetically no matter what. Bake the intended rank
# into the category label itself ("1. Southwest") and sort that label
# ascending -- guarantees the visual order regardless of the axis-sort limit.
DEMAND_REGIONS_RANKED = [row + ("%d. %s" % (i, row[0]),) for i, row in enumerate(DEMAND_REGIONS, start=1)]
demand_sql = ("SELECT * FROM VALUES\n    %s\n  AS d(region, ev_backlog, hybrid_backlog, ev_backlog_prior, "
              "hybrid_backlog_prior, growth_pct, backlog_weeks, urgent_flag, region_rank_label)\n  ORDER BY ev_backlog DESC"
              % sql_values(DEMAND_REGIONS_RANKED))
add({"id": "sql-demand", "kind": "table", "name": "Regional Demand",
     "source": {"connectionId": CONN, "kind": "sql", "statement": demand_sql},
     "columns": [{"id": "dm-region", "formula": "[Custom SQL/region]", "name": "Region"},
                 {"id": "dm-rank", "formula": "[Custom SQL/region_rank_label]", "name": "Region Rank Label"},
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
     "value": {"columnId": "kd-evwait-v", "color": INK, "fontSize": 24},
     "comparisonColumn": {"columnId": "kd-evwait-c"},
     "comparison": {"display": "delta", "fontSize": 11, "colorGood": GOOD, "colorBad": BAD},
     "name": title("EV WAITLIST (FLEET-WIDE)", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kd-hywait", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-hywait-v", "formula": "Sum([Regional Demand/Hybrid Backlog])", "name": "Hybrid waitlist", "format": NUM0},
                 {"id": "kd-hywait-c", "formula": "Sum([Regional Demand/Hybrid Backlog Prior])", "name": "Prior", "format": NUM0}],
     "value": {"columnId": "kd-hywait-v", "color": INK, "fontSize": 24},
     "comparisonColumn": {"columnId": "kd-hywait-c"},
     "comparison": {"display": "delta", "fontSize": 11, "colorGood": BAD, "colorBad": GOOD},
     "name": title("HYBRID WAITLIST", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kd-backlog", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-backlog-v", "formula": "Max([Regional Demand/Backlog Weeks])", "name": "Longest regional backlog", "format": NUM1}],
     "value": {"columnId": "kd-backlog-v", "color": INK, "fontSize": 24},
     "name": title("LONGEST BACKLOG (WKS)", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kd-margin", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-margin-v", "formula": "Sum([Regional Demand/EV Backlog]) * 437", "name": "Margin left on the table", "format": MONEYK}],
     "value": {"columnId": "kd-margin-v", "color": WARN, "fontSize": 24},
     "name": title("MARGIN AT RISK", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kd-regions", "kind": "kpi-chart", "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [{"id": "kd-regions-v", "formula": "Sum([Regional Demand/Urgent Flag])", "name": "Regions past threshold", "format": NUM0}],
     "value": {"columnId": "kd-regions-v", "color": WARN, "fontSize": 24},
     "name": title("REGIONS AT RISK", 10.5), "style": flat(), "layout": {"anchor": "start"}})

DEMAND_AI_PROMPT = (
    '"You are a demand-planning analyst at an automaker. Fleet-wide EV order backlog is "'
    ' & Text(Sum([Regional Demand/EV Backlog])) & '
    '" units, up from " & Text(Sum([Regional Demand/EV Backlog Prior])) & '
    '" 30 days ago, while Hybrid backlog is " & Text(Sum([Regional Demand/Hybrid Backlog])) & '
    '" units (roughly flat). The worst-hit region is backlogged " & Text(Round(Max([Regional Demand/Backlog Weeks]),1)) & '
    '" weeks, and " & Text(Sum([Regional Demand/Urgent Flag])) & " of 5 regions are growing over 25% per month. '
    'Unclaimed margin from this gap is roughly $" & Text(Round(Sum([Regional Demand/EV Backlog])*437/1000000,1)) & '
    '"M. In 2 sentences, tell a plant operations leader what is happening and why battery-cell supply -- not plant '
    'capacity -- is the constraint to watch if they shift production toward EV."'
)
add({"id": "c-ai-signal", "kind": "container", "style": {"backgroundColor": BLUE_TINT, "borderColor": BLUE, "borderWidth": 1, "borderRadius": "round"}})
icon_image("ai-signal-icon", "sparkle", bg=BLUE, size=13)
add({"id": "ai-signal-title", "kind": "text", "body": "**AI INSIGHT**",
     "style": {"color": BLUE, "backgroundColor": BLUE_TINT, "padding": "none", "fontSize": 10.5}})
add({"id": "txt-ai-signal", "kind": "text",
     "body": '{{ Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", "CLAUDE-4-SONNET", %s), \'"\', \'\') }}' % DEMAND_AI_PROMPT,
     "style": {"color": INK, "backgroundColor": BLUE_TINT, "padding": "none"}, "verticalAlign": "middle"})
button("btn-explore-scenarios", "Explore Scenarios →", [
    {"effect": "set-control-value", "control": "c_ev_shift",
     "value": {"type": "constant", "value": {"type": "number", "value": 14}}},
    {"effect": "navigate", "target": {"type": "page", "page": "pg2"}}], fill=NAVY)

add({"id": "c-demand-panel", "kind": "container", "style": panel()})
icon_image("demand-icon", "signal", bg=BLUE, size=13)
add({"id": "demand-title", "kind": "text", "body": "**Regional Demand Pulse**",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none", "fontSize": 13.5}})
add({"id": "demand-sub", "kind": "text", "body": "EV and Hybrid backlog by region",
     "style": {"color": MUTED, "backgroundColor": CARD, "padding": "none", "fontSize": 11.5}})
add({"id": "plg-demand", "kind": "plugin", "pluginId": PLUGIN_DEMAND_PULSE_ID,
     "displayName": "Regional Demand Pulse",
     "config": {"source": {"kind": "element", "elementId": "sql-demand"},
                "region": "dm-region", "ev_backlog": "dm-ev", "hybrid_backlog": "dm-hy",
                "growth_pct": "dm-growth", "backlog_weeks": "dm-weeks"},
     "style": {"backgroundColor": CARD}})

add({"id": "c-bar-demand", "kind": "container", "style": panel()})
icon_image("bar-demand-icon", "chart", bg=BLUE, size=13)
add({"id": "bar-demand-title", "kind": "text", "body": "**EV Backlog by Region (Ranked)**",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none", "fontSize": 13.5}})
add({"id": "bar-demand", "kind": "bar-chart", "name": " ",
     "description": {"visibility": "shown", "text": "Sorted descending, units on order"},
     "source": {"elementId": "sql-demand", "kind": "table"},
     "columns": [
         {"id": "bd-region", "formula": "[Regional Demand/Region Rank Label]", "name": "Region"},
         {"id": "bd-ev", "formula": "Sum([Regional Demand/EV Backlog])", "name": "EV Backlog", "format": NUM0}],
     "xAxis": {"columnId": "bd-region", "sort": {"direction": "ascending"}},
     "yAxis": {"columnIds": ["bd-ev"]},
     "orientation": "horizontal",
     "colorAssignment": {"palette": {"scheme": [BLUE], "type": "categorical"}},
     "legend": {"visibility": "hidden"}, "style": flat()})

# Backlog Trend -- new chart per the reference image, backed by real (synthetic)
# monthly data ending at the same fleet-wide totals shown in the KPI row above,
# so it's grounded rather than decorative.
TREND_MONTHS = [
    ("Jan", 2650, 560), ("Feb", 2950, 580), ("Mar", 3300, 590),
    ("Apr", 3650, 600), ("May", 3900, 605), ("Jun", 4120, 610),
]
# Same fix as the regions bar chart: a chart x-axis defaults to alphabetical
# category order, so plain "Jan/Feb/Mar..." would render as "Apr/Feb/Jan/..."
# Bake the month rank into the label ("1. Jan") and sort that label ascending.
trend_sql = ("SELECT * FROM VALUES\n    %s\n  AS t(month_idx, month_label, month_rank_label, ev_total, hybrid_total)\n  ORDER BY month_idx ASC"
             % sql_values([(i, m, "%d. %s" % (i + 1, m), ev, hy) for i, (m, ev, hy) in enumerate(TREND_MONTHS)]))
add({"id": "sql-trend", "kind": "table", "name": "Backlog Trend Months",
     "source": {"connectionId": CONN, "kind": "sql", "statement": trend_sql},
     "columns": [{"id": "tm-idx", "formula": "[Custom SQL/month_idx]", "name": "Month Index", "hidden": True},
                 {"id": "tm-label", "formula": "[Custom SQL/month_label]", "name": "Month"},
                 {"id": "tm-rank", "formula": "[Custom SQL/month_rank_label]", "name": "Month Rank Label"},
                 {"id": "tm-ev", "formula": "[Custom SQL/ev_total]", "name": "EV Total", "format": NUM0},
                 {"id": "tm-hy", "formula": "[Custom SQL/hybrid_total]", "name": "Hybrid Total", "format": NUM0}]})
add({"id": "c-backlog-trend", "kind": "container", "style": panel()})
icon_image("trend-icon", "check", bg=BLUE, size=13)
add({"id": "trend-title", "kind": "text", "body": "**Backlog Trend**",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none", "fontSize": 13.5}})
add({"id": "ch-backlog-trend", "kind": "line-chart", "name": " ",
     "description": {"visibility": "shown", "text": "Fleet-wide EV vs Hybrid backlog, last 6 months"},
     "source": {"elementId": "sql-trend", "kind": "table"},
     "columns": [
         {"id": "tt-label", "formula": "[Backlog Trend Months/Month Rank Label]", "name": "Month"},
         {"id": "tt-ev", "formula": "Sum([Backlog Trend Months/EV Total])", "name": "EV", "format": NUM0},
         {"id": "tt-hy", "formula": "Sum([Backlog Trend Months/Hybrid Total])", "name": "Hybrid", "format": NUM0}],
     "xAxis": {"columnId": "tt-label", "sort": {"direction": "ascending"}},
     "yAxis": {"columnIds": ["tt-ev", "tt-hy"]},
     "colorAssignment": {"palette": {"scheme": [BLUE, GRAY], "type": "categorical"}},
     "legend": {"visibility": "shown"}, "style": flat()})

build_rail("r1", "Market Signal Assistant",
           "Answer questions about regional EV/Hybrid demand, backlog, growth rate, and urgency "
           "threshold using the Regional Demand data source. Be concise -- 2-3 sentences. Battery-cell "
           "supply (not plant capacity) is the binding constraint on any EV production push.",
           ["sql-demand"])

# ==================================================================== PAGE 2 data: EV & Hybrid Reallocation
# Closed-form fleet math (volume-neutral shift -- proven in the prior build):
#   EV units = 5600 + 56*shift   Hybrid units = 7300 - 56*shift
#   Margin impact = 56*750*shift               Cell kWh = 522200 + 3416*shift (of 581628 contracted, i.e. 89.7% baseline)
EV_BASE, HY_BASE, SLOPE = 5600, 7300, 56
CELL_BASE, CELL_SLOPE, CELL_CONTRACT = 522200, 3416, 581628
TOTAL_CAPACITY = EV_BASE + HY_BASE

fleet_sql = ("SELECT * FROM VALUES\n    %s\n  AS f(powertrain, baseline_units, cell_kwh_per_unit)"
             % sql_values([("EV", EV_BASE, 75), ("Hybrid", HY_BASE, 14)]))
add({"id": "sql-fleet", "kind": "table", "name": "Fleet Baseline",
     "source": {"connectionId": CONN, "kind": "sql", "statement": fleet_sql},
     "columns": [{"id": "fl-pt", "formula": "[Custom SQL/powertrain]", "name": "Powertrain"},
                 {"id": "fl-base", "formula": "[Custom SQL/baseline_units]", "name": "Baseline Units"},
                 {"id": "fl-cellkwh", "formula": "[Custom SQL/cell_kwh_per_unit]", "name": "Cell Kwh Per Unit"}]})

add({"id": "ctrl-ev-shift", "kind": "control", "controlId": "c_ev_shift", "name": "EV-share shift",
     "controlType": "number", "mode": "=", "includeNulls": "when-no-value-is-selected", "value": 0})

add({"id": "tbl-fleet-scenario", "kind": "table", "name": "Fleet Scenario",
     "source": {"elementId": "sql-fleet", "kind": "table"},
     "columns": [
         {"id": "fs-pt", "formula": "[Fleet Baseline/Powertrain]", "name": "Powertrain", "hidden": True},
         {"id": "fs-factor", "hidden": True, "name": "Factor",
          "formula": 'If([Powertrain] = "EV", 1 + [c_ev_shift] * %d / [Fleet Baseline/Baseline Units], '
                     '1 - [c_ev_shift] * %d / [Fleet Baseline/Baseline Units])' % (SLOPE, SLOPE)},
         {"id": "fs-units", "formula": "Round([Fleet Baseline/Baseline Units] * [Factor])", "name": "Units", "format": NUM0},
         {"id": "fs-cells", "hidden": True, "name": "Row Cell Kwh", "formula": "[Units] * [Fleet Baseline/Cell Kwh Per Unit]"},
     ],
     "tableComponents": {"summaryBar": "hidden"}, "style": panel()})

EFF = "[Fleet Scenario/Units]"
add({"id": "kr-ev", "kind": "kpi-chart", "source": {"elementId": "tbl-fleet-scenario", "kind": "table"},
     "columns": [{"id": "kr-ev-v", "formula": 'SumIf(%s, [Fleet Scenario/Powertrain] = "EV")' % EFF, "name": "EV units", "format": NUM0},
                 {"id": "kr-ev-c", "formula": str(EV_BASE), "name": "Baseline", "format": NUM0}],
     "value": {"columnId": "kr-ev-v", "color": INK, "fontSize": 22},
     "comparisonColumn": {"columnId": "kr-ev-c"},
     "comparison": {"display": "delta", "colorGood": GOOD, "colorBad": BAD},
     "name": title("EV UNITS", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kr-hy", "kind": "kpi-chart", "source": {"elementId": "tbl-fleet-scenario", "kind": "table"},
     "columns": [{"id": "kr-hy-v", "formula": 'SumIf(%s, [Fleet Scenario/Powertrain] = "Hybrid")' % EFF, "name": "Hybrid units", "format": NUM0},
                 {"id": "kr-hy-c", "formula": str(HY_BASE), "name": "Baseline", "format": NUM0}],
     "value": {"columnId": "kr-hy-v", "color": INK, "fontSize": 22},
     "comparisonColumn": {"columnId": "kr-hy-c"},
     "comparison": {"display": "delta", "colorGood": BAD, "colorBad": GOOD},
     "name": title("HYBRID UNITS", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kr-margin", "kind": "kpi-chart", "source": {"elementId": "tbl-fleet-scenario", "kind": "table"},
     "columns": [{"id": "kr-margin-v", "formula": "%d * [c_ev_shift]" % (SLOPE * 750), "name": "Margin impact", "format": MONEYK}],
     "value": {"columnId": "kr-margin-v", "color": GOOD, "fontSize": 22},
     "name": title("MARGIN IMPACT", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kr-total", "kind": "kpi-chart", "source": {"elementId": "tbl-fleet-scenario", "kind": "table"},
     "columns": [{"id": "kr-total-v", "formula": "Sum(%s)" % EFF, "name": "Total capacity", "format": NUM0}],
     "value": {"columnId": "kr-total-v", "color": INK, "fontSize": 22},
     "name": title("TOTAL CAPACITY", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kr-capused", "kind": "kpi-chart", "source": {"elementId": "tbl-fleet-scenario", "kind": "table"},
     "columns": [{"id": "kc-v", "formula": "Sum(%s) / %d" % (EFF, TOTAL_CAPACITY), "name": "Plant capacity used", "format": PCT1}],
     "value": {"columnId": "kc-v", "color": INK, "fontSize": 22},
     "name": title("CAPACITY USED", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kr-cellused", "kind": "kpi-chart", "source": {"elementId": "tbl-fleet-scenario", "kind": "table"},
     "columns": [{"id": "kl-v", "formula": "Sum([Fleet Scenario/Row Cell Kwh]) / %d" % CELL_CONTRACT, "name": "Battery cell used", "format": PCT1}],
     "value": {"columnId": "kl-v", "color": WARN, "fontSize": 22},
     "name": title("CELL USED", 10.5), "style": flat(), "layout": {"anchor": "start"}})

AI_PROMPT = (
    '"You are a manufacturing operations analyst advising an automaker\'\'s executive team. Baseline production is 5,600 EV '
    'units and 7,300 Hybrid units. A planner is evaluating a "'
    ' & Text([c_ev_shift]) & '
    '"-point EV-share shift, which moves margin by roughly $" & Text(Round([c_ev_shift] * 42)) & '
    '"K and changes production to " & Text(Sum([Fleet Scenario/Units])/2 + %d*[c_ev_shift]) & ' % SLOPE +
    '" EV units and " & Text(%d - %d*[c_ev_shift]) & ' % (HY_BASE, SLOPE) +
    '" Hybrid units. At that level, battery-cell supply-contract commitment would be "'
    ' & Text(Round(100*(%d + %d*[c_ev_shift])/%d,1)) & ' % (CELL_BASE, CELL_SLOPE, CELL_CONTRACT) +
    '"%. In 2-3 sentences, tell the executive team whether this shift is feasible given battery-cell supply, and name the '
    'binding constraint if it is at risk of being breached. If the shift is 0, just describe the baseline position."'
)
add({"id": "c-ai", "kind": "container", "style": {"backgroundColor": BLUE_TINT, "borderColor": BLUE, "borderWidth": 1, "borderRadius": "round"}})
add({"id": "ai-title", "kind": "text", "body": "**AI INSIGHT**",
     "style": {"color": BLUE, "backgroundColor": BLUE_TINT, "padding": "none", "fontSize": 10.5}})
add({"id": "txt-ai", "kind": "text",
     "body": '{{ Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", "CLAUDE-4-SONNET", %s), \'"\', \'\') }}' % AI_PROMPT,
     "style": {"color": INK, "backgroundColor": BLUE_TINT, "padding": "none"}, "verticalAlign": "middle"})

add({"id": "c-workspace-pg2", "kind": "container", "style": panel()})
add({"id": "c-slider", "kind": "container", "style": flat()})
add({"id": "slider-label", "kind": "text", "body": "**Reallocate production mix**",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none", "fontSize": 13.5}})
add({"id": "slider-hint", "kind": "text", "body": "EV-share shift (−20 to +20)",
     "style": {"color": MUTED, "backgroundColor": CARD, "padding": "none", "fontSize": 10.5}})

RAMP_MONTHS = [(m, "M%d" % m, m / 6.0) for m in range(7)]
ramp_sql = ("SELECT * FROM VALUES\n    %s\n  AS r(month_idx, month_label, ramp_fraction)\n  ORDER BY month_idx ASC"
            % sql_values(RAMP_MONTHS))
add({"id": "sql-ramp", "kind": "table", "name": "Rollout Months",
     "source": {"connectionId": CONN, "kind": "sql", "statement": ramp_sql},
     "columns": [{"id": "rm-idx", "formula": "[Custom SQL/month_idx]", "name": "Month Index"},
                 {"id": "rm-label", "formula": "[Custom SQL/month_label]", "name": "Month"},
                 {"id": "rm-frac", "formula": "[Custom SQL/ramp_fraction]", "name": "Ramp Fraction"}]})
add({"id": "ch-trend", "kind": "line-chart", "name": "Production rollout",
     "description": {"visibility": "shown", "text": "EV vs Hybrid units, ramping to the modeled shift over 6 months"},
     "source": {"elementId": "sql-ramp", "kind": "table"},
     "columns": [
         {"id": "rt-idx", "formula": "[Rollout Months/Month Index]", "name": "Month Order", "hidden": True},
         {"id": "rt-label", "formula": "[Rollout Months/Month]", "name": "Month"},
         {"id": "rt-ev", "formula": "%d + %d * [c_ev_shift] * [Rollout Months/Ramp Fraction]" % (EV_BASE, SLOPE),
          "name": "EV units", "format": NUM0},
         {"id": "rt-hy", "formula": "%d - %d * [c_ev_shift] * [Rollout Months/Ramp Fraction]" % (HY_BASE, SLOPE),
          "name": "Hybrid units", "format": NUM0}],
     "xAxis": {"columnId": "rt-label"},
     "yAxis": {"columnIds": ["rt-ev", "rt-hy"]},
     "colorAssignment": {"palette": {"scheme": [BLUE, GRAY], "type": "categorical"}},
     "legend": {"visibility": "shown"}, "style": flat()})

button("btn-reset", "Reset", [
    {"effect": "set-control-value", "control": "c_ev_shift",
     "value": {"type": "constant", "value": {"type": "number", "value": 0}}}],
    fill=CARD, font=INK, appearance="outline")
button("btn-open-compare", "+ New scenario", [{"effect": "open-overlay", "overlayId": "m-scenarios"}],
       fill=CARD, font=BLUE, appearance="outline")
button("btn-submit", "Save & submit for approval", [
    {"effect": "insert-rows", "tableElementId": "it-registry", "values": {
        "reg-id": {"type": "formula", "formula": '"SCN-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
        "reg-name": {"type": "formula", "formula": '"Reallocation scenario – " & DateFormat(Now(), "%b %d, %H:%M")'},
        "reg-type": {"type": "formula",
                     "formula": '"EV-Share Shift " & If([c_ev_shift] >= 0, "+" & Text([c_ev_shift]), Text([c_ev_shift]))'},
        "reg-shift": {"type": "control", "control": "c_ev_shift"},
        "reg-owner": {"type": "constant", "value": {"type": "text", "value": "C. Miller"}},
        "reg-status": {"type": "constant", "value": {"type": "text", "value": "Pending"}}}},
    {"effect": "navigate", "target": {"type": "page", "page": "pg3"}}], fill=BLUE)

# ---------------------------------------------------------------- scenario studio
add({"id": "it-scenarios", "kind": "input-table", "name": " ",
     "inputMode": "view", "source": {"kind": "empty", "connectionId": CONN},
     "columns": [
         {"id": "sc-id", "name": "Scenario ID", "type": "text", "hidden": True},
         {"id": "sc-name", "name": "Scenario", "type": "text"},
         {"id": "sc-shift", "name": "EV shift", "type": "number", "format": NUM0},
         {"id": "sc-margin", "name": "Margin impact", "formula": "%d * [EV shift]" % (SLOPE * 750), "format": MONEYK},
         {"id": "sc-cellused", "name": "Cell used",
          "formula": "(%d + %d * [EV shift]) / %d" % (CELL_BASE, CELL_SLOPE, CELL_CONTRACT), "format": PCT1},
         {"id": "ID", "name": "Row ID", "hidden": True},
         {"id": "CREATED_AT", "name": "Created At", "hidden": True},
         {"id": "UPDATED_AT", "name": "Updated At", "hidden": True},
         {"id": "CREATED_BY", "name": "Created By", "hidden": True}],
     "sort": [{"columnId": "CREATED_AT", "direction": "ascending", "nulls": "last"}],
     "conditionalFormats": [
         {"type": "dataBars", "columnIds": ["sc-margin"], "scheme": [BLUE_TINT, GOOD]},
         {"type": "single", "columnIds": ["sc-cellused"], "condition": ">", "value": 1.0,
          "style": {"backgroundColor": BAD_BG, "color": BAD, "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"}, "style": flat()})
add({"id": "ctrl-scenario-name", "kind": "control", "controlId": "c_scenario_name", "name": "Scenario name",
     "controlType": "text", "case": "insensitive", "mode": "contains",
     "includeNulls": "when-no-value-is-selected", "showOperators": False})
button("btn-create-scenario", "Save scenario", [
    {"effect": "insert-rows", "tableElementId": "it-scenarios", "values": {
        "sc-id": {"type": "formula", "formula": '"SC-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
        "sc-name": {"type": "formula", "formula": 'Coalesce(NullIf([c_scenario_name], ""), "Scenario") & " (" & Text([c_ev_shift]) & ")"'},
        "sc-shift": {"type": "control", "control": "c_ev_shift"}}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-scenarios"}},
    {"effect": "clear-control", "scope": {"type": "control", "controlId": "c_scenario_name"}}], fill=BLUE)
button("btn-close-compare", "Cancel", [{"effect": "close-overlay"}], fill=CARD, font=MUTED, appearance="outline")

overlays.append({
    "id": "m-scenarios", "type": "modal", "name": "Scenario studio",
    "modal": {"width": "large", "header": {"title": " ", "showCloseIcon": "shown"},
              "footer": {"primaryCta": {"visible": "hidden"}, "secondaryCta": {"visible": "hidden"}}}})
icon_image("ms-icon", "sliders", bg=BLUE, size=14)
add({"id": "ms-title", "kind": "text", "body": "**New scenario**",
     "style": {"color": INK, "backgroundColor": CANVAS, "padding": "none", "fontSize": 16}})
add({"id": "ms-sub", "kind": "text",
     "body": "Snapshot the current lever value and save it for comparison before submitting.",
     "style": {"color": MUTED, "backgroundColor": CANVAS, "padding": "none", "fontSize": 11.5}})
# Card-ify the form row and the saved-scenarios table -- matches the panel()
# + icon/title header language used everywhere else in the dashboard (e.g.
# c-demand-panel, c-bar-demand) instead of leaving raw controls floating
# directly on the modal's bare canvas background.
add({"id": "c-ms-form", "kind": "container", "style": panel()})
add({"id": "c-ms-table", "kind": "container", "style": panel()})
icon_image("ms-table-icon", "database", bg=BLUE, size=13)
add({"id": "ms-table-title", "kind": "text", "body": "**Saved scenarios**",
     "style": {"color": INK, "backgroundColor": CARD, "padding": "none", "fontSize": 13.5}})

# A real tool, not just Q&A: the assistant can actually move the EV-share
# shift lever when asked (e.g. "shift production 10 points toward EV"),
# mirroring the cohort-builder agent-tool pattern (set-control-value via
# agent-input).
RAIL2_TOOLS = [{
    "toolId": "t-set-shift", "kind": "action", "name": "Set EV-share shift",
    "description": "Move the EV-share shift lever to a specific point value (-20 to +20) that the "
                    "user asks for, e.g. 'shift 10 points toward EV' -> 10, 'shift toward Hybrid by 5' -> -5.",
    "steps": [{"kind": "effect", "effect": "set-control-value", "control": "c_ev_shift",
               "value": {"type": "agent-input", "inputName": "The EV-share shift point value, as a number from -20 to 20"}}],
}]
build_rail("r2", "Reallocation Assistant",
           "Answer questions about the EV/Hybrid production mix, margin impact, and battery-cell "
           "supply usage using the Fleet Scenario and Rollout Months data sources. Be concise -- 2-3 "
           "sentences. Whenever the user mentions a specific shift amount, in either direction -- "
           "'shift 15 points toward EV', 'move 10 points toward Hybrid', 'try a 5-point shift' -- "
           "ALWAYS call the Set EV-share shift tool immediately with that value (negative for a "
           "Hybrid-direction shift) before replying. Do this proactively; never just describe what "
           "the shift would do or ask for confirmation first -- apply it, then summarize the "
           "resulting EV units, Hybrid units, margin impact, and battery-cell usage.",
           ["tbl-fleet-scenario", "sql-ramp"], tools=RAIL2_TOOLS)

# ==================================================================== PAGE 3 data: Approvals
add({"id": "it-registry", "kind": "input-table", "name": "Scenario Registry",
     "inputMode": "view", "source": {"kind": "empty", "connectionId": CONN},
     "columns": [
         {"id": "reg-id", "name": "Scenario ID", "type": "text"},
         {"id": "reg-name", "name": "Scenario", "type": "text"},
         {"id": "reg-type", "name": "Type", "type": "text"},
         {"id": "reg-shift", "name": "Reg Shift", "type": "number", "hidden": True},
         {"id": "reg-owner", "name": "Submitted by", "type": "text"},
         {"id": "reg-status", "name": "Status", "type": "text", "values": ["Pending", "Approved", "Rejected"]},
         {"id": "reg-comments", "name": "Reviewer comments", "type": "text"},
         {"id": "ID", "name": "Row ID", "hidden": True},
         {"id": "CREATED_AT", "name": "Created At"},
         {"id": "UPDATED_AT", "name": "Updated At", "hidden": True},
         {"id": "CREATED_BY", "name": "Created By", "hidden": True}],
     "actions": [{"id": "act-select-reg", "trigger": "on-select", "effects": [
         {"effect": "set-control-value", "control": "c_selected_scenario", "value": {"type": "column", "columnId": "reg-id"}},
         {"effect": "open-overlay", "overlayId": "m-review"}]}],
     "sort": [{"columnId": "CREATED_AT", "direction": "descending", "nulls": "last"}],
     "conditionalFormats": [
         {"type": "single", "columnIds": ["reg-status"], "condition": "=", "value": "Approved",
          "style": {"backgroundColor": GOOD_BG, "color": GOOD, "bold": True}},
         {"type": "single", "columnIds": ["reg-status"], "condition": "=", "value": "Rejected",
          "style": {"backgroundColor": BAD_BG, "color": BAD, "bold": True}},
         {"type": "single", "columnIds": ["reg-status"], "condition": "=", "value": "Pending",
          "style": {"backgroundColor": WARN_BG, "color": WARN, "bold": True}}],
     "tableComponents": {"summaryBar": "hidden"}, "style": panel()})

add({"id": "kp-pending", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "kp-pending-v", "formula": 'CountIf([Scenario Registry/Status] = "Pending")',
                  "name": "Pending", "format": NUM0}],
     "value": {"columnId": "kp-pending-v", "color": WARN, "fontSize": 22},
     "name": title("PENDING", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kp-approved", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "kp-approved-v", "formula": 'CountIf([Scenario Registry/Status] = "Approved")',
                  "name": "Approved", "format": NUM0}],
     "value": {"columnId": "kp-approved-v", "color": GOOD, "fontSize": 22},
     "name": title("APPROVED", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kp-rejected", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "kp-rejected-v", "formula": 'CountIf([Scenario Registry/Status] = "Rejected")',
                  "name": "Rejected", "format": NUM0}],
     "value": {"columnId": "kp-rejected-v", "color": BAD, "fontSize": 22},
     "name": title("REJECTED", 10.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "kp-rate", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "kp-rate-v",
                  "formula": ('If(CountIf([Scenario Registry/Status] = "Approved") + '
                               'CountIf([Scenario Registry/Status] = "Rejected") = 0, 0, '
                               'CountIf([Scenario Registry/Status] = "Approved") / '
                               '(CountIf([Scenario Registry/Status] = "Approved") + '
                               'CountIf([Scenario Registry/Status] = "Rejected")))'),
                  "name": "Approval rate", "format": PCT1}],
     "value": {"columnId": "kp-rate-v", "color": INK, "fontSize": 22},
     "name": title("APPROVAL RATE", 10.5), "style": flat(), "layout": {"anchor": "start"}})

# ---------------------------------------------------------------- review modal (scenario detail + decision)
add({"id": "ctrl-selected-scenario", "kind": "control", "controlId": "c_selected_scenario",
     "name": "Selected scenario", "controlType": "text", "case": "insensitive", "mode": "equals",
     "includeNulls": "when-no-value-is-selected", "showOperators": False})
overlays.append({
    "id": "m-review", "type": "modal", "name": "Review scenario",
    "modal": {"width": "small", "header": {"title": " ", "showCloseIcon": "shown"},
              "footer": {"primaryCta": {"visible": "hidden"}, "secondaryCta": {"visible": "hidden"}}}})
add({"id": "review-selected", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "rs-v",
                  "formula": "MaxIf([Scenario Registry/Scenario], [Scenario Registry/Scenario ID] = [c_selected_scenario])",
                  "name": "Reviewing"}],
     "value": {"columnId": "rs-v", "color": INK, "fontSize": 16},
     "name": title("REVIEWING", 10.5), "style": {"backgroundColor": CARD, "padding": "none"},
     "layout": {"anchor": "start"}})
SEL_SHIFT = 'MaxIf([Scenario Registry/Reg Shift], [Scenario Registry/Scenario ID] = [c_selected_scenario])'
add({"id": "review-ev", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "rev-v", "formula": "%d + %d * %s" % (EV_BASE, SLOPE, SEL_SHIFT), "name": "EV units", "format": NUM0}],
     "value": {"columnId": "rev-v", "color": INK, "fontSize": 15},
     "name": title("EV UNITS", 9.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "review-hy", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "rhy-v", "formula": "%d - %d * %s" % (HY_BASE, SLOPE, SEL_SHIFT), "name": "Hybrid units", "format": NUM0}],
     "value": {"columnId": "rhy-v", "color": INK, "fontSize": 15},
     "name": title("HYBRID UNITS", 9.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "review-margin", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "rmg-v", "formula": "%d * %s" % (SLOPE * 750, SEL_SHIFT), "name": "Margin impact", "format": MONEYK}],
     "value": {"columnId": "rmg-v", "color": GOOD, "fontSize": 15},
     "name": title("MARGIN IMPACT", 9.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "review-cell", "kind": "kpi-chart", "source": {"elementId": "it-registry", "kind": "table"},
     "columns": [{"id": "rcl-v", "formula": "(%d + %d * %s) / %d" % (CELL_BASE, CELL_SLOPE, SEL_SHIFT, CELL_CONTRACT),
                  "name": "Battery cell used", "format": PCT1}],
     "value": {"columnId": "rcl-v", "color": WARN, "fontSize": 15},
     "name": title("CELL USED", 9.5), "style": flat(), "layout": {"anchor": "start"}})
add({"id": "ctrl-review-decision", "kind": "control", "controlId": "c_review_decision",
     "name": "Decision", "controlType": "segmented",
     "source": {"kind": "manual", "valueType": "text", "values": ["Approved", "Rejected"]},
     "value": "Approved"})
add({"id": "ctrl-review-comments", "kind": "control", "controlId": "c_review_comments",
     "name": "Reviewer comments", "controlType": "text", "case": "insensitive", "mode": "contains",
     "includeNulls": "when-no-value-is-selected", "showOperators": False})
button("btn-save-decision", "Save", [
    {"effect": "update-rows", "tableElementId": "it-registry",
     "whichRows": {"type": "formula", "formula": "[Scenario ID] = [c_selected_scenario]"},
     "values": {"reg-status": {"type": "control", "control": "c_review_decision"},
                "reg-comments": {"type": "control", "control": "c_review_comments"}}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-registry"}},
    {"effect": "clear-control", "scope": {"type": "control", "controlId": "c_review_comments"}},
    {"effect": "close-overlay"}], fill=BLUE)
button("btn-cancel-review", "Cancel", [{"effect": "close-overlay"}], fill=CARD, font=MUTED, appearance="outline")

build_rail("r3", "Approvals Assistant",
           "Answer questions about scenario submissions, their status (Pending/Approved/Rejected), "
           "and reviewer comments using the Scenario Registry data source. Be concise -- 2-3 sentences.",
           ["it-registry"])

# KPI rows are grouped into one shared panel() container each (see flat())
# instead of floating as separate bordered cards. Each cell also gets a small
# colored icon badge above it, per the reference image.
add({"id": "c-kpi-pg1", "kind": "container", "style": panel()})
add({"id": "c-kpi-pg2", "kind": "container", "style": panel()})
add({"id": "c-kpi-pg3", "kind": "container", "style": panel()})
add({"id": "c-kpi-review", "kind": "container", "style": panel()})

KPI1_XML = kpi_badge_cells([
    ("kd-evwait", "car", BLUE, 1, 6), ("kd-hywait", "leaf", GOOD, 6, 11),
    ("kd-backlog", "clock", BLUE, 11, 16), ("kd-margin", "dollar", AMBER_BADGE, 16, 20),
    ("kd-regions", "pin", NAVY, 20, 25)])
KPI2_XML = kpi_badge_cells([
    ("kr-ev", "car", BLUE, 1, 5), ("kr-hy", "leaf", GOOD, 5, 9), ("kr-margin", "dollar", AMBER_BADGE, 9, 13),
    ("kr-total", "chart", BLUE, 13, 17), ("kr-capused", "signal", BLUE, 17, 21), ("kr-cellused", "database", NAVY, 21, 25)])
KPI3_XML = kpi_badge_cells([
    ("kp-pending", "clock", AMBER_BADGE, 1, 7), ("kp-approved", "check", GOOD, 7, 13),
    ("kp-rejected", "alert", BAD, 13, 19), ("kp-rate", "chart", BLUE, 19, 25)])

# app-shell sidebar, rebuilt once per real page with that page highlighted
build_sidebar("nav1", "pg1")
build_sidebar("nav2", "pg2")
build_sidebar("nav3", "pg3")

add({"id": "c-quick-questions-1", "kind": "container", "style": panel()})
add({"id": "c-quick-questions-2", "kind": "container", "style": panel()})
add({"id": "c-quick-questions-3", "kind": "container", "style": panel()})

# ==================================================================== layout
LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
%(nav1)s
  <Element elementId="hdr-pg1-title" gridColumn="7 / 25" gridRow="1 / 2"/>
  <Element elementId="hdr-pg1-sub" gridColumn="7 / 25" gridRow="2 / 3"/>

  <Container elementId="c-kpi-pg1" type="grid" gridColumn="7 / 25" gridRow="4 / 13" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="repeat(10, auto)">
%(kpi1)s
  </Container>

  <Container elementId="c-ai-signal" type="grid" gridColumn="7 / 25" gridRow="14 / 21" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ai-signal-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
    <Element elementId="ai-signal-title" gridColumn="2 / 20" gridRow="1 / 2"/>
    <Element elementId="txt-ai-signal" gridColumn="1 / 20" gridRow="2 / 6"/>
    <Element elementId="btn-explore-scenarios" gridColumn="20 / 25" gridRow="2 / 4"/>
  </Container>

  <Container elementId="c-quick-questions-1" type="grid" gridColumn="7 / 13" gridRow="22 / 38" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
%(qq1)s
  </Container>
  <Container elementId="c-demand-panel" type="grid" gridColumn="13 / 25" gridRow="22 / 38" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="demand-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
    <Element elementId="demand-title" gridColumn="2 / 25" gridRow="1 / 2"/>
    <Element elementId="demand-sub" gridColumn="1 / 25" gridRow="2 / 3"/>
    <Element elementId="plg-demand" gridColumn="1 / 25" gridRow="3 / 16"/>
  </Container>

  <Container elementId="c-bar-demand" type="grid" gridColumn="7 / 16" gridRow="39 / 53" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="bar-demand-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
    <Element elementId="bar-demand-title" gridColumn="2 / 25" gridRow="1 / 2"/>
    <Element elementId="bar-demand" gridColumn="1 / 25" gridRow="2 / 14"/>
  </Container>
  <Container elementId="c-backlog-trend" type="grid" gridColumn="16 / 25" gridRow="39 / 53" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="trend-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
    <Element elementId="trend-title" gridColumn="2 / 25" gridRow="1 / 2"/>
    <Element elementId="ch-backlog-trend" gridColumn="1 / 25" gridRow="2 / 14"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg2">
%(nav2)s
  <Element elementId="hdr-pg2-title" gridColumn="7 / 25" gridRow="1 / 2"/>
  <Element elementId="hdr-pg2-sub" gridColumn="7 / 25" gridRow="2 / 3"/>

  <Container elementId="c-kpi-pg2" type="grid" gridColumn="7 / 25" gridRow="4 / 13" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="repeat(10, auto)">
%(kpi2)s
  </Container>

  <Container elementId="c-quick-questions-2" type="grid" gridColumn="7 / 13" gridRow="14 / 35" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
%(qq2)s
  </Container>

  <Container elementId="c-ai" type="grid" gridColumn="13 / 25" gridRow="14 / 21" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ai-title" gridColumn="1 / 25" gridRow="1 / 2"/>
    <Element elementId="txt-ai" gridColumn="1 / 25" gridRow="2 / 6"/>
  </Container>

  <Container elementId="c-workspace-pg2" type="grid" gridColumn="13 / 25" gridRow="22 / 35" gridTemplateColumns="repeat(19, 1fr)" gridTemplateRows="auto">
    <Container elementId="c-slider" type="grid" gridColumn="1 / 7" gridRow="1 / 13" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
      <Element elementId="slider-label" gridColumn="1 / 13" gridRow="1 / 2"/>
      <Element elementId="slider-hint" gridColumn="1 / 13" gridRow="2 / 3"/>
      <Element elementId="ctrl-ev-shift" gridColumn="1 / 13" gridRow="3 / 5"/>
      <Element elementId="btn-reset" gridColumn="1 / 13" gridRow="5 / 7"/>
      <Element elementId="btn-open-compare" gridColumn="1 / 13" gridRow="7 / 9"/>
      <Element elementId="btn-submit" gridColumn="1 / 13" gridRow="9 / 11"/>
    </Container>
    <Element elementId="ch-trend" gridColumn="8 / 20" gridRow="1 / 13"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg3">
%(nav3)s
  <Element elementId="hdr-pg3-title" gridColumn="7 / 25" gridRow="1 / 2"/>
  <Element elementId="hdr-pg3-sub" gridColumn="7 / 25" gridRow="2 / 3"/>

  <Container elementId="c-kpi-pg3" type="grid" gridColumn="7 / 25" gridRow="4 / 13" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="repeat(10, auto)">
%(kpi3)s
  </Container>

  <Container elementId="c-quick-questions-3" type="grid" gridColumn="7 / 13" gridRow="14 / 35" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
%(qq3)s
  </Container>
  <Element elementId="it-registry" gridColumn="13 / 25" gridRow="14 / 35"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto" id="m-review">
  <Element elementId="review-selected" gridColumn="1 / 13" gridRow="1 / 3"/>
  <Container elementId="c-kpi-review" type="grid" gridColumn="1 / 13" gridRow="3 / 6" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="repeat(3, auto)">
    <Element elementId="review-ev" gridColumn="1 / 4" gridRow="1 / 4"/>
    <Element elementId="review-hy" gridColumn="4 / 7" gridRow="1 / 4"/>
    <Element elementId="review-margin" gridColumn="7 / 10" gridRow="1 / 4"/>
    <Element elementId="review-cell" gridColumn="10 / 13" gridRow="1 / 4"/>
  </Container>
  <Element elementId="ctrl-review-decision" gridColumn="1 / 13" gridRow="6 / 8"/>
  <Element elementId="ctrl-review-comments" gridColumn="1 / 13" gridRow="8 / 10"/>
  <Element elementId="btn-save-decision" gridColumn="1 / 7" gridRow="10 / 12"/>
  <Element elementId="btn-cancel-review" gridColumn="7 / 13" gridRow="10 / 12"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto" id="m-scenarios">
  <Element elementId="ms-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
  <Element elementId="ms-title" gridColumn="2 / 13" gridRow="1 / 2"/>
  <Element elementId="ms-sub" gridColumn="1 / 13" gridRow="2 / 3"/>
  <Container elementId="c-ms-form" type="grid" gridColumn="1 / 13" gridRow="4 / 7" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ctrl-scenario-name" gridColumn="1 / 8" gridRow="1 / 3"/>
    <Element elementId="btn-create-scenario" gridColumn="8 / 13" gridRow="1 / 3"/>
  </Container>
  <Container elementId="c-ms-table" type="grid" gridColumn="1 / 13" gridRow="8 / 19" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="ms-table-icon" gridColumn="1 / 2" gridRow="1 / 2"/>
    <Element elementId="ms-table-title" gridColumn="2 / 13" gridRow="1 / 2"/>
    <Element elementId="it-scenarios" gridColumn="1 / 13" gridRow="2 / 11"/>
  </Container>
  <Element elementId="btn-close-compare" gridColumn="1 / 13" gridRow="20 / 22"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pgData">
  <Element elementId="sql-demand" gridColumn="1 / 9" gridRow="1 / 13"/>
  <Element elementId="sql-fleet" gridColumn="9 / 17" gridRow="1 / 13"/>
  <Element elementId="tbl-fleet-scenario" gridColumn="17 / 25" gridRow="1 / 13"/>
  <Element elementId="sql-ramp" gridColumn="1 / 9" gridRow="13 / 25"/>
  <Element elementId="ctrl-selected-scenario" gridColumn="9 / 17" gridRow="13 / 15"/>
  <Element elementId="sql-trend" gridColumn="17 / 25" gridRow="13 / 25"/>
</Page>""" % {
    "nav1": SIDEBAR_XML % {"p": "nav1"}, "nav2": SIDEBAR_XML % {"p": "nav2"}, "nav3": SIDEBAR_XML % {"p": "nav3"},
    "qq1": RAIL_XML % {"p": "r1"}, "qq2": RAIL_XML % {"p": "r2"}, "qq3": RAIL_XML % {"p": "r3"},
    "kpi1": KPI1_XML, "kpi2": KPI2_XML, "kpi3": KPI3_XML,
}

# page headers as plain text (no gradient band) -- added after RAIL_XML references above so hdr ids exist
plain_header("hdr-pg1", "Market Signal",
             "Demand is moving faster than production — regional EV waitlists are surging while Hybrid holds flat.")
plain_header("hdr-pg2", "EV & Hybrid Reallocation",
             "Model a shift in production mix and see the impact on margin and battery-cell supply.")
plain_header("hdr-pg3", "Approvals", "Scenario submissions awaiting review.")

SPEC = {
    "name": "CM Motors",
    "folderId": S.FOLDER_CLAUDE_BUILDER,
    "document": {
        "schemaVersion": 1,
        "kind": "workbook",
        "elements": elements,
        "pages": [{"id": "pg1", "name": "Market Signal"},
                  {"id": "pg2", "name": "EV & Hybrid Reallocation"},
                  {"id": "pg3", "name": "Approvals"},
                  {"id": "pgData", "name": "Data", "visibility": "hidden"}],
        "layout": LAYOUT,
        "overlays": overlays,
        "agents": agents,
        "settings": {"theme": {"overrides": {
            "colors": {"surface": CANVAS, "highlight": BLUE, "success": GOOD, "warning": WARN, "danger": BAD},
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
            print("verify failed:", str(exc.body)[:3000])
            sys.exit(1)
    elif action == "create":
        r = S.create_workbook(SPEC)
        print("created", r["workbookId"])
        meta = S.get_workbook_meta(r["workbookId"])
        print("urlId:", meta.get("workbookUrlId") or meta.get("url"))
        pathlib.Path(__file__).with_name("sigma_motors_v2_id.txt").write_text(r["workbookId"])
    elif action == "update":
        workbook_id = sys.argv[2]
        S.update_workbook(workbook_id, SPEC)
        print("updated", workbook_id)


if __name__ == "__main__":
    main()
