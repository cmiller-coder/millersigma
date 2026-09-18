#!/usr/bin/env python3
"""Build the Groma NAV REIT Cockpit Sigma workbook.

Deterministic synthetic records implement the accounting and classification
rules in the supplied REIT Cockpit blueprint. No production Groma data is used.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import urllib.parse
import urllib.request


HERE = pathlib.Path(__file__).resolve().parent
CONNECTION_ID = "a9d45cfe-ff65-4515-8193-a7072602a1ee"
FOLDER_ID = "a758d7ee-8c23-423d-9d60-5b635d9e9b58"

INK = "#172B2D"
FOREST = "#174A3A"
GREEN = "#2F745B"
MINT = "#DCEDE5"
GOLD = "#D29B3D"
CREAM = "#F7F4EC"
WHITE = "#FFFFFF"
BORDER = "#D9DED8"
GOOD = "#19725B"
WARN = "#A96F12"
BAD = "#B33C32"

MONEY = {"kind": "number", "formatString": "$.3~s"}
MONEY0 = {"kind": "number", "formatString": "$,.0f"}
PCT1 = {"kind": "number", "formatString": ".1%"}
PCT2 = {"kind": "number", "formatString": "+.2%"}
NUM0 = {"kind": "number", "formatString": ",.0f"}
DATE = {"kind": "datetime", "formatString": "%b %d, %Y"}

SCOPE = (
    "Illustrative demo using deterministic synthetic records shaped to the June 30, "
    "2026 cockpit specification. No production Groma, Buildium, loan, ownership, "
    "valuation, tenant, or investor data is present."
)

PROPERTY_SQL = r"""
WITH properties AS (
  SELECT * FROM VALUES
    ('BLD-1001','Harbor House','Groma Residential I LLC','East Boston',18,'2019-04-18',6200000,9150000,4860000,1.00,FALSE,FALSE,824000,246000,0,93000,320000,5700000,823600,9150000,4860000),
    ('BLD-1002','Maverick Flats','Groma Residential I LLC','East Boston',24,'2020-08-07',8400000,12600000,6720000,1.00,FALSE,FALSE,1090000,331000,0,128000,415000,7220000,1090000,12600000,6720000),
    ('BLD-1003','Chelsea Commons','Groma Residential II LLC','Chelsea',31,'2021-02-11',11200000,14800000,8010000,0.82,FALSE,FALSE,1345000,438000,0,154000,530000,9580000,1345000,14800000,8010000),
    ('BLD-1004','Broadway Lofts','Groma Residential II LLC','Chelsea',16,'2021-11-19',6900000,8750000,4380000,0.82,FALSE,TRUE,712000,198000,96000,101000,287000,6010000,616000,8750000,4380000),
    ('BLD-1005','Winter Hill Place','Groma Residential III LLC','Somerville',22,'2022-03-25',10100000,13750000,7330000,0.74,FALSE,FALSE,1210000,389000,0,142000,476000,8650000,1210000,13750000,7330000),
    ('BLD-1006','Union Square Row','Groma Residential III LLC','Somerville',14,'2022-09-09',7450000,10300000,5280000,0.74,FALSE,FALSE,895000,302000,0,99000,364000,6890000,895000,10300000,5280000),
    ('BLD-1007','Roxbury Crossing','Groma Opportunity LLC','Roxbury',38,'2023-01-17',13900000,17800000,9610000,0.68,FALSE,FALSE,1570000,565000,0,186000,690000,11300000,1570000,17800000,9610000),
    ('BLD-1008','Dudley Terrace','Groma Opportunity LLC','Roxbury',27,'2023-06-02',9700000,12100000,6400000,0.68,FALSE,TRUE,1040000,314000,126000,139000,522000,8440000,914000,12100000,6400000),
    ('BLD-1009','Jamaica Plain Court','Groma Residential IV LLC','Jamaica Plain',20,'2023-10-12',8900000,10900000,5720000,0.61,FALSE,FALSE,965000,346000,0,112000,401000,7510000,965000,10900000,5720000),
    ('BLD-1010','Centre Street Homes','Groma Residential IV LLC','Jamaica Plain',12,'2024-02-23',5700000,6650000,3380000,0.61,FALSE,FALSE,562000,221000,0,71000,248000,4990000,562000,6650000,3380000),
    ('BLD-1011','Seaport Residential JV','Harbor Equity JV LLC','South Boston',74,'2020-06-30',31600000,47500000,26800000,0.43,TRUE,FALSE,4180000,1520000,0,382000,1250000,23800000,4180000,47500000,26800000),
    ('BLD-1012','Dorchester Garden','Groma Workforce Housing LLC','Dorchester',42,'2024-07-15',15600000,16900000,8900000,0.57,FALSE,FALSE,1780000,702000,0,211000,930000,12700000,1780000,16900000,8900000)
  AS p(buildium_id,property_name,holding,neighborhood,units,acq_date,acq_cost,
       approved_value,debt,ownership_pct,equity_method,master_lease,total_income,
       total_expense,master_tenant_expense,cash_interest,recurring_capex,
       capex_budget,api_income,nav_tracker_value,control_debt)
)
SELECT
  buildium_id, property_name, holding, neighborhood, units,
  TO_DATE(acq_date) AS acquisition_date, acq_cost, approved_value, debt,
  ownership_pct, equity_method, master_lease, total_income, total_expense,
  master_tenant_expense,
  total_income - total_expense - master_tenant_expense AS raw_noi,
  cash_interest, recurring_capex, capex_budget,
  total_income - total_expense - master_tenant_expense - cash_interest AS cash_earnings,
  total_income - total_expense - master_tenant_expense - cash_interest - recurring_capex AS cash_contribution,
  approved_value * ownership_pct AS reit_value,
  IFF(equity_method, 0, debt * ownership_pct) AS reit_debt,
  IFF(equity_method, approved_value * ownership_pct,
      (approved_value - debt) * ownership_pct) AS reit_equity,
  (total_income - total_expense - master_tenant_expense) * ownership_pct AS reit_noi,
  (total_income - total_expense - master_tenant_expense - cash_interest - recurring_capex) * ownership_pct AS reit_cash_contribution,
  IFF(equity_method, 'Equity method — in-LLC debt excluded',
      IFF(master_lease, 'Consolidated — master rent allocated', 'Consolidated')) AS accounting_treatment,
  api_income - total_expense - master_tenant_expense AS api_noi,
  nav_tracker_value,
  control_debt,
  (total_income - total_expense - master_tenant_expense) - (api_income - total_expense - master_tenant_expense) AS noi_tie_delta,
  approved_value - nav_tracker_value AS value_tie_delta,
  debt - control_debt AS debt_tie_delta,
  IFF(ABS((total_income - total_expense - master_tenant_expense) - (api_income - total_expense - master_tenant_expense)) <= 500
      AND ABS(approved_value-nav_tracker_value) <= 500
      AND ABS(debt-control_debt) <= 500, 'Tied', 'Review') AS tie_status,
  IFF(DATEDIFF('month', TO_DATE(acq_date), '2026-06-30') >= 36, 'Seasoned', 'Lease-up') AS maturity,
  IFF(approved_value = 0, NULL, debt / approved_value) AS asset_ltv,
  (total_income - total_expense - master_tenant_expense) / NULLIF(approved_value,0) AS implied_yield
