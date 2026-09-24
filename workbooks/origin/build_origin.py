#!/usr/bin/env python3
"""Origin Investments POV — Model of Record + fundraising pulse + Excel writeback.

Built from the 3 Sep 2026 intro call with Dayna McCue (Data and AI Enablement).
Synthetic Redshift-shaped Snowflake SQL on Papercrane staging. Not production
Origin data. Do not mix with OneMedNet or Barton workbooks.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request


HERE = pathlib.Path(__file__).resolve().parent
LOGO_SVG = HERE / "assets" / "origin-logo-white.svg"
CONN = "a9d45cfe-ff65-4515-8193-a7072602a1ee"
FOLDER = "a758d7ee-8c23-423d-9d60-5b635d9e9b58"

NAVY = "#0C2340"
NAVY_DEEP = "#061526"
GOLD = "#C4A35A"
CREAM = "#F4EEE4"
CANVAS = "#F7F4EE"
CARD = "#FFFFFF"
BORDER = "#D9D1C3"
TEXT = "#0C2340"
MUTED = "#C9D6E5"
WHITE = "#FFFFFF"

MONEY = {
    "kind": "number",
    "formatString": "$.3~s",
    "currencySymbol": "$",
    "decimalSymbol": ".",
    "digitGroupingSymbol": ",",
    "digitGroupingSize": [3],
}
MONEY0 = {
    "kind": "number",
    "formatString": "$,.0f",
    "currencySymbol": "$",
    "decimalSymbol": ".",
    "digitGroupingSymbol": ",",
    "digitGroupingSize": [3],
}
PCT1 = {"kind": "number", "formatString": ".1%"}
PCT2 = {"kind": "number", "formatString": "+,.1%"}
NUM0 = {"kind": "number", "formatString": ",.0f"}
NUM1 = {"kind": "number", "formatString": ",.1f"}

SCOPE = (
    "Proof of value on deterministic Snowflake-generated records shaped like Origin's "
    "Redshift warehouse — not production fund accounting. Product names, Sunbelt "
    "markets and Excel-on-desktop language come from Origin's public site and the "
    "3 Sep 2026 discovery call. AskSimon stays the chat layer; this workbook is the "
    "governed, shareable model of record."
)

ASSET_SQL = r"""
WITH months AS (
  SELECT SEQ4() AS month_offset
  FROM TABLE(GENERATOR(ROWCOUNT => 18))
),
assets AS (
  SELECT SEQ4() AS n
  FROM TABLE(GENERATOR(ROWCOUNT => 48))
),
base AS (
  SELECT
    n,
    GET(ARRAY_CONSTRUCT(
      'Dallas','Charlotte','Nashville','Miami','Denver','Austin','Phoenix','Tampa'
    ), MOD(n, 8))::STRING AS market,
    CASE
      WHEN n < 20 THEN 'IncomePlus Fund'
      WHEN n < 32 THEN 'Select Asset Fund'
      WHEN n < 40 THEN 'Origin Exchange'
      WHEN n < 45 THEN 'Private Credit'
      ELSE 'QOZ Program'
    END AS strategy,
    CASE
      WHEN n < 20 THEN 'Common equity'
      WHEN n < 32 THEN IFF(MOD(n, 3) = 0, 'Preferred equity', 'Common equity')
      WHEN n < 40 THEN 'DST'
      WHEN n < 45 THEN 'Senior debt'
      ELSE 'Common equity'
    END AS capital_stack,
    GET(ARRAY_CONSTRUCT(
      'The Hartley','Creekside','Ridgeview','Sycamore Flats','The Millwright',
      'Oak & Line','Riverbend','Station 12','The Marlowe','Canvas',
      'North Park','Southbank'
    ), MOD(n, 12))::STRING AS community,
    180 + MOD(ABS(HASH(n)), 260) AS units,
    42000000 + MOD(ABS(HASH(n * 17)), 110000000) AS gav_seed,
    IFF(MOD(n, 11) = 0, 'Desktop Excel', 'Published in warehouse') AS source_of_truth,
    IFF(MOD(n, 11) = 0, 'Peter', 'Asset Management') AS model_owner
  FROM assets
)
SELECT
  DATEADD('month', month_offset - 17, DATE_TRUNC('month', CURRENT_DATE())) AS as_of_month,
  'ORI-' || LPAD(TO_VARCHAR(n), 3, '0') AS asset_id,
  community || ' ' || market AS asset_name,
  market,
  strategy,
  capital_stack,
  units,
  LEAST(0.985, GREATEST(0.88,
    0.905
    + 0.0035 * month_offset
    + (MOD(ABS(HASH(n * 31)), 40) - 18) / 1000.0
  )) AS occupancy,
  ROUND(gav_seed * (1 + 0.004 * (month_offset - 9)), 0) AS gav,
  ROUND(
    gav_seed * (1 + 0.004 * (month_offset - 9))
    * LEAST(0.985, GREATEST(0.88,
        0.905 + 0.0035 * month_offset + (MOD(ABS(HASH(n * 31)), 40) - 18) / 1000.0
      ))
    * (0.048 + MOD(ABS(HASH(n * 7)), 14) / 1000.0),
    0
  ) AS noi,
  0.048 + MOD(ABS(HASH(n * 7)), 14) / 1000.0 AS cap_rate,
  source_of_truth,
  model_owner,
  IFF(source_of_truth = 'Desktop Excel', 'Waiting on desktop', 'Ready') AS qe_status,
  IFF(
    DATEADD('month', month_offset - 17, DATE_TRUNC('month', CURRENT_DATE()))
      = DATE_TRUNC('month', CURRENT_DATE()),
    1, 0
  ) AS is_current,
  IFF(
    DATEADD('month', month_offset - 17, DATE_TRUNC('month', CURRENT_DATE()))
      = DATEADD('month', -1, DATE_TRUNC('month', CURRENT_DATE())),
    1, 0
  ) AS is_prior
