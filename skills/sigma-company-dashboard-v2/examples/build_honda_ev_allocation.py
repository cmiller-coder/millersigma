#!/usr/bin/env python3
"""Honda — Hybrid vs. EV Allocation.

Page 1  Executive overview   (Editorial Ops theme: light paper, hairline rules)
Page 2  Allocation data app  (denser console feel, still light so input tables work)
Page 3  Data (hidden)        baseline + registry plumbing

Theme: "Editorial Ops" — Editorial Minimal structure recoloured to Honda
(#CC0000 sampled from Honda's own logo SVG), with Control Room density on page 2.
Semantics are teal/amber so Honda red only ever means brand or a capacity breach.
"""
import json
import os
import sys
import urllib.error
import urllib.request

# Usage:
#   python3 build_honda_ev_allocation.py                      # print the spec only
#   python3 build_honda_ev_allocation.py <BASE> <TOKEN> <CONNECTION_ID> <FOLDER_ID>
#
# CONNECTION_ID must be a warehouse connection with Sigma write-back enabled
# (the linked input table and the plan registry both persist there).
_ARGS = sys.argv[1:]
BASE = _ARGS[0] if len(_ARGS) > 0 else os.environ.get("SIGMA_BASE_URL", "")
TOKEN = _ARGS[1] if len(_ARGS) > 1 else os.environ.get("SIGMA_API_TOKEN", "")
CONN = _ARGS[2] if len(_ARGS) > 2 else "<connection-id>"
FOLDER = _ARGS[3] if len(_ARGS) > 3 else "<folder-id>"

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
  0.18 AS bev_mix_target
FROM mix x
CROSS JOIN models m
CROSS JOIN regions r
JOIN plant_cap c ON c.plant = m.plant
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
       a.cell_kwh_used, ROUND(a.allocated_units * 20) AS cell_kwh_available
FROM alloc a JOIN plant_cap c ON c.plant = a.plant
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
         {"id": "al-prop", "type": "number", "name": "Proposed Units"},
         {"id": "al-note", "type": "text", "name": "Planner Note"},
         {"id": "al-eff", "formula": "Coalesce([Proposed Units], [Baseline Units])",
          "name": "Effective Units", "format": INT},
         {"id": "al-var", "formula": "[Effective Units] - [Baseline Units]",
          "name": "Variance", "format": DLT},
         {"id": "al-cells", "formula": "[Effective Units] * [kWh per Unit]",
          "name": "Cell kWh", "format": INT, "hidden": True},
     ],
     "sort": [{"columnId": "al-month", "direction": "ascending", "nulls": "last"},
              {"columnId": "al-model", "direction": "ascending", "nulls": "last"}],
     "tableComponents": {"summaryBar": "hidden"},
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
         {"id": "pl-id", "name": "Plant Month", "hidden": True,
          "formula": '[Plant] & " · " & DateFormat([Month], "%b %Y")'},
         {"id": "pl-flag", "name": "Capacity Status",
          "formula": 'If([Allocated] > [Capacity], "Over capacity", "Within capacity")'},
     ],
     "groupings": [{"id": "g-pl", "groupBy": ["pl-plant", "pl-month"],
                    "calculations": ["pl-eff", "pl-cap", "pl-util", "pl-id", "pl-flag"]}],
     "tableComponents": {"summaryBar": "hidden"},
     "tableStyle": {"preset": "presentation", "cellSpacing": "small"},
     "visibleAsSource": True})

# --------------------------------------------------------------- KPIs
def kpi(eid, label, source, formula, fmt, comparison=None, comp_formula=None,
        comp_fmt=None, value_color=INK, size=34):
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
        el["comparison"] = {"display": "delta", "colorGood": GOOD, "colorBad": WARN,
                            "fontSize": 12, "label": comparison}
    return el


EFF = "[Allocation Plan/Effective Units]"
add(kpi("k-units", "Plan of record units", "sql-alloc",
        "Sum([Allocation Baseline/Baseline Units])", INT))
add(kpi("k-elec", "Electrified mix", "sql-alloc",
        'Sum(If([Allocation Baseline/Powertrain] <> "ICE", [Allocation Baseline/Baseline Units], 0))'
        " / Sum([Allocation Baseline/Baseline Units])", PCT1))
add(kpi("k-bev", "BEV mix vs target", "sql-alloc",
        'Sum(If([Allocation Baseline/Powertrain] = "BEV", [Allocation Baseline/Baseline Units], 0))'
        " / Sum([Allocation Baseline/Baseline Units])", PCT1,
        comparison="Target", comp_formula="Avg([Allocation Baseline/BEV Mix Target])"))
