"""Pluggable approval-workflow surface — Draft -> Submitted -> Approved/Adjust/Rejected.

Extracted from sigma-input-table-app/examples/build_forecast_approval_workflow.py
and generalized so any company builder can compose it in, instead of copying
1500 lines per prospect. Every gotcha this pattern has hit is baked in:

  * Registry writes (create/submit/decide/delete) go through button + control(s)
    + insert/update/delete-rows, never a raw cell edit (inputMode:"view" still
    enforces draft-only for direct cell typing as of 2026-08-12/13).
  * The record id is auto-generated with a SCALAR formula on insert
    ("PREFIX-" & DateFormat(Now(), ...)) -- never ask the user to invent one.
  * Modal footer CTAs are hidden (overlay-level actions can't resolve controls,
    so the real buttons are page elements inside the modal -- leaving the
    built-in footer visible shows a dead second pair of buttons).
  * The submit target is an EXPLICIT control the caller places wherever the
    "submit for review" action lives, not an implicit "currently selected"
    control -- that broke the first version of this pattern when a user
    landed on a page without having selected anything yet.
  * Every write ends with refresh-element on the review queue.

Usage (see the bottom of this file for a runnable composition example):

    import surfaces_approval_workflow as approval
    wf = approval.build(
        prefix="wf", connection_id=CONN,
        entity_singular="Scenario", entity_plural="Scenarios",
        extra_registry_columns=[{"id": "wf-region", "name": "Region", "type": "text"}],
    )
    elements += wf["elements"]
    pages += wf["pages"]
    overlays += wf["overlays"]
    layout += wf["layout_xml"]
    # Place wf["unplaced"]["create_button"] and wf["unplaced"]["submit_button"]
    # plus wf["unplaced"]["submit_target_control"] on whatever page makes sense
    # for your app (e.g. the same page as a reallocation or commission modeler).
"""

DEFAULT_STATUSES = ["Draft", "Submitted", "Approved", "Adjust", "Rejected"]