FROM properties
""".strip()

CAPEX_SQL = r"""
SELECT * FROM VALUES
  ('TX-2601','BLD-1001','Harbor House','2026-01-14','Roof membrane replacement',118000,'Recurring','Description: roof preserves rentability',TRUE),
  ('TX-2602','BLD-1002','Maverick Flats','2026-02-08','Unit 3A gut renovation',94000,'Value-add','Description: renovation changes unit basis',FALSE),
  ('TX-2603','BLD-1003','Chelsea Commons','2026-02-19','Boiler circulation pump',2100,'Recurring','Auto floor: amount below $2,500',TRUE),
  ('TX-2604','BLD-1004','Broadway Lofts','2026-03-03','Master lease unit refresh',62000,'Value-add','Manual pick: acquisition plan scope',FALSE),
  ('TX-2605','BLD-1005','Winter Hill Place','2026-03-22','Fire alarm panel replacement',136000,'Recurring','Description: life-safety maintenance',TRUE),
  ('TX-2606','BLD-1006','Union Square Row','2026-04-04','Kitchen repositioning package',151000,'Value-add','Description: renovation changes unit basis',FALSE),
  ('TX-2607','BLD-1007','Roxbury Crossing','2026-04-18','Exterior masonry stabilization',228000,'Recurring','Manual pick: preserves existing use',TRUE),
  ('TX-2608','BLD-1008','Dudley Terrace','2026-04-29','New basement amenity',87000,'Value-add','Description: adds rentable amenity',FALSE),
  ('TX-2609','BLD-1009','Jamaica Plain Court','2026-05-07','Turnover paint and flooring',2400,'Recurring','Auto floor: amount below $2,500',TRUE),
  ('TX-2610','BLD-1010','Centre Street Homes','2026-05-21','Electrical service upgrade',73000,'Recurring','Manual pick: required existing-system work',TRUE),
  ('TX-2611','BLD-1011','Seaport Residential JV','2026-06-02','Penthouse reconfiguration',315000,'Value-add','Description: renovation changes unit basis',FALSE),
  ('TX-2612','BLD-1012','Dorchester Garden','2026-06-16','Window seal remediation',46000,'Recurring','Description: envelope maintenance',TRUE)
  AS c(transaction_id,buildium_id,property_name,posted_date,description,amount,
       auto_class,rule_reason,deduct_from_cash)
""".strip()

TAB_SQL = r"""
SELECT * FROM VALUES
  (1,'Dashboard','Fund headline & holdings','SREO + Property Cash Flow + NAV recon','Executive'),
  (2,'REIT NAV & Holdings','Fund headline & holdings','Fund NAV + portfolio roll-ups','Executive'),
  (3,'SREO','Fund headline & holdings','Layer 1','Executive'),
  (4,'Portfolio','Property detail & cash','Layer 1','Property'),
  (5,'Property Cash Flow','Property detail & cash','Income statement + GL capex','Property'),
  (6,'Operating Scorecard','Property detail & cash','Income statement + rent roll','Property'),
  (7,'REIT Drivers','Property detail & cash','SREO + Property Cash Flow','Property'),
  (8,'Fund Health','Cohort & health','Layer 1','Portfolio'),
  (9,'Deep Dive','Cohort & health','Layer 1','Portfolio'),
  (10,'Cohort Analysis','Cohort & health','Layer 1','Portfolio'),
  (11,'Concentration','Cohort & health','Layer 1','Portfolio'),
  (12,'REIT Cash Flow & CAD','Cash to shareholders','Property cash flow + fund refs','Cash'),
  (13,'Dividend Forecast','Cash to shareholders','CAD + policy dials','Cash'),
  (14,'Capital Allocation','Cash to shareholders','PPM + NAV','Cash'),
  (15,'Debt & Risk','Debt, performance & peers','Loan database + NOI','Risk'),
  (16,'Debt','Debt, performance & peers','Loan database','Risk'),
  (17,'Fund Performance','Debt, performance & peers','NAV + contributions','Risk'),
  (18,'Peer Comps','Debt, performance & peers','Editable peer config','Risk'),
  (19,'Capex Review','Capex & configuration','GL 15xx classification','Config'),
  (20,'Capex Transactions','Capex & configuration','GL transaction detail','Config'),
  (21,'Policy','Capex & configuration','Editable policy config','Config'),
  (22,'Process','Capex & configuration','Quarterly workflow','Config'),
  (23,'Sources & Open Items','Capex & configuration','Provenance + validation','Config'),
  (24,'Budget vs Actual','Capex & configuration','Property plan + GL actuals','Config')
  AS t(tab_number,tab_name,decision_group,direct_source,demo_destination)
