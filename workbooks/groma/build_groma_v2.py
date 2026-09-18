#!/usr/bin/env python3
"""Groma NAV REIT cockpit, v2.

What changed from v1 and why
----------------------------
v1 was a faithful reproduction of five of Groma's twenty-four spreadsheet tabs,
on twelve properties. That proves parity with the spreadsheet, not advantage
over it, and at twelve rows you cannot demonstrate concentration, cohort
spread, or finding the one wrong building - which is the entire reason to put
this in Sigma instead of Excel. It also led every page with a dense table and
put the actual point in a text caption beside it, which is why it was hard to
narrate.

v2 keeps the accounting engine (the five accuracy-critical rules from the
blueprint) and rebuilds everything above it:

  * ~150 properties, deterministic, matching the real book's scale. The named
    demo exemplars are pinned so the spoken demo still works.
  * Four pages named after decisions, not artifacts:
        1 What is the REIT worth, and can I trust it?
        2 Which buildings need me this quarter?
        3 Decide and commit                (write-back)
        4 Prove it                         (tie-outs + lineage)
  * Each page leads with one answer and one visual that carries it; tables sit
    underneath as proof.
  * A native, data-bound NAV bridge waterfall in which the equity-method
    adjustment is its own visible bar - the workbook's hardest idea, explained
    at a glance instead of in a caption.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
CONNECTION_ID = "a9d45cfe-ff65-4515-8193-a7072602a1ee"
FOLDER_ID = "a758d7ee-8c23-423d-9d60-5b635d9e9b58"

# Groma's own palette, sampled by frequency from groma.com's stylesheet -
# not guessed. Deep muted greens with a coral accent; the previous build used
# an evergreen/gold scheme that was nobody's brand.
INK = "#152B26"          # their body ink
FOREST = "#041915"       # darkest green - header band
GREEN = "#3A524B"        # dominant brand green (48 occurrences on their site)
GREEN_MID = "#2E423D"
SAGE = "#7A9B8E"
CORAL = "#ED5737"        # their accent
MINT = "#E8ECE9"
CREAM = "#F4F6F5"
WHITE = "#FFFFFF"
BORDER = "#D9DED8"
GOOD = "#2E6B57"
WARN = "#C4551F"         # darkened coral, legible as text on white
BAD = "#B33C32"
MUTED = "#5C6B63"
GOLD = CORAL             # accent alias: every former "gold" accent is coral now
LOGO = (Path := __import__("pathlib").Path)(__file__).resolve().parent.joinpath("logo.txt").read_text().strip()

MONEY = {"kind": "number", "formatString": "$.3~s"}
MONEY0 = {"kind": "number", "formatString": "$,.0f"}
PCT1 = {"kind": "number", "formatString": ".1%"}
NUM0 = {"kind": "number", "formatString": ",.0f"}
DATE = {"kind": "datetime", "formatString": "%b %d, %Y"}

SCOPE = (
    "Illustrative demo · 150 properties · synthetic records shaped to the June 30, 2026 "
    "cockpit spec · no production Groma, Buildium, loan or valuation data"
)

# ---------------------------------------------------------------------------
# The book
# ---------------------------------------------------------------------------
HOLDINGS = [
    ("Groma Residential I LLC", 1.00),
    ("Groma Residential II LLC", 0.82),
    ("Groma Residential III LLC", 0.74),
    ("Groma Residential IV LLC", 0.61),
    ("Groma Opportunity LLC", 0.68),
    ("Groma Workforce Housing LLC", 0.57),
    ("Harbor Equity JV LLC", 0.43),
]
HOODS = [
    ("East Boston", 1.00), ("Chelsea", 0.92), ("Somerville", 1.12),
    ("Roxbury", 0.86), ("Jamaica Plain", 1.02), ("Dorchester", 0.84),
    ("South Boston", 1.24), ("Everett", 0.88), ("Malden", 0.83),
    ("Revere", 0.81), ("Quincy", 0.95), ("Allston", 1.06),
]
STREETS = ["Bennington", "Saratoga", "Meridian", "Shawmut", "Dudley", "Centre",
           "Hyde Park", "Blue Hill", "Washington", "Broadway", "Dorchester",
           "Bowdoin", "Geneva", "Columbia", "Highland", "Medford", "Ferry",
           "Eastern", "Shirley", "Beach", "Adams", "Newport", "Harvard",
           "Cambridge", "Brighton", "Market", "Chestnut", "Walnut", "Maple", "Elm"]
SUFFIX = ["Street Apartments", "Terrace", "Commons", "Place", "Lofts", "Court",
          "Row", "Residences", "Flats", "Crossing", "Gardens", "House"]

# Pinned so the spoken demo keeps working: the equity-method JV, the two
# master-lease buildings, and the two capex exemplars.
PINNED = [
    ("BLD-1001", "Harbor House", "Groma Residential I LLC", "East Boston", 18, "2019-04-18", 6200000, 9150000, 4860000, 1.00, False, False),
    ("BLD-1002", "Maverick Flats", "Groma Residential I LLC", "East Boston", 24, "2020-08-07", 8400000, 12600000, 6720000, 1.00, False, False),
    ("BLD-1004", "Broadway Lofts", "Groma Residential II LLC", "Chelsea", 16, "2021-11-19", 6900000, 8750000, 4380000, 0.82, False, True),
    ("BLD-1008", "Dudley Terrace", "Groma Opportunity LLC", "Roxbury", 27, "2023-06-02", 9700000, 12100000, 6400000, 0.68, False, True),
    ("BLD-1011", "Seaport Residential JV", "Harbor Equity JV LLC", "South Boston", 74, "2020-06-30", 31600000, 47500000, 26800000, 0.43, True, False),
]

# Deliberate, explainable second-source breaks so the controls page can show
# the check catching something. A break is a data problem to reconcile at the
# source, never something to patch with a constant in the workbook.
NOI_BREAKS = {
    "BLD-1004": (24600, "Buildium API pull missing a June maintenance invoice batch - reconcile at the source"),
    "BLD-1137": (18200, "Property re-keyed mid-quarter after an entity-suffix rename; API pull still on the old key"),
}


def _h(*parts, mod=10 ** 9):
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % mod


def _pick(seq, *seed):
    return seq[_h(*seed, mod=len(seq))]


def _jit(lo, hi, *seed):
    return lo + (hi - lo) * (_h(*seed, mod=10_000) / 10_000.0)


def build_book(n_total=150):
    rows = list(PINNED)
    used = {r[1] for r in rows}
    i = 0
    while len(rows) < n_total:
        i += 1
        pid = f"BLD-{1100 + i}"
        hood, hood_mult = _pick(HOODS, pid, "hood")
        holding, own = _pick(HOLDINGS, pid, "hold")
        if holding == "Harbor Equity JV LLC":      # single equity-method asset only
            holding, own = HOLDINGS[_h(pid, "reassign", mod=6)]
        name = f"{_pick(STREETS, pid, 'st')} {_pick(SUFFIX, pid, 'sfx')}"
        if name in used:
            name = f"{_pick(STREETS, pid, 'st2')} {_pick(SUFFIX, pid, 'sfx2')} {i}"
        used.add(name)
        units = int(_jit(6, 46, pid, "units"))
        year = int(_jit(2018, 2025, pid, "yr"))
        acq = f"{year}-{1 + _h(pid, 'mo', mod=12):02d}-{1 + _h(pid, 'dy', mod=27):02d}"
        ppu = _jit(255000, 405000, pid, "ppu") * hood_mult * (1 - 0.035 * (2025 - year))
        cost = round(units * ppu, -4)
        value = round(cost * _jit(1.04, 1.46, pid, "appr"), -4)
        debt = round(value * _jit(0.38, 0.62, pid, "ltv"), -4)
        ml = _h(pid, "ml", mod=100) < 4
        rows.append((pid, name, holding, hood, units, acq, int(cost), int(value), int(debt), own, False, ml))
    return rows


def financials(r):
    pid, _n, _h2, hood, units, _a, _c, _v, debt, _o, _e, ml = r
    rpu = _jit(2050, 3350, pid, "rent") * dict(HOODS)[hood]
    income = round(units * rpu * 12, -3)
    margin = _jit(0.55, 0.69, pid, "margin")
    expense = round(income * (1 - margin), -3)
    master = round(income * _jit(0.10, 0.16, pid, "ml"), -3) if ml else 0
    interest = round(debt * _jit(0.049, 0.062, pid, "rate"), -3)
    return int(income), int(expense), int(master), int(interest)


BOOK = build_book()
NAMES = {r[0]: r[1] for r in BOOK}
UNITS = {r[0]: r[4] for r in BOOK}

# ---------------------------------------------------------------------------
# Capex: recurring capex per property is DERIVED from these lines, never typed
# twice. The blueprint's rule is "the tagging is the number" - the amount
# deducted to reach cash contribution must BE the sum of the recurring lines.
# ---------------------------------------------------------------------------
RESERVE_PER_UNIT = 1500
BUDGET_CONTINGENCY = 1.10

# per-unit cost in $000s. Calibrated so portfolio recurring capex lands near
# $2,000/unit/year (~10% of NOI) - lumpy envelope and life-safety work on a
# value-add book, not a token reserve, but not 30% of NOI either.
RECURRING_WORK = [
    ("Roof membrane replacement", "Description: roof preserves rentability", 2.10),
    ("Boiler replacement", "Description: required existing-system work", 1.40),
    ("Fire alarm panel replacement", "Description: life-safety maintenance", 1.70),
    ("Exterior masonry stabilization", "Manual pick: preserves existing use", 1.95),
    ("Window seal remediation", "Description: envelope maintenance", 0.75),
    ("Parking deck membrane", "Description: envelope maintenance", 1.05),
    ("Turnover paint and flooring", "Description: turnover maintenance", 0.38),
    ("Sprinkler head certification", "Description: life-safety maintenance", 0.88),
    ("Basement drainage repair", "Description: maintenance preserves existing use", 0.48),
    ("Elevator controller service", "Description: required existing-system work", 0.65),
]
VALUEADD_WORK = [
    ("Unit gut renovation", "Description: renovation changes unit basis", 1.45),
    ("Kitchen repositioning package", "Description: renovation changes unit basis", 1.20),
    ("New basement amenity", "Description: adds rentable amenity", 0.80),
    ("Bike room build-out", "Description: adds rentable amenity", 0.58),
    ("Unit repositioning", "Description: renovation changes unit basis", 1.00),
]

PINNED_CAPEX = [
    ("TX-2601", "BLD-1001", "2026-01-14", "Roof membrane replacement", 118000, "Recurring", "Description: roof preserves rentability"),
    ("TX-2602", "BLD-1002", "2026-02-08", "Unit 3A gut renovation", 94000, "Value-add", "Description: renovation changes unit basis"),
    ("TX-2603", "BLD-1011", "2026-06-02", "Penthouse reconfiguration", 315000, "Value-add", "Description: renovation changes unit basis"),
    ("TX-2604", "BLD-1004", "2026-03-03", "Master lease unit refresh", 62000, "Value-add", "Manual pick: acquisition plan scope"),
    ("TX-2605", "BLD-1008", "2026-04-29", "Turnover paint and flooring", 2400, "Recurring", "Auto floor: amount below $2,500"),
]


def build_capex():
    lines = list(PINNED_CAPEX)
    seq = 2700
    for r in BOOK:
        pid, units = r[0], r[4]
        n = 2 + _h(pid, "ncapex", mod=3)          # 2-4 lines per property
        for k in range(n):
            seq += 1
            value_add = _h(pid, "cls", k, mod=100) < 32
            pool = VALUEADD_WORK if value_add else RECURRING_WORK
            desc, reason, per_unit_k = _pick(pool, pid, "work", k)
            amount = int(round(units * per_unit_k * 1000 * _jit(0.55, 1.45, pid, "amt", k), -2))
            if not value_add and _h(pid, "floor", k, mod=100) < 12:
                amount = int(_jit(900, 2400, pid, "small", k))
                reason = "Auto floor: amount below $2,500"
            month = 1 + _h(pid, "cmo", k, mod=6)
            day = 1 + _h(pid, "cdy", k, mod=27)
            lines.append((f"TX-{seq}", pid, f"2026-{month:02d}-{day:02d}", desc,
                          amount, "Value-add" if value_add else "Recurring", reason))
    return lines


CAPEX = build_capex()


def recurring_capex(pid):
    return sum(l[4] for l in CAPEX if l[1] == pid and l[5] == "Recurring")


def total_capex(pid):
    return sum(l[4] for l in CAPEX if l[1] == pid)


def capex_budget(pid):
    """Approved recurring-capex plan: a per-unit reserve, varied by asset.

    Deliberately independent of what was actually spent, so real overruns
    exist and the over-budget exception is a live signal rather than a
    constant zero.
    """
    raw = 2400 * UNITS[pid] * _jit(0.85, 1.45, pid, "plan")
    return int(round(raw / 1000.0) * 1000)


def q(v: str) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def property_sql() -> str:
    rows = []
    for r in BOOK:
        pid, name, holding, hood, units, acq, cost, value, debt, own, eq, ml = r
        income, expense, master, interest = financials(r)
        brk, reason = NOI_BREAKS.get(pid, (0, ""))
        # the independent API pull nets master rent the same way the primary
        # income statement does; subtracting it twice on the check side is the
        # bug that produces false Review flags
        api_income = income - master - brk
        rows.append("    (" + ",".join([
            q(pid), q(name), q(holding), q(hood), str(units), q(acq), str(cost),
            str(value), str(debt), f"{own:.2f}",
            "TRUE" if eq else "FALSE", "TRUE" if ml else "FALSE",
            str(income), str(expense), str(master), str(interest),
            str(recurring_capex(pid)), str(capex_budget(pid)),
            str(api_income), str(value), str(debt), q(reason),
        ]) + ")")
    return """
