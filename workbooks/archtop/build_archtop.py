#!/usr/bin/env python3
"""Build the Archtop Fiber FP&A + growth + FCC Sigma workbook.

Synthetic Snowflake data shaped like Archtop's planned Snowflake model.
The workbook does not claim to use production billing, GIS, or FCC records.
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
CONNECTION_ID = "a9d45cfe-ff65-4515-8193-a7072602a1ee"
FOLDER_ID = "a758d7ee-8c23-423d-9d60-5b635d9e9b58"
LOGO_URL = "https://archtopfiber.com/wp-content/uploads/archtop-fiber-reg-logo2x.png"

NAVY = "#285B73"
NAVY_DARK = "#173B50"
CORAL = "#FF5A49"
CORAL_DARK = "#D83E35"
SKY = "#DCEEF4"
CANVAS = "#F5F8FA"
CARD = "#FFFFFF"
BORDER = "#D8E2E8"
TEXT = "#183747"
WHITE = "#FFFFFF"
GOOD = "#16836B"
WARN = "#C27B16"
BAD = "#C13F36"

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
DATE_MON = {"kind": "datetime", "formatString": "%b %Y"}

SCOPE = (
    "Illustrative proof of value using deterministic Snowflake-generated records "
    "shaped like Archtop billing, GIS, CRM and finance data. It is not production "
    "revenue, customer, service-location or FCC filing data. Production controls "
    "would inherit Snowflake permissions and governed source mappings."
)

FINANCE_SQL = r"""
WITH months AS (
  SELECT SEQ4() AS month_n
  FROM TABLE(GENERATOR(ROWCOUNT => 18))
),
markets AS (
  SELECT column1::STRING AS market, column2::STRING AS state,
         column3::STRING AS legacy_company, column4::STRING AS source_system,
         column5::NUMBER AS market_order
  FROM VALUES
    ('Kingston', 'NY', 'Archtop Fiber', 'MBS Postgres dump', 1),
    ('Saugerties', 'NY', 'Archtop Fiber', 'MBS Postgres dump', 2),
    ('Rhinebeck', 'NY', 'Archtop Fiber', 'MBS Postgres dump', 3),
    ('Hudson', 'NY', 'Archtop Fiber', 'MBS Postgres dump', 4),
    ('Warwick', 'NY', 'Warwick Valley Telephone', 'Legacy CSV', 5),
    ('Hancock', 'NY', 'Hancock Telephone', 'Legacy CSV', 6),
    ('Stroudsburg', 'PA', 'Archtop Fiber', 'MBS Postgres dump', 7),
    ('Pittsfield', 'MA', 'Archtop Fiber', 'MBS Postgres dump', 8)
),
plans AS (
  SELECT column1::STRING AS plan, column2::NUMBER AS monthly_price,
         column3::FLOAT AS mix, column4::NUMBER AS plan_order
  FROM VALUES
    ('500 Mbps', 39.99, 0.42, 1),
    ('1 Gig', 49.99, 0.39, 2),
    ('2 Gig', 69.99, 0.19, 3)
),
base AS (
  SELECT
    DATEADD('month', month_n - 17, DATE_TRUNC('month', CURRENT_DATE())) AS period,
    m.market, m.state, m.legacy_company, m.source_system, m.market_order,
    p.plan, p.monthly_price, p.plan_order,
    ROUND((2060 + m.market_order * 230 + month_n * (36 + m.market_order * 2))
          * p.mix, 0) AS subscribers,
    ROUND((42 + m.market_order * 3 + month_n * 1.6) * p.mix, 0) AS gross_adds,
    ROUND((21 + m.market_order * 1.2 + month_n * 0.45) * p.mix, 0) AS churned,
    5600 + m.market_order * 740 + month_n * 115 AS serviceable_locations,
    6200 + m.market_order * 790 + month_n * 132 AS raw_passings,
    190 + m.market_order * 14 + MOD(month_n * 17 + m.market_order * 9, 85)
      AS campaign_leads,
    8400 + m.market_order * 610 + month_n * 180 AS campaign_spend,
    p.monthly_price
      * ROUND((2060 + m.market_order * 230 + month_n * (36 + m.market_order * 2))
              * p.mix, 0) AS billed_revenue,
    IFF(
      m.source_system = 'Legacy CSV',
      (MOD(month_n + m.market_order + p.plan_order, 5) - 2) * 487,
      (MOD(month_n + m.market_order + p.plan_order, 7) - 3) * 119
    ) AS reconciliation_delta,
    11 + MOD(m.market_order * 7 + month_n * 3, 35) AS duplicate_records,
    IFF(m.source_system = 'Legacy CSV', 0.87, 0.965)
      - MOD(month_n + m.market_order, 4) / 1000.0 AS address_completeness
  FROM months
  CROSS JOIN markets m
  CROSS JOIN plans p
)
SELECT
  period, market, state, legacy_company, source_system, plan, monthly_price,
  subscribers, gross_adds, churned, gross_adds - churned AS net_adds,
  serviceable_locations, raw_passings, campaign_leads, campaign_spend,
  billed_revenue,
  billed_revenue + reconciliation_delta AS gl_revenue,
  reconciliation_delta,
  billed_revenue * 0.29 AS network_and_support_cost,
  billed_revenue * 0.018 AS regulatory_fees,
  duplicate_records,
  address_completeness,
  subscribers * monthly_price / NULLIF(subscribers, 0) AS arpu,
  subscribers / NULLIF(serviceable_locations, 0) AS penetration,
  IFF(period = DATE_TRUNC('month', CURRENT_DATE()), 1, 0) AS is_current,
  IFF(period = DATEADD('month', -1, DATE_TRUNC('month', CURRENT_DATE())), 1, 0)
    AS is_prior
