#!/usr/bin/env python3
"""Build/update the 'Scatter Lasso Select — Plugin Demo' workbook.

Reference example: a custom canvas-scatterplot plugin (100K points, rectangle-
brush selection) whose selection drives a native `list` control, which in turn
filters a second table — all wired declaratively via the workbooks-as-code spec,
including the plugin-variable-to-control binding (no manual UI step needed).

See reference/api-cheatsheet.md "More gotchas" for the Cloudflare-WAF key-name
block, the YAML-response parsing trap, and the visibleAsSource/hidden-page fix
this generator had to work around.

Usage:
  eval "$(bash scripts/get-token-staging.sh)"   # sets SIGMA_API_TOKEN, run from millersigma/
  python3 build_scatter_lasso.py [--no-variable-binding]

First run should POST to /v2/workbooks/spec (new workbook); subsequent edits
should PUT to /v2/workbooks/{urlId}/spec (in place) — see sigma-code-rep-
interactivity memory / this file's own history for the pattern.
"""
import json, os, sys, urllib.request, urllib.error

BASE = os.environ["SIGMA_BASE_URL"]
TOKEN = os.environ["SIGMA_API_TOKEN"]
CONNECTION_ID = os.environ.get("CONNECTION_ID", "")   # a Snowflake connection with GENERATOR/NORMAL support
FOLDER_ID = os.environ.get("FOLDER_ID", "")            # target folder id
PLUGIN_ID = os.environ.get("SCATTER_LASSO_PLUGIN_ID", "")  # from scripts/register_plugin.py
WORKBOOK_URL_ID = os.environ.get("WORKBOOK_URL_ID", "")    # set after first POST to PUT-in-place on reruns

SQL = """
WITH seg AS (
  SELECT * FROM VALUES
    (0,'Champions',80,82,9,7),
    (1,'Loyal',62,55,11,9),
    (2,'New',25,20,8,6),
    (3,'At Risk',30,58,10,8),
    (4,'Dormant',15,12,7,5)
  AS t(SEG_IDX,SEGMENT,CX,CY,SPX,SPY)
),
base AS (
  SELECT SEQ4() AS ID, UNIFORM(0,4,RANDOM()) AS SEG_IDX
  FROM TABLE(GENERATOR(ROWCOUNT=>100000))
)
SELECT
  b.ID,
  s.SEGMENT,
  ROUND(GREATEST(0,LEAST(100, NORMAL(s.CX::float, s.SPX::float, RANDOM()))),2) AS TENURE_SCORE,
  ROUND(GREATEST(0,LEAST(100, NORMAL(s.CY::float, s.SPY::float, RANDOM()))),2) AS ENGAGEMENT_SCORE,
  ROUND(GREATEST(5, NORMAL(s.CY::float*6, 40::float, RANDOM())),2) AS LIFETIME_VALUE
FROM base b JOIN seg s ON b.SEG_IDX = s.SEG_IDX
""".strip()

SRC_NAME = "Customer Engagement Base"

