#!/usr/bin/env python3
"""Apple Inc. — one BI page + one data-app page (with internal Plan/Approvals
tabs). Editorial Minimal theme. Demo org, no plugin, no PDF.

Structural rebuild after the second round of feedback: the workbook should
read as "a BI slide, then one tab per data app" -- not a pile of top-level
pages where the approval queue shows up as a THIRD, seemingly-unrelated tab
next to Home and the modeler. Fixed two ways:

1. `reallocation_modeler.build(..., embed=True)` and
   `approval_workflow.build(..., embed_review=True)` skip generating their
   own standalone pages and instead return element ids via `unplaced` --
   this script lays both sections out as two TABS inside ONE
   `tabbed-container` on a single "Regional Allocation Planner" page. Top-
   level nav is now exactly two pages: Home, Regional Allocation Planner.
2. Every content zone gets a small-caps eyebrow header (the `s-*` text
   elements below), the same convention Honda's and ShiftKey's builds use
   ("ALLOCATION GRID", "APPROVAL QUEUE", "PLANT-MONTH LOAD") -- a page with
   five unlabeled zones back to back doesn't read as organized even when
   each zone individually is fine.

Usage:
    python3 build_apple_reallocation_demo.py
    python3 build_apple_reallocation_demo.py BASE TOKEN CONNECTION_ID FOLDER_ID
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                       / "sigma-input-table-app" / "surfaces"))
import approval_workflow  # noqa: E402
import reallocation_modeler  # noqa: E402

_ARGS = sys.argv[1:]
BASE = _ARGS[0] if len(_ARGS) > 0 else ""
TOKEN = _ARGS[1] if len(_ARGS) > 1 else ""
CONN = _ARGS[2] if len(_ARGS) > 2 else "<connection-id>"
FOLDER = _ARGS[3] if len(_ARGS) > 3 else "<folder-id>"

# theme-presets.json option 2 "editorial-minimal", translated to real
# settings.theme.overrides -- not re-guessed. {brand.primary} -> Apple's
# real sampled black (the logo has no color to sample beyond black/white,
# so this is the one placeholder filled from the company's actual brand
# rather than the logo asset).
BRAND_PRIMARY = "#000000"
CANVAS = "#F5F1E9"
CARD = "#FCFAF6"
TEXT = "#24211D"
TEXT_MUTED = "#746F67"
BORDER = "#D8D1C5"
CATEGORICAL = ["#2D5B50", "#6C8A80", "#BE6A42", "#24211D", "#B4A58E"]

LOGO_URI = pathlib.Path(__file__).with_name("apple_logo_black.datauri.txt")
LOGO_DATA_URI = LOGO_URI.read_text().strip() if LOGO_URI.exists() else None


def eyebrow(eid, label):
    return {"id": eid, "kind": "text",
            "body": f'<span style="color: {TEXT_MUTED}">**{label}**</span>'}


REALLOC_SQL = """
SELECT * FROM VALUES
  ('iPhone',   'Americas',       82000, 88000),
  ('iPhone',   'Europe',         46000, 50000),
  ('iPhone',   'Greater China',  38000, 42000),
  ('iPhone',   'Japan',          14000, 16000),
  ('Mac',      'Americas',       15000, 18000),
  ('Mac',      'Europe',          9000, 11000),
  ('Mac',      'Greater China',   6000,  8000),
  ('Mac',      'Japan',           2500,  3500),
  ('Services', 'Americas',       28000, 30000),
  ('Services', 'Europe',         16000, 18000),
  ('Services', 'Greater China',   9000, 11000),
  ('Services', 'Japan',           4500,  5500)
AS t(category, region, baseline_units, capacity_units)
"""

realloc = reallocation_modeler.build(
    prefix="rl", connection_id=CONN,
    dimension_columns=[{"id": "category", "name": "Category"}, {"id": "region", "name": "Region"}],
    baseline_sql=REALLOC_SQL, capacity_dimension_id="region",
    measure_label="Revenue ($M)", page_name="Regional Allocation Planner",
    embed=True,
)
wf = approval_workflow.build(
    prefix="wf", connection_id=CONN,
    entity_singular="Allocation Plan", entity_plural="Allocation Plans",
    embed_review=True,
)

# ------------------------------------------------------- exec overview data
TREND_SQL = """
SELECT * FROM VALUES
  ('2026-08-01','iPhone',130000),('2026-09-01','iPhone',133000),('2026-10-01','iPhone',137000),
  ('2026-11-01','iPhone',142000),('2026-12-01','iPhone',148000),('2027-01-01','iPhone',152000),
  ('2026-08-01','Mac',30000),('2026-09-01','Mac',31000),('2026-10-01','Mac',31500),
  ('2026-11-01','Mac',32000),('2026-12-01','Mac',33000),('2027-01-01','Mac',33500),
  ('2026-08-01','Services',45000),('2026-09-01','Services',47000),('2026-10-01','Services',49000),
  ('2026-11-01','Services',51500),('2026-12-01','Services',54000),('2027-01-01','Services',57000)
