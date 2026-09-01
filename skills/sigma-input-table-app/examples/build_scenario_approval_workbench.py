#!/usr/bin/env python3
"""Scenario Modeler + Approval Workflow — combined "super" pattern prototype.

Merges two previously-separate sigma-input-table-app patterns into one app:

  * scenario-modeler-pattern.md's cross-join modeler — multiple NAMED
    scenarios, Base Case always present, driver-based projection.
  * approval-workflow-pattern.md's fuller lifecycle — Draft -> Submitted ->
    Approved / Adjust / Rejected (not just Draft/Submitted/Approved), a review
    queue, reviewer comments, and a decision modal.

Also bakes in every gotcha both patterns' authors hit the hard way:

  * NO update-rows with a per-row `formula` value fired from a button — that
    has no row context and fails only on a real click, not at verify/save/
    round-trip. The bulk "shift" lever is a plain computed column reading a
    control instead (instant, cannot partially fail).
  * Scenario ID is auto-generated with a scalar Now()-based formula, not
    typed by the user.
  * Modal footer CTAs are explicitly hidden (real buttons live in the page).
  * Linked-table passthrough columns use `key`, never `formula`.
  * inputMode: "view" is used everywhere writes must survive publish, with
    the known caveat: verified live 2026-08-12/13 that direct cell-click
    typing still enforces draft-only on papercranestaging even with this
    set. The one place this app asks for a typed cell (per-row Growth %) may
    therefore only be enterable in Edit mode until Sigma fixes that; every
    other write in this app (create/submit/review/decide/reset) goes through
    a button + control, which is unaffected.

Usage:
    python3 build_scenario_approval_workbench.py \
      <SIGMA_BASE_URL> <TOKEN> <CONNECTION_ID> <FOLDER_ID>

With no arguments, prints the spec JSON without creating anything.
"""
import json
import sys
import urllib.error
import urllib.request

BASE_SQL = """
SELECT * FROM VALUES
  ('Hardware', 'West',    18400),
  ('Hardware', 'Central', 12100),
  ('Hardware', 'East',    21700),
  ('Hardware', 'South',    9800),
  ('Services', 'West',     7600),
  ('Services', 'Central',  5200),
  ('Services', 'East',     8900),
  ('Services', 'South',    4100),
  ('Subscriptions', 'West',    15300),
  ('Subscriptions', 'Central', 10800),
  ('Subscriptions', 'East',    19200),
  ('Subscriptions', 'South',    6700)
AS t(product, region, baseline_units)
"""