FROM base
CROSS JOIN months
""".strip()

REGISTRY_SQL = r"""
SELECT * FROM (
  VALUES
    ('IncomePlus NAV & distribution model', 'IncomePlus Fund', 'Peter',
     'Desktop Excel', 'Marketing deck, investor services, IC', '2026-08-28', 'Waiting on desktop'),
    ('Select Asset development waterfall', 'Select Asset Fund', 'Peter',
     'Desktop Excel', 'Acquisitions, finance', '2026-09-02', 'Waiting on desktop'),
    ('Origin Exchange DST inventory', 'Origin Exchange', 'Investor Services',
     'Published in warehouse', '1031 advisors, sales', '2026-09-08', 'Ready'),
    ('Private Credit book & covenants', 'Private Credit', 'Origin Credit Advisers',
     'SharePoint workbook', 'Investment management, finance', '2026-09-05', 'In review'),
    ('QOZ project-level IRRs', 'QOZ Program', 'Acquisitions',
     'Desktop Excel', 'Tax, investor services', '2026-08-19', 'Waiting on desktop'),
    ('Sunbelt occupancy & rent (Multilytics feed)', 'IncomePlus Fund', 'Asset Management',
     'Published in warehouse', 'IM, marketing', '2026-09-09', 'Ready'),
    ('Quarter-end IC pack', 'IncomePlus Fund', 'Finance',
     'Desktop Excel', 'Leadership, marketing', '2026-09-04', 'Waiting on desktop'),
    ('Fundraising pacing vs Salesforce', 'IncomePlus Fund', 'Sales ops',
     'Published in warehouse', 'Sales, marketing', '2026-09-09', 'Ready')
) AS t(model_name, strategy, owner, location, consumed_by, last_touch, qe_status)
""".strip()

SALES_SQL = r"""
WITH opps AS (
  SELECT SEQ4() AS n
  FROM TABLE(GENERATOR(ROWCOUNT => 160))
)
SELECT
  'OPP-' || LPAD(TO_VARCHAR(n), 4, '0') AS opportunity_id,
  GET(ARRAY_CONSTRUCT(
    'IncomePlus Fund','Origin Exchange','Private Credit','Select Asset Fund','QOZ Program'
  ), MOD(n, 5))::STRING AS product,
  GET(ARRAY_CONSTRUCT(
    'Prospecting','Diligence','Soft circle','Committed','Closed Won'
  ), MOD(ABS(HASH(n * 13)), 5))::STRING AS stage,
  GET(ARRAY_CONSTRUCT(
    'North Central RIA','Southeast wealth','Texas family office','National 1031',
    'Independent BD','Chicago private bank'
  ), MOD(n, 6))::STRING AS channel,
  GET(ARRAY_CONSTRUCT(
    'IncomePlus RIA tour','1031 advisor series','Credit interval launch',
    'Multilytics webinar','QOZ tax roundtable'
  ), MOD(n, 5))::STRING AS campaign,
  GET(ARRAY_CONSTRUCT(
    'Avery Chen','Marcus Hale','Priya Shah','Jordan Blake','Elena Ruiz'
  ), MOD(n, 5))::STRING AS owner,
  250000 + MOD(ABS(HASH(n * 41)), 7800000) AS amount,
  1850 + MOD(ABS(HASH(n * 19)), 42000) AS campaign_spend,
  DATEADD('day', MOD(ABS(HASH(n)), 260) - 200, CURRENT_DATE()) AS close_date,
  420000000 AS fy_target,
  IFF(GET(ARRAY_CONSTRUCT(
    'Prospecting','Diligence','Soft circle','Committed','Closed Won'
  ), MOD(ABS(HASH(n * 13)), 5))::STRING = 'Closed Won', 1, 0) AS is_closed,
  IFF(GET(ARRAY_CONSTRUCT(
    'Prospecting','Diligence','Soft circle','Committed','Closed Won'
  ), MOD(ABS(HASH(n * 13)), 5))::STRING IN ('Soft circle','Committed'), 1, 0) AS in_pipeline
FROM opps
""".strip()

FORECAST_SQL = r"""
SELECT * FROM (
  VALUES
    ('IncomePlus Fund', 0.946, 61200000, 1.008),
    ('Select Asset Fund', 0.912, 18400000, 1.021),
    ('Origin Exchange', 0.961, 9800000, 1.006),
    ('Private Credit', 1.000, 22100000, 1.000),
    ('QOZ Program', 0.889, 6400000, 1.018)
) AS t(strategy, published_occupancy, published_noi, base_case_mult)
""".strip()

elements: list[dict] = []


def add(el: dict) -> dict:
    elements.append(el)
    return el


def b64_svg(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def header_bg() -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="220" viewBox="0 0 1600 220">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0.35">
      <stop offset="0%" stop-color="{NAVY_DEEP}"/>
      <stop offset="55%" stop-color="{NAVY}"/>
      <stop offset="100%" stop-color="#1A4A73"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.82" cy="0.2" r="0.55">
      <stop offset="0%" stop-color="{GOLD}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{NAVY}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1600" height="220" fill="url(#g)"/>
  <rect width="1600" height="220" fill="url(#glow)"/>
  <rect y="217" width="1600" height="3" fill="{GOLD}"/>
</svg>"""
    return b64_svg(svg)


def card_grad(a: str, b: str) -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="280" viewBox="0 0 520 280">
  <defs><linearGradient id="c" x1="0" y1="0" x2="0.9" y2="1">
    <stop offset="0%" stop-color="{a}"/><stop offset="100%" stop-color="{b}"/>
  </linearGradient></defs>
  <rect width="520" height="280" fill="url(#c)"/>