AS t(month_start, category, revenue)
"""
sql_trend = {
    "id": "sql-trend", "kind": "table", "name": "Revenue Trend", "visibleAsSource": True,
    "source": {"connectionId": CONN, "kind": "sql", "statement": TREND_SQL},
    "columns": [
        {"id": "tr-month", "formula": "[Custom SQL/MONTH_START]", "name": "Month",
         "format": {"kind": "datetime", "formatString": "%b %Y"}},
        {"id": "tr-category", "formula": "[Custom SQL/CATEGORY]", "name": "Category"},
        {"id": "tr-revenue", "formula": "[Custom SQL/REVENUE]", "name": "Revenue",
         "format": {"kind": "number", "formatString": ",d"}},
    ],
}

decision = {
    "id": "home-decision", "kind": "text",
    "body": "**THE DECISION**  Where should the next allocation shift go, and is "
            "Services on track to keep growing as a share of revenue?",
}
insight = {
    "id": "home-insight", "kind": "text",
    "body": (
        "**Planning signal**  Services is "
        "{{Sum(If([Revenue Trend/Category] = \"Services\", [Revenue Trend/Revenue], 0)) / "
        "Sum([Revenue Trend/Revenue]) | .1%}} of the six-month revenue shown here, "
        "the fastest-growing of the three lines above. Greater China carries the least "
        "allocation headroom of any region in the reallocation plan on the next tab."
    ),
}
logo_el = ({"id": "home-logo", "kind": "image", "source": {"kind": "url", "url": LOGO_DATA_URI}}
           if LOGO_DATA_URI else None)
logo_el_planner = ({"id": "planner-logo", "kind": "image", "source": {"kind": "url", "url": LOGO_DATA_URI}}
                    if LOGO_DATA_URI else None)


def kpi(eid, label, formula, fmt=",d", source="rl-base"):
    return {
        "id": eid, "kind": "kpi-chart", "name": label,
        "source": {"kind": "table", "elementId": source},
        "columns": [{"id": eid + "-value", "name": label, "formula": formula,
                     "format": {"kind": "number", "formatString": fmt}}],
        "value": {"columnId": eid + "-value", "fontSize": 30},
        "style": {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1,
                   "borderRadius": "square"},
    }


kpi_total = kpi("home-kpi-total", "Total Revenue ($M)",
                 "Sum([Reallocation Base/Baseline Revenue ($M)])")
kpi_iphone = kpi("home-kpi-iphone", "iPhone Mix",
                  'Sum(If([Reallocation Base/Category] = "iPhone", '
                  '[Reallocation Base/Baseline Revenue ($M)], 0)) / '
                  'Sum([Reallocation Base/Baseline Revenue ($M)])', fmt=".1%")
kpi_services = kpi("home-kpi-services", "Services Mix",
                    'Sum(If([Reallocation Base/Category] = "Services", '
                    '[Reallocation Base/Baseline Revenue ($M)], 0)) / '
                    'Sum([Reallocation Base/Baseline Revenue ($M)])', fmt=".1%")
kpi_intl = kpi("home-kpi-intl", "Ex-Americas Mix",
               'Sum(If([Reallocation Base/Region] <> "Americas", '
               '[Reallocation Base/Baseline Revenue ($M)], 0)) / '
               'Sum([Reallocation Base/Baseline Revenue ($M)])', fmt=".1%")
kpi_capacity = kpi("home-kpi-capacity", "Network Utilization",
                    "Sum([Reallocation Base/Baseline Revenue ($M)]) / "
                    "Sum([Reallocation Base/Capacity])", fmt=".1%")

chart_trend = {
    "id": "home-chart-trend", "kind": "line-chart", "name": "Revenue by category",
    "source": {"kind": "table", "elementId": "sql-trend"},
    "columns": [
        {"id": "ct-month", "name": "Month", "formula": "[Revenue Trend/Month]"},
        {"id": "ct-revenue", "name": "Revenue", "formula": "Sum([Revenue Trend/Revenue])"},
        {"id": "ct-category", "name": "Category", "formula": "[Revenue Trend/Category]"},
    ],
    "xAxis": {"columnId": "ct-month"}, "yAxis": {"columnIds": ["ct-revenue"]},
    "color": {"by": "category", "column": "ct-category"},
    "stacking": "none", "legend": {"position": "top"},
}
chart_regional_mix = {
    "id": "home-chart-regional", "kind": "bar-chart", "name": "Revenue by region and category",
    "source": {"kind": "table", "elementId": "rl-base"},
    "columns": [
        {"id": "cr-region", "name": "Region", "formula": "[Reallocation Base/Region]"},
        {"id": "cr-revenue", "name": "Revenue", "formula": "Sum([Reallocation Base/Baseline Revenue ($M)])"},
        {"id": "cr-category", "name": "Category", "formula": "[Reallocation Base/Category]"},
    ],
    "xAxis": {"columnId": "cr-region",
              "sort": {"by": "cr-revenue", "aggregation": "sum", "direction": "descending"}},
    "yAxis": {"columnIds": ["cr-revenue"]},
    "color": {"by": "category", "column": "cr-category"},
    "stacking": "stacked", "legend": {"position": "top"},
}

tbl_detail = {
    "id": "home-tbl-detail", "kind": "table", "name": "Regional plan health",
    "source": {"kind": "table", "elementId": "rl-base"},
    "columns": [
        {"id": "td-region", "name": "Region", "formula": "[Reallocation Base/Region]"},
        {"id": "td-category", "name": "Category", "formula": "[Reallocation Base/Category]"},
        {"id": "td-revenue", "name": "Revenue ($M)", "formula": "[Reallocation Base/Baseline Revenue ($M)]",
         "format": {"kind": "number", "formatString": "$,d"}},
        {"id": "td-capacity", "name": "Capacity ($M)", "formula": "[Reallocation Base/Capacity]",
         "format": {"kind": "number", "formatString": "$,d"}},
        {"id": "td-util", "name": "Utilization",
         "formula": "[Reallocation Base/Baseline Revenue ($M)] / [Reallocation Base/Capacity]",
         "format": {"kind": "number", "formatString": ".1%"}},
    ],
    "sort": [{"columnId": "td-util", "direction": "descending", "nulls": "last"}],
    "tableComponents": {"summaryBar": "hidden"},
}

header = {
    "id": "home-header", "kind": "text",
    "body": "## Apple Inc.\n**GLOBAL OPERATIONS PLANNING**\n"
            "# Regional allocation command center",
}
planner_header = {
    "id": "planner-header", "kind": "text",
    "body": "## Apple Inc.\n**GLOBAL OPERATIONS PLANNING**",
}

# A real `navigation` element baked into page content -- not Sigma's native
# page-tab bar, which is viewer-chrome (depends on settings.navigation and
# headless export doesn't render it, so it's easy to ship a workbook that
# LOOKS navigable while building it and isn't for a real viewer). This is
# actual content, always visible regardless of theme or viewer settings.
# Every top-level page needs its OWN instance (an element is placed once),
# each listing every other top-level page.
NAV_OPTIONS = [
    {"label": "Home", "destination": {"type": "page", "pageId": "page-home"}},
    {"label": "Regional Allocation Planner",
     "destination": {"type": "page", "pageId": "page-planner"}},
]


def make_nav(eid):
    return {"id": eid, "kind": "navigation", "mode": "manual", "showIcons": False,
            "style": {"backgroundColor": "transparent"},
            "optionStyle": {"textColor": TEXT_MUTED, "selectedColor": BRAND_PRIMARY,
                             "style": "pill", "orientation": "horizontal"},
            "options": NAV_OPTIONS}


nav_home = make_nav("nav-home")
nav_planner = make_nav("nav-planner")

s_overview = eyebrow("s-overview", "OVERVIEW")
s_trends = eyebrow("s-trends", "REVENUE TRENDS & REGIONAL MIX")
s_detail = eyebrow("s-detail", "REGIONAL PLAN HEALTH")
s_next = eyebrow("s-next", "NEXT STEP")

# --------------------------------------------------- allocation-planner tab
tc_planner = {
    "id": "tc-planner", "kind": "tabbed-container",
    "tabs": [{"name": "Plan"}, {"name": "Approvals"}],
    "tabBar": {"visibility": "shown", "style": "button", "alignment": "start", "size": "small"},
    "spacing": "small",
    "style": {"backgroundColor": CANVAS},
}
s_scenario = eyebrow("s-scenario", "SCENARIO CONTROLS")
s_baseline_eff = eyebrow("s-baseline-eff", "BASELINE VS EFFECTIVE")
s_grid = eyebrow("s-grid", "ALLOCATION GRID — TYPE TO OVERRIDE THE SCENARIO")
s_load = eyebrow("s-load", "CAPACITY LOAD BY REGION")

home_page_id = "page-home"
home_data_page_id = "page-home-data"
planner_page_id = "page-planner"
pages = [
    {"id": home_page_id, "name": "Home", "backgroundColor": CANVAS},
    {"id": home_data_page_id, "name": "Data", "visibility": "hidden", "backgroundColor": CANVAS},
    {"id": planner_page_id, "name": "Regional Allocation Planner", "backgroundColor": CANVAS},
    *realloc["pages"],  # already just the hidden data page (embed=True)
    *wf["pages"],       # already just the hidden data page + 2 modals (embed_review=True)
]
elements = [
    header, planner_header,
    *([logo_el] if logo_el else []), *([logo_el_planner] if logo_el_planner else []),
    nav_home, nav_planner, decision,
    s_overview, kpi_total, kpi_iphone, kpi_services, kpi_intl, kpi_capacity,
    s_trends, sql_trend, chart_trend, chart_regional_mix,
    s_detail, tbl_detail, insight, s_next,
    tc_planner, s_scenario, s_baseline_eff, s_grid, s_load,
    *realloc["elements"], *wf["elements"],
]
overlays = [*realloc["overlays"], *wf["overlays"]]

logo_layout = ('<Element elementId="home-logo" gridColumn="22 / 25" gridRow="1 / 3"/>'
               if logo_el else "")
logo_layout_planner = ('<Element elementId="planner-logo" gridColumn="22 / 25" gridRow="1 / 3"/>'
                        if logo_el_planner else "")
r = realloc["unplaced"]
w = wf["unplaced"]
layout = f"""
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{home_page_id}">
  <Element elementId="home-header" gridColumn="1 / 16" gridRow="1 / 4"/>
  <Element elementId="nav-home" gridColumn="16 / 22" gridRow="1 / 3"/>
  {logo_layout}
  <Element elementId="home-decision" gridColumn="1 / 25" gridRow="4 / 6"/>
  <Element elementId="s-overview" gridColumn="1 / 25" gridRow="6 / 7"/>
  <Element elementId="home-kpi-total" gridColumn="1 / 6" gridRow="7 / 14"/>
  <Element elementId="home-kpi-iphone" gridColumn="6 / 11" gridRow="7 / 14"/>
  <Element elementId="home-kpi-services" gridColumn="11 / 16" gridRow="7 / 14"/>
  <Element elementId="home-kpi-intl" gridColumn="16 / 21" gridRow="7 / 14"/>
  <Element elementId="home-kpi-capacity" gridColumn="21 / 25" gridRow="7 / 14"/>
  <Element elementId="s-trends" gridColumn="1 / 25" gridRow="14 / 15"/>
  <Element elementId="home-chart-trend" gridColumn="1 / 13" gridRow="15 / 28"/>
  <Element elementId="home-chart-regional" gridColumn="13 / 25" gridRow="15 / 28"/>
  <Element elementId="s-detail" gridColumn="1 / 25" gridRow="28 / 29"/>
  <Element elementId="home-tbl-detail" gridColumn="1 / 25" gridRow="29 / 43"/>
  <Element elementId="home-insight" gridColumn="1 / 25" gridRow="43 / 46"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{home_data_page_id}">
  <Element elementId="sql-trend" gridColumn="1 / 25" gridRow="1 / 15"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{planner_page_id}">
  <Element elementId="planner-header" gridColumn="1 / 16" gridRow="1 / 3"/>
  <Element elementId="nav-planner" gridColumn="16 / 22" gridRow="1 / 3"/>
  {logo_layout_planner}
  <TabbedContainer elementId="tc-planner" gridColumn="1 / 25" gridRow="3 / 63">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="{r['title']}" gridColumn="1 / 25" gridRow="1 / 3"/>
      <Element elementId="s-scenario" gridColumn="1 / 25" gridRow="3 / 4"/>
      <Element elementId="{r['shift_control']}" gridColumn="1 / 9" gridRow="4 / 11"/>
      <Element elementId="{r['reset_button']}" gridColumn="9 / 13" gridRow="7 / 9"/>
      <Element elementId="{r['kpi_effective']}" gridColumn="13 / 17" gridRow="4 / 11"/>
      <Element elementId="{r['kpi_baseline']}" gridColumn="17 / 21" gridRow="4 / 11"/>
      <Element elementId="{r['kpi_breach']}" gridColumn="21 / 25" gridRow="4 / 11"/>
      <Element elementId="s-baseline-eff" gridColumn="1 / 25" gridRow="11 / 12"/>
      <Element elementId="{r['chart']}" gridColumn="1 / 25" gridRow="12 / 23"/>
      <Element elementId="s-grid" gridColumn="1 / 25" gridRow="23 / 24"/>
      <Element elementId="{r['assumptions_table']}" gridColumn="1 / 25" gridRow="24 / 42"/>
      <Element elementId="s-load" gridColumn="1 / 25" gridRow="42 / 43"/>
      <Element elementId="{r['capacity_table']}" gridColumn="1 / 25" gridRow="43 / 55"/>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="{w['review_title']}" gridColumn="1 / 25" gridRow="1 / 4"/>
      <Element elementId="{w['review_kpi_total']}" gridColumn="1 / 9" gridRow="4 / 11"/>
      <Element elementId="{w['review_kpi_submitted']}" gridColumn="9 / 17" gridRow="4 / 11"/>
      <Element elementId="{w['review_kpi_approved']}" gridColumn="17 / 25" gridRow="4 / 11"/>
      <Element elementId="s-next" gridColumn="1 / 25" gridRow="11 / 12"/>
      <Element elementId="{w['create_button']}" gridColumn="1 / 7" gridRow="12 / 15"/>
      <Element elementId="{w['submit_target_control']}" gridColumn="7 / 17" gridRow="12 / 15"/>
      <Element elementId="{w['submit_button']}" gridColumn="17 / 25" gridRow="12 / 15"/>
      <Element elementId="{w['review_table']}" gridColumn="1 / 25" gridRow="15 / 32"/>
    </Tab>
  </TabbedContainer>
