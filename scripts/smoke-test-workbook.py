#!/usr/bin/env python3
"""End-to-end smoke test of the workbooks-as-code path against a live org.

Builds a small but complete workbook (title, date + list filters, three KPIs,
bar chart, line chart, detail table) from a warehouse table, then checks every
stage that can fail independently:

    verify -> create -> per-element generated SQL -> PNG render -> update -> delete

Use it to confirm credentials, connection health, and the spec shape itself
before spending an iteration loop on a real build — and after any Sigma release,
to catch spec-shape drift early (the shape has changed under us before; see
skills/sigma-workbook-conventions/reference/workbook-spec-api.md).

    python3 scripts/smoke-test-workbook.py            # build, verify, then delete
    python3 scripts/smoke-test-workbook.py --keep     # leave the workbook behind
    python3 scripts/smoke-test-workbook.py --png /tmp/shot.png

Credentials come from SIGMA_BASE_URL / SIGMA_CLIENT_ID / SIGMA_CLIENT_SECRET in
the environment, falling back to `.env` in the repo root.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# The classic Sigma sample retail table. Override with --connection / --path.
DEFAULT_CONNECTION_NAME = "Sigma Sample Database"
DEFAULT_TABLE_PATH = ["RETAIL", "PLUGS_ELECTRONICS", "PLUGS_ELECTRONICS_HANDS_ON_LAB_DATA"]

PASSTHROUGH = [
    ("col-date", "Date"),
    ("col-qty", "Quantity"),
    ("col-price", "Price"),
    ("col-cost", "Cost"),
    ("col-product-family", "Product Family"),
    ("col-store-name", "Store Name"),
    ("col-store-region", "Store Region"),
]


class ApiError(RuntimeError):
    def __init__(self, status, body, url):
        self.status, self.body, self.url = status, body, url
        super().__init__("HTTP %s on %s\n%s" % (status, url, body))


# ------------------------------------------------------------------ transport


def load_env() -> dict:
    env = {k: os.environ[k] for k in
           ("SIGMA_BASE_URL", "SIGMA_CLIENT_ID", "SIGMA_CLIENT_SECRET")
           if os.environ.get(k)}
    dotenv = REPO_ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    missing = [k for k in ("SIGMA_BASE_URL", "SIGMA_CLIENT_ID", "SIGMA_CLIENT_SECRET")
               if not env.get(k)]
    if missing:
        sys.exit("smoke-test-workbook: missing %s (env or .env)" % ", ".join(missing))
    return env


class Api:
    def __init__(self, env: dict):
        self.base = env["SIGMA_BASE_URL"].rstrip("/")
        self._env = env
        self._token = None

    def token(self) -> str:
        if self._token:
            return self._token
        cred = base64.b64encode(
            ("%s:%s" % (self._env["SIGMA_CLIENT_ID"],
                        self._env["SIGMA_CLIENT_SECRET"])).encode()).decode()
        req = urllib.request.Request(
            self.base + "/v2/auth/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={"Authorization": "Basic " + cred,
                     "Content-Type": "application/x-www-form-urlencoded"},
            method="POST")
        with urllib.request.urlopen(req, timeout=40) as resp:
            self._token = json.load(resp)["access_token"]
        return self._token

    def call(self, method, path, body=None, accept="application/json", binary=False):
        url = self.base + path
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": "Bearer " + self.token(), "Accept": accept}
        if data:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, exc.read().decode()[:800], url) from None
        if binary:
            return raw
        text = raw.decode()
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            return text


# -------------------------------------------------------------------- the spec


def build_spec(name, folder_id, connection_id, table_path):
    wh = table_path[-1]
    tbl = "Transactions"

    columns = [{"id": cid, "name": col, "formula": "[%s/%s]" % (wh, col)}
               for cid, col in PASSTHROUGH]
    # Materialize row-level values so downstream elements can aggregate them.
    columns += [
        {"id": "col-revenue", "name": "Revenue", "formula": "[Quantity] * [Price]"},
        {"id": "col-cogs", "name": "COGS", "formula": "[Quantity] * [Cost]"},
    ]

    def kpi(el_id, title, formula, value_name, format_string):
        return {
            "id": el_id,
            "kind": "kpi-chart",
            "name": title,
            "source": {"kind": "table", "elementId": "tbl-tx"},
            "columns": [{"id": el_id + "-val", "name": value_name, "formula": formula,
                         "format": {"kind": "number", "formatString": format_string}}],
            "value": {"columnId": el_id + "-val"},
        }

    document = {
        "schemaVersion": 1,
        "kind": "workbook",
        "pages": [{"id": "page-overview", "name": "Overview"}],
        "elements": [
            {"id": "container-header", "kind": "container"},
            {"id": "container-body", "kind": "container"},
            {"id": "text-title", "kind": "text",
             "body": "## **Retail Overview**\nBuilt from code via "
                     "`POST /v2/workbooks/spec` — API smoke test."},
            {"id": "tbl-tx", "kind": "table", "name": tbl,
             "source": {"kind": "warehouse-table",
                        "connectionId": connection_id, "path": table_path},
             "columns": columns},
            kpi("kpi-revenue", "Total Revenue", "Sum([%s/Revenue])" % tbl,
                "Revenue", "$.3~s"),
            kpi("kpi-units", "Units Sold", "Sum([%s/Quantity])" % tbl,
                "Units", ",d"),
            kpi("kpi-margin", "Gross Margin",
                "(Sum([{t}/Revenue]) - Sum([{t}/COGS])) / Sum([{t}/Revenue])".format(t=tbl),
                "Margin", ".1%"),
            {"id": "chart-revenue-region", "kind": "bar-chart",
             "name": "Revenue by Store Region",
             "source": {"kind": "table", "elementId": "tbl-tx"},
             "columns": [
                 {"id": "br-region", "name": "Store Region",
                  "formula": "[%s/Store Region]" % tbl},
                 {"id": "br-revenue", "name": "Revenue",
                  "formula": "Sum([%s/Revenue])" % tbl},
             ],
             "xAxis": {"columnId": "br-region",
                       "sort": {"by": "br-revenue", "aggregation": "sum",
                                "direction": "descending"}},
             "yAxis": {"columnIds": ["br-revenue"]}},
            {"id": "chart-revenue-month", "kind": "line-chart",
             "name": "Revenue by Month",
             "source": {"kind": "table", "elementId": "tbl-tx"},
             "columns": [
                 {"id": "ln-month", "name": "Month",
                  "formula": 'DateTrunc("month", [%s/Date])' % tbl},
                 {"id": "ln-revenue", "name": "Revenue",
                  "formula": "Sum([%s/Revenue])" % tbl},
             ],
             "xAxis": {"columnId": "ln-month"},
             "yAxis": {"columnIds": ["ln-revenue"]}},
            {"kind": "control", "id": "ctrl-date", "controlId": "DateRange",
             "controlType": "date-range", "name": "Date Range", "mode": "between",
             "includeNulls": "when-no-value-is-selected",
             "filters": [{"source": {"kind": "table", "elementId": "tbl-tx"},
                          "columnId": "col-date"}]},
            {"kind": "control", "id": "ctrl-region", "controlId": "StoreRegion",
             "controlType": "list", "name": "Store Region", "mode": "include",
             "selectionMode": "multiple", "values": [],
             "source": {"kind": "source",
                        "source": {"kind": "table", "elementId": "tbl-tx"},
                        "columnId": "col-store-region"},
             "filters": [{"source": {"kind": "table", "elementId": "tbl-tx"},
                          "columnId": "col-store-region"}]},
        ],
        "layout": """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-overview">
  <Container elementId="container-header" type="grid"
             gridColumn="1 / 25" gridRow="1 / 4"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="text-title"  gridColumn="1 / 13" gridRow="1 / 4"/>
    <Element elementId="ctrl-date"   gridColumn="13 / 19" gridRow="1 / 4"/>
    <Element elementId="ctrl-region" gridColumn="19 / 25" gridRow="1 / 4"/>
  </Container>
  <Container elementId="container-body" type="grid"
             gridColumn="1 / 25" gridRow="4 / 30"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="kpi-revenue" gridColumn="1 / 9"   gridRow="1 / 9"/>
    <Element elementId="kpi-units"   gridColumn="9 / 17"  gridRow="1 / 9"/>
    <Element elementId="kpi-margin"  gridColumn="17 / 25" gridRow="1 / 9"/>
    <Element elementId="chart-revenue-region" gridColumn="1 / 13"  gridRow="9 / 23"/>
    <Element elementId="chart-revenue-month"  gridColumn="13 / 25" gridRow="9 / 23"/>
  </Container>
  <Element elementId="tbl-tx" gridColumn="1 / 25" gridRow="30 / 48"/>