WITH properties AS (
  SELECT * FROM VALUES
""" + ",\n".join(rows) + """
  AS p(buildium_id,property_name,holding,neighborhood,units,acq_date,acq_cost,
       approved_value,debt,ownership_pct,equity_method,master_lease,total_income,
       total_expense,master_tenant_expense,cash_interest,recurring_capex,
       capex_budget,api_income,nav_tracker_value,control_debt,break_reason)
), base AS (
SELECT
  buildium_id, property_name, holding, neighborhood, units,
  TO_DATE(acq_date) AS acquisition_date, acq_cost, approved_value, debt,
  ownership_pct, equity_method, master_lease, total_income, total_expense,
  master_tenant_expense, cash_interest, recurring_capex, capex_budget,
  break_reason, api_income, nav_tracker_value, control_debt,
  total_income - total_expense - master_tenant_expense AS raw_noi,
  capex_budget - recurring_capex AS budget_headroom,
  total_income - total_expense - master_tenant_expense - cash_interest AS cash_earnings,
  total_income - total_expense - master_tenant_expense - cash_interest - recurring_capex AS cash_contribution,
  approved_value * ownership_pct AS reit_value,
  IFF(equity_method, 0, debt * ownership_pct) AS reit_debt,
  IFF(equity_method, approved_value * ownership_pct,
      (approved_value - debt) * ownership_pct) AS reit_equity,
  (total_income - total_expense - master_tenant_expense) * ownership_pct AS reit_noi,
  (total_income - total_expense - master_tenant_expense - cash_interest - recurring_capex) * ownership_pct AS reit_cash_contribution,
  IFF(equity_method, 'Equity method - in-LLC debt excluded',
      IFF(master_lease, 'Consolidated - master rent allocated', 'Consolidated')) AS accounting_treatment,
  api_income - total_expense AS api_noi,
  (total_income - total_expense - master_tenant_expense) - (api_income - total_expense) AS noi_tie_delta,
  approved_value - nav_tracker_value AS value_tie_delta,
  debt - control_debt AS debt_tie_delta,
  IFF(DATEDIFF('month', TO_DATE(acq_date), '2026-06-30') >= 36, 'Seasoned', 'Lease-up') AS maturity,
  IFF(approved_value = 0, NULL, debt / approved_value) AS asset_ltv,
  approved_value / NULLIF(units,0) AS value_per_unit,
  (total_income - total_expense - master_tenant_expense) / NULLIF(total_income,0) AS noi_margin,
  (total_income - total_expense - master_tenant_expense) / NULLIF(approved_value,0) AS implied_yield
FROM properties
)
SELECT
  base.*,
  IFF(ABS(noi_tie_delta) <= 500 AND ABS(value_tie_delta) <= 500
      AND ABS(debt_tie_delta) <= 500, 'Tied', 'Review') AS tie_status,
  AVG(noi_margin) OVER (PARTITION BY neighborhood) AS hood_margin,
  noi_margin - AVG(noi_margin) OVER (PARTITION BY neighborhood) AS margin_gap,
  IFF(recurring_capex > capex_budget, 'Over budget', 'Within budget') AS budget_flag,
  IFF(noi_margin - AVG(noi_margin) OVER (PARTITION BY neighborhood) < -0.05,
      'Below cohort', 'At or above cohort') AS margin_flag
