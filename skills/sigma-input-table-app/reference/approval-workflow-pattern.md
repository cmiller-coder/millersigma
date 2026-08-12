# Forecast Approval Workflow Pattern

Use this pattern when a planning app needs a real state machine around editable
forecast rows:

```text
Draft → Submitted → Approved
                  ↘ Adjust
                  ↘ Rejected
```

Runnable example:
[`../examples/build_forecast_approval_workflow.py`](../examples/build_forecast_approval_workflow.py).

## Architecture

The workflow has two separate write-back tables:

1. **Plan Registry** — one row per scenario. Carries Plan ID, name, owner,
   status, reviewer comments, and Sigma's system audit columns.
2. **Forecast Entries** — one row per Plan ID × period × business dimension.
   Carries baseline, proposed value, row-level variance, and planner comments.

Do not put lifecycle status on every forecast row. Keeping status at the plan
grain makes transitions atomic and avoids partially submitted scenarios.

The visible review queue is a normal table sourced from the Plan Registry. It
hosts an `on-select` action that sets workbook variable controls and opens the
review modal.

## Why `inputMode: "view"`

`inputMode: "view"` allows published-workbook viewers to write. The tempting
default, `edit`, only allows writes while editing the workbook and silently
makes the published data app read-only.

## Status column

Use one validated text storage column:

```json
{
  "id": "pr-status",
  "name": "Status",
  "type": "text",
  "values": ["Draft", "Submitted", "Approved", "Adjust", "Rejected"],
  "pills": "color-by-option"
}
```

The create-plan action inserts `Draft`. The submit action writes `Submitted`.
The review modal uses a segmented control with the three reviewer decisions.

## Selecting rows for update

The example uses formula selectors:

```json
{
  "effect": "update-rows",
  "table": "it-plan-registry",
  "whichRows": {
    "type": "formula",
    "formula": "[Plan ID] = [selected_plan_id]"
  },
  "values": {
    "pr-status": {
      "type": "constant",
      "value": {"type": "text", "value": "Submitted"}
    }
  }
}
```

Why formula selection instead of `single-row.primaryKeys`:

- A fresh empty input table's system `ID` is unknown immediately after insert.
- The domain Plan ID is already available in the form and actions.
- Formula selection keeps the example portable across new workbooks.

The Plan ID must therefore be unique. In a production app, validate uniqueness
before insert or generate the ID in a trusted upstream process.

## Review modal

The queue's `on-select` action does three things in order:

1. Set `selected_plan_id` from the selected row.
2. Set `selected_plan_name`.
3. Open `modal-review`.

The modal's Save Decision button updates both Status and Reviewer Comments,
refreshes the review queue, and closes the overlay.

This avoids UI-only action sequences: every action is inline in the workbook
spec and survives a GET/PUT round trip.

## Refresh after writes

Every insert, update, or delete ends with:

```json
{
  "effect": "refresh-element",
  "target": {"type": "element", "element": "tbl-review"}
}
```

Without an explicit refresh, the write is persisted but the queue can continue
showing stale rows until the next workbook refresh.

## Forecast calculations

The forecast input table demonstrates the standard row-level modeler shape:

```text
Variance = Proposed − Baseline
```

For a fuller modeler, add:

- `Base Case` hidden formula column with a non-flat default scenario.
- `Effective Forecast = Coalesce([User Entry], [Base Case])`.
- Variance and uplift KPIs/charts sourced directly from the linked input table.
- A date dimension on KPIs for period comparison.
- Bulk populate/clear actions using `update-rows`.

See the main `sigma-input-table-app` skill for these non-negotiable defaults.

## Current API requirements

- Controls need IDs matching `^[a-zA-Z0-9_-]{1,64}$`; do not copy dotted IDs
  from old workbook GET-backs.
- Elements are flat in `document.elements`; pages contain metadata only.
- Modal definitions live in `document.overlays`, with content placed by a
  matching `<Page id="<overlay-id>">` block in `document.layout`.
- Action sequence IDs must be stable and workbook-unique.
- Input table storage-column IDs are action targets. If columns are recreated
  with new IDs, update every `values` map in every action.
- Never re-POST a large legacy GET-back as a new workbook. Re-author the small
  supported surface as this example does.