FROM base
""".strip()

GROWTH_SQL = r"""
SELECT * FROM (
  VALUES
    ('Kingston', 'NY', 'Fiber Ready', 19840, 8620, 0.434, 52.40, 0.958, 42000,
     0.036, 54.00, 188, 96, 'Spectrum', 'Friends & neighbors'),
    ('Saugerties', 'NY', 'Fiber Ready', 12610, 4870, 0.386, 50.90, 0.931, 31000,
     0.041, 53.00, 102, 91, 'Spectrum', 'Win-back: reliability'),
    ('Rhinebeck', 'NY', 'Fiber Ready', 8850, 4010, 0.453, 56.10, 0.972, 22000,
     0.032, 57.00, 74, 97, 'Cable + fixed wireless', 'Neighbor referral'),
    ('Hudson', 'NY', 'Final stages', 14820, 2640, 0.178, 48.80, 0.914, 46000,
     0.052, 52.00, 165, 84, 'Spectrum', 'Pre-order launch'),
    ('Warwick', 'NY', 'Fiber Ready', 16440, 7160, 0.435, 51.70, 0.883, 38000,
     0.044, 54.00, 126, 79, 'Cable', 'Legacy-base upsell'),
    ('Hancock', 'NY', 'Under construction', 7120, 1040, 0.146, 47.50, 0.861, 19000,
     0.055, 51.00, 61, 76, 'DSL + fixed wireless', 'Build awareness'),
    ('Stroudsburg', 'PA', 'Construction starting', 23600, 1180, 0.050, 49.20, 0.906,
     52000, 0.061, 53.00, 214, 88, 'Cable', 'Pre-register households'),
    ('Pittsfield', 'MA', 'Construction starting', 21180, 920, 0.043, 49.70, 0.919,
     48000, 0.058, 53.50, 177, 90, 'Cable + fiber', 'Underserved block outreach')
) AS t(
  market, state, build_phase, serviceable_locations, subscribers, penetration,
  current_arpu, address_quality, recommended_budget, base_take_rate,
  target_arpu, recent_home_sales, propensity_score, primary_competitor,
  recommended_campaign
)
""".strip()

BUDGET_SQL = r"""
SELECT * FROM (
  VALUES
    ('Kingston', 'NY', 8620, 52.40, 3340000, 820000, 410, 53.50, 3400000, 880000),
    ('Saugerties', 'NY', 4870, 50.90, 1840000, 510000, 285, 52.00, 1880000, 535000),
    ('Rhinebeck', 'NY', 4010, 56.10, 1720000, 430000, 190, 56.80, 1750000, 445000),
    ('Hudson', 'NY', 2640, 48.80, 1080000, 760000, 460, 51.50, 1180000, 790000),
    ('Warwick', 'NY', 7160, 51.70, 2820000, 690000, 330, 53.20, 2890000, 715000),
    ('Hancock', 'NY', 1040, 47.50, 520000, 580000, 260, 50.50, 610000, 610000),
    ('Stroudsburg', 'PA', 1180, 49.20, 610000, 1210000, 620, 52.50, 790000, 1280000),
    ('Pittsfield', 'MA', 920, 49.70, 490000, 1080000, 560, 53.00, 650000, 1140000)
) AS t(
  market, state, subscribers, current_arpu, current_opex, current_capex,
  base_case_net_adds, base_case_arpu, base_case_opex, base_case_capex
)
""".strip()

FCC_SQL = r"""
WITH counties AS (
  SELECT column1::STRING AS state, column2::STRING AS county,
         column3::STRING AS market, column4::NUMBER AS served_seed,
         column5::NUMBER AS order_n
  FROM VALUES
    ('NY', 'Ulster', 'Kingston', 7840, 1),
    ('NY', 'Ulster', 'Saugerties', 4260, 2),
    ('NY', 'Dutchess', 'Rhinebeck', 3610, 3),
    ('NY', 'Columbia', 'Hudson', 2380, 4),
    ('NY', 'Orange', 'Warwick', 6320, 5),
    ('NY', 'Delaware', 'Hancock', 890, 6),
    ('PA', 'Monroe', 'Stroudsburg', 740, 7),
    ('MA', 'Berkshire', 'Pittsfield', 610, 8)
),
tech AS (
  SELECT column1::STRING AS technology, column2::NUMBER AS down_mbps,
         column3::NUMBER AS up_mbps, column4::FLOAT AS share
  FROM VALUES
    ('Fiber to the Premises', 500, 500, 0.42),
    ('Fiber to the Premises', 1000, 1000, 0.39),
    ('Fiber to the Premises', 2000, 2000, 0.19)
)
SELECT
  'BDC 2026 H1' AS filing_period,
  c.state, c.county, c.market, t.technology, t.down_mbps, t.up_mbps,
  ROUND(c.served_seed * t.share, 0) AS served_locations,
  ROUND((c.served_seed * 1.08) * t.share, 0) AS fabric_locations,
  ROUND(c.served_seed * t.share
        * (0.986 - IFF(c.order_n IN (5, 6), 0.045, 0)), 0) AS valid_bsl_ids,
  ROUND(c.served_seed * t.share
        * IFF(c.order_n IN (5, 6), 0.054, 0.012), 0) AS address_exceptions,
  ROUND(c.served_seed * t.share
        * IFF(c.order_n IN (6, 7, 8), 0.027, 0.006), 0) AS technology_mismatches,
  IFF(c.order_n IN (5, 6), 'Legacy CSV', 'MBS + Vetro GIS') AS source_mapping,
  IFF(c.order_n IN (5, 6), 'Needs review', 'Ready') AS review_status,
  IFF(c.order_n IN (5, 6), 42000 + c.order_n * 6500, 0)
    AS illustrative_support_at_risk
