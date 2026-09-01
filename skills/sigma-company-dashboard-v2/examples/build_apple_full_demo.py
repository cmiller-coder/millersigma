#!/usr/bin/env python3
"""Apple Inc. — full composed demo: basic BI + reallocation planner (with
approval workflow baked in) + cohort builder (with activation baked in).

Real segment structure (Apple's actual 10-K reporting): Products (iPhone,
Mac, iPad, Services, Wearables/Home/Accessories) and Geographic segments
(Americas, Europe, Greater China, Japan, Rest of Asia Pacific). Reallocation
grid uses 3 products x 4 regions to keep the demo readable; revenue figures
are illustrative, shaped to real reported mix, not exact real financials.

No bespoke plugin, no PDF report. Logo is Wikimedia Commons' public-domain
Apple wordmark (fetch_logo.py's corporate-site scrape returned a hero photo,
not a logomark -- same "site scrape failed, fall back to Wikipedia's own
lead image" path documented for Honda's build).

Usage:
    python3 build_apple_full_demo.py
    python3 build_apple_full_demo.py BASE TOKEN CONNECTION_ID FOLDER_ID
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                       / "sigma-input-table-app" / "surfaces"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                       / "sigma-cohort-builder-app" / "surfaces"))
import approval_workflow  # noqa: E402
import reallocation_modeler  # noqa: E402
import cohort_activation  # noqa: E402

_ARGS = sys.argv[1:]
BASE = _ARGS[0] if len(_ARGS) > 0 else ""
TOKEN = _ARGS[1] if len(_ARGS) > 1 else ""
CONN = _ARGS[2] if len(_ARGS) > 2 else "<connection-id>"
FOLDER = _ARGS[3] if len(_ARGS) > 3 else "<folder-id>"

INK = "#000000"
CANVAS = "#F5F5F7"  # Apple's own off-white gray, not guessed

LOGO_URI = pathlib.Path(__file__).with_name("apple_logo_black.datauri.txt")
LOGO_DATA_URI = LOGO_URI.read_text().strip() if LOGO_URI.exists() else None

# ----------------------------------------------------------- reallocation
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
)
wf = approval_workflow.build(
    prefix="wf", connection_id=CONN,
    entity_singular="Allocation Plan", entity_plural="Allocation Plans",
)

# ----------------------------------------------------------------- cohort
COHORT_SQL = """
SELECT * FROM VALUES
  ('U0001','Americas','Multi-Device',1),('U0002','Americas','iPhone Only',0),
  ('U0003','Europe','Services Subscriber',1),('U0004','Europe','iPhone Only',1),
  ('U0005','Greater China','Multi-Device',0),('U0006','Greater China','iPhone Only',1),
  ('U0007','Japan','Services Subscriber',0),('U0008','Americas','Multi-Device',1),
  ('U0009','Europe','Multi-Device',1),('U0010','Greater China','Services Subscriber',1)
