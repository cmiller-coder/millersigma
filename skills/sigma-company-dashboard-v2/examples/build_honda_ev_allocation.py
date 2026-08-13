import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

# Usage:
#   python3 build_honda_ev_allocation.py                      # print the spec only
#   python3 build_honda_ev_allocation.py <BASE> <TOKEN> <CONNECTION_ID> <FOLDER_ID>
#
# CONNECTION_ID must be a warehouse connection with Sigma write-back enabled --
# the linked input table and the plan registry both persist there.
#
# The Allocation Pulse plugin is optional. Set HONDA_PULSE_PLUGIN_ID to a plugin
# registered in the target org to include it; leave it unset (the default) to
# build without it. Registering a plugin needs the org's `canDevelopPlugins`
# feature, so the plugin-free build is the portable path.
_ARGS = sys.argv[1:]
BASE = _ARGS[0] if len(_ARGS) > 0 else os.environ.get("SIGMA_BASE_URL", "")
TOKEN = _ARGS[1] if len(_ARGS) > 1 else os.environ.get("SIGMA_API_TOKEN", "")
CONN = _ARGS[2] if len(_ARGS) > 2 else "<connection-id>"
FOLDER = _ARGS[3] if len(_ARGS) > 3 else "<folder-id>"
PULSE_PLUGIN_ID = os.environ.get(
    "HONDA_PULSE_PLUGIN_ID", "<honda-allocation-pulse-plugin-id>"
)
PAPERCRANE_ORG_ID = "8c99818a-90b3-4cae-bdb7-cf69a741171a"

