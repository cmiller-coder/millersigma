"""Build the ShiftKey Marketplace Control Tower in papercranestaging.

The workbook is purpose-built from the ShiftKey discovery call:

* Page 1 answers why marketplace fill is below plan, with a complete drill path
  from region -> state -> market -> facility -> credential -> shift.
* Page 2 turns the answer into governed account/supply action: ownership,
  status, notes, and review persist in a linked input table.
* Snowflake Cortex narrates the same governed metrics shown on screen.

Usage:
    python3 build_shiftkey_marketplace_control_tower.py
    python3 build_shiftkey_marketplace_control_tower.py BASE TOKEN CONNECTION_ID FOLDER_ID

Writes are refused unless the token resolves to papercranestaging. demeng is
read-only and is used only to inspect inspiration workbooks.
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request


_ARGS = sys.argv[1:]
BASE = _ARGS[0] if len(_ARGS) > 0 else os.environ.get("SIGMA_BASE_URL", "")
TOKEN = _ARGS[1] if len(_ARGS) > 1 else os.environ.get("SIGMA_API_TOKEN", "")
CONN = _ARGS[2] if len(_ARGS) > 2 else "<connection-id>"
FOLDER = _ARGS[3] if len(_ARGS) > 3 else "<folder-id>"
PAPERCRANE_ORG_ID = "8c99818a-90b3-4cae-bdb7-cf69a741171a"


# ShiftKey's live 2023 identity: exact colors are pulled from shiftkey.com CSS.
INK = "#1D2227"
GREEN = "#0ABC28"
TEAL = "#4AAE9B"
PAPER = "#F5F6F2"
CARD = "#FFFFFF"
CARD_ALT = "#F0F3EF"
RULE = "#D2D3D4"
MUTED = "#667078"
ALARM = "#C94343"
WARN = "#C98321"
GOOD = "#0B8A3A"

INT = {"kind": "number", "formatString": ",d"}
MONEY = {"kind": "number", "formatString": "$,.0f"}
MONEY1 = {"kind": "number", "formatString": "$,.1f"}
PCT1 = {"kind": "number", "formatString": ".1%"}
HOURS1 = {"kind": "number", "formatString": ".1f"}
MON = {"kind": "datetime", "formatString": "%b %Y"}


# Official ShiftKey mark. The live site serves a white SVG for dark surfaces.
LOGO_URL = "https://www.shiftkey.com/img/ui/logo-mark.svg"
try:
    req = urllib.request.Request(LOGO_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(resp.read()).decode()
except Exception:
    LOGO_URI = None


# ---------------------------------------------------------------------- data
# One row per facility x credential x daypart x month. Every dashboard metric
# and drill path comes from this table, so filters never silently stop at a
# disconnected visual.
MARKET_SQL = r"""
WITH months AS (
  SELECT SEQ4() AS m_idx,
         DATEADD('month', SEQ4(), DATE_TRUNC('month', CURRENT_DATE())) AS month_start
  FROM TABLE(GENERATOR(ROWCOUNT => 6))
),
facilities AS (
  SELECT * FROM VALUES
    ('FAC-1001','Cherry Creek Care Center','CO','Denver','Mountain','Skilled Nursing','Maya Chen',144,0.91,62),
    ('FAC-1002','Front Range Post Acute','CO','Aurora','Mountain','Post Acute','Maya Chen',128,0.76,48),
    ('FAC-1003','Sonoran Senior Living','AZ','Phoenix','Mountain','Assisted Living','Jordan Ellis',122,0.84,53),
    ('FAC-1004','Silver State Rehabilitation','NV','Las Vegas','Mountain','Rehabilitation','Jordan Ellis',106,0.88,49),
    ('FAC-2001','Cedar Creek Skilled Nursing','TX','Dallas–Fort Worth','South Central','Skilled Nursing','Priya Shah',168,0.75,58),
    ('FAC-2002','Trinity Senior Care','TX','Dallas–Fort Worth','South Central','Assisted Living','Priya Shah',136,0.87,64),
    ('FAC-2003','Hill Country Recovery','TX','Austin','South Central','Post Acute','Marcus Reed',118,0.92,61),
    ('FAC-2004','Red River Rehabilitation','OK','Oklahoma City','South Central','Rehabilitation','Marcus Reed',94,0.93,55),
    ('FAC-3001','Lakeshore Senior Care','IL','Chicago','Midwest','Skilled Nursing','Nina Patel',152,0.85,59),
    ('FAC-3002','Gateway Post Acute','MO','St. Louis','Midwest','Post Acute','Nina Patel',126,0.90,60),
    ('FAC-3003','Twin Cities Transitional Care','MN','Minneapolis','Midwest','Rehabilitation','Evan Brooks',108,0.94,67),
    ('FAC-3004','Buckeye Assisted Living','OH','Columbus','Midwest','Assisted Living','Evan Brooks',98,0.96,69),
    ('FAC-4001','Peachtree Rehabilitation','GA','Atlanta','Southeast','Rehabilitation','Lena Ortiz',132,0.82,52),
    ('FAC-4002','Cumberland Care Center','TN','Nashville','Southeast','Skilled Nursing','Lena Ortiz',124,0.89,57),
    ('FAC-4003','Queen City Senior Living','NC','Charlotte','Southeast','Assisted Living','Theo Martin',112,0.93,65),
    ('FAC-4004','Gulf Coast Health Center','FL','Tampa','Southeast','Post Acute','Theo Martin',146,0.86,56)
  AS f(facility_id, facility, state, market, region, facility_type,
       account_owner, base_demand, base_fill, supply_base)
),
credentials AS (
  SELECT * FROM VALUES
    ('CNA',0.42,31.0,23.0,1.00,0.00),
    ('LPN',0.28,48.0,36.0,0.78,-0.035),
    ('RN',0.20,72.0,56.0,0.56,-0.075),
    ('CMA',0.10,34.0,25.0,0.82,-0.020)
  AS c(credential, demand_share, bill_rate, payout_rate, supply_factor, fill_adjust)
),
dayparts AS (
  SELECT * FROM VALUES
    ('Day',0.44,0.020),('Evening',0.33,-0.010),('Night',0.23,-0.065)
  AS d(daypart, demand_share, fill_adjust)
),
raw AS (
  SELECT
    f.facility_id || '|' || c.credential || '|' || d.daypart || '|'
      || TO_VARCHAR(m.month_start,'YYYYMM') AS activity_key,
    m.month_start, m.m_idx,
    f.facility_id, f.facility, f.state, f.market, f.region, f.facility_type,
    f.account_owner, c.credential, d.daypart,
    ROUND(f.base_demand * c.demand_share * d.demand_share
          * (1 + 0.025 * m.m_idx)) AS posted_shifts,
    0.90 AS target_fill_rate,
    LEAST(0.97, GREATEST(0.52,
      f.base_fill + c.fill_adjust + d.fill_adjust + 0.007 * m.m_idx
      + (MOD(ABS(HASH(f.facility_id || c.credential || TO_VARCHAR(m.m_idx))),7)-3)/200.0
    )) AS actual_fill_rate,
    c.bill_rate * (1 + 0.008 * m.m_idx) AS bill_rate,
    c.payout_rate * (1 + 0.006 * m.m_idx) AS payout_rate,
    ROUND(f.supply_base * c.supply_factor
          * (1 + (MOD(ABS(HASH(f.facility_id || c.credential)),5)-2)/20.0)) AS professional_supply
  FROM months m
  CROSS JOIN facilities f
  CROSS JOIN credentials c
  CROSS JOIN dayparts d
),
calc AS (
  SELECT *,
    ROUND(posted_shifts * actual_fill_rate) AS filled_shifts,
    ROUND(posted_shifts * target_fill_rate) AS budget_filled_shifts,
    ROUND(0.35 + professional_supply / NULLIF(posted_shifts * 1.6,0), 2) AS bid_depth,
    ROUND(6 + (1-actual_fill_rate)*76 + IFF(daypart='Night',7,0),1) AS time_to_fill_hours,
    LEAST(0.18, GREATEST(0.015, 0.035 + (0.86-actual_fill_rate)/4
      + IFF(daypart='Night',0.018,0))) AS late_cancel_rate
  FROM raw
)
SELECT
  activity_key, month_start, facility_id, facility, state, market, region,
  facility_type, account_owner, credential, daypart,
  posted_shifts, filled_shifts, budget_filled_shifts,
  posted_shifts - filled_shifts AS unfilled_shifts,
  actual_fill_rate, target_fill_rate, bid_depth, time_to_fill_hours,
  late_cancel_rate, professional_supply, bill_rate, payout_rate,
  filled_shifts * 8 * bill_rate AS actual_revenue,
  budget_filled_shifts * 8 * bill_rate AS budget_revenue,
  filled_shifts * 8 * (bill_rate - payout_rate) AS gross_profit,
  (posted_shifts - filled_shifts) * 8 * bill_rate AS open_shift_exposure,
  IFF(actual_fill_rate < target_fill_rate - 0.10, 'Critical',
      IFF(actual_fill_rate < target_fill_rate - 0.05, 'Watch', 'On plan')) AS risk_tier,
  IFF(MOD(ABS(HASH(activity_key)),10) < 4, TRUE, FALSE) AS sami_assisted
FROM calc
""".strip()


FACILITY_SQL = """
SELECT
  facility_id, facility, state, market, region, facility_type, account_owner,
  SUM(posted_shifts) AS posted_shifts,
  SUM(filled_shifts) AS filled_shifts,
  SUM(budget_filled_shifts) AS budget_filled_shifts,
  SUM(unfilled_shifts) AS unfilled_shifts,
  SUM(filled_shifts) / NULLIF(SUM(posted_shifts),0) AS fill_rate,
  SUM(budget_filled_shifts) / NULLIF(SUM(posted_shifts),0) AS target_fill_rate,
  AVG(bid_depth) AS bid_depth,
  AVG(time_to_fill_hours) AS time_to_fill_hours,
  AVG(late_cancel_rate) AS late_cancel_rate,
  SUM(actual_revenue) AS actual_revenue,
  SUM(budget_revenue) AS budget_revenue,
  SUM(actual_revenue) - SUM(budget_revenue) AS revenue_variance,
  SUM(gross_profit) AS gross_profit,
  SUM(open_shift_exposure) AS open_shift_exposure,
  CASE
    WHEN SUM(filled_shifts)/NULLIF(SUM(posted_shifts),0)
         < SUM(budget_filled_shifts)/NULLIF(SUM(posted_shifts),0) - 0.10 THEN 'Critical'
    WHEN SUM(filled_shifts)/NULLIF(SUM(posted_shifts),0)
         < SUM(budget_filled_shifts)/NULLIF(SUM(posted_shifts),0) - 0.05 THEN 'Watch'
    ELSE 'On plan'
  END AS risk_tier,
  CASE
    WHEN AVG(bid_depth) < 0.75 THEN 'Activate credential-ready supply'
    WHEN AVG(time_to_fill_hours) > 18 THEN 'Review rate and posting lead time'
    WHEN AVG(late_cancel_rate) > 0.07 THEN 'Review cancellation pattern'
    ELSE 'Monitor account'
  END AS recommended_action
FROM (%s) activity
GROUP BY facility_id, facility, state, market, region, facility_type, account_owner
""".strip() % MARKET_SQL


SUPPLY_SQL = """
SELECT
  region, state, market, credential,
  SUM(posted_shifts) AS posted_shifts,
  SUM(filled_shifts) AS filled_shifts,
  SUM(unfilled_shifts) AS open_shifts,
  SUM(professional_supply) / 18 AS credential_ready_supply,
  AVG(bid_depth) AS bid_depth,
  AVG(time_to_fill_hours) AS time_to_fill_hours,
  SUM(filled_shifts)/NULLIF(SUM(posted_shifts),0) AS fill_rate,
  CASE
    WHEN SUM(filled_shifts)/NULLIF(SUM(posted_shifts),0) < 0.78 THEN 'Activate now'
    WHEN AVG(bid_depth) < 1.00 THEN 'Build bid depth'
    ELSE 'Balanced'
  END AS supply_status
FROM (%s) activity
GROUP BY region, state, market, credential
""".strip() % MARKET_SQL


# One row per account manager. Governed marketplace economics come from
# MARKET_SQL; the *scenarios* themselves are user-created rows in the
# `it-scenario-reg` input table, cross-joined onto this baseline. That is what
# makes "create a new scenario" a real user action instead of a fixed list
# hard-coded in SQL. Defaults below only feed the empty-registry fallback.
COMMISSION_SQL = """
WITH activity AS (%s),
facility_perf AS (
  SELECT
    account_owner, region, facility_id,
    SUM(gross_profit) AS gross_profit,
    SUM(actual_revenue) AS actual_revenue,
    SUM(filled_shifts) AS filled_shifts,
    SUM(posted_shifts) AS posted_shifts,
    SUM(budget_filled_shifts) AS budget_filled_shifts
  FROM activity
  GROUP BY account_owner, region, facility_id
),
reps AS (
  SELECT
    account_owner,
    MIN(region) AS primary_region,
    SUM(gross_profit) AS commissionable_gross_profit,
    SUM(actual_revenue) AS actual_revenue,
    SUM(filled_shifts) / NULLIF(SUM(posted_shifts),0) AS fill_rate,
    COUNT(DISTINCT facility_id) AS facilities,
    COUNT(DISTINCT IFF(
      filled_shifts/NULLIF(posted_shifts,0)
      < budget_filled_shifts/NULLIF(posted_shifts,0) - 0.10,
      facility_id, NULL)) AS critical_facilities
  FROM facility_perf
  GROUP BY account_owner
)
SELECT
  r.account_owner, r.primary_region,
  r.commissionable_gross_profit, r.actual_revenue, r.fill_rate,
  r.facilities, r.critical_facilities,
  ROUND(85000 + MOD(ABS(HASH(r.account_owner)),45000)) AS quota_basis,
  0.80 AS base_tier_1_limit,
  1.00 AS base_tier_2_limit,
  0.030 AS default_tier_1_rate,
  0.050 AS default_tier_2_rate,
  0.080 AS default_tier_3_rate,
  1.00 AS default_quality_modifier
FROM reps r
""".strip() % MARKET_SQL


# Month grain of the same governed economics, for the "scenario impact over time"
# surface. Monthly quota is the annual basis spread across the six months in the
# window, so monthly attainment is comparable to the annual view.
COMMISSION_MONTH_SQL = """
WITH activity AS (%s),
rep_month AS (
  SELECT
    account_owner,
    DATE_TRUNC('month', month_start) AS month_start,
    SUM(gross_profit) AS gross_profit,
    SUM(actual_revenue) AS actual_revenue,
    SUM(filled_shifts) / NULLIF(SUM(posted_shifts),0) AS fill_rate,
    SUM(posted_shifts) AS posted_shifts,
    SUM(filled_shifts) AS filled_shifts
  FROM activity
  GROUP BY account_owner, DATE_TRUNC('month', month_start)
),
months AS (SELECT COUNT(DISTINCT month_start) AS n FROM rep_month)
SELECT
  m.account_owner, m.month_start, m.gross_profit, m.actual_revenue,
  m.fill_rate, m.posted_shifts, m.filled_shifts,
  ROUND((85000 + MOD(ABS(HASH(m.account_owner)),45000)) / (SELECT n FROM months))
    AS monthly_quota_basis