def build_spec(connection_id, folder_id):
    statuses = ["Draft", "Submitted", "Approved", "Adjust", "Rejected"]

    base = {
        "id": "sbase", "kind": "table", "name": "Demand Base",
        "visibleAsSource": True,
        "source": {"connectionId": connection_id, "kind": "sql", "statement": BASE_SQL},
        "columns": [
            {"id": "sb-prod", "formula": "[Custom SQL/PRODUCT]", "name": "Product"},
            {"id": "sb-region", "formula": "[Custom SQL/REGION]", "name": "Region"},
            {"id": "sb-units", "formula": "[Custom SQL/BASELINE_UNITS]", "name": "Baseline Units"},
        ],
    }

    scenarios = {
        "id": "scenarios", "kind": "input-table", "name": "Scenarios",
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": connection_id},
        "columns": [
            {"id": "sc-id", "name": "Scenario ID", "type": "text"},
            {"id": "sc-name", "name": "Scenario Name", "type": "text"},
            {"id": "sc-owner", "name": "Owner", "type": "text"},
            {"id": "sc-status", "name": "Status", "type": "text",
             "values": statuses, "pills": "color-by-option"},
            {"id": "sc-comments", "name": "Reviewer Comments", "type": "text"},
            {"id": "CREATED_AT", "name": "Created At"},
            {"id": "UPDATED_AT", "name": "Updated At"},
        ],
        "tableComponents": {"summaryBar": "hidden"},
    }

    # Editable modeling grid, linked directly off the flat base table (no
    # pivot/cross-join layer). A pivot-sourced linked input table with a
    # control-referencing formula column produced "circular column
    # reference" / "reference to errored column" at render time in testing
    # here -- passed verify/create, broke on first real render, same
    # "looks fine until you click it" shape as every other gotcha this
    # pattern has hit. Cursor's independently-built Honda example proved the
    # control-in-formula technique itself is sound when linked from a flat
    # table, so that's the shape kept here. Multiple SIMULTANEOUS named
    # scenarios (the cross-join's actual value-add) is dropped for this
    # combined prototype -- one modeled scenario at a time, which is what
    # the approval-workflow side needs anyway. Revisit the cross-join once
    # the pivot-linkage failure above is root-caused.
    assumptions = {
        "id": "assum", "kind": "input-table", "name": "Assumptions",
        "inputMode": "view",
        "source": {"kind": "linked", "from": "sbase"},
        "columns": [
            {"id": "ia-prod", "key": "sb-prod"},
            {"id": "ia-region", "key": "sb-region"},
            {"id": "ia-units", "key": "sb-units"},
            {"id": "ia-growth", "type": "number", "name": "Growth %"},
            {"id": "ia-shiftfactor", "hidden": True, "name": "Shift Factor",
             "formula": "1 + Coalesce([bulk_shift_pct], 0) / 100.0"},
            {"id": "ia-proj",
             "formula": "[Baseline Units] * (1 + Coalesce([Growth %], 0) / 100.0) "
                        "* [Shift Factor]",
             "name": "Projected Units",
             "format": {"kind": "number", "formatString": ",d"}},
        ],
        "order": ["ia-prod", "ia-region", "ia-units", "ia-growth", "ia-proj"],
        "sort": [{"columnId": "ia-prod", "direction": "ascending", "nulls": "last"}],
        "tableComponents": {"summaryBar": "hidden"},
    }

    book = {
        "id": "book", "kind": "table", "name": "Book", "visibleAsSource": True,
        "source": {"elementId": "assum", "kind": "table"},
        "columns": [
            {"id": "bk-prod", "formula": "[Assumptions/Product]", "name": "Product"},
            {"id": "bk-region", "formula": "[Assumptions/Region]", "name": "Region"},
            {"id": "bk-base", "formula": "[Assumptions/Baseline Units]", "name": "Baseline Units"},
            {"id": "bk-proj", "formula": "[Assumptions/Projected Units]", "name": "Projected Units"},
        ],
    }

    chart = {
        "id": "chart-compare", "kind": "bar-chart", "name": "Baseline vs Projected",
        "source": {"kind": "table", "elementId": "book"},
        # Bracket-qualified with the source element name -- an unqualified
        # bare formula whose column NAME matches what it references (e.g.
        # name:"Baseline Units", formula:"Sum([Baseline Units])") resolves
        # to itself instead of the upstream column. See the module docstring.
        "columns": [
            {"id": "cc-prod", "name": "Product", "formula": "[Book/Product]"},
            {"id": "cc-base", "name": "Baseline Units", "formula": "Sum([Book/Baseline Units])"},
            {"id": "cc-proj", "name": "Projected Units", "formula": "Sum([Book/Projected Units])"},
        ],
        "xAxis": {"columnId": "cc-prod"},
        "yAxis": {"columnIds": ["cc-base", "cc-proj"]},
        "stacking": "none", "legend": {"position": "top"},
    }

    review = {
        "id": "tbl-review", "kind": "table", "name": "Scenario Review Queue",
        "source": {"kind": "table", "elementId": "scenarios"},
        "columns": [
            {"id": "rv-status", "name": "Status", "formula": "[Scenarios/Status]"},
            {"id": "rv-name", "name": "Scenario Name", "formula": "[Scenarios/Scenario Name]"},
            {"id": "rv-owner", "name": "Owner", "formula": "[Scenarios/Owner]"},
            {"id": "rv-comments", "name": "Reviewer Comments",
             "formula": "[Scenarios/Reviewer Comments]"},
            {"id": "rv-updated", "name": "Updated At", "formula": "[Scenarios/Updated At]"},
            {"id": "rv-scen-id", "name": "Scenario ID", "formula": "[Scenarios/Scenario ID]",
             "hidden": True},
        ],
        "actions": [{
            "id": "select-scenario-for-review", "trigger": "on-select",
            "effects": [
                {"effect": "set-control-value", "control": "selected_scenario_id",
                 "value": {"type": "column", "columnId": "rv-scen-id"}},
                {"effect": "set-control-value", "control": "selected_scenario_name",
                 "value": {"type": "column", "columnId": "rv-name"}},
                {"effect": "open-overlay", "overlayId": "modal-review"},
            ],
        }],
        "sort": [{"columnId": "rv-updated", "direction": "descending", "nulls": "last"}],
        "tableComponents": {"summaryBar": "hidden"},
    }

    def kpi(eid, label, formula):
        return {
            "id": eid, "kind": "kpi-chart", "name": label,
            "source": {"kind": "table", "elementId": "scenarios"},
            "columns": [{"id": eid + "-value", "name": label, "formula": formula,
                         "format": {"kind": "number", "formatString": ",d"}}],
            "value": {"columnId": eid + "-value", "fontSize": 30},
            "style": {"backgroundColor": "#ffffff", "borderColor": "#d7dde8", "borderWidth": 1},
        }

    controls = [
        # Global what-if lever. Safe from a button/live-typing because it
        # only ever feeds a computed column (ia-shiftfactor), never a
        # per-row update-rows value.
        {"id": "ctrl-bulk-shift", "kind": "control",
         "controlId": "bulk_shift_pct", "name": "Bulk demand shift %",
         "controlType": "number", "mode": "=", "value": 0,
         "includeNulls": "when-no-value-is-selected"},
        {"id": "ctrl-new-name", "kind": "control",
         "controlId": "new_scenario_name", "name": "Scenario Name",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected", "showOperators": False},
        {"id": "ctrl-new-owner", "kind": "control",
         "controlId": "new_scenario_owner", "name": "Owner",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected", "showOperators": False},
        # Explicit submit target, typed/pasted by the planner -- not an
        # implicit "currently selected" control. The Assumptions grid models
        # one shared scenario at a time, so submit-for-review names WHICH
        # registered scenario record this modeled state belongs to.
        {"id": "ctrl-submit-name", "kind": "control",
         "controlId": "submit_scenario_name", "name": "Scenario to submit",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected", "showOperators": False},
        {"id": "ctrl-selected-id", "kind": "control",
         "controlId": "selected_scenario_id", "name": "Selected Scenario ID",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected", "showOperators": False},
        {"id": "ctrl-selected-name", "kind": "control",
         "controlId": "selected_scenario_name", "name": "Selected Scenario Name",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected", "showOperators": False},
        {"id": "ctrl-decision", "kind": "control",
         "controlId": "review_decision", "name": "Decision",
         "controlType": "segmented", "value": "Approved",
         "source": {"kind": "manual", "valueType": "text",
                    "values": ["Approved", "Adjust", "Rejected"],
                    "labels": ["Approve", "Request changes", "Reject"]}},
        {"id": "ctrl-review-comments", "kind": "control",
         "controlId": "review_comments", "name": "Reviewer Comments",
         "controlType": "text-area", "value": ""},
    ]

    def button(eid, label, effects, color="#1e3558", font="#ffffff", appearance="filled"):
        return {
            "id": eid, "kind": "button", "text": label,
            "appearance": appearance, "align": "stretch",
            "fillColor": color, "fontColor": font, "fontWeight": "bold",
            "actions": [{"id": "action-" + eid, "trigger": "on-click", "effects": effects}],
        }

    create_button = button("btn-create-scenario", "New scenario", [
        {"effect": "open-overlay", "overlayId": "modal-create"},
    ], "#0d6efd")

    create_submit = button("btn-create-submit", "Create draft", [
        {"effect": "insert-rows", "tableElementId": "scenarios",
         "values": {
             # Scalar formula, legal in an action value (only per-row
             # formulas over a button trigger are rejected).
             "sc-id": {"type": "formula",
                       "formula": '"SCN-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
             "sc-name": {"type": "control", "control": "new_scenario_name"},
             "sc-owner": {"type": "control", "control": "new_scenario_owner"},
             "sc-status": {"type": "constant", "value": {"type": "text", "value": "Draft"}},
         }},
        {"effect": "set-control-value", "control": "submit_scenario_name",
         "value": {"type": "control", "control": "new_scenario_name"}},
        {"effect": "clear-control", "scope": {"type": "control", "controlId": "new_scenario_name"}},
        {"effect": "clear-control", "scope": {"type": "control", "controlId": "new_scenario_owner"}},
        {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-review"}},
        {"effect": "close-overlay"},
    ], "#0d6efd")

    submit_review = button("btn-submit-review", "Submit scenario for review", [
        {"effect": "update-rows", "tableElementId": "scenarios",
         "whichRows": {"type": "formula",
                       "formula": "[Scenario Name] = [submit_scenario_name]"},
         "values": {"sc-status": {"type": "constant",
                                  "value": {"type": "text", "value": "Submitted"}}}},
        {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-review"}},
    ], "#198754")

    review_submit = button("btn-review-submit", "Save decision", [
        {"effect": "update-rows", "tableElementId": "scenarios",
         "whichRows": {"type": "formula",
                       "formula": "[Scenario ID] = [selected_scenario_id]"},
         "values": {
             "sc-status": {"type": "control", "control": "review_decision"},
             "sc-comments": {"type": "control", "control": "review_comments"},
         }},
        {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-review"}},
        {"effect": "close-overlay"},
    ], "#198754")

    delete_scenario = button("btn-delete-scenario", "Delete scenario", [
        {"effect": "delete-rows", "tableElementId": "scenarios",
         "whichRows": {"type": "formula", "formula": "[Scenario ID] = [selected_scenario_id]"}},
        {"effect": "refresh-element", "target": {"type": "element", "element": "tbl-review"}},
        {"effect": "close-overlay"},
    ], "#dc3545")

    # Constants only -- legal from a button, unlike a per-row formula reset.
    reset_button = button("btn-reset", "Clear manual growth overrides", [
        {"effect": "update-rows", "tableElementId": "assum",
         "whichRows": {"type": "formula", "formula": "True"},
         "values": {"ia-growth": {"type": "constant", "value": {"type": "number", "value": None}}}},
        {"effect": "set-control-value", "control": "bulk_shift_pct",
         "value": {"type": "constant", "value": {"type": "number", "value": 0}}},
    ], "#6c757d")

    cancel_create = button("btn-create-cancel", "Cancel", [{"effect": "close-overlay"}],
                           "#ffffff", "#1e3558", "outline")
    cancel_review = button("btn-review-cancel", "Cancel", [{"effect": "close-overlay"}],
                           "#ffffff", "#1e3558", "outline")

    elements = [
        base,
        # Controls must be declared BEFORE any element whose formula
        # references them by controlId. Verified live 2026-08-13: with the
        # control declared AFTER `assumptions` in this list, its hidden
        # "Shift Factor" formula column fails with "Reference to errored
        # column" -- passes verify/create either way, only a real render
        # shows it. Moving the control earlier in `elements` (this ordering)
        # is the fix; nothing else about the formula or the control itself
        # changed between the broken and working versions.
        *controls,
        scenarios, assumptions, book, chart, review,
        kpi("kpi-total", "Total Scenarios", "Count([Scenarios/Scenario ID])"),
        kpi("kpi-submitted", "Submitted", 'CountIf([Scenarios/Status] = "Submitted")'),
        kpi("kpi-approved", "Approved", 'CountIf([Scenarios/Status] = "Approved")'),
        {"id": "title-model", "kind": "text",
         "body": "## **Demand Scenario Workbench**\nPick a scenario, apply a bulk shift or "
                 "per-row growth override, then submit for review."},
        {"id": "title-review", "kind": "text",
         "body": "## **Approval Queue**\nSelect any scenario row to approve, request changes, "
                 "reject, or delete it."},
        {"id": "create-help", "kind": "text",
         "body": "New scenario. Starts as Draft with zero overrides."},
        {"id": "review-help", "kind": "text",
         "body": "Choose a decision and add reviewer comments."},
        create_button, create_submit, submit_review, review_submit,
        delete_scenario, cancel_create, cancel_review, reset_button,
    ]

    pages = [
        {"id": "page-model", "name": "Scenario Workbench"},
        {"id": "page-review", "name": "Review"},
        {"id": "page-data", "name": "Data", "visibility": "hidden"},
    ]
    overlays = [
        {"id": "modal-create", "type": "modal", "name": "New Scenario",
         "modal": {"width": "small",
                   "header": {"title": "New scenario", "showCloseIcon": "shown"},
                   "footer": {"primaryCta": {"visible": "hidden"},
                              "secondaryCta": {"visible": "hidden"}}}},
        {"id": "modal-review", "type": "modal", "name": "Review Scenario",
         "modal": {"width": "small",
                   "header": {"title": "Review scenario", "showCloseIcon": "shown"},
                   "footer": {"primaryCta": {"visible": "hidden"},
                              "secondaryCta": {"visible": "hidden"}}}},
    ]

    layout = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-model">
  <Element elementId="title-model" gridColumn="1 / 13" gridRow="1 / 4"/>
  <Element elementId="ctrl-submit-name" gridColumn="13 / 18" gridRow="1 / 4"/>
  <Element elementId="ctrl-bulk-shift" gridColumn="18 / 21" gridRow="1 / 4"/>
  <Element elementId="btn-create-scenario" gridColumn="21 / 25" gridRow="1 / 2"/>
  <Element elementId="btn-submit-review" gridColumn="21 / 25" gridRow="2 / 3"/>
  <Element elementId="btn-reset" gridColumn="21 / 25" gridRow="3 / 4"/>
  <Element elementId="chart-compare" gridColumn="1 / 25" gridRow="4 / 15"/>
  <Element elementId="assum" gridColumn="1 / 25" gridRow="15 / 33"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-review">
  <Element elementId="title-review" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="kpi-total" gridColumn="1 / 9" gridRow="4 / 11"/>
  <Element elementId="kpi-submitted" gridColumn="9 / 17" gridRow="4 / 11"/>
  <Element elementId="kpi-approved" gridColumn="17 / 25" gridRow="4 / 11"/>
  <Element elementId="tbl-review" gridColumn="1 / 25" gridRow="11 / 28"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-data">
  <Element elementId="sbase" gridColumn="1 / 13" gridRow="1 / 12"/>
  <Element elementId="scenarios" gridColumn="13 / 25" gridRow="1 / 12"/>
  <Element elementId="book" gridColumn="1 / 13" gridRow="12 / 23"/>
  <Element elementId="ctrl-selected-id" gridColumn="13 / 19" gridRow="12 / 15"/>
  <Element elementId="ctrl-selected-name" gridColumn="19 / 25" gridRow="12 / 15"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="modal-create">
  <Element elementId="create-help" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="ctrl-new-name" gridColumn="1 / 25" gridRow="3 / 6"/>
  <Element elementId="ctrl-new-owner" gridColumn="1 / 25" gridRow="6 / 9"/>
  <Element elementId="btn-create-cancel" gridColumn="13 / 19" gridRow="9 / 12"/>
  <Element elementId="btn-create-submit" gridColumn="19 / 25" gridRow="9 / 12"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="modal-review">
  <Element elementId="review-help" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="ctrl-decision" gridColumn="1 / 25" gridRow="3 / 6"/>
  <Element elementId="ctrl-review-comments" gridColumn="1 / 25" gridRow="6 / 11"/>
  <Element elementId="btn-delete-scenario" gridColumn="1 / 7" gridRow="11 / 14"/>
  <Element elementId="btn-review-cancel" gridColumn="13 / 19" gridRow="11 / 14"/>
  <Element elementId="btn-review-submit" gridColumn="19 / 25" gridRow="11 / 14"/>
</Page>
"""

    return {
        "name": "Scenario Workbench + Approval — Combined Pattern Prototype",
        "folderId": folder_id,
        "description": "Prototype merging the cross-join scenario modeler with the fuller "
                       "Draft/Submitted/Approved/Adjust/Rejected approval workflow.",
        "document": {
            "schemaVersion": 1,
            "kind": "workbook",
            "elements": elements,
            "pages": pages,
            "overlays": overlays,
            "layout": layout,
            "settings": {
                "theme": {"name": "Light",
                          "overrides": {"borderRadius": "round", "hasCards": "shown",
                                        "colors": {"highlight": "#1e3558",
                                                   "success": "#3bb5b3",
                                                   "danger": "#ee465c"}}},
                "navigation": {"pageHeader": "enabled", "pageTabsInViewMode": "shown"},
            },
        },
    }


def call(base, token, method, path, body):
    req = urllib.request.Request(
        base.rstrip("/") + path, data=json.dumps(body).encode(), method=method,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(json.dumps(build_spec("<connection-id>", "<folder-id>"), indent=2))
        raise SystemExit(0)
    if len(sys.argv) != 5:
        raise SystemExit("usage: build_scenario_approval_workbench.py "
                          "<SIGMA_BASE_URL> <TOKEN> <CONNECTION_ID> <FOLDER_ID>")
    base_url, token, connection_id, folder_id = sys.argv[1:5]
    spec = build_spec(connection_id, folder_id)
    status, result = call(base_url, token, "POST", "/v2/workbooks/spec/verify", spec)
    print("verify", status, json.dumps(result, indent=2) if not isinstance(result, str) else result)
    if status >= 400 or not result.get("valid"):
        raise SystemExit(1)
    status, result = call(base_url, token, "POST", "/v2/workbooks/spec", spec)
    print("create", status, json.dumps(result, indent=2) if not isinstance(result, str) else result)
    raise SystemExit(0 if status < 400 else 1)