add(kpi("k-cap", "Plant capacity used", "sql-plant",
        "Sum([Plant Capacity/Allocated Units]) / Sum([Plant Capacity/Capacity Units])", PCT1))
add(kpi("k-cell", "Battery cell used", "sql-plant",
        "Sum([Plant Capacity/Cell kWh Used]) / Sum([Plant Capacity/Cell kWh Available])", PCT1))

add(kpi("k-prop", "Proposed units", "it-alloc", "Sum(%s)" % EFF, INT,
        comparison="Plan of record", comp_formula="Sum([Allocation Plan/Baseline Units])"))
add(kpi("k-bev2", "Proposed BEV mix", "it-alloc",
        'Sum(If([Allocation Plan/Powertrain] = "BEV", %s, 0)) / Sum(%s)' % (EFF, EFF), PCT1,
        comparison="Target", comp_formula="Avg([Allocation Plan/BEV Mix Target])"
        if False else "0.18"))
add(kpi("k-shift", "Net unit shift", "it-alloc", "Sum([Allocation Plan/Variance])", DLT))
add(kpi("k-over", "Plant-months over capacity", "tbl-load",
        'CountDistinct(If([Plant Month Load/Capacity Status] = "Over capacity", '
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

add({"id": "ch-prop", "kind": "line-chart", "name": "Proposed vs plan of record",
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
add(control("ct-shift", "c_bev_shift", "BEV shift %", "number", 10))
add(control("ct-plan-id", "c_plan_id", "Plan ID"))
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

add(button("b-populate", "Copy plan of record", [
    {"effect": "update-rows", "table": "it-alloc",
     "whichRows": {"type": "formula", "formula": "True"},
     "values": {"al-prop": {"type": "formula", "formula": "[Baseline Units]"}}}] + REFRESH))
add(button("b-clear", "Clear proposals", [
    {"effect": "update-rows", "table": "it-alloc",
     "whichRows": {"type": "formula", "formula": "True"},
     "values": {"al-prop": {"type": "constant", "value": {"type": "number", "value": None}},
                "al-note": {"type": "constant", "value": {"type": "text", "value": None}}}}]
    + REFRESH, CARD, INK, "outline"))
add(button("b-shift", "Apply BEV shift", [
    {"effect": "update-rows", "table": "it-alloc",
     "whichRows": {"type": "formula", "formula": '[Powertrain] = "BEV"'},
     "values": {"al-prop": {"type": "formula",
                            "formula": "Round([Baseline Units] * (1 + [c_bev_shift] / 100))"}}},
    {"effect": "update-rows", "table": "it-alloc",
     "whichRows": {"type": "formula", "formula": '[Powertrain] = "ICE"'},
     "values": {"al-prop": {"type": "formula",
                            "formula": "Round([Baseline Units] * (1 - [c_bev_shift] / 100))"}}}]
    + REFRESH, HONDA))
add(button("b-newplan", "Create plan", [
    {"effect": "open-overlay", "overlayId": "m-create"}], HONDA))
add(button("b-create-save", "Create draft", [
    {"effect": "insert-rows", "table": "it-registry", "values": {
        "pr-id": {"type": "control", "control": "c_plan_id"},
        "pr-name": {"type": "control", "control": "c_plan_name"},
        "pr-owner": {"type": "control", "control": "c_plan_owner"},
        "pr-scope": {"type": "constant",
                     "value": {"type": "text", "value": "Hybrid vs EV allocation"}},
        "pr-status": {"type": "constant", "value": {"type": "text", "value": "Draft"}}}},
    {"effect": "set-control-value", "control": "c_selected_plan",
     "value": {"type": "control", "control": "c_plan_id"}},
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
        ("Hybrid &amp; EV allocation", "Plan of record for the next six months — mix, capacity and battery supply."),
        ("Allocation planner", "Shift volume between powertrains, then submit the plan for review.")], start=1):
    add({"id": "c-hdr%d" % idx, "kind": "container", "spacing": "small",
         "style": {"backgroundColor": CARD, "borderRadius": "square",
                   "borderColor": RULE, "borderWidth": 1}})
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
                   '<span style="color: %s">How much volume should move from ICE to hybrid and EV '
                   'without breaching plant capacity or battery cell supply?</span>' % (HONDA, INK)))
add(text("s-mix", '<span style="color: %s">**MIX TRAJECTORY**</span>' % INK_SOFT))
add(text("s-cap", '<span style="color: %s">**CAPACITY POSTURE**</span>' % INK_SOFT))
add(text("s-region", '<span style="color: %s">**REGIONAL MIX**</span>' % INK_SOFT))
add(text("s-grid", '<span style="color: %s">**ALLOCATION GRID — EDIT PROPOSED UNITS**</span>' % INK_SOFT))
add(text("s-queue", '<span style="color: %s">**APPROVAL QUEUE — SELECT A ROW TO DECIDE**</span>' % INK_SOFT))
add(text("s-load", '<span style="color: %s">**PLANT-MONTH LOAD VS CAPACITY**</span>' % INK_SOFT))
add(text("m-create-help", '### Create allocation plan\nA draft plan is registered, then submitted for review.'))
add(text("m-review-help", '### Review allocation plan\nApprove, request changes, or reject the selected plan.'))

for cid in ("c-kpi1", "c-app-kpi", "c-grid", "c-queue"):
    add({"id": cid, "kind": "container", "spacing": "small",
         "style": {"backgroundColor": CARD, "borderRadius": "square",
                   "borderColor": RULE, "borderWidth": 1}})

pages = [{"id": "pg-exec", "name": "Executive overview"},
         {"id": "pg-app", "name": "Allocation planner"},
         {"id": "pg-data", "name": "Data", "visibility": "hidden"}]
overlays = [
    {"id": "m-create", "type": "modal", "name": "Create plan",
     "modal": {"width": "large", "header": {"title": "Create allocation plan",
                                           "showCloseIcon": "shown"}}},
    {"id": "m-review", "type": "modal", "name": "Review plan",
     "modal": {"width": "large", "header": {"title": "Review allocation plan",
                                            "showCloseIcon": "shown"}}},
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
  <Element elementId="ct-region" gridColumn="1 / 6" gridRow="17 / 20"/>
  <Element elementId="ct-pt" gridColumn="6 / 11" gridRow="17 / 20"/>
  <Element elementId="ct-shift" gridColumn="11 / 15" gridRow="17 / 20"/>
  <Element elementId="b-shift" gridColumn="15 / 19" gridRow="17 / 20"/>
  <Element elementId="b-populate" gridColumn="19 / 22" gridRow="17 / 20"/>
  <Element elementId="b-clear" gridColumn="22 / 25" gridRow="17 / 20"/>
  <Element elementId="s-grid" gridColumn="1 / 25" gridRow="20 / 21"/>
  <Container elementId="c-grid" type="grid" gridColumn="1 / 25" gridRow="21 / 39"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="it-alloc" gridColumn="1 / 25" gridRow="1 / 18"/>
  </Container>
  <Element elementId="ch-prop" gridColumn="1 / 13" gridRow="39 / 53"/>
  <Element elementId="s-load" gridColumn="13 / 25" gridRow="39 / 40"/>
  <Element elementId="tbl-load" gridColumn="13 / 25" gridRow="40 / 53"/>
  <Element elementId="s-queue" gridColumn="1 / 25" gridRow="53 / 54"/>
  <Container elementId="c-queue" type="grid" gridColumn="1 / 25" gridRow="54 / 68"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="tbl-review" gridColumn="1 / 20" gridRow="1 / 14"/>
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
  <Element elementId="m-create-help" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="ct-plan-id" gridColumn="1 / 13" gridRow="4 / 7"/>
  <Element elementId="ct-plan-name" gridColumn="13 / 25" gridRow="4 / 7"/>
  <Element elementId="ct-plan-owner" gridColumn="1 / 25" gridRow="7 / 10"/>
  <Element elementId="b-create-cancel" gridColumn="13 / 19" gridRow="10 / 13"/>
  <Element elementId="b-create-save" gridColumn="19 / 25" gridRow="10 / 13"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="m-review">
  <Element elementId="m-review-help" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="ct-decision" gridColumn="1 / 25" gridRow="4 / 7"/>
  <Element elementId="ct-review-note" gridColumn="1 / 25" gridRow="7 / 12"/>
  <Element elementId="b-review-cancel" gridColumn="13 / 19" gridRow="12 / 15"/>
  <Element elementId="b-review-save" gridColumn="19 / 25" gridRow="12 / 15"/>
</Page>
"""

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

def call(method, path, payload):
    req = urllib.request.Request(
        BASE.rstrip("/") + path, data=json.dumps(payload).encode(), method=method,
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
    status, result = call("POST", "/v2/workbooks/spec/verify", body)
    print("verify", status, result)
    if status >= 400 or not (isinstance(result, dict) and result.get("valid")):
        raise SystemExit(1)
    status, result = call("POST", "/v2/workbooks/spec", body)
    print("create", status, result)
    raise SystemExit(0 if status < 400 else 1)