</Page>
""" + realloc["layout_xml"] + wf["layout_xml"]

document = {
    "schemaVersion": 1,
    "kind": "workbook",
    "elements": elements,
    "pages": pages,
    "overlays": overlays,
    "layout": layout,
    "settings": {
        "theme": {"name": "Light",
                  "overrides": {
                      "colors": {"text": TEXT, "surface": CARD, "highlight": BRAND_PRIMARY,
                                 "success": "#2D5B50", "danger": "#BE6A42"},
                      "categoricalScheme": CATEGORICAL,
                      "borderRadius": "square",
                      "hasCards": "shown",
                      "elementBorder": {"color": BORDER, "width": 1},
                      "space": {"unit": "large", "showElementPadding": "shown"},
                      "tableStyles": {"preset": "presentation", "cellSpacing": "medium",
                                      "gridLines": "horizontal", "banding": "hidden"},
                      "pageWidth": "large"}},
        "navigation": {"pageHeader": "enabled", "pageTabsInViewMode": "shown"},
    },
}

body = {
    "name": "Apple — Regional Allocation Planner (Editorial Minimal, tabbed)",
    "folderId": FOLDER,
    "description": "One BI page + one data-app page (Plan/Approvals tabs inside). "
                    "Editorial Minimal theme, demo org, no plugin, no PDF.",
    "document": document,
}


def call(method, path, payload):
    req = urllib.request.Request(
        BASE.rstrip("/") + path, data=json.dumps(payload).encode(), method=method,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r_:
            raw = r_.read().decode()
            return r_.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


if __name__ == "__main__":
    if len(_ARGS) < 4:
        print(json.dumps(body, indent=2))
        raise SystemExit(0)
    status, result = call("POST", "/v2/workbooks/spec/verify", body)
    print("verify", status, result)
    if status >= 400 or not (isinstance(result, dict) and result.get("valid")):
        raise SystemExit(1)
    status, result = call("POST", "/v2/workbooks/spec", body)
    print("create", status, result)
