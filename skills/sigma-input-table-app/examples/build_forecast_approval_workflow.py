#!/usr/bin/env python3
"""Forecast approval workflow — reusable Sigma input-table data-app example.

Creates a two-page planning app with:

  * Plan Registry input table (Draft → Submitted → Approved/Adjust/Rejected)
  * Forecast Entries input table (baseline, proposed, variance, comments)
  * Review queue with on-select actions
  * Create-plan and review-decision modal overlays
  * Insert / update / delete row actions
  * Status KPIs that react to the write-back table

The workflow is intentionally domain-neutral. Rename "Forecast" to Budget,
Demand Plan, Headcount Plan, etc. and add domain columns to it-forecast.

Usage:
    python3 build_forecast_approval_workflow.py \
      <SIGMA_BASE_URL> <TOKEN> <CONNECTION_ID> <FOLDER_ID>

With no arguments, prints the spec JSON without creating anything.
"""
import json
import sys
import urllib.error
import urllib.request


def build_spec(connection_id, folder_id):
    statuses = ["Draft", "Submitted", "Approved", "Adjust", "Rejected"]

    registry = {
        "id": "it-plan-registry",
        "kind": "input-table",
        "name": "Plan Registry",
        # "view" means any workbook viewer can write in published mode.
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": connection_id},
        "columns": [
            {"id": "pr-plan-id", "name": "Plan ID", "type": "text"},
            {"id": "pr-plan-name", "name": "Plan Name", "type": "text"},
            {"id": "pr-owner", "name": "Owner", "type": "text"},
            {"id": "pr-status", "name": "Status", "type": "text",
             "values": statuses, "pills": "color-by-option"},
            {"id": "pr-comments", "name": "Reviewer Comments", "type": "text"},
            {"id": "ID", "name": "Row ID"},
            {"id": "CREATED_AT", "name": "Created At"},
            {"id": "UPDATED_AT", "name": "Updated At"},
            {"id": "CREATED_BY", "name": "Created By"},
            {"id": "UPDATED_BY", "name": "Updated By"},
        ],
        "tableComponents": {"summaryBar": "hidden"},
    }

    forecast = {
        "id": "it-forecast",
        "kind": "input-table",
        "name": "Forecast Entries",
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": connection_id},
        "columns": [
            {"id": "fc-plan-id", "name": "Plan ID", "type": "text"},
            {"id": "fc-period", "name": "Period", "type": "datetime"},
            {"id": "fc-dimension", "name": "Dimension", "type": "text"},
            {"id": "fc-baseline", "name": "Baseline", "type": "number"},
            {"id": "fc-proposed", "name": "Proposed", "type": "number"},
            {"id": "fc-variance", "name": "Variance",
             "formula": "[Proposed] - [Baseline]",
             "format": {"kind": "number", "formatString": "+,.2f"}},
            {"id": "fc-comments", "name": "Planner Comments", "type": "text"},
        ],
        "tableComponents": {"summaryBar": "hidden"},
        "sort": [{"columnId": "fc-period", "direction": "ascending", "nulls": "last"}],
    }

    # Review table inherits the write-back rows and hosts the row-selection action.
    review = {
        "id": "tbl-review",
        "kind": "table",
        "name": "Plan Review Queue",
        "source": {"kind": "table", "elementId": "it-plan-registry"},
        "columns": [
            {"id": "rv-status", "name": "Status", "formula": "[Plan Registry/Status]"},
            {"id": "rv-name", "name": "Plan Name", "formula": "[Plan Registry/Plan Name]"},
            {"id": "rv-owner", "name": "Owner", "formula": "[Plan Registry/Owner]"},
            {"id": "rv-comments", "name": "Reviewer Comments",
             "formula": "[Plan Registry/Reviewer Comments]"},
            {"id": "rv-created", "name": "Created At", "formula": "[Plan Registry/Created At]"},
            {"id": "rv-updated", "name": "Updated At", "formula": "[Plan Registry/Updated At]"},
            {"id": "rv-plan-id", "name": "Plan ID", "formula": "[Plan Registry/Plan ID]",
             "hidden": True},
        ],
        "actions": [{
            "id": "select-plan-for-review",
            "trigger": "on-select",
            "effects": [
                {"effect": "set-control-value", "control": "selected_plan_id",
                 "value": {"type": "column", "column": "rv-plan-id"}},
                {"effect": "set-control-value", "control": "selected_plan_name",
                 "value": {"type": "column", "column": "rv-name"}},
                {"effect": "open-overlay", "overlayId": "modal-review"},
            ],
        }],
        "sort": [{"columnId": "rv-updated", "direction": "descending", "nulls": "last"}],
        "tableComponents": {"summaryBar": "hidden"},
    }

    def kpi(eid, label, formula):
        return {
            "id": eid, "kind": "kpi-chart", "name": label,
            "source": {"kind": "table", "elementId": "it-plan-registry"},
            "columns": [{"id": eid + "-value", "name": label, "formula": formula,
                         "format": {"kind": "number", "formatString": ",d"}}],
            "value": {"columnId": eid + "-value", "fontSize": 30},
            "style": {"backgroundColor": "#ffffff", "borderColor": "#d7dde8",
                      "borderWidth": 1},
        }

    # Workbook-global variables. Keep controlIds alphanumeric/underscore/hyphen:
    # dotted IDs found in old GET-backs are rejected on fresh CREATE.
    controls = [
        {"id": "ctrl-selected-id", "kind": "control",
         "controlId": "selected_plan_id", "name": "Selected Plan ID",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
        {"id": "ctrl-selected-name", "kind": "control",
         "controlId": "selected_plan_name", "name": "Selected Plan Name",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
        {"id": "ctrl-new-id", "kind": "control",
         "controlId": "new_plan_id", "name": "Plan ID",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
        {"id": "ctrl-new-name", "kind": "control",
         "controlId": "new_plan_name", "name": "Plan Name",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
        {"id": "ctrl-new-owner", "kind": "control",
         "controlId": "new_plan_owner", "name": "Owner",
         "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
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

    def button(eid, label, effects, color="#1e3558", font="#ffffff",
               appearance="filled"):
        return {
            "id": eid, "kind": "button", "text": label,
            "appearance": appearance, "align": "stretch",
            "fillColor": color, "fontColor": font, "fontWeight": "bold",
            "actions": [{"id": "action-" + eid, "trigger": "on-click",
                         "effects": effects}],
        }

    create_button = button("btn-create-plan", "Create scenario", [
        {"effect": "open-overlay", "overlayId": "modal-create"},
    ], "#0d6efd")

    create_submit = button("btn-create-submit", "Create draft", [
        {"effect": "insert-rows", "table": "it-plan-registry",
         "values": {
             "pr-plan-id": {"type": "control", "control": "new_plan_id"},
             "pr-plan-name": {"type": "control", "control": "new_plan_name"},
             "pr-owner": {"type": "control", "control": "new_plan_owner"},
             "pr-status": {"type": "constant",
                           "value": {"type": "text", "value": "Draft"}},
         }},
        {"effect": "set-control-value", "control": "selected_plan_id",
         "value": {"type": "control", "control": "new_plan_id"}},
        {"effect": "set-control-value", "control": "selected_plan_name",
         "value": {"type": "control", "control": "new_plan_name"}},
        {"effect": "refresh-element",
         "target": {"type": "element", "element": "tbl-review"}},
        {"effect": "close-overlay"},
    ], "#0d6efd")

    submit_review = button("btn-submit-review", "Submit selected plan for review", [
        {"effect": "update-rows", "table": "it-plan-registry",
         # Formula targeting avoids depending on the input table's system Row ID.
         "whichRows": {"type": "formula",
                       "formula": "[Plan ID] = [selected_plan_id]"},
         "values": {
             "pr-status": {"type": "constant",
                           "value": {"type": "text", "value": "Submitted"}},
         }},
        {"effect": "refresh-element",
         "target": {"type": "element", "element": "tbl-review"}},
    ], "#198754")

    review_submit = button("btn-review-submit", "Save decision", [
        {"effect": "update-rows", "table": "it-plan-registry",
         "whichRows": {"type": "formula",
                       "formula": "[Plan ID] = [selected_plan_id]"},
         "values": {
             "pr-status": {"type": "control", "control": "review_decision"},
             "pr-comments": {"type": "control", "control": "review_comments"},
         }},
        {"effect": "refresh-element",
         "target": {"type": "element", "element": "tbl-review"}},
        {"effect": "close-overlay"},
    ], "#198754")

    delete_plan = button("btn-delete-plan", "Delete plan", [
        {"effect": "delete-rows", "table": "it-plan-registry",
         "whichRows": {"type": "formula",
                       "formula": "[Plan ID] = [selected_plan_id]"}},
        {"effect": "refresh-element",
         "target": {"type": "element", "element": "tbl-review"}},
        {"effect": "close-overlay"},
    ], "#dc3545")

    cancel_create = button("btn-create-cancel", "Cancel",
                           [{"effect": "close-overlay"}],
                           "#ffffff", "#1e3558", "outline")
    cancel_review = button("btn-review-cancel", "Cancel",
                           [{"effect": "close-overlay"}],
                           "#ffffff", "#1e3558", "outline")

    elements = [
        registry, forecast, review,
        kpi("kpi-total", "Total Plans", "Count([Plan Registry/Plan ID])"),
        kpi("kpi-submitted", "Submitted",
            'CountIf([Plan Registry/Status] = "Submitted")'),
        kpi("kpi-approved", "Approved",
            'CountIf([Plan Registry/Status] = "Approved")'),
        {"id": "title-forecast", "kind": "text",
         "body": "## **Forecast Scenario Modeler**\nEnter baseline and proposed values, then submit the selected plan for review."},
        {"id": "title-review", "kind": "text",
         "body": "## **Approval Queue**\nSelect any plan row to approve, request changes, reject, or delete it."},
        {"id": "create-help", "kind": "text",
         "body": "**New plan**\nCreate a Draft registry row. Forecast entries use the same Plan ID."},
        {"id": "review-help", "kind": "text",
         "body": "**Review selected plan**\nChoose a decision and add reviewer comments."},
        *controls,
        create_button, create_submit, submit_review, review_submit,
        delete_plan, cancel_create, cancel_review,
    ]

    pages = [
        {"id": "page-forecast", "name": "Forecast"},
        {"id": "page-review", "name": "Review"},
        {"id": "page-data", "name": "Data", "visibility": "hidden"},
    ]
    overlays = [
        {"id": "modal-create", "type": "modal", "name": "Create Plan",
         "modal": {"width": "large",
                   "header": {"title": "Create Forecast Plan",
                              "showCloseIcon": "shown"}}},
        {"id": "modal-review", "type": "modal", "name": "Review Plan",
         "modal": {"width": "large",
                   "header": {"title": "Review Forecast Plan",
                              "showCloseIcon": "shown"}}},
    ]

    layout = """<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-forecast">
  <Element elementId="title-forecast" gridColumn="1 / 17" gridRow="1 / 4"/>
  <Element elementId="btn-create-plan" gridColumn="17 / 21" gridRow="1 / 4"/>
  <Element elementId="btn-submit-review" gridColumn="21 / 25" gridRow="1 / 4"/>
  <Element elementId="it-forecast" gridColumn="1 / 25" gridRow="4 / 24"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-review">
  <Element elementId="title-review" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="kpi-total" gridColumn="1 / 9" gridRow="4 / 11"/>
  <Element elementId="kpi-submitted" gridColumn="9 / 17" gridRow="4 / 11"/>
  <Element elementId="kpi-approved" gridColumn="17 / 25" gridRow="4 / 11"/>
  <Element elementId="tbl-review" gridColumn="1 / 25" gridRow="11 / 28"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="page-data">
  <Element elementId="it-plan-registry" gridColumn="1 / 25" gridRow="1 / 15"/>
  <Element elementId="ctrl-selected-id" gridColumn="1 / 9" gridRow="15 / 18"/>
  <Element elementId="ctrl-selected-name" gridColumn="9 / 17" gridRow="15 / 18"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="modal-create">
  <Element elementId="create-help" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="ctrl-new-id" gridColumn="1 / 13" gridRow="4 / 7"/>
  <Element elementId="ctrl-new-name" gridColumn="13 / 25" gridRow="4 / 7"/>
  <Element elementId="ctrl-new-owner" gridColumn="1 / 25" gridRow="7 / 10"/>
  <Element elementId="btn-create-cancel" gridColumn="13 / 19" gridRow="10 / 13"/>
  <Element elementId="btn-create-submit" gridColumn="19 / 25" gridRow="10 / 13"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="modal-review">
  <Element elementId="review-help" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="ctrl-decision" gridColumn="1 / 25" gridRow="4 / 7"/>
  <Element elementId="ctrl-review-comments" gridColumn="1 / 25" gridRow="7 / 12"/>
  <Element elementId="btn-delete-plan" gridColumn="1 / 7" gridRow="12 / 15"/>
  <Element elementId="btn-review-cancel" gridColumn="13 / 19" gridRow="12 / 15"/>
  <Element elementId="btn-review-submit" gridColumn="19 / 25" gridRow="12 / 15"/>
</Page>
"""

    return {
        "name": "Forecast Approval Workflow — Example",
        "folderId": folder_id,
        "description": "Reusable Draft → Submitted → Approved/Adjust/Rejected input-table workflow.",
        "document": {
            "schemaVersion": 1,
            "kind": "workbook",
            "elements": elements,
            "pages": pages,
            "overlays": overlays,
            "layout": layout,
            "settings": {
                "theme": {"name": "Light",
                          "overrides": {"borderRadius": "round",
                                        "hasCards": "shown",
                                        "colors": {"highlight": "#1e3558",
                                                   "success": "#3bb5b3",
                                                   "danger": "#ee465c"}}},
                "navigation": {"pageHeader": "enabled",
                               "pageTabsInViewMode": "shown"},
            },
        },
    }


def call(base, token, method, path, body):
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(body).encode(),
        method=method,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Placeholder IDs make the output useful for reading/diffing.
        print(json.dumps(build_spec("<connection-id>", "<folder-id>"), indent=2))
        raise SystemExit(0)
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: build_forecast_approval_workflow.py "
            "<SIGMA_BASE_URL> <TOKEN> <CONNECTION_ID> <FOLDER_ID>"
        )
    base, token, connection_id, folder_id = sys.argv[1:5]
    spec = build_spec(connection_id, folder_id)
    status, result = call(base, token, "POST", "/v2/workbooks/spec/verify", spec)
    print("verify", status, json.dumps(result, indent=2) if not isinstance(result, str) else result)
    if status >= 400 or not result.get("valid"):
        raise SystemExit(1)
    status, result = call(base, token, "POST", "/v2/workbooks/spec", spec)
    print("create", status, json.dumps(result, indent=2) if not isinstance(result, str) else result)
    raise SystemExit(0 if status < 400 else 1)