AS t(customer_id, region, segment_type, is_lapsed)
"""
coh_pop = {
    "id": "coh-pop", "kind": "table", "name": "Customer Population", "visibleAsSource": True,
    "source": {"connectionId": CONN, "kind": "sql", "statement": COHORT_SQL},
    "columns": [
        {"id": "coh-id", "formula": "[Custom SQL/CUSTOMER_ID]", "name": "Customer ID"},
        {"id": "coh-region", "formula": "[Custom SQL/REGION]", "name": "Region"},
        {"id": "coh-segtype", "formula": "[Custom SQL/SEGMENT_TYPE]", "name": "Segment Type"},
        {"id": "coh-lapsed", "formula": "[Custom SQL/IS_LAPSED]", "name": "Is Lapsed"},
    ],
}
ctrl_cohort_name = {
    "id": "ctrl-cohort-name", "kind": "control", "controlId": "cohort_name_ctrl",
    "name": "Cohort Name", "controlType": "text", "case": "insensitive", "mode": "equals",
    "value": "Lapsed Services subscribers", "includeNulls": "when-no-value-is-selected",
    "showOperators": False,
}
title_cohort = {"id": "coh-title", "kind": "text",
                "body": "## **Customer Segmentation**\nName the cohort, choose where to send it, "
                        "and activate."}
tbl_cohort_pop = {
    "id": "coh-tbl", "kind": "table", "name": "Population Detail",
    "source": {"kind": "table", "elementId": "coh-pop"},
    "columns": [
        {"id": "cohd-id", "name": "Customer ID", "formula": "[Customer Population/Customer ID]"},
        {"id": "cohd-region", "name": "Region", "formula": "[Customer Population/Region]"},
        {"id": "cohd-segtype", "name": "Segment Type", "formula": "[Customer Population/Segment Type]"},
        {"id": "cohd-lapsed", "name": "Is Lapsed", "formula": "[Customer Population/Is Lapsed]"},
    ],
    "tableComponents": {"summaryBar": "hidden"},
}

act = cohort_activation.build(
    prefix="act", connection_id=CONN,
    cohort_table_id="coh-pop", cohort_table_name="Customer Population",
    cohort_name_formula="[cohort_name_ctrl]",
    count_formula='CountDistinct(If([Customer Population/Is Lapsed] = 1, '
                  '[Customer Population/Customer ID], Null))',
    destinations=[{"id": "iterable", "label": "Iterable"}, {"id": "braze", "label": "Braze"},
                  {"id": "sfmc", "label": "Salesforce Marketing Cloud"}],
)

# ------------------------------------------------------------------- home
header = {
    "id": "home-header", "kind": "text",
    "body": "## Apple Inc.\n**GLOBAL OPERATIONS PLANNING**\n"
            "# Regional allocation & customer activation\n"
            "Where should the next allocation go, who signs off, and which segment "
            "gets activated next?",
}
logo_el = ({"id": "home-logo", "kind": "image", "source": {"kind": "url", "url": LOGO_DATA_URI}}
           if LOGO_DATA_URI else None)


def kpi(eid, label, formula, source="rl-base", fmt=",d"):
    return {
        "id": eid, "kind": "kpi-chart", "name": label,
        "source": {"kind": "table", "elementId": source},
        "columns": [{"id": eid + "-value", "name": label, "formula": formula,
                     "format": {"kind": "number", "formatString": fmt}}],
        "value": {"columnId": eid + "-value", "fontSize": 30},
        "style": {"backgroundColor": "#ffffff", "borderColor": "#d7dde8", "borderWidth": 1},
    }


kpi_total = kpi("home-kpi-total", "Total Revenue ($M)", "Sum([Reallocation Base/Baseline Revenue ($M)])")
kpi_iphone = kpi("home-kpi-iphone", "iPhone Mix",
                  'Sum(If([Reallocation Base/Category] = "iPhone", '
                  '[Reallocation Base/Baseline Revenue ($M)], 0)) / '
                  'Sum([Reallocation Base/Baseline Revenue ($M)])', fmt=".1%")
kpi_intl = kpi("home-kpi-intl", "Ex-Americas Mix",
               'Sum(If([Reallocation Base/Region] <> "Americas", '
               '[Reallocation Base/Baseline Revenue ($M)], 0)) / '
               'Sum([Reallocation Base/Baseline Revenue ($M)])', fmt=".1%")

home_page_id = "page-home"
cohort_page_id = "page-cohort"
cohort_data_page_id = "page-cohort-data"
pages = [{"id": home_page_id, "name": "Home"}, *realloc["pages"], *wf["pages"],
         {"id": cohort_page_id, "name": "Cohort Builder"},
         {"id": cohort_data_page_id, "name": "Data", "visibility": "hidden"}, *act["pages"]]
elements = [header, *([logo_el] if logo_el else []), kpi_total, kpi_iphone, kpi_intl,
            *realloc["elements"], *wf["elements"],
            coh_pop, ctrl_cohort_name, title_cohort, tbl_cohort_pop, *act["elements"]]
overlays = [*realloc["overlays"], *wf["overlays"], *act["overlays"]]

logo_layout = ('<Element elementId="home-logo" gridColumn="22 / 25" gridRow="1 / 4"/>'
               if logo_el else "")
home_layout = f"""
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{home_page_id}">
  <Element elementId="home-header" gridColumn="1 / 22" gridRow="1 / 5"/>
  {logo_layout}
  <Element elementId="home-kpi-total" gridColumn="1 / 9" gridRow="5 / 12"/>
  <Element elementId="home-kpi-iphone" gridColumn="9 / 17" gridRow="5 / 12"/>
  <Element elementId="home-kpi-intl" gridColumn="17 / 25" gridRow="5 / 12"/>
  <Element elementId="{wf['unplaced']['create_button']}" gridColumn="1 / 7" gridRow="12 / 15"/>
  <Element elementId="{wf['unplaced']['submit_target_control']}" gridColumn="7 / 17" gridRow="12 / 15"/>
  <Element elementId="{wf['unplaced']['submit_button']}" gridColumn="17 / 25" gridRow="12 / 15"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{cohort_page_id}">
  <Element elementId="coh-title" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="ctrl-cohort-name" gridColumn="1 / 13" gridRow="4 / 7"/>
  <Element elementId="{act['unplaced']['destination_control']}" gridColumn="13 / 19" gridRow="4 / 7"/>
  <Element elementId="{act['unplaced']['activate_button']}" gridColumn="19 / 25" gridRow="4 / 7"/>
  <Element elementId="coh-tbl" gridColumn="1 / 25" gridRow="7 / 22"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{cohort_data_page_id}">
  <Element elementId="coh-pop" gridColumn="1 / 25" gridRow="1 / 15"/>
</Page>
"""
layout = home_layout + realloc["layout_xml"] + wf["layout_xml"] + act["layout_xml"]

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
                                "colors": {"highlight": INK, "success": "#3bb5b3",
                                           "danger": "#ee465c"}}},
        "navigation": {"pageHeader": "enabled", "pageTabsInViewMode": "shown"},
    },
}

body = {
    "name": "Apple — Regional Allocation & Customer Activation",
    "folderId": FOLDER,
    "description": "Full composed demo: basic BI + reallocation planner (approval workflow "
                    "baked in) + cohort builder (activation baked in). No plugin, no PDF.",
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