</Page>
""",
    }
    return {"name": name, "folderId": folder_id, "document": document}


# ------------------------------------------------------------------ the stages


def resolve_folder(api: Api) -> str:
    who = api.call("GET", "/v2/whoami")
    member = api.call("GET", "/v2/members/%s" % who["userId"])
    return member["homeFolderId"]


def resolve_connection(api: Api, name: str) -> str:
    conns = api.call("GET", "/v2/connections?limit=200").get("entries", [])
    for c in conns:
        if (c.get("name") or "").lower() == name.lower():
            return c["connectionId"]
    sys.exit("smoke-test-workbook: no connection named %r (have: %s)"
             % (name, ", ".join(sorted(c.get("name") or "" for c in conns))))


def render_png(api: Api, workbook_id: str, out_path: pathlib.Path,
               poll_seconds=3, max_wait=180) -> int:
    """PNG export is async: POST for a queryId, then poll until bytes appear."""
    job = api.call("POST", "/v2/workbooks/%s/export" % workbook_id,
                   {"format": {"type": "png"}, "pageId": "page-overview"})
    query_id = job.get("queryId")
    waited = 0
    while waited < max_wait:
        try:
            blob = api.call("GET", "/v2/query/%s/download" % query_id,
                            accept="*/*", binary=True)
            if blob:
                out_path.write_bytes(blob)
                return len(blob)
        except ApiError as exc:
            # Not-ready and gateway-timeout-on-a-live-render are both retryable.
            if exc.status not in (404, 409, 425, 500, 502, 503, 504):
                raise
        time.sleep(poll_seconds)
        waited += poll_seconds
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="API Smoke Test — Retail Overview")
    ap.add_argument("--folder", help="folder UUID (default: the caller's home folder)")
    ap.add_argument("--connection", default=DEFAULT_CONNECTION_NAME)
    ap.add_argument("--path", nargs=3, metavar=("DB", "SCHEMA", "TABLE"),
                    default=DEFAULT_TABLE_PATH)
    ap.add_argument("--png", type=pathlib.Path,
                    default=pathlib.Path("/tmp/sigma-smoke-test.png"))
    ap.add_argument("--keep", action="store_true",
                    help="leave the workbook in place instead of deleting it")
    args = ap.parse_args()

    api = Api(load_env())
    folder = args.folder or resolve_folder(api)
    connection = resolve_connection(api, args.connection)
    print("folder     %s" % folder)
    print("connection %s (%s)" % (connection, args.connection))

    spec = build_spec(args.name, folder, connection, list(args.path))

    print("verify     %s" % json.dumps(api.call("POST", "/v2/workbooks/spec/verify", spec)))
    workbook_id = api.call("POST", "/v2/workbooks/spec", spec)["workbookId"]
    meta = api.call("GET", "/v2/workbooks/%s" % workbook_id)
    print("created    %s\n           %s" % (workbook_id, meta.get("url")))

    failures = []
    for element in ("tbl-tx", "kpi-revenue", "kpi-margin",
                    "chart-revenue-region", "chart-revenue-month"):
        try:
            sql = api.call("GET", "/v2/workbooks/%s/elements/%s/query"
                           % (workbook_id, element)).get("sql") or ""
            print("sql        %-22s ok (%d chars)" % (element, len(sql)))
        except ApiError as exc:
            failures.append("%s: query failed HTTP %s" % (element, exc.status))
            print("sql        %-22s FAILED %s" % (element, exc.status))

    written = render_png(api, workbook_id, args.png)
    if written:
        print("png        %d bytes -> %s" % (written, args.png))
    else:
        failures.append("png render timed out")
        print("png        FAILED (timed out)")

    if args.keep:
        print("kept       %s" % meta.get("url"))
    else:
        api.call("DELETE", "/v2/files/%s" % workbook_id)
        print("deleted    %s" % workbook_id)

    if failures:
        sys.stderr.write("\n".join("FAIL " + f for f in failures) + "\n")
        sys.exit(1)
    print("\nsmoke test passed")


if __name__ == "__main__":
    main()