""".strip()

elements: list[dict] = []
overlays: list[dict] = []


def add(element: dict) -> dict:
    elements.append(element)
    return element


def panel(background: str = WHITE) -> dict:
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
            "textColor": FOREST,
            "selectedColor": GOLD,
            "style": "pill",
            "orientation": "horizontal",
        },
        "options": [
            {"label": "NAV", "destination": {"type": "page", "pageId": "pg-nav"}},
            {"label": "Properties", "destination": {"type": "page", "pageId": "pg-property"}},
            {"label": "Budget App", "destination": {"type": "page", "pageId": "pg-budget"}},
            {"label": "Capex", "destination": {"type": "page", "pageId": "pg-capex"}},
            {"label": "Controls", "destination": {"type": "page", "pageId": "pg-controls"}},
        ],
    })


def header(idx: int, title: str, subtitle: str) -> None:
    add({"id": f"hdr-{idx}", "kind": "container", "style": panel(WHITE)})
    add({
        "id": f"brand-{idx}",
        "kind": "text",
        "body": "## **GROMA**\nNAV REIT",
        "verticalAlign": "center",
    })
    add({
        "id": f"title-{idx}",
        "kind": "text",
        "body": f"# **{title}**\n{subtitle}",
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
    background: str = FOREST,
    comparison_label: str = "Reference",
    invert: bool = False,
) -> None:
    add({
        "id": eid,
        "kind": "kpi-chart",
        "source": {"kind": "table", "elementId": source},
        "columns": [
            {"id": f"{eid}-value", "name": label, "formula": current, "format": fmt},
            {"id": f"{eid}-ref", "name": comparison_label, "formula": prior, "format": fmt},
        ],
        "value": {"columnId": f"{eid}-value", "color": WHITE, "fontSize": 27},
        "comparisonColumn": {"columnId": f"{eid}-ref"},
        "comparison": {
            "display": "delta",
            "colorGood": "#F5DFAE" if invert else "#C8E9D8",
            "colorBad": "#C8E9D8" if invert else "#F5DFAE",
            "fontSize": 12,
        },
        "name": {"text": label, "color": WHITE, "fontSize": 13},
        "style": {"backgroundColor": background, "borderRadius": "round"},
    })


def list_control(eid: str, cid: str, label: str, table: str, column: str,
                 filters: list[tuple[str, str]] | None = None) -> None:
    targets = [{"source": {"kind": "table", "elementId": table}, "columnId": column}]
    for target, col in filters or []:
        targets.append({"source": {"kind": "table", "elementId": target}, "columnId": col})
    add({
        "id": eid,
        "kind": "control",
        "controlId": cid,
        "name": label,
        "controlType": "list",
        "mode": "include",
        "selectionMode": "multiple",
        "values": [],
        "filters": targets,
        "source": {
            "kind": "source",
            "source": {"kind": "table", "elementId": table},
            "columnId": column,
        },
    })


def build_spec() -> dict:
    elements.clear()
    overlays.clear()

    sql_table("src-property", "Layer 1 Property Quarter", PROPERTY_SQL, [
        {"id": "p-id", "name": "Buildium ID", "formula": "[Custom SQL/buildium_id]"},
        {"id": "p-name", "name": "Property", "formula": "[Custom SQL/property_name]"},
        {"id": "p-holding", "name": "Holding", "formula": "[Custom SQL/holding]"},
        {"id": "p-neighborhood", "name": "Neighborhood", "formula": "[Custom SQL/neighborhood]"},
        {"id": "p-units", "name": "Units", "formula": "[Custom SQL/units]", "format": NUM0},
        {"id": "p-date", "name": "Acquisition Date", "formula": "[Custom SQL/acquisition_date]", "format": DATE},
        {"id": "p-cost", "name": "Acquisition Cost", "formula": "[Custom SQL/acq_cost]", "format": MONEY0},
        {"id": "p-value", "name": "Approved Value", "formula": "[Custom SQL/approved_value]", "format": MONEY0},
        {"id": "p-debt", "name": "Debt", "formula": "[Custom SQL/debt]", "format": MONEY0},
        {"id": "p-own", "name": "REIT Ownership", "formula": "[Custom SQL/ownership_pct]", "format": PCT1},
        {"id": "p-equity-method", "name": "Equity Method", "formula": "[Custom SQL/equity_method]"},
        {"id": "p-master", "name": "Master Lease", "formula": "[Custom SQL/master_lease]"},
        {"id": "p-income", "name": "Buildium TTM Income", "formula": "[Custom SQL/total_income]", "format": MONEY0},
        {"id": "p-expense", "name": "Buildium TTM Expense", "formula": "[Custom SQL/total_expense]", "format": MONEY0},
        {"id": "p-master-expense", "name": "Master Tenant Expense", "formula": "[Custom SQL/master_tenant_expense]", "format": MONEY0},
        {"id": "p-noi", "name": "Raw NOI", "formula": "[Custom SQL/raw_noi]", "format": MONEY0},
        {"id": "p-interest", "name": "Cash Interest", "formula": "[Custom SQL/cash_interest]", "format": MONEY0},
        {"id": "p-rec-capex", "name": "Recurring Capex", "formula": "[Custom SQL/recurring_capex]", "format": MONEY0},
        {"id": "p-budget", "name": "Capex Budget", "formula": "[Custom SQL/capex_budget]", "format": MONEY0},
        {"id": "p-cash-earnings", "name": "Cash Earnings", "formula": "[Custom SQL/cash_earnings]", "format": MONEY0},
        {"id": "p-cash-contribution", "name": "Cash Contribution", "formula": "[Custom SQL/cash_contribution]", "format": MONEY0},
        {"id": "p-reit-value", "name": "REIT Value", "formula": "[Custom SQL/reit_value]", "format": MONEY0},
        {"id": "p-reit-debt", "name": "REIT Debt", "formula": "[Custom SQL/reit_debt]", "format": MONEY0},
        {"id": "p-reit-equity", "name": "REIT Equity", "formula": "[Custom SQL/reit_equity]", "format": MONEY0},
        {"id": "p-reit-noi", "name": "REIT NOI", "formula": "[Custom SQL/reit_noi]", "format": MONEY0},
        {"id": "p-reit-cash", "name": "REIT Cash Contribution", "formula": "[Custom SQL/reit_cash_contribution]", "format": MONEY0},
        {"id": "p-treatment", "name": "Accounting Treatment", "formula": "[Custom SQL/accounting_treatment]"},
        {"id": "p-api-noi", "name": "API NOI Check", "formula": "[Custom SQL/api_noi]", "format": MONEY0},
        {"id": "p-nav-check", "name": "NAV Tracker Check", "formula": "[Custom SQL/nav_tracker_value]", "format": MONEY0},
        {"id": "p-debt-check", "name": "Debt Control Check", "formula": "[Custom SQL/control_debt]", "format": MONEY0},
        {"id": "p-noi-delta", "name": "NOI Tie Delta", "formula": "[Custom SQL/noi_tie_delta]", "format": MONEY0},
        {"id": "p-value-delta", "name": "Value Tie Delta", "formula": "[Custom SQL/value_tie_delta]", "format": MONEY0},
        {"id": "p-debt-delta", "name": "Debt Tie Delta", "formula": "[Custom SQL/debt_tie_delta]", "format": MONEY0},
        {"id": "p-tie", "name": "Tie Status", "formula": "[Custom SQL/tie_status]"},
        {"id": "p-maturity", "name": "Maturity", "formula": "[Custom SQL/maturity]"},
        {"id": "p-ltv", "name": "Asset LTV", "formula": "[Custom SQL/asset_ltv]", "format": PCT1},
        {"id": "p-yield", "name": "Implied Yield", "formula": "[Custom SQL/implied_yield]", "format": PCT1},
    ])

    sql_table("src-capex", "Capex Transaction Detail", CAPEX_SQL, [
        {"id": "c-id", "name": "Transaction ID", "formula": "[Custom SQL/transaction_id]"},
        {"id": "c-property-id", "name": "Buildium ID", "formula": "[Custom SQL/buildium_id]"},
        {"id": "c-property", "name": "Property", "formula": "[Custom SQL/property_name]"},
        {"id": "c-date", "name": "Posted Date", "formula": "[Custom SQL/posted_date]"},
        {"id": "c-desc", "name": "Description", "formula": "[Custom SQL/description]"},
        {"id": "c-amount", "name": "Amount", "formula": "[Custom SQL/amount]", "format": MONEY0},
        {"id": "c-auto", "name": "Auto Class", "formula": "[Custom SQL/auto_class]"},
        {"id": "c-reason", "name": "Rule Reason", "formula": "[Custom SQL/rule_reason]"},
        {"id": "c-deduct", "name": "Deduct From Cash", "formula": "[Custom SQL/deduct_from_cash]"},
    ])

    sql_table("src-tabs", "Decision Tab Lineage", TAB_SQL, [
        {"id": "t-num", "name": "#", "formula": "[Custom SQL/tab_number]", "format": NUM0},
        {"id": "t-name", "name": "Decision Tab", "formula": "[Custom SQL/tab_name]"},
        {"id": "t-group", "name": "Decision Group", "formula": "[Custom SQL/decision_group]"},
        {"id": "t-source", "name": "Direct Source", "formula": "[Custom SQL/direct_source]"},
        {"id": "t-demo", "name": "Demo Destination", "formula": "[Custom SQL/demo_destination]"},
    ])

    prop = "Layer 1 Property Quarter"

    # Page 1: executive NAV.
    header(1, "NAV & Cash Control Room", "One governed property layer → twenty-four decisions")
    add({"id": "scope-nav", "kind": "text", "body": SCOPE, "style": panel(MINT)})
    list_control("ctrl-nav-holding", "NavHolding", "Holding", "src-property", "p-holding")
    list_control("ctrl-nav-neighborhood", "NavNeighborhood", "Neighborhood", "src-property", "p-neighborhood")
    kpi("kpi-nav", "src-property", "REIT net asset value",
        f"Sum([{prop}/REIT Equity])", f"Sum([{prop}/REIT Value])",
        MONEY, FOREST, "REIT gross value")
    kpi("kpi-noi", "src-property", "Raw TTM NOI — REIT share",
        f"Sum([{prop}/REIT NOI])", f"Sum([{prop}/Raw NOI])",
        MONEY, GREEN, "100% NOI")
    kpi("kpi-cash", "src-property", "Cash contribution — REIT share",
        f"Sum([{prop}/REIT Cash Contribution])", f"Sum([{prop}/REIT NOI])",
        MONEY, FOREST, "REIT NOI")
    kpi("kpi-ltv", "src-property", "REIT look-through LTV",
        f"Sum([{prop}/REIT Debt]) / NullIf(Sum([{prop}/REIT Value]),0)",
        "0.55", PCT1, GOLD, "Policy ceiling", True)
    add({
        "id": "chart-nav",
        "kind": "bar-chart",
        "name": "REIT equity by property — select a bar for full lineage",
        "source": {"kind": "table", "elementId": "src-property"},
        "columns": [
            {"id": "nv-name", "name": "Property", "formula": f"[{prop}/Property]"},
            {"id": "nv-equity", "name": "REIT Equity", "formula": f"Sum([{prop}/REIT Equity])", "format": MONEY},
            {"id": "nv-color", "name": "REIT Equity Color", "formula": f"Sum([{prop}/REIT Equity])", "format": MONEY},
        ],
        "xAxis": {"columnId": "nv-name", "sort": {"by": "nv-equity", "aggregation": "sum", "direction": "descending"}},
        "yAxis": {"columnIds": ["nv-equity"]},
        "color": {"by": "scale", "column": "nv-color", "scheme": [MINT, FOREST],
                  "domain": {"min": 1000000, "max": 21000000}},
        "legend": {"visibility": "hidden"},
        "style": panel(),
    })
    add({
        "id": "chart-cash",
        "kind": "bar-chart",
        "name": "REIT cash contribution by property",
        "source": {"kind": "table", "elementId": "src-property"},
        "columns": [
            {"id": "nc-name", "name": "Property", "formula": f"[{prop}/Property]"},
            {"id": "nc-cash", "name": "REIT Cash Contribution", "formula": f"Sum([{prop}/REIT Cash Contribution])", "format": MONEY},
            {"id": "nc-color", "name": "Cash Color", "formula": f"Sum([{prop}/REIT Cash Contribution])", "format": MONEY},
        ],
        "xAxis": {"columnId": "nc-name"},
        "yAxis": {"columnIds": ["nc-cash"]},
        "color": {"by": "scale", "column": "nc-color", "scheme": [WARN, MINT, GOOD],
                  "domain": {"min": 0, "mid": 250000, "max": 700000}},
        "legend": {"visibility": "hidden"},
        "style": panel(),
    })
    add({
        "id": "tbl-holdings",
        "kind": "table",
        "name": "Holdings scorecard — 100% asset block vs REIT ownership block",
        "source": {"kind": "table", "elementId": "src-property"},
        "columns": [
            {"id": "h-name", "name": "Property", "formula": f"[{prop}/Property]"},
            {"id": "h-treatment", "name": "Accounting Treatment", "formula": f"[{prop}/Accounting Treatment]"},
            {"id": "h-own", "name": "REIT %", "formula": f"Avg([{prop}/REIT Ownership])", "format": PCT1},
            {"id": "h-noi", "name": "100% Raw NOI", "formula": f"Sum([{prop}/Raw NOI])", "format": MONEY0},
            {"id": "h-value", "name": "100% Value", "formula": f"Sum([{prop}/Approved Value])", "format": MONEY0},
            {"id": "h-debt", "name": "100% Debt", "formula": f"Sum([{prop}/Debt])", "format": MONEY0},
            {"id": "h-reit-value", "name": "REIT Value", "formula": f"Sum([{prop}/REIT Value])", "format": MONEY0},
            {"id": "h-reit-debt", "name": "REIT Debt", "formula": f"Sum([{prop}/REIT Debt])", "format": MONEY0},
            {"id": "h-reit-equity", "name": "REIT Equity", "formula": f"Sum([{prop}/REIT Equity])", "format": MONEY0},
            {"id": "h-tie", "name": "Tie Status", "formula": f"Max([{prop}/Tie Status])"},
        ],
        "groupings": [{"id": "h-group", "groupBy": ["h-name", "h-treatment"],
                       "calculations": ["h-own", "h-noi", "h-value", "h-debt", "h-reit-value", "h-reit-debt", "h-reit-equity", "h-tie"]}],
        "conditionalFormats": [
            {"type": "dataBars", "columnIds": ["h-reit-equity"], "scheme": [GREEN, CREAM]},
            {"type": "single", "columnIds": ["h-treatment"], "condition": "formula",
             "formula": 'Contains([Accounting Treatment], "Equity method")',
             "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
            {"type": "single", "columnIds": ["h-tie"], "condition": "=", "value": "Tied",
             "style": {"backgroundColor": "#DCEDE5", "color": GOOD, "bold": True}},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal", "banding": "shown", "bandingColor": CREAM},
        "style": panel(),
    })

    # Page 2: property operations and rule visibility.
    header(2, "Property Operating Scorecard", "Raw Buildium NOI → interest → recurring capex → REIT cash")
    add({"id": "scope-property", "kind": "text",
         "body": SCOPE + " NOI contains no normalizations or add-backs.",
         "style": panel(MINT)})
    list_control("ctrl-prop-neighborhood", "PropNeighborhood", "Neighborhood", "src-property", "p-neighborhood")
    list_control("ctrl-prop-maturity", "PropMaturity", "Maturity", "src-property", "p-maturity")
    kpi("kpi-prop-noi", "src-property", "100% raw NOI", f"Sum([{prop}/Raw NOI])",
        f"Sum([{prop}/API NOI Check])", MONEY, FOREST, "Buildium API check")
    kpi("kpi-prop-margin", "src-property", "NOI margin", f"Sum([{prop}/Raw NOI]) / NullIf(Sum([{prop}/Buildium TTM Income]),0)",
        "0.55", PCT1, GREEN, "55% reference")
    kpi("kpi-prop-rec-capex", "src-property", "Recurring capex", f"Sum([{prop}/Recurring Capex])",
        f"Sum([{prop}/Capex Budget])", MONEY, GOLD, "Total capex budget", True)
    kpi("kpi-prop-cash", "src-property", "100% cash contribution", f"Sum([{prop}/Cash Contribution])",
        f"Sum([{prop}/Cash Earnings])", MONEY, FOREST, "Before recurring capex")
    add({
        "id": "tbl-property",
        "kind": "table",
        "name": "Property cash ladder — select any row for source and rule detail",
        "source": {"kind": "table", "elementId": "src-property"},
        "columns": [
            {"id": "os-name", "name": "Property", "formula": f"[{prop}/Property]"},
            {"id": "os-neighborhood", "name": "Neighborhood", "formula": f"[{prop}/Neighborhood]"},
            {"id": "os-special", "name": "Treatment", "formula": f"[{prop}/Accounting Treatment]"},
            {"id": "os-income", "name": "Buildium Income", "formula": f"Sum([{prop}/Buildium TTM Income])", "format": MONEY0},
            {"id": "os-expense", "name": "Buildium Expense", "formula": f"Sum([{prop}/Buildium TTM Expense])", "format": MONEY0},
            {"id": "os-master", "name": "Master Rent Allocation", "formula": f"Sum([{prop}/Master Tenant Expense])", "format": MONEY0},
            {"id": "os-noi", "name": "Raw NOI", "formula": f"Sum([{prop}/Raw NOI])", "format": MONEY0},
            {"id": "os-interest", "name": "Cash Interest", "formula": f"Sum([{prop}/Cash Interest])", "format": MONEY0},
            {"id": "os-capex", "name": "Recurring Capex", "formula": f"Sum([{prop}/Recurring Capex])", "format": MONEY0},
            {"id": "os-cash", "name": "Cash Contribution", "formula": f"Sum([{prop}/Cash Contribution])", "format": MONEY0},
            {"id": "os-share", "name": "REIT %", "formula": f"Avg([{prop}/REIT Ownership])", "format": PCT1},
            {"id": "os-reit-cash", "name": "REIT Cash", "formula": f"Sum([{prop}/REIT Cash Contribution])", "format": MONEY0},
            {"id": "os-yield", "name": "Implied Yield", "formula": f"Avg([{prop}/Implied Yield])", "format": PCT1},
        ],
        "groupings": [{"id": "os-group", "groupBy": ["os-name", "os-neighborhood", "os-special"],
                       "calculations": ["os-income", "os-expense", "os-master", "os-noi", "os-interest", "os-capex", "os-cash", "os-share", "os-reit-cash", "os-yield"]}],
        "conditionalFormats": [
            {"type": "dataBars", "columnIds": ["os-reit-cash"], "scheme": [GREEN, CREAM]},
            {"type": "single", "columnIds": ["os-special"], "condition": "formula",
             "formula": 'Not([Treatment] = "Consolidated")',
             "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
            {"type": "single", "columnIds": ["os-yield"], "condition": "<", "value": 0.045,
             "style": {"backgroundColor": "#F8DFDC", "color": BAD, "bold": True}},
            {"type": "single", "columnIds": ["os-yield"], "condition": ">", "value": 0.055,
             "style": {"backgroundColor": MINT, "color": GOOD}},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal", "banding": "shown", "bandingColor": CREAM},
        "style": panel(),
    })
    add({"id": "property-note", "kind": "text",
         "body": "**The point:** the math is simple; the treatment is not. The JV excludes in-LLC debt, master leases allocate offsetting rent expense, and every REIT column uses the quarter-specific ownership register.",
         "style": panel("#F5E5BC")})

    # Page 3: property-manager budget application.
    header(3, "Property Budget Application", "Enter forecast and capex decisions where leadership sees them immediately")
    add({"id": "scope-budget", "kind": "text",
         "body": SCOPE + " Peach cells are editable and warehouse-backed.",
         "style": panel(MINT)})
    add({
        "id": "ctrl-scenario",
        "kind": "control",
        "controlId": "BudgetScenario",
        "name": "Management scenario",
        "controlType": "segmented",
        "source": {"kind": "manual", "valueType": "text",
                   "values": ["Current Plan", "Lease-up Upside", "Cost Pressure"],
                   "labels": ["Current Plan", "Lease-up Upside", "Cost Pressure"]},
        "value": "Current Plan",
    })
    add({"id": "ctrl-budget-comment", "kind": "control", "controlId": "BudgetComment",
         "name": "Workflow comment", "controlType": "text", "mode": "equals",
         "case": "insensitive", "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False})
    add({
        "id": "it-budget",
        "kind": "input-table",
        "name": "Live Property Budget",
        "source": {"kind": "linked", "from": "src-property"},
        "inputMode": "view",
        "columns": [
            {"id": "ib-id", "key": "p-id"},
            {"id": "ib-name", "key": "p-name"},
            {"id": "ib-neighborhood", "key": "p-neighborhood"},
            {"id": "ib-noi-override", "name": "PM Forecast NOI", "type": "number", "format": MONEY0},
            {"id": "ib-capex-override", "name": "Revised Capex Budget", "type": "number", "format": MONEY0},
            {"id": "ib-owner", "name": "Property Manager", "type": "text"},
            {"id": "ib-note", "name": "Manager Note", "type": "text"},
            {"id": "ib-status", "name": "Budget Status", "type": "text",
             "allowedValues": {"kind": "list", "values": ["Draft", "Submitted", "Approved"], "pills": "color-by-option"}},
            {"id": "ib-noi", "key": "p-noi", "hidden": True},
            {"id": "ib-rec-capex", "key": "p-rec-capex", "hidden": True},
            {"id": "ib-budget", "key": "p-budget", "hidden": True},
            {"id": "ib-value", "key": "p-value", "hidden": True},
            {"id": "ib-own", "key": "p-own", "hidden": True},
            {"id": "ib-effective-noi", "name": "Effective Forecast NOI",
             "formula": 'Coalesce([PM Forecast NOI], [Raw NOI] * Switch([BudgetScenario], "Lease-up Upside", 1.06, "Cost Pressure", 0.94, 1.00))',
             "format": MONEY0},
            {"id": "ib-effective-budget", "name": "Effective Capex Budget",
             "formula": 'Coalesce([Revised Capex Budget], [Capex Budget] * Switch([BudgetScenario], "Lease-up Upside", 1.08, "Cost Pressure", 0.92, 1.00))',
             "format": MONEY0},
            {"id": "ib-remaining", "name": "Budget Remaining",
             "formula": "[Effective Capex Budget] - [Recurring Capex]", "format": MONEY0},
            {"id": "ib-noi-delta", "name": "NOI Δ vs TTM",
             "formula": "[Effective Forecast NOI] - [Raw NOI]", "format": MONEY0},
            {"id": "ib-reit-noi", "name": "Forecast REIT NOI",
             "formula": "[Effective Forecast NOI] * [REIT Ownership]", "format": MONEY0},
            {"id": "ib-implied-value", "name": "Management Value Sensitivity",
             "formula": '[Effective Forecast NOI] / Switch([BudgetScenario], "Lease-up Upside", 0.0475, "Cost Pressure", 0.0575, 0.0525)',
             "format": MONEY0},
            {"id": "ib-value-delta", "name": "Value Sensitivity Δ",
             "formula": "[Management Value Sensitivity] - [Approved Value]", "format": MONEY0},
        ],
        "order": ["ib-id", "ib-name", "ib-neighborhood", "ib-noi-override", "ib-capex-override", "ib-owner", "ib-note", "ib-status",
                  "ib-noi", "ib-rec-capex", "ib-budget", "ib-value", "ib-own", "ib-effective-noi", "ib-effective-budget", "ib-remaining",
                  "ib-noi-delta", "ib-reit-noi", "ib-implied-value", "ib-value-delta"],
        "conditionalFormats": [
            {"type": "single", "columnIds": ["ib-noi-override", "ib-capex-override", "ib-owner", "ib-note", "ib-status"],
             "condition": "formula", "formula": "True", "style": {"backgroundColor": "#FFF0E8"}},
            {"type": "dataBars", "columnIds": ["ib-remaining"], "scheme": [GOLD, CREAM]},
            {"type": "single", "columnIds": ["ib-remaining"], "condition": "<", "value": 0,
             "style": {"backgroundColor": "#F8DFDC", "color": BAD, "bold": True}},
            {"type": "single", "columnIds": ["ib-status"], "condition": "=", "value": "Approved",
             "style": {"backgroundColor": MINT, "color": GOOD, "bold": True}},
            {"type": "single", "columnIds": ["ib-status"], "condition": "=", "value": "Submitted",
             "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal", "banding": "shown", "bandingColor": CREAM},
        "style": panel(),
    })
    budget = "Live Property Budget"
    add({
        "id": "it-approval",
        "kind": "input-table",
        "name": "Budget Approval History",
        "source": {"kind": "empty", "connectionId": CONNECTION_ID},
        "inputMode": "view",
        "columns": [
            {"id": "al-scenario", "name": "Scenario", "type": "text"},
            {"id": "al-status", "name": "Status", "type": "text",
             "allowedValues": {"kind": "list", "values": ["Submitted", "Approved"], "pills": "color-by-option"}},
            {"id": "al-by", "name": "By", "type": "text"},
            {"id": "al-at", "name": "At", "type": "datetime"},
            {"id": "al-note", "name": "Comment", "type": "text"},
        ],
        "sort": [{"columnId": "al-at", "direction": "descending", "nulls": "last"}],
        "conditionalFormats": [
            {"type": "single", "columnIds": ["al-status"], "condition": "=", "value": "Approved",
             "style": {"backgroundColor": MINT, "color": GOOD, "bold": True}},
            {"type": "single", "columnIds": ["al-status"], "condition": "=", "value": "Submitted",
             "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal"},
        "style": panel(),
    })
    for button_id, label, status, appearance in [
        ("btn-budget-submit", "Submit budget", "Submitted", "filled"),
        ("btn-budget-approve", "Approve budget", "Approved", "outline"),
    ]:
        add({
            "id": button_id, "kind": "button", "text": label, "appearance": appearance,
            "actions": [{
                "id": f"act-{button_id}", "trigger": "on-click",
                "successToast": {"showMessage": "shown", "title": f"Budget {status.lower()}"},
                "effects": [{
                    "effect": "insert-rows", "tableElementId": "it-approval",
                    "values": {
                        "al-scenario": {"type": "control", "control": "BudgetScenario"},
                        "al-status": {"type": "constant", "value": {"type": "text", "value": status}},
                        "al-by": {"type": "formula", "formula": "CurrentUserEmail()"},
                        "al-at": {"type": "formula", "formula": "Now()"},
                        "al-note": {"type": "control", "control": "BudgetComment"},
                    },
                }],
            }],
        })
    kpi("kpi-budget-noi", "it-budget", "Forecast REIT NOI", f"Sum([{budget}/Forecast REIT NOI])",
        f"Sum([{budget}/Raw NOI] * [{budget}/REIT Ownership])", MONEY, FOREST, "Current TTM")
    kpi("kpi-budget-remain", "it-budget", "Capex budget remaining", f"Sum([{budget}/Budget Remaining])",
        f"Sum([{budget}/Effective Capex Budget])", MONEY, GREEN, "Effective budget")
    kpi("kpi-budget-value", "it-budget", "Management value sensitivity", f"Sum([{budget}/Management Value Sensitivity] * [{budget}/REIT Ownership])",
        f"Sum([{budget}/Approved Value] * [{budget}/REIT Ownership])", MONEY, GOLD, "Approved REIT value")
    add({
        "id": "chart-budget",
        "kind": "bar-chart",
        "name": "Budget remaining by property — select for detail",
        "source": {"kind": "table", "elementId": "it-budget"},
        "columns": [
            {"id": "br-name", "name": "Property", "formula": f"[{budget}/Property]"},
            {"id": "br-value", "name": "Budget Remaining", "formula": f"Sum([{budget}/Budget Remaining])", "format": MONEY},
            {"id": "br-color", "name": "Remaining Color", "formula": f"Sum([{budget}/Budget Remaining])", "format": MONEY},
        ],
        "xAxis": {"columnId": "br-name"},
        "yAxis": {"columnIds": ["br-value"]},
        "color": {"by": "scale", "column": "br-color", "scheme": [BAD, CREAM, GOOD],
                  "domain": {"min": -100000, "mid": 0, "max": 12000000}},
        "legend": {"visibility": "hidden"},
        "style": panel(),
    })
    add({"id": "budget-note", "kind": "text",
         "body": "**Demo move:** change one property's forecast NOI or capex budget, then submit the scenario. Leadership sees the portfolio impact immediately while the approved quarterly mark remains separately governed.",
         "style": panel("#F5E5BC")})

    # Page 4: capex classification application.
    header(4, "Capex Classification Review", "Description + recurring floor + persistent manual picks — never dollar size")
    add({"id": "scope-capex", "kind": "text", "body": SCOPE, "style": panel(MINT)})
    list_control("ctrl-capex-property", "CapexProperty", "Property", "src-capex", "c-property")
    add({
        "id": "it-capex",
        "kind": "input-table",
        "name": "15xx Capex Review Queue",
        "source": {"kind": "linked", "from": "src-capex"},
        "inputMode": "view",
        "columns": [
            {"id": "ic-id", "key": "c-id"},
            {"id": "ic-property", "key": "c-property"},
            {"id": "ic-date", "key": "c-date"},
            {"id": "ic-desc", "key": "c-desc"},
            {"id": "ic-amount", "key": "c-amount"},
            {"id": "ic-auto", "key": "c-auto"},
            {"id": "ic-reason", "key": "c-reason"},
            {"id": "ic-override", "name": "Manual Class Override", "type": "text",
             "allowedValues": {"kind": "list", "values": ["Recurring", "Value-add"], "pills": "color-by-option"}},
            {"id": "ic-reviewer", "name": "Reviewer", "type": "text"},
            {"id": "ic-note", "name": "Override Rationale", "type": "text"},
            {"id": "ic-effective", "name": "Effective Class", "formula": "Coalesce([Manual Class Override], [Auto Class])"},
            {"id": "ic-cash-impact", "name": "Cash Contribution Impact",
             "formula": 'If([Effective Class] = "Recurring", -[Amount], 0)', "format": MONEY0},
            {"id": "ic-affo", "name": "AFFO Deduction",
             "formula": 'If([Effective Class] = "Recurring", [Amount], 0)', "format": MONEY0},
        ],
        "conditionalFormats": [
            {"type": "single", "columnIds": ["ic-override", "ic-reviewer", "ic-note"],
             "condition": "formula", "formula": "True", "style": {"backgroundColor": "#FFF0E8"}},
            {"type": "single", "columnIds": ["ic-effective"], "condition": "=", "value": "Recurring",
             "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
            {"type": "single", "columnIds": ["ic-effective"], "condition": "=", "value": "Value-add",
             "style": {"backgroundColor": MINT, "color": GOOD, "bold": True}},
            {"type": "dataBars", "columnIds": ["ic-affo"], "scheme": [GOLD, CREAM]},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal", "banding": "shown", "bandingColor": CREAM},
        "style": panel(),
    })
    capex = "15xx Capex Review Queue"
    kpi("kpi-capex-total", "it-capex", "Capex reviewed", f"Sum([{capex}/Amount])", "0", MONEY, FOREST, "Unreviewed")
    kpi("kpi-capex-rec", "it-capex", "Recurring / AFFO deduction", f"Sum([{capex}/AFFO Deduction])",
        f"Sum([{capex}/Amount])", MONEY, GOLD, "All capex", True)
    kpi("kpi-capex-value", "it-capex", "Value-add capex",
        f"Sum(If([{capex}/Effective Class] = \"Value-add\", [{capex}/Amount], 0))",
        f"Sum([{capex}/Amount])", MONEY, GREEN, "All capex")
    add({
        "id": "chart-capex",
        "kind": "bar-chart",
        "name": "Capex by effective class",
        "source": {"kind": "table", "elementId": "it-capex"},
        "columns": [
            {"id": "cx-class", "name": "Class", "formula": f"[{capex}/Effective Class]"},
            {"id": "cx-amount", "name": "Amount", "formula": f"Sum([{capex}/Amount])", "format": MONEY},
            {"id": "cx-color", "name": "Class Color", "formula": f"[{capex}/Effective Class]"},
        ],
        "xAxis": {"columnId": "cx-class"},
        "yAxis": {"columnIds": ["cx-amount"]},
        "color": {"by": "category", "column": "cx-color", "scheme": [GOLD, GREEN]},
        "legend": {"visibility": "hidden"},
        "style": panel(),
    })
    add({"id": "capex-note", "kind": "text",
         "body": "**Accuracy test:** the $118k roof is recurring while the $94k gut renovation is value-add. A size threshold would classify the economics incorrectly; this queue makes the judgment visible and persistent.",
         "style": panel("#F5E5BC")})

    # Page 5: tie-outs, lineage, and 24-tab map.
    header(5, "Controls, Tie-outs & Lineage", "Every important number has an independent check")
    add({"id": "scope-controls", "kind": "text",
         "body": SCOPE + " Green means the primary and independent source agree within $500.",
         "style": panel(MINT)})
    kpi("kpi-tie-noi", "src-property", "NOI net tie delta", f"Sum([{prop}/NOI Tie Delta])", "0", MONEY0, FOREST, "Target", True)
    kpi("kpi-tie-value", "src-property", "Value net tie delta", f"Sum([{prop}/Value Tie Delta])", "0", MONEY0, GREEN, "Target", True)
    kpi("kpi-tie-debt", "src-property", "Debt net tie delta", f"Sum([{prop}/Debt Tie Delta])", "0", MONEY0, FOREST, "Target", True)
    kpi("kpi-tie-count", "src-property", "Properties requiring review",
        f"CountIf([{prop}/Tie Status] = \"Review\")", "0", NUM0, GOLD, "Target", True)
    add({
        "id": "tbl-tieouts",
        "kind": "table",
        "name": "Independent property tie-outs",
        "source": {"kind": "table", "elementId": "src-property"},
        "columns": [
            {"id": "to-name", "name": "Property", "formula": f"[{prop}/Property]"},
            {"id": "to-noi", "name": "Workbook NOI", "formula": f"Sum([{prop}/Raw NOI])", "format": MONEY0},
            {"id": "to-api", "name": "Buildium API NOI", "formula": f"Sum([{prop}/API NOI Check])", "format": MONEY0},
            {"id": "to-noi-d", "name": "NOI Δ", "formula": f"Sum([{prop}/NOI Tie Delta])", "format": MONEY0},
            {"id": "to-value", "name": "Approved Value", "formula": f"Sum([{prop}/Approved Value])", "format": MONEY0},
            {"id": "to-nav", "name": "NAV Tracker", "formula": f"Sum([{prop}/NAV Tracker Check])", "format": MONEY0},
            {"id": "to-value-d", "name": "Value Δ", "formula": f"Sum([{prop}/Value Tie Delta])", "format": MONEY0},
            {"id": "to-debt", "name": "Loan Database", "formula": f"Sum([{prop}/Debt])", "format": MONEY0},
            {"id": "to-control", "name": "Mortgage Control", "formula": f"Sum([{prop}/Debt Control Check])", "format": MONEY0},
            {"id": "to-debt-d", "name": "Debt Δ", "formula": f"Sum([{prop}/Debt Tie Delta])", "format": MONEY0},
            {"id": "to-status", "name": "Status", "formula": f"Max([{prop}/Tie Status])"},
        ],
        "groupings": [{"id": "to-group", "groupBy": ["to-name"],
                       "calculations": ["to-noi", "to-api", "to-noi-d", "to-value", "to-nav", "to-value-d", "to-debt", "to-control", "to-debt-d", "to-status"]}],
        "conditionalFormats": [
            {"type": "single", "columnIds": ["to-status"], "condition": "=", "value": "Tied",
             "style": {"backgroundColor": MINT, "color": GOOD, "bold": True}},
            {"type": "single", "columnIds": ["to-status"], "condition": "=", "value": "Review",
             "style": {"backgroundColor": "#F8DFDC", "color": BAD, "bold": True}},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal"},
        "style": panel(),
    })
    add({
        "id": "tbl-tabs",
        "kind": "table",
        "name": "Twenty-four decision tabs — one Layer 1 pipeline",
        "source": {"kind": "table", "elementId": "src-tabs"},
        "columns": [
            {"id": "dt-num", "name": "#", "formula": "[Decision Tab Lineage/#]"},
            {"id": "dt-name", "name": "Decision Tab", "formula": "[Decision Tab Lineage/Decision Tab]"},
            {"id": "dt-group", "name": "Decision Group", "formula": "[Decision Tab Lineage/Decision Group]"},
            {"id": "dt-source", "name": "Direct Source", "formula": "[Decision Tab Lineage/Direct Source]"},
            {"id": "dt-demo", "name": "Demo Destination", "formula": "[Decision Tab Lineage/Demo Destination]"},
        ],
        "sort": [{"columnId": "dt-num", "direction": "ascending", "nulls": "last"}],
        "conditionalFormats": [
            {"type": "single", "columnIds": ["dt-demo"], "condition": "=", "value": "Executive",
             "style": {"backgroundColor": MINT, "color": FOREST, "bold": True}},
            {"type": "single", "columnIds": ["dt-demo"], "condition": "=", "value": "Config",
             "style": {"backgroundColor": "#F5E5BC", "color": WARN}},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal", "banding": "shown", "bandingColor": CREAM},
        "style": panel(),
    })
    add({"id": "controls-note", "kind": "text",
         "body": "**Quarterly commit path:** refresh raw pulls → set ownership subject set → join on canonical Buildium ID → classify accounts and capex → build Layer 1 → validate tie-outs → publish one governed quarter.",
         "style": panel("#F5E5BC")})

    # Property detail drawer.
    overlays.append({
        "id": "drawer-property",
        "type": "drawer",
        "name": "Property Detail",
        "drawer": {"width": "large", "showShadow": "shown",
                   "header": {"title": "Property source & rule detail", "showCloseIcon": "shown"}},
    })
    add({"id": "drawer-title", "kind": "text",
         "body": "## **Property lineage**\nSource figures, special treatment, REIT-share math and independent tie-outs.",
         "style": panel("#F5E5BC")})
    add({
        "id": "ctrl-property-drill", "kind": "control", "controlId": "PropertyDrill",
        "name": "Selected property", "controlType": "list", "mode": "include",
        "selectionMode": "single", "value": "Seaport Residential JV",
        "values": ["Seaport Residential JV"],
        "filters": [{"source": {"kind": "table", "elementId": "tbl-property-detail"}, "columnId": "pd-name"}],
        "source": {"kind": "source", "source": {"kind": "table", "elementId": "tbl-property-detail"}, "columnId": "pd-name"},
    })
    add({
        "id": "tbl-property-detail",
        "kind": "table",
        "name": "Property accounting and cash detail",
        "source": {"kind": "table", "elementId": "src-property"},
        "columns": [
            {"id": "pd-name", "name": "Property", "formula": f"[{prop}/Property]"},
            {"id": "pd-id", "name": "Buildium ID", "formula": f"[{prop}/Buildium ID]"},
            {"id": "pd-treatment", "name": "Accounting Treatment", "formula": f"[{prop}/Accounting Treatment]"},
            {"id": "pd-own", "name": "Quarter Ownership", "formula": f"Avg([{prop}/REIT Ownership])", "format": PCT1},
            {"id": "pd-income", "name": "Income", "formula": f"Sum([{prop}/Buildium TTM Income])", "format": MONEY0},
            {"id": "pd-expense", "name": "Expense", "formula": f"Sum([{prop}/Buildium TTM Expense])", "format": MONEY0},
            {"id": "pd-master", "name": "Master Rent Allocation", "formula": f"Sum([{prop}/Master Tenant Expense])", "format": MONEY0},
            {"id": "pd-noi", "name": "Raw NOI", "formula": f"Sum([{prop}/Raw NOI])", "format": MONEY0},
            {"id": "pd-value", "name": "100% Value", "formula": f"Sum([{prop}/Approved Value])", "format": MONEY0},
            {"id": "pd-debt", "name": "100% Debt", "formula": f"Sum([{prop}/Debt])", "format": MONEY0},
            {"id": "pd-rvalue", "name": "REIT Value", "formula": f"Sum([{prop}/REIT Value])", "format": MONEY0},
            {"id": "pd-rdebt", "name": "REIT Debt", "formula": f"Sum([{prop}/REIT Debt])", "format": MONEY0},
            {"id": "pd-equity", "name": "REIT Equity", "formula": f"Sum([{prop}/REIT Equity])", "format": MONEY0},
            {"id": "pd-status", "name": "Tie Status", "formula": f"Max([{prop}/Tie Status])"},
        ],
        "groupings": [{"id": "pd-group", "groupBy": ["pd-name", "pd-id", "pd-treatment"],
                       "calculations": ["pd-own", "pd-income", "pd-expense", "pd-master", "pd-noi", "pd-value", "pd-debt", "pd-rvalue", "pd-rdebt", "pd-equity", "pd-status"]}],
        "conditionalFormats": [
            {"type": "single", "columnIds": ["pd-treatment"], "condition": "formula",
             "formula": 'Contains([Accounting Treatment], "Equity method")',
             "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
            {"type": "single", "columnIds": ["pd-status"], "condition": "=", "value": "Tied",
             "style": {"backgroundColor": MINT, "color": GOOD, "bold": True}},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal"},
        "style": panel(),
    })
    add({"id": "drawer-rule", "kind": "text",
         "body": "**Critical rule:** for the equity-method JV, REIT debt is $0 because the mortgage remains inside the LLC. REIT equity therefore equals REIT value. A naive ownership split would double-count debt and understate NAV.",
         "style": panel(MINT)})

    by_id = {element["id"]: element for element in elements}

    def drill(element_id: str, column_id: str) -> None:
        by_id[element_id]["actions"] = [{
            "id": f"drill-{element_id}",
            "trigger": {"on": "on-select", "condition": {"type": "column", "columnId": column_id, "condition": "IsNotNull"}},
            "effects": [
                {"effect": "set-control-value", "control": "PropertyDrill", "value": {"type": "column", "columnId": column_id}},
                {"effect": "open-overlay", "overlayId": "drawer-property"},
            ],
        }]

    for target, column in [
        ("chart-nav", "nv-name"),
        ("chart-cash", "nc-name"),
        ("tbl-holdings", "h-name"),
        ("tbl-property", "os-name"),
        ("chart-budget", "br-name"),
    ]:
        drill(target, column)

    layout = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-nav">
  <Container elementId="hdr-1" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="brand-1" gridColumn="1 / 5" gridRow="1 / 6"/>
    <Element elementId="title-1" gridColumn="5 / 15" gridRow="1 / 6"/>
    <Element elementId="nav-1" gridColumn="15 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-nav" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Element elementId="ctrl-nav-holding" gridColumn="1 / 13" gridRow="8 / 11"/>
  <Element elementId="ctrl-nav-neighborhood" gridColumn="13 / 25" gridRow="8 / 11"/>
  <Element elementId="kpi-nav" gridColumn="1 / 7" gridRow="11 / 19"/>
  <Element elementId="kpi-noi" gridColumn="7 / 13" gridRow="11 / 19"/>
  <Element elementId="kpi-cash" gridColumn="13 / 19" gridRow="11 / 19"/>
  <Element elementId="kpi-ltv" gridColumn="19 / 25" gridRow="11 / 19"/>
  <Element elementId="chart-nav" gridColumn="1 / 13" gridRow="19 / 35"/>
  <Element elementId="chart-cash" gridColumn="13 / 25" gridRow="19 / 35"/>
  <Element elementId="tbl-holdings" gridColumn="1 / 25" gridRow="35 / 57"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-property">
  <Container elementId="hdr-2" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="brand-2" gridColumn="1 / 5" gridRow="1 / 6"/>
    <Element elementId="title-2" gridColumn="5 / 15" gridRow="1 / 6"/>
    <Element elementId="nav-2" gridColumn="15 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-property" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Element elementId="ctrl-prop-neighborhood" gridColumn="1 / 13" gridRow="8 / 11"/>
  <Element elementId="ctrl-prop-maturity" gridColumn="13 / 25" gridRow="8 / 11"/>
  <Element elementId="kpi-prop-noi" gridColumn="1 / 7" gridRow="11 / 19"/>
  <Element elementId="kpi-prop-margin" gridColumn="7 / 13" gridRow="11 / 19"/>
  <Element elementId="kpi-prop-rec-capex" gridColumn="13 / 19" gridRow="11 / 19"/>
  <Element elementId="kpi-prop-cash" gridColumn="19 / 25" gridRow="11 / 19"/>
  <Element elementId="tbl-property" gridColumn="1 / 20" gridRow="19 / 47"/>
  <Element elementId="property-note" gridColumn="20 / 25" gridRow="19 / 47"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-budget">
  <Container elementId="hdr-3" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="brand-3" gridColumn="1 / 5" gridRow="1 / 6"/>
    <Element elementId="title-3" gridColumn="5 / 15" gridRow="1 / 6"/>
    <Element elementId="nav-3" gridColumn="15 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-budget" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Element elementId="ctrl-scenario" gridColumn="1 / 9" gridRow="8 / 11"/>
  <Element elementId="ctrl-budget-comment" gridColumn="9 / 17" gridRow="8 / 11"/>
  <Element elementId="btn-budget-submit" gridColumn="17 / 21" gridRow="8 / 11"/>
  <Element elementId="btn-budget-approve" gridColumn="21 / 25" gridRow="8 / 11"/>
  <Element elementId="kpi-budget-noi" gridColumn="1 / 9" gridRow="11 / 19"/>
  <Element elementId="kpi-budget-remain" gridColumn="9 / 17" gridRow="11 / 19"/>
  <Element elementId="kpi-budget-value" gridColumn="17 / 25" gridRow="11 / 19"/>
  <Element elementId="chart-budget" gridColumn="1 / 19" gridRow="19 / 34"/>
  <Element elementId="budget-note" gridColumn="19 / 25" gridRow="19 / 34"/>
  <Element elementId="it-budget" gridColumn="1 / 25" gridRow="34 / 57"/>
  <Element elementId="it-approval" gridColumn="1 / 25" gridRow="57 / 69"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-capex">
  <Container elementId="hdr-4" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="brand-4" gridColumn="1 / 5" gridRow="1 / 6"/>
    <Element elementId="title-4" gridColumn="5 / 15" gridRow="1 / 6"/>
    <Element elementId="nav-4" gridColumn="15 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-capex" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Element elementId="ctrl-capex-property" gridColumn="1 / 13" gridRow="8 / 11"/>
  <Element elementId="kpi-capex-total" gridColumn="1 / 9" gridRow="11 / 19"/>
  <Element elementId="kpi-capex-rec" gridColumn="9 / 17" gridRow="11 / 19"/>
  <Element elementId="kpi-capex-value" gridColumn="17 / 25" gridRow="11 / 19"/>
  <Element elementId="chart-capex" gridColumn="1 / 13" gridRow="19 / 34"/>
  <Element elementId="capex-note" gridColumn="13 / 25" gridRow="19 / 34"/>
  <Element elementId="it-capex" gridColumn="1 / 25" gridRow="34 / 59"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-controls">
  <Container elementId="hdr-5" type="grid" gridColumn="1 / 25" gridRow="1 / 6" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="brand-5" gridColumn="1 / 5" gridRow="1 / 6"/>
    <Element elementId="title-5" gridColumn="5 / 15" gridRow="1 / 6"/>
    <Element elementId="nav-5" gridColumn="15 / 25" gridRow="2 / 6"/>
  </Container>
  <Element elementId="scope-controls" gridColumn="1 / 25" gridRow="6 / 9"/>
  <Element elementId="kpi-tie-noi" gridColumn="1 / 7" gridRow="9 / 17"/>
  <Element elementId="kpi-tie-value" gridColumn="7 / 13" gridRow="9 / 17"/>
  <Element elementId="kpi-tie-debt" gridColumn="13 / 19" gridRow="9 / 17"/>
  <Element elementId="kpi-tie-count" gridColumn="19 / 25" gridRow="9 / 17"/>
  <Element elementId="tbl-tieouts" gridColumn="1 / 25" gridRow="17 / 39"/>
  <Element elementId="controls-note" gridColumn="1 / 25" gridRow="39 / 43"/>
  <Element elementId="tbl-tabs" gridColumn="1 / 25" gridRow="43 / 70"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-data">
  <Element elementId="src-property" gridColumn="1 / 25" gridRow="1 / 24"/>
  <Element elementId="src-capex" gridColumn="1 / 13" gridRow="24 / 45"/>
  <Element elementId="src-tabs" gridColumn="13 / 25" gridRow="24 / 45"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="drawer-property">
  <Element elementId="drawer-title" gridColumn="1 / 25" gridRow="1 / 5"/>
  <Element elementId="ctrl-property-drill" gridColumn="1 / 25" gridRow="5 / 8"/>
  <Element elementId="tbl-property-detail" gridColumn="1 / 25" gridRow="8 / 30"/>
  <Element elementId="drawer-rule" gridColumn="1 / 25" gridRow="30 / 36"/>
</Page>
"""

    return {
        "name": "Groma NAV REIT — Property Budget & Valuation Cockpit",
        "folderId": FOLDER_ID,
        "document": {
            "schemaVersion": 1,
            "kind": "workbook",
            "elements": elements,
            "overlays": overlays,
            "pages": [
                {"id": "pg-nav", "name": "NAV Control Room"},
                {"id": "pg-property", "name": "Property Scorecard"},
                {"id": "pg-budget", "name": "Property Budget App"},
                {"id": "pg-capex", "name": "Capex Review"},
                {"id": "pg-controls", "name": "Controls & Lineage"},
                {"id": "pg-data", "name": "Data", "visibility": "hidden"},
            ],
            "layout": layout,
            "settings": {
                "navigation": {"pageHeader": "enabled"},
                "theme": {"overrides": {
                    "colors": {"text": INK, "highlight": GOLD, "success": GOOD,
                               "warning": WARN, "danger": BAD, "darkMode": "hidden"},
                    "backgroundColor": CREAM,
                    "elementBackgroundColor": WHITE,
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
        "SIGMA_BASE_URL", "SIGMA_CLIENT_ID", "SIGMA_CLIENT_SECRET",
        "SIGMA_PAPERCRANE_API_BASE", "SIGMA_PAPERCRANE_CLIENT_ID",
        "SIGMA_PAPERCRANE_CLIENT_SECRET",
    ):
        if key not in values and os.environ.get(key):
            values[key] = os.environ[key]
    return values


class SigmaApi:
    def __init__(self, env: dict[str, str]):
        self.base = env.get("SIGMA_PAPERCRANE_API_BASE") or env.get("SIGMA_API_BASE") or env.get("SIGMA_BASE_URL")
        client_id = env.get("SIGMA_PAPERCRANE_CLIENT_ID") or env.get("SIGMA_CLIENT_ID")
        client_secret = env.get("SIGMA_PAPERCRANE_CLIENT_SECRET") or env.get("SIGMA_CLIENT_SECRET")
        if not self.base or not client_id or not client_secret:
            raise RuntimeError("Sigma base URL, client id, and client secret are required")
        encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        request = urllib.request.Request(
            self.base + "/v2/auth/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={"Authorization": "Basic " + encoded,
                     "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            self.token = json.load(response)["access_token"]

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Authorization": "Bearer " + self.token,
                     "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as error:
            raw = error.read().decode()
            raise RuntimeError(f"Sigma {method} {path} failed ({error.code}): {raw}") from error
        return json.loads(raw) if raw else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=pathlib.Path, default=pathlib.Path("/workspace/.env"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    sub.add_parser("create")
    update = sub.add_parser("update")
    update.add_argument("workbook_id")
    update.add_argument("--expected-version", type=int, required=True)
    args = parser.parse_args()

    api = SigmaApi(read_env(args.env_file))
    spec = build_spec()
    if args.command == "verify":
        result = api.request("POST", "/v2/workbooks/spec/verify", spec)
    elif args.command == "create":
        result = api.request("POST", "/v2/workbooks/spec", spec)
    else:
        result = api.request(
            "PUT",
            f"/v2/workbooks/{args.workbook_id}/spec",
            {"expectedVersion": args.expected_version, **spec},
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