def spec(include_var_binding=True):
    src_cols = [
        {"id": "id", "formula": "[Custom SQL/ID]", "name": "Customer ID"},
        {"id": "segment", "formula": "[Custom SQL/SEGMENT]", "name": "Segment"},
        {"id": "tenure", "formula": "[Custom SQL/TENURE_SCORE]", "name": "Tenure Score"},
        {"id": "engagement", "formula": "[Custom SQL/ENGAGEMENT_SCORE]", "name": "Engagement Score"},
        {"id": "ltv", "formula": "[Custom SQL/LIFETIME_VALUE]", "name": "Lifetime Value"},
    ]
    scatter_source = {
        "id": "scatterSource",
        "kind": "table",
        "name": SRC_NAME,
        "source": {"connectionId": CONNECTION_ID, "statement": SQL, "kind": "sql"},
        "columns": src_cols,
        "order": [c["id"] for c in src_cols],
        "visibleAsSource": False,
    }

    filtered_cols = [
        {"id": "f_id", "formula": f"[{SRC_NAME}/Customer ID]", "name": "Customer ID"},
        {"id": "f_segment", "formula": f"[{SRC_NAME}/Segment]", "name": "Segment"},
        {"id": "f_tenure", "formula": f"[{SRC_NAME}/Tenure Score]", "name": "Tenure Score"},
        {"id": "f_engagement", "formula": f"[{SRC_NAME}/Engagement Score]", "name": "Engagement Score"},
        {"id": "f_ltv", "formula": f"[{SRC_NAME}/Lifetime Value]", "name": "Lifetime Value"},
    ]
    filtered_table = {
        "id": "filteredTable",
        "kind": "table",
        "name": "Selected Customers",
        "source": {"elementId": "scatterSource", "kind": "table"},
        "columns": filtered_cols,
        "order": [c["id"] for c in filtered_cols],
    }

    # A native `list` control: populates its picklist from the FULL (unfiltered)
    # scatterSource so it never shrinks, and filters the separate filteredTable.
    control = {
        "id": "segFilterCtrl",
        "kind": "control",
        "controlId": "segment-filter",
        "controlType": "list",
        "source": {"kind": "source", "source": {"elementId": "scatterSource", "kind": "table"}, "columnId": "segment"},
        "filters": [{"source": {"kind": "table", "elementId": "filteredTable"}, "columnId": "f_segment"}],
    }

    plugin_config = {
        "source": {"kind": "element", "elementId": "scatterSource"},
        "xAxis": "tenure",
        "yAxis": "engagement",
        "colorBy": "segment",
        "filterColumn": "segment",
        # dropdown config values must be strings even though the declared `values` are numbers
        "pointSize": "2",
        "pointOpacity": "0.6",
    }
    if include_var_binding:
        # Bare controlId string — same pattern as column bindings. This is what
        # lets the plugin's rectangle-selection reach out and set a REAL Sigma
        # control (segFilterCtrl above) purely from the spec, no manual UI bind.
        plugin_config["selectionVar"] = "segment-filter"

    plugin_el = {
        "id": "scatterPlugin",
        "kind": "plugin",
        "pluginId": PLUGIN_ID,
        "config": plugin_config,
    }

    title = {
        "id": "titleText",
        "kind": "text",
        "body": "### Scatter Lasso Select — Plugin Demo",
        "verticalAlign": "middle",
    }
    caption = {
        "id": "captionText",
        "kind": "text",
        "body": "Drag a rectangle on the scatterplot to select customers. The selected segment(s) filter the table below via the **Segment Filter** control (top right) — try it manually too.",
        "verticalAlign": "middle",
    }

    page1_elements = [title, control, caption, plugin_el, filtered_table]
    # scatterSource lives on its own hidden page: visibleAsSource:false alone
    # does NOT keep an element off the page layout (Sigma auto-appends a
    # LayoutElement for anything you don't place explicitly).
    page2_elements = [scatter_source]

    layout = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page1">\n'
        '  <LayoutElement elementId="titleText" gridColumn="1 / 18" gridRow="1 / 4"/>\n'
        '  <LayoutElement elementId="segFilterCtrl" gridColumn="18 / 25" gridRow="1 / 4"/>\n'
        '  <LayoutElement elementId="captionText" gridColumn="1 / 25" gridRow="4 / 6"/>\n'
        '  <LayoutElement elementId="scatterPlugin" gridColumn="1 / 25" gridRow="6 / 40"/>\n'
        '  <LayoutElement elementId="filteredTable" gridColumn="1 / 25" gridRow="41 / 64"/>\n'
        '</Page>\n'
        '<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page2">\n'
        '  <LayoutElement elementId="scatterSource" gridColumn="1 / 25" gridRow="1 / 21"/>\n'
        '</Page>\n'
    )

    return {
        "name": "Scatter Lasso Select — Plugin Demo",
        "folderId": FOLDER_ID,
        "schemaVersion": 1,
        "pages": [
            {"id": "page1", "name": "Scatter Explorer", "elements": page1_elements},
            {"id": "page2", "name": "Source Data", "elements": page2_elements, "visibility": "hidden"},
        ],
        "layout": layout,
    }


def call(method, url, body):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        # Content matters more than this header for the Cloudflare block (see
        # cheatsheet), but a browser-like UA is cheap insurance either way.
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json", "User-Agent": "curl/8.4.0"},
        method=method,
    )
    try:
        res = urllib.request.urlopen(req, timeout=60)
        raw = res.read().decode()
        # POST/PUT .../spec returns YAML, not JSON — don't let a JSONDecodeError
        # on a SUCCESSFUL call look like a crash (it'll trick you into re-POSTing
        # and creating a duplicate workbook).
        try:
            return True, json.loads(raw)
        except json.JSONDecodeError:
            return True, raw
    except urllib.error.HTTPError as e:
        return False, {"status": e.code, "body": e.read().decode()}


if __name__ == "__main__":
    no_var = "--no-variable-binding" in sys.argv
    body = spec(include_var_binding=not no_var)
    if WORKBOOK_URL_ID:
        url = f"{BASE.rstrip('/')}/v2/workbooks/{WORKBOOK_URL_ID}/spec"
        ok, result = call("PUT", url, body)
    else:
        url = f"{BASE.rstrip('/')}/v2/workbooks/spec"
        ok, result = call("POST", url, body)
    if ok:
        print(json.dumps(result, indent=2) if isinstance(result, dict) else result)
    else:
        print(f"{'PUT' if WORKBOOK_URL_ID else 'POST'} failed ({result['status']}):", file=sys.stderr)
        print(result["body"][:2000], file=sys.stderr)
        sys.exit(1)