FROM counties c
CROSS JOIN tech t
""".strip()


elements: list[dict] = []


def add(element: dict) -> dict:
    elements.append(element)
    return element


def panel(background: str = CARD) -> dict:
    return {
        "backgroundColor": background,
        "borderColor": BORDER,
        "borderWidth": 1,
        "borderRadius": "round",
    }


def sql_table(eid: str, name: str, sql: str, columns: list[dict]) -> None:
    add({
        "id": eid,
        "kind": "table",
        "name": name,
        "source": {
            "kind": "sql",
            "connectionId": CONNECTION_ID,
            "statement": sql,
        },
        "columns": columns,
    })


def nav(eid: str) -> None:
    add({
        "id": eid,
        "kind": "navigation",
        "mode": "manual",
        "showIcons": False,
        "optionStyle": {
            "textColor": NAVY,
            "selectedColor": CORAL,
            "style": "pill",
            "orientation": "horizontal",
        },
        "options": [
            {"label": "FP&A",
             "destination": {"type": "page", "pageId": "pg-finance"}},
            {"label": "Budget App",
             "destination": {"type": "page", "pageId": "pg-budget"}},
            {"label": "Growth",
             "destination": {"type": "page", "pageId": "pg-growth"}},
            {"label": "FCC",
             "destination": {"type": "page", "pageId": "pg-fcc"}},
        ],
    })


def header(idx: int, title: str, subtitle: str) -> None:
    add({
        "id": f"hdr-{idx}",
        "kind": "container",
        "style": {
            "backgroundColor": WHITE,
            "borderColor": CORAL,
            "borderWidth": 3,
            "borderRadius": "round",
        },
    })
    add({
        "id": f"logo-{idx}",
        "kind": "image",
        "source": {"kind": "url", "url": LOGO_URL},
        "style": {"fit": "contain", "align": "start"},
    })
    add({
        "id": f"title-{idx}",
        "kind": "text",
        "body": f"# **{title}**",
        "verticalAlign": "center",
    })
    add({
        "id": f"subtitle-{idx}",
        "kind": "text",
        "body": subtitle,
        "verticalAlign": "center",
    })
    nav(f"nav-{idx}")


def kpi(
    eid: str,
    source: str,
    label: str,
    current: str,
    prior: str,
    fmt: dict,
    background: str = NAVY,
    good: str = "#C7F0DD",
    bad: str = "#FFD0CB",
    comparison_label: str = "Prior month",
) -> None:
    add({
        "id": eid,
        "kind": "kpi-chart",
        "source": {"kind": "table", "elementId": source},
        "columns": [
            {"id": f"{eid}-current", "name": label, "formula": current, "format": fmt},
            {"id": f"{eid}-prior", "name": comparison_label,
             "formula": prior, "format": fmt},
        ],
        "value": {"columnId": f"{eid}-current", "color": WHITE, "fontSize": 28},
        "comparisonColumn": {"columnId": f"{eid}-prior"},
        "comparison": {
            "display": "delta",
            "colorGood": good,
            "colorBad": bad,
            "fontSize": 13,
        },
        "name": {"text": label, "color": WHITE, "fontSize": 13},
        "style": {"backgroundColor": background, "borderRadius": "round"},
    })


def list_control(
    eid: str,
    control_id: str,
    label: str,
    table: str,
    column: str,
    extra_filters: tuple[tuple[str, str], ...] = (),
) -> None:
    filters = [
        {"source": {"kind": "table", "elementId": table}, "columnId": column}
    ]
    filters.extend(
        {"source": {"kind": "table", "elementId": target}, "columnId": col}
        for target, col in extra_filters
    )
    add({
        "id": eid,
        "kind": "control",
        "controlId": control_id,
        "name": label,
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [],
        "filters": filters,
        "source": {
            "kind": "source",
            "source": {"kind": "table", "elementId": table},
            "columnId": column,
        },
    })


def build_spec() -> dict:
    elements.clear()

    sql_table("tbl-fin", "Finance Ledger", FINANCE_SQL, [
        {"id": "fin-period", "name": "Period",
         "formula": "[Custom SQL/period]", "format": DATE_MON},
        {"id": "fin-market", "name": "Market", "formula": "[Custom SQL/market]"},
        {"id": "fin-state", "name": "State", "formula": "[Custom SQL/state]"},
        {"id": "fin-legacy", "name": "Legacy Company",
         "formula": "[Custom SQL/legacy_company]"},
        {"id": "fin-source", "name": "Source System",
         "formula": "[Custom SQL/source_system]"},
        {"id": "fin-plan", "name": "Plan", "formula": "[Custom SQL/plan]"},
        {"id": "fin-price", "name": "Monthly Price",
         "formula": "[Custom SQL/monthly_price]", "format": MONEY0},
        {"id": "fin-subs", "name": "Subscribers",
         "formula": "[Custom SQL/subscribers]", "format": NUM0},
        {"id": "fin-adds", "name": "Gross Adds",
         "formula": "[Custom SQL/gross_adds]", "format": NUM0},
        {"id": "fin-churn", "name": "Churned",
         "formula": "[Custom SQL/churned]", "format": NUM0},
        {"id": "fin-net", "name": "Net Adds",
         "formula": "[Custom SQL/net_adds]", "format": NUM0},
        {"id": "fin-serviceable", "name": "Serviceable Locations",
         "formula": "[Custom SQL/serviceable_locations]", "format": NUM0},
        {"id": "fin-passings", "name": "Raw Passings",
         "formula": "[Custom SQL/raw_passings]", "format": NUM0},
        {"id": "fin-leads", "name": "Campaign Leads",
         "formula": "[Custom SQL/campaign_leads]", "format": NUM0},
        {"id": "fin-spend", "name": "Campaign Spend",
         "formula": "[Custom SQL/campaign_spend]", "format": MONEY0},
        {"id": "fin-billed", "name": "Billing Revenue",
         "formula": "[Custom SQL/billed_revenue]", "format": MONEY0},
        {"id": "fin-gl", "name": "GL Revenue",
         "formula": "[Custom SQL/gl_revenue]", "format": MONEY0},
        {"id": "fin-delta", "name": "Reconciliation Delta",
         "formula": "[Custom SQL/reconciliation_delta]", "format": MONEY0},
        {"id": "fin-cost", "name": "Network & Support Cost",
         "formula": "[Custom SQL/network_and_support_cost]", "format": MONEY0},
        {"id": "fin-fee", "name": "Regulatory Fees",
         "formula": "[Custom SQL/regulatory_fees]", "format": MONEY0},
        {"id": "fin-dupes", "name": "Duplicate Records",
         "formula": "[Custom SQL/duplicate_records]", "format": NUM0},
        {"id": "fin-address", "name": "Address Completeness",
         "formula": "[Custom SQL/address_completeness]", "format": PCT1},
        {"id": "fin-arpu", "name": "ARPU",
         "formula": "[Custom SQL/arpu]", "format": MONEY0},
        {"id": "fin-penetration", "name": "Penetration",
         "formula": "[Custom SQL/penetration]", "format": PCT1},
        {"id": "fin-current", "name": "Is Current",
         "formula": "[Custom SQL/is_current]"},
        {"id": "fin-prior", "name": "Is Prior",
         "formula": "[Custom SQL/is_prior]"},
    ])

    sql_table("tbl-growth", "Market Opportunity", GROWTH_SQL, [
        {"id": "gr-market", "name": "Market", "formula": "[Custom SQL/market]"},
        {"id": "gr-state", "name": "State", "formula": "[Custom SQL/state]"},
        {"id": "gr-phase", "name": "Build Phase", "formula": "[Custom SQL/build_phase]"},
        {"id": "gr-locs", "name": "Serviceable Locations",
         "formula": "[Custom SQL/serviceable_locations]", "format": NUM0},
        {"id": "gr-subs", "name": "Subscribers",
         "formula": "[Custom SQL/subscribers]", "format": NUM0},
        {"id": "gr-pen", "name": "Penetration",
         "formula": "[Custom SQL/penetration]", "format": PCT1},
        {"id": "gr-arpu", "name": "Current ARPU",
         "formula": "[Custom SQL/current_arpu]", "format": MONEY0},
        {"id": "gr-quality", "name": "Address Quality",
         "formula": "[Custom SQL/address_quality]", "format": PCT1},
        {"id": "gr-budget", "name": "Recommended Budget",
         "formula": "[Custom SQL/recommended_budget]", "format": MONEY0},
        {"id": "gr-take", "name": "Base Take Rate",
         "formula": "[Custom SQL/base_take_rate]", "format": PCT1},
        {"id": "gr-target-arpu", "name": "Target ARPU",
         "formula": "[Custom SQL/target_arpu]", "format": MONEY0},
        {"id": "gr-sales", "name": "Recent Home Sales",
         "formula": "[Custom SQL/recent_home_sales]", "format": NUM0},
        {"id": "gr-score", "name": "Propensity Score",
         "formula": "[Custom SQL/propensity_score]", "format": NUM0},
        {"id": "gr-competitor", "name": "Primary Competitor",
         "formula": "[Custom SQL/primary_competitor]"},
        {"id": "gr-campaign", "name": "Recommended Campaign",
         "formula": "[Custom SQL/recommended_campaign]"},
    ])

    sql_table("tbl-budget", "Budget Baseline", BUDGET_SQL, [
        {"id": "bd-market", "name": "Market", "formula": "[Custom SQL/market]"},
        {"id": "bd-state", "name": "State", "formula": "[Custom SQL/state]"},
        {"id": "bd-subs", "name": "Subscribers",
         "formula": "[Custom SQL/subscribers]", "format": NUM0},
        {"id": "bd-arpu", "name": "Current ARPU",
         "formula": "[Custom SQL/current_arpu]", "format": MONEY0},
        {"id": "bd-opex", "name": "Current Opex",
         "formula": "[Custom SQL/current_opex]", "format": MONEY0},
        {"id": "bd-capex", "name": "Current Capex",
         "formula": "[Custom SQL/current_capex]", "format": MONEY0},
        {"id": "bd-base-adds", "name": "Base Case Net Adds",
         "formula": "[Custom SQL/base_case_net_adds]", "format": NUM0},
        {"id": "bd-base-arpu", "name": "Base Case ARPU",
         "formula": "[Custom SQL/base_case_arpu]", "format": MONEY0},
        {"id": "bd-base-opex", "name": "Base Case Opex",
         "formula": "[Custom SQL/base_case_opex]", "format": MONEY0},
        {"id": "bd-base-capex", "name": "Base Case Capex",
         "formula": "[Custom SQL/base_case_capex]", "format": MONEY0},
    ])

    sql_table("tbl-fcc", "FCC Source", FCC_SQL, [
        {"id": "fc-period", "name": "Filing Period",
         "formula": "[Custom SQL/filing_period]"},
        {"id": "fc-state", "name": "State", "formula": "[Custom SQL/state]"},
        {"id": "fc-county", "name": "County", "formula": "[Custom SQL/county]"},
        {"id": "fc-market", "name": "Market", "formula": "[Custom SQL/market]"},
        {"id": "fc-tech", "name": "Technology",
         "formula": "[Custom SQL/technology]"},
        {"id": "fc-down", "name": "Max Download Mbps",
         "formula": "[Custom SQL/down_mbps]", "format": NUM0},
        {"id": "fc-up", "name": "Max Upload Mbps",
         "formula": "[Custom SQL/up_mbps]", "format": NUM0},
        {"id": "fc-served", "name": "Served Locations",
         "formula": "[Custom SQL/served_locations]", "format": NUM0},
        {"id": "fc-fabric", "name": "Fabric Locations",
         "formula": "[Custom SQL/fabric_locations]", "format": NUM0},
        {"id": "fc-valid", "name": "Valid BSL IDs",
         "formula": "[Custom SQL/valid_bsl_ids]", "format": NUM0},
        {"id": "fc-address", "name": "Address Exceptions",
         "formula": "[Custom SQL/address_exceptions]", "format": NUM0},
        {"id": "fc-mismatch", "name": "Technology Mismatches",
         "formula": "[Custom SQL/technology_mismatches]", "format": NUM0},
        {"id": "fc-source", "name": "Source Mapping",
         "formula": "[Custom SQL/source_mapping]"},
        {"id": "fc-status", "name": "Review Status",
         "formula": "[Custom SQL/review_status]"},
        {"id": "fc-risk", "name": "Illustrative Support at Risk",
         "formula": "[Custom SQL/illustrative_support_at_risk]", "format": MONEY0},
    ])

    # Page 1 — FP&A reconciliation control room.
    header(1, "FP&A Control Room",
           "Billing → Snowflake → general ledger, reconciled at subscriber and plan grain")
    add({
        "id": "scope-fin",
        "kind": "text",
        "body": SCOPE,
        "style": {"backgroundColor": SKY, "borderRadius": "round"},
    })
    list_control("ctrl-fin-market", "FinMarket", "Market",
                 "tbl-fin", "fin-market")
    list_control("ctrl-fin-source", "FinSource", "Source system",
                 "tbl-fin", "fin-source")
    list_control("ctrl-fin-plan", "FinPlan", "Plan",
                 "tbl-fin", "fin-plan")

    fin = "Finance Ledger"
    current = f"[{fin}/Is Current] = 1"
    prior = f"[{fin}/Is Prior] = 1"
    kpi(
        "kpi-mrr", "tbl-fin", "Monthly recurring revenue",
        f"Sum(If({current}, [{fin}/Billing Revenue], 0))",
        f"Sum(If({prior}, [{fin}/Billing Revenue], 0))",
        MONEY, NAVY_DARK,
    )
    kpi(
        "kpi-arpu", "tbl-fin", "Subscriber ARPU",
        f"Sum(If({current}, [{fin}/Billing Revenue], 0)) / "
        f"NullIf(Sum(If({current}, [{fin}/Subscribers], 0)), 0)",
        f"Sum(If({prior}, [{fin}/Billing Revenue], 0)) / "
        f"NullIf(Sum(If({prior}, [{fin}/Subscribers], 0)), 0)",
        MONEY0, NAVY,
    )
    kpi(
        "kpi-subs", "tbl-fin", "Subscribers",
        f"Sum(If({current}, [{fin}/Subscribers], 0))",
        f"Sum(If({prior}, [{fin}/Subscribers], 0))",
        NUM0, CORAL_DARK,
    )
    kpi(
        "kpi-recon", "tbl-fin", "Unreconciled billing ↔ GL",
        f"Abs(Sum(If({current}, [{fin}/Reconciliation Delta], 0)))",
        f"Abs(Sum(If({prior}, [{fin}/Reconciliation Delta], 0)))",
        MONEY0, BAD, good="#FFD0CB", bad="#C7F0DD",
    )
    add({
        "id": "ch-revenue",
        "kind": "line-chart",
        "name": "Revenue trend — billing vs general ledger",
        "source": {"kind": "table", "elementId": "tbl-fin"},
        "columns": [
            {"id": "rev-month", "name": "Month",
             "formula": f"DateTrunc(\"month\", [{fin}/Period])", "format": DATE_MON},
            {"id": "rev-bill", "name": "Billing",
             "formula": f"Sum([{fin}/Billing Revenue])", "format": MONEY},
            {"id": "rev-gl", "name": "General ledger",
             "formula": f"Sum([{fin}/GL Revenue])", "format": MONEY},
        ],
        "xAxis": {"columnId": "rev-month"},
        "yAxis": {"columnIds": ["rev-bill", "rev-gl"]},
        "stacking": "none",
        "legend": {"position": "top"},
        "style": panel(),
    })
    add({
        "id": "ch-plan",
        "kind": "bar-chart",
        "name": "Current MRR and subscriber mix by package",
        "source": {"kind": "table", "elementId": "tbl-fin"},
        "columns": [
            {"id": "plan-name", "name": "Plan",
             "formula": f"[{fin}/Plan]"},
            {"id": "plan-mrr", "name": "MRR",
             "formula": f"Sum(If({current}, [{fin}/Billing Revenue], 0))",
             "format": MONEY},
            {"id": "plan-subs", "name": "Subscribers",
             "formula": f"Sum(If({current}, [{fin}/Subscribers], 0))",
             "format": NUM0},
        ],
        "xAxis": {"columnId": "plan-name"},
        "yAxis": {"columnIds": ["plan-mrr"]},
        "legend": {"visibility": "hidden"},
        "style": panel(),
    })
    add({
        "id": "tbl-recon",
        "kind": "table",
        "name": "Reconciliation workbench — drill to market, source and plan",
        "source": {"kind": "table", "elementId": "tbl-fin"},
        "columns": [
            {"id": "rc-source", "name": "Source System",
             "formula": f"[{fin}/Source System]"},
            {"id": "rc-market", "name": "Market",
             "formula": f"[{fin}/Market]"},
            {"id": "rc-plan", "name": "Plan",
             "formula": f"[{fin}/Plan]"},
            {"id": "rc-bill", "name": "Billing Revenue",
             "formula": f"Sum(If({current}, [{fin}/Billing Revenue], 0))",
             "format": MONEY0},
            {"id": "rc-gl", "name": "GL Revenue",
             "formula": f"Sum(If({current}, [{fin}/GL Revenue], 0))",
             "format": MONEY0},
            {"id": "rc-var", "name": "Variance",
             "formula": "[GL Revenue] - [Billing Revenue]", "format": MONEY0},
            {"id": "rc-dupes", "name": "Duplicate Rows",
             "formula": f"Sum(If({current}, [{fin}/Duplicate Records], 0))",
             "format": NUM0},
            {"id": "rc-quality", "name": "Address Completeness",
             "formula": f"Avg(If({current}, [{fin}/Address Completeness], Null))",
             "format": PCT1},
        ],
        "groupings": [{
            "id": "rc-group",
            "groupBy": ["rc-source", "rc-market", "rc-plan"],
            "calculations": [
                "rc-bill", "rc-gl", "rc-var", "rc-dupes", "rc-quality"
            ],
        }],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {
            "preset": "presentation",
            "cellSpacing": "small",
            "gridLines": "horizontal",
        },
        "style": panel(),
    })
    add({
        "id": "fin-note",
        "kind": "text",
        "body": (
            "**Demo move:** filter Source system to **Legacy CSV**. The workbook "
            "preserves billing, GL and address-quality lineage together, so FP&A "
            "can explain the variance without a Python script or another emailed CSV."
        ),
        "style": panel("#FFF3F1"),
    })

    # Page 2 — FP&A budget and approval application.
    header(4, "FY27 Budget & Forecast Application",
           "Edit market assumptions, see EBITDA and cash impact, then submit or approve")
    add({
        "id": "scope-budget",
        "kind": "text",
        "body": (
            SCOPE + " Editable assumptions are stored in a warehouse-backed input "
            "table. Submit and Approve append workflow events with user "
            "and timestamp context."
        ),
        "style": {"backgroundColor": SKY, "borderRadius": "round"},
    })
    add({
        "id": "ctrl-plan-name",
        "kind": "control",
        "controlId": "PlanName",
        "name": "Plan name",
        "controlType": "text",
        "mode": "equals",
        "case": "insensitive",
        "value": "FY27 Board Plan",
        "includeNulls": "when-no-value-is-selected",
        "showOperators": False,
    })
    add({
        "id": "ctrl-plan-comment",
        "kind": "control",
        "controlId": "PlanComment",
        "name": "Submission comment",
        "controlType": "text",
        "mode": "equals",
        "case": "insensitive",
        "value": "",
        "includeNulls": "when-no-value-is-selected",
        "showOperators": False,
    })
    add({
        "id": "it-budget",
        "kind": "input-table",
        "name": "FY27 Market Budget",
        "source": {"kind": "linked", "from": "tbl-budget"},
        "inputMode": "view",
        "columns": [
            {"id": "ib-market", "key": "bd-market"},
            {"id": "ib-state", "key": "bd-state"},
            {"id": "ib-adds-entry", "name": "Your Net Adds", "type": "number",
             "format": NUM0},
            {"id": "ib-arpu-entry", "name": "Your ARPU", "type": "number",
             "format": MONEY0},
            {"id": "ib-opex-entry", "name": "Your Opex", "type": "number",
             "format": MONEY0},
            {"id": "ib-capex-entry", "name": "Your Capex", "type": "number",
             "format": MONEY0},
            {"id": "ib-comment", "name": "Finance Comment", "type": "text"},
            {"id": "ib-subs", "key": "bd-subs", "hidden": True},
            {"id": "ib-current-arpu", "key": "bd-arpu", "hidden": True},
            {"id": "ib-current-opex", "key": "bd-opex", "hidden": True},
            {"id": "ib-current-capex", "key": "bd-capex", "hidden": True},
            {"id": "ib-base-adds", "key": "bd-base-adds", "hidden": True},
            {"id": "ib-base-arpu", "key": "bd-base-arpu", "hidden": True},
            {"id": "ib-base-opex", "key": "bd-base-opex", "hidden": True},
            {"id": "ib-base-capex", "key": "bd-base-capex", "hidden": True},
            {"id": "ib-current-arr", "name": "Current ARR",
             "formula": "[Subscribers] * [Current ARPU] * 12",
             "format": MONEY0},
            {"id": "ib-current-ebitda", "name": "Current EBITDA",
             "formula": "[Current ARR] - [Current Opex]",
             "format": MONEY0},
            {"id": "ib-effective-adds", "name": "Effective Net Adds",
             "formula": "Coalesce([Your Net Adds], [Base Case Net Adds])",
             "format": NUM0},
            {"id": "ib-effective-arpu", "name": "Effective ARPU",
             "formula": "Coalesce([Your ARPU], [Base Case ARPU])",
             "format": MONEY0},
            {"id": "ib-effective-opex", "name": "Effective Opex",
             "formula": "Coalesce([Your Opex], [Base Case Opex])",
             "format": MONEY0},
            {"id": "ib-effective-capex", "name": "Effective Capex",
             "formula": "Coalesce([Your Capex], [Base Case Capex])",
             "format": MONEY0},
            {"id": "ib-projected-arr", "name": "Projected ARR",
             "formula": (
                 "[Current ARR] + [Effective Net Adds] * [Effective ARPU] * 12"
             ), "format": MONEY0},
            {"id": "ib-projected-ebitda", "name": "Projected EBITDA",
             "formula": "[Projected ARR] - [Effective Opex]",
             "format": MONEY0},
            {"id": "ib-ebitda-margin", "name": "EBITDA Margin",
             "formula": "[Projected EBITDA] / NullIf([Projected ARR], 0)",
             "format": PCT1},
            {"id": "ib-free-cash", "name": "Free Cash Flow",
             "formula": "[Projected EBITDA] - [Effective Capex]",
             "format": MONEY0},
            {"id": "ib-ebitda-delta", "name": "EBITDA Δ vs current",
             "formula": "[Projected EBITDA] - [Current EBITDA]",
             "format": MONEY0},
            {"id": "ib-capex-delta", "name": "Capex Δ vs current",
             "formula": "[Effective Capex] - [Current Capex]",
             "format": MONEY0},
        ],
        "order": [
            "ib-market", "ib-state", "ib-adds-entry", "ib-arpu-entry",
            "ib-opex-entry", "ib-capex-entry", "ib-comment",
            "ib-base-adds", "ib-base-arpu", "ib-base-opex", "ib-base-capex",
            "ib-subs", "ib-current-arpu", "ib-current-opex",
            "ib-current-capex", "ib-current-arr", "ib-current-ebitda",
            "ib-effective-adds", "ib-effective-arpu", "ib-effective-opex",
            "ib-effective-capex", "ib-projected-arr", "ib-projected-ebitda",
            "ib-ebitda-margin", "ib-free-cash", "ib-ebitda-delta",
            "ib-capex-delta",
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {
            "preset": "presentation",
            "cellSpacing": "small",
            "gridLines": "horizontal",
        },
        "style": panel(),
    })
    add({
        "id": "it-plan-log",
        "kind": "input-table",
        "name": "Plan Approval History",
        "source": {"kind": "empty", "connectionId": CONNECTION_ID},
        "inputMode": "view",
        "columns": [
            {"id": "log-plan", "name": "Plan", "type": "text"},
            {"id": "log-status", "name": "Status", "type": "text",
             "allowedValues": {
                 "kind": "list",
                 "values": ["Submitted", "Approved"],
                 "pills": "color-by-option",
             }},
            {"id": "log-by", "name": "By", "type": "text"},
            {"id": "log-at", "name": "At", "type": "datetime"},
            {"id": "log-note", "name": "Comment", "type": "text"},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {
            "preset": "presentation",
            "cellSpacing": "small",
            "gridLines": "horizontal",
        },
        "style": panel(),
    })
    for button_id, label, status, appearance in [
        ("btn-submit-plan", "Submit plan", "Submitted", "filled"),
        ("btn-approve-plan", "Approve plan", "Approved", "outline"),
    ]:
        add({
            "id": button_id,
            "kind": "button",
            "text": label,
            "appearance": appearance,
            "actions": [{
                "id": f"act-{button_id}",
                "trigger": "on-click",
                "successToast": {
                    "showMessage": "shown",
                    "title": f"Plan {status.lower()}",
                },
                "effects": [{
                    "effect": "insert-rows",
                    "tableElementId": "it-plan-log",
                    "values": {
                        "log-plan": {
                            "type": "control",
                            "control": "PlanName",
                        },
                        "log-status": {
                            "type": "constant",
                            "value": {"type": "text", "value": status},
                        },
                        "log-by": {
                            "type": "formula",
                            "formula": "CurrentUserEmail()",
                        },
                        "log-at": {
                            "type": "formula",
                            "formula": "Now()",
                        },
                        "log-note": {
                            "type": "control",
                            "control": "PlanComment",
                        },
                    },
                }],
            }],
        })
    budget = "FY27 Market Budget"
    kpi(
        "kpi-budget-arr", "it-budget", "Projected ARR",
        f"Sum([{budget}/Projected ARR])",
        f"Sum([{budget}/Current ARR])",
        MONEY, NAVY_DARK, comparison_label="Current run rate",
    )
    kpi(
        "kpi-budget-ebitda", "it-budget", "Projected EBITDA",
        f"Sum([{budget}/Projected EBITDA])",
        f"Sum([{budget}/Current EBITDA])",
        MONEY, NAVY, comparison_label="Current EBITDA",
    )
    kpi(
        "kpi-budget-margin", "it-budget", "EBITDA margin",
        f"Sum([{budget}/Projected EBITDA]) / "
        f"NullIf(Sum([{budget}/Projected ARR]), 0)",
        f"Sum([{budget}/Current EBITDA]) / "
        f"NullIf(Sum([{budget}/Current ARR]), 0)",
        PCT1, CORAL_DARK, comparison_label="Current margin",
    )
    kpi(
        "kpi-budget-fcf", "it-budget", "Free cash flow",
        f"Sum([{budget}/Free Cash Flow])",
        f"Sum([{budget}/Current EBITDA]) - "
        f"Sum([{budget}/Current Capex])",
        MONEY, NAVY_DARK, comparison_label="Current FCF",
    )
    add({
        "id": "ch-budget-ebitda",
        "kind": "bar-chart",
        "name": "Current vs projected EBITDA by market",
        "source": {"kind": "table", "elementId": "it-budget"},
        "columns": [
            {"id": "be-market", "name": "Market",
             "formula": f"[{budget}/Market]"},
            {"id": "be-current", "name": "Current EBITDA",
             "formula": f"Sum([{budget}/Current EBITDA])", "format": MONEY},
            {"id": "be-projected", "name": "Projected EBITDA",
             "formula": f"Sum([{budget}/Projected EBITDA])", "format": MONEY},
        ],
        "xAxis": {"columnId": "be-market"},
        "yAxis": {"columnIds": ["be-current", "be-projected"]},
        "stacking": "none",
        "legend": {"position": "top"},
        "style": panel(),
    })
    add({
        "id": "ch-budget-cash",
        "kind": "bar-chart",
        "name": "Projected free cash flow by market",
        "source": {"kind": "table", "elementId": "it-budget"},
        "columns": [
            {"id": "bc-market", "name": "Market",
             "formula": f"[{budget}/Market]"},
            {"id": "bc-fcf", "name": "Free Cash Flow",
             "formula": f"Sum([{budget}/Free Cash Flow])", "format": MONEY},
        ],
        "xAxis": {"columnId": "bc-market"},
        "yAxis": {"columnIds": ["bc-fcf"]},
        "legend": {"visibility": "hidden"},
        "style": panel(),
    })
    add({
        "id": "budget-note",
        "kind": "text",
        "body": (
            "**The finance app moment:** override Hudson net adds, ARPU, opex or "
            "capex. Projected ARR, EBITDA, margin and free cash flow update from "
            "the same editable grid. Then add a comment and Submit; approval history "
            "writes back with the acting user and timestamp."
        ),
        "style": panel("#FFF3F1"),
    })

    # Page 3 — service-location growth data application.
    header(2, "Serviceable Location Growth Planner",
           "Turn passings, address quality and campaign economics into a governed action plan")
    add({
        "id": "scope-growth",
        "kind": "text",
        "body": (
            SCOPE + " Type into Promo Budget, Take Rate Override, Target ARPU "
            "or FP&A Note. Every KPI and chart on this page reads the editable table."
        ),
        "style": {"backgroundColor": SKY, "borderRadius": "round"},
    })
    add({
        "id": "it-growth",
        "kind": "input-table",
        "name": "Growth Scenarios",
        "source": {"kind": "linked", "from": "tbl-growth"},
        "inputMode": "view",
        "columns": [
            {"id": "it-market", "key": "gr-market"},
            {"id": "it-state", "key": "gr-state"},
            {"id": "it-phase", "key": "gr-phase"},
            {"id": "it-budget", "name": "Promo Budget", "type": "number",
             "format": MONEY0},
            {"id": "it-take", "name": "Take Rate Override", "type": "number",
             "format": PCT1},
            {"id": "it-target", "name": "Target ARPU Override", "type": "number",
             "format": MONEY0},
            {"id": "it-note", "name": "FP&A Note", "type": "text"},
            {"id": "it-locs", "key": "gr-locs"},
            {"id": "it-subs", "key": "gr-subs"},
            {"id": "it-pen", "key": "gr-pen"},
            {"id": "it-arpu", "key": "gr-arpu"},
            {"id": "it-quality", "key": "gr-quality"},
            {"id": "it-rec-budget", "key": "gr-budget"},
            {"id": "it-base-take", "key": "gr-take"},
            {"id": "it-rec-arpu", "key": "gr-target-arpu"},
            {"id": "it-sales", "key": "gr-sales"},
            {"id": "it-score", "key": "gr-score"},
            {"id": "it-competitor", "key": "gr-competitor"},
            {"id": "it-campaign", "key": "gr-campaign"},
            {"id": "it-effective-budget", "name": "Effective Budget",
             "formula": "Coalesce([Promo Budget], [Recommended Budget])",
             "format": MONEY0},
            {"id": "it-effective-take", "name": "Effective Take Rate",
             "formula": "Coalesce([Take Rate Override], [Base Take Rate])",
             "format": PCT1},
            {"id": "it-effective-arpu", "name": "Effective Target ARPU",
             "formula": "Coalesce([Target ARPU Override], [Target ARPU])",
             "format": MONEY0},
            {"id": "it-project-adds", "name": "Projected Net Adds",
             "formula": (
                 "Round(Greatest([Serviceable Locations] - [Subscribers], 0) "
                 "* [Effective Take Rate] * [Address Quality], 0)"
             ), "format": NUM0},
            {"id": "it-project-arr", "name": "Projected ARR",
             "formula": "[Projected Net Adds] * [Effective Target ARPU] * 12",
             "format": MONEY0},
            {"id": "it-cac", "name": "Projected CAC",
             "formula": "[Effective Budget] / NullIf([Projected Net Adds], 0)",
             "format": MONEY0},
            {"id": "it-delta", "name": "ARR Δ vs current",
             "formula": (
                 "[Projected ARR] - "
                 "([Serviceable Locations] - [Subscribers]) * [Base Take Rate] "
                 "* [Address Quality] * [Current ARPU] * 12"
             ), "format": MONEY0},
        ],
        "order": [
            "it-market", "it-state", "it-phase", "it-budget", "it-take",
            "it-target", "it-note", "it-locs", "it-subs", "it-pen",
            "it-arpu", "it-quality", "it-rec-budget", "it-base-take",
            "it-rec-arpu", "it-sales", "it-score", "it-competitor",
            "it-campaign", "it-effective-budget", "it-effective-take",
            "it-effective-arpu", "it-project-adds", "it-project-arr",
            "it-cac", "it-delta",
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {
            "preset": "presentation",
            "cellSpacing": "small",
            "gridLines": "horizontal",
        },
        "style": panel(),
    })
    growth = "Growth Scenarios"
    kpi(
        "kpi-open-locs", "it-growth", "Clean opportunity locations",
        f"Sum(Greatest([{growth}/Serviceable Locations] - "
        f"[{growth}/Subscribers], 0) * [{growth}/Address Quality])",
        f"Sum(Greatest([{growth}/Serviceable Locations] - "
        f"[{growth}/Subscribers], 0))",
        NUM0, NAVY_DARK, comparison_label="Raw locations",
    )
    kpi(
        "kpi-project-adds", "it-growth", "Projected net adds",
        f"Sum([{growth}/Projected Net Adds])",
        f"Sum((Greatest([{growth}/Serviceable Locations] - "
        f"[{growth}/Subscribers], 0)) * [{growth}/Base Take Rate] "
        f"* [{growth}/Address Quality])",
        NUM0, CORAL_DARK, comparison_label="Base case",
    )
    kpi(
        "kpi-project-arr", "it-growth", "Projected incremental ARR",
        f"Sum([{growth}/Projected ARR])",
        f"Sum((Greatest([{growth}/Serviceable Locations] - "
        f"[{growth}/Subscribers], 0)) * [{growth}/Base Take Rate] "
        f"* [{growth}/Address Quality] * [{growth}/Current ARPU] * 12)",
        MONEY, NAVY, comparison_label="Base case",
    )
    kpi(
        "kpi-cac", "it-growth", "Blended projected CAC",
        f"Sum([{growth}/Effective Budget]) / "
        f"NullIf(Sum([{growth}/Projected Net Adds]), 0)",
        f"Sum([{growth}/Recommended Budget]) / "
        f"NullIf(Sum((Greatest([{growth}/Serviceable Locations] - "
        f"[{growth}/Subscribers], 0)) * [{growth}/Base Take Rate] "
        f"* [{growth}/Address Quality]), 0)",
        MONEY0, NAVY_DARK, comparison_label="Base case",
    )
    add({
        "id": "ch-growth",
        "kind": "bar-chart",
        "name": "Projected net adds by market",
        "source": {"kind": "table", "elementId": "it-growth"},
        "columns": [
            {"id": "grow-market", "name": "Market",
             "formula": f"[{growth}/Market]"},
            {"id": "grow-adds", "name": "Projected Net Adds",
             "formula": f"Sum([{growth}/Projected Net Adds])", "format": NUM0},
        ],
        "xAxis": {
            "columnId": "grow-market",
            "sort": {
                "by": "grow-adds",
                "aggregation": "sum",
                "direction": "descending",
            },
        },
        "yAxis": {"columnIds": ["grow-adds"]},
        "legend": {"visibility": "hidden"},
        "style": panel(),
    })
    add({
        "id": "ch-quality",
        "kind": "bar-chart",
        "name": "Penetration vs address quality",
        "source": {"kind": "table", "elementId": "it-growth"},
        "columns": [
            {"id": "quality-market", "name": "Market",
             "formula": f"[{growth}/Market]"},
            {"id": "quality-pen", "name": "Penetration",
             "formula": f"Avg([{growth}/Penetration])", "format": PCT1},
            {"id": "quality-address", "name": "Address Quality",
             "formula": f"Avg([{growth}/Address Quality])", "format": PCT1},
        ],
        "xAxis": {"columnId": "quality-market"},
        "yAxis": {"columnIds": ["quality-pen", "quality-address"]},
        "stacking": "none",
        "legend": {"position": "top"},
        "style": panel(),
    })
    add({
        "id": "growth-note",
        "kind": "text",
        "body": (
            "**Hand FP&A the keyboard.** Change Hudson's take rate or budget. "
            "The scenario updates without exporting a CSV, while Market, Vetro-style "
            "serviceability, competitor context and the finance outcome stay together."
        ),
        "style": panel("#FFF3F1"),
    })

    # Page 3 — export-ready FCC reporting and exception review.
    header(3, "FCC & State Reporting Pack",
           "Broadband serviceable-location reconciliation with owner-ready exceptions")
    add({
        "id": "scope-fcc",
        "kind": "text",
        "body": (
            SCOPE + " The support-at-risk field is illustrative scenario context, "
            "not a forecast of an actual government charge or award."
        ),
        "style": {"backgroundColor": SKY, "borderRadius": "round"},
    })
    list_control("ctrl-fcc-state", "FccState", "State",
                 "tbl-fcc", "fc-state")
    list_control("ctrl-fcc-status", "FccStatus", "Review status",
                 "tbl-fcc", "fc-status")
    fcc = "FCC Source"
    kpi(
        "kpi-fcc-served", "tbl-fcc", "Served locations",
        f"Sum([{fcc}/Served Locations])",
        f"Sum([{fcc}/Fabric Locations])",
        NUM0, NAVY_DARK, comparison_label="Fabric locations",
    )
    kpi(
        "kpi-fcc-valid", "tbl-fcc", "Valid BSL coverage",
        f"Sum([{fcc}/Valid BSL IDs]) / NullIf(Sum([{fcc}/Served Locations]), 0)",
        "0.985",
        PCT1, NAVY, comparison_label="98.5% target",
    )
    kpi(
        "kpi-fcc-exceptions", "tbl-fcc", "Address exceptions",
        f"Sum([{fcc}/Address Exceptions])",
        f"Sum([{fcc}/Address Exceptions]) * 1.18",
        NUM0, CORAL_DARK, good="#FFD0CB", bad="#C7F0DD",
        comparison_label="Prior run",
    )
    kpi(
        "kpi-fcc-risk", "tbl-fcc", "Illustrative support at risk",
        f"Sum([{fcc}/Illustrative Support at Risk])",
        f"Sum([{fcc}/Illustrative Support at Risk]) * 1.25",
        MONEY, BAD, good="#FFD0CB", bad="#C7F0DD",
        comparison_label="Prior exposure",
    )
    add({
        "id": "fcc-report-title",
        "kind": "text",
        "body": (
            "## **Broadband Data Collection — 2026 H1**\n"
            "**Provider:** Archtop Fiber  ·  **Technology:** Fiber to the Premises  "
            "·  **Prepared for:** FP&A / Regulatory review"
        ),
        "style": panel(),
    })
    add({
        "id": "tbl-fcc-summary",
        "kind": "table",
        "name": "Filing summary — state, county, technology and speed tier",
        "source": {"kind": "table", "elementId": "tbl-fcc"},
        "columns": [
            {"id": "fs-state", "name": "State", "formula": f"[{fcc}/State]"},
            {"id": "fs-county", "name": "County", "formula": f"[{fcc}/County]"},
            {"id": "fs-tech", "name": "Technology", "formula": f"[{fcc}/Technology]"},
            {"id": "fs-down", "name": "Down Mbps",
             "formula": f"[{fcc}/Max Download Mbps]", "format": NUM0},
            {"id": "fs-up", "name": "Up Mbps",
             "formula": f"[{fcc}/Max Upload Mbps]", "format": NUM0},
            {"id": "fs-served", "name": "Served Locations",
             "formula": f"Sum([{fcc}/Served Locations])", "format": NUM0},
            {"id": "fs-fabric", "name": "Fabric Locations",
             "formula": f"Sum([{fcc}/Fabric Locations])", "format": NUM0},
            {"id": "fs-valid", "name": "Valid BSL IDs",
             "formula": f"Sum([{fcc}/Valid BSL IDs])", "format": NUM0},
            {"id": "fs-address", "name": "Address Exceptions",
             "formula": f"Sum([{fcc}/Address Exceptions])", "format": NUM0},
        ],
        "groupings": [{
            "id": "fs-group",
            "groupBy": ["fs-state", "fs-county", "fs-tech", "fs-down", "fs-up"],
            "calculations": [
                "fs-served", "fs-fabric", "fs-valid", "fs-address"
            ],
        }],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {
            "preset": "presentation",
            "cellSpacing": "small",
            "gridLines": "horizontal",
        },
        "style": panel(),
    })
    add({
        "id": "it-fcc-review",
        "kind": "input-table",
        "name": "FCC Exception Review",
        "source": {"kind": "linked", "from": "tbl-fcc"},
        "inputMode": "view",
        "columns": [
            {"id": "fr-state", "key": "fc-state"},
            {"id": "fr-county", "key": "fc-county"},
            {"id": "fr-market", "key": "fc-market"},
            {"id": "fr-speed", "key": "fc-down"},
            {"id": "fr-address", "key": "fc-address"},
            {"id": "fr-mismatch", "key": "fc-mismatch"},
            {"id": "fr-source", "key": "fc-source"},
            {"id": "fr-status-source", "key": "fc-status"},
            {"id": "fr-owner", "name": "Review Owner", "type": "text"},
            {"id": "fr-resolution", "name": "Resolution", "type": "text"},
            {"id": "fr-certify", "name": "Certification Status",
             "type": "text", "allowedValues": {
                 "kind": "list",
                 "values": ["Needs review", "Validated", "Excluded"],
                 "pills": "color-by-option",
             }},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {
            "preset": "presentation",
            "cellSpacing": "small",
            "gridLines": "horizontal",
        },
        "style": panel(),
    })
    add({
        "id": "fcc-note",
        "kind": "text",
        "body": (
            "**Demo move:** filter Review status to **Needs review**, assign an owner "
            "and type a resolution. The same governed source feeds the regulator-ready "
            "summary and the operational exception queue—no once-a-quarter Python merge."
        ),
        "style": panel("#FFF3F1"),
    })

    layout = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-finance">
  <Container elementId="hdr-1" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-1" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="title-1" gridColumn="6 / 16" gridRow="1 / 4"/>
    <Element elementId="subtitle-1" gridColumn="6 / 16" gridRow="4 / 6"/>
    <Element elementId="nav-1" gridColumn="16 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-fin" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Element elementId="ctrl-fin-market" gridColumn="1 / 9" gridRow="8 / 11"/>
  <Element elementId="ctrl-fin-source" gridColumn="9 / 17" gridRow="8 / 11"/>
  <Element elementId="ctrl-fin-plan" gridColumn="17 / 25" gridRow="8 / 11"/>
  <Element elementId="kpi-mrr" gridColumn="1 / 7" gridRow="11 / 19"/>
  <Element elementId="kpi-arpu" gridColumn="7 / 13" gridRow="11 / 19"/>
  <Element elementId="kpi-subs" gridColumn="13 / 19" gridRow="11 / 19"/>
  <Element elementId="kpi-recon" gridColumn="19 / 25" gridRow="11 / 19"/>
  <Element elementId="ch-revenue" gridColumn="1 / 16" gridRow="19 / 35"/>
  <Element elementId="ch-plan" gridColumn="16 / 25" gridRow="19 / 35"/>
  <Element elementId="tbl-recon" gridColumn="1 / 20" gridRow="35 / 54"/>
  <Element elementId="fin-note" gridColumn="20 / 25" gridRow="35 / 54"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-budget">
  <Container elementId="hdr-4" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-4" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="title-4" gridColumn="6 / 16" gridRow="1 / 4"/>
    <Element elementId="subtitle-4" gridColumn="6 / 16" gridRow="4 / 6"/>
    <Element elementId="nav-4" gridColumn="16 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-budget" gridColumn="1 / 25" gridRow="6 / 9"/>
  <Element elementId="ctrl-plan-name" gridColumn="1 / 9" gridRow="9 / 12"/>
  <Element elementId="ctrl-plan-comment" gridColumn="9 / 17" gridRow="9 / 12"/>
  <Element elementId="btn-submit-plan" gridColumn="17 / 21" gridRow="9 / 12"/>
  <Element elementId="btn-approve-plan" gridColumn="21 / 25" gridRow="9 / 12"/>
  <Element elementId="kpi-budget-arr" gridColumn="1 / 7" gridRow="12 / 20"/>
  <Element elementId="kpi-budget-ebitda" gridColumn="7 / 13" gridRow="12 / 20"/>
  <Element elementId="kpi-budget-margin" gridColumn="13 / 19" gridRow="12 / 20"/>
  <Element elementId="kpi-budget-fcf" gridColumn="19 / 25" gridRow="12 / 20"/>
  <Element elementId="ch-budget-ebitda" gridColumn="1 / 13" gridRow="20 / 35"/>
  <Element elementId="ch-budget-cash" gridColumn="13 / 25" gridRow="20 / 35"/>
  <Element elementId="it-budget" gridColumn="1 / 20" gridRow="35 / 54"/>
  <Element elementId="budget-note" gridColumn="20 / 25" gridRow="35 / 54"/>
  <Element elementId="it-plan-log" gridColumn="1 / 25" gridRow="54 / 66"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-growth">
  <Container elementId="hdr-2" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-2" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="title-2" gridColumn="6 / 16" gridRow="1 / 4"/>
    <Element elementId="subtitle-2" gridColumn="6 / 16" gridRow="4 / 6"/>
    <Element elementId="nav-2" gridColumn="16 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-growth" gridColumn="1 / 25" gridRow="6 / 9"/>
  <Element elementId="kpi-open-locs" gridColumn="1 / 7" gridRow="9 / 17"/>
  <Element elementId="kpi-project-adds" gridColumn="7 / 13" gridRow="9 / 17"/>
  <Element elementId="kpi-project-arr" gridColumn="13 / 19" gridRow="9 / 17"/>
  <Element elementId="kpi-cac" gridColumn="19 / 25" gridRow="9 / 17"/>
  <Element elementId="ch-growth" gridColumn="1 / 13" gridRow="17 / 32"/>
  <Element elementId="ch-quality" gridColumn="13 / 25" gridRow="17 / 32"/>
  <Element elementId="it-growth" gridColumn="1 / 20" gridRow="32 / 52"/>
  <Element elementId="growth-note" gridColumn="20 / 25" gridRow="32 / 52"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-fcc">
  <Container elementId="hdr-3" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-3" gridColumn="1 / 6" gridRow="1 / 6"/>
    <Element elementId="title-3" gridColumn="6 / 16" gridRow="1 / 4"/>
    <Element elementId="subtitle-3" gridColumn="6 / 16" gridRow="4 / 6"/>
    <Element elementId="nav-3" gridColumn="16 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-fcc" gridColumn="1 / 25" gridRow="6 / 9"/>
  <Element elementId="ctrl-fcc-state" gridColumn="1 / 9" gridRow="9 / 12"/>
  <Element elementId="ctrl-fcc-status" gridColumn="9 / 17" gridRow="9 / 12"/>
  <Element elementId="kpi-fcc-served" gridColumn="1 / 7" gridRow="12 / 20"/>
  <Element elementId="kpi-fcc-valid" gridColumn="7 / 13" gridRow="12 / 20"/>
  <Element elementId="kpi-fcc-exceptions" gridColumn="13 / 19" gridRow="12 / 20"/>
  <Element elementId="kpi-fcc-risk" gridColumn="19 / 25" gridRow="12 / 20"/>
  <Element elementId="fcc-report-title" gridColumn="1 / 25" gridRow="20 / 24"/>
  <Element elementId="tbl-fcc-summary" gridColumn="1 / 25" gridRow="24 / 42"/>
  <Element elementId="it-fcc-review" gridColumn="1 / 20" gridRow="42 / 60"/>
  <Element elementId="fcc-note" gridColumn="20 / 25" gridRow="42 / 60"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-data">
  <Element elementId="tbl-fin" gridColumn="1 / 13" gridRow="1 / 18"/>
  <Element elementId="tbl-growth" gridColumn="13 / 25" gridRow="1 / 18"/>
  <Element elementId="tbl-fcc" gridColumn="1 / 13" gridRow="18 / 36"/>
  <Element elementId="tbl-budget" gridColumn="13 / 25" gridRow="18 / 36"/>
</Page>
"""

    return {
        "name": "Archtop Fiber — FP&A Growth & FCC Control Room",
        "folderId": FOLDER_ID,
        "document": {
            "schemaVersion": 1,
            "kind": "workbook",
            "elements": elements,
            "pages": [
                {"id": "pg-finance", "name": "FP&A Control Room"},
                {"id": "pg-budget", "name": "Budget & Forecast App"},
                {"id": "pg-growth", "name": "Growth Planner"},
                {"id": "pg-fcc", "name": "FCC Reporting"},
                {"id": "pg-data", "name": "Data", "visibility": "hidden"},
            ],
            "layout": layout,
            "settings": {
                "navigation": {"pageHeader": "enabled"},
                "theme": {"overrides": {
                    "colors": {
                        "text": TEXT,
                        "highlight": CORAL,
                        "success": GOOD,
                        "warning": WARN,
                        "danger": BAD,
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


def read_env(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    for key in (
        "SIGMA_BASE_URL",
        "SIGMA_CLIENT_ID",
        "SIGMA_CLIENT_SECRET",
        "SIGMA_PAPERCRANE_API_BASE",
        "SIGMA_PAPERCRANE_CLIENT_ID",
        "SIGMA_PAPERCRANE_CLIENT_SECRET",
    ):
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
        client_id = (
            env.get("SIGMA_PAPERCRANE_CLIENT_ID")
            or env.get("SIGMA_CLIENT_ID")
        )
        client_secret = (
            env.get("SIGMA_PAPERCRANE_CLIENT_SECRET")
            or env.get("SIGMA_CLIENT_SECRET")
        )
        if not self.base or not client_id or not client_secret:
            raise RuntimeError(
                "Sigma base URL, client id, and client secret are required"
            )
        encoded = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()
        request = urllib.request.Request(
            self.base + "/v2/auth/token",
            data=urllib.parse.urlencode(
                {"grant_type": "client_credentials"}
            ).encode(),
            headers={
                "Authorization": "Basic " + encoded,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            self.token = json.load(response)["access_token"]

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Sigma {method} {path} failed ({exc.code}): "
                + exc.read().decode()[:5000]
            ) from None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env-file",
        type=pathlib.Path,
        default=pathlib.Path("/workspace/.env"),
    )
    parser.add_argument("action", choices=["verify", "create", "update"])
    parser.add_argument("workbook_id", nargs="?")
    parser.add_argument("--expected-version", type=int)
    args = parser.parse_args()

    api = SigmaApi(read_env(args.env_file))
    spec = build_spec()
    if args.action == "verify":
        result = api.call("POST", "/v2/workbooks/spec/verify", spec)
        print(json.dumps(result, indent=2)[:10000])
        return
    if args.action == "create":
        result = api.call("POST", "/v2/workbooks/spec", spec)
        print(json.dumps(result, indent=2)[:4000])
        (HERE / "workbook_id.txt").write_text(result["workbookId"] + "\n")
        return
    if not args.workbook_id:
        raise SystemExit("update requires workbook_id")
    meta = api.call("GET", f"/v2/workbooks/{args.workbook_id}")
    if (
        args.expected_version is not None
        and meta["latestVersion"] != args.expected_version
    ):
        raise RuntimeError(
            f"Live version is {meta['latestVersion']}, "
            f"expected {args.expected_version}"
        )
    result = api.call(
        "PUT", f"/v2/workbooks/{args.workbook_id}/spec", spec
    )
    print(json.dumps(result, indent=2)[:4000])
    updated = api.call("GET", f"/v2/workbooks/{args.workbook_id}")
    print(
        "latestVersion",
        updated.get("latestVersion"),
        "workbookUrlId",
        updated.get("workbookUrlId"),
    )


if __name__ == "__main__":
    main()