</svg>"""
    return b64_svg(svg)


def logo_uri() -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.read_bytes()).decode()


def sql_table(eid: str, name: str, statement: str, columns: list[dict]) -> None:
    add({
        "id": eid,
        "kind": "table",
        "name": name,
        "visibleAsSource": True,
        "source": {"kind": "sql", "connectionId": CONN, "statement": statement},
        "columns": columns,
    })


def list_control(eid: str, cid: str, name: str, table_id: str, column_id: str, extra=()) -> None:
    add({
        "kind": "control",
        "id": eid,
        "controlId": cid,
        "name": name,
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [],
        "filters": [{"source": {"kind": "table", "elementId": table_id}, "columnId": column_id}, *extra],
        "source": {
            "kind": "source",
            "source": {"kind": "table", "elementId": table_id},
            "columnId": column_id,
        },
    })


def nav(idx: int) -> None:
    add({
        "id": f"nav{idx}",
        "kind": "navigation",
        "mode": "manual",
        "showIcons": False,
        "optionStyle": {
            "textColor": MUTED,
            "selectedColor": WHITE,
            "style": "pill",
            "orientation": "horizontal",
        },
        "options": [
            {"label": "Model of Record", "destination": {"type": "page", "pageId": "pg1"}},
            {"label": "Sales & Marketing", "destination": {"type": "page", "pageId": "pg2"}},
            {"label": "Quarter-end Writeback", "destination": {"type": "page", "pageId": "pg3"}},
        ],
    })


def header_block(idx: int, title: str, subtitle: str) -> None:
    add({
        "id": f"c-hdr{idx}",
        "kind": "container",
        "spacing": "small",
        "style": {"backgroundColor": NAVY, "borderRadius": "round", "padding": "none"},
        "backgroundImage": {"source": {"kind": "url", "url": header_bg()}, "style": {"fit": "cover"}},
    })
    add({
        "id": f"logo{idx}",
        "kind": "image",
        "source": {"kind": "url", "url": logo_uri()},
        "style": {"fit": "contain", "align": "start", "padding": "none"},
    })
    add({
        "id": f"ttl{idx}",
        "kind": "text",
        "body": f'# **<span style="color: #FFFFFF">{title}</span>**',
        "style": {"backgroundColor": "transparent", "padding": "none"},
        "verticalAlign": "end",
    })
    add({
        "id": f"sub{idx}",
        "kind": "text",
        "body": f'<span style="color: #E6D5A8">{subtitle}</span>',
        "style": {"backgroundColor": "transparent", "padding": "none"},
        "verticalAlign": "start",
    })
    nav(idx)


def kpi_card(key: str, src: str, label: str, cur: str, pri: str, fmt: dict, ga: str, gb: str) -> None:
    add({
        "id": f"c-{key}",
        "kind": "container",
        "spacing": "small",
        "style": {"borderRadius": "round", "padding": "none"},
        "backgroundImage": {"source": {"kind": "url", "url": card_grad(ga, gb)}, "style": {"fit": "cover"}},
    })
    add({
        "id": f"kc-{key}",
        "kind": "kpi-chart",
        "source": {"elementId": src, "kind": "table"},
        "columns": [
            {"id": f"vc-{key}", "formula": cur, "name": label, "format": fmt},
            {"id": f"vk-{key}", "formula": pri, "name": "Prior month", "format": fmt},
        ],
        "value": {"columnId": f"vc-{key}", "color": WHITE, "fontSize": 26},
        "comparisonColumn": {"columnId": f"vk-{key}"},
        "comparison": {
            "display": "delta",
            "colorGood": "#CDEBB8",
            "colorBad": "#FFCFC7",
            "fontSize": 13,
        },
        "name": {"text": label, "color": WHITE, "fontSize": 12},
        "layout": {"anchor": "middle"},
        "style": {"padding": "none", "backgroundColor": ga},
    })
    add({
        "id": f"kp-{key}",
        "kind": "kpi-chart",
        "source": {"elementId": src, "kind": "table"},
        "columns": [{"id": f"vp-{key}", "formula": pri, "name": "Prior month", "format": fmt}],
        "value": {"columnId": f"vp-{key}", "color": WHITE, "fontSize": 20},
        "name": {"text": "Prior month", "color": WHITE, "fontSize": 12},
        "layout": {"anchor": "middle"},
        "style": {"padding": "none", "backgroundColor": gb},
    })


def read_env(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    # Injected SIGMA_CLIENT_ID may belong to a different org than Papercrane
    # staging. Prefer file values; fill gaps from the environment only.
    for key in ("SIGMA_BASE_URL", "SIGMA_CLIENT_ID", "SIGMA_CLIENT_SECRET",
                "SIGMA_PAPERCRANE_API_BASE", "SIGMA_PAPERCRANE_CLIENT_ID",
                "SIGMA_PAPERCRANE_CLIENT_SECRET"):
        if key not in values and os.environ.get(key):
            values[key] = os.environ[key]
    return values


class SigmaApi:
    def __init__(self, env: dict[str, str]):
        self.base = (
            env.get("SIGMA_PAPERCRANE_API_BASE")
            or env.get("SIGMA_API_BASE")
            or env.get("SIGMA_BASE_URL")
        )
        client_id = env.get("SIGMA_PAPERCRANE_CLIENT_ID") or env.get("SIGMA_CLIENT_ID")
        client_secret = env.get("SIGMA_PAPERCRANE_CLIENT_SECRET") or env.get("SIGMA_CLIENT_SECRET")
        if not self.base or not client_id or not client_secret:
            raise RuntimeError("Sigma base URL, client id, and client secret are required")
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        request = urllib.request.Request(
            self.base + "/v2/auth/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            self.token = json.load(response)["access_token"]

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Sigma {method} {path} failed ({exc.code}): " + exc.read().decode()[:4000]
            ) from None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return raw


def build_spec() -> dict:
    elements.clear()

    sql_table("tbl-asset", "Asset Ledger", ASSET_SQL, [
        {"id": "a-month", "formula": "[Custom SQL/as_of_month]", "name": "As Of Month"},
        {"id": "a-id", "formula": "[Custom SQL/asset_id]", "name": "Asset Id"},
        {"id": "a-name", "formula": "[Custom SQL/asset_name]", "name": "Asset"},
        {"id": "a-mkt", "formula": "[Custom SQL/market]", "name": "Market"},
        {"id": "a-strat", "formula": "[Custom SQL/strategy]", "name": "Strategy"},
        {"id": "a-stack", "formula": "[Custom SQL/capital_stack]", "name": "Capital Stack"},
        {"id": "a-units", "formula": "[Custom SQL/units]", "name": "Units", "format": NUM0},
        {"id": "a-occ", "formula": "[Custom SQL/occupancy]", "name": "Occupancy", "format": PCT1},
        {"id": "a-gav", "formula": "[Custom SQL/gav]", "name": "Gross Asset Value", "format": MONEY0},
        {"id": "a-noi", "formula": "[Custom SQL/noi]", "name": "NOI", "format": MONEY0},
        {"id": "a-cap", "formula": "[Custom SQL/cap_rate]", "name": "Cap Rate", "format": PCT1},
        {"id": "a-src", "formula": "[Custom SQL/source_of_truth]", "name": "Source of Truth"},
        {"id": "a-own", "formula": "[Custom SQL/model_owner]", "name": "Model Owner"},
        {"id": "a-qe", "formula": "[Custom SQL/qe_status]", "name": "Quarter-End Status"},
        {"id": "a-cur", "formula": "[Custom SQL/is_current]", "name": "Is Current"},
        {"id": "a-pri", "formula": "[Custom SQL/is_prior]", "name": "Is Prior"},
    ])
    sql_table("tbl-reg", "Model Registry", REGISTRY_SQL, [
        {"id": "r-name", "formula": "[Custom SQL/model_name]", "name": "Model"},
        {"id": "r-strat", "formula": "[Custom SQL/strategy]", "name": "Strategy"},
        {"id": "r-own", "formula": "[Custom SQL/owner]", "name": "Owner"},
        {"id": "r-loc", "formula": "[Custom SQL/location]", "name": "Where it lives"},
        {"id": "r-use", "formula": "[Custom SQL/consumed_by]", "name": "Consumed by"},
        {"id": "r-touch", "formula": "[Custom SQL/last_touch]", "name": "Last touch"},
        {"id": "r-qe", "formula": "[Custom SQL/qe_status]", "name": "Quarter-End Status"},
    ])
    sql_table("tbl-sales", "Fundraising Book", SALES_SQL, [
        {"id": "s-id", "formula": "[Custom SQL/opportunity_id]", "name": "Opportunity Id"},
        {"id": "s-prod", "formula": "[Custom SQL/product]", "name": "Product"},
        {"id": "s-stg", "formula": "[Custom SQL/stage]", "name": "Stage"},
        {"id": "s-ch", "formula": "[Custom SQL/channel]", "name": "Channel"},
        {"id": "s-camp", "formula": "[Custom SQL/campaign]", "name": "Campaign"},
        {"id": "s-own", "formula": "[Custom SQL/owner]", "name": "Owner"},
        {"id": "s-amt", "formula": "[Custom SQL/amount]", "name": "Amount", "format": MONEY0},
        {"id": "s-spend", "formula": "[Custom SQL/campaign_spend]", "name": "Campaign Spend", "format": MONEY0},
        {"id": "s-dt", "formula": "[Custom SQL/close_date]", "name": "Close Date"},
        {"id": "s-tgt", "formula": "[Custom SQL/fy_target]", "name": "FY Target", "format": MONEY0},
        {"id": "s-cl", "formula": "[Custom SQL/is_closed]", "name": "Is Closed"},
        {"id": "s-pl", "formula": "[Custom SQL/in_pipeline]", "name": "In Pipeline"},
    ])
    sql_table("tbl-fcst", "Forecast Source", FORECAST_SQL, [
        {"id": "f-strat", "formula": "[Custom SQL/strategy]", "name": "Strategy"},
        {"id": "f-occ", "formula": "[Custom SQL/published_occupancy]", "name": "Published Occupancy", "format": PCT1},
        {"id": "f-noi", "formula": "[Custom SQL/published_noi]", "name": "Published NOI", "format": MONEY0},
        {"id": "f-mult", "formula": "[Custom SQL/base_case_mult]", "name": "Base Case Mult", "format": NUM1},
    ])

    header_block(
        1,
        "Origin — Model of Record",
        "Investment management & investor services · one published number, not Peter's laptop",
    )
    add({
        "id": "scope1",
        "kind": "text",
        "body": SCOPE,
        "style": {"backgroundColor": CREAM, "borderRadius": "round", },
    })

    list_control("ctrl-mkt", "OriginMarket", "Market", "tbl-asset", "a-mkt")
    list_control(
        "ctrl-strat",
        "OriginStrategy",
        "Strategy",
        "tbl-asset",
        "a-strat",
        extra=[{"source": {"kind": "table", "elementId": "tbl-reg"}, "columnId": "r-strat"}],
    )
    list_control("ctrl-src", "OriginSource", "Source of truth", "tbl-asset", "a-src")

    AL = "Asset Ledger"
    kpi_card(
        "gav", "tbl-asset", "Gross asset value",
        f"Sum(If([{AL}/Is Current] = 1, [{AL}/Gross Asset Value], 0))",
        f"Sum(If([{AL}/Is Prior] = 1, [{AL}/Gross Asset Value], 0))",
        MONEY, NAVY, "#16385C",
    )
    kpi_card(
        "occ", "tbl-asset", "In-place occupancy",
        f"Sum(If([{AL}/Is Current] = 1, [{AL}/Occupancy] * [{AL}/Units], 0)) / NullIf(Sum(If([{AL}/Is Current] = 1, [{AL}/Units], 0)), 0)",
        f"Sum(If([{AL}/Is Prior] = 1, [{AL}/Occupancy] * [{AL}/Units], 0)) / NullIf(Sum(If([{AL}/Is Prior] = 1, [{AL}/Units], 0)), 0)",
        PCT1, "#16385C", "#1F4E79",
    )
    kpi_card(
        "noi", "tbl-asset", "In-place NOI",
        f"Sum(If([{AL}/Is Current] = 1, [{AL}/NOI], 0))",
        f"Sum(If([{AL}/Is Prior] = 1, [{AL}/NOI], 0))",
        MONEY, "#1F4E79", "#245886",
    )
    kpi_card(
        "desk", "tbl-asset", "Desktop models outstanding",
        f"CountDistinct(If([{AL}/Is Current] = 1 And [{AL}/Source of Truth] = \"Desktop Excel\", [{AL}/Asset Id], Null))",
        f"CountDistinct(If([{AL}/Is Prior] = 1 And [{AL}/Source of Truth] = \"Desktop Excel\", [{AL}/Asset Id], Null))",
        NUM0, "#6B4F1D", GOLD,
    )

    add({
        "id": "ch-occ",
        "kind": "bar-chart",
        "source": {"elementId": "tbl-asset", "kind": "table"},
        "columns": [
            {"id": "ch-occ-x", "formula": f"[{AL}/Market]", "name": "Market"},
            {"id": "ch-occ-y", "formula": (
                f"Sum(If([{AL}/Is Current] = 1, [{AL}/Occupancy] * [{AL}/Units], 0)) "
                f"/ NullIf(Sum(If([{AL}/Is Current] = 1, [{AL}/Units], 0)), 0)"
            ), "name": "Occupancy", "format": PCT1},
        ],
        "xAxis": {"columnId": "ch-occ-x"},
        "yAxis": {"columnIds": ["ch-occ-y"], "format": {"scale": {"type": "linear", "zero": False}}},
        "name": {"text": "Current occupancy by Sunbelt market", "fontSize": 14},
        "legend": {"visibility": "hidden"},
        "style": {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1, "borderRadius": "round"},
    })
    add({
        "id": "ch-gav",
        "kind": "bar-chart",
        "source": {"elementId": "tbl-asset", "kind": "table"},
        "columns": [
            {"id": "ch-gav-x", "formula": f"[{AL}/Strategy]", "name": "Strategy"},
            {"id": "ch-gav-y", "formula": f"Sum(If([{AL}/Is Current] = 1, [{AL}/Gross Asset Value], 0))",
             "name": "GAV", "format": MONEY},
        ],
        "xAxis": {"columnId": "ch-gav-x"},
        "yAxis": {"columnIds": ["ch-gav-y"]},
        "name": {"text": "Gross asset value by offering", "fontSize": 14},
        "legend": {"visibility": "hidden"},
        "style": {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1, "borderRadius": "round"},
    })
    add({
        "id": "tbl-grid",
        "kind": "table",
        "name": "Property model grid",
        "source": {"elementId": "tbl-asset", "kind": "table"},
        "columns": [
            {"id": "g-name", "formula": f"[{AL}/Asset]", "name": "Asset"},
            {"id": "g-mkt", "formula": f"[{AL}/Market]", "name": "Market"},
            {"id": "g-st", "formula": f"[{AL}/Strategy]", "name": "Strategy"},
            {"id": "g-un", "formula": f"[{AL}/Units]", "name": "Units", "format": NUM0},
            {"id": "g-occ", "formula": f"[{AL}/Occupancy]", "name": "Occupancy", "format": PCT1},
            {"id": "g-gav", "formula": f"[{AL}/Gross Asset Value]", "name": "GAV", "format": MONEY0},
            {"id": "g-noi", "formula": f"[{AL}/NOI]", "name": "NOI", "format": MONEY0},
            {"id": "g-src", "formula": f"[{AL}/Source of Truth]", "name": "Source of Truth"},
            {"id": "g-own", "formula": f"[{AL}/Model Owner]", "name": "Owner"},
            {"id": "g-qe", "formula": f"[{AL}/Quarter-End Status]", "name": "QE Status"},
            {"id": "g-cur", "formula": f"[{AL}/Is Current]", "name": "Is Current"},
        ],
    })
    add({
        "kind": "control",
        "id": "ctrl-cur",
        "controlId": "OriginCurrentMonth",
        "name": "Current month",
        "controlType": "list",
        "mode": "include",
        "selectionMode": "single",
        "values": [1],
        "filters": [{"source": {"kind": "table", "elementId": "tbl-grid"}, "columnId": "g-cur"}],
        "source": {
            "kind": "source",
            "source": {"kind": "table", "elementId": "tbl-grid"},
            "columnId": "g-cur",
        },
    })
    add({
        "id": "tbl-chase",
        "kind": "table",
        "name": "Quarter-end chase list",
        "source": {"elementId": "tbl-reg", "kind": "table"},
        "columns": [
            {"id": "c-m", "formula": "[Model Registry/Model]", "name": "Model"},
            {"id": "c-o", "formula": "[Model Registry/Owner]", "name": "Owner"},
            {"id": "c-l", "formula": "[Model Registry/Where it lives]", "name": "Where it lives"},
            {"id": "c-u", "formula": "[Model Registry/Consumed by]", "name": "Who needs it"},
            {"id": "c-t", "formula": "[Model Registry/Last touch]", "name": "Last touch"},
            {"id": "c-q", "formula": "[Model Registry/Quarter-End Status]", "name": "Status"},
        ],
    })
    add({
        "id": "note1",
        "kind": "text",
        "body": (
            "**Why this page exists.** IM and accounting want to stay in Excel — "
            "the rest of Origin cannot. Filter to Desktop Excel to see the assets "
            "still trapped on a laptop at quarter-end. Same grid, live warehouse grain, "
            "permissioned share instead of a scavenger hunt for Peter's file."
        ),
        "style": {"backgroundColor": CARD, "borderRadius": "round", },
    })

    header_block(
        2,
        "Origin — Sales & Marketing Pulse",
        "One click for the road · fundraising pacing, Salesforce-shaped pipeline, campaign performance",
    )
    add({
        "id": "scope2",
        "kind": "text",
        "body": SCOPE,
        "style": {"backgroundColor": CREAM, "borderRadius": "round", },
    })
    list_control("ctrl-prod", "OriginProduct", "Product", "tbl-sales", "s-prod")
    list_control("ctrl-stage", "OriginStage", "Stage", "tbl-sales", "s-stg")
    list_control("ctrl-camp", "OriginCampaign", "Campaign", "tbl-sales", "s-camp")

    FB = "Fundraising Book"
    kpi_card(
        "raised", "tbl-sales", "YTD closed",
        f"Sum(If([{FB}/Is Closed] = 1, [{FB}/Amount], 0))",
        f"Max([{FB}/FY Target]) * 0.62",
        MONEY, NAVY, "#16385C",
    )
    kpi_card(
        "pace", "tbl-sales", "Pace to FY target",
        f"Sum(If([{FB}/Is Closed] = 1, [{FB}/Amount], 0)) / NullIf(Max([{FB}/FY Target]), 0)",
        "0.75",
        PCT1, "#16385C", "#1F4E79",
    )
    kpi_card(
        "pipe", "tbl-sales", "Soft circle + committed",
        f"Sum(If([{FB}/In Pipeline] = 1, [{FB}/Amount], 0))",
        f"Sum(If([{FB}/In Pipeline] = 1, [{FB}/Amount], 0)) * 0.91",
        MONEY, "#1F4E79", "#245886",
    )
    kpi_card(
        "roas", "tbl-sales", "Closed $ per campaign $",
        f"Sum(If([{FB}/Is Closed] = 1, [{FB}/Amount], 0)) / NullIf(Sum([{FB}/Campaign Spend]), 0)",
        "18",
        NUM1, "#6B4F1D", GOLD,
    )
    add({
        "id": "ch-funnel",
        "kind": "bar-chart",
        "source": {"elementId": "tbl-sales", "kind": "table"},
        "columns": [
            {"id": "fn-x", "formula": f"[{FB}/Stage]", "name": "Stage"},
            {"id": "fn-y", "formula": f"Sum([{FB}/Amount])", "name": "Amount", "format": MONEY},
            {"id": "fn-o", "formula": (
                f'Switch([{FB}/Stage], "Prospecting", 1, "Diligence", 2, '
                f'"Soft circle", 3, "Committed", 4, "Closed Won", 5, 9)'
            ), "name": "Stage Order"},
        ],
        "xAxis": {"columnId": "fn-x", "sort": {"by": "fn-o", "direction": "ascending"}},
        "yAxis": {"columnIds": ["fn-y"]},
        "name": {"text": "Pipeline by stage", "fontSize": 14},
        "legend": {"visibility": "hidden"},
        "style": {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1, "borderRadius": "round"},
    })
    add({
        "id": "ch-camp",
        "kind": "bar-chart",
        "source": {"elementId": "tbl-sales", "kind": "table"},
        "columns": [
            {"id": "cp-x", "formula": f"[{FB}/Campaign]", "name": "Campaign"},
            {"id": "cp-y", "formula": f"Sum(If([{FB}/Is Closed] = 1, [{FB}/Amount], 0))",
             "name": "Closed", "format": MONEY},
        ],
        "xAxis": {"columnId": "cp-x"},
        "yAxis": {"columnIds": ["cp-y"]},
        "name": {"text": "Closed capital by campaign", "fontSize": 14},
        "legend": {"visibility": "hidden"},
        "style": {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1, "borderRadius": "round"},
    })
    add({
        "id": "tbl-opps",
        "kind": "table",
        "name": "Opportunity list",
        "source": {"elementId": "tbl-sales", "kind": "table"},
        "columns": [
            {"id": "o-id", "formula": f"[{FB}/Opportunity Id]", "name": "Opportunity"},
            {"id": "o-p", "formula": f"[{FB}/Product]", "name": "Product"},
            {"id": "o-s", "formula": f"[{FB}/Stage]", "name": "Stage"},
            {"id": "o-c", "formula": f"[{FB}/Channel]", "name": "Channel"},
            {"id": "o-k", "formula": f"[{FB}/Campaign]", "name": "Campaign"},
            {"id": "o-w", "formula": f"[{FB}/Owner]", "name": "Owner"},
            {"id": "o-a", "formula": f"[{FB}/Amount]", "name": "Amount", "format": MONEY0},
            {"id": "o-d", "formula": f"[{FB}/Close Date]", "name": "Close Date"},
        ],
    })
    add({
        "id": "note2",
        "kind": "text",
        "body": (
            "**Sales on the road.** Dayna's read: warehouse is further along for "
            "marketing and sales than for IM. This page is the one-click alternative "
            "to Salesforce MFA → Tableau → hunt the dashboard. Same Redshift grain "
            "AskSimon already reads — Sigma is the visual, shareable layer."
        ),
        "style": {"backgroundColor": CARD, "borderRadius": "round", },
    })

    header_block(
        3,
        "Origin — Quarter-end writeback",
        "Spreadsheet UI they already love · published baseline, typed overrides, audit-ready",
    )
    add({
        "id": "scope3",
        "kind": "text",
        "body": (
            SCOPE + " Edit occupancy in the grid. KPIs and the variance chart move immediately. "
            "Production would inherit warehouse permissions and an audit log — the control "
            "IM asked for without leaving Excel muscle memory."
        ),
        "style": {"backgroundColor": CREAM, "borderRadius": "round", },
    })
    add({
        "id": "assum",
        "kind": "input-table",
        "source": {"kind": "linked", "from": "tbl-fcst"},
        "inputMode": "view",
        "name": "Assumptions",
        "columns": [
            {"id": "ia-st", "key": "f-strat"},
            {"id": "ia-occ", "key": "f-occ"},
            {"id": "ia-noi", "key": "f-noi"},
            {"id": "ia-mult", "key": "f-mult"},
            {
                "id": "ia-base",
                "formula": "[Published Occupancy] * [Base Case Mult]",
                "name": "Base Case Occupancy",
                "format": PCT1,
            },
            {"id": "ia-entry", "type": "number", "name": "Your Occupancy", "format": PCT1},
            {
                "id": "ia-eff",
                "formula": "Coalesce([Your Occupancy], [Base Case Occupancy])",
                "name": "Effective Occupancy",
                "format": PCT1,
            },
            {
                "id": "ia-pnoi",
                "formula": (
                    "[Published NOI] * Coalesce([Your Occupancy], [Base Case Occupancy]) "
                    "/ NullIf([Published Occupancy], 0)"
                ),
                "name": "Projected NOI",
                "format": MONEY0,
            },
            {
                "id": "ia-dlt",
                "formula": "[Projected NOI] - [Published NOI]",
                "name": "NOI Δ vs published",
                "format": MONEY0,
            },
            {"id": "ia-note", "type": "text", "name": "IC comment"},
        ],
        "tableComponents": {"summaryBar": "hidden"},
    })
    add({
        "id": "book",
        "kind": "table",
        "name": "Book",
        "visibleAsSource": True,
        "source": {"elementId": "assum", "kind": "table"},
        "columns": [
            {"id": "bk-st", "formula": "[Assumptions/Strategy]", "name": "strategy"},
            {"id": "bk-pub", "formula": "[Assumptions/Published NOI]", "name": "published_noi"},
            {"id": "bk-proj", "formula": "[Assumptions/Projected NOI]", "name": "projected_noi"},
            {"id": "bk-occ", "formula": "[Assumptions/Effective Occupancy]", "name": "eff_occ"},
            {"id": "bk-base", "formula": "[Assumptions/Base Case Occupancy]", "name": "base_occ"},
        ],
    })
    add({
        "id": "hint3",
        "kind": "text",
        "body": (
            "**Stay in the spreadsheet.** Type **Your Occupancy** on any strategy. "
            "Effective occupancy falls back to Base Case so the page is alive on load. "
            "Projected NOI and the bars move with the cell. Production writeback uses "
            "warehouse permissions and the audit log — IM keeps the model, everyone else "
            "sees the same published number."
        ),
        "style": {"backgroundColor": CARD, "borderRadius": "round", },
        "verticalAlign": "middle",
    })
    add({
        "id": "k-proj",
        "kind": "kpi-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [{"id": "kv-proj", "formula": "Sum([Book/projected_noi])", "format": MONEY}],
        "value": {"columnId": "kv-proj", "color": WHITE, "fontSize": 28},
        "name": {"text": "Projected NOI", "color": WHITE, "fontSize": 14},
        "style": {"backgroundColor": NAVY, "borderRadius": "round"},
    })
    add({
        "id": "k-pub",
        "kind": "kpi-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [{"id": "kv-pub", "formula": "Sum([Book/published_noi])", "format": MONEY}],
        "value": {"columnId": "kv-pub", "color": WHITE, "fontSize": 28},
        "name": {"text": "Published NOI", "color": WHITE, "fontSize": 14},
        "style": {"backgroundColor": "#16385C", "borderRadius": "round"},
    })
    add({
        "id": "k-upl",
        "kind": "kpi-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [{
            "id": "kv-upl",
            "formula": "(Sum([Book/projected_noi]) - Sum([Book/published_noi])) / NullIf(Sum([Book/published_noi]), 0)",
            "format": PCT2,
        }],
        "value": {"columnId": "kv-upl", "color": WHITE, "fontSize": 28},
        "name": {"text": "Uplift vs published", "color": WHITE, "fontSize": 14},
        "style": {"backgroundColor": "#6B4F1D", "borderRadius": "round"},
    })
    add({
        "id": "ch-var",
        "kind": "bar-chart",
        "source": {"elementId": "book", "kind": "table"},
        "columns": [
            {"id": "v-x", "formula": "[Book/strategy]", "name": "Strategy"},
            {"id": "v-b", "formula": "Sum([Book/published_noi])", "name": "Published", "format": MONEY},
            {"id": "v-p", "formula": "Sum([Book/projected_noi])", "name": "Projected", "format": MONEY},
        ],
        "xAxis": {"columnId": "v-x"},
        "yAxis": {"columnIds": ["v-b", "v-p"]},
        "stacking": "none",
        "name": {"text": "Published vs projected NOI", "fontSize": 14},
        "legend": {"position": "top-left"},
        "style": {"backgroundColor": CARD, "borderColor": BORDER, "borderWidth": 1, "borderRadius": "round"},
    })

    layout = f'''<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo1" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="ttl1" gridColumn="6 / 16" gridRow="1 / 4"/>
    <Element elementId="sub1" gridColumn="6 / 16" gridRow="4 / 6"/>
    <Element elementId="nav1" gridColumn="16 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope1" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Element elementId="ctrl-mkt" gridColumn="1 / 9" gridRow="8 / 10"/>
  <Element elementId="ctrl-strat" gridColumn="9 / 17" gridRow="8 / 10"/>
  <Element elementId="ctrl-src" gridColumn="17 / 25" gridRow="8 / 10"/>
  <Container elementId="c-gav" type="grid" gridColumn="1 / 7" gridRow="10 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-gav" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-gav" gridColumn="7 / 13" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-occ" type="grid" gridColumn="7 / 13" gridRow="10 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-occ" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-occ" gridColumn="7 / 13" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-noi" type="grid" gridColumn="13 / 19" gridRow="10 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-noi" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-noi" gridColumn="7 / 13" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-desk" type="grid" gridColumn="19 / 25" gridRow="10 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-desk" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-desk" gridColumn="7 / 13" gridRow="1 / 8"/>
  </Container>
  <Element elementId="ch-occ" gridColumn="1 / 13" gridRow="18 / 32"/>
  <Element elementId="ch-gav" gridColumn="13 / 25" gridRow="18 / 32"/>
  <Element elementId="tbl-grid" gridColumn="1 / 16" gridRow="32 / 50"/>
  <Element elementId="tbl-chase" gridColumn="16 / 25" gridRow="32 / 46"/>
  <Element elementId="note1" gridColumn="16 / 25" gridRow="46 / 50"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg2">
  <Container elementId="c-hdr2" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo2" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="ttl2" gridColumn="6 / 16" gridRow="1 / 4"/>
    <Element elementId="sub2" gridColumn="6 / 16" gridRow="4 / 6"/>
    <Element elementId="nav2" gridColumn="16 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope2" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Element elementId="ctrl-prod" gridColumn="1 / 9" gridRow="8 / 10"/>
  <Element elementId="ctrl-stage" gridColumn="9 / 17" gridRow="8 / 10"/>
  <Element elementId="ctrl-camp" gridColumn="17 / 25" gridRow="8 / 10"/>
  <Container elementId="c-raised" type="grid" gridColumn="1 / 7" gridRow="10 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-raised" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-raised" gridColumn="7 / 13" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-pace" type="grid" gridColumn="7 / 13" gridRow="10 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-pace" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-pace" gridColumn="7 / 13" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-pipe" type="grid" gridColumn="13 / 19" gridRow="10 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-pipe" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-pipe" gridColumn="7 / 13" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-roas" type="grid" gridColumn="19 / 25" gridRow="10 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <Element elementId="kc-roas" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="kp-roas" gridColumn="7 / 13" gridRow="1 / 8"/>
  </Container>
  <Element elementId="ch-funnel" gridColumn="1 / 13" gridRow="18 / 34"/>
  <Element elementId="ch-camp" gridColumn="13 / 25" gridRow="18 / 34"/>
  <Element elementId="tbl-opps" gridColumn="1 / 18" gridRow="34 / 52"/>
  <Element elementId="note2" gridColumn="18 / 25" gridRow="34 / 52"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg3">
  <Container elementId="c-hdr3" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo3" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="ttl3" gridColumn="6 / 16" gridRow="1 / 4"/>
    <Element elementId="sub3" gridColumn="6 / 16" gridRow="4 / 6"/>
    <Element elementId="nav3" gridColumn="16 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope3" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Element elementId="hint3" gridColumn="1 / 25" gridRow="8 / 10"/>
  <Element elementId="k-proj" gridColumn="1 / 9" gridRow="10 / 16"/>
  <Element elementId="k-pub" gridColumn="9 / 17" gridRow="10 / 16"/>
  <Element elementId="k-upl" gridColumn="17 / 25" gridRow="10 / 16"/>
  <Element elementId="ch-var" gridColumn="1 / 25" gridRow="16 / 32"/>
  <Element elementId="assum" gridColumn="1 / 25" gridRow="32 / 46"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pgData">
  <Element elementId="tbl-asset" gridColumn="1 / 13" gridRow="1 / 16"/>
  <Element elementId="tbl-reg" gridColumn="13 / 25" gridRow="1 / 16"/>
  <Element elementId="tbl-sales" gridColumn="1 / 13" gridRow="16 / 32"/>
  <Element elementId="tbl-fcst" gridColumn="13 / 25" gridRow="16 / 24"/>
  <Element elementId="book" gridColumn="13 / 25" gridRow="24 / 32"/>
  <Element elementId="ctrl-cur" gridColumn="13 / 25" gridRow="32 / 36"/>
</Page>
'''

    return {
        "name": "Origin Investments — Model of Record",
        "folderId": FOLDER,
        "document": {
            "schemaVersion": 1,
            "kind": "workbook",
            "elements": elements,
            "pages": [
                {"id": "pg1", "name": "Model of Record"},
                {"id": "pg2", "name": "Sales & Marketing"},
                {"id": "pg3", "name": "Quarter-end Writeback"},
                {"id": "pgData", "name": "Data", "visibility": "hidden"},
            ],
            "layout": layout,
            "settings": {
                "navigation": {"pageHeader": "enabled"},
                "theme": {"overrides": {
                    "colors": {
                        "text": TEXT,
                        "highlight": GOLD,
                        "success": "#2E9E7E",
                        "warning": GOLD,
                        "danger": "#B42318",
                        "darkMode": "hidden",
                    },
                    "backgroundColor": CANVAS,
                    "elementBackgroundColor": CARD,
                    "borderColor": BORDER,
                    "borderRadius": "round",
                    "space": {"unit": "small", "showElementPadding": "shown"},
                    "fonts": {"dataFont": "Inter", "textFont": "Inter"},
                }},
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=pathlib.Path, default=pathlib.Path("/workspace/.env"))
    parser.add_argument("action", choices=["verify", "create", "update"])
    parser.add_argument("workbook_id", nargs="?")
    parser.add_argument("--expected-version", type=int)
    args = parser.parse_args()

    spec = build_spec()
    api = SigmaApi(read_env(args.env_file))
    if args.action == "verify":
        result = api.call("POST", "/v2/workbooks/spec/verify", spec)
        print(json.dumps(result, indent=2)[:4000])
        return
    if args.action == "create":
        result = api.call("POST", "/v2/workbooks/spec", spec)
        print(json.dumps(result, indent=2)[:4000])
        (HERE / "workbook_id.txt").write_text(result["workbookId"] + "\n")
        return
    if not args.workbook_id:
        raise SystemExit("update requires workbook_id")
    meta = api.call("GET", f"/v2/workbooks/{args.workbook_id}")
    if args.expected_version is not None and meta["latestVersion"] != args.expected_version:
        raise RuntimeError(
            f"Live version is {meta['latestVersion']}, expected {args.expected_version}"
        )
    result = api.call("PUT", f"/v2/workbooks/{args.workbook_id}/spec", spec)
    print(json.dumps(result, indent=2)[:2000])
    updated = api.call("GET", f"/v2/workbooks/{args.workbook_id}")
    print("latestVersion", updated.get("latestVersion"), "urlId", updated.get("urlId"))


if __name__ == "__main__":
    main()