FROM base
""".strip()


def capex_sql() -> str:
    rows = []
    for tid, pid, date, desc, amount, auto, reason in CAPEX:
        rows.append("  (" + ",".join([
            q(tid), q(pid), q(NAMES[pid]), q(date), q(desc), str(amount),
            q(auto), q(reason), "TRUE" if auto == "Recurring" else "FALSE",
        ]) + ")")
    return """
SELECT * FROM VALUES
""" + ",\n".join(rows) + """
  AS c(transaction_id,buildium_id,property_name,posted_date,description,amount,
       auto_class,rule_reason,deduct_from_cash)
""".strip()


def bridge_sql() -> str:
    """The NAV bridge, as explicit steps.

    The equity-method add-back is its own step so the rule that moves the most
    money is a bar you can point at, not a footnote. Ties to REIT NAV exactly.
    """
    A = sum(r[7] for r in BOOK)
    B = sum(r[8] for r in BOOK)
    own_eq = sum((r[7] - r[8]) * r[9] for r in BOOK)
    jv = sum(r[8] * r[9] for r in BOOK if r[10])
    minority = (A - B) - own_eq
    steps = [
        (1, "Value", int(A)),
        (2, "Debt", -int(B)),
        (3, "Minority", -int(round(minority))),
        (4, "JV add-back", int(round(jv))),
    ]
    rows = ["  (" + ",".join([str(o), q(l), str(v)]) + ")" for o, l, v in steps]
    return """
SELECT * FROM VALUES
""" + ",\n".join(rows) + """
  AS b(step_order,step_label,amount)
""".strip()


TAB_SQL = r"""
SELECT * FROM VALUES
  (1,'Dashboard','Fund headline & holdings','SREO + Property Cash Flow + NAV recon'),
  (2,'REIT NAV & Holdings','Fund headline & holdings','Fund NAV + portfolio roll-ups'),
  (3,'SREO','Fund headline & holdings','Layer 1'),
  (4,'Portfolio','Property detail & cash','Layer 1'),
  (5,'Property Cash Flow','Property detail & cash','Income statement + GL capex'),
  (6,'Operating Scorecard','Property detail & cash','Income statement + rent roll'),
  (7,'REIT Drivers','Property detail & cash','SREO + Property Cash Flow'),
  (8,'Fund Health','Cohort & health','Layer 1'),
  (9,'Deep Dive','Cohort & health','Layer 1'),
  (10,'Cohort Analysis','Cohort & health','Layer 1'),
  (11,'Concentration','Cohort & health','Layer 1'),
  (12,'REIT Cash Flow & CAD','Cash to shareholders','Property cash flow + fund refs'),
  (13,'Dividend Forecast','Cash to shareholders','CAD + policy dials'),
  (14,'Capital Allocation','Cash to shareholders','PPM + NAV'),
  (15,'Debt & Risk','Debt, performance & peers','Loan database + NOI'),
  (16,'Debt','Debt, performance & peers','Loan database'),
  (17,'Fund Performance','Debt, performance & peers','NAV + contributions'),
  (18,'Peer Comps','Debt, performance & peers','Editable peer config'),
  (19,'Capex Review','Capex & configuration','GL 15xx classification'),
  (20,'Capex Transactions','Capex & configuration','GL transaction detail'),
  (21,'Policy','Capex & configuration','Editable policy config'),
  (22,'Process','Capex & configuration','Quarterly workflow'),
  (23,'Sources & Open Items','Capex & configuration','Provenance + validation'),
  (24,'Budget vs Actual','Capex & configuration','Property plan + GL actuals')
  AS t(tab_number,tab_name,decision_group,direct_source)