FROM rep_month m
""".strip() % MARKET_SQL


elements = []
add = elements.append


def col(cid, name, alias, fmt=None, hidden=False):
    out = {"id": cid, "name": name, "formula": "[Custom SQL/%s]" % alias}
    if fmt:
        out["format"] = fmt
    if hidden:
        out["hidden"] = True
    return out


def sql_table(eid, name, statement, columns):
    return {
        "id": eid, "kind": "table", "name": name, "visibleAsSource": True,
        "source": {"kind": "sql", "connectionId": CONN, "statement": statement},
        "columns": columns,
        "tableComponents": {"summaryBar": "hidden"},
        "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                       "gridLines": "horizontal",
                       "textStyles": {"header": {"fontWeight": "bold"}}},
    }


# ------------------------------------------------------------------- theming
# A section band: centered white bold title on a brand-coloured bar. This is how
# the Summit commission app separates its outcome surfaces, and it reads far
# better than a small-caps grey label floating above a table.
#
# ⚠️ A text element's own `style.backgroundColor` is NOT rendered — verified by
# pixel-inspecting a PNG export, where the band rows came back as page
# background and the white title was invisible. The colour has to come from a
# CONTAINER wrapping the text (which is how the Summit app does it), so every
# band records its colour here and gets a wrapper generated into the layout.
BAND_COLORS = {}


def band(eid, title, color=INK):
    BAND_COLORS[eid] = color
    return {
        "id": eid, "kind": "text",
        "body": '<p class="p-large" style="text-align: center">'
                '<span style="color: #FFFFFF">**%s**</span></p>' % title,
        "style": {"backgroundColor": "transparent", "padding": "none"},
        "verticalAlign": "middle",
    }


def table_theme(header_bg=CARD_ALT, cell_align="right", divider=GREEN):
    """Presentation table styling: tinted centered title, bold column headers,
    a brand divider under the header, and banding for row tracking."""
    return {
        "preset": "presentation", "cellSpacing": "small", "banding": "shown",
        "bandingColor": "#FAFBFA", "headerDividerColor": divider,
        "textStyles": {
            "header": {"fontSize": 14, "backgroundColor": header_bg,
                       "align": "center", "fontWeight": "bold"},
            "columnHeader": {"fontWeight": "bold", "backgroundColor": header_bg},
            "rowHeader": {"fontWeight": "bold", "backgroundColor": header_bg},
            "cell": {"fontSize": 13, "align": cell_align},
        },
    }


# Nine-stop scale for rate/intensity columns (the Summit heatmap treatment).
GREEN_SCALE = ["#EAF8EC", "#D2F0D8", "#B6E7C3", "#95DCAB", "#6FCE90",
               "#48BE74", "#2AA95C", "#158C47", "#0B6E36"]


def scale_cf(column_ids, scheme=None):
    return {"type": "backgroundScale", "columnIds": column_ids,
            "scheme": scheme or GREEN_SCALE, "includeValues": True}


add(sql_table("sql-market", "Marketplace Activity", MARKET_SQL, [
    col("ma-key", "Activity Key", "activity_key", hidden=True),
    col("ma-month", "Month", "month_start", MON),
    col("ma-fid", "Facility ID", "facility_id"),
    col("ma-fac", "Facility", "facility"),
    col("ma-state", "State", "state"),
    col("ma-market", "Market", "market"),
    col("ma-region", "Region", "region"),
    col("ma-ftype", "Facility Type", "facility_type"),
    col("ma-owner", "Account Owner", "account_owner"),
    col("ma-cred", "Credential", "credential"),
    col("ma-day", "Shift", "daypart"),
    col("ma-post", "Posted Shifts", "posted_shifts", INT),
    col("ma-fill", "Filled Shifts", "filled_shifts", INT),
    col("ma-bfill", "Plan Filled Shifts", "budget_filled_shifts", INT),
    col("ma-open", "Unfilled Shifts", "unfilled_shifts", INT),
    col("ma-fr", "Fill Rate", "actual_fill_rate", PCT1),
    col("ma-target", "Plan Fill Rate", "target_fill_rate", PCT1),
    col("ma-bid", "Bid Depth", "bid_depth"),
    col("ma-ttf", "Time to Fill", "time_to_fill_hours", HOURS1),
    col("ma-cancel", "Late Cancel Rate", "late_cancel_rate", PCT1),
    col("ma-supply", "Credential-Ready Supply", "professional_supply", INT),
    col("ma-bill", "Facility Bill Rate", "bill_rate", MONEY1),
    col("ma-pay", "Professional Payout", "payout_rate", MONEY1),
    col("ma-rev", "Actual Revenue", "actual_revenue", MONEY),
    col("ma-brev", "Plan Revenue", "budget_revenue", MONEY),
    col("ma-gp", "Gross Profit", "gross_profit", MONEY),
    col("ma-exposure", "Open Shift Exposure", "open_shift_exposure", MONEY),
    col("ma-risk", "Risk Tier", "risk_tier"),
    col("ma-sami", "SAMI Assisted", "sami_assisted"),
]))

add(sql_table("sql-facility", "Facility Performance", FACILITY_SQL, [
    col("fp-id", "Facility ID", "facility_id"),
    col("fp-fac", "Facility", "facility"),
    col("fp-state", "State", "state"),
    col("fp-market", "Market", "market"),
    col("fp-region", "Region", "region"),
    col("fp-type", "Facility Type", "facility_type"),
    col("fp-owner", "Account Owner", "account_owner"),
    col("fp-post", "Posted Shifts", "posted_shifts", INT),
    col("fp-fill", "Filled Shifts", "filled_shifts", INT),
    col("fp-bfill", "Plan Filled Shifts", "budget_filled_shifts", INT),
    col("fp-open", "Unfilled Shifts", "unfilled_shifts", INT),
    col("fp-fr", "Fill Rate", "fill_rate", PCT1),
    col("fp-target", "Plan Fill Rate", "target_fill_rate", PCT1),
    col("fp-bid", "Bid Depth", "bid_depth"),
    col("fp-ttf", "Time to Fill", "time_to_fill_hours", HOURS1),
    col("fp-cancel", "Late Cancel Rate", "late_cancel_rate", PCT1),
    col("fp-rev", "Actual Revenue", "actual_revenue", MONEY),
    col("fp-brev", "Plan Revenue", "budget_revenue", MONEY),
    col("fp-var", "Revenue Variance", "revenue_variance", MONEY),
    col("fp-gp", "Gross Profit", "gross_profit", MONEY),
    col("fp-exp", "Open Shift Exposure", "open_shift_exposure", MONEY),
    col("fp-risk", "Risk Tier", "risk_tier"),
    col("fp-reco", "Recommended Action", "recommended_action"),
]))

_supply_table = sql_table("sql-supply", "Supply Coverage", SUPPLY_SQL, [
    col("sc-region", "Region", "region"),
    col("sc-state", "State", "state"),
    col("sc-market", "Market", "market"),
    col("sc-cred", "Credential", "credential"),
    col("sc-post", "Posted Shifts", "posted_shifts", INT),
    col("sc-fill", "Filled Shifts", "filled_shifts", INT),
    col("sc-open", "Open Shifts", "open_shifts", INT),
    col("sc-pros", "Credential-Ready Supply", "credential_ready_supply", INT),
    col("sc-bid", "Bid Depth", "bid_depth"),
    col("sc-ttf", "Time to Fill", "time_to_fill_hours", HOURS1),
    col("sc-fr", "Fill Rate", "fill_rate", PCT1),
    col("sc-status", "Supply Status", "supply_status"),
])
_supply_table["conditionalFormats"] = [
    {"type": "dataBars", "columnIds": ["sc-fr"], "scheme": [GREEN, CARD_ALT]},
    {"type": "single", "columnIds": ["sc-status"], "condition": "formula",
     "formula": '[Supply Status] = "Activate now"',
     "style": {"backgroundColor": "#FCE8E8", "color": ALARM}},
    {"type": "single", "columnIds": ["sc-status"], "condition": "formula",
     "formula": '[Supply Status] = "Build bid depth"',
     "style": {"backgroundColor": "#FFF3DF", "color": WARN}},
    {"type": "single", "columnIds": ["sc-status"], "condition": "formula",
     "formula": '[Supply Status] = "Balanced"',
     "style": {"backgroundColor": "#E8F7EC", "color": GOOD}},
]
add(_supply_table)

add(sql_table("sql-commission", "Commission AM Base", COMMISSION_SQL, [
    col("cb-owner", "Account Manager", "account_owner"),
    col("cb-region", "Primary Region", "primary_region"),
    col("cb-gp", "Commissionable Gross Profit", "commissionable_gross_profit", MONEY),
    col("cb-rev", "Actual Revenue", "actual_revenue", MONEY),
    col("cb-fill", "Fill Rate", "fill_rate", PCT1),
    col("cb-facs", "Facilities", "facilities", INT),
    col("cb-critical", "Critical Facilities", "critical_facilities", INT),
    col("cb-quota-basis", "Quota Basis", "quota_basis", MONEY),
    col("cb-t1lim", "Base Tier 1 Limit", "base_tier_1_limit", PCT1),
    col("cb-t2lim", "Base Tier 2 Limit", "base_tier_2_limit", PCT1),
    col("cb-t1rate-d", "Default Tier 1 Rate", "default_tier_1_rate", PCT1, hidden=True),
    col("cb-t2rate-d", "Default Tier 2 Rate", "default_tier_2_rate", PCT1, hidden=True),
    col("cb-t3rate-d", "Default Tier 3 Rate", "default_tier_3_rate", PCT1, hidden=True),
    col("cb-quality-d", "Default Quality Modifier", "default_quality_modifier",
        hidden=True),
]))

add(sql_table("sql-commission-month", "Commission AM Month", COMMISSION_MONTH_SQL, [
    col("cn-owner", "Account Manager", "account_owner"),
    col("cn-month", "Month", "month_start", MON),
    col("cn-gp", "Monthly Gross Profit", "gross_profit", MONEY),
    col("cn-rev", "Monthly Revenue", "actual_revenue", MONEY),
    col("cn-fill", "Monthly Fill Rate", "fill_rate", PCT1),
    col("cn-quota", "Monthly Quota Basis", "monthly_quota_basis", MONEY),
]))


# The scenario registry. This is an EMPTY input table, so rows only exist
# because a user (or the copilot) created them — that is the "create a new
# scenario" capability the demeng Sales Commission Modeling app has and a
# SQL-seeded scenario list cannot. Scenario-level plan assumptions and the
# finance lifecycle live here, one row per scenario.
add({
    "id": "it-scenario-reg", "kind": "input-table",
    "name": "Commission Scenario Registry", "inputMode": "view",
    "source": {"kind": "empty", "connectionId": CONN},
    "columns": [
        {"id": "rg-name", "type": "text", "name": "Scenario Name"},
        {"id": "rg-desc", "type": "text", "name": "Scenario Description"},
        {"id": "rg-order", "type": "number", "name": "Scenario Order"},
        {"id": "rg-quota-factor", "type": "number", "name": "Quota Factor"},
        {"id": "rg-t1rate", "type": "number", "name": "Tier 1 Rate"},
        {"id": "rg-t2rate", "type": "number", "name": "Tier 2 Rate"},
        {"id": "rg-t3rate", "type": "number", "name": "Tier 3 Rate"},
        {"id": "rg-quality", "type": "number", "name": "Quality Modifier"},
        {"id": "rg-status", "type": "text", "name": "Scenario Status",
         "values": ["Draft", "Submitted", "Approved", "Adjust", "Rejected"],
         "pills": "color-by-option"},
        {"id": "rg-note", "type": "text", "name": "Finance Note"},
        {"id": "rg-status-f", "name": "Workflow Status",
         "formula": 'Coalesce([Scenario Status], "Draft")'},
    ],
    "sort": [{"columnId": "rg-order", "direction": "ascending", "nulls": "last"}],
    "conditionalFormats": [
        {"type": "single",
         "columnIds": ["rg-name", "rg-desc", "rg-order", "rg-quota-factor",
                       "rg-t1rate", "rg-t2rate", "rg-t3rate", "rg-quality",
                       "rg-status", "rg-note"],
         "condition": "formula", "formula": "True",
         "style": {"backgroundColor": "#F2FFF3"}},
    ],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                   "gridLines": "horizontal", "banding": "shown",
                   "bandingColor": CARD_ALT},
})


# Cross join (1 = 1) of every account manager against every registered
# scenario. `left-outer` plus Coalesce means an empty registry still renders a
# usable "Base Plan" at governed defaults, so the page is never blank before the
# first scenario is created. Union is NOT supported by the spec API, so the
# registry has to be the single source of scenario rows.
add({
    "id": "jn-comm-calc", "kind": "table", "name": "Commission Scenario Grid",
    "visibleAsSource": True,
    "source": {"kind": "join",
               "joins": [{"left": {"elementId": "sql-commission", "kind": "table"},
                          "right": {"elementId": "it-scenario-reg", "kind": "table"},
                          "columns": [{"left": "1", "right": "1"}],
                          "joinType": "left-outer"}],
               "primarySource": {"elementId": "sql-commission", "kind": "table"}},
    "columns": [
        {"id": "jn-scenario", "name": "Scenario Name",
         "formula": 'Coalesce([Commission Scenario Registry/Scenario Name], "Base Plan")'},
        {"id": "jn-desc", "name": "Scenario Description",
         "formula": 'Coalesce([Commission Scenario Registry/Scenario Description], '
                    '"Governed default plan — create a scenario to model against it")'},
        {"id": "jn-order", "name": "Scenario Order", "hidden": True,
         "formula": "Coalesce([Commission Scenario Registry/Scenario Order], 0)",
         "format": INT},
        {"id": "jn-owner", "name": "Account Manager",
         "formula": "[Commission AM Base/Account Manager]"},
        {"id": "jn-region", "name": "Primary Region",
         "formula": "[Commission AM Base/Primary Region]"},
        {"id": "jn-gp", "name": "Commissionable Gross Profit",
         "formula": "[Commission AM Base/Commissionable Gross Profit]", "format": MONEY},
        {"id": "jn-rev", "name": "Actual Revenue",
         "formula": "[Commission AM Base/Actual Revenue]", "format": MONEY},
        {"id": "jn-fill", "name": "Fill Rate",
         "formula": "[Commission AM Base/Fill Rate]", "format": PCT1},
        {"id": "jn-facs", "name": "Facilities",
         "formula": "[Commission AM Base/Facilities]", "format": INT},
        {"id": "jn-critical", "name": "Critical Facilities",
         "formula": "[Commission AM Base/Critical Facilities]", "format": INT},
        # Scenario assumptions resolve registry value -> governed default.
        {"id": "jn-quota", "name": "Base Quota",
         "formula": "Round([Commission AM Base/Quota Basis] * "
                    "Coalesce([Commission Scenario Registry/Quota Factor], 1.0))",
         "format": MONEY},
        {"id": "jn-t1lim", "name": "Base Tier 1 Limit",
         "formula": "[Commission AM Base/Base Tier 1 Limit]", "format": PCT1},
        {"id": "jn-t2lim", "name": "Base Tier 2 Limit",
         "formula": "[Commission AM Base/Base Tier 2 Limit]", "format": PCT1},
        {"id": "jn-t1rate", "name": "Base Tier 1 Rate",
         "formula": "Coalesce("
                    "[Commission Scenario Registry/Tier 1 Rate], "
                    "[Commission AM Base/Default Tier 1 Rate])", "format": PCT1},
        {"id": "jn-t2rate", "name": "Base Tier 2 Rate",
         "formula": "Coalesce("
                    "[Commission Scenario Registry/Tier 2 Rate], "
                    "[Commission AM Base/Default Tier 2 Rate])", "format": PCT1},
        {"id": "jn-t3rate", "name": "Base Tier 3 Rate",
         "formula": "Coalesce("
                    "[Commission Scenario Registry/Tier 3 Rate], "
                    "[Commission AM Base/Default Tier 3 Rate])", "format": PCT1},
        {"id": "jn-quality", "name": "Base Quality Modifier",
         "formula": "Coalesce("
                    "[Commission Scenario Registry/Quality Modifier], "
                    "[Commission AM Base/Default Quality Modifier])"},
        {"id": "jn-status", "name": "Scenario Workflow Status",
         "formula": 'Coalesce([Commission Scenario Registry/Scenario Status], "Draft")'},
        {"id": "jn-note", "name": "Scenario Finance Note",
         "formula": "[Commission Scenario Registry/Finance Note]"},
        # Payout math lives HERE, on the plain join — not on the linked input
        # table. A linked input table's row identity is its key values, so when a
        # user creates a scenario the scenario-name key changes and the grid goes
        # stale (verified: source had 8 rows, the linked table returned 0). Every
        # KPI, chart and outcome surface therefore reads this element, and the
        # linked table is only where per-AM overrides are typed.
        {"id": "jn-attain", "name": "Attainment",
         "formula": "[Commissionable Gross Profit] / [Base Quota]", "format": PCT1},
        {"id": "jn-tier", "name": "Tier Achieved",
         "formula": 'If([Attainment] <= [Base Tier 1 Limit], "Tier 1", '
                    '[Attainment] <= [Base Tier 2 Limit], "Tier 2", "Tier 3")'},
        {"id": "jn-payout0", "name": "Payout Before Quality",
         "formula": (
             "If([Commissionable Gross Profit] <= [Base Quota] * [Base Tier 1 Limit], "
             "[Commissionable Gross Profit] * [Base Tier 1 Rate], "
             "[Base Quota] * [Base Tier 1 Limit] * [Base Tier 1 Rate] + "
             "If([Commissionable Gross Profit] <= [Base Quota] * [Base Tier 2 Limit], "
             "([Commissionable Gross Profit] - [Base Quota] * [Base Tier 1 Limit]) "
             "* [Base Tier 2 Rate], "
             "([Base Quota] * [Base Tier 2 Limit] - "
             "[Base Quota] * [Base Tier 1 Limit]) * [Base Tier 2 Rate] + "
             "([Commissionable Gross Profit] - [Base Quota] * [Base Tier 2 Limit]) "
             "* [Base Tier 3 Rate]))"
         ), "format": MONEY},
        {"id": "jn-payout", "name": "Final Payout",
         "formula": "[Payout Before Quality] * [Base Quality Modifier] * "
                    "If([Fill Rate] >= 0.90, 1.05, [Fill Rate] < 0.82, 0.90, 1.00)",
         "format": MONEY},
    ],
    "order": ["jn-scenario", "jn-owner", "jn-gp", "jn-quota", "jn-status"],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
})


# Same cross join at month grain, so payout can be shown over time per scenario.
# Monthly tiering compares the month's GP to the month's share of quota.
add({
    "id": "jn-comm-month", "kind": "table", "name": "Commission Month Grid",
    "visibleAsSource": True,
    "source": {"kind": "join",
               "joins": [{"left": {"elementId": "sql-commission-month", "kind": "table"},
                          "right": {"elementId": "it-scenario-reg", "kind": "table"},
                          "columns": [{"left": "1", "right": "1"}],
                          "joinType": "left-outer"}],
               "primarySource": {"elementId": "sql-commission-month", "kind": "table"}},
    "columns": [
        {"id": "jm-scenario", "name": "Scenario Name",
         "formula": 'Coalesce([Commission Scenario Registry/Scenario Name], "Base Plan")'},
        {"id": "jm-owner", "name": "Account Manager",
         "formula": "[Commission AM Month/Account Manager]"},
        {"id": "jm-month", "name": "Month",
         "formula": "[Commission AM Month/Month]", "format": MON},
        {"id": "jm-gp", "name": "Monthly Gross Profit",
         "formula": "[Commission AM Month/Monthly Gross Profit]", "format": MONEY},
        {"id": "jm-fill", "name": "Monthly Fill Rate",
         "formula": "[Commission AM Month/Monthly Fill Rate]", "format": PCT1},
        {"id": "jm-quota", "name": "Monthly Quota",
         "formula": "Round([Commission AM Month/Monthly Quota Basis] * "
                    "Coalesce([Commission Scenario Registry/Quota Factor], 1.0))",
         "format": MONEY},
        {"id": "jm-attain", "name": "Monthly Attainment",
         "formula": "[Monthly Gross Profit] / [Monthly Quota]", "format": PCT1},
        {"id": "jm-tier", "name": "Tier Achieved",
         "formula": 'If([Monthly Attainment] <= 0.80, "Tier 1", '
                    '[Monthly Attainment] <= 1.00, "Tier 2", "Tier 3")'},
        {"id": "jm-rate", "name": "Effective Rate",
         "formula": 'If([Tier Achieved] = "Tier 1", '
                    "Coalesce([Commission Scenario Registry/Tier 1 Rate], 0.030), "
                    'If([Tier Achieved] = "Tier 2", '
                    "Coalesce([Commission Scenario Registry/Tier 2 Rate], 0.050), "
                    "Coalesce([Commission Scenario Registry/Tier 3 Rate], 0.080)))",
         "format": PCT1},
        {"id": "jm-payout", "name": "Monthly Payout",
         "formula": "[Monthly Gross Profit] * [Effective Rate] * "
                    "Coalesce([Commission Scenario Registry/Quality Modifier], 1.0) * "
                    "If([Monthly Fill Rate] >= 0.90, 1.05, "
                    "[Monthly Fill Rate] < 0.82, 0.90, 1.00)",
         "format": MONEY},
    ],
    "order": ["jm-scenario", "jm-owner", "jm-month", "jm-gp", "jm-payout"],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
})


# ------------------------------------------------------------- write-back app
add({
    "id": "it-actions", "kind": "input-table", "name": "Facility Action Plan",
    "inputMode": "view",
    "source": {"kind": "linked", "from": "sql-facility"},
    "columns": [
        {"id": "ap-id", "key": "fp-id", "name": "Facility ID", "hidden": True},
        {"id": "ap-fac", "key": "fp-fac", "name": "Facility"},
        {"id": "ap-state", "key": "fp-state", "name": "State"},
        {"id": "ap-market", "key": "fp-market", "name": "Market"},
        {"id": "ap-region", "key": "fp-region", "name": "Region"},
        {"id": "ap-type", "key": "fp-type", "name": "Facility Type"},
        {"id": "ap-owner0", "key": "fp-owner", "name": "Account Owner"},
        {"id": "ap-post", "key": "fp-post", "name": "Posted Shifts"},
        {"id": "ap-fill", "key": "fp-fill", "name": "Filled Shifts"},
        {"id": "ap-bfill", "key": "fp-bfill", "name": "Plan Filled Shifts"},
        {"id": "ap-open", "key": "fp-open", "name": "Unfilled Shifts"},
        {"id": "ap-fr", "key": "fp-fr", "name": "Fill Rate"},
        {"id": "ap-target", "key": "fp-target", "name": "Plan Fill Rate"},
        {"id": "ap-bid", "key": "fp-bid", "name": "Bid Depth"},
        {"id": "ap-ttf", "key": "fp-ttf", "name": "Time to Fill"},
        {"id": "ap-rev", "key": "fp-rev", "name": "Actual Revenue"},
        {"id": "ap-brev", "key": "fp-brev", "name": "Plan Revenue"},
        {"id": "ap-var", "key": "fp-var", "name": "Revenue Variance"},
        {"id": "ap-exp", "key": "fp-exp", "name": "Open Shift Exposure"},
        {"id": "ap-risk", "key": "fp-risk", "name": "Risk Tier"},
        {"id": "ap-reco", "key": "fp-reco", "name": "Recommended Action"},
        {"id": "ap-status", "name": "Action Status", "type": "text",
         "values": ["Unassigned", "Ready for outreach", "Contacted", "Monitoring", "Resolved"],
         "pills": "color-by-option"},
        {"id": "ap-owner", "name": "Action Owner", "type": "text"},
        {"id": "ap-note", "name": "Client Note", "type": "text"},
        {"id": "ap-next", "name": "Next Step", "type": "text"},
        {"id": "ap-effective", "name": "Workflow Status",
         "formula": 'Coalesce([Action Status], "Unassigned")'},
    ],
    "sort": [
        {"columnId": "ap-risk", "direction": "ascending", "nulls": "last"},
        {"columnId": "ap-exp", "direction": "descending", "nulls": "last"},
    ],
    "conditionalFormats": [
        {"type": "single", "columnIds": ["ap-status", "ap-owner", "ap-note", "ap-next"],
         "condition": "formula", "formula": "True",
         "style": {"backgroundColor": "#F2FFF3"}},
        {"type": "dataBars", "columnIds": ["ap-exp"], "scheme": [ALARM, CARD_ALT]},
        {"type": "single", "columnIds": ["ap-risk"], "condition": "formula",
         "formula": '[Risk Tier] = "Critical"',
         "style": {"backgroundColor": "#FCE8E8", "color": ALARM}},
        {"type": "single", "columnIds": ["ap-risk"], "condition": "formula",
         "formula": '[Risk Tier] = "On plan"',
         "style": {"backgroundColor": "#E8F7EC", "color": GOOD}},
    ],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                   "gridLines": "horizontal", "banding": "shown",
                   "bandingColor": CARD_ALT},
})

# ------------------------------------------- commission outcome surfaces (3)
# The Summit commission app reads as three stacked answers, not one grid:
# totals per scenario, the same totals per rep, and the impact over time. Each
# gets a heat-scaled rate column so the expensive plan is obvious at a glance.
add({
    "id": "tbl-comm-outcome", "kind": "table", "name": "Scenario Outcomes",
    "visibleAsSource": True,
    "source": {"kind": "table", "elementId": "jn-comm-calc"},
    "columns": [
        {"id": "so-scenario", "name": "Scenario Name",
         "formula": "[Commission Scenario Grid/Scenario Name]"},
        # Descriptive columns must be aggregates to sit in a grouping's
        # calculations; Min() over a constant-per-group value is the idiom.
        {"id": "so-status", "name": "Status",
         "formula": "Min([Commission Scenario Grid/Scenario Workflow Status])"},
        {"id": "so-payout", "name": "Total Payout",
         "formula": "Sum([Commission Scenario Grid/Final Payout])", "format": MONEY},
        {"id": "so-gp", "name": "Commissionable GP",
         "formula": "Sum([Commission Scenario Grid/Commissionable Gross Profit])",
         "format": MONEY},
        {"id": "so-rate", "name": "Payout Rate",
         "formula": "Sum([Commission Scenario Grid/Final Payout]) / "
                    "Sum([Commission Scenario Grid/Commissionable Gross Profit])",
         "format": PCT1},
        {"id": "so-attain", "name": "Avg Attainment",
         "formula": "Avg([Commission Scenario Grid/Attainment])", "format": PCT1},
        {"id": "so-above", "name": "AMs \u2265 Quota",
         "formula": 'CountDistinct(If([Commission Scenario Grid/Attainment] >= 1, '
                    "[Commission Scenario Grid/Account Manager], Null))", "format": INT},
    ],
    "groupings": [{"id": "so-grp", "groupBy": ["so-scenario"],
                   "calculations": ["so-status", "so-payout", "so-gp",
                                    "so-rate", "so-attain", "so-above"]}],
    "conditionalFormats": [scale_cf(["so-rate"]),
                           {"type": "dataBars", "columnIds": ["so-payout"],
                            "scheme": [GREEN, CARD_ALT]}],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": table_theme(header_bg="#E4F7E8", cell_align="right"),
    "noDrill": True,
})

add({
    "id": "tbl-comm-owner", "kind": "table",
    "name": "Scenario Outcomes by Account Manager",
    "visibleAsSource": True,
    "source": {"kind": "table", "elementId": "jn-comm-calc"},
    "columns": [
        {"id": "sw-owner", "name": "Account Mgr",
         "formula": "[Commission Scenario Grid/Account Manager]"},
        {"id": "sw-scenario", "name": "Scenario",
         "formula": "[Commission Scenario Grid/Scenario Name]"},
        {"id": "sw-payout", "name": "Total Payout",
         "formula": "Sum([Commission Scenario Grid/Final Payout])", "format": MONEY},
        {"id": "sw-gp", "name": "Commissionable GP",
         "formula": "Sum([Commission Scenario Grid/Commissionable Gross Profit])",
         "format": MONEY},
        {"id": "sw-rate", "name": "Payout Rate",
         "formula": "Sum([Commission Scenario Grid/Final Payout]) / "
                    "Sum([Commission Scenario Grid/Commissionable Gross Profit])",
         "format": PCT1},
        {"id": "sw-attain", "name": "Attainment",
         "formula": "Avg([Commission Scenario Grid/Attainment])", "format": PCT1},
        {"id": "sw-tier", "name": "Tier",
         "formula": "Min([Commission Scenario Grid/Tier Achieved])"},
        {"id": "sw-fill", "name": "Fill Rate",
         "formula": "Avg([Commission Scenario Grid/Fill Rate])", "format": PCT1},
    ],
    "groupings": [{"id": "sw-grp", "groupBy": ["sw-owner", "sw-scenario"],
                   "calculations": ["sw-payout", "sw-gp", "sw-rate",
                                    "sw-attain", "sw-tier", "sw-fill"]}],
    "conditionalFormats": [scale_cf(["sw-rate"]),
                           {"type": "dataBars", "columnIds": ["sw-payout"],
                            "scheme": [GREEN, CARD_ALT]}],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": table_theme(header_bg="#E4F7E8", cell_align="right"),
    "noDrill": True,
})

add({
    "id": "tbl-comm-time", "kind": "table", "name": "Scenario Impact Over Time",
    "visibleAsSource": True,
    "source": {"kind": "table", "elementId": "jn-comm-month"},
    "columns": [
        {"id": "st-scenario", "name": "Scenario",
         "formula": "[Commission Month Grid/Scenario Name]"},
        {"id": "st-owner", "name": "Account Mgr",
         "formula": "[Commission Month Grid/Account Manager]"},
        {"id": "st-month", "name": "Month",
         "formula": "[Commission Month Grid/Month]", "format": MON},
        {"id": "st-gp", "name": "Comm. GP",
         "formula": "Sum([Commission Month Grid/Monthly Gross Profit])", "format": MONEY},
        {"id": "st-quota", "name": "Quota",
         "formula": "Sum([Commission Month Grid/Monthly Quota])", "format": MONEY},
        {"id": "st-attain", "name": "Attainment",
         "formula": "Sum([Commission Month Grid/Monthly Gross Profit]) / "
                    "Sum([Commission Month Grid/Monthly Quota])", "format": PCT1},
        {"id": "st-tier", "name": "Tier",
         "formula": "Min([Commission Month Grid/Tier Achieved])"},
        {"id": "st-rate", "name": "Rate",
         "formula": "Avg([Commission Month Grid/Effective Rate])", "format": PCT1},
        {"id": "st-payout", "name": "Payout",
         "formula": "Sum([Commission Month Grid/Monthly Payout])", "format": MONEY},
    ],
    "groupings": [{"id": "st-grp",
                   "groupBy": ["st-scenario", "st-owner", "st-month"],
                   "calculations": ["st-gp", "st-quota", "st-attain", "st-tier",
                                    "st-rate", "st-payout"]}],
    "conditionalFormats": [scale_cf(["st-rate"]),
                           {"type": "dataBars", "columnIds": ["st-payout"],
                            "scheme": [GREEN, CARD_ALT]}],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": table_theme(header_bg="#E4F7E8", cell_align="center"),
    "noDrill": True,
})

add({
    "id": "ch-comm-time", "kind": "line-chart", "name": "Payout by month and scenario",
    "source": {"kind": "table", "elementId": "jn-comm-month"},
    "columns": [
        {"id": "ct-month", "name": "Month",
         "formula": "[Commission Month Grid/Month]", "format": MON},
        {"id": "ct-payout", "name": "Monthly Payout",
         "formula": "Sum([Commission Month Grid/Monthly Payout])", "format": MONEY},
        {"id": "ct-scen", "name": "Scenario",
         "formula": "[Commission Month Grid/Scenario Name]"},
    ],
    "xAxis": {"columnId": "ct-month"},
    "yAxis": {"columnIds": ["ct-payout"]},
    "color": {"by": "category", "column": "ct-scen"},
    "legend": {"position": "top"},
    "noDrill": True,
})

add({
    "id": "tbl-action-view", "kind": "table", "name": "Account Action Queue",
    "visibleAsSource": True,
    "source": {"kind": "table", "elementId": "it-actions"},
    "columns": [
        {"id": "av-id", "name": "Facility ID", "formula": "[Facility Action Plan/Facility ID]", "hidden": True},
        {"id": "av-fac", "name": "Facility", "formula": "[Facility Action Plan/Facility]"},
        {"id": "av-market", "name": "Market", "formula": "[Facility Action Plan/Market]"},
        {"id": "av-region", "name": "Region", "formula": "[Facility Action Plan/Region]"},
        {"id": "av-owner0", "name": "Account Owner", "formula": "[Facility Action Plan/Account Owner]"},
        {"id": "av-fr", "name": "Fill Rate", "formula": "[Facility Action Plan/Fill Rate]", "format": PCT1},
        {"id": "av-target", "name": "Plan", "formula": "[Facility Action Plan/Plan Fill Rate]", "format": PCT1},
        {"id": "av-open", "name": "Unfilled", "formula": "[Facility Action Plan/Unfilled Shifts]", "format": INT},
        {"id": "av-exp", "name": "Open Shift Exposure", "formula": "[Facility Action Plan/Open Shift Exposure]", "format": MONEY},
        {"id": "av-risk", "name": "Risk Tier", "formula": "[Facility Action Plan/Risk Tier]"},
        {"id": "av-reco", "name": "Recommended Action", "formula": "[Facility Action Plan/Recommended Action]"},
        {"id": "av-status", "name": "Workflow Status", "formula": "[Facility Action Plan/Workflow Status]"},
        {"id": "av-owner", "name": "Action Owner", "formula": "[Facility Action Plan/Action Owner]"},
        {"id": "av-note", "name": "Client Note", "formula": "[Facility Action Plan/Client Note]"},
    ],
    "actions": [{"id": "act-open-facility", "trigger": "on-select", "effects": [
        {"effect": "set-control-value", "control": "selected_facility",
         "value": {"type": "column", "column": "av-id"}},
        {"effect": "open-overlay", "overlayId": "m-action"},
    ]}],
    "sort": [{"columnId": "av-exp", "direction": "descending", "nulls": "last"}],
    "conditionalFormats": [
        {"type": "dataBars", "columnIds": ["av-exp"], "scheme": [ALARM, CARD_ALT]},
        {"type": "single", "columnIds": ["av-risk"], "condition": "formula",
         "formula": '[Risk Tier] = "Critical"',
         "style": {"backgroundColor": "#FCE8E8", "color": ALARM}},
    ],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
})


# ----------------------------------------------------------------- helpers
def text(eid, body, **extra):
    out = {"id": eid, "kind": "text", "body": body}
    out.update(extra)
    return out


def control(eid, control_id, name, control_type="text", value="", **extra):
    out = {"id": eid, "kind": "control", "controlId": control_id,
           "name": name, "controlType": control_type, "value": value}
    if control_type == "text":
        out.update({"case": "insensitive", "mode": "contains",
                    "includeNulls": "when-no-value-is-selected",
                    "showOperators": False})
    elif control_type in ("number", "date"):
        out.update({"mode": "=", "includeNulls": "when-no-value-is-selected"})
    out.update(extra)
    return out


def button(eid, label, effects, background=INK, foreground="#FFFFFF", appearance="filled"):
    return {
        "id": eid, "kind": "button", "text": label,
        "appearance": appearance,
        "style": {"backgroundColor": background, "color": foreground},
        "actions": [{"id": "act-" + eid, "trigger": "on-click", "effects": effects}],
    }


def kpi(eid, label, source, formula, fmt, comparison_label=None,
        comparison_formula=None, value_color=INK, neutral_comparison=False):
    columns = [{"id": eid + "-v", "name": label, "formula": formula, "format": fmt}]
    out = {
        "id": eid, "kind": "kpi-chart",
        "name": {"text": label, "color": MUTED, "fontSize": 11, "fontWeight": "bold"},
        "source": {"kind": "table", "elementId": source},
        "columns": columns,
        "value": {"columnId": eid + "-v", "color": value_color, "fontSize": 32},
        "layout": {"anchor": "middle"},
        "style": {"backgroundColor": CARD, "borderColor": RULE, "borderWidth": 1},
    }
    if comparison_label:
        columns.append({"id": eid + "-c", "name": comparison_label,
                        "formula": comparison_formula, "format": fmt})
        out["comparisonColumn"] = {"columnId": eid + "-c"}
        if neutral_comparison:
            out["comparison"] = {"display": "delta", "label": comparison_label,
                                 "fontSize": 11, "direction": "none",
                                 "colorNeutral": ALARM}
        else:
            out["comparison"] = {"display": "delta", "label": comparison_label,
                                 "fontSize": 11, "colorGood": GOOD, "colorBad": ALARM}
    return out


# --------------------------------------------------------------- controls
add(control(
    "ct-region", "region_filter", "Region", "list", "",
    mode="include", selectionMode="multiple", values=[],
    source={"kind": "source", "source": {"kind": "table", "elementId": "sql-market"},
            "columnId": "ma-region"},
    filters=[
        {"source": {"kind": "table", "elementId": "sql-market"}, "columnId": "ma-region"},
        {"source": {"kind": "table", "elementId": "sql-facility"}, "columnId": "fp-region"},
        {"source": {"kind": "table", "elementId": "it-actions"}, "columnId": "ap-region"},
        {"source": {"kind": "table", "elementId": "tbl-action-view"}, "columnId": "av-region"},
        {"source": {"kind": "table", "elementId": "sql-supply"}, "columnId": "sc-region"},
    ],
))
add(control(
    "ct-credential", "credential_filter", "Credential", "list", "",
    mode="include", selectionMode="multiple", values=[],
    source={"kind": "source", "source": {"kind": "table", "elementId": "sql-market"},
            "columnId": "ma-cred"},
    filters=[
        {"source": {"kind": "table", "elementId": "sql-market"}, "columnId": "ma-cred"},
        {"source": {"kind": "table", "elementId": "sql-supply"}, "columnId": "sc-cred"},
    ],
))
add(control(
    "ct-risk", "risk_filter", "Risk tier", "list", "",
    mode="include", selectionMode="multiple", values=[],
    source={"kind": "source", "source": {"kind": "table", "elementId": "it-actions"},
            "columnId": "ap-risk"},
    filters=[
        {"source": {"kind": "table", "elementId": "it-actions"}, "columnId": "ap-risk"},
        {"source": {"kind": "table", "elementId": "tbl-action-view"}, "columnId": "av-risk"},
    ],
))
add(control(
    "ct-grain", "date_grain", "Date grain", "segmented", "month",
    source={"kind": "manual", "valueType": "text",
            "values": ["month", "quarter"], "labels": ["Month", "Quarter"]},
))
add(control("ct-selected", "selected_facility", "Selected facility"))
add(control(
    "ct-decision", "action_decision", "Action status", "segmented", "Ready for outreach",
    source={"kind": "manual", "valueType": "text",
            "values": ["Ready for outreach", "Contacted", "Monitoring", "Resolved"],
            "labels": ["Ready", "Contacted", "Monitor", "Resolved"]},
))
add(control("ct-action-owner", "action_owner", "Action owner"))
add(control("ct-action-note", "action_note", "Client note", "text-area"))
add(control("ct-next-step", "next_step", "Next step"))
# Sourced from the JOIN, not the registry: the join always yields at least the
# Base Plan fallback, so the picker is never empty before the first scenario is
# created. Filtering stays on the modeling grid, which is what the page reads.
#
# ⚠️ No default value on purpose. A hardcoded "Base Plan" default silently
# emptied the whole page the moment a user created their first scenario: the
# left-outer fallback label stops appearing once the registry has rows, so the
# filter matched nothing and every KPI read null. Defaulting to no selection
# means the page always shows all scenarios until the user picks one.
add(control(
    "ct-comm-scenario", "commission_scenario", "Commission scenario",
    "list", "", mode="include", selectionMode="single", values=[],
    source={"kind": "source",
            "source": {"kind": "table", "elementId": "jn-comm-calc"},
            "columnId": "jn-scenario"},
    filters=[],
))
add(control(
    "ct-comm-owner", "commission_owner", "Account manager",
    "list", "", mode="include", selectionMode="multiple", values=[],
    source={"kind": "source",
            "source": {"kind": "table", "elementId": "sql-commission"},
            "columnId": "cb-owner"},
    filters=[],
))
add(control(
    "ct-comm-decision", "commission_decision", "Finance decision",
    "segmented", "Approved",
    source={"kind": "manual", "valueType": "text",
            "values": ["Approved", "Adjust", "Rejected"],
            "labels": ["Approve", "Request changes", "Reject"]},
))
add(control("ct-comm-note", "commission_note", "Finance note", "text-area"))
# New-scenario form. These are TEXT controls on purpose: a number *parameter*
# control is rejected by the spec API, so numeric assumptions come in as text and
# are cast with Number([ctrl]) inside the insert-rows values.
add(control("ct-new-name", "new_scenario_name", "Scenario name"))
add(control("ct-new-desc", "new_scenario_desc", "What this plan tests"))
add(control("ct-new-quota", "new_scenario_quota", "Quota factor (1.00 = plan)"))
add(control("ct-new-t1", "new_scenario_t1", "Tier 1 rate (e.g. 0.030)"))
add(control("ct-new-t2", "new_scenario_t2", "Tier 2 rate (e.g. 0.050)"))
add(control("ct-new-t3", "new_scenario_t3", "Tier 3 rate (e.g. 0.080)"))
add(control("ct-new-quality", "new_scenario_quality", "Fill-quality modifier (1.00 = neutral)"))


# ------------------------------------------------------------------ KPIs
add(kpi("k-fill", "Marketplace fill rate", "sql-market",
        "Sum([Marketplace Activity/Filled Shifts]) / Sum([Marketplace Activity/Posted Shifts])",
        PCT1, "vs plan",
        "Sum([Marketplace Activity/Plan Filled Shifts]) / Sum([Marketplace Activity/Posted Shifts])"))
add(kpi("k-open", "Unfilled shifts", "sql-market",
        "Sum([Marketplace Activity/Unfilled Shifts])", INT,
        "plan gap",
        "Sum([Marketplace Activity/Posted Shifts]) - Sum([Marketplace Activity/Plan Filled Shifts])",
        ALARM, neutral_comparison=True))
add(kpi("k-exposure", "Open shift exposure", "sql-market",
        "Sum([Marketplace Activity/Open Shift Exposure])", MONEY,
        "revenue to plan",
        "Sum([Marketplace Activity/Plan Revenue]) - Sum([Marketplace Activity/Actual Revenue])",
        ALARM, neutral_comparison=True))
add(kpi("k-margin", "Marketplace take", "sql-market",
        "Sum([Marketplace Activity/Gross Profit]) / Sum([Marketplace Activity/Actual Revenue])",
        PCT1, "target", "0.245"))
add(kpi("k-sami", "SAMI-assisted fills", "sql-market",
        "Sum(If([Marketplace Activity/SAMI Assisted], [Marketplace Activity/Filled Shifts], 0))"
        " / Sum([Marketplace Activity/Filled Shifts])", PCT1,
        "operating goal", "0.40", GREEN))

add(kpi("k-critical", "Critical facilities", "sql-facility",
        'CountDistinct(If([Facility Performance/Risk Tier] = "Critical", '
        "[Facility Performance/Facility ID], Null))", INT, value_color=ALARM))
add(kpi("k-action-exp", "Exposure in action queue", "it-actions",
        "Sum([Facility Action Plan/Open Shift Exposure])", MONEY, value_color=ALARM))
add(kpi("k-ready", "Ready for outreach", "it-actions",
        'CountDistinct(If([Facility Action Plan/Workflow Status] = "Ready for outreach", '
        "[Facility Action Plan/Facility ID], Null))", INT, value_color=GREEN))
add(kpi("k-action-fill", "Queue fill rate", "it-actions",
        "Sum([Facility Action Plan/Filled Shifts]) / Sum([Facility Action Plan/Posted Shifts])",
        PCT1, "plan",
        "Sum([Facility Action Plan/Plan Filled Shifts]) / "
        "Sum([Facility Action Plan/Posted Shifts])"))
add(kpi("k-comm-payout", "Scenario payout", "jn-comm-calc",
        "Sum([Commission Scenario Grid/Final Payout])", MONEY))
add(kpi("k-comm-rate", "Payout / gross profit", "jn-comm-calc",
        "Sum([Commission Scenario Grid/Final Payout]) / "
        "Sum([Commission Scenario Grid/Commissionable Gross Profit])", PCT1,
        "operating guardrail", "0.055"))
add(kpi("k-comm-attain", "Average attainment", "jn-comm-calc",
        "Avg([Commission Scenario Grid/Attainment])", PCT1,
        "target", "1.00"))
add(kpi("k-comm-above", "AMs at or above quota", "jn-comm-calc",
        'CountDistinct(If([Commission Scenario Grid/Attainment] >= 1, '
        "[Commission Scenario Grid/Account Manager], Null))", INT))


# ---------------------------------------------------------------- visuals
add({
    "id": "ch-fill", "kind": "line-chart", "name": "Fill rate: actual vs plan",
    "source": {"kind": "table", "elementId": "sql-market"},
    "columns": [
        {"id": "cf-month", "name": "Period",
         "formula": "DateTrunc([date_grain], [Marketplace Activity/Month])", "format": MON},
        {"id": "cf-actual", "name": "Actual",
         "formula": "Sum([Marketplace Activity/Filled Shifts]) / "
                    "Sum([Marketplace Activity/Posted Shifts])", "format": PCT1},
        {"id": "cf-plan", "name": "Plan",
         "formula": "Sum([Marketplace Activity/Plan Filled Shifts]) / "
                    "Sum([Marketplace Activity/Posted Shifts])", "format": PCT1},
    ],
    "xAxis": {"columnId": "cf-month"},
    "yAxis": {"columnIds": ["cf-actual", "cf-plan"]},
    "legend": {"position": "top"},
})
add({
    "id": "ch-region", "kind": "bar-chart", "name": "Demand coverage by region",
    "source": {"kind": "table", "elementId": "sql-market"},
    "columns": [
        {"id": "cr-region", "name": "Region", "formula": "[Marketplace Activity/Region]"},
        {"id": "cr-post", "name": "Posted", "formula": "Sum([Marketplace Activity/Posted Shifts])", "format": INT},
        {"id": "cr-fill", "name": "Filled", "formula": "Sum([Marketplace Activity/Filled Shifts])", "format": INT},
        {"id": "cr-plan", "name": "Plan", "formula": "Sum([Marketplace Activity/Plan Filled Shifts])", "format": INT},
    ],
    "xAxis": {"columnId": "cr-region",
              "sort": {"by": "cr-post", "aggregation": "sum", "direction": "descending"}},
    "yAxis": {"columnIds": ["cr-post", "cr-fill", "cr-plan"]},
    "stacking": "none", "legend": {"position": "top"},
})
add({
    "id": "ch-credential", "kind": "bar-chart", "name": "Coverage gap by credential",
    "source": {"kind": "table", "elementId": "sql-market"},
    "columns": [
        {"id": "cc-cred", "name": "Credential", "formula": "[Marketplace Activity/Credential]"},
        {"id": "cc-open", "name": "Unfilled", "formula": "Sum([Marketplace Activity/Unfilled Shifts])", "format": INT},
        {"id": "cc-supply", "name": "Credential-ready supply",
         "formula": "Sum([Marketplace Activity/Credential-Ready Supply]) / 18", "format": INT},
    ],
    "xAxis": {"columnId": "cc-cred"},
    "yAxis": {"columnIds": ["cc-open", "cc-supply"]},
    "stacking": "none", "legend": {"position": "top"},
})
add({
    "id": "pvt-variance", "kind": "table",
    "name": "Actual vs plan — drill from region to facility",
    "source": {"kind": "table", "elementId": "sql-market"},
    "columns": [
        {"id": "pv-region", "name": "Region", "formula": "[Marketplace Activity/Region]"},
        {"id": "pv-state", "name": "State", "formula": "[Marketplace Activity/State]"},
        {"id": "pv-market", "name": "Market", "formula": "[Marketplace Activity/Market]"},
        {"id": "pv-fac", "name": "Facility", "formula": "[Marketplace Activity/Facility]"},
        {"id": "pv-actual", "name": "Actual Revenue", "formula": "Sum([Marketplace Activity/Actual Revenue])", "format": MONEY},
        {"id": "pv-plan", "name": "Plan Revenue", "formula": "Sum([Marketplace Activity/Plan Revenue])", "format": MONEY},
        {"id": "pv-var", "name": "Variance", "formula": "[Actual Revenue] - [Plan Revenue]", "format": MONEY},
        {"id": "pv-fill", "name": "Fill Rate",
         "formula": "Sum([Marketplace Activity/Filled Shifts]) / "
                    "Sum([Marketplace Activity/Posted Shifts])", "format": PCT1},
    ],
    "groupings": [{
        "id": "g-pv",
        "groupBy": ["pv-region", "pv-state", "pv-market", "pv-fac"],
        "calculations": ["pv-actual", "pv-plan", "pv-var", "pv-fill"],
    }],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                   "gridLines": "horizontal"},
})
add({
    "id": "ch-facility", "kind": "bar-chart", "name": "Facility actual vs plan revenue",
    "source": {"kind": "table", "elementId": "it-actions"},
    "columns": [
        {"id": "fc-fac", "name": "Facility", "formula": "[Facility Action Plan/Facility]"},
        {"id": "fc-actual", "name": "Actual", "formula": "Sum([Facility Action Plan/Actual Revenue])", "format": MONEY},
        {"id": "fc-plan", "name": "Plan", "formula": "Sum([Facility Action Plan/Plan Revenue])", "format": MONEY},
    ],
    "xAxis": {"columnId": "fc-fac",
              "sort": {"by": "fc-actual", "aggregation": "sum", "direction": "ascending"},
              "format": {"labels": {"labelAngle": -45}}},
    "yAxis": {"columnIds": ["fc-actual", "fc-plan"]},
    "stacking": "none", "legend": {"position": "top"},
})
add({
    "id": "ch-supply", "kind": "bar-chart", "name": "Open shifts vs ready supply",
    "source": {"kind": "table", "elementId": "sql-supply"},
    "columns": [
        {"id": "su-market", "name": "Market", "formula": "[Supply Coverage/Market]"},
        {"id": "su-open", "name": "Open shifts", "formula": "Sum([Supply Coverage/Open Shifts])", "format": INT},
        {"id": "su-pros", "name": "Ready professionals",
         "formula": "Sum([Supply Coverage/Credential-Ready Supply])", "format": INT},
        {"id": "su-cred", "name": "Credential", "formula": "[Supply Coverage/Credential]"},
    ],
    "xAxis": {"columnId": "su-market"},
    "yAxis": {"columnIds": ["su-open", "su-pros"]},
    "color": {"by": "category", "column": "su-cred"},
    "stacking": "none", "legend": {"position": "top"},
})
add({
    "id": "ch-comm-owner", "kind": "bar-chart",
    "name": "Projected payout by account manager",
    "source": {"kind": "table", "elementId": "jn-comm-calc"},
    "columns": [
        {"id": "co-owner", "name": "Account Manager",
         "formula": "[Commission Scenario Grid/Account Manager]"},
        {"id": "co-payout", "name": "Final Payout",
         "formula": "Sum([Commission Scenario Grid/Final Payout])", "format": MONEY},
        {"id": "co-gp", "name": "Commissionable Gross Profit",
         "formula": "Sum([Commission Scenario Grid/Commissionable Gross Profit])",
         "format": MONEY},
        {"id": "co-attain", "name": "Attainment",
         "formula": "Avg([Commission Scenario Grid/Attainment])", "format": PCT1},
        {"id": "co-tier", "name": "Tier Achieved",
         "formula": "[Commission Scenario Grid/Tier Achieved]"},
    ],
    "xAxis": {"columnId": "co-owner"},
    "yAxis": {"columnIds": ["co-payout"]},
    "color": {"by": "category", "column": "co-tier"},
    "legend": {"position": "top"},
})
add({
    "id": "ch-comm-attain", "kind": "bar-chart",
    "name": "Attainment vs quota",
    "source": {"kind": "table", "elementId": "jn-comm-calc"},
    "columns": [
        {"id": "ca-owner", "name": "Account Manager",
         "formula": "[Commission Scenario Grid/Account Manager]"},
        {"id": "ca-attain", "name": "Attainment",
         "formula": "Avg([Commission Scenario Grid/Attainment])", "format": PCT1},
        {"id": "ca-target", "name": "Quota", "formula": "1.00", "format": PCT1},
    ],
    "xAxis": {"columnId": "ca-owner"},
    "yAxis": {"columnIds": ["ca-attain", "ca-target"]},
    "stacking": "none", "legend": {"position": "top"},
})


# ------------------------------------------------------------------ actions
REFRESH_ACTIONS = [
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-actions"}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-action-view"}},
]
add(button("b-ready", "✓ Stage critical facilities", [
    {"effect": "update-rows", "table": "it-actions",
     "whichRows": {"type": "formula", "formula": '[Risk Tier] = "Critical"'},
     "values": {"ap-status": {"type": "constant",
                              "value": {"type": "text", "value": "Ready for outreach"}}}},
] + REFRESH_ACTIONS, GREEN, INK))
add(button("b-clear", "↺ Clear workflow fields", [
    {"effect": "update-rows", "table": "it-actions",
     "whichRows": {"type": "formula", "formula": "True"},
     "values": {
         "ap-status": {"type": "constant", "value": {"type": "text", "value": None}},
         "ap-owner": {"type": "constant", "value": {"type": "text", "value": None}},
         "ap-note": {"type": "constant", "value": {"type": "text", "value": None}},
         "ap-next": {"type": "constant", "value": {"type": "text", "value": None}},
     }},
] + REFRESH_ACTIONS, CARD, INK, "outline"))
add(button("b-save-action", "✓ Save account action", [
    {"effect": "update-rows", "table": "it-actions",
     "whichRows": {"type": "formula", "formula": "[Facility ID] = [selected_facility]"},
     "values": {
         "ap-status": {"type": "control", "control": "action_decision"},
         "ap-owner": {"type": "control", "control": "action_owner"},
         "ap-note": {"type": "control", "control": "action_note"},
         "ap-next": {"type": "control", "control": "next_step"},
     }},
] + REFRESH_ACTIONS + [{"effect": "close-overlay"}], GREEN, INK))
add(button("b-cancel-action", "Cancel", [{"effect": "close-overlay"}],
           CARD, INK, "outline"))
# Every commission write refreshes the registry, the join and the modeling grid,
# because a scenario-level change has to travel all three.
COMM_REFRESH = [
    {"effect": "refresh-element",
     "target": {"type": "element", "element": "it-scenario-reg"}},
    {"effect": "refresh-element",
     "target": {"type": "element", "element": "jn-comm-calc"}},
]
SCENARIO_ROW = {"type": "formula", "formula": "[Scenario Name] = [commission_scenario]"}

add(button("b-comm-create", "+ New scenario", [
    {"effect": "open-overlay", "overlayId": "m-scenario"},
], GREEN, INK))


def seed_scenario(name, desc, order, quota_factor, t1, t2, t3, quality):
    """One governed starter scenario, inserted as a real registry row."""
    def num(v):
        return {"type": "constant", "value": {"type": "number", "value": v}}

    def txt(v):
        return {"type": "constant", "value": {"type": "text", "value": v}}

    return {"effect": "insert-rows", "table": "it-scenario-reg",
            "values": {"rg-name": txt(name), "rg-desc": txt(desc),
                       "rg-order": num(order), "rg-quota-factor": num(quota_factor),
                       "rg-t1rate": num(t1), "rg-t2rate": num(t2),
                       "rg-t3rate": num(t3), "rg-quality": num(quality),
                       "rg-status": txt("Draft")}}


# Cold start: an empty registry renders only the Base Plan fallback. This loads
# the three governed starter plans as real, editable, deletable rows.
add(button("b-comm-seed", "⤓ Load governed plans", [
    seed_scenario("Base Plan",
                  "Balanced payout against governed gross profit",
                  1, 1.00, 0.030, 0.050, 0.080, 1.00),
    seed_scenario("Retention Weighted",
                  "Rewards fill quality and critical-account recovery",
                  2, 0.96, 0.028, 0.052, 0.085, 1.08),
    seed_scenario("Growth Accelerator",
                  "Raises quota and pays more above target",
                  3, 1.08, 0.035, 0.060, 0.100, 0.96),
] + COMM_REFRESH, CARD, INK, "outline"))

add(button("b-scenario-create", "✓ Create scenario", [
    {"effect": "insert-rows", "table": "it-scenario-reg",
     "values": {
         "rg-name": {"type": "control", "control": "new_scenario_name"},
         "rg-desc": {"type": "control", "control": "new_scenario_desc"},
         "rg-order": {"type": "formula", "formula": "99"},
         "rg-quota-factor": {"type": "formula",
                             "formula": "Coalesce(Number([new_scenario_quota]), 1.0)"},
         "rg-t1rate": {"type": "formula",
                       "formula": "Coalesce(Number([new_scenario_t1]), 0.030)"},
         "rg-t2rate": {"type": "formula",
                       "formula": "Coalesce(Number([new_scenario_t2]), 0.050)"},
         "rg-t3rate": {"type": "formula",
                       "formula": "Coalesce(Number([new_scenario_t3]), 0.080)"},
         "rg-quality": {"type": "formula",
                        "formula": "Coalesce(Number([new_scenario_quality]), 1.0)"},
         "rg-status": {"type": "constant", "value": {"type": "text", "value": "Draft"}},
     }},
    # Select the scenario just created so the grid and KPIs land on it.
    {"effect": "set-control-value", "control": "commission_scenario",
     "value": {"type": "control", "control": "new_scenario_name"}},
] + COMM_REFRESH + [
    {"effect": "clear-control", "scope": {"type": "control", "control": "new_scenario_name"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "new_scenario_desc"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "new_scenario_quota"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "new_scenario_t1"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "new_scenario_t2"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "new_scenario_t3"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "new_scenario_quality"}},
    {"effect": "close-overlay"},
], GREEN, INK))
add(button("b-scenario-cancel", "Cancel", [{"effect": "close-overlay"}],
           CARD, INK, "outline"))

add(button("b-comm-submit", "✓ Submit scenario", [
    {"effect": "update-rows", "table": "it-scenario-reg",
     "whichRows": SCENARIO_ROW,
     "values": {"rg-status": {"type": "constant",
                              "value": {"type": "text", "value": "Submitted"}}}},
] + COMM_REFRESH, GREEN, INK))
add(button("b-comm-review", "Finance review", [
    {"effect": "open-overlay", "overlayId": "m-commission"},
], INK))
add(button("b-comm-reset", "↺ Reset selected scenario", [
    {"effect": "update-rows", "table": "it-scenario-reg",
     "whichRows": SCENARIO_ROW,
     "values": {
         "rg-status": {"type": "constant", "value": {"type": "text", "value": "Draft"}},
         "rg-note": {"type": "constant", "value": {"type": "text", "value": None}},
     }},
] + COMM_REFRESH, CARD, INK, "outline"))
add(button("b-comm-save", "✓ Save finance decision", [
    {"effect": "update-rows", "table": "it-scenario-reg",
     "whichRows": SCENARIO_ROW,
     "values": {
         "rg-status": {"type": "control", "control": "commission_decision"},
         "rg-note": {"type": "control", "control": "commission_note"},
     }},
] + COMM_REFRESH + [{"effect": "close-overlay"}], GREEN, INK))
add(button("b-comm-cancel", "Cancel", [{"effect": "close-overlay"}],
           CARD, INK, "outline"))


# ------------------------------------------------------- commission disputes
# Adapted from the demeng "Commissions Dispute" POV: a full ticketing workflow
# where an account manager disputes a payout, then finance works it through a
# status lifecycle with a threaded comment trail and SLA timestamps. Two empty
# input tables — the dispute registry and an append-only comment log — plus a
# selectable queue and two modals. This is the finance/commissions workflow the
# discovery call named as living in spreadsheets today.
DISPUTE_TYPES = ["Rate or tier", "Quota", "Fill-quality modifier",
                 "Missing facility credit", "Clawback", "Other"]

add({
    "id": "it-dispute", "kind": "input-table", "name": "Commission Disputes",
    "inputMode": "view", "source": {"kind": "empty", "connectionId": CONN},
    "columns": [
        {"id": "dp-ticket", "type": "text", "name": "Dispute ID"},
        {"id": "dp-am", "type": "text", "name": "Account Manager"},
        {"id": "dp-scenario", "type": "text", "name": "Scenario"},
        {"id": "dp-type", "type": "text", "name": "Dispute Type",
         "values": DISPUTE_TYPES, "pills": "color-by-option"},
        {"id": "dp-priority", "type": "text", "name": "Priority",
         "values": ["Low", "Medium", "High", "Critical"], "pills": "color-by-option"},
        {"id": "dp-status", "type": "text", "name": "Status",
         "values": ["Submitted", "In Review", "Escalated", "Resolved"],
         "pills": "color-by-option"},
        {"id": "dp-amount", "type": "number", "name": "Amount in Dispute",
         "format": MONEY},
        {"id": "dp-title", "type": "text", "name": "Case Title"},
        {"id": "dp-desc", "type": "text", "name": "Description"},
        {"id": "dp-inreview", "type": "datetime", "name": "In Review Date"},
        {"id": "dp-esc", "type": "datetime", "name": "Escalation Date"},
        {"id": "dp-resolved", "type": "datetime", "name": "Resolved Date"},
        {"id": "dp-resolution", "type": "text", "name": "Resolution Note"},
        {"id": "CREATED_AT"},
        {"id": "CREATED_BY"},
        # Threaded comment view: pull every log entry for this ticket, oldest to
        # newest, into one cell — the demeng ListAgg-into-Lookup pattern.
        {"id": "dp-comments", "name": "Comment Thread",
         "formula": 'Lookup(ListAgg([Dispute Comment Log/Entry Text], "\\n\\n"), '
                    "[Dispute ID], [Dispute Comment Log/Ticket ID])"},
        {"id": "dp-age", "name": "Age (days)",
         "formula": 'DateDiff("day", [Created At], Coalesce([Resolved Date], Now()))',
         "format": INT},
        {"id": "dp-status-f", "name": "Workflow Status",
         "formula": 'Coalesce([Status], "Submitted")'},
    ],
    "sort": [{"columnId": "dp-status", "direction": "ascending", "nulls": "last"},
             {"columnId": "dp-amount", "direction": "descending", "nulls": "last"}],
    "conditionalFormats": [
        {"type": "dataBars", "columnIds": ["dp-amount"], "scheme": [ALARM, CARD_ALT]},
        {"type": "single", "columnIds": ["dp-status"], "condition": "formula",
         "formula": '[Status] = "Escalated"',
         "style": {"backgroundColor": "#FCE8E8", "color": ALARM}},
        {"type": "single", "columnIds": ["dp-status"], "condition": "formula",
         "formula": '[Status] = "Resolved"',
         "style": {"backgroundColor": "#E8F7EC", "color": GOOD}},
    ],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                   "gridLines": "horizontal", "banding": "shown",
                   "bandingColor": CARD_ALT},
})

add({
    "id": "it-dispute-log", "kind": "input-table", "name": "Dispute Comment Log",
    "inputMode": "edit", "source": {"kind": "empty", "connectionId": CONN},
    "columns": [
        {"id": "dl-ticket", "type": "text", "name": "Ticket ID"},
        {"id": "dl-author", "type": "text", "name": "Author",
         "values": ["Account Manager", "Finance"], "pills": "color-by-option"},
        {"id": "dl-comment", "type": "text", "name": "Comment"},
        {"id": "CREATED_AT"},
        {"id": "CREATED_BY"},
        # One rendered line per comment; CREATED_AT/CREATED_BY are auto system
        # columns and must not be written by the insert.
        {"id": "dl-entry", "name": "Entry Text",
         "formula": 'DateFormat([Created At], "%b %-d %-I:%M %p") & "  ·  " & '
                    'Coalesce([Author], "") & ": " & Coalesce([Comment], "")'},
    ],
    "sort": [{"columnId": "CREATED_AT", "direction": "ascending", "nulls": "last"}],
})

add({
    "id": "tbl-dispute", "kind": "table", "name": "Dispute Queue",
    "visibleAsSource": True,
    "source": {"kind": "table", "elementId": "it-dispute"},
    "columns": [
        {"id": "dq-ticket", "name": "Dispute ID", "formula": "[Commission Disputes/Dispute ID]"},
        {"id": "dq-am", "name": "Account Manager", "formula": "[Commission Disputes/Account Manager]"},
        {"id": "dq-scenario", "name": "Scenario", "formula": "[Commission Disputes/Scenario]"},
        {"id": "dq-type", "name": "Dispute Type", "formula": "[Commission Disputes/Dispute Type]"},
        {"id": "dq-priority", "name": "Priority", "formula": "[Commission Disputes/Priority]"},
        {"id": "dq-amount", "name": "Amount in Dispute", "formula": "[Commission Disputes/Amount in Dispute]", "format": MONEY},
        {"id": "dq-age", "name": "Age (days)", "formula": "[Commission Disputes/Age (days)]", "format": INT},
        {"id": "dq-status", "name": "Workflow Status", "formula": "[Commission Disputes/Workflow Status]"},
    ],
    "actions": [{"id": "act-open-dispute", "trigger": "on-select", "effects": [
        {"effect": "set-control-value", "control": "dispute_selected",
         "value": {"type": "column", "column": "dq-ticket"}},
        {"effect": "open-overlay", "overlayId": "m-dispute-detail"},
    ]}],
    "sort": [{"columnId": "dq-amount", "direction": "descending", "nulls": "last"}],
    "conditionalFormats": [
        {"type": "dataBars", "columnIds": ["dq-amount"], "scheme": [ALARM, CARD_ALT]},
        {"type": "single", "columnIds": ["dq-status"], "condition": "formula",
         "formula": '[Workflow Status] = "Escalated"',
         "style": {"backgroundColor": "#FCE8E8", "color": ALARM}},
    ],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
})

add({
    "id": "tbl-dispute-thread", "kind": "table", "name": "Selected Dispute Comments",
    "visibleAsSource": True,
    "source": {"kind": "table", "elementId": "it-dispute-log"},
    "columns": [
        {"id": "dt-entry", "name": "Comment trail", "formula": "[Dispute Comment Log/Entry Text]"},
        {"id": "dt-ticket", "name": "Ticket ID", "formula": "[Dispute Comment Log/Ticket ID]", "hidden": True},
        {"id": "dt-created", "name": "Logged", "formula": "[Dispute Comment Log/Created At]", "hidden": True},
    ],
    "sort": [{"columnId": "dt-created", "direction": "ascending", "nulls": "last"}],
    "tableComponents": {"summaryBar": "hidden"},
    "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
})

# Dispute KPIs.
add(kpi("k-dp-open", "Open disputes", "it-dispute",
        'CountDistinct(If([Commission Disputes/Workflow Status] <> "Resolved", '
        "[Commission Disputes/Dispute ID], Null))", INT, value_color=ALARM))
add(kpi("k-dp-amount", "Amount in dispute", "it-dispute",
        'Coalesce(SumIf([Commission Disputes/Amount in Dispute], '
        '[Commission Disputes/Workflow Status] <> "Resolved"), 0)', MONEY,
        value_color=ALARM))
add(kpi("k-dp-age", "Avg open age (days)", "it-dispute",
        'Coalesce(Avg(If([Commission Disputes/Workflow Status] <> "Resolved", '
        "[Commission Disputes/Age (days)], Null)), 0)", HOURS1, value_color=INK))
add(kpi("k-dp-esc", "Escalated", "it-dispute",
        'CountDistinct(If([Commission Disputes/Workflow Status] = "Escalated", '
        "[Commission Disputes/Dispute ID], Null))", INT, value_color=WARN))

add({
    "id": "ch-dp-status", "kind": "bar-chart", "name": "Disputes by status",
    "source": {"kind": "table", "elementId": "it-dispute"},
    "columns": [
        {"id": "ds-status", "name": "Status", "formula": "[Commission Disputes/Workflow Status]"},
        {"id": "ds-count", "name": "Disputes",
         "formula": "CountDistinct([Commission Disputes/Dispute ID])", "format": INT},
        {"id": "ds-amt", "name": "Amount in Dispute",
         "formula": "Sum([Commission Disputes/Amount in Dispute])", "format": MONEY},
    ],
    "xAxis": {"columnId": "ds-status"},
    "yAxis": {"columnIds": ["ds-count"]},
    "legend": {"position": "top"},
})
add({
    # Pie/donut are rejected on papercranestaging (same org drift as pivot-table),
    # so disputed-$-by-type is a horizontal-reading bar instead.
    "id": "ch-dp-type", "kind": "bar-chart", "name": "Disputed $ by type",
    "source": {"kind": "table", "elementId": "it-dispute"},
    "columns": [
        {"id": "dt-type", "name": "Dispute Type", "formula": "[Commission Disputes/Dispute Type]"},
        {"id": "dt-amt", "name": "Amount in Dispute",
         "formula": "Sum([Commission Disputes/Amount in Dispute])", "format": MONEY},
    ],
    "xAxis": {"columnId": "dt-type"},
    "yAxis": {"columnIds": ["dt-amt"]},
    "legend": {"position": "top"},
    "noDrill": True,
})

# Dispute controls. The selected-dispute control is set by the queue's on-select
# and also filters the comment log + thread table, so the detail modal shows only
# the chosen ticket's trail.
add(control(
    "ct-dispute-selected", "dispute_selected", "Selected dispute", "text", "",
    mode="equals",
    filters=[
        {"source": {"kind": "table", "elementId": "it-dispute-log"}, "columnId": "dl-ticket"},
        {"source": {"kind": "table", "elementId": "tbl-dispute-thread"}, "columnId": "dt-ticket"},
    ],
))
add(control(
    "ct-dispute-statusf", "dispute_status_filter", "Status", "list", "",
    mode="include", selectionMode="multiple", values=[],
    source={"kind": "source", "source": {"kind": "table", "elementId": "it-dispute"},
            "columnId": "dp-status-f"},
    filters=[
        {"source": {"kind": "table", "elementId": "it-dispute"}, "columnId": "dp-status-f"},
        {"source": {"kind": "table", "elementId": "tbl-dispute"}, "columnId": "dq-status"},
    ],
))
# New-dispute form: AM and Scenario pull from governed lists; the rest are typed.
add(control(
    "ct-nd-am", "nd_am", "Account manager", "list", "",
    mode="include", selectionMode="single", values=[],
    source={"kind": "source", "source": {"kind": "table", "elementId": "sql-commission"},
            "columnId": "cb-owner"},
))
add(control(
    "ct-nd-scenario", "nd_scenario", "Scenario", "list", "",
    mode="include", selectionMode="single", values=[],
    source={"kind": "source", "source": {"kind": "table", "elementId": "jn-comm-calc"},
            "columnId": "jn-scenario"},
))
add(control(
    "ct-nd-type", "nd_type", "Dispute type", "segmented", "Rate or tier",
    source={"kind": "manual", "valueType": "text",
            "values": DISPUTE_TYPES, "labels": DISPUTE_TYPES},
))
add(control(
    "ct-nd-priority", "nd_priority", "Priority", "segmented", "Medium",
    source={"kind": "manual", "valueType": "text",
            "values": ["Low", "Medium", "High", "Critical"],
            "labels": ["Low", "Medium", "High", "Critical"]},
))
add(control("ct-nd-amount", "nd_amount", "Amount in dispute ($)"))
add(control("ct-nd-title", "nd_title", "Case title"))
add(control("ct-nd-desc", "nd_desc", "What is being disputed", "text-area"))
add(control(
    "ct-dp-author", "comment_author", "Commenting as", "segmented", "Finance",
    source={"kind": "manual", "valueType": "text",
            "values": ["Account Manager", "Finance"],
            "labels": ["Account Manager", "Finance"]},
))
add(control("ct-dp-comment", "dispute_comment", "Add a comment", "text-area"))
add(control("ct-dp-resolution", "resolution_note", "Resolution note", "text-area"))

# Dispute actions.
DISPUTE_REFRESH = [
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-dispute"}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-dispute"}},
]
DISPUTE_ROW = {"type": "formula", "formula": "[Dispute ID] = [dispute_selected]"}

add(button("b-dispute-new", "+ File a dispute", [
    {"effect": "open-overlay", "overlayId": "m-dispute-new"},
], GREEN, INK))


def seed_dispute(ticket, am, scenario, dtype, priority, amount, title, desc,
                 status, resolution=None):
    """One sample dispute, inserted as a real registry row (constants only).

    No public API inserts input-table rows, so a one-click seed button is how a
    fresh demo is populated. Ticket ids are explicit constants (unique), and the
    open stages stamp Now() into the matching SLA date so the queue looks worked.
    """
    def txt(v):
        return {"type": "constant", "value": {"type": "text", "value": v}}

    def num(v):
        return {"type": "constant", "value": {"type": "number", "value": v}}

    def now():
        return {"type": "formula", "formula": "Now()"}

    values = {"dp-ticket": txt(ticket), "dp-am": txt(am), "dp-scenario": txt(scenario),
              "dp-type": txt(dtype), "dp-priority": txt(priority), "dp-amount": num(amount),
              "dp-title": txt(title), "dp-desc": txt(desc), "dp-status": txt(status)}
    if status in ("In Review", "Escalated", "Resolved"):
        values["dp-inreview"] = now()
    if status == "Escalated":
        values["dp-esc"] = now()
    if status == "Resolved":
        values["dp-resolved"] = now()
        values["dp-resolution"] = txt(resolution or "Adjusted and closed.")
    return {"effect": "insert-rows", "table": "it-dispute", "values": values}


# Six realistic disputes across the full lifecycle so the KPIs, both charts and
# the queue all populate from one click.
add(button("b-dispute-seed", "⤓ Load sample disputes", [
    seed_dispute("DSP-1001", "Maya Chen", "Growth Accelerator", "Rate or tier",
                 "High", 4200, "Tier 3 rate not applied above target",
                 "Attainment cleared the Tier 3 boundary but payout used the "
                 "Tier 2 rate.", "Submitted"),
    seed_dispute("DSP-1002", "Jordan Ellis", "Base Plan", "Fill-quality modifier",
                 "Medium", 1800, "Fill modifier penalized facility cancellations",
                 "Late facility cancellations dropped my fill rate below 82% and "
                 "cut the modifier — those shifts were filled.", "In Review"),
    seed_dispute("DSP-1003", "Marcus Reed", "Retention Weighted", "Missing facility credit",
                 "Critical", 7600, "Cedar Creek recovery not credited",
                 "Critical-account recovery at Cedar Creek Skilled Nursing is not "
                 "reflected in commissionable gross profit.", "Escalated"),
    seed_dispute("DSP-1004", "Lena Ortiz", "Growth Accelerator", "Quota",
                 "Medium", 3100, "Quota factor above signed plan",
                 "Quota factor applied is 1.08; my signed plan is 1.00.", "Submitted"),
    seed_dispute("DSP-1005", "Evan Brooks", "Base Plan", "Clawback",
                 "High", 5400, "Clawback on shifts that were filled",
                 "Clawback applied to shifts that were filled and worked; looks "
                 "like a late-cancel misclassification.", "In Review"),
    seed_dispute("DSP-1006", "Priya Nair", "Retention Weighted", "Rate or tier",
                 "Low", 900, "Rounding on tier boundary",
                 "Small rounding difference at the tier boundary.", "Resolved",
                 resolution="Confirmed rounding; corrected in next payout run."),
] + DISPUTE_REFRESH, CARD, INK, "outline"))
add(button("b-dispute-create", "✓ Create dispute", [
    {"effect": "insert-rows", "table": "it-dispute", "values": {
        # Generated on insert with a scalar formula — never asked of the user.
        "dp-ticket": {"type": "formula",
                      "formula": '"DSP-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
        "dp-am": {"type": "control", "control": "nd_am"},
        "dp-scenario": {"type": "control", "control": "nd_scenario"},
        "dp-type": {"type": "control", "control": "nd_type"},
        "dp-priority": {"type": "control", "control": "nd_priority"},
        "dp-amount": {"type": "formula", "formula": "Number([nd_amount])"},
        "dp-title": {"type": "control", "control": "nd_title"},
        "dp-desc": {"type": "control", "control": "nd_desc"},
        "dp-status": {"type": "constant", "value": {"type": "text", "value": "Submitted"}},
    }},
] + DISPUTE_REFRESH + [
    {"effect": "clear-control", "scope": {"type": "control", "control": "nd_am"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "nd_scenario"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "nd_amount"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "nd_title"}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "nd_desc"}},
    {"effect": "close-overlay"},
], GREEN, INK))
add(button("b-dispute-cancel", "Cancel", [{"effect": "close-overlay"}],
           CARD, INK, "outline"))
add(button("b-dispute-comment", "✓ Add comment", [
    {"effect": "insert-rows", "table": "it-dispute-log", "values": {
        "dl-ticket": {"type": "control", "control": "dispute_selected"},
        "dl-author": {"type": "control", "control": "comment_author"},
        "dl-comment": {"type": "control", "control": "dispute_comment"}}},
    {"effect": "clear-control", "scope": {"type": "control", "control": "dispute_comment"}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-dispute-log"}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-dispute-thread"}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "it-dispute"}},
], INK))
add(button("b-dispute-review", "▶ Start review", [
    {"effect": "update-rows", "table": "it-dispute", "whichRows": DISPUTE_ROW,
     "values": {"dp-status": {"type": "constant", "value": {"type": "text", "value": "In Review"}},
                "dp-inreview": {"type": "formula", "formula": "Now()"}}},
] + DISPUTE_REFRESH, GREEN, INK))
add(button("b-dispute-escalate", "▲ Escalate", [
    {"effect": "update-rows", "table": "it-dispute", "whichRows": DISPUTE_ROW,
     "values": {"dp-status": {"type": "constant", "value": {"type": "text", "value": "Escalated"}},
                "dp-esc": {"type": "formula", "formula": "Now()"}}},
] + DISPUTE_REFRESH, ALARM, "#FFFFFF"))
add(button("b-dispute-resolve", "✓ Resolve dispute", [
    {"effect": "update-rows", "table": "it-dispute", "whichRows": DISPUTE_ROW,
     "values": {"dp-status": {"type": "constant", "value": {"type": "text", "value": "Resolved"}},
                "dp-resolved": {"type": "formula", "formula": "Now()"},
                "dp-resolution": {"type": "control", "control": "resolution_note"}}},
] + DISPUTE_REFRESH + [
    {"effect": "clear-control", "scope": {"type": "control", "control": "resolution_note"}},
    {"effect": "close-overlay"},
], GREEN, INK))
add(button("b-dispute-close", "Close", [{"effect": "close-overlay"}], CARD, INK, "outline"))


# ------------------------------------------------------------------- chrome
# Slim app bar, not a hero banner. The first version was nine grid rows of mostly
# empty dark space with the logo floating in the middle of it. Dashboard
# convention: a thin branded bar carrying logo + wordmark + navigation, then the
# page title on the canvas where it reads at normal weight.
#
# Navigation is BUTTONS rather than the `navigation` element on purpose: that
# element only accepts optionStyle.style "pill" (every other value is rejected
# with a masked Invalid kind), while buttons let each page render its own tab
# filled and the rest ghosted — a real active state a single nav cannot express.
NAV_PAGES = [
    ("Marketplace pulse", "pg-pulse"),
    ("Action workspace", "pg-action"),
    ("Commission modeling", "pg-commission"),
    ("Disputes", "pg-dispute"),
]


def brand_header(page_num, title, subtitle, active_page):
    add({"id": "hdr-%d" % page_num, "kind": "container", "spacing": "small",
         "style": {"backgroundColor": INK, "borderRadius": "round",
                   "borderColor": INK, "borderWidth": 1}})
    if LOGO_URI:
        add({"id": "logo-%d" % page_num, "kind": "image",
             "source": {"kind": "url", "url": LOGO_URI},
             "style": {"fit": "contain", "align": "start",
                       "backgroundColor": "transparent", "padding": "none"}})
    else:
        add(text("logo-%d" % page_num, '<span style="color: %s">**\u219f**</span>' % GREEN))
    add(text("word-%d" % page_num,
             '<span style="color:#FFFFFF;font-size:17px">**shiftkey**</span>'
             '<span style="color:%s;font-size:13px">  MARKETPLACE INTELLIGENCE</span>'
             % TEAL,
             style={"backgroundColor": "transparent", "padding": "none"},
             verticalAlign="middle"))
    for idx, (label, pid) in enumerate(NAV_PAGES):
        is_active = pid == active_page
        add({"id": "nav-%d-%d" % (page_num, idx), "kind": "button", "text": label,
             "appearance": "filled" if is_active else "outline",
             "style": {"backgroundColor": GREEN if is_active else INK,
                       "color": INK if is_active else "#FFFFFF"},
             "actions": [{"id": "act-nav-%d-%d" % (page_num, idx),
                          "trigger": "on-click",
                          "effects": [{"effect": "navigate",
                                       "target": {"type": "page", "page": pid}}]}]})
    add(text("title-%d" % page_num,
             '<span style="color:%s;font-size:23px">**%s**</span>' % (INK, title),
             style={"backgroundColor": "transparent", "padding": "none"},
             verticalAlign="middle"))
    add(text("sub-%d" % page_num,
             '<span style="color:%s;font-size:13px">%s</span>' % (MUTED, subtitle),
             style={"backgroundColor": "transparent", "padding": "none"},
             verticalAlign="middle"))


brand_header(
    1, "Marketplace control tower",
    "One governed path from national fill rate to facility, credential and the next action.",
    "pg-pulse",
)
brand_header(
    2, "From insight to action",
    "Account and supply teams work the same constraint queue — without exporting to a spreadsheet.",
    "pg-action",
)
brand_header(
    3, "Commission & exceptions",
    "Model payout tiers on governed marketplace economics, then submit one scenario for finance review.",
    "pg-commission",
)
brand_header(
    4, "Commission disputes",
    "Account managers file payout disputes; finance works each case through review, escalation and resolution — with a full comment trail.",
    "pg-dispute",
)

add(text(
    "decision",
    '<span style="color:%s">**THE DECISION**</span>  '
    '<span style="color:%s">Where is credentialed supply failing to meet facility demand — '
    'and which client or professional conversation happens today?</span>' % (GREEN, INK),
))
add(band("sec-trend", "Marketplace liquidity", TEAL))
add(band("sec-gap", "Where coverage breaks", TEAL))
add(band("sec-drill", "Actual vs plan — expand region → state → market → facility", INK))
add(band("sec-queue", "Facility action queue — select a row for the call brief", INK))
add(band("sec-supply", "Supply activation — market × credential", TEAL))
add(band("sec-comm-outcome", "Scenario outcomes", TEAL))
add(band("sec-comm-owner", "Scenario outcomes by account manager", TEAL))
add(band("sec-comm-time", "Scenario impact over time", TEAL))
add(band("sec-comm-registry", "Scenario registry — plans users created", INK))
add(band("sec-dispute-queue", "Dispute queue — select a row to work the case", INK))
add(band("sec-dispute-mix", "Where disputes concentrate", TEAL))
add(band("sec-pulse-credential", "Coverage gap by credential", TEAL))
add(band("sec-pulse-analyst", "Ask the marketplace analyst", INK))
add(text(
    "dispute-new-copy",
    "### File a commission dispute\n"
    "Name the account manager, the scenario in question, and the amount. A Dispute "
    "ID is generated automatically and the case enters the queue as **Submitted** "
    "for finance to review.",
    style={"backgroundColor": "transparent"},
))
add(text(
    "dispute-detail-copy",
    '**Dispute {{[dispute_selected]}}** — move it through review, add to the comment '
    'trail, and record a resolution. Status changes stamp the SLA dates, and the '
    'comment log keeps a full audit trail per ticket.',
    style={"backgroundColor": "transparent"},
))
add(text("sec-dispute-thread",
         '<span style="color:%s">**COMMENT TRAIL**</span>' % MUTED))

def region_fill_formula(region):
    return (
        '(SumIf([Marketplace Activity/Filled Shifts], '
        '[Marketplace Activity/Region] = "%(r)s") / NullIf(SumIf('
        '[Marketplace Activity/Posted Shifts], '
        '[Marketplace Activity/Region] = "%(r)s"), 0))' % {"r": region}
    )


_MT = region_fill_formula("Mountain")
_SC = region_fill_formula("South Central")
_MW = region_fill_formula("Midwest")
_SE = region_fill_formula("Southeast")
# Rank the four regional fill rates deterministically in Sigma. Cortex receives
# the already-resolved priority region; it explains the actions rather than
# being asked to perform metric ranking.
_PRIORITY_REGION = (
    'If(%(mt)s <= %(sc)s, '
    'If(%(mt)s <= %(mw)s, If(%(mt)s <= %(se)s, "Mountain", "Southeast"), '
    'If(%(mw)s <= %(se)s, "Midwest", "Southeast")), '
    'If(%(sc)s <= %(mw)s, If(%(sc)s <= %(se)s, "South Central", "Southeast"), '
    'If(%(mw)s <= %(se)s, "Midwest", "Southeast")))' %
    {"mt": _MT, "sc": _SC, "mw": _MW, "se": _SE}
)
_PRIORITY_RATE = (
    'If(%(mt)s <= %(sc)s, '
    'If(%(mt)s <= %(mw)s, If(%(mt)s <= %(se)s, %(mt)s, %(se)s), '
    'If(%(mw)s <= %(se)s, %(mw)s, %(se)s)), '
    'If(%(sc)s <= %(mw)s, If(%(sc)s <= %(se)s, %(sc)s, %(se)s), '
    'If(%(mw)s <= %(se)s, %(mw)s, %(se)s)))' %
    {"mt": _MT, "sc": _SC, "mw": _MW, "se": _SE}
)

AI_PROMPT = (
    '"You are ShiftKey marketplace operations. Write TWO sentences, 45-65 words. '
    'First: explain why the supplied priority region is below the 90 percent fill '
    'plan. Second: state one demand-side account action and one supply-side activation '
    'action. Do not re-rank regions or restate all KPIs. The governed calculation says '
    'the priority region is " & ' + _PRIORITY_REGION + ' & " at " & '
    'Text(Round((' + _PRIORITY_RATE + ') * 100, 1)) & '
    '" percent fill versus a 90 percent plan."'
)
add({"id": "c-ai", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": "#EFF8F1", "borderRadius": "round",
               "borderColor": "#C9E8D0", "borderWidth": 1}})
add({"id": "txt-ai", "kind": "text",
     "body": '<span style="color:%s">**CORTEX MARKETPLACE BRIEF**</span>  '
             '{{Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", "CLAUDE-4-SONNET", '
             % GOOD + AI_PROMPT + "), '\"', \"\")}}",
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

add({"id": "pulse-action", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": CARD, "borderRadius": "round",
               "borderColor": RULE, "borderWidth": 1}})
add(text(
    "txt-action-pulse",
    '<span style="color:%s">**● LIVE ACTION SIGNAL**</span>　'
    '<span style="color:%s">CRITICAL FACILITIES</span> '
    '<span style="color:%s">**{{CountDistinct(If([Facility Performance/Risk Tier] = "Critical", '
    '[Facility Performance/Facility ID], Null)) | ,d}}**</span>　'
    '<span style="color:%s">OPEN EXPOSURE</span> '
    '<span style="color:%s">**{{Sum([Facility Performance/Open Shift Exposure]) | $,.0f}}**</span>　'
    '<span style="color:%s">READY FOR OUTREACH</span> '
    '<span style="color:%s">**{{CountDistinct(If([Facility Action Plan/Workflow Status] = '
    '"Ready for outreach", [Facility Action Plan/Facility ID], Null)) | ,d}}**</span>'
    % (GREEN, MUTED, ALARM, MUTED, INK, MUTED, GREEN),
    style={"backgroundColor": "transparent", "padding": "none"},
    verticalAlign="middle",
))

add({"id": "c-comm-ai", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": "#EFF8F1", "borderRadius": "round",
               "borderColor": "#C9E8D0", "borderWidth": 1}})
add({"id": "txt-comm-ai", "kind": "text",
     "body": '<span style="color:%s">**CORTEX SCENARIO READ**</span>  '
             '{{Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", "CLAUDE-4-SONNET", '
             '"You are ShiftKey sales compensation finance. In two sentences, '
             'assess the selected scenario for payout cost, attainment distribution '
             'and whether its quality modifier aligns account-manager incentives with '
             'facility fill. Be quantitative and do not invent metrics. Scenario " & '
             'Coalesce([commission_scenario], "all scenarios") & ": total payout $" & '
             'Text(Round(Sum([Commission Scenario Grid/Final Payout]),0)) & '
             '", commissionable gross profit $" & '
             'Text(Round(Sum([Commission Scenario Grid/Commissionable Gross Profit]),0)) & '
             '", average attainment " & '
             'Text(Round(Avg([Commission Scenario Grid/Attainment])*100,1)) & '
             '" percent, average fill " & '
             'Text(Round(Avg([Commission Scenario Grid/Fill Rate])*100,1)) & " percent."'
             "), '\"', \"\")}}" % GOOD,
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

add({"id": "tabs-persona", "kind": "tabbed-container",
     "tabs": [{"name": "Account Team"}, {"name": "Supply Ops"}],
     "tabBar": {"visibility": "shown", "style": "button",
                "alignment": "end", "size": "small"},
     "spacing": "small", "style": {"backgroundColor": PAPER}})

for cid in ("kpi-pulse", "filters-pulse", "pivot-wrap", "analyst-wrap",
            "comm-outcome-wrap", "comm-owner-wrap", "comm-time-wrap",
            "kpi-action", "queue-wrap", "supply-wrap",
            "kpi-commission", "comm-controls", "comm-registry",
            "kpi-dispute", "dispute-controls", "dispute-queue-wrap", "dispute-mix"):
    add({"id": cid, "kind": "container", "spacing": "small",
         "style": {"backgroundColor": CARD, "borderRadius": "round",
                   "borderColor": RULE, "borderWidth": 1}})


# ---------------------------------------------------------- action modal copy
add(text(
    "modal-copy",
    'Use the governed anomaly, assign an owner, and record the next action. '
    '**Ready for outreach** stages the facility for CRM/Twilio handoff; this demo '
    'does not send production messages.',
    style={"backgroundColor": "transparent"},
))
add(text(
    "commission-modal-copy",
    'Review **{{Coalesce([commission_scenario], "the selected scenario")}}** '
    'against governed gross profit, attainment '
    'and fill quality. The decision is written to the scenario registry, so it '
    'applies to every account-manager row in the scenario and stays in the audit trail.',
    style={"backgroundColor": "transparent"},
))
add(text(
    "scenario-modal-copy",
    "### Model a new commission plan\n"
    "Name the plan and set its assumptions. Blank fields inherit the governed "
    "default. The new scenario is created as a real row, selected immediately, and "
    "cross-joined onto every account manager — then tune per-AM overrides in the grid.",
    style={"backgroundColor": "transparent"},
))


# ------------------------------------------------------- Marketplace Copilot
# A Sigma agent grounded in the SAME governed tables the tiles use, with action
# tools that drive the real controls and the Facility Action Plan input table.
# Every tool writes only constants, control values, or formula-scoped rows -- no
# per-row action-value formula (which has no row context from a chat/button).
add(text("copilot-hd",
         '<span style="color:%s">**◆ MARKETPLACE COPILOT**</span>　'
         '<span style="color:%s">Ask, filter, and stage — grounded in the '
         'governed metrics</span>' % (GREEN, MUTED),
         style={"backgroundColor": "transparent", "padding": "none"},
         verticalAlign="middle"))
add({"id": "chat-copilot", "kind": "chat", "agentId": "ag-market"})

agents = [{
    "id": "ag-market",
    "name": "Marketplace Copilot",
    "description": ("Answers ShiftKey marketplace fill, coverage and margin "
                    "questions and drives the facility action queue."),
    "instructions": (
        "You are ShiftKey's marketplace operations copilot. The data covers posted, "
        "filled and unfilled shifts across region, state, market, facility, facility "
        "type, credential (CNA, CMA, LPN, RN) and shift, over six months, spanning "
        "demand (Marketplace Activity and Facility Performance) and supply (Supply "
        "Coverage), plus the editable Facility Action Plan. Definitions, which you must "
        "not redefine: fill rate = filled shifts / posted shifts; unfilled shifts = "
        "posted - filled; the fill plan is 90 percent; open-shift exposure and revenue "
        "are dollars; marketplace take = (facility bill rate - professional payout) / "
        "facility bill rate; bid depth = bids per posted shift; credential-ready supply "
        "is qualified professionals in the market catchment. Risk tiers are Critical, "
        "Watch and On plan. Always name the specific region, market, facility and "
        "credential, and always separate a demand-side account lever from a supply-side "
        "activation lever. You can also focus, create, submit and approve commission "
        "scenarios, and file commission disputes on an account manager's behalf. Be "
        "concise and quantitative."
    ),
    # Static greeting: generated-mode openings can hang on "Thinking..." in the
    # chat shell and leave the demo with no prompt chips. A concrete opener that
    # names a real critical facility is more reliable for a live prospect walk.
    "greeting": {"mode": "static",
                 "message": "Cedar Creek Skilled Nursing is the top critical "
                            "account in Dallas–Fort Worth. Ask me:\n"
                            "1) Why is fill below the 90% plan, and which region is worst?\n"
                            "2) Focus Mountain and show the credential gap.\n"
                            "3) Stage critical facilities for outreach."},
    "dataSources": [{"kind": "table", "elementId": "sql-market"},
                    {"kind": "table", "elementId": "sql-facility"},
                    {"kind": "table", "elementId": "sql-supply"},
                    {"kind": "table", "elementId": "it-actions"},
                    {"kind": "table", "elementId": "it-scenario-reg"},
                    {"kind": "table", "elementId": "it-dispute"}],
    "tools": [
        {"toolId": "t-region", "kind": "action", "name": "Focus a region",
         "description": "Filter the workbook to one or more marketplace regions.",
         "steps": [{"kind": "effect", "effect": "set-control-value",
                    "control": "region_filter",
                    "value": {"type": "agent-input",
                              "inputName": "Region(s) to focus on"}}]},
        {"toolId": "t-cred", "kind": "action", "name": "Focus a credential",
         "description": "Filter the workbook to one or more credentials (CNA, CMA, LPN, RN).",
         "steps": [{"kind": "effect", "effect": "set-control-value",
                    "control": "credential_filter",
                    "value": {"type": "agent-input",
                              "inputName": "Credential(s) to focus on"}}]},
        {"toolId": "t-risk", "kind": "action",
         "name": "Filter the queue by risk tier",
         "description": "Set the action-queue risk filter (Critical, Watch, On plan).",
         "steps": [{"kind": "effect", "effect": "set-control-value",
                    "control": "risk_filter",
                    "value": {"type": "agent-input",
                              "inputName": "Risk tier(s) to show"}}]},
        {"toolId": "t-stage", "kind": "action",
         "name": "Stage critical facilities for outreach",
         "description": "Mark every critical-risk facility Ready for outreach.",
         "steps": [
             {"kind": "effect", "effect": "update-rows", "table": "it-actions",
              "whichRows": {"type": "formula", "formula": '[Risk Tier] = "Critical"'},
              "values": {"ap-status": {"type": "constant",
                                       "value": {"type": "text",
                                                 "value": "Ready for outreach"}}}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "it-actions"}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "tbl-action-view"}}]},
        {"toolId": "t-clear", "kind": "action", "name": "Clear workflow fields",
         "description": "Reset status, owner, note and next step on every facility.",
         "steps": [
             {"kind": "effect", "effect": "update-rows", "table": "it-actions",
              "whichRows": {"type": "formula", "formula": "True"},
              "values": {
                  "ap-status": {"type": "constant", "value": {"type": "text", "value": None}},
                  "ap-owner": {"type": "constant", "value": {"type": "text", "value": None}},
                  "ap-note": {"type": "constant", "value": {"type": "text", "value": None}},
                  "ap-next": {"type": "constant", "value": {"type": "text", "value": None}}}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "it-actions"}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "tbl-action-view"}}]},
        {"toolId": "t-comm-scenario", "kind": "action",
         "name": "Focus a commission scenario",
         "description": "Select any scenario that exists in the scenario registry.",
         "steps": [{"kind": "effect", "effect": "set-control-value",
                    "control": "commission_scenario",
                    "value": {"type": "agent-input",
                              "inputName": "Commission scenario to select"}}]},
        # The copilot can create a scenario, exactly like the New scenario modal.
        # insert-rows values are scalar-only, so the numeric assumptions arrive as
        # agent inputs and are cast with Number(); blanks fall back to the plan.
        {"toolId": "t-comm-create", "kind": "action",
         "name": "Create a commission scenario",
         "description": ("Register a brand-new named commission scenario with its own "
                         "quota factor, tier rates and fill-quality modifier, then "
                         "select it. Use this whenever the user wants to model a plan "
                         "that does not exist yet."),
         "steps": [
             {"kind": "effect", "effect": "insert-rows", "table": "it-scenario-reg",
              "values": {
                  "rg-name": {"type": "agent-input", "inputName": "New scenario name"},
                  "rg-desc": {"type": "agent-input",
                              "inputName": "What this scenario tests"},
                  "rg-order": {"type": "formula", "formula": "99"},
                  "rg-quota-factor": {"type": "agent-input",
                                      "inputName": "Quota factor (1.0 = plan)"},
                  "rg-t1rate": {"type": "agent-input", "inputName": "Tier 1 rate"},
                  "rg-t2rate": {"type": "agent-input", "inputName": "Tier 2 rate"},
                  "rg-t3rate": {"type": "agent-input", "inputName": "Tier 3 rate"},
                  "rg-quality": {"type": "agent-input",
                                 "inputName": "Fill-quality modifier"},
                  "rg-status": {"type": "constant",
                                "value": {"type": "text", "value": "Draft"}}}},
             {"kind": "effect", "effect": "set-control-value",
              "control": "commission_scenario",
              "value": {"type": "agent-input", "inputName": "New scenario name"}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "it-scenario-reg"}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "jn-comm-calc"}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "jn-comm-calc"}}]},
        {"toolId": "t-comm-submit", "kind": "action",
         "name": "Submit the selected commission scenario",
         "description": "Move the selected scenario to Submitted for finance review.",
         "steps": [
             {"kind": "effect", "effect": "update-rows", "table": "it-scenario-reg",
              "whichRows": {"type": "formula",
                            "formula": "[Scenario Name] = [commission_scenario]"},
              "values": {"rg-status": {"type": "constant",
                                       "value": {"type": "text", "value": "Submitted"}}}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "it-scenario-reg"}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "jn-comm-calc"}}]},
        {"toolId": "t-comm-approve", "kind": "action",
         "name": "Approve the selected commission scenario",
         "description": "Finance-approve the scenario and write an audit note.",
         "steps": [
             {"kind": "effect", "effect": "update-rows", "table": "it-scenario-reg",
              "whichRows": {"type": "formula",
                            "formula": "[Scenario Name] = [commission_scenario]"},
              "values": {
                  "rg-status": {"type": "constant",
                                "value": {"type": "text", "value": "Approved"}},
                  "rg-note": {"type": "agent-input",
                              "inputName": "Finance approval note"}}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "it-scenario-reg"}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "jn-comm-calc"}}]},
        # File a commission dispute on an AM's behalf. Dispute ID is generated on
        # insert; amount is cast from the agent's text input.
        {"toolId": "t-dispute-file", "kind": "action",
         "name": "File a commission dispute",
         "description": ("Open a commission dispute ticket for an account manager, "
                         "capturing the scenario, dispute type, amount and a "
                         "description. Use when the user wants to contest a payout."),
         "steps": [
             {"kind": "effect", "effect": "insert-rows", "table": "it-dispute",
              "values": {
                  "dp-ticket": {"type": "formula",
                                "formula": '"DSP-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
                  "dp-am": {"type": "agent-input", "inputName": "Account manager"},
                  "dp-scenario": {"type": "agent-input", "inputName": "Scenario in dispute"},
                  "dp-type": {"type": "agent-input", "inputName": "Dispute type"},
                  "dp-priority": {"type": "agent-input", "inputName": "Priority"},
                  "dp-amount": {"type": "agent-input", "inputName": "Amount in dispute"},
                  "dp-title": {"type": "agent-input", "inputName": "Case title"},
                  "dp-desc": {"type": "agent-input", "inputName": "What is being disputed"},
                  "dp-status": {"type": "constant",
                                "value": {"type": "text", "value": "Submitted"}}}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "it-dispute"}},
             {"kind": "effect", "effect": "refresh-element",
              "target": {"type": "element", "element": "tbl-dispute"}}]},
    ],
}]

# A second, purpose-configured agent for the Marketplace pulse page. Where the
# Action-workspace copilot drives write-back workflows, this one is an analyst:
# it answers the "why is fill below plan" drill questions and reshapes the pulse
# page's own controls (region, credential, month/quarter grain). Same governed
# definitions, narrower toolset, no write actions.
agents.append({
    "id": "ag-pulse",
    "name": "Marketplace Analyst",
    "description": ("Answers marketplace fill, coverage and margin questions on the "
                    "pulse page and reshapes its region, credential and date-grain "
                    "controls."),
    "instructions": (
        "You are ShiftKey's marketplace analyst on the Marketplace Pulse page. The "
        "data covers posted, filled and unfilled shifts across region, state, market, "
        "facility, facility type, credential (CNA, CMA, LPN, RN) and shift over six "
        "months, spanning demand (Marketplace Activity, Facility Performance) and "
        "supply (Supply Coverage). Definitions you must not redefine: fill rate = "
        "filled shifts / posted shifts; unfilled shifts = posted - filled; the fill "
        "plan is 90 percent; open-shift exposure and revenue are dollars; marketplace "
        "take = (facility bill rate - professional payout) / facility bill rate; "
        "credential-ready supply is qualified professionals in the market catchment. "
        "When asked why fill is below plan, name the worst region and the credential "
        "with the largest supply gap, and separate a demand-side account lever from a "
        "supply-side activation lever. You reshape the page with the focus-region, "
        "focus-credential and date-grain tools; you do not write back data. Be concise "
        "and quantitative."
    ),
    "greeting": {"mode": "static",
                 "message": "Fill is 84.9% against a 90% plan. Ask me:\n"
                            "1) Which region is worst, and is it demand or supply?\n"
                            "2) Show the credential with the biggest coverage gap.\n"
                            "3) Switch the trend to quarterly."},
    "dataSources": [{"kind": "table", "elementId": "sql-market"},
                    {"kind": "table", "elementId": "sql-facility"},
                    {"kind": "table", "elementId": "sql-supply"}],
    "tools": [
        {"toolId": "tp-region", "kind": "action", "name": "Focus a region",
         "description": "Filter the pulse page to one or more marketplace regions.",
         "steps": [{"kind": "effect", "effect": "set-control-value",
                    "control": "region_filter",
                    "value": {"type": "agent-input",
                              "inputName": "Region(s) to focus on"}}]},
        {"toolId": "tp-cred", "kind": "action", "name": "Focus a credential",
         "description": "Filter the pulse page to one or more credentials (CNA, CMA, LPN, RN).",
         "steps": [{"kind": "effect", "effect": "set-control-value",
                    "control": "credential_filter",
                    "value": {"type": "agent-input",
                              "inputName": "Credential(s) to focus on"}}]},
        {"toolId": "tp-grain", "kind": "action", "name": "Set the trend date grain",
         "description": "Switch the fill-rate trend between month and quarter.",
         "steps": [{"kind": "effect", "effect": "set-control-value",
                    "control": "date_grain",
                    "value": {"type": "agent-input",
                              "inputName": "Date grain (month or quarter)"}}]},
    ],
})

add(text("pulse-analyst-hd",
         '<span style="color:%s">**◆ MARKETPLACE ANALYST**</span>　'
         '<span style="color:%s">Ask why fill is below plan — the analyst answers '
         'and reshapes this page</span>' % (GREEN, MUTED),
         style={"backgroundColor": "transparent", "padding": "none"},
         verticalAlign="middle"))
add({"id": "chat-pulse", "kind": "chat", "agentId": "ag-pulse"})


# --------------------------------------------------------------- drill pass
DRILL_KINDS = {"bar-chart", "line-chart", "area-chart", "combo-chart",
               "scatter-chart", "pie-chart", "donut-chart", "kpi-chart"}
TECHNICAL_NAMES = {"Activity Key", "Facility ID"}


def add_drill_columns():
    by_id = {e["id"]: e for e in elements}
    for viz in elements:
        if viz.get("kind") not in DRILL_KINDS or viz.get("noDrill"):
            continue
        source = viz.get("source") or {}
        if source.get("kind") != "table":
            continue
        parent = by_id.get(source.get("elementId"))
        if not parent or not isinstance(parent.get("name"), str):
            continue
        names = {c.get("name") for c in viz.get("columns", []) if c.get("name")}
        n = 0
        for source_col in parent.get("columns", []):
            name = source_col.get("name")
            if (not name or name in names or name in TECHNICAL_NAMES
                    or source_col.get("hidden")):
                continue
            n += 1
            passthrough = {
                "id": "%s-drill-%02d" % (viz["id"], n),
                "name": name,
                "formula": "[%s/%s]" % (parent["name"], name),
            }
            if source_col.get("format"):
                passthrough["format"] = source_col["format"]
            viz.setdefault("columns", []).append(passthrough)
            names.add(name)


add_drill_columns()

# `noDrill` is a builder-only marker; strip it before it reaches the API.
for _el in elements:
    _el.pop("noDrill", None)


# ------------------------------------------------------------------- layout
pages = [
    {"id": "pg-pulse", "name": "Marketplace pulse", "backgroundColor": PAPER},
    {"id": "pg-action", "name": "Action workspace", "backgroundColor": PAPER},
    {"id": "pg-commission", "name": "Commission modeling", "backgroundColor": PAPER},
    {"id": "pg-dispute", "name": "Commission disputes", "backgroundColor": PAPER},
    {"id": "pg-data", "name": "Data", "visibility": "hidden", "backgroundColor": PAPER},
]
overlays = [
    {"id": "m-action", "type": "modal", "name": "Facility action",
     "modal": {"width": "small",
               "header": {"title": "Facility action", "showCloseIcon": "shown"},
               "footer": {"primaryCta": {"visible": "hidden"},
                          "secondaryCta": {"visible": "hidden"}}}},
    {"id": "m-commission", "type": "modal", "name": "Finance review",
     "modal": {"width": "small",
               "header": {"title": "Commission scenario review",
                          "showCloseIcon": "shown"},
               "footer": {"primaryCta": {"visible": "hidden"},
                          "secondaryCta": {"visible": "hidden"}}}},
    {"id": "m-scenario", "type": "modal", "name": "New scenario",
     "modal": {"width": "small",
               "header": {"title": "New commission scenario",
                          "showCloseIcon": "shown"},
               "footer": {"primaryCta": {"visible": "hidden"},
                          "secondaryCta": {"visible": "hidden"}}}},
    {"id": "m-dispute-new", "type": "modal", "name": "File a dispute",
     "modal": {"width": "small",
               "header": {"title": "File a commission dispute",
                          "showCloseIcon": "shown"},
               "footer": {"primaryCta": {"visible": "hidden"},
                          "secondaryCta": {"visible": "hidden"}}}},
    {"id": "m-dispute-detail", "type": "modal", "name": "Dispute detail",
     "modal": {"width": "medium",
               "header": {"title": "Work the dispute", "showCloseIcon": "shown"},
               "footer": {"primaryCta": {"visible": "hidden"},
                          "secondaryCta": {"visible": "hidden"}}}},
]

layout = """<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-pulse">
  <Container elementId="hdr-1" type="grid" gridColumn="1 / 25" gridRow="1 / 4"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-1" gridColumn="1 / 3" gridRow="1 / 3"/>
    <Element elementId="word-1" gridColumn="3 / 9" gridRow="1 / 3"/>
    <Element elementId="nav-1-0" gridColumn="9 / 13" gridRow="1 / 3"/>
    <Element elementId="nav-1-1" gridColumn="13 / 17" gridRow="1 / 3"/>
    <Element elementId="nav-1-2" gridColumn="17 / 21" gridRow="1 / 3"/>
    <Element elementId="nav-1-3" gridColumn="21 / 25" gridRow="1 / 3"/>
  </Container>
  <Element elementId="title-1" gridColumn="1 / 15" gridRow="4 / 6"/>
  <Element elementId="sub-1" gridColumn="15 / 25" gridRow="4 / 6"/>
  <Element elementId="decision" gridColumn="1 / 25" gridRow="6 / 8"/>
  <Container elementId="kpi-pulse" type="grid" gridColumn="1 / 25" gridRow="8 / 15"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="k-fill" gridColumn="1 / 6" gridRow="1 / 7"/>
    <Element elementId="k-open" gridColumn="6 / 11" gridRow="1 / 7"/>
    <Element elementId="k-exposure" gridColumn="11 / 16" gridRow="1 / 7"/>
    <Element elementId="k-margin" gridColumn="16 / 21" gridRow="1 / 7"/>
    <Element elementId="k-sami" gridColumn="21 / 25" gridRow="1 / 7"/>
  </Container>
  <Container elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="15 / 19"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-ai" gridColumn="1 / 25" gridRow="1 / 4"/>
  </Container>
  <Container elementId="filters-pulse" type="grid" gridColumn="1 / 25" gridRow="19 / 23"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ct-region" gridColumn="1 / 9" gridRow="1 / 4"/>
    <Element elementId="ct-credential" gridColumn="9 / 17" gridRow="1 / 4"/>
    <Element elementId="ct-grain" gridColumn="17 / 25" gridRow="1 / 4"/>
  </Container>
  <Element elementId="sec-trend" gridColumn="1 / 15" gridRow="23 / 24"/>
  <Element elementId="sec-pulse-analyst" gridColumn="15 / 25" gridRow="23 / 24"/>
  <Element elementId="ch-fill" gridColumn="1 / 15" gridRow="24 / 34"/>
  <Element elementId="sec-gap" gridColumn="1 / 15" gridRow="34 / 35"/>
  <Element elementId="ch-region" gridColumn="1 / 15" gridRow="35 / 45"/>
  <Element elementId="sec-pulse-credential" gridColumn="1 / 15" gridRow="45 / 46"/>
  <Element elementId="ch-credential" gridColumn="1 / 15" gridRow="46 / 56"/>
  <Container elementId="analyst-wrap" type="grid" gridColumn="15 / 25" gridRow="24 / 56"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="pulse-analyst-hd" gridColumn="1 / 25" gridRow="1 / 2"/>
    <Element elementId="chat-pulse" gridColumn="1 / 25" gridRow="2 / 32"/>
  </Container>
  <Element elementId="sec-drill" gridColumn="1 / 25" gridRow="56 / 57"/>
  <Container elementId="pivot-wrap" type="grid" gridColumn="1 / 25" gridRow="57 / 69"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="pvt-variance" gridColumn="1 / 25" gridRow="1 / 12"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-action">
  <Container elementId="hdr-2" type="grid" gridColumn="1 / 25" gridRow="1 / 4"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-2" gridColumn="1 / 3" gridRow="1 / 3"/>
    <Element elementId="word-2" gridColumn="3 / 9" gridRow="1 / 3"/>
    <Element elementId="nav-2-0" gridColumn="9 / 13" gridRow="1 / 3"/>
    <Element elementId="nav-2-1" gridColumn="13 / 17" gridRow="1 / 3"/>
    <Element elementId="nav-2-2" gridColumn="17 / 21" gridRow="1 / 3"/>
    <Element elementId="nav-2-3" gridColumn="21 / 25" gridRow="1 / 3"/>
  </Container>
  <Element elementId="title-2" gridColumn="1 / 15" gridRow="4 / 6"/>
  <Element elementId="sub-2" gridColumn="15 / 25" gridRow="4 / 6"/>
  <Container elementId="pulse-action" type="grid" gridColumn="1 / 25" gridRow="6 / 10"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-action-pulse" gridColumn="1 / 25" gridRow="1 / 4"/>
  </Container>
  <Container elementId="kpi-action" type="grid" gridColumn="1 / 25" gridRow="10 / 18"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="k-critical" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="k-action-exp" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="k-ready" gridColumn="13 / 19" gridRow="1 / 8"/>
    <Element elementId="k-action-fill" gridColumn="19 / 25" gridRow="1 / 8"/>
  </Container>
  <TabbedContainer elementId="tabs-persona" gridColumn="1 / 25" gridRow="18 / 65">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="ct-risk" gridColumn="1 / 8" gridRow="1 / 4"/>
      <Element elementId="b-ready" gridColumn="8 / 16" gridRow="1 / 4"/>
      <Element elementId="b-clear" gridColumn="16 / 25" gridRow="1 / 4"/>
      <Element elementId="sec-queue" gridColumn="1 / 17" gridRow="4 / 5"/>
      <Container elementId="queue-wrap" type="grid" gridColumn="1 / 17" gridRow="5 / 24"
                 gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="tbl-action-view" gridColumn="1 / 25" gridRow="1 / 19"/>
      </Container>
      <Element elementId="copilot-hd" gridColumn="17 / 25" gridRow="4 / 5"/>
      <Element elementId="chat-copilot" gridColumn="17 / 25" gridRow="5 / 24"/>
      <Element elementId="ch-facility" gridColumn="1 / 25" gridRow="24 / 40"/>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="sec-supply" gridColumn="1 / 25" gridRow="1 / 2"/>
      <Element elementId="ch-supply" gridColumn="1 / 25" gridRow="2 / 18"/>
      <Container elementId="supply-wrap" type="grid" gridColumn="1 / 25" gridRow="18 / 39"
                 gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="sql-supply" gridColumn="1 / 25" gridRow="1 / 20"/>
      </Container>
    </Tab>
  </TabbedContainer>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-commission">
  <Container elementId="hdr-3" type="grid" gridColumn="1 / 25" gridRow="1 / 4"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-3" gridColumn="1 / 3" gridRow="1 / 3"/>
    <Element elementId="word-3" gridColumn="3 / 9" gridRow="1 / 3"/>
    <Element elementId="nav-3-0" gridColumn="9 / 13" gridRow="1 / 3"/>
    <Element elementId="nav-3-1" gridColumn="13 / 17" gridRow="1 / 3"/>
    <Element elementId="nav-3-2" gridColumn="17 / 21" gridRow="1 / 3"/>
    <Element elementId="nav-3-3" gridColumn="21 / 25" gridRow="1 / 3"/>
  </Container>
  <Element elementId="title-3" gridColumn="1 / 15" gridRow="4 / 6"/>
  <Element elementId="sub-3" gridColumn="15 / 25" gridRow="4 / 6"/>
  <Container elementId="comm-controls" type="grid" gridColumn="1 / 25" gridRow="6 / 11"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ct-comm-scenario" gridColumn="1 / 7" gridRow="1 / 4"/>
    <Element elementId="ct-comm-owner" gridColumn="7 / 13" gridRow="1 / 4"/>
    <Element elementId="b-comm-create" gridColumn="13 / 19" gridRow="1 / 4"/>
    <Element elementId="b-comm-seed" gridColumn="19 / 25" gridRow="1 / 4"/>
    <Element elementId="b-comm-submit" gridColumn="13 / 17" gridRow="4 / 6"/>
    <Element elementId="b-comm-review" gridColumn="17 / 21" gridRow="4 / 6"/>
    <Element elementId="b-comm-reset" gridColumn="21 / 25" gridRow="4 / 6"/>
  </Container>
  <Container elementId="kpi-commission" type="grid" gridColumn="1 / 25" gridRow="11 / 18"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="k-comm-payout" gridColumn="1 / 7" gridRow="1 / 7"/>
    <Element elementId="k-comm-rate" gridColumn="7 / 13" gridRow="1 / 7"/>
    <Element elementId="k-comm-attain" gridColumn="13 / 19" gridRow="1 / 7"/>
    <Element elementId="k-comm-above" gridColumn="19 / 25" gridRow="1 / 7"/>
  </Container>
  <Container elementId="c-comm-ai" type="grid" gridColumn="1 / 25" gridRow="18 / 22"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-comm-ai" gridColumn="1 / 25" gridRow="1 / 4"/>
  </Container>
  <Element elementId="sec-comm-outcome" gridColumn="1 / 13" gridRow="22 / 23"/>
  <Element elementId="sec-comm-owner" gridColumn="13 / 25" gridRow="22 / 23"/>
  <Container elementId="comm-outcome-wrap" type="grid" gridColumn="1 / 13" gridRow="23 / 34"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="tbl-comm-outcome" gridColumn="1 / 25" gridRow="1 / 11"/>
  </Container>
  <Container elementId="comm-owner-wrap" type="grid" gridColumn="13 / 25" gridRow="23 / 34"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="tbl-comm-owner" gridColumn="1 / 25" gridRow="1 / 11"/>
  </Container>
  <Element elementId="ch-comm-owner" gridColumn="1 / 13" gridRow="34 / 44"/>
  <Element elementId="ch-comm-attain" gridColumn="13 / 25" gridRow="34 / 44"/>
  <Element elementId="sec-comm-time" gridColumn="1 / 25" gridRow="44 / 45"/>
  <Container elementId="comm-time-wrap" type="grid" gridColumn="1 / 25" gridRow="45 / 57"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ch-comm-time" gridColumn="1 / 10" gridRow="1 / 12"/>
    <Element elementId="tbl-comm-time" gridColumn="10 / 25" gridRow="1 / 12"/>
  </Container>
  <Element elementId="sec-comm-registry" gridColumn="1 / 25" gridRow="57 / 58"/>
  <Container elementId="comm-registry" type="grid" gridColumn="1 / 25" gridRow="58 / 66"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="it-scenario-reg" gridColumn="1 / 25" gridRow="1 / 7"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-dispute">
  <Container elementId="hdr-4" type="grid" gridColumn="1 / 25" gridRow="1 / 4"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo-4" gridColumn="1 / 3" gridRow="1 / 3"/>
    <Element elementId="word-4" gridColumn="3 / 9" gridRow="1 / 3"/>
    <Element elementId="nav-4-0" gridColumn="9 / 13" gridRow="1 / 3"/>
    <Element elementId="nav-4-1" gridColumn="13 / 17" gridRow="1 / 3"/>
    <Element elementId="nav-4-2" gridColumn="17 / 21" gridRow="1 / 3"/>
    <Element elementId="nav-4-3" gridColumn="21 / 25" gridRow="1 / 3"/>
  </Container>
  <Element elementId="title-4" gridColumn="1 / 15" gridRow="4 / 6"/>
  <Element elementId="sub-4" gridColumn="15 / 25" gridRow="4 / 6"/>
  <Container elementId="dispute-controls" type="grid" gridColumn="1 / 25" gridRow="6 / 10"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ct-dispute-statusf" gridColumn="1 / 9" gridRow="1 / 4"/>
    <Element elementId="b-dispute-seed" gridColumn="11 / 18" gridRow="1 / 4"/>
    <Element elementId="b-dispute-new" gridColumn="18 / 25" gridRow="1 / 4"/>
  </Container>
  <Container elementId="kpi-dispute" type="grid" gridColumn="1 / 25" gridRow="10 / 17"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="k-dp-open" gridColumn="1 / 7" gridRow="1 / 7"/>
    <Element elementId="k-dp-amount" gridColumn="7 / 13" gridRow="1 / 7"/>
    <Element elementId="k-dp-age" gridColumn="13 / 19" gridRow="1 / 7"/>
    <Element elementId="k-dp-esc" gridColumn="19 / 25" gridRow="1 / 7"/>
  </Container>
  <Element elementId="sec-dispute-mix" gridColumn="1 / 25" gridRow="17 / 18"/>
  <Container elementId="dispute-mix" type="grid" gridColumn="1 / 25" gridRow="18 / 29"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="ch-dp-status" gridColumn="1 / 13" gridRow="1 / 11"/>
    <Element elementId="ch-dp-type" gridColumn="13 / 25" gridRow="1 / 11"/>
  </Container>
  <Element elementId="sec-dispute-queue" gridColumn="1 / 25" gridRow="29 / 30"/>
  <Container elementId="dispute-queue-wrap" type="grid" gridColumn="1 / 25" gridRow="30 / 45"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="tbl-dispute" gridColumn="1 / 25" gridRow="1 / 14"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-data">
  <Element elementId="sql-market" gridColumn="1 / 13" gridRow="1 / 16"/>
  <Element elementId="sql-facility" gridColumn="13 / 25" gridRow="1 / 16"/>
  <Element elementId="it-actions" gridColumn="1 / 25" gridRow="16 / 34"/>
  <Element elementId="ct-selected" gridColumn="1 / 7" gridRow="34 / 37"/>
  <Element elementId="sql-commission" gridColumn="7 / 16" gridRow="34 / 48"/>
  <Element elementId="jn-comm-calc" gridColumn="16 / 25" gridRow="34 / 48"/>
  <Element elementId="it-dispute" gridColumn="1 / 13" gridRow="48 / 64"/>
  <Element elementId="it-dispute-log" gridColumn="13 / 25" gridRow="48 / 64"/>
  <Element elementId="ct-dispute-selected" gridColumn="1 / 7" gridRow="64 / 67"/>
  <Element elementId="sql-commission-month" gridColumn="1 / 13" gridRow="67 / 82"/>
  <Element elementId="jn-comm-month" gridColumn="13 / 25" gridRow="67 / 82"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="m-action">
  <Element elementId="modal-copy" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="ct-decision" gridColumn="1 / 25" gridRow="4 / 7"/>
  <Element elementId="ct-action-owner" gridColumn="1 / 13" gridRow="7 / 10"/>
  <Element elementId="ct-next-step" gridColumn="13 / 25" gridRow="7 / 10"/>
  <Element elementId="ct-action-note" gridColumn="1 / 25" gridRow="10 / 15"/>
  <Element elementId="b-cancel-action" gridColumn="1 / 13" gridRow="15 / 18"/>
  <Element elementId="b-save-action" gridColumn="13 / 25" gridRow="15 / 18"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="m-commission">
  <Element elementId="commission-modal-copy" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="ct-comm-decision" gridColumn="1 / 25" gridRow="4 / 7"/>
  <Element elementId="ct-comm-note" gridColumn="1 / 25" gridRow="7 / 12"/>
  <Element elementId="b-comm-cancel" gridColumn="1 / 13" gridRow="12 / 15"/>
  <Element elementId="b-comm-save" gridColumn="13 / 25" gridRow="12 / 15"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="m-dispute-new">
  <Element elementId="dispute-new-copy" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="ct-nd-am" gridColumn="1 / 13" gridRow="4 / 7"/>
  <Element elementId="ct-nd-scenario" gridColumn="13 / 25" gridRow="4 / 7"/>
  <Element elementId="ct-nd-title" gridColumn="1 / 17" gridRow="7 / 10"/>
  <Element elementId="ct-nd-amount" gridColumn="17 / 25" gridRow="7 / 10"/>
  <Element elementId="ct-nd-type" gridColumn="1 / 25" gridRow="10 / 13"/>
  <Element elementId="ct-nd-priority" gridColumn="1 / 25" gridRow="13 / 16"/>
  <Element elementId="ct-nd-desc" gridColumn="1 / 25" gridRow="16 / 20"/>
  <Element elementId="b-dispute-cancel" gridColumn="1 / 13" gridRow="20 / 23"/>
  <Element elementId="b-dispute-create" gridColumn="13 / 25" gridRow="20 / 23"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="m-dispute-detail">
  <Element elementId="dispute-detail-copy" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="b-dispute-review" gridColumn="1 / 9" gridRow="4 / 7"/>
  <Element elementId="b-dispute-escalate" gridColumn="9 / 17" gridRow="4 / 7"/>
  <Element elementId="sec-dispute-thread" gridColumn="1 / 25" gridRow="7 / 8"/>
  <Element elementId="tbl-dispute-thread" gridColumn="1 / 25" gridRow="8 / 18"/>
  <Element elementId="ct-dp-author" gridColumn="1 / 25" gridRow="18 / 21"/>
  <Element elementId="ct-dp-comment" gridColumn="1 / 19" gridRow="21 / 25"/>
  <Element elementId="b-dispute-comment" gridColumn="19 / 25" gridRow="21 / 24"/>
  <Element elementId="ct-dp-resolution" gridColumn="1 / 25" gridRow="25 / 29"/>
  <Element elementId="b-dispute-close" gridColumn="1 / 13" gridRow="29 / 32"/>
  <Element elementId="b-dispute-resolve" gridColumn="13 / 25" gridRow="29 / 32"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="m-scenario">
  <Element elementId="scenario-modal-copy" gridColumn="1 / 25" gridRow="1 / 5"/>
  <Element elementId="ct-new-name" gridColumn="1 / 13" gridRow="5 / 8"/>
  <Element elementId="ct-new-quota" gridColumn="13 / 25" gridRow="5 / 8"/>
  <Element elementId="ct-new-desc" gridColumn="1 / 25" gridRow="8 / 11"/>
  <Element elementId="ct-new-t1" gridColumn="1 / 9" gridRow="11 / 14"/>
  <Element elementId="ct-new-t2" gridColumn="9 / 17" gridRow="11 / 14"/>
  <Element elementId="ct-new-t3" gridColumn="17 / 25" gridRow="11 / 14"/>
  <Element elementId="ct-new-quality" gridColumn="1 / 25" gridRow="14 / 17"/>
  <Element elementId="b-scenario-cancel" gridColumn="1 / 13" gridRow="17 / 20"/>
  <Element elementId="b-scenario-create" gridColumn="13 / 25" gridRow="17 / 20"/>