# Honda's corporate wordmark, public domain on Wikimedia Commons. Fetched at build
# time and inlined as a data URI so the workbook needs no external asset host.
# Falls back to a typographic wordmark if the fetch fails -- never hand-draw a mark.
LOGO_SVG_URL = "https://upload.wikimedia.org/wikipedia/commons/7/76/Honda_logo.svg"
try:
    _req = urllib.request.Request(LOGO_SVG_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(_req, timeout=20) as _r:
        LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(_r.read()).decode()
except Exception:
    LOGO_URI = None

# ---- Editorial Ops palette (Honda) ----
PAPER, CARD, CARD_ALT = "#F7F7F5", "#FFFFFF", "#F1F2F0"
RULE, INK, INK_SOFT = "#DEDFDB", "#16181A", "#5C6166"
HONDA, HONDA_DEEP, SILVER = "#CC0000", "#8E0000", "#8A9099"
GOOD, WARN, ALARM = "#0E7C66", "#B4761B", "#CC0000"

INT = {"kind": "number", "formatString": ",d"}
MON = {"kind": "datetime", "formatString": "%b %Y"}
PCT1 = {"kind": "number", "formatString": ".1%"}
DLT = {"kind": "number", "formatString": "+,d"}

elements = []
add = elements.append

# --------------------------------------------------------------- baseline data
ALLOC_SQL = """
WITH months AS (
  SELECT SEQ4() AS m_idx,
         DATEADD('month', SEQ4(), DATE_TRUNC('month', CURRENT_DATE())) AS month_start
  FROM TABLE(GENERATOR(ROWCOUNT => 6))
),
models AS (
  SELECT * FROM VALUES
    ('Civic','Marysville OH',1.00),('Accord','Marysville OH',0.72),
    ('CR-V','East Liberty OH',1.24),('HR-V','Celaya MX',0.61),
    ('Pilot','Lincoln AL',0.54),('Prologue','Ramos Arizpe MX',0.38)
  AS m(model, plant, model_weight)
),
plant_cap AS (
  SELECT * FROM VALUES
    ('Marysville OH',56000),('East Liberty OH',40000),('Celaya MX',20000),
    ('Lincoln AL',16000),('Ramos Arizpe MX',12500)
  AS c(plant, capacity_units)
),
powertrains AS (
  SELECT * FROM VALUES ('ICE',0.0),('HEV',1.5),('PHEV',17.0),('BEV',85.0)
  AS p(powertrain, kwh_per_unit)
),
regions AS (
  SELECT * FROM VALUES
    ('West',0.31),('Central',0.24),('Northeast',0.26),('Southeast',0.19)
  AS r(region, region_share)
),
mix AS (
  SELECT mo.m_idx, mo.month_start, p.powertrain, p.kwh_per_unit,
         CASE p.powertrain
           WHEN 'BEV'  THEN 0.13 + 0.012 * mo.m_idx
           WHEN 'PHEV' THEN 0.07 + 0.004 * mo.m_idx
           WHEN 'HEV'  THEN 0.34 + 0.002 * mo.m_idx
           ELSE              0.46 - 0.018 * mo.m_idx
         END AS mix_share
  FROM months mo CROSS JOIN powertrains p
),
-- Per-month BEV:ICE baseline ratio. Because every powertrain shares the same
-- model/region expansion, this ratio is also the ratio of their unit totals --
-- which is what makes a mix shift volume-neutral (see ice_offset_factor).
shares AS (
  SELECT m_idx,
         MAX(CASE WHEN powertrain = 'BEV' THEN mix_share END) AS bev_share,
         MAX(CASE WHEN powertrain = 'ICE' THEN mix_share END) AS ice_share
  FROM mix GROUP BY m_idx
),
-- Contracted cell supply is sized off the baseline's own cell draw per
-- plant-month, so the plan of record lands inside contract with real but
-- uneven headroom. Mix moves are what consume the remainder.
plant_factor AS (
  SELECT * FROM VALUES
    ('Marysville OH',0.88),('East Liberty OH',0.86),('Celaya MX',0.92),
    ('Lincoln AL',0.84),('Ramos Arizpe MX',0.90)
  AS pf(plant, cell_util_target)
),
plant_cells AS (
  SELECT x.month_start, m.plant,
         SUM(ROUND(30000 * (1 + 0.015 * x.m_idx) * m.model_weight * x.mix_share)
             * x.kwh_per_unit) AS cell_used
  FROM mix x CROSS JOIN models m
  GROUP BY x.month_start, m.plant
)
SELECT
  m.model || '|' || x.powertrain || '|' || r.region || '|'
    || TO_VARCHAR(x.month_start,'YYYYMM')                            AS row_key,
  x.month_start, m.model, m.plant, x.powertrain, r.region,
  ROUND(30000 * (1 + 0.015 * x.m_idx) * m.model_weight
        * x.mix_share * r.region_share)                              AS baseline_units,
  ROUND(30000 * (1 + 0.028 * x.m_idx) * m.model_weight
        * x.mix_share * r.region_share)                              AS demand_units,
  x.kwh_per_unit, c.capacity_units AS plant_capacity,
  0.18 AS bev_mix_target,
  s.bev_share / s.ice_share                                          AS ice_offset_factor,
  ROUND(pc.cell_used / pf.cell_util_target)                          AS cell_kwh_contracted
FROM mix x
CROSS JOIN models m
CROSS JOIN regions r
JOIN plant_cap c    ON c.plant = m.plant
JOIN shares s       ON s.m_idx = x.m_idx
JOIN plant_factor pf ON pf.plant = m.plant
JOIN plant_cells pc ON pc.plant = m.plant AND pc.month_start = x.month_start
""".strip()

# Plant x month capacity/battery grain, aggregated in SQL so utilisation is honest.
PLANT_SQL = """
WITH months AS (
  SELECT SEQ4() AS m_idx,
         DATEADD('month', SEQ4(), DATE_TRUNC('month', CURRENT_DATE())) AS month_start
  FROM TABLE(GENERATOR(ROWCOUNT => 6))
),
models AS (
  SELECT * FROM VALUES
    ('Civic','Marysville OH',1.00),('Accord','Marysville OH',0.72),
    ('CR-V','East Liberty OH',1.24),('HR-V','Celaya MX',0.61),
    ('Pilot','Lincoln AL',0.54),('Prologue','Ramos Arizpe MX',0.38)
  AS m(model, plant, model_weight)
),
plant_cap AS (
  SELECT * FROM VALUES
    ('Marysville OH',56000),('East Liberty OH',40000),('Celaya MX',20000),
    ('Lincoln AL',16000),('Ramos Arizpe MX',12500)
  AS c(plant, capacity_units)
),
powertrains AS (
  SELECT * FROM VALUES ('ICE',0.0),('HEV',1.5),('PHEV',17.0),('BEV',85.0)
  AS p(powertrain, kwh_per_unit)
),
plant_factor AS (
  SELECT * FROM VALUES
    ('Marysville OH',0.88),('East Liberty OH',0.86),('Celaya MX',0.92),
    ('Lincoln AL',0.84),('Ramos Arizpe MX',0.90)
  AS pf(plant, cell_util_target)
),
mix AS (
  SELECT mo.m_idx, mo.month_start, p.powertrain, p.kwh_per_unit,
         CASE p.powertrain
           WHEN 'BEV'  THEN 0.13 + 0.012 * mo.m_idx
           WHEN 'PHEV' THEN 0.07 + 0.004 * mo.m_idx
           WHEN 'HEV'  THEN 0.34 + 0.002 * mo.m_idx
           ELSE              0.46 - 0.018 * mo.m_idx
         END AS mix_share
  FROM months mo CROSS JOIN powertrains p
),
alloc AS (
  SELECT x.month_start, m.plant,
         SUM(ROUND(30000 * (1 + 0.015 * x.m_idx) * m.model_weight * x.mix_share))
           AS allocated_units,
         SUM(ROUND(30000 * (1 + 0.015 * x.m_idx) * m.model_weight * x.mix_share)
             * x.kwh_per_unit) AS cell_kwh_used
  FROM mix x CROSS JOIN models m
  GROUP BY x.month_start, m.plant
)
SELECT a.month_start, a.plant, a.allocated_units, c.capacity_units,
       a.cell_kwh_used,
       ROUND(a.cell_kwh_used / pf.cell_util_target) AS cell_kwh_available
FROM alloc a
JOIN plant_cap c     ON c.plant = a.plant
JOIN plant_factor pf ON pf.plant = a.plant
""".strip()


def sql_table(eid, name, statement, cols, **extra):
    el = {"id": eid, "kind": "table", "name": name, "visibleAsSource": True,
          "source": {"kind": "sql", "connectionId": CONN, "statement": statement},
          "columns": cols, "tableComponents": {"summaryBar": "hidden"},
          "tableStyle": {"preset": "presentation", "cellSpacing": "medium",
                         "textStyles": {"header": {"fontWeight": "bold"}}}}
    el.update(extra)
    return el


def c(cid, name, alias, fmt=None):
    col = {"id": cid, "name": name, "formula": "[Custom SQL/%s]" % alias}
    if fmt:
        col["format"] = fmt
    return col


add(sql_table("sql-alloc", "Allocation Baseline", ALLOC_SQL, [
    c("ab-key", "Row Key", "row_key"), c("ab-month", "Month", "month_start", MON),
    c("ab-model", "Model", "model"), c("ab-plant", "Plant", "plant"),
    c("ab-pt", "Powertrain", "powertrain"), c("ab-region", "Region", "region"),
    c("ab-base", "Baseline Units", "baseline_units", INT),
    c("ab-demand", "Demand Signal", "demand_units", INT),
    c("ab-kwh", "kWh per Unit", "kwh_per_unit"),
    c("ab-cap", "Plant Capacity", "plant_capacity", INT),
    c("ab-target", "BEV Mix Target", "bev_mix_target", PCT1),
    c("ab-offset", "ICE Offset Factor", "ice_offset_factor"),
    c("ab-cellcap", "Cell kWh Contracted", "cell_kwh_contracted", INT),
]))
add(sql_table("sql-plant", "Plant Capacity", PLANT_SQL, [
    c("pc-month", "Month", "month_start", MON), c("pc-plant", "Plant", "plant"),
    c("pc-alloc", "Allocated Units", "allocated_units", INT),
    c("pc-cap", "Capacity Units", "capacity_units", INT),
    c("pc-used", "Cell kWh Used", "cell_kwh_used", INT),
    c("pc-avail", "Cell kWh Available", "cell_kwh_available", INT),
]))

# --------------------------------------------------------------- write-back
add({"id": "it-alloc", "kind": "input-table", "name": "Allocation Plan",
     "inputMode": "view", "source": {"kind": "linked", "from": "sql-alloc"},
     "columns": [
         {"id": "al-key", "key": "ab-key", "hidden": True},
         {"id": "al-month", "key": "ab-month", "name": "Month"},
         {"id": "al-model", "key": "ab-model", "name": "Model"},
         {"id": "al-pt", "key": "ab-pt", "name": "Powertrain"},
         {"id": "al-region", "key": "ab-region", "name": "Region"},
         {"id": "al-plant", "key": "ab-plant", "name": "Plant"},
         {"id": "al-base", "key": "ab-base", "name": "Baseline Units"},
         {"id": "al-demand", "key": "ab-demand", "name": "Demand Signal"},
         {"id": "al-kwh", "key": "ab-kwh", "name": "kWh per Unit", "hidden": True},
         {"id": "al-cap", "key": "ab-cap", "name": "Plant Capacity", "hidden": True},
         {"id": "al-offset", "key": "ab-offset", "name": "ICE Offset Factor",
          "hidden": True},
         {"id": "al-cellcap", "key": "ab-cellcap", "name": "Cell kWh Contracted",
          "hidden": True},
         {"id": "al-prop", "type": "number", "name": "Proposed Units"},
         {"id": "al-note", "type": "text", "name": "Planner Note"},
         # Control-driven scenario. Column formulas CAN read key-bound source
         # columns and control values (unlike action value formulas), so the
         # whole what-if resolves per row at query time.
         {"id": "al-basis", "name": "Basis Units", "hidden": True,
          "formula": 'If([c_basis] = "demand", [Demand Signal], [Baseline Units])'},
         {"id": "al-factor", "name": "Scenario Factor", "hidden": True,
          "formula": 'If([Powertrain] = "BEV", 1 + [c_bev_shift] / 100, '
                     'If([Powertrain] = "ICE", '
                     '1 - [c_bev_shift] / 100 * [ICE Offset Factor], 1))'},
         {"id": "al-scen", "name": "Scenario Units", "hidden": True,
          "formula": "Round([Basis Units] * [Scenario Factor])", "format": INT},
         {"id": "al-eff", "formula": "Coalesce([Proposed Units], [Scenario Units])",
          "name": "Effective Units", "format": INT},
         {"id": "al-var", "formula": "[Effective Units] - [Baseline Units]",
          "name": "Variance", "format": DLT},
         {"id": "al-cells", "formula": "[Effective Units] * [kWh per Unit]",
          "name": "Cell kWh", "format": INT, "hidden": True},
     ],
     "sort": [{"columnId": "al-month", "direction": "ascending", "nulls": "last"},
              {"columnId": "al-model", "direction": "ascending", "nulls": "last"}],
     "tableComponents": {"summaryBar": "hidden"},
     "conditionalFormats": [
         {"type": "single", "columnIds": ["al-prop", "al-note"], "condition": "formula",
          "formula": "True", "style": {"backgroundColor": "#FFFDF3"}},
         {"type": "dataBars", "columnIds": ["al-var"], "scheme": [HONDA, CARD_ALT]},
     ],
     "tableStyle": {"preset": "presentation", "cellSpacing": "small",
                    "banding": "shown", "bandingColor": CARD_ALT,
                    "gridLines": "horizontal",
                    "textStyles": {"header": {"fontWeight": "bold"}}}})

add({"id": "it-registry", "kind": "input-table", "name": "Plan Registry",
     "inputMode": "view", "source": {"kind": "empty", "connectionId": CONN},
     "columns": [
         {"id": "pr-id", "name": "Plan ID", "type": "text"},
         {"id": "pr-name", "name": "Plan Name", "type": "text"},
         {"id": "pr-owner", "name": "Owner", "type": "text"},
         {"id": "pr-scope", "name": "Scope", "type": "text"},
         {"id": "pr-status", "name": "Status", "type": "text",
          "values": ["Draft", "Submitted", "Approved", "Adjust", "Rejected"],
          "pills": "color-by-option"},
         {"id": "pr-comments", "name": "Reviewer Comments", "type": "text"},
         {"id": "ID", "name": "Row ID"}, {"id": "CREATED_AT", "name": "Created At"},
         {"id": "UPDATED_AT", "name": "Updated At"}, {"id": "CREATED_BY", "name": "Created By"},
     ],
     "tableComponents": {"summaryBar": "hidden"},
     "tableStyle": {"preset": "presentation", "cellSpacing": "medium"}})

# Correct-grain plant load, derived from the editable plan.
add({"id": "tbl-load", "kind": "table", "name": "Plant Month Load",
     "source": {"kind": "table", "elementId": "it-alloc"},
     "columns": [
         {"id": "pl-plant", "name": "Plant", "formula": "[Allocation Plan/Plant]"},
         {"id": "pl-month", "name": "Month", "formula": "[Allocation Plan/Month]",
          "format": MON},
         {"id": "pl-eff", "name": "Allocated", "formula": "Sum([Allocation Plan/Effective Units])",
          "format": INT},
         {"id": "pl-cap", "name": "Capacity", "formula": "Max([Allocation Plan/Plant Capacity])",
          "format": INT},
         {"id": "pl-util", "name": "Utilisation", "formula": "[Allocated] / [Capacity]",
          "format": PCT1},
         {"id": "pl-cells", "name": "Cell kWh",
          "formula": "Sum([Allocation Plan/Cell kWh])", "format": INT},
         {"id": "pl-cellcap", "name": "Cell Contract",
          "formula": "Max([Allocation Plan/Cell kWh Contracted])", "format": INT},
         {"id": "pl-cellutil", "name": "Cell Commitment",
          "formula": "[Cell kWh] / [Cell Contract]", "format": PCT1},
         {"id": "pl-id", "name": "Plant Month", "hidden": True,
          "formula": '[Plant] & " · " & DateFormat([Month], "%b %Y")'},
         {"id": "pl-flag", "name": "Capacity Status",
          "formula": 'If([Allocated] > [Capacity], "Over capacity", "Within capacity")'},
         {"id": "pl-cellflag", "name": "Cell Status",
          "formula": 'If([Cell kWh] > [Cell Contract], "Over contract", "Within contract")'},
     ],
     "groupings": [{"id": "g-pl", "groupBy": ["pl-plant", "pl-month"],
                    "calculations": ["pl-eff", "pl-cap", "pl-util", "pl-cells",
                                     "pl-cellcap", "pl-cellutil", "pl-id",
                                     "pl-flag", "pl-cellflag"]}],
     "tableComponents": {"summaryBar": "hidden"},
     "conditionalFormats": [
         {"type": "dataBars", "columnIds": ["pl-util"], "scheme": [GOOD, CARD_ALT]},
         {"type": "dataBars", "columnIds": ["pl-cellutil"], "scheme": [HONDA, CARD_ALT]},
         {"type": "single", "columnIds": ["pl-flag"], "condition": "formula",
          "formula": '[Capacity Status] = "Over capacity"',
          "style": {"backgroundColor": "#FBE9E7", "color": ALARM}},
         {"type": "single", "columnIds": ["pl-flag"], "condition": "formula",
          "formula": '[Capacity Status] = "Within capacity"',
          "style": {"backgroundColor": "#E9F5F1", "color": GOOD}},
         {"type": "single", "columnIds": ["pl-cellflag"], "condition": "formula",
          "formula": '[Cell Status] = "Over contract"',
          "style": {"backgroundColor": "#FBE9E7", "color": ALARM}},
         {"type": "single", "columnIds": ["pl-cellflag"], "condition": "formula",
          "formula": '[Cell Status] = "Within contract"',
          "style": {"backgroundColor": "#E9F5F1", "color": GOOD}},
     ],
     "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
     "visibleAsSource": True})

# --------------------------------------------------------------- KPIs
def kpi(eid, label, source, formula, fmt, comparison=None, comp_formula=None,
        comp_fmt=None, value_color=INK, size=34, direction=None):
    cols = [{"id": eid + "-v", "name": label, "formula": formula, "format": fmt}]
    el = {"id": eid, "kind": "kpi-chart", "name": {"text": label, "color": INK_SOFT,
                                                   "fontSize": 12, "fontWeight": "bold"},
          "source": {"kind": "table", "elementId": source},
          "columns": cols,
          "value": {"columnId": eid + "-v", "color": value_color, "fontSize": size},
          "style": {"backgroundColor": CARD, "borderColor": RULE, "borderWidth": 1},
          "layout": {"anchor": "middle"}}
    if comparison:
        cols.append({"id": eid + "-c", "name": comparison, "formula": comp_formula,
                     "format": comp_fmt or fmt})
        el["comparisonColumn"] = {"columnId": eid + "-c"}
        el["comparison"] = {"display": "delta", "fontSize": 12, "label": comparison}
        # For constraint KPIs (cell commitment) a rising number is bad, and Sigma's
        # default arrow treatment would paint the breach green. `direction: none`
        # shows the gap without asserting a good/bad sign -- and in that mode the
        # API requires colorNeutral rather than colorGood/colorBad.
        if direction == "none":
            el["comparison"]["direction"] = "none"
            el["comparison"]["colorNeutral"] = INK_SOFT
        else:
            el["comparison"]["colorGood"] = GOOD
            el["comparison"]["colorBad"] = WARN
    return el


EFF = "[Allocation Plan/Effective Units]"
add(kpi("k-units", "Plan of record units", "sql-alloc",
        "Sum([Allocation Baseline/Baseline Units])", INT,
        comparison="Demand signal",
        comp_formula="Sum([Allocation Baseline/Demand Signal])"))
add(kpi("k-elec", "Electrified mix", "sql-alloc",
        'Sum(If([Allocation Baseline/Powertrain] <> "ICE", [Allocation Baseline/Baseline Units], 0))'
        " / Sum([Allocation Baseline/Baseline Units])", PCT1,
        comparison="FY goal", comp_formula="0.60", comp_fmt=PCT1))
add(kpi("k-bev", "BEV mix vs target", "sql-alloc",
        'Sum(If([Allocation Baseline/Powertrain] = "BEV", [Allocation Baseline/Baseline Units], 0))'
        " / Sum([Allocation Baseline/Baseline Units])", PCT1,
        comparison="Target", comp_formula="Avg([Allocation Baseline/BEV Mix Target])"))
add(kpi("k-cap", "Plant capacity used", "sql-plant",
        "Sum([Plant Capacity/Allocated Units]) / Sum([Plant Capacity/Capacity Units])", PCT1,
        comparison="Operating ceiling", comp_formula="0.95", comp_fmt=PCT1))
add(kpi("k-cell", "Battery cell used", "sql-plant",
        "Sum([Plant Capacity/Cell kWh Used]) / Sum([Plant Capacity/Cell kWh Available])", PCT1,
        comparison="Cell commitment", comp_formula="0.85", comp_fmt=PCT1))

add(kpi("k-prop", "Proposed units", "it-alloc", "Sum(%s)" % EFF, INT,
        comparison="Plan of record", comp_formula="Sum([Allocation Plan/Baseline Units])"))
add(kpi("k-bev2", "Proposed BEV mix", "it-alloc",
        'Sum(If([Allocation Plan/Powertrain] = "BEV", %s, 0)) / Sum(%s)' % (EFF, EFF), PCT1,
        comparison="Target", comp_formula="Avg([Allocation Plan/BEV Mix Target])"
        if False else "0.18"))
add(kpi("k-shift", "Net unit shift", "it-alloc", "Sum([Allocation Plan/Variance])", DLT))
# The constraint that actually binds when mix moves: assembly volume can be held
# flat while cell draw runs past the contracted pool.
add(kpi("k-cellprop", "Cell commitment", "tbl-load",
        "Sum([Plant Month Load/Cell kWh]) / Sum([Plant Month Load/Cell Contract])",
        PCT1, comparison="Contracted", comp_formula="1.0", comp_fmt=PCT1,
        direction="none"))
add(kpi("k-over", "Plant-months over cell contract", "tbl-load",
        'CountDistinct(If([Plant Month Load/Cell Status] = "Over contract", '
        "[Plant Month Load/Plant Month], Null))", INT, value_color=ALARM))

# --------------------------------------------------------------- charts
add({"id": "ch-mix", "kind": "line-chart", "name": "Powertrain mix by month",
     "source": {"kind": "table", "elementId": "sql-alloc"},
     "columns": [
         {"id": "mx-month", "name": "Month", "formula": '[Allocation Baseline/Month]', "format": MON},
         {"id": "mx-units", "name": "Units", "formula": "Sum([Allocation Baseline/Baseline Units])",
          "format": INT},
         {"id": "mx-pt", "name": "Powertrain", "formula": "[Allocation Baseline/Powertrain]"},
     ],
     "xAxis": {"columnId": "mx-month"}, "yAxis": {"columnIds": ["mx-units"]},
     "color": {"by": "category", "column": "mx-pt"},
     "stacking": "none", "legend": {"position": "top"}})

add({"id": "ch-plant", "kind": "bar-chart", "name": "Allocation vs capacity by plant",
     "source": {"kind": "table", "elementId": "sql-plant"},
     "columns": [
         {"id": "cp-plant", "name": "Plant", "formula": "[Plant Capacity/Plant]"},
         {"id": "cp-alloc", "name": "Allocated", "formula": "Sum([Plant Capacity/Allocated Units])",
          "format": INT},
         {"id": "cp-cap", "name": "Capacity", "formula": "Sum([Plant Capacity/Capacity Units])",
          "format": INT},
     ],
     "xAxis": {"columnId": "cp-plant",
               "sort": {"by": "cp-alloc", "aggregation": "sum", "direction": "descending"}},
     "yAxis": {"columnIds": ["cp-alloc", "cp-cap"]},
     "stacking": "none", "legend": {"position": "top"}})

add({"id": "ch-region", "kind": "bar-chart", "name": "Units by region and powertrain",
     "source": {"kind": "table", "elementId": "sql-alloc"},
     "columns": [
         {"id": "cr-region", "name": "Region", "formula": "[Allocation Baseline/Region]"},
         {"id": "cr-units", "name": "Units",
          "formula": "Sum([Allocation Baseline/Baseline Units])", "format": INT},
         {"id": "cr-pt", "name": "Powertrain", "formula": "[Allocation Baseline/Powertrain]"},
     ],
     "xAxis": {"columnId": "cr-region",
               "sort": {"by": "cr-units", "aggregation": "sum", "direction": "descending"}},
     "yAxis": {"columnIds": ["cr-units"]},
     "color": {"by": "category", "column": "cr-pt"}, "legend": {"position": "top"},
     "stacking": "stacked"})

add({"id": "ch-prop", "kind": "bar-chart", "name": "Proposed vs plan of record",
     "source": {"kind": "table", "elementId": "it-alloc"},
     "columns": [
         {"id": "pv-month", "name": "Month", "formula": "[Allocation Plan/Month]", "format": MON},
         {"id": "pv-base", "name": "Plan of record",
          "formula": "Sum([Allocation Plan/Baseline Units])", "format": INT},
         {"id": "pv-eff", "name": "Proposed", "formula": "Sum(%s)" % EFF, "format": INT},
     ],
     "xAxis": {"columnId": "pv-month"}, "yAxis": {"columnIds": ["pv-base", "pv-eff"]},
     "stacking": "none", "legend": {"position": "top"}})


# --------------------------------------------------------------- controls
def control(eid, cid, name, ctype="text", value="", **extra):
    el = {"id": eid, "kind": "control", "controlId": cid, "name": name,
          "controlType": ctype, "value": value}
    if ctype == "text":
        el.update({"case": "insensitive", "mode": "contains",
                   "includeNulls": "when-no-value-is-selected", "showOperators": False})
    elif ctype in ("number", "date"):
        el.update({"mode": "=", "includeNulls": "when-no-value-is-selected"})
    el.update(extra)
    return el


add(control("ct-region", "c_region", "Region", "list", "",
            mode="include", selectionMode="multiple", values=[],
            source={"kind": "source", "source": {"kind": "table", "elementId": "it-alloc"},
                    "columnId": "al-region"},
            filters=[{"source": {"kind": "table", "elementId": "it-alloc"},
                      "columnId": "al-region"}]))
add(control("ct-pt", "c_powertrain", "Powertrain", "list", "",
            mode="include", selectionMode="multiple", values=[],
            source={"kind": "source", "source": {"kind": "table", "elementId": "it-alloc"},
                    "columnId": "al-pt"},
            filters=[{"source": {"kind": "table", "elementId": "it-alloc"},
                      "columnId": "al-pt"}]))
# Scenario levers are CONTROLS, not write actions. An update-rows value formula
# fired from a button has no row context, so a per-row expression like
# [Baseline Units] cannot be evaluated ("Unknown column"). Driving the scenario
# through computed columns instead is both correct and instant -- no 10k-row
# warehouse write to wait on -- and manual cell edits still persist as genuine
# overrides via Coalesce. Defaults to 0 so the app opens at plan of record.
add(control("ct-shift", "c_bev_shift", "BEV shift %", "number", 0))
add(control("ct-basis", "c_basis", "Plan basis", "segmented", "record",
            source={"kind": "manual", "valueType": "text",
                    "values": ["record", "demand"],
                    "labels": ["Plan of record", "Demand signal"]}))
add(control("ct-plan-name", "c_plan_name", "Plan name"))
add(control("ct-plan-owner", "c_plan_owner", "Owner"))
add(control("ct-sel-plan", "c_selected_plan", "Selected plan"))
add(control("ct-decision", "c_decision", "Decision", "segmented", "Approved",
            source={"kind": "manual", "valueType": "text",
                    "values": ["Approved", "Adjust", "Rejected"],
                    "labels": ["Approve", "Request changes", "Reject"]}))
add(control("ct-review-note", "c_review_note", "Reviewer comments", "text-area"))

# --------------------------------------------------------------- buttons
def button(eid, label, effects, fill=INK, font="#FFFFFF", appearance="filled"):
    return {"id": eid, "kind": "button", "text": label, "appearance": appearance,
            "align": "stretch", "fillColor": fill, "fontColor": font, "fontWeight": "bold",
            "actions": [{"id": "a-" + eid, "trigger": "on-click", "effects": effects}]}


REFRESH = [{"effect": "refresh-element", "target": {"type": "element", "element": e}}
           for e in ("it-alloc", "tbl-load")]

# Only constants and control values are legal in an update-rows value formula
# fired from a button (no row context), so this reset is the one write action
# that belongs on the grid. It clears manual overrides and hands the rows back
# to the control-driven scenario.
add(button("b-clear", "Clear manual overrides", [
    {"effect": "update-rows", "table": "it-alloc",
     "whichRows": {"type": "formula", "formula": "True"},
     "values": {"al-prop": {"type": "constant", "value": {"type": "number", "value": None}},
                "al-note": {"type": "constant", "value": {"type": "text", "value": None}}}}]
    + REFRESH, CARD, INK, "outline"))
add(button("b-newplan", "Create plan", [
    {"effect": "open-overlay", "overlayId": "m-create"}], HONDA))
# A plan identifier is bookkeeping, not something a planner should be asked to
# invent, so it is generated here and never surfaced in the form. This is a
# SCALAR formula (Now() plus concatenation) -- legal in an action value, unlike a
# per-row expression, which has no row to resolve against from a button.
# The identifier is picked up later by the queue's on-select handler, so nothing
# needs to guess it at insert time.
add(button("b-create-save", "Create draft", [
    {"effect": "insert-rows", "table": "it-registry", "values": {
        "pr-id": {"type": "formula",
                  "formula": '"PLAN-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
        "pr-name": {"type": "control", "control": "c_plan_name"},
        "pr-owner": {"type": "control", "control": "c_plan_owner"},
        "pr-scope": {"type": "constant",
                     "value": {"type": "text", "value": "Hybrid vs EV allocation"}},
        "pr-status": {"type": "constant", "value": {"type": "text", "value": "Draft"}}}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-review"}},
    {"effect": "close-overlay"}], GOOD))
add(button("b-create-cancel", "Cancel", [{"effect": "close-overlay"}], CARD, INK, "outline"))
add(button("b-submit", "Submit plan for review", [
    {"effect": "update-rows", "table": "it-registry",
     "whichRows": {"type": "formula", "formula": "[Plan ID] = [c_selected_plan]"},
     "values": {"pr-status": {"type": "constant",
                              "value": {"type": "text", "value": "Submitted"}}}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-review"}}], GOOD))
add(button("b-review-save", "Save decision", [
    {"effect": "update-rows", "table": "it-registry",
     "whichRows": {"type": "formula", "formula": "[Plan ID] = [c_selected_plan]"},
     "values": {"pr-status": {"type": "control", "control": "c_decision"},
                "pr-comments": {"type": "control", "control": "c_review_note"}}},
    {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-review"}},
    {"effect": "close-overlay"}], GOOD))
add(button("b-review-cancel", "Cancel", [{"effect": "close-overlay"}], CARD, INK, "outline"))
add(button("b-goto-app", "Open allocation planner", [
    {"effect": "navigate", "target": {"type": "page", "page": "pg-app"}}], INK))

# review queue with on-select -> decision modal
add({"id": "tbl-review", "kind": "table", "name": "Approval Queue",
     "source": {"kind": "table", "elementId": "it-registry"},
     "columns": [
         {"id": "rv-status", "name": "Status", "formula": "[Plan Registry/Status]"},
         {"id": "rv-name", "name": "Plan Name", "formula": "[Plan Registry/Plan Name]"},
         {"id": "rv-owner", "name": "Owner", "formula": "[Plan Registry/Owner]"},
         {"id": "rv-scope", "name": "Scope", "formula": "[Plan Registry/Scope]"},
         {"id": "rv-note", "name": "Reviewer Comments", "formula": "[Plan Registry/Reviewer Comments]"},
         {"id": "rv-updated", "name": "Updated", "formula": "[Plan Registry/Updated At]"},
         {"id": "rv-id", "name": "Plan ID", "formula": "[Plan Registry/Plan ID]", "hidden": True},
     ],
     "actions": [{"id": "act-review", "trigger": "on-select", "effects": [
         {"effect": "set-control-value", "control": "c_selected_plan",
          "value": {"type": "column", "column": "rv-id"}},
         {"effect": "open-overlay", "overlayId": "m-review"}]}],
     "sort": [{"columnId": "rv-updated", "direction": "descending", "nulls": "last"}],
     "tableComponents": {"summaryBar": "hidden"},
     "tableStyle": {"preset": "presentation", "cellSpacing": "small"}})

# --------------------------------------------------------------- chrome / text
def text(eid, body, **extra):
    el = {"id": eid, "kind": "text", "body": body}
    el.update(extra)
    return el


SERIF = 'font-family: Georgia'
for idx, (head, sub) in enumerate([
        ("Hybrid &amp; EV allocation",
         "Six months of plan of record — and what it costs in assembly capacity and "
         "contracted battery cells to change it."),
        ("Allocation planner",
         "Trade volume between powertrains at constant build, watch the cell contract "
         "answer back, then submit for review.")], start=1):
    add({"id": "c-hdr%d" % idx, "kind": "container", "spacing": "small",
         "style": {"backgroundColor": CARD, "borderRadius": "square",
                   "borderColor": RULE, "borderWidth": 1}})
    if LOGO_URI:
        add({"id": "wm%d" % idx, "kind": "image",
             "source": {"kind": "url", "url": LOGO_URI},
             "style": {"fit": "contain", "align": "start",
                       "backgroundColor": "transparent", "padding": "none"}})
    else:
        add(text("wm%d" % idx,
                 '<span style="font-size: 26px; color: %s">**HONDA**</span>' % HONDA,
                 style={"backgroundColor": "transparent", "padding": "none"},
                 verticalAlign="middle"))
    add(text("eyebrow%d" % idx,
             '<span style="color: %s">**HONDA · NORTH AMERICA PLANNING**</span>' % HONDA,
             style={"backgroundColor": "transparent", "padding": "none"},
             verticalAlign="end"))
    add(text("ttl%d" % idx,
             '# **<span style="%s; color: %s">%s</span>**' % (SERIF, INK, head),
             style={"backgroundColor": "transparent", "padding": "none"},
             verticalAlign="middle"))
    add(text("sub%d" % idx, '<span style="color: %s">%s</span>' % (INK_SOFT, sub),
             style={"backgroundColor": "transparent", "padding": "none"},
             verticalAlign="start"))
    add({"id": "nav%d" % idx, "kind": "navigation", "mode": "manual", "showIcons": False,
         "style": {"backgroundColor": "transparent"},
         "optionStyle": {"textColor": INK_SOFT, "selectedColor": HONDA,
                         "style": "pill", "orientation": "horizontal"},
         "options": [
             {"label": "Executive overview", "destination": {"type": "page", "pageId": "pg-exec"}},
             {"label": "Allocation planner", "destination": {"type": "page", "pageId": "pg-app"}}]})
add(text("q-exec", '<span style="color: %s">**THE DECISION**</span>  '
                   '<span style="color: %s">Buyers moved to hybrid faster than the EV plan assumed. '
                   'How much volume do we re-trade — and what breaks when we do?</span>'
                   % (HONDA, INK)))
add({"id": "c-insight", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": "#FFF8F7", "borderRadius": "square",
               "borderColor": "#F2D6D2", "borderWidth": 1}})
add(text("insight",
         '<span style="color: %s">**WHERE THE PLAN IS TIGHT**</span>  '
         '<span style="color: %s">BEV is </span>'
         '<span style="color: %s">**{{Sum(If([Allocation Baseline/Powertrain] = "BEV", '
         '[Allocation Baseline/Baseline Units], 0)) / Sum([Allocation Baseline/Baseline Units]) '
         '| .1%%}}**</span>'
         '<span style="color: %s"> of the plan against an 18.0%% target, while plants run at </span>'
         '<span style="color: %s">**{{Sum([Plant Capacity/Allocated Units]) '
         '/ Sum([Plant Capacity/Capacity Units]) | .1%%}}**</span>'
         '<span style="color: %s"> of build capacity and </span>'
         '<span style="color: %s">**{{Sum([Plant Capacity/Cell kWh Used]) '
         '/ Sum([Plant Capacity/Cell kWh Available]) | .1%%}}**</span>'
         '<span style="color: %s"> of contracted cells. Trading ICE for BEV one-for-one '
         'holds build volume flat and still consumes that cell headroom — so the mix '
         'decision is really a battery decision.</span>'
         % (HONDA, INK_SOFT, INK, INK_SOFT, INK, INK_SOFT, INK, INK_SOFT),
         style={"backgroundColor": "transparent", "padding": "none"}))
# --------------------------------------------------------------- AI insight
# Live LLM narration via Snowflake Cortex. A `text` element whose body contains a
# {{formula}} needs no `source`, and the formula may reference other elements.
#
# The insight is only as good as what it is handed. Aggregate totals alone produce
# "cell commitment rose, watch capacity" -- true, useless, and already on screen.
# There are only five plants, so pass each plant's own commitment explicitly and
# the model can name the binding plant and where the headroom actually is.
#
# SumIf over tbl-load's group-level calculations is the same aggregation the
# k-cellprop KPI uses (verified), just sliced per plant.
PLANTS = ["Marysville OH", "East Liberty OH", "Celaya MX",
          "Lincoln AL", "Ramos Arizpe MX"]
_per_plant = ' & ", " & '.join(
    '"%(p)s " & Text(Round('
    'SumIf([Plant Month Load/Cell kWh], [Plant Month Load/Plant] = "%(p)s") '
    '/ NullIf(SumIf([Plant Month Load/Cell Contract], '
    '[Plant Month Load/Plant] = "%(p)s"), 0) * 100, 0)) & "%%"' % {"p": p}
    for p in PLANTS)

_AI_PROMPT = (
    '"You are a Honda North America production planner. Write TWO sentences, '
    '40-60 words total. First sentence: name the plant most over its battery '
    'cell contract, quantify by how many points, and say what to do. Second '
    'sentence: name the plant with the most remaining cell headroom and say how '
    'much mix could move there. Use the real plant names. Do NOT restate the '
    'network totals, they are already on screen. Data: network cell commitment " '
    '& Text(Round(Sum([Plant Month Load/Cell kWh]) '
    '/ NullIf(Sum([Plant Month Load/Cell Contract]), 0) * 100, 1)) & "%%, '
    'plant-months over contract " '
    '& Text(CountDistinct(If([Plant Month Load/Cell Status] = "Over contract", '
    '[Plant Month Load/Plant Month], Null))) & " of " '
    '& Text(CountDistinct([Plant Month Load/Plant Month])) '
    '& ". Assembly utilisation " '
    '& Text(Round(Sum([Plant Month Load/Allocated]) '
    '/ NullIf(Sum([Plant Month Load/Capacity]), 0) * 100, 1)) '
    '& "%%. Cell commitment by plant: " & ' + _per_plant + ' & "."'
)

add({"id": "c-ai", "kind": "container", "spacing": "small",
     "style": {"backgroundColor": "#F4F6F8", "borderRadius": "square",
               "borderColor": "#D8DEE4", "borderWidth": 1}})
add({"id": "txt-ai", "kind": "text",
     "body": '<span style="color: %s">**AI READ ON THE CONSTRAINT**</span>  '
             '{{Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE", "CLAUDE-4-SONNET", '
             % HONDA + _AI_PROMPT + "), '\"', \"\")}}",
     "style": {"backgroundColor": "transparent", "padding": "none"},
     "verticalAlign": "middle"})

add(text("s-mix", '<span style="color: %s">**MIX TRAJECTORY**</span>' % INK_SOFT))
add(text("s-cap", '<span style="color: %s">**CAPACITY POSTURE**</span>' % INK_SOFT))
add(text("s-region", '<span style="color: %s">**REGIONAL MIX**</span>' % INK_SOFT))
add(text("s-grid", '<span style="color: %s">**ALLOCATION GRID — TYPE TO OVERRIDE THE '
                   'SCENARIO**</span>' % INK_SOFT))
add(text("s-queue", '<span style="color: %s">**APPROVAL QUEUE — SELECT A ROW TO DECIDE**</span>' % INK_SOFT))
add(text("s-load", '<span style="color: %s">**PLANT-MONTH LOAD — ASSEMBLY CAPACITY AND '
                   'CELL CONTRACT**</span>' % INK_SOFT))
# The modal header already carries the title, so the body copy says what happens
# next instead of repeating it. No plan ID field: it is generated on insert.
add(text("m-create-help",
         'Name the plan and assign an owner. It is registered as a **Draft** and '
         'appears in the approval queue, where it can be submitted for review.',
         style={"backgroundColor": "transparent"}))
add(text("m-review-help",
         'Record a decision on the selected plan. Comments are written back with '
         'the status so the queue keeps the full audit trail.',
         style={"backgroundColor": "transparent"}))

for cid in ("c-kpi1", "c-app-kpi", "c-grid", "c-queue"):
    add({"id": cid, "kind": "container", "spacing": "small",
         "style": {"backgroundColor": CARD, "borderRadius": "square",
                   "borderColor": RULE, "borderWidth": 1}})

pages = [{"id": "pg-exec", "name": "Executive overview", "backgroundColor": PAPER},
         {"id": "pg-app", "name": "Allocation planner", "backgroundColor": PAPER},
         {"id": "pg-data", "name": "Data", "visibility": "hidden"}]
# Overlay-level footer CTAs cannot resolve controls, so every modal here does its
# work with button elements placed inside the modal page. Leaving the built-in
# primary/secondary CTAs visible would show a second, non-functional pair of
# buttons -- hide them explicitly. `x-small`/`small` keep the dialog dialog-sized;
# `large` reads as a full-width sheet.
_MODAL_FOOTER = {"primaryCta": {"visible": "hidden"},
                 "secondaryCta": {"visible": "hidden"}}
overlays = [
    {"id": "m-create", "type": "modal", "name": "Create plan",
     "modal": {"width": "small", "header": {"title": "Create allocation plan",
                                           "showCloseIcon": "shown"},
               "footer": _MODAL_FOOTER}},
    {"id": "m-review", "type": "modal", "name": "Review plan",
     "modal": {"width": "small", "header": {"title": "Review allocation plan",
                                            "showCloseIcon": "shown"},
               "footer": _MODAL_FOOTER}},
]

logo1 = '    <Element elementId="wm1" gridColumn="1 / 5" gridRow="1 / 3"/>\n'
logo2 = '    <Element elementId="wm2" gridColumn="1 / 5" gridRow="1 / 3"/>\n'

layout = f"""<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-exec">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 9"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
{logo1}    <Element elementId="nav1" gridColumn="13 / 25" gridRow="1 / 3"/>
    <Element elementId="eyebrow1" gridColumn="1 / 13" gridRow="3 / 4"/>
    <Element elementId="ttl1" gridColumn="1 / 17" gridRow="4 / 7"/>
    <Element elementId="sub1" gridColumn="1 / 17" gridRow="7 / 8"/>
    <Element elementId="b-goto-app" gridColumn="19 / 25" gridRow="6 / 8"/>
  </Container>
  <Element elementId="q-exec" gridColumn="1 / 25" gridRow="9 / 11"/>
  <Container elementId="c-insight" type="grid" gridColumn="1 / 25" gridRow="48 / 52"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="insight" gridColumn="1 / 25" gridRow="1 / 4"/>
  </Container>
  <Container elementId="c-kpi1" type="grid" gridColumn="1 / 25" gridRow="11 / 19"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="k-units" gridColumn="1 / 6" gridRow="1 / 8"/>
    <Element elementId="k-elec" gridColumn="6 / 11" gridRow="1 / 8"/>
    <Element elementId="k-bev" gridColumn="11 / 16" gridRow="1 / 8"/>
    <Element elementId="k-cap" gridColumn="16 / 20" gridRow="1 / 8"/>
    <Element elementId="k-cell" gridColumn="20 / 25" gridRow="1 / 8"/>
  </Container>
  <Element elementId="s-mix" gridColumn="1 / 13" gridRow="19 / 20"/>
  <Element elementId="s-cap" gridColumn="13 / 25" gridRow="19 / 20"/>
  <Element elementId="ch-mix" gridColumn="1 / 13" gridRow="20 / 34"/>
  <Element elementId="ch-plant" gridColumn="13 / 25" gridRow="20 / 34"/>
  <Element elementId="s-region" gridColumn="1 / 25" gridRow="34 / 35"/>
  <Element elementId="ch-region" gridColumn="1 / 25" gridRow="35 / 48"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-app">
  <Container elementId="c-hdr2" type="grid" gridColumn="1 / 25" gridRow="1 / 9"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
{logo2}    <Element elementId="nav2" gridColumn="13 / 25" gridRow="1 / 3"/>
    <Element elementId="eyebrow2" gridColumn="1 / 13" gridRow="3 / 4"/>
    <Element elementId="ttl2" gridColumn="1 / 17" gridRow="4 / 7"/>
    <Element elementId="sub2" gridColumn="1 / 17" gridRow="7 / 8"/>
    <Element elementId="b-newplan" gridColumn="19 / 25" gridRow="6 / 8"/>
  </Container>
  <Container elementId="c-app-kpi" type="grid" gridColumn="1 / 25" gridRow="9 / 17"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="k-prop" gridColumn="1 / 7" gridRow="1 / 8"/>
    <Element elementId="k-bev2" gridColumn="7 / 13" gridRow="1 / 8"/>
    <Element elementId="k-shift" gridColumn="13 / 19" gridRow="1 / 8"/>
    <Element elementId="k-over" gridColumn="19 / 25" gridRow="1 / 8"/>
  </Container>
  <Element elementId="ct-basis" gridColumn="1 / 8" gridRow="17 / 20"/>
  <Element elementId="ct-shift" gridColumn="8 / 12" gridRow="17 / 20"/>
  <Element elementId="ct-region" gridColumn="12 / 17" gridRow="17 / 20"/>
  <Element elementId="ct-pt" gridColumn="17 / 21" gridRow="17 / 20"/>
  <Element elementId="b-clear" gridColumn="21 / 25" gridRow="17 / 20"/>
  <Element elementId="s-grid" gridColumn="1 / 25" gridRow="20 / 21"/>
  <Container elementId="c-grid" type="grid" gridColumn="1 / 25" gridRow="21 / 39"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="it-alloc" gridColumn="1 / 25" gridRow="1 / 18"/>
  </Container>
  <Element elementId="ch-prop" gridColumn="1 / 13" gridRow="39 / 53"/>
  <Element elementId="s-load" gridColumn="13 / 25" gridRow="39 / 40"/>
  <Element elementId="tbl-load" gridColumn="13 / 25" gridRow="40 / 53"/>
  <Element elementId="s-queue" gridColumn="1 / 25" gridRow="53 / 54"/>
  <Container elementId="c-queue" type="grid" gridColumn="1 / 25" gridRow="54 / 64"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="tbl-review" gridColumn="1 / 20" gridRow="1 / 10"/>
    <Element elementId="b-submit" gridColumn="20 / 25" gridRow="1 / 4"/>
  </Container>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-data">
  <Element elementId="sql-alloc" gridColumn="1 / 13" gridRow="1 / 14"/>
  <Element elementId="sql-plant" gridColumn="13 / 25" gridRow="1 / 14"/>
  <Element elementId="it-registry" gridColumn="1 / 25" gridRow="14 / 26"/>
  <Element elementId="ct-sel-plan" gridColumn="1 / 7" gridRow="26 / 29"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="m-create">
  <Element elementId="m-create-help" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="ct-plan-name" gridColumn="1 / 25" gridRow="3 / 6"/>
  <Element elementId="ct-plan-owner" gridColumn="1 / 25" gridRow="6 / 9"/>
  <Element elementId="b-create-cancel" gridColumn="1 / 13" gridRow="9 / 12"/>
  <Element elementId="b-create-save" gridColumn="13 / 25" gridRow="9 / 12"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="m-review">
  <Element elementId="m-review-help" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="ct-decision" gridColumn="1 / 25" gridRow="3 / 6"/>
  <Element elementId="ct-review-note" gridColumn="1 / 25" gridRow="6 / 11"/>
  <Element elementId="b-review-cancel" gridColumn="1 / 13" gridRow="11 / 14"/>
  <Element elementId="b-review-save" gridColumn="13 / 25" gridRow="11 / 14"/>
</Page>
"""

# ---------------------------------------------------------------- personas + plugin
# Page 1 is already the executive persona. Page 2 switches between the two
# operational personas: Planner edits allocations; Approver reviews capacity
# exceptions and lifecycle status. The compact plugin is deliberately outside
# the tabs so both personas retain the same live context.
for _eid, _label in {
    "b-goto-app": "→ Open allocation planner",
    "b-newplan": "＋ Create plan",
    "b-clear": "↺ Clear manual overrides",
    "b-submit": "✓ Submit plan for review",
    "b-create-save": "✓ Create draft",
    "b-create-cancel": "× Cancel",
    "b-review-save": "✓ Save decision",
    "b-review-cancel": "× Cancel",
}.items():
    next(e for e in elements if e["id"] == _eid)["text"] = _label

# The Allocation Pulse plugin is optional. Registering a plugin needs the
# `canDevelopPlugins` org feature; when it is unavailable (or no plugin id is
# passed) the workbook is built without the plugin strip and the app page
# reclaims that row. Everything else -- KPIs, personas, input tables, approval
# queue -- is unaffected.
HAS_PULSE = not PULSE_PLUGIN_ID.startswith("<")
if HAS_PULSE:
    add({
        "id": "plg-pulse",
        "kind": "plugin",
        "pluginId": PULSE_PLUGIN_ID,
        "displayName": "Allocation Pulse",
        "config": {
            "mixSource": {"kind": "element", "elementId": "it-alloc"},
            "powertrain": "al-pt",
            "units": "al-eff",
            "capacitySource": {"kind": "element", "elementId": "tbl-load"},
            "allocated": "pl-eff",
            "capacity": "pl-cap",
            "status": "pl-flag",
            "cellUsed": "pl-cells",
            "cellContract": "pl-cellcap",
            "cellStatus": "pl-cellflag",
        },
        "style": {"backgroundColor": "#FFFFFF"},
    })
add({
    "id": "tc-persona",
    "kind": "tabbed-container",
    "tabs": [{"name": "Planner"}, {"name": "Approver"}],
    "tabBar": {
        "visibility": "shown",
        "style": "button",
        "alignment": "end",
        "size": "small",
    },
    "spacing": "small",
    "style": {"backgroundColor": PAPER},
})

# Formula-driven dashboard controls, following the same DateTrunc / Switch
# pattern as the universal v2 builder.
add(control(
    "ct-exec-grain", "ExecDateGrain", "Date grain", "segmented", "month",
    source={"kind": "manual", "valueType": "text",
            "values": ["month", "quarter"],
            "labels": ["Month", "Quarter"]},
))
add(control(
    "ct-exec-series", "ExecSeries", "Color by", "segmented", "Powertrain",
    source={"kind": "manual", "valueType": "text",
            "values": ["Powertrain", "Plant", "Model"],
            "labels": ["Powertrain", "Plant", "Model"]},
))
add(control(
    "ct-app-grain", "AppDateGrain", "Date grain", "segmented", "month",
    source={"kind": "manual", "valueType": "text",
            "values": ["month", "quarter"],
            "labels": ["Month", "Quarter"]},
))

for _col in next(e for e in elements if e["id"] == "ch-mix")["columns"]:
    if _col["id"] == "mx-month":
        _col["formula"] = (
            'DateTrunc([ExecDateGrain], [Allocation Baseline/Month])'
        )
for _col in next(e for e in elements if e["id"] == "ch-region")["columns"]:
    if _col["id"] == "cr-pt":
        _col["name"] = "Series"
        _col["formula"] = (
            'Switch([ExecSeries], "Plant", [Allocation Baseline/Plant], '
            '"Model", [Allocation Baseline/Model], '
            '[Allocation Baseline/Powertrain])'
        )
next(e for e in elements if e["id"] == "ch-region")["name"] = (
    "Units by region and selected series"
)
for _col in next(e for e in elements if e["id"] == "ch-prop")["columns"]:
    if _col["id"] == "pv-month":
        _col["formula"] = (
            'DateTrunc([AppDateGrain], [Allocation Plan/Month])'
        )

# "Use demand signal" used to be a write action with the same no-row-context
# defect; it is now the ct-basis segmented control, which re-bases every row
# instantly through the Basis Units column.

_exec_page = """<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-exec">
  <Container elementId="c-hdr1" type="grid" gridColumn="1 / 25" gridRow="1 / 9"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="wm1" gridColumn="1 / 5" gridRow="1 / 3"/>
    <Element elementId="nav1" gridColumn="13 / 25" gridRow="1 / 3"/>
    <Element elementId="eyebrow1" gridColumn="1 / 13" gridRow="3 / 4"/>
    <Element elementId="ttl1" gridColumn="1 / 17" gridRow="4 / 7"/>
    <Element elementId="sub1" gridColumn="1 / 17" gridRow="7 / 8"/>
    <Element elementId="b-goto-app" gridColumn="19 / 25" gridRow="6 / 8"/>
  </Container>
  <Element elementId="q-exec" gridColumn="1 / 25" gridRow="9 / 11"/>
  <Container elementId="c-kpi1" type="grid" gridColumn="1 / 25" gridRow="11 / 19"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="k-units" gridColumn="1 / 6" gridRow="1 / 8"/>
    <Element elementId="k-elec" gridColumn="6 / 11" gridRow="1 / 8"/>
    <Element elementId="k-bev" gridColumn="11 / 16" gridRow="1 / 8"/>
    <Element elementId="k-cap" gridColumn="16 / 20" gridRow="1 / 8"/>
    <Element elementId="k-cell" gridColumn="20 / 25" gridRow="1 / 8"/>
  </Container>
  <Element elementId="ct-exec-grain" gridColumn="1 / 7" gridRow="19 / 22"/>
  <Element elementId="ct-exec-series" gridColumn="7 / 15" gridRow="19 / 22"/>
  <Element elementId="s-mix" gridColumn="1 / 13" gridRow="22 / 23"/>
  <Element elementId="s-cap" gridColumn="13 / 25" gridRow="22 / 23"/>
  <Element elementId="ch-mix" gridColumn="1 / 13" gridRow="23 / 37"/>
  <Element elementId="ch-plant" gridColumn="13 / 25" gridRow="23 / 37"/>
  <Element elementId="s-region" gridColumn="1 / 25" gridRow="37 / 38"/>
  <Element elementId="ch-region" gridColumn="1 / 25" gridRow="38 / 51"/>
  <Container elementId="c-insight" type="grid" gridColumn="1 / 25" gridRow="51 / 55"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="insight" gridColumn="1 / 25" gridRow="1 / 4"/>
  </Container>
</Page>"""

_pulse_slot = ('  <Element elementId="plg-pulse" gridColumn="1 / 25" gridRow="9 / 14"/>\n'
               if HAS_PULSE else "")
_kpi_row0 = 14 if HAS_PULSE else 9
_kpi_row1 = _kpi_row0 + 8
_ai_row0 = _kpi_row1
_ai_row1 = _ai_row0 + 4
_tabs_row0 = _ai_row1
_tabs_row1 = _tabs_row0 + 49
_app_page = """<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-app">
  <Container elementId="c-hdr2" type="grid" gridColumn="1 / 25" gridRow="1 / 9"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="wm2" gridColumn="1 / 5" gridRow="1 / 3"/>
    <Element elementId="nav2" gridColumn="13 / 25" gridRow="1 / 3"/>
    <Element elementId="eyebrow2" gridColumn="1 / 13" gridRow="3 / 4"/>
    <Element elementId="ttl2" gridColumn="1 / 17" gridRow="4 / 7"/>
    <Element elementId="sub2" gridColumn="1 / 17" gridRow="7 / 8"/>
    <Element elementId="b-newplan" gridColumn="19 / 25" gridRow="6 / 8"/>
  </Container>
""" + _pulse_slot + """  <Container elementId="c-app-kpi" type="grid" gridColumn="1 / 25" gridRow="{kpi0} / {kpi1}"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="k-prop" gridColumn="1 / 6" gridRow="1 / 8"/>
    <Element elementId="k-shift" gridColumn="6 / 11" gridRow="1 / 8"/>
    <Element elementId="k-bev2" gridColumn="11 / 16" gridRow="1 / 8"/>
    <Element elementId="k-cellprop" gridColumn="16 / 20" gridRow="1 / 8"/>
    <Element elementId="k-over" gridColumn="20 / 25" gridRow="1 / 8"/>
  </Container>
  <Container elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="{ai0} / {ai1}"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="txt-ai" gridColumn="1 / 25" gridRow="1 / 4"/>
  </Container>
  <TabbedContainer elementId="tc-persona" gridColumn="1 / 25" gridRow="{tabs0} / {tabs1}">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="ct-basis" gridColumn="1 / 9" gridRow="1 / 4"/>
      <Element elementId="ct-shift" gridColumn="9 / 14" gridRow="1 / 4"/>
      <Element elementId="ct-app-grain" gridColumn="14 / 19" gridRow="1 / 4"/>
      <Element elementId="b-clear" gridColumn="19 / 25" gridRow="1 / 4"/>
      <Element elementId="ct-region" gridColumn="1 / 9" gridRow="4 / 7"/>
      <Element elementId="ct-pt" gridColumn="9 / 17" gridRow="4 / 7"/>
      <Element elementId="s-grid" gridColumn="1 / 25" gridRow="7 / 8"/>
      <Container elementId="c-grid" type="grid" gridColumn="1 / 25" gridRow="8 / 27"
                 gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="it-alloc" gridColumn="1 / 25" gridRow="1 / 19"/>
      </Container>
      <Element elementId="ch-prop" gridColumn="1 / 25" gridRow="27 / 43"/>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="s-load" gridColumn="1 / 25" gridRow="1 / 2"/>
      <Element elementId="tbl-load" gridColumn="1 / 25" gridRow="2 / 16"/>
      <Element elementId="s-queue" gridColumn="1 / 25" gridRow="16 / 17"/>
      <Container elementId="c-queue" type="grid" gridColumn="1 / 25" gridRow="17 / 32"
                 gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
        <Element elementId="tbl-review" gridColumn="1 / 20" gridRow="1 / 15"/>
        <Element elementId="b-submit" gridColumn="20 / 25" gridRow="1 / 4"/>
      </Container>
    </Tab>
  </TabbedContainer>
</Page>""".format(kpi0=_kpi_row0, kpi1=_kpi_row1, ai0=_ai_row0, ai1=_ai_row1,
                 tabs0=_tabs_row0, tabs1=_tabs_row1)
layout, _exec_count = re.subn(
    r'<Page type="grid"[^>]*id="pg-exec">.*?</Page>',
    _exec_page,
    layout,
    count=1,
    flags=re.S,
)
layout, _app_count = re.subn(
    r'<Page type="grid"[^>]*id="pg-app">.*?</Page>',
    _app_page,
    layout,
    count=1,
    flags=re.S,
)
if (_exec_count, _app_count) != (1, 1):
    raise RuntimeError("could not replace visible page layouts")

# ---------------------------------------------------------------- drillability
# Sigma's right-click drill-down menu only exposes columns declared by the
# visualization itself; it does not inherit the parent table's schema. A chart
# with only Month / Units / Powertrain therefore cannot drill to Model, Plant,
# Region, demand, or the constraint columns even though they all exist upstream.
#
# Copy every business-relevant source column onto every chart and KPI. These
# passthroughs are not bound to xAxis/yAxis/color/value, so they do not alter the
# visual; they only make the fields available in Sigma's drill menu. Technical
# keys and helper columns stay out because an end user should never drill to
# row_key or ice_offset_factor.
_DRILLABLE_KINDS = {"bar-chart", "line-chart", "area-chart", "combo-chart",
                    "scatter-chart", "pie-chart", "donut-chart", "kpi-chart",
                    "pivot-table"}
_TECHNICAL_DRILL_NAMES = {
    "Row Key", "ICE Offset Factor", "Scenario Factor", "Basis Units",
    "Scenario Units", "Plant Month",
}


def add_drill_passthroughs(all_elements):
    by_id = {el["id"]: el for el in all_elements}
    for visual in all_elements:
        if visual.get("kind") not in _DRILLABLE_KINDS:
            continue
        source = visual.get("source") or {}
        if source.get("kind") != "table":
            continue
        parent = by_id.get(source.get("elementId"))
        if not parent or not isinstance(parent.get("name"), str):
            continue

        declared_names = {
            col.get("name") for col in visual.get("columns", []) if col.get("name")
        }
        drill_index = 0
        for source_col in parent.get("columns", []):
            name = source_col.get("name")
            if (not name or source_col.get("hidden") or
                    name in _TECHNICAL_DRILL_NAMES or name in declared_names):
                continue
            drill_index += 1
            visual.setdefault("columns", []).append({
                "id": "%s-drill-%02d" % (visual["id"], drill_index),
                "name": name,
                "formula": "[%s/%s]" % (parent["name"], name),
                **({"format": source_col["format"]} if source_col.get("format") else {}),
            })
            declared_names.add(name)


add_drill_passthroughs(elements)

document = {"schemaVersion": 1, "kind": "workbook", "elements": elements,
            "pages": pages, "overlays": overlays, "layout": layout,
            "settings": {
                "theme": {"name": "Light", "overrides": {
                    "colors": {"text": INK, "surface": CARD, "highlight": HONDA,
                               "success": GOOD, "warning": WARN, "danger": ALARM},
                    "categoricalScheme": [HONDA, INK, SILVER, GOOD, WARN, HONDA_DEEP],
                    "borderRadius": "square", "hasCards": "shown",
                    "elementBorder": {"color": RULE, "width": 1},
                    "space": {"unit": "medium", "showElementPadding": "shown"},
                    "tableStyles": {"preset": "presentation", "cellSpacing": "medium",
                                    "gridLines": "horizontal", "banding": "hidden"},
                    "pageWidth": "large"}},
                "navigation": {"pageHeader": "disabled", "pageTabsInViewMode": "hidden"}}}

body = {"name": "Honda — Hybrid vs. EV Allocation",
        "folderId": FOLDER,
        "description": "Executive overview + allocation data app (linked input table, "
                       "capacity/battery constraints, approval workflow). Editorial Ops theme.",
        "document": document}

def call(method, path, payload=None):
    req = urllib.request.Request(
        BASE.rstrip("/") + path,
        data=(json.dumps(payload).encode() if payload is not None else None),
        method=method,
        headers={"Authorization": "Bearer " + TOKEN,
                 "Content-Type": "application/json", "Accept": "application/json"})
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
    who_status, who = call("GET", "/v2/whoami")
    org_id = who.get("organizationId") if isinstance(who, dict) else None
    if who_status >= 400 or org_id != PAPERCRANE_ORG_ID:
        raise SystemExit(
            "Refusing to build outside papercranestaging: authenticated org is "
            "%s, expected %s. demeng is read-only for examples."
            % (org_id, PAPERCRANE_ORG_ID)
        )
    if not HAS_PULSE:
        print("note: building without the Allocation Pulse plugin "
              "(set HONDA_PULSE_PLUGIN_ID to include it).")
    status, result = call("POST", "/v2/workbooks/spec/verify", body)
    print("verify", status, result)
    if status >= 400 or not (isinstance(result, dict) and result.get("valid")):
        raise SystemExit(1)
    status, result = call("POST", "/v2/workbooks/spec", body)
    print("create", status, result)
    raise SystemExit(0 if status < 400 else 1)