""".strip()

# ---------------------------------------------------------------------------
# element helpers
# ---------------------------------------------------------------------------
elements: list[dict] = []
overlays: list[dict] = []
agents: list[dict] = []
PROP = "Layer 1 Property Book"
CAPEXT = "Capex Transaction Detail"


def add(e):
    elements.append(e)
    return e


def panel(bg=WHITE):
    return {"backgroundColor": bg, "borderColor": BORDER, "borderWidth": 1,
            "borderRadius": "round"}


def sql_table(eid, name, sql, columns):
    add({"id": eid, "kind": "table", "name": name,
         "source": {"kind": "sql", "connectionId": CONNECTION_ID, "statement": sql},
         "columns": columns})


NAV_OPTIONS = [
    ("Worth", "pg-worth"), ("Attention", "pg-attention"),
    ("Decide", "pg-decide"), ("Prove", "pg-prove"),
]


def header(idx, title):
    # Dark brand band carrying Groma's real white logo, per the standing
    # header convention. Their own site is near-black green, so the white
    # wordmark they publish drops straight in with no recolouring.
    add({"id": f"hdr-{idx}", "kind": "container",
         "style": {"backgroundColor": FOREST, "borderRadius": "round"}})
    add({"id": f"brand-{idx}", "kind": "image",
         "source": {"kind": "url", "url": LOGO},
         "style": {"fit": "contain", "align": "start", "padding": "none"}})
    add({"id": f"title-{idx}", "kind": "text", "verticalAlign": "center",
         "body": f'### **<span style="color: {WHITE}">{title}</span>**'})
    add({"id": f"nav-{idx}", "kind": "navigation", "mode": "manual", "showIcons": False,
         "optionStyle": {"textColor": SAGE, "selectedColor": CORAL,
                         "style": "pill", "orientation": "horizontal"},
         "options": [{"label": l, "destination": {"type": "page", "pageId": p}}
                     for l, p in NAV_OPTIONS]})


def kpi(eid, source, label, current, prior, fmt, accent=INK,
        comparison_label="Reference", invert=False):
    """Native Sigma KPI card: light surface, dark value, coloured delta chip."""
    add({"id": eid, "kind": "kpi-chart",
         "source": {"kind": "table", "elementId": source},
         "columns": [
             {"id": f"{eid}-value", "name": label, "formula": current, "format": fmt},
             {"id": f"{eid}-ref", "name": comparison_label, "formula": prior, "format": fmt},
         ],
         "value": {"columnId": f"{eid}-value", "color": accent, "fontSize": 28},
         "comparisonColumn": {"columnId": f"{eid}-ref"},
         "comparison": {"display": "delta", "colorGood": BAD if invert else GOOD,
                        "colorBad": GOOD if invert else BAD, "fontSize": 12},
         "name": {"text": label, "color": MUTED, "fontSize": 12},
         "style": {"backgroundColor": WHITE, "borderRadius": "round",
                   "borderColor": BORDER, "borderWidth": 1}})


def list_control(eid, cid, label, table, column, extra=()):
    targets = [{"source": {"kind": "table", "elementId": table}, "columnId": column}]
    for t, c in extra:
        targets.append({"source": {"kind": "table", "elementId": t}, "columnId": c})
    add({"id": eid, "kind": "control", "controlId": cid, "name": label,
         "controlType": "list", "mode": "include", "selectionMode": "multiple",
         "values": [], "filters": targets,
         "source": {"kind": "source",
                    "source": {"kind": "table", "elementId": table},
                    "columnId": column}})


def text(eid, body, bg=None):
    e = {"id": eid, "kind": "text", "body": body}
    if bg:
        e["style"] = panel(bg)
    return add(e)


def scope(eid):
    """Small muted disclaimer. Explanatory prose does not belong on a product
    surface: the numbers and the visuals carry the argument, and the spoken
    demo script carries the rest. Four tinted full-width slabs of paragraph
    were the single biggest thing making this look unfinished."""
    return add({"id": eid, "kind": "text", "verticalAlign": "center",
                "body": f'<span style="color: {MUTED}">{SCOPE}</span>'})


def agent(aid, name, page, instructions, greeting, sources):
    agents.append({"id": aid, "name": name, "instructions": instructions,
                   "greeting": {"mode": "static", "message": greeting},
                   "dataSources": [{"kind": "table", "elementId": s} for s in sources]})
    add({"id": f"chat-{aid}", "kind": "chat", "agentId": aid, "style": panel()})


GUARD = (
    " The figures are deterministic synthetic records shaped to the June 30, 2026 cockpit "
    "specification. Never claim they are production Groma, Buildium, loan, ownership, "
    "valuation, tenant or investor data, and never claim the workbook is connected to "
    "Groma systems. If the governed layer does not contain something, say so rather than "
    "estimating."
)
RULES = (
    " Accounting rules that govern every answer. (1) NOI is raw: Buildium total income minus "
    "total expense over the TTM window, with an explicit master-tenant rent allocation for "
    "master-lease properties; no normalisations or add-backs. (2) Seaport Residential JV is an "
    "equity-method joint venture: its mortgage sits inside the LLC below the REIT, so its REIT "
    "debt is $0 and REIT equity equals REIT value. Pro-rating that in-LLC mortgage would "
    "double-count a material amount of debt and understate NAV. (3) Master-lease properties "
    "book rent on the entity while the offsetting master-tenant rent sits elsewhere, so a naive "
    "account sum overstates their NOI. (4) Capex classification is nature-based, never dollar "
    "size: description rules, an auto-recurring floor at $2,500, and manual picks that persist. "
    "Only recurring capex is deducted to reach cash contribution. (5) Every REIT column is the "
    "100 percent figure times the quarter-specific ownership percent."
)


def build_spec() -> dict:
    elements.clear(); overlays.clear(); agents.clear()

    # ---------------- data layer
    sql_table("src-property", PROP, property_sql(), [
        {"id": "p-id", "name": "Buildium ID", "formula": "[Custom SQL/buildium_id]"},
        {"id": "p-name", "name": "Property", "formula": "[Custom SQL/property_name]"},
        {"id": "p-holding", "name": "Holding", "formula": "[Custom SQL/holding]"},
        {"id": "p-hood", "name": "Neighborhood", "formula": "[Custom SQL/neighborhood]"},
        {"id": "p-units", "name": "Units", "formula": "[Custom SQL/units]", "format": NUM0},
        {"id": "p-date", "name": "Acquired", "formula": "[Custom SQL/acquisition_date]", "format": DATE},
        {"id": "p-value", "name": "Approved Value", "formula": "[Custom SQL/approved_value]", "format": MONEY0},
        {"id": "p-debt", "name": "Debt", "formula": "[Custom SQL/debt]", "format": MONEY0},
        {"id": "p-own", "name": "REIT %", "formula": "[Custom SQL/ownership_pct]", "format": PCT1},
        {"id": "p-treatment", "name": "Accounting Treatment", "formula": "[Custom SQL/accounting_treatment]"},
        {"id": "p-income", "name": "Buildium Income", "formula": "[Custom SQL/total_income]", "format": MONEY0},
        {"id": "p-expense", "name": "Buildium Expense", "formula": "[Custom SQL/total_expense]", "format": MONEY0},
        {"id": "p-master", "name": "Master Rent Allocation", "formula": "[Custom SQL/master_tenant_expense]", "format": MONEY0},
        {"id": "p-noi", "name": "Raw NOI", "formula": "[Custom SQL/raw_noi]", "format": MONEY0},
        {"id": "p-interest", "name": "Cash Interest", "formula": "[Custom SQL/cash_interest]", "format": MONEY0},
        {"id": "p-rec-capex", "name": "Recurring Capex", "formula": "[Custom SQL/recurring_capex]", "format": MONEY0},
        {"id": "p-budget", "name": "Capex Budget", "formula": "[Custom SQL/capex_budget]", "format": MONEY0},
        {"id": "p-headroom", "name": "Budget Headroom", "formula": "[Custom SQL/budget_headroom]", "format": MONEY0},
        {"id": "p-cash", "name": "Cash Contribution", "formula": "[Custom SQL/cash_contribution]", "format": MONEY0},
        {"id": "p-reit-value", "name": "REIT Value", "formula": "[Custom SQL/reit_value]", "format": MONEY0},
        {"id": "p-reit-debt", "name": "REIT Debt", "formula": "[Custom SQL/reit_debt]", "format": MONEY0},
        {"id": "p-reit-equity", "name": "REIT Equity", "formula": "[Custom SQL/reit_equity]", "format": MONEY0},
        {"id": "p-reit-noi", "name": "REIT NOI", "formula": "[Custom SQL/reit_noi]", "format": MONEY0},
        {"id": "p-reit-cash", "name": "REIT Cash Contribution", "formula": "[Custom SQL/reit_cash_contribution]", "format": MONEY0},
        {"id": "p-vpu", "name": "Value per Unit", "formula": "[Custom SQL/value_per_unit]", "format": MONEY0},
        {"id": "p-margin", "name": "NOI Margin", "formula": "[Custom SQL/noi_margin]", "format": PCT1},
        {"id": "p-hood-margin", "name": "Neighborhood Avg Margin", "formula": "[Custom SQL/hood_margin]", "format": PCT1},
        {"id": "p-gap", "name": "Margin Gap vs Cohort", "formula": "[Custom SQL/margin_gap]", "format": PCT1},
        {"id": "p-margin-flag", "name": "Margin Flag", "formula": "[Custom SQL/margin_flag]"},
        {"id": "p-budget-flag", "name": "Budget Flag", "formula": "[Custom SQL/budget_flag]"},
        {"id": "p-maturity", "name": "Maturity", "formula": "[Custom SQL/maturity]"},
        {"id": "p-ltv", "name": "Asset LTV", "formula": "[Custom SQL/asset_ltv]", "format": PCT1},
        {"id": "p-yield", "name": "Implied Yield", "formula": "[Custom SQL/implied_yield]", "format": PCT1},
        {"id": "p-api-noi", "name": "Buildium API NOI", "formula": "[Custom SQL/api_noi]", "format": MONEY0},
        {"id": "p-nav-check", "name": "NAV Tracker", "formula": "[Custom SQL/nav_tracker_value]", "format": MONEY0},
        {"id": "p-debt-check", "name": "Mortgage Control", "formula": "[Custom SQL/control_debt]", "format": MONEY0},
        {"id": "p-noi-delta", "name": "NOI Delta", "formula": "[Custom SQL/noi_tie_delta]", "format": MONEY0},
        {"id": "p-value-delta", "name": "Value Delta", "formula": "[Custom SQL/value_tie_delta]", "format": MONEY0},
        {"id": "p-debt-delta", "name": "Debt Delta", "formula": "[Custom SQL/debt_tie_delta]", "format": MONEY0},
        {"id": "p-tie", "name": "Tie Status", "formula": "[Custom SQL/tie_status]"},
        {"id": "p-break", "name": "Break Reason", "formula": "[Custom SQL/break_reason]"},
    ])

    sql_table("src-capex", CAPEXT, capex_sql(), [
        {"id": "c-id", "name": "Transaction ID", "formula": "[Custom SQL/transaction_id]"},
        {"id": "c-pid", "name": "Buildium ID", "formula": "[Custom SQL/buildium_id]"},
        {"id": "c-property", "name": "Property", "formula": "[Custom SQL/property_name]"},
        {"id": "c-date", "name": "Posted Date", "formula": "[Custom SQL/posted_date]"},
        {"id": "c-desc", "name": "Description", "formula": "[Custom SQL/description]"},
        {"id": "c-amount", "name": "Amount", "formula": "[Custom SQL/amount]", "format": MONEY0},
        {"id": "c-auto", "name": "Auto Class", "formula": "[Custom SQL/auto_class]"},
        {"id": "c-reason", "name": "Rule Reason", "formula": "[Custom SQL/rule_reason]"},
    ])

    sql_table("src-bridge", "NAV Bridge Steps", bridge_sql(), [
        {"id": "b-order", "name": "Step Order", "formula": "[Custom SQL/step_order]", "format": NUM0},
        {"id": "b-label", "name": "Step", "formula": "[Custom SQL/step_label]"},
        {"id": "b-amount", "name": "Amount", "formula": "[Custom SQL/amount]", "format": MONEY0},
    ])

    sql_table("src-tabs", "Decision Tab Lineage", TAB_SQL, [
        {"id": "t-num", "name": "#", "formula": "[Custom SQL/tab_number]", "format": NUM0},
        {"id": "t-name", "name": "Decision Tab", "formula": "[Custom SQL/tab_name]"},
        {"id": "t-group", "name": "Decision Group", "formula": "[Custom SQL/decision_group]"},
        {"id": "t-source", "name": "Direct Source", "formula": "[Custom SQL/direct_source]"},
    ])

    # =====================================================================
    # PAGE 1 - What is the REIT worth, and can I trust it?
    # =====================================================================
    header(1, "What is the REIT worth?")
    scope("scope-1")
    list_control("ctrl-holding", "Holding", "Holding", "src-property", "p-holding")
    list_control("ctrl-hood", "Hood", "Neighborhood", "src-property", "p-hood")

    kpi("kpi-nav", "src-property", "REIT net asset value",
        f"Sum([{PROP}/REIT Equity])", f"Sum([{PROP}/REIT Value])", MONEY,
        INK, "REIT gross value")
    # The rule that moves the most money gets a number, not just a caption.
    kpi("kpi-jv", "src-property", "NAV protected by equity method",
        f'Sum(If([{PROP}/Accounting Treatment] = "Equity method - in-LLC debt excluded", '
        f'[{PROP}/Debt] * [{PROP}/REIT %], 0))',
        "0", MONEY, WARN, "If naively pro-rated")
    kpi("kpi-noi", "src-property", "Raw TTM NOI - REIT share",
        f"Sum([{PROP}/REIT NOI])", f"Sum([{PROP}/Raw NOI])", MONEY,
        INK, "NOI at 100%")
    kpi("kpi-ltv", "src-property", "Look-through LTV",
        f"Sum([{PROP}/REIT Debt]) / Sum([{PROP}/REIT Value])", "0.55", PCT1,
        WARN, "Policy ceiling", invert=True)

    # the hero: NAV bridge, with the equity-method step as its own bar
    add({"id": "chart-bridge", "kind": "waterfall-chart",
         "name": "How $1.25B of property becomes $466M of REIT NAV",
         "source": {"kind": "table", "elementId": "src-bridge"},
         "columns": [
             {"id": "bw-label", "name": "Step", "formula": "[NAV Bridge Steps/Step]"},
             {"id": "bw-amount", "name": "Amount", "formula": f"Sum([NAV Bridge Steps/Amount])", "format": MONEY},
             {"id": "bw-order", "name": "Order", "formula": f"Min([NAV Bridge Steps/Step Order])", "format": NUM0},
         ],
         # orientation is accepted here but has no effect on waterfall-chart
         "total": {"label": "REIT NAV"},
         "xAxis": {"columnId": "bw-label", "sort": {"by": "bw-order", "aggregation": "min", "direction": "ascending"}},
         "yAxis": {"columnIds": ["bw-amount"]},
         "legend": {"visibility": "hidden"},
         "style": panel()})
    # concentration - only meaningful because there are 150 properties
    add({"id": "chart-conc", "kind": "bar-chart",
         "name": "REIT NAV by holding",
         "source": {"kind": "table", "elementId": "src-property"},
         "columns": [
             {"id": "cc-hold", "name": "Holding", "formula": f"[{PROP}/Holding]"},
             {"id": "cc-eq", "name": "REIT Equity", "formula": f"Sum([{PROP}/REIT Equity])", "format": MONEY},
             {"id": "cc-color", "name": "Shade", "formula": f"Sum([{PROP}/REIT Equity])", "format": MONEY},
         ],
         "color": {"by": "scale", "column": "cc-color", "scheme": [GREEN, GREEN],
                   "domain": {"min": 0, "max": 130000000}},
         "orientation": "horizontal",
         "xAxis": {"columnId": "cc-hold", "sort": {"by": "cc-eq", "aggregation": "sum", "direction": "descending"}},
         "yAxis": {"columnIds": ["cc-eq"]},
         "legend": {"visibility": "hidden"},
         "style": panel()})

    add({"id": "tbl-holdings", "kind": "table",
         "name": "Holdings roll-up - seven LLCs, 150 properties",
         "source": {"kind": "table", "elementId": "src-property"},
         "columns": [
             {"id": "h-hold", "name": "Holding", "formula": f"[{PROP}/Holding]"},
             {"id": "h-count", "name": "Properties", "formula": f"CountDistinct([{PROP}/Buildium ID])", "format": NUM0},
             {"id": "h-units", "name": "Units", "formula": f"Sum([{PROP}/Units])", "format": NUM0},
             {"id": "h-own", "name": "REIT %", "formula": f"Max([{PROP}/REIT %])", "format": PCT1},
             {"id": "h-value", "name": "100% Value", "formula": f"Sum([{PROP}/Approved Value])", "format": MONEY},
             {"id": "h-debt", "name": "100% Debt", "formula": f"Sum([{PROP}/Debt])", "format": MONEY},
             {"id": "h-rv", "name": "REIT Value", "formula": f"Sum([{PROP}/REIT Value])", "format": MONEY},
             {"id": "h-rd", "name": "REIT Debt", "formula": f"Sum([{PROP}/REIT Debt])", "format": MONEY},
             {"id": "h-re", "name": "REIT Equity", "formula": f"Sum([{PROP}/REIT Equity])", "format": MONEY},
             {"id": "h-noi", "name": "REIT NOI", "formula": f"Sum([{PROP}/REIT NOI])", "format": MONEY},
             {"id": "h-treat", "name": "Treatment", "formula": f"Max([{PROP}/Accounting Treatment])"},
         ],
         "groupings": [{"id": "h-grp", "groupBy": ["h-hold"],
                        "calculations": ["h-count", "h-units", "h-own", "h-value", "h-debt",
                                         "h-rv", "h-rd", "h-re", "h-noi", "h-treat"]}],
         "conditionalFormats": [
             {"type": "single", "columnIds": ["h-treat"], "condition": "formula",
              "formula": f'Contains([{PROP}/Accounting Treatment], "Equity method")',
              "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
         ],
         "tableComponents": {"summaryBar": "shown"},
         "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal"},
         "style": panel()})

    agent("agent-nav", "NAV & Accounting Copilot", "pg-worth",
          "You are a REIT accounting analyst for the Groma NAV REIT cockpit. You answer questions "
          "about net asset value, the NAV bridge, raw TTM NOI, leverage and per-property ownership "
          "from the Layer 1 property book of 150 properties across seven holdings. When a number "
          "looks surprising, name the property and the one accounting rule that produced it." + RULES + GUARD,
          "Ask me about REIT NAV, the bridge, NOI or leverage. Try \"Why is Seaport Residential JV's "
          "REIT debt zero?\", \"Which holding carries the most REIT equity?\", or \"What would NAV be "
          "if the JV debt were pro-rated?\"",
          ["src-property", "src-bridge"])

    # =====================================================================
    # PAGE 2 - Which buildings need me this quarter?
    # =====================================================================
    header(2, "Which buildings need me this quarter?")
    scope("scope-2")
    list_control("ctrl-hood2", "Hood2", "Neighborhood", "src-property", "p-hood")
    list_control("ctrl-maturity", "Maturity", "Maturity", "src-property", "p-maturity")
    list_control("ctrl-margin-flag", "MarginFlag", "Cohort position", "src-property", "p-margin-flag")

    kpi("kpi-below", "src-property", "Below neighborhood cohort",
        f"CountDistinct(If([{PROP}/Margin Flag] = \"Below cohort\", [{PROP}/Buildium ID], null))",
        f"CountDistinct([{PROP}/Buildium ID])", NUM0, WARN, "Properties", invert=True)
    kpi("kpi-over", "src-property", "Recurring capex over budget",
        f"CountDistinct(If([{PROP}/Budget Flag] = \"Over budget\", [{PROP}/Buildium ID], null))",
        f"CountDistinct([{PROP}/Buildium ID])", NUM0, WARN, "Properties", invert=True)
    kpi("kpi-leaseup", "src-property", "Still in lease-up",
        f"CountDistinct(If([{PROP}/Maturity] = \"Lease-up\", [{PROP}/Buildium ID], null))",
        f"CountDistinct([{PROP}/Buildium ID])", NUM0, INK, "Properties")
    kpi("kpi-review", "src-property", "Failing a tie-out",
        f"CountDistinct(If([{PROP}/Tie Status] = \"Review\", [{PROP}/Buildium ID], null))",
        "0", NUM0, BAD, "Target", invert=True)

    # Bespoke plugin: Sigma has no treemap kind, so this is genuinely not
    # expressible natively - and it is this page's argument, not decoration.
    # Area = REIT equity, colour = gap to that property's OWN neighbourhood
    # cohort, which is the comparison the whole page is built on.
    add({"id": "plg-treemap", "kind": "plugin",
         "pluginId": "9a060e72-6678-4abd-8705-a8bd2dc1cd02",
         "displayName": "The whole book by neighbourhood",
         "config": {
             "source": {"kind": "element", "elementId": "src-property"},
             "property": "p-name",
             "neighborhood": "p-hood",
             "equity": "p-reit-equity",
             "gap": "p-gap",
             "margin": "p-margin",
         },
         "style": {"backgroundColor": WHITE}})

    add({"id": "tbl-attention", "kind": "table",
         "name": "Action queue - widest negative gap to neighborhood cohort first",
         "source": {"kind": "table", "elementId": "src-property"},
         "columns": [
             {"id": "a-name", "name": "Property", "formula": f"[{PROP}/Property]"},
             {"id": "a-hood", "name": "Neighborhood", "formula": f"[{PROP}/Neighborhood]"},
             {"id": "a-hold", "name": "Holding", "formula": f"[{PROP}/Holding]"},
             {"id": "a-units", "name": "Units", "formula": f"[{PROP}/Units]", "format": NUM0},
             {"id": "a-margin", "name": "NOI Margin", "formula": f"[{PROP}/NOI Margin]", "format": PCT1},
             {"id": "a-hoodm", "name": "Cohort Avg", "formula": f"[{PROP}/Neighborhood Avg Margin]", "format": PCT1},
             {"id": "a-gap", "name": "Gap", "formula": f"[{PROP}/Margin Gap vs Cohort]", "format": PCT1},
             {"id": "a-noi", "name": "Raw NOI", "formula": f"[{PROP}/Raw NOI]", "format": MONEY},
             {"id": "a-capex", "name": "Recurring Capex", "formula": f"[{PROP}/Recurring Capex]", "format": MONEY},
             {"id": "a-headroom", "name": "Budget Headroom", "formula": f"[{PROP}/Budget Headroom]", "format": MONEY},
             {"id": "a-mat", "name": "Maturity", "formula": f"[{PROP}/Maturity]"},
             {"id": "a-treat", "name": "Treatment", "formula": f"[{PROP}/Accounting Treatment]"},
         ],
         "sort": [{"columnId": "a-gap", "direction": "ascending", "nulls": "last"}],
         "conditionalFormats": [
             {"type": "single", "columnIds": ["a-gap"], "condition": "<", "value": -0.05,
              "style": {"backgroundColor": "#F8DFDC", "color": BAD, "bold": True}},
             {"type": "single", "columnIds": ["a-headroom"], "condition": "<", "value": 0,
              "style": {"backgroundColor": "#F8DFDC", "color": BAD, "bold": True}},
             {"type": "single", "columnIds": ["a-treat"], "condition": "formula",
              "formula": f'Not(Contains([{PROP}/Accounting Treatment], "Consolidated")) Or Contains([{PROP}/Accounting Treatment], "master rent")',
              "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
         ],
         "tableComponents": {"summaryBar": "hidden"},
         "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                        "gridLines": "horizontal", "banding": "shown", "bandingColor": CREAM},
         "style": panel()})

    agent("agent-port", "Portfolio Copilot", "pg-attention",
          "You are an asset-management analyst for the Groma NAV REIT cockpit, working across 150 "
          "properties in twelve neighborhoods. Your job is triage: surface the small number of "
          "buildings that need a decision this quarter and say why, using the neighborhood cohort "
          "as the comparison rather than the portfolio average. Always name properties and give the "
          "gap in points." + RULES + GUARD,
          "Ask me which buildings need attention. Try \"Which five properties are furthest below "
          "their neighborhood cohort?\", \"Which assets are over their recurring capex budget?\", or "
          "\"Are the lease-up assets dragging margin?\"",
          ["src-property"])

    # =====================================================================
    # PAGE 3 - Decide and commit (write-back)
    # =====================================================================
    header(3, "Decide and commit")
    scope("scope-3")

    add({"id": "ctrl-scenario", "kind": "control", "controlId": "Scenario",
         "name": "Management scenario", "controlType": "segmented",
         "source": {"kind": "manual", "valueType": "text",
                    "values": ["Current Plan", "Lease-up Upside", "Cost Pressure"]},
         "value": "Current Plan"})
    add({"id": "ctrl-comment", "kind": "control", "controlId": "Comment",
         "name": "Workflow comment", "controlType": "text-area"})

    add({"id": "it-budget", "kind": "input-table", # NOTE: this element's name is also its formula reference key
         # (BUD below, and the three KPIs). Do not decorate it.
         "name": "Live Property Budget",
         "source": {"kind": "linked", "from": "src-property"},
         "inputMode": "view",
         "columns": [
             # passthrough from the linked source: {"key": "<source column id>"}
             {"id": "ib-id", "key": "p-id"},
             {"id": "ib-name", "key": "p-name"},
             {"id": "ib-hood", "key": "p-hood"},
             {"id": "ib-noi", "key": "p-noi", "hidden": True},
             {"id": "ib-rec", "key": "p-rec-capex", "hidden": True},
             {"id": "ib-budget", "key": "p-budget", "hidden": True},
             {"id": "ib-own", "key": "p-own", "hidden": True},
             {"id": "ib-rnoi", "key": "p-reit-noi", "hidden": True},
             {"id": "ib-rvalue", "key": "p-reit-value", "hidden": True},
             # editable (peach) cells
             {"id": "ib-fnoi", "type": "number", "name": "PM Forecast NOI"},
             {"id": "ib-fcapex", "type": "number", "name": "Revised Capex Budget"},
             {"id": "ib-owner", "type": "text", "name": "Property Manager"},
             {"id": "ib-note", "type": "text", "name": "Manager Note"},
             {"id": "ib-status", "type": "text", "name": "Budget Status"},
             # derived. Blank overrides fall back to scenario-scaled actuals via
             # Coalesce, so a manager can touch one building without retyping the book.
             {"id": "ib-eff-noi", "name": "Effective Forecast NOI", "format": MONEY0,
              "formula": 'Coalesce([PM Forecast NOI], [Raw NOI] * Switch([Scenario], "Lease-up Upside", 1.06, "Cost Pressure", 0.94, 1))'},
             {"id": "ib-eff-budget", "name": "Effective Capex Budget", "format": MONEY0,
              "formula": 'Coalesce([Revised Capex Budget], [Capex Budget] * Switch([Scenario], "Lease-up Upside", 1.08, "Cost Pressure", 0.92, 1))'},
             {"id": "ib-remaining", "name": "Budget Remaining", "format": MONEY0,
              "formula": "[Effective Capex Budget] - [Recurring Capex]"},
             {"id": "ib-freit-noi", "name": "Forecast REIT NOI", "format": MONEY0,
              "formula": "[Effective Forecast NOI] * [REIT %]"},
             # REIT-share basis so it is comparable to REIT value; capitalising
             # the 100% NOI produced a $1.28B figure sitting next to a $914M
             # REIT value, which is apples to oranges.
             {"id": "ib-sens", "name": "Management Value Sensitivity", "format": MONEY0,
              "formula": '[Forecast REIT NOI] / Switch([Scenario], "Lease-up Upside", 0.0475, "Cost Pressure", 0.0575, 0.0525)'},
         ],
         "conditionalFormats": [
             {"type": "single", "columnIds": ["ib-fnoi", "ib-fcapex", "ib-owner", "ib-note", "ib-status"],
              "condition": "formula", "formula": "True", "style": {"backgroundColor": "#FFF0E8"}},
             {"type": "single", "columnIds": ["ib-remaining"], "condition": "<", "value": 0,
              "style": {"backgroundColor": "#F8DFDC", "color": BAD, "bold": True}},
         ],
         "tableComponents": {"summaryBar": "shown"},
         "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                        "gridLines": "horizontal", "banding": "shown", "bandingColor": CREAM},
         "style": panel()})

    add({"id": "it-approval", "kind": "input-table", "name": "Budget Approval History",
         "source": {"kind": "empty", "connectionId": CONNECTION_ID},
         "inputMode": "view",
         "sort": [{"columnId": "ap-at", "direction": "descending", "nulls": "last"}],
         "columns": [
             {"id": "ap-scenario", "type": "text", "name": "Scenario"},
             {"id": "ap-status", "type": "text", "name": "Status"},
             {"id": "ap-by", "type": "text", "name": "By"},
             {"id": "ap-at", "type": "datetime", "name": "At"},
             {"id": "ap-note", "type": "text", "name": "Comment"},
         ],
         "conditionalFormats": [
             {"type": "single", "columnIds": ["ap-status"], "condition": "=", "value": "Approved",
              "style": {"backgroundColor": MINT, "color": GOOD, "bold": True}},
             {"type": "single", "columnIds": ["ap-status"], "condition": "=", "value": "Submitted",
              "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
         ],
         "tableComponents": {"summaryBar": "hidden"},
         "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal"},
         "style": panel()})

    BUD = "Live Property Budget"
    kpi("kpi-fnoi", "it-budget", "Forecast REIT NOI",
        f"Sum([{BUD}/Forecast REIT NOI])", f"Sum([{BUD}/REIT NOI])", MONEY, INK, "Current TTM")
    kpi("kpi-remaining", "it-budget", "Capex budget remaining",
        f"Sum([{BUD}/Budget Remaining])", f"Sum([{BUD}/Effective Capex Budget])", MONEY,
        INK, "Effective budget")
    kpi("kpi-sens", "it-budget", "Management value sensitivity",
        f"Sum([{BUD}/Management Value Sensitivity])", f"Sum([{BUD}/REIT Value])", MONEY,
        WARN, "Approved REIT value")

    for bid, label, status, appearance in (
        ("btn-submit", "Submit budget", "Submitted", "filled"),
        ("btn-approve", "Approve budget", "Approved", "outline"),
    ):
        add({"id": bid, "kind": "button", "text": label, "appearance": appearance,
             "actions": [{"id": f"act-{bid}", "trigger": "on-click", "effects": [
                 {"effect": "insert-rows", "tableElementId": "it-approval", "values": {
                     "ap-scenario": {"type": "control", "control": "Scenario"},
                     "ap-status": {"type": "constant", "value": {"type": "text", "value": status}},
                     "ap-by": {"type": "formula", "formula": "CurrentUserEmail()"},
                     "ap-at": {"type": "formula", "formula": "Now()"},
                     "ap-note": {"type": "control", "control": "Comment"},
                 }}],
                 "successToast": {"title": f"Budget {status.lower()}", "showMessage": "shown"}}]})

    add({"id": "it-capex", "kind": "input-table", "name": "15xx capex queue — classified by nature of work, never dollar size",
         "source": {"kind": "linked", "from": "src-capex"},
         "inputMode": "view",
         "columns": [
             {"id": "ic-id", "key": "c-id"},
             {"id": "ic-prop", "key": "c-property"},
             {"id": "ic-date", "key": "c-date"},
             {"id": "ic-desc", "key": "c-desc"},
             {"id": "ic-amt", "key": "c-amount"},
             {"id": "ic-auto", "key": "c-auto"},
             {"id": "ic-reason", "key": "c-reason"},
             {"id": "ic-override", "type": "text", "name": "Manual Class Override"},
             {"id": "ic-reviewer", "type": "text", "name": "Reviewer"},
             {"id": "ic-rationale", "type": "text", "name": "Override Rationale"},
             {"id": "ic-effective", "name": "Effective Class",
              "formula": "Coalesce([Manual Class Override], [Auto Class])"},
             {"id": "ic-affo", "name": "AFFO Deduction", "format": MONEY0,
              "formula": 'If([Effective Class] = "Recurring", [Amount], 0)'},
         ],
         "conditionalFormats": [
             {"type": "single", "columnIds": ["ic-override", "ic-reviewer", "ic-rationale"],
              "condition": "formula", "formula": "True", "style": {"backgroundColor": "#FFF0E8"}},
             {"type": "single", "columnIds": ["ic-effective"], "condition": "=", "value": "Recurring",
              "style": {"backgroundColor": "#F5E5BC", "color": WARN, "bold": True}},
             {"type": "single", "columnIds": ["ic-effective"], "condition": "=", "value": "Value-add",
              "style": {"backgroundColor": MINT, "color": GOOD, "bold": True}},
         ],
         "tableComponents": {"summaryBar": "shown"},
         "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                        "gridLines": "horizontal", "banding": "shown", "bandingColor": CREAM},
         "style": panel()})
    agent("agent-budget", "Budget & Capex Copilot", "pg-decide",
          "You help property managers and asset managers commit budget and capex decisions in the "
          "Groma NAV REIT cockpit. Forecast overrides fall back to scenario-scaled actuals when "
          "blank, so a manager can touch one building without retyping the book. The value output is "
          "a management sensitivity for internal steering, never the approved quarterly mark or the "
          "external appraiser's view." + RULES + GUARD,
          "Ask me about the budget. Try \"Which properties have no PM forecast yet?\", \"What happens "
          "to REIT NOI if I raise Dudley Terrace to $650k?\", or \"Why is the $118k roof recurring?\"",
          ["src-property", "src-capex"])

    # =====================================================================
    # PAGE 4 - Prove it
    # =====================================================================
    header(4, "Prove it")
    scope("scope-4")

    kpi("kpi-tie-noi", "src-property", "NOI net tie delta",
        f"Sum([{PROP}/NOI Delta])", "0", MONEY0, INK, "Target", invert=True)
    kpi("kpi-tie-value", "src-property", "Value net tie delta",
        f"Sum([{PROP}/Value Delta])", "0", MONEY0, INK, "Target", invert=True)
    kpi("kpi-tie-debt", "src-property", "Debt net tie delta",
        f"Sum([{PROP}/Debt Delta])", "0", MONEY0, INK, "Target", invert=True)
    kpi("kpi-tie-count", "src-property", "Properties requiring review",
        f"CountDistinct(If([{PROP}/Tie Status] = \"Review\", [{PROP}/Buildium ID], null))",
        "0", NUM0, BAD, "Target", invert=True)

    add({"id": "tbl-tie", "kind": "table", "name": "Independent tie-outs - 150 properties, exceptions first",
         "source": {"kind": "table", "elementId": "src-property"},
         "columns": [
             {"id": "to-status", "name": "Status", "formula": f"[{PROP}/Tie Status]"},
             {"id": "to-name", "name": "Property", "formula": f"[{PROP}/Property]"},
             {"id": "to-noi", "name": "Workbook NOI", "formula": f"[{PROP}/Raw NOI]", "format": MONEY0},
             {"id": "to-api", "name": "Buildium API NOI", "formula": f"[{PROP}/Buildium API NOI]", "format": MONEY0},
             {"id": "to-nd", "name": "NOI Delta", "formula": f"[{PROP}/NOI Delta]", "format": MONEY0},
             {"id": "to-val", "name": "Approved Value", "formula": f"[{PROP}/Approved Value]", "format": MONEY0},
             {"id": "to-nav", "name": "NAV Tracker", "formula": f"[{PROP}/NAV Tracker]", "format": MONEY0},
             {"id": "to-debt", "name": "Loan Database", "formula": f"[{PROP}/Debt]", "format": MONEY0},
             {"id": "to-ctrl", "name": "Mortgage Control", "formula": f"[{PROP}/Mortgage Control]", "format": MONEY0},
             {"id": "to-reason", "name": "Break Reason", "formula": f"[{PROP}/Break Reason]"},
         ],
         "sort": [{"columnId": "to-status", "direction": "ascending", "nulls": "last"}],
         "conditionalFormats": [
             {"type": "single", "columnIds": ["to-status"], "condition": "=", "value": "Tied",
              "style": {"backgroundColor": MINT, "color": GOOD, "bold": True}},
             {"type": "single", "columnIds": ["to-status"], "condition": "=", "value": "Review",
              "style": {"backgroundColor": "#F8DFDC", "color": BAD, "bold": True}},
         ],
         "tableComponents": {"summaryBar": "hidden"},
         "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal"},
         "style": panel()})

    add({"id": "tbl-tabs", "kind": "table", "name": "Twenty-four decision tabs — one Layer 1 dataset, one quarterly commit",
         "source": {"kind": "table", "elementId": "src-tabs"},
         "columns": [
             {"id": "tt-num", "name": "#", "formula": "[Decision Tab Lineage/#]", "format": NUM0},
             {"id": "tt-name", "name": "Decision Tab", "formula": "[Decision Tab Lineage/Decision Tab]"},
             {"id": "tt-group", "name": "Decision Group", "formula": "[Decision Tab Lineage/Decision Group]"},
             {"id": "tt-src", "name": "Direct Source", "formula": "[Decision Tab Lineage/Direct Source]"},
         ],
         "tableComponents": {"summaryBar": "hidden"},
         "tableStyle": {"preset": "presentation", "cellSpacing": "small", "gridLines": "horizontal"},
         "style": panel()})
    agent("agent-tie", "Tie-out Copilot", "pg-prove",
          "You are a financial controls analyst for the Groma NAV REIT cockpit. Every important "
          "figure is checked against an independent second source. Agreement within $500 is Tied; "
          "anything else is Review and must be explained with both numbers and the named break "
          "reason. A divergence is a data problem to reconcile at the source, never something to "
          "patch with a constant in the workbook." + RULES + GUARD,
          "Ask me what ties and what does not. Try \"Which properties require review and why?\", "
          "\"What is the total NOI tie delta?\", or \"Confirm debt ties to the mortgage control centre.\"",
          ["src-property"])

    layout = LAYOUT
    return {"name": "Groma NAV REIT — Decision Cockpit",
            "folderId": FOLDER_ID,
            "document": {"schemaVersion": 1, "kind": "workbook",
                         "elements": elements, "agents": agents, "overlays": overlays,
                         "pages": [
                             {"id": "pg-worth", "name": "1 · Worth"},
                             {"id": "pg-attention", "name": "2 · Attention"},
                             {"id": "pg-decide", "name": "3 · Decide"},
                             {"id": "pg-prove", "name": "4 · Prove"},
                             {"id": "pg-data", "name": "Data", "visibility": "hidden"},
                         ],
                         "settings": {
                             "theme": {"overrides": {
                                 "colors": {"text": INK, "highlight": GOLD, "success": GOOD,
                                            "warning": WARN, "danger": BAD, "darkMode": "hidden"},
                                 "fonts": {"textFont": "Inter", "dataFont": "Inter"},
                                 "borderRadius": "round",
                                 "space": {"unit": "small", "showElementPadding": "shown"}}},
                         },
                         "layout": layout}}


def _hdr(i):
    return (f'  <Container elementId="hdr-{i}" type="grid" gridColumn="1 / 25" gridRow="1 / 4" '
            f'gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">\n'
            f'    <Element elementId="brand-{i}" gridColumn="1 / 4" gridRow="1 / 4"/>\n'
            f'    <Element elementId="title-{i}" gridColumn="4 / 17" gridRow="1 / 4"/>\n'
            f'    <Element elementId="nav-{i}" gridColumn="17 / 25" gridRow="1 / 4"/>\n'
            f'  </Container>')


LAYOUT = f"""<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-worth">
{_hdr(1)}
  <Element elementId="scope-1" gridColumn="1 / 25" gridRow="4 / 5"/>
  <Element elementId="ctrl-holding" gridColumn="1 / 13" gridRow="5 / 8"/>
  <Element elementId="ctrl-hood" gridColumn="13 / 25" gridRow="5 / 8"/>
  <Element elementId="kpi-nav" gridColumn="1 / 7" gridRow="8 / 16"/>
  <Element elementId="kpi-jv" gridColumn="7 / 13" gridRow="8 / 16"/>
  <Element elementId="kpi-noi" gridColumn="13 / 19" gridRow="8 / 16"/>
  <Element elementId="kpi-ltv" gridColumn="19 / 25" gridRow="8 / 16"/>
  <Element elementId="chart-bridge" gridColumn="1 / 16" gridRow="16 / 35"/>
  <Element elementId="chart-conc" gridColumn="16 / 25" gridRow="16 / 35"/>
  <Element elementId="tbl-holdings" gridColumn="1 / 19" gridRow="35 / 53"/>
  <Element elementId="chat-agent-nav" gridColumn="19 / 25" gridRow="35 / 53"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-attention">
{_hdr(2)}
  <Element elementId="scope-2" gridColumn="1 / 25" gridRow="4 / 5"/>
  <Element elementId="ctrl-hood2" gridColumn="1 / 9" gridRow="5 / 8"/>
  <Element elementId="ctrl-maturity" gridColumn="9 / 17" gridRow="5 / 8"/>
  <Element elementId="ctrl-margin-flag" gridColumn="17 / 25" gridRow="5 / 8"/>
  <Element elementId="kpi-below" gridColumn="1 / 7" gridRow="8 / 16"/>
  <Element elementId="kpi-over" gridColumn="7 / 13" gridRow="8 / 16"/>
  <Element elementId="kpi-leaseup" gridColumn="13 / 19" gridRow="8 / 16"/>
  <Element elementId="kpi-review" gridColumn="19 / 25" gridRow="8 / 16"/>
  <Element elementId="plg-treemap" gridColumn="1 / 19" gridRow="16 / 35"/>
  <Element elementId="chat-agent-port" gridColumn="19 / 25" gridRow="16 / 35"/>
  <Element elementId="tbl-attention" gridColumn="1 / 25" gridRow="35 / 59"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-decide">
{_hdr(3)}
  <Element elementId="scope-3" gridColumn="1 / 25" gridRow="4 / 5"/>
  <Element elementId="ctrl-scenario" gridColumn="1 / 10" gridRow="5 / 8"/>
  <Element elementId="ctrl-comment" gridColumn="10 / 18" gridRow="5 / 8"/>
  <Element elementId="btn-submit" gridColumn="18 / 21" gridRow="5 / 8"/>
  <Element elementId="btn-approve" gridColumn="21 / 25" gridRow="5 / 8"/>
  <Element elementId="kpi-fnoi" gridColumn="1 / 9" gridRow="8 / 16"/>
  <Element elementId="kpi-remaining" gridColumn="9 / 17" gridRow="8 / 16"/>
  <Element elementId="kpi-sens" gridColumn="17 / 25" gridRow="8 / 16"/>
  <Element elementId="it-budget" gridColumn="1 / 19" gridRow="16 / 38"/>
  <Element elementId="chat-agent-budget" gridColumn="19 / 25" gridRow="16 / 38"/>
  <Element elementId="it-approval" gridColumn="1 / 25" gridRow="38 / 48"/>
  <Element elementId="it-capex" gridColumn="1 / 25" gridRow="48 / 72"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-prove">
{_hdr(4)}
  <Element elementId="scope-4" gridColumn="1 / 25" gridRow="4 / 5"/>
  <Element elementId="kpi-tie-noi" gridColumn="1 / 7" gridRow="5 / 13"/>
  <Element elementId="kpi-tie-value" gridColumn="7 / 13" gridRow="5 / 13"/>
  <Element elementId="kpi-tie-debt" gridColumn="13 / 19" gridRow="5 / 13"/>
  <Element elementId="kpi-tie-count" gridColumn="19 / 25" gridRow="5 / 13"/>
  <Element elementId="tbl-tie" gridColumn="1 / 19" gridRow="13 / 38"/>
  <Element elementId="chat-agent-tie" gridColumn="19 / 25" gridRow="13 / 38"/>
  <Element elementId="tbl-tabs" gridColumn="1 / 25" gridRow="38 / 66"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-data">
  <Element elementId="src-property" gridColumn="1 / 13" gridRow="1 / 12"/>
  <Element elementId="src-capex" gridColumn="13 / 25" gridRow="1 / 12"/>
  <Element elementId="src-bridge" gridColumn="1 / 13" gridRow="12 / 20"/>
  <Element elementId="src-tabs" gridColumn="13 / 25" gridRow="12 / 20"/>