</Page>"""


# Wrap every section band in a coloured container, since the colour cannot ride
# on the text element itself. Rewrites
#   <Element elementId="sec-x" gridColumn="A / B" gridRow="C / D"/>
# into a container at the same grid slot holding the title text.
def wrap_bands(layout_xml):
    pattern = re.compile(
        r'<Element elementId="(?P<eid>%s)" '
        r'gridColumn="(?P<col>[^"]+)" gridRow="(?P<row>[^"]+)"\s*/>'
        % "|".join(re.escape(k) for k in BAND_COLORS)
    )

    def repl(m):
        eid = m.group("eid")
        wrap_id = eid + "-bg"
        # `spacing` only accepts the named sizes; "none" is rejected by the API.
        add({"id": wrap_id, "kind": "container", "spacing": "small",
             "style": {"backgroundColor": BAND_COLORS[eid],
                       "borderRadius": "round",
                       "borderColor": BAND_COLORS[eid], "borderWidth": 1}})
        return (
            '<Container elementId="%s" type="grid" gridColumn="%s" gridRow="%s" '
            'gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">'
            '<Element elementId="%s" gridColumn="1 / 25" gridRow="1 / 2"/>'
            "</Container>" % (wrap_id, m.group("col"), m.group("row"), eid)
        )

    return pattern.sub(repl, layout_xml)


layout = wrap_bands(layout)


document = {
    "schemaVersion": 1, "kind": "workbook", "elements": elements,
    "pages": pages, "overlays": overlays, "layout": layout, "agents": agents,
    "settings": {
        "theme": {"name": "Light", "overrides": {
            "colors": {"text": INK, "surface": CARD, "highlight": GREEN,
                       "success": GOOD, "warning": WARN, "danger": ALARM},
            "categoricalScheme": [GREEN, INK, TEAL, WARN, ALARM, "#7D8A91"],
            "borderRadius": "round", "hasCards": "shown",
            "elementBorder": {"color": RULE, "width": 1},
            "space": {"unit": "medium", "showElementPadding": "shown"},
            "tableStyles": {"preset": "presentation", "cellSpacing": "small",
                            "gridLines": "horizontal", "banding": "shown",
                            "bandingColor": CARD_ALT},
            "pageWidth": "large",
        }},
        "navigation": {"pageHeader": "disabled", "pageTabsInViewMode": "hidden"},
    },
}

body = {
    "name": "ShiftKey — Marketplace Control Tower",
    "folderId": FOLDER,
    "description": (
        "Governed actual-vs-plan marketplace intelligence with complete drill context, "
        "Cortex narrative, and a facility/supply action workflow. Illustrative data."
    ),
    "document": document,
}


def call(method, path, payload=None):
    req = urllib.request.Request(
        BASE.rstrip("/") + path,
        data=(json.dumps(payload).encode() if payload is not None else None),
        method=method,
        headers={"Authorization": "Bearer " + TOKEN,
                 "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


if __name__ == "__main__":
    if len(_ARGS) < 4:
        print(json.dumps(body, indent=2))
        raise SystemExit(0)

    status, who = call("GET", "/v2/whoami")
    org_id = who.get("organizationId") if isinstance(who, dict) else None
    if status >= 400 or org_id != PAPERCRANE_ORG_ID:
        raise SystemExit(
            "Refusing to build outside papercranestaging: authenticated org is "
            "%s, expected %s. demeng is read-only." % (org_id, PAPERCRANE_ORG_ID)
        )

    status, result = call("POST", "/v2/workbooks/spec/verify", body)
    print("verify", status, result)
    if status >= 400 or not (isinstance(result, dict) and result.get("valid")):
        raise SystemExit(1)
    status, result = call("POST", "/v2/workbooks/spec", body)
    print("create", status, result)
    raise SystemExit(0 if status < 400 else 1)
