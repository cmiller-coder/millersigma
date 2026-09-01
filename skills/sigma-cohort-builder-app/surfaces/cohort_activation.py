"""Pluggable cohort-activation surface — "send to [ESP/CRM]" with a
confirmation, not an approval lifecycle.

Cohort builders are a different shape from scenario/reallocation/commission
modelers: there's no number to approve, just a population to push somewhere.
So instead of surfaces_approval_workflow.py's Draft->Submitted->Approved
lifecycle, this is: pick a destination, click Activate, get a confirmation
+ a persistent audit trail. `destinations` is the one thing to tailor per
prospect -- pass whichever ESP/CRM/ad platform they actually use (Iterable,
Braze, Salesforce Marketing Cloud, HubSpot, an ad platform's audience API,
...); there is no default that fits everyone the way Approved/Adjust/
Rejected fits every approval workflow.

Hard platform constraint this works around: Sigma's action effect enum has
exactly 12 members (Open URL, Open/Close Overlay, Set/Clear Control, Insert/
Update/Delete Rows, Refresh Element, Navigate, Open Document, Select Tab) --
verified against the live OpenAPI schema 2026-08-13. There is no call-api
effect and no native toast/notification component, so an outbound "send to
Iterable" is NOT a real integration from a workbook spec -- it can only be
simulated: insert-rows into an audit-log table (the persistent, truthful
part) plus an open-overlay confirmation (the "toast" a demo needs). Say this
distinction out loud to a prospect; don't imply the workbook actually calls
Iterable's API.

Usage:

    import surfaces_cohort_activation as activation
    a = activation.build(
        prefix="act", connection_id=CONN,
        cohort_table_id="population", cohort_table_name="Population",
        cohort_name_formula='"All customers"',   # or a control/column reference
        count_formula="CountDistinct([Population/Customer ID])",
        destinations=[{"id": "iterable", "label": "Iterable"},
                      {"id": "braze", "label": "Braze"}],
    )
    elements += a["elements"]; pages += a["pages"]; overlays += a["overlays"]
    layout += a["layout_xml"]
    # Place a["unplaced"]["activate_button"] wherever the cohort builder page
    # wants it (e.g. next to the existing "Save cohort" button).
"""


