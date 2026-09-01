#!/usr/bin/env python3
"""YETI Holdings — Category/Channel Reallocation Planner.

First real end-to-end test of the pluggable surfaces (surfaces/
reallocation_modeler.py + surfaces/approval_workflow.py) composed with a
company-specific exec page, real fetched logo, and real segment structure --
Coolers & Equipment / Drinkware categories, Wholesale / DTC channels (YETI's
actual reported segments). No bespoke plugin, no PDF report, per request.

Usage:
    python3 build_yeti_reallocation.py
    python3 build_yeti_reallocation.py BASE TOKEN CONNECTION_ID FOLDER_ID
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

# Sampled from YETI's own logo asset (navy roundel + white wordmark), not
# guessed -- fetch_logo.py's white-only wordmark washed out against a light
# canvas, so this uses the self-contained badge mark instead (navy circle
# baked in, legible on any background).
NAVY = "#00263C"
CHARCOAL = "#1A1A1A"
CARD = "#FFFFFF"
CANVAS = "#F2F2EF"

LOGO_URI = pathlib.Path(__file__).with_name("yeti_badge.datauri.txt")
LOGO_DATA_URI = LOGO_URI.read_text().strip() if LOGO_URI.exists() else None

BASELINE_SQL = """
SELECT * FROM VALUES
  ('Coolers & Equipment', 'Wholesale',        412000, 460000),
  ('Coolers & Equipment', 'Direct-to-Consumer', 298000, 320000),
  ('Drinkware',           'Wholesale',        355000, 400000),
  ('Drinkware',           'Direct-to-Consumer', 341000, 350000)
AS t(category, channel, baseline_units, capacity_units)
"""

realloc = reallocation_modeler.build(
    prefix="rl",
    connection_id=CONN,
    dimension_columns=[{"id": "category", "name": "Category"}, {"id": "channel", "name": "Channel"}],
    baseline_sql=BASELINE_SQL,
    capacity_dimension_id="channel",
    measure_label="Units",
    page_name="Reallocation Planner",
)

wf = approval_workflow.build(
    prefix="wf",
    connection_id=CONN,
    entity_singular="Allocation Plan",
    entity_plural="Allocation Plans",
)

header = {
    "id": "home-header", "kind": "text",
    "body": "## YETI Holdings\n**MERCHANDISE PLANNING**\n"
            "# Category & channel allocation command center\n"
            "Where should the next production run go — and who signs off on it?",
}
logo_el = None
if LOGO_DATA_URI:
    logo_el = {"id": "home-logo", "kind": "image",
               "source": {"kind": "url", "url": LOGO_DATA_URI}}

kpi_total = {
    "id": "home-kpi-total", "kind": "kpi-chart", "name": "Total Baseline Units",
    "source": {"kind": "table", "elementId": "rl-base"},
    "columns": [{"id": "home-kpi-total-value", "name": "Total Baseline Units",
                 "formula": "Sum([Reallocation Base/Baseline Units])",
                 "format": {"kind": "number", "formatString": ",d"}}],
    "value": {"columnId": "home-kpi-total-value", "fontSize": 30},
    "style": {"backgroundColor": "#ffffff", "borderColor": "#d7dde8", "borderWidth": 1},
}
kpi_dtc_mix = {
    "id": "home-kpi-dtc", "kind": "kpi-chart", "name": "DTC Mix",
    "source": {"kind": "table", "elementId": "rl-base"},
    "columns": [{"id": "home-kpi-dtc-value", "name": "DTC Mix",
                 "formula": 'Sum(If([Reallocation Base/Channel] = "Direct-to-Consumer", '
                            '[Reallocation Base/Baseline Units], 0)) / '
                            'Sum([Reallocation Base/Baseline Units])',
                 "format": {"kind": "number", "formatString": ".1%"}}],
    "value": {"columnId": "home-kpi-dtc-value", "fontSize": 30},
    "style": {"backgroundColor": "#ffffff", "borderColor": "#d7dde8", "borderWidth": 1},
}
kpi_categories = {
    "id": "home-kpi-cat", "kind": "kpi-chart", "name": "Categories in plan",
    "source": {"kind": "table", "elementId": "rl-base"},
    "columns": [{"id": "home-kpi-cat-value", "name": "Categories in plan",
                 "formula": "CountDistinct([Reallocation Base/Category])",
                 "format": {"kind": "number", "formatString": ",d"}}],
    "value": {"columnId": "home-kpi-cat-value", "fontSize": 30},
    "style": {"backgroundColor": "#ffffff", "borderColor": "#d7dde8", "borderWidth": 1},
}

home_page_id = "page-home"
pages = [{"id": home_page_id, "name": "Home"}, *realloc["pages"], *wf["pages"]]
elements = [header, *( [logo_el] if logo_el else [] ),
            kpi_total, kpi_dtc_mix, kpi_categories,
            *realloc["elements"], *wf["elements"]]
overlays = [*realloc["overlays"], *wf["overlays"]]

logo_layout = '<Element elementId="home-logo" gridColumn="21 / 25" gridRow="1 / 4"/>' if logo_el else ""
home_layout = f"""
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{home_page_id}">
  <Element elementId="home-header" gridColumn="1 / 21" gridRow="1 / 5"/>
  {logo_layout}
  <Element elementId="home-kpi-total" gridColumn="1 / 9" gridRow="5 / 12"/>
  <Element elementId="home-kpi-dtc" gridColumn="9 / 17" gridRow="5 / 12"/>
  <Element elementId="home-kpi-cat" gridColumn="17 / 25" gridRow="5 / 12"/>
  <Element elementId="{wf['unplaced']['create_button']}" gridColumn="1 / 7" gridRow="12 / 15"/>
  <Element elementId="{wf['unplaced']['submit_target_control']}" gridColumn="7 / 17" gridRow="12 / 15"/>
  <Element elementId="{wf['unplaced']['submit_button']}" gridColumn="17 / 25" gridRow="12 / 15"/>
</Page>
"""
layout = home_layout + realloc["layout_xml"] + wf["layout_xml"]

document = {
    "schemaVersion": 1,
    "kind": "workbook",
    "elements": elements,
    "pages": pages,
    "overlays": overlays,
    "layout": layout,
    "settings": {
        "theme": {"name": "Light",
                  "overrides": {"borderRadius": "round", "hasCards": "shown",
                                "colors": {"highlight": NAVY, "success": "#3bb5b3",
                                           "danger": "#ee465c"}}},
        "navigation": {"pageHeader": "enabled", "pageTabsInViewMode": "shown"},
    },
}

body = {
    "name": "YETI — Category & Channel Reallocation Planner",
    "folderId": FOLDER,
    "description": "Composed-surfaces test: reallocation_modeler + approval_workflow, "
                    "no plugin, no PDF report.",
    "document": document,
}


def call(method, path, payload):
    req = urllib.request.Request(
        BASE.rstrip("/") + path, data=json.dumps(payload).encode(), method=method,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
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