</Page>"""


# ---------------------------------------------------------------------------
def read_env(path: pathlib.Path) -> dict:
    values = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
    for key in ("SIGMA_BASE_URL", "SIGMA_CLIENT_ID", "SIGMA_CLIENT_SECRET"):
        if key not in values and os.environ.get(key):
            values[key] = os.environ[key]
    return values


class Api:
    def __init__(self, env):
        self.base = env["SIGMA_BASE_URL"]
        cred = base64.b64encode(
            f"{env['SIGMA_CLIENT_ID']}:{env['SIGMA_CLIENT_SECRET']}".encode()).decode()
        req = urllib.request.Request(
            self.base + "/v2/auth/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={"Authorization": "Basic " + cred,
                     "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        with urllib.request.urlopen(req, timeout=40) as r:
            self.token = json.load(r)["access_token"]

    def call(self, method, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            self.base + path, data=data, method=method,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/json", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read().decode()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:1200]}") from None
        return json.loads(raw) if raw.strip().startswith(("{", "[")) else {"raw": raw}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", type=pathlib.Path, default=pathlib.Path("/nonexistent"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    sub.add_parser("create")
    up = sub.add_parser("update")
    up.add_argument("workbook_id")
    up.add_argument("--expected-version", type=int, required=True)
    args = ap.parse_args()

    spec = build_spec()
    api = Api(read_env(args.env_file))
    if args.cmd == "verify":
        print(json.dumps(api.call("POST", "/v2/workbooks/spec/verify", spec), indent=2))
    elif args.cmd == "create":
        r = api.call("POST", "/v2/workbooks/spec", spec)
        print(json.dumps(r, indent=2))
        if r.get("workbookId"):
            (HERE / "workbook_id.txt").write_text(r["workbookId"] + "\n")
    else:
        print(json.dumps(api.call(
            "PUT", f"/v2/workbooks/{args.workbook_id}/spec",
            {"expectedVersion": args.expected_version, **spec}), indent=2))


if __name__ == "__main__":
    main()