def build(
    prefix,
    connection_id,
    cohort_table_id,
    cohort_table_name,
    cohort_name_formula,
    count_formula,
    destinations,
    history_page_name="Activation History",
):
    """`cohort_name_formula` and `count_formula` are formula strings evaluated
    against whatever page the Activate button lives on -- typically a bare
    control reference (`"[cohort_name_ctrl]"`) and a live COUNT/CountDistinct
    over the current filtered population. `destinations` is a list of
    {"id","label"}; at least one is required, and there is no built-in
    default -- ask which platform(s) the prospect actually uses.
    """
    if not destinations:
        raise ValueError("destinations is required -- ask the prospect which "
                          "ESP/CRM/ad platform they actually use")
    p = prefix
    log_id = f"{p}-log"
    modal_id = f"m-{p}-confirm"

    log = {
        "id": log_id, "kind": "input-table", "name": "Activation Log",
        "inputMode": "view",
        "source": {"kind": "empty", "connectionId": connection_id},
        "columns": [
            {"id": f"{p}-lg-cohort", "name": "Cohort", "type": "text"},
            {"id": f"{p}-lg-dest", "name": "Destination", "type": "text",
             "values": [d["label"] for d in destinations], "pills": "color-by-option"},
            {"id": f"{p}-lg-count", "name": "Record Count", "type": "number"},
            {"id": "CREATED_AT", "name": "Activated At"},
            {"id": "CREATED_BY", "name": "Activated By"},
        ],
        "tableComponents": {"summaryBar": "hidden"},
    }

    history = {
        "id": f"{p}-history", "kind": "table", "name": "Activation History",
        "source": {"kind": "table", "elementId": log_id},
        "columns": [
            {"id": f"{p}-h-cohort", "name": "Cohort", "formula": "[Activation Log/Cohort]"},
            {"id": f"{p}-h-dest", "name": "Destination", "formula": "[Activation Log/Destination]"},
            {"id": f"{p}-h-count", "name": "Record Count", "formula": "[Activation Log/Record Count]"},
            {"id": f"{p}-h-when", "name": "Activated At", "formula": "[Activation Log/Activated At]"},
            {"id": f"{p}-h-who", "name": "Activated By", "formula": "[Activation Log/Activated By]"},
        ],
        "sort": [{"columnId": f"{p}-h-when", "direction": "descending", "nulls": "last"}],
        "tableComponents": {"summaryBar": "hidden"},
    }

    dest_control = {
        "id": f"ctrl-{p}-dest", "kind": "control", "controlId": f"{p}_destination",
        "name": "Send to", "controlType": "segmented" if len(destinations) <= 4 else "list",
        "value": destinations[0]["label"],
        "source": {"kind": "manual", "valueType": "text",
                   "values": [d["label"] for d in destinations],
                   "labels": [d["label"] for d in destinations]},
    }

    confirm_text = {
        "id": f"{p}-confirm-text", "kind": "text",
        "body": (f"### Activation confirmed\n"
                 f"**{{{{{cohort_name_formula}}}}}** was sent to "
                 f"**{{{{[{p}_destination]}}}}**. **{{{{{count_formula}}}}}** records queued "
                 "for activation.\n\n_This is a simulated confirmation for the demo — "
                 "wire a real export/webhook for production use._"),
    }

    btn_activate = {
        "id": f"btn-{p}-activate", "kind": "button", "text": "Activate cohort",
        "appearance": "filled", "align": "stretch", "fillColor": "#0d6efd",
        "fontColor": "#ffffff", "fontWeight": "bold",
        "actions": [{"id": f"action-btn-{p}-activate", "trigger": "on-click", "effects": [
            {"effect": "insert-rows", "tableElementId": log_id, "values": {
                f"{p}-lg-cohort": {"type": "formula", "formula": cohort_name_formula},
                f"{p}-lg-dest": {"type": "control", "control": f"{p}_destination"},
                f"{p}-lg-count": {"type": "formula", "formula": count_formula},
            }},
            {"effect": "refresh-element", "target": {"type": "element", "element": f"{p}-history"}},
            {"effect": "open-overlay", "overlayId": modal_id},
        ]}],
    }
    btn_done = {
        "id": f"btn-{p}-done", "kind": "button", "text": "Done",
        "appearance": "filled", "align": "stretch", "fillColor": "#198754",
        "fontColor": "#ffffff", "fontWeight": "bold",
        "actions": [{"id": f"action-btn-{p}-done", "trigger": "on-click",
                     "effects": [{"effect": "close-overlay"}]}],
    }

    data_page_id = f"page-{p}-data"
    raw_page_id = f"page-{p}-raw"
    pages = [{"id": data_page_id, "name": history_page_name},
             {"id": raw_page_id, "name": "Data", "visibility": "hidden"}]
    overlays = [
        {"id": modal_id, "type": "modal", "name": "Activation Confirmed",
         "modal": {"width": "small", "header": {"title": "Activation confirmed", "showCloseIcon": "shown"},
                   "footer": {"primaryCta": {"visible": "hidden"},
                              "secondaryCta": {"visible": "hidden"}}}},
    ]
    elements = [log, dest_control, history, confirm_text, btn_activate, btn_done]

    layout_xml = f"""
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{data_page_id}">
  <Element elementId="{history['id']}" gridColumn="1 / 25" gridRow="1 / 18"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{raw_page_id}">
  <Element elementId="{log_id}" gridColumn="1 / 25" gridRow="1 / 15"/>
</Page>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="{modal_id}">
  <Element elementId="{confirm_text['id']}" gridColumn="1 / 25" gridRow="1 / 8"/>
  <Element elementId="{btn_done['id']}" gridColumn="19 / 25" gridRow="8 / 11"/>
</Page>
"""

    return {
        "elements": elements,
        "pages": pages,
        "overlays": overlays,
        "layout_xml": layout_xml,
        "unplaced": {
            "activate_button": btn_activate["id"],
            "destination_control": dest_control["id"],
        },
    }