def build(
    prefix,
    connection_id,
    entity_singular="Plan",
    entity_plural="Plans",
    statuses=None,
    extra_registry_columns=None,
    review_page_name="Review",
    data_page_name="Data",
    embed_review=False,
):
    """Returns {"elements", "pages", "overlays", "layout_xml", "unplaced"}.

    `prefix` must be unique within the target workbook -- every element/control
    id this module creates is `f"{prefix}-..."` so two surfaces can be composed
    into the same workbook without id collisions. `extra_registry_columns` are
    domain columns beyond the built-in id/name/owner/status/comments (e.g. a
    Region or Commission Plan Type column) -- pass a list of
    `{"id", "name", "type"}` (or `"values"`/`"pills"` for an enum column); each
    gets carried into the review queue automatically.

    `embed_review=True` skips generating a standalone top-level "Review" page
    -- a workbook with one BI page and one data-app page reads as fragmented
    if the approval queue shows up as a THIRD unrelated top-level tab. Instead
    the review title/KPIs/table are left unplaced (see `unplaced["review_*"]`
    below) for the caller to lay out inside their own `tabbed-container` (e.g.
    a "Plan" tab for the modeler + an "Approvals" tab for this). The hidden
    data page and the two modals are unaffected either way -- they were never
    top-level nav tabs.
    """
    statuses = list(statuses or DEFAULT_STATUSES)
    extra_registry_columns = list(extra_registry_columns or [])
    p = prefix

    registry_id = f"{p}-registry"
    review_id = f"{p}-review"
    modal_create_id = f"m-{p}-create"
    modal_review_id = f"m-{p}-review"

    registry_columns = [
        {"id": f"{p}-rec-id", "name": f"{entity_singular} ID", "type": "text"},
        {"id": f"{p}-rec-name", "name": f"{entity_singular} Name", "type": "text"},
        {"id": f"{p}-rec-owner", "name": "Owner", "type": "text"},
        {"id": f"{p}-rec-status", "name": "Status", "type": "text",
         "values": statuses, "pills": "color-by-option"},
        {"id": f"{p}-rec-comments", "name": "Reviewer Comments", "type": "text"},
        *extra_registry_columns,
        {"id": "ID", "name": "Row ID"},
        {"id": "CREATED_AT", "name": "Created At"},
        {"id": "UPDATED_AT", "name": "Updated At"},
    ]

    registry = {
        "id": registry_id, "kind": "input-table", "name": f"{entity_plural} Registry",
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": connection_id},
        "columns": registry_columns,
        "tableComponents": {"summaryBar": "hidden"},
    }

    review_columns = [
        {"id": f"{p}-rv-status", "name": "Status", "formula": f"[{entity_plural} Registry/Status]"},
        {"id": f"{p}-rv-name", "name": f"{entity_singular} Name",
         "formula": f"[{entity_plural} Registry/{entity_singular} Name]"},
        {"id": f"{p}-rv-owner", "name": "Owner", "formula": f"[{entity_plural} Registry/Owner]"},
        {"id": f"{p}-rv-comments", "name": "Reviewer Comments",
         "formula": f"[{entity_plural} Registry/Reviewer Comments]"},
        {"id": f"{p}-rv-updated", "name": "Updated At",
         "formula": f"[{entity_plural} Registry/Updated At]"},
        {"id": f"{p}-rv-id", "name": f"{entity_singular} ID",
         "formula": f"[{entity_plural} Registry/{entity_singular} ID]", "hidden": True},
    ]
    review = {
        "id": review_id, "kind": "table", "name": f"{entity_singular} Review Queue",
        "source": {"kind": "table", "elementId": registry_id},
        "columns": review_columns,
        "actions": [{
            "id": f"{p}-select-for-review", "trigger": "on-select",
            "effects": [
                {"effect": "set-control-value", "control": f"{p}_selected_id",
                 "value": {"type": "column", "columnId": f"{p}-rv-id"}},
                {"effect": "set-control-value", "control": f"{p}_selected_name",
                 "value": {"type": "column", "columnId": f"{p}-rv-name"}},
                {"effect": "open-overlay", "overlayId": modal_review_id},
            ],
        }],
        "sort": [{"columnId": f"{p}-rv-updated", "direction": "descending", "nulls": "last"}],
        "tableComponents": {"summaryBar": "hidden"},
    }

    def kpi(suffix, label, formula):
        return {
            "id": f"{p}-kpi-{suffix}", "kind": "kpi-chart", "name": label,
            "source": {"kind": "table", "elementId": registry_id},
            "columns": [{"id": f"{p}-kpi-{suffix}-value", "name": label, "formula": formula,
                         "format": {"kind": "number", "formatString": ",d"}}],
            "value": {"columnId": f"{p}-kpi-{suffix}-value", "fontSize": 30},
            "style": {"backgroundColor": "#ffffff", "borderColor": "#d7dde8", "borderWidth": 1},
        }

    kpis = [
        kpi("total", f"Total {entity_plural}", f"Count([{entity_plural} Registry/{entity_singular} ID])"),
        kpi("submitted", "Submitted", f'CountIf([{entity_plural} Registry/Status] = "Submitted")'),
        kpi("approved", "Approved", f'CountIf([{entity_plural} Registry/Status] = "Approved")'),
    ]

    controls = [
        {"id": f"ctrl-{p}-new-name", "kind": "control", "controlId": f"{p}_new_name",
         "name": f"{entity_singular} Name", "controlType": "text", "case": "insensitive",
         "mode": "equals", "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
        {"id": f"ctrl-{p}-new-owner", "kind": "control", "controlId": f"{p}_new_owner",
         "name": "Owner", "controlType": "text", "case": "insensitive", "mode": "equals",
         "value": "", "includeNulls": "when-no-value-is-selected", "showOperators": False},
        # Explicit submit target -- the caller places this control next to
        # wherever "submit for review" lives. Not an implicit "currently
        # selected" control (see module docstring).
        {"id": f"ctrl-{p}-submit-name", "kind": "control", "controlId": f"{p}_submit_name",
         "name": f"{entity_singular} to submit", "controlType": "text", "case": "insensitive",
         "mode": "equals", "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
        {"id": f"ctrl-{p}-selected-id", "kind": "control", "controlId": f"{p}_selected_id",
         "name": f"Selected {entity_singular} ID", "controlType": "text", "case": "insensitive",
         "mode": "equals", "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
        {"id": f"ctrl-{p}-selected-name", "kind": "control", "controlId": f"{p}_selected_name",
         "name": f"Selected {entity_singular} Name", "controlType": "text", "case": "insensitive",
         "mode": "equals", "value": "", "includeNulls": "when-no-value-is-selected",
         "showOperators": False},
        {"id": f"ctrl-{p}-decision", "kind": "control", "controlId": f"{p}_decision",
         "name": "Decision", "controlType": "segmented", "value": "Approved",
         "source": {"kind": "manual", "valueType": "text",
                    "values": ["Approved", "Adjust", "Rejected"],
                    "labels": ["Approve", "Request changes", "Reject"]}},
        {"id": f"ctrl-{p}-review-comments", "kind": "control", "controlId": f"{p}_review_comments",
         "name": "Reviewer Comments", "controlType": "text-area", "value": ""},
    ]

    def button(eid, label, effects, color="#1e3558", font="#ffffff", appearance="filled"):
        return {
            "id": eid, "kind": "button", "text": label,
            "appearance": appearance, "align": "stretch",
            "fillColor": color, "fontColor": font, "fontWeight": "bold",
            "actions": [{"id": f"action-{eid}", "trigger": "on-click", "effects": effects}],
        }

    btn_create = button(f"btn-{p}-create", f"New {entity_singular.lower()}", [
        {"effect": "open-overlay", "overlayId": modal_create_id},
    ], "#0d6efd")

    btn_create_submit = button(f"btn-{p}-create-submit", "Create draft", [
        {"effect": "insert-rows", "tableElementId": registry_id, "values": {
            f"{p}-rec-id": {"type": "formula",
                            "formula": f'"{p.upper()}-" & DateFormat(Now(), "%y%m%d-%H%M%S")'},
            f"{p}-rec-name": {"type": "control", "control": f"{p}_new_name"},
            f"{p}-rec-owner": {"type": "control", "control": f"{p}_new_owner"},
            f"{p}-rec-status": {"type": "constant", "value": {"type": "text", "value": "Draft"}},
        }},
        {"effect": "set-control-value", "control": f"{p}_submit_name",
         "value": {"type": "control", "control": f"{p}_new_name"}},
        {"effect": "clear-control", "scope": {"type": "control", "controlId": f"{p}_new_name"}},
        {"effect": "clear-control", "scope": {"type": "control", "controlId": f"{p}_new_owner"}},
        {"effect": "refresh-element", "target": {"type": "element", "element": review_id}},
        {"effect": "close-overlay"},
    ], "#0d6efd")

    btn_submit = button(f"btn-{p}-submit", f"Submit {entity_singular.lower()} for review", [
        {"effect": "update-rows", "tableElementId": registry_id,
         "whichRows": {"type": "formula",
                       "formula": f"[{entity_singular} Name] = [{p}_submit_name]"},
         "values": {f"{p}-rec-status": {"type": "constant",
                                        "value": {"type": "text", "value": "Submitted"}}}},
        {"effect": "refresh-element", "target": {"type": "element", "element": review_id}},
    ], "#198754")

    btn_review_submit = button(f"btn-{p}-review-submit", "Save decision", [
        {"effect": "update-rows", "tableElementId": registry_id,
         "whichRows": {"type": "formula",
                       "formula": f"[{entity_singular} ID] = [{p}_selected_id]"},
         "values": {
             f"{p}-rec-status": {"type": "control", "control": f"{p}_decision"},
             f"{p}-rec-comments": {"type": "control", "control": f"{p}_review_comments"},
         }},
        {"effect": "refresh-element", "target": {"type": "element", "element": review_id}},
        {"effect": "close-overlay"},
    ], "#198754")

    btn_delete = button(f"btn-{p}-delete", f"Delete {entity_singular.lower()}", [
        {"effect": "delete-rows", "tableElementId": registry_id,
         "whichRows": {"type": "formula", "formula": f"[{entity_singular} ID] = [{p}_selected_id]"}},
        {"effect": "refresh-element", "target": {"type": "element", "element": review_id}},
        {"effect": "close-overlay"},
    ], "#dc3545")

    btn_create_cancel = button(f"btn-{p}-create-cancel", "Cancel",
                                [{"effect": "close-overlay"}], "#ffffff", "#1e3558", "outline")
    btn_review_cancel = button(f"btn-{p}-review-cancel", "Cancel",
                                [{"effect": "close-overlay"}], "#ffffff", "#1e3558", "outline")

    text_review_title = {"id": f"{p}-title-review", "kind": "text",
                          "body": f"## **Approval Queue**\nSelect any {entity_singular.lower()} "
                                  "row to approve, request changes, reject, or delete it."}
    text_create_help = {"id": f"{p}-create-help", "kind": "text",
                         "body": f"New {entity_singular.lower()}. Starts as Draft with zero overrides."}
    text_review_help = {"id": f"{p}-review-help", "kind": "text",
                         "body": "Choose a decision and add reviewer comments."}

    review_page_id = f"page-{p}-review"
    data_page_id = f"page-{p}-data"

    pages = [
        {"id": data_page_id, "name": data_page_name, "visibility": "hidden"},
    ]
    if not embed_review:
        pages.insert(0, {"id": review_page_id, "name": review_page_name})
    overlays = [
        {"id": modal_create_id, "type": "modal", "name": f"New {entity_singular}",
         "modal": {"width": "small",
                   "header": {"title": f"New {entity_singular.lower()}", "showCloseIcon": "shown"},
                   "footer": {"primaryCta": {"visible": "hidden"},
                              "secondaryCta": {"visible": "hidden"}}}},
        {"id": modal_review_id, "type": "modal", "name": f"Review {entity_singular}",
         "modal": {"width": "small",
                   "header": {"title": f"Review {entity_singular.lower()}", "showCloseIcon": "shown"},
                   "footer": {"primaryCta": {"visible": "hidden"},
                              "secondaryCta": {"visible": "hidden"}}}},
    ]

    review_section_xml = f"""
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{review_page_id}">
  <Element elementId="{text_review_title['id']}" gridColumn="1 / 25" gridRow="1 / 4"/>
  <Element elementId="{kpis[0]['id']}" gridColumn="1 / 9" gridRow="4 / 11"/>
  <Element elementId="{kpis[1]['id']}" gridColumn="9 / 17" gridRow="4 / 11"/>
  <Element elementId="{kpis[2]['id']}" gridColumn="17 / 25" gridRow="4 / 11"/>
  <Element elementId="{review_id}" gridColumn="1 / 25" gridRow="11 / 28"/>
</Page>
"""
    layout_xml = f"""
{"" if embed_review else review_section_xml}
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{data_page_id}">
  <Element elementId="{registry_id}" gridColumn="1 / 25" gridRow="1 / 15"/>
  <Element elementId="ctrl-{p}-selected-id" gridColumn="1 / 9" gridRow="15 / 18"/>
  <Element elementId="ctrl-{p}-selected-name" gridColumn="9 / 17" gridRow="15 / 18"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{modal_create_id}">
  <Element elementId="{text_create_help['id']}" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="ctrl-{p}-new-name" gridColumn="1 / 25" gridRow="3 / 6"/>
  <Element elementId="ctrl-{p}-new-owner" gridColumn="1 / 25" gridRow="6 / 9"/>
  <Element elementId="{btn_create_cancel['id']}" gridColumn="13 / 19" gridRow="9 / 12"/>
  <Element elementId="{btn_create_submit['id']}" gridColumn="19 / 25" gridRow="9 / 12"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{modal_review_id}">
  <Element elementId="{text_review_help['id']}" gridColumn="1 / 25" gridRow="1 / 3"/>
  <Element elementId="ctrl-{p}-decision" gridColumn="1 / 25" gridRow="3 / 6"/>
  <Element elementId="ctrl-{p}-review-comments" gridColumn="1 / 25" gridRow="6 / 10"/>
  <Element elementId="{btn_delete['id']}" gridColumn="1 / 7" gridRow="10 / 13"/>
  <Element elementId="{btn_review_cancel['id']}" gridColumn="13 / 19" gridRow="10 / 13"/>
  <Element elementId="{btn_review_submit['id']}" gridColumn="19 / 25" gridRow="10 / 13"/>
</Page>
"""

    elements = [
        registry,
        # Controls declared before anything that could reference them by
        # formula -- element declaration order matters for control-in-formula
        # resolution (verified live 2026-08-13; see scenario-modeler-pattern.md).
        *controls,
        review, *kpis,
        text_review_title, text_create_help, text_review_help,
        btn_create, btn_create_submit, btn_submit, btn_review_submit,
        btn_delete, btn_create_cancel, btn_review_cancel,
    ]

    return {
        "elements": elements,
        "pages": pages,
        "overlays": overlays,
        "layout_xml": layout_xml,
        "unplaced": {
            "create_button": btn_create["id"],
            "submit_button": btn_submit["id"],
            "submit_target_control": f"ctrl-{p}-submit-name",
            # Only meaningful when embed_review=True -- lay these out inside
            # your own tab/page instead of relying on this module's own
            # "Review" page (which isn't generated in that mode).
            "review_title": text_review_title["id"],
            "review_kpi_total": kpis[0]["id"],
            "review_kpi_submitted": kpis[1]["id"],
            "review_kpi_approved": kpis[2]["id"],
            "review_table": review_id,
        },
    }
