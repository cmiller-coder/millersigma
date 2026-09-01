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

**Combining this with a scenario modeler (control-driven bulk-shift lever,
not just per-row entry)?** Use
[`../examples/build_scenario_approval_workbench.py`](../examples/build_scenario_approval_workbench.py)
and see `scenario-modeler-pattern.md`'s section on the element-declaration-order
requirement for controls referenced in formula columns — a real, previously
undocumented gotcha found building the combined version.

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

## Why `inputMode: "view"` — and its current limit

`inputMode: "view"` is the setting that is *supposed to* let published-workbook
viewers write. The tempting default, `edit`, only allows writes while editing
the workbook and silently makes the published data app read-only.

**Verified live on papercranestaging, 2026-08-12/13: `inputMode: "view"`
stores and validates, but direct cell-click editing in default (published,
non-edit) view is still rejected on this org.** A from-scratch workbook, never
touched in the UI, with a plain `inputMode: "view"` input table, did not
accept typed input in a cell without first clicking "Edit workbook." Don't
trust an earlier "verified end-to-end" note about this setting elsewhere in
this repo — that check only confirmed the field round-trips on GET, not that
the runtime honors it.

**What still works: button-triggered `insert-rows` / `update-rows` /
`delete-rows` actions.** Every write in this example — create plan, submit,
approve/adjust/reject, delete, and add forecast entry — goes through a button
+ control(s) + effect, never a raw cell edit. That path is unaffected by the
cell-editing limitation above. **Build every write-back surface this way —
controls feeding an action button — until Sigma confirms direct published-mode
cell editing is fixed; don't rely on a viewer typing directly into an
input-table cell outside of Edit mode.**

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
  "tableElementId": "it-plan-registry",
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
before insert or generate the ID in a trusted upstream process — or better,
skip asking the user for an ID at all. A **scalar** formula in an action
`values` map is legal (only *per-row* formulas over a button trigger are
rejected, see below), which is the clean way to auto-generate one on insert:

```json
"pr-id": {"type": "formula",
          "formula": "\"PLAN-\" & DateFormat(Now(), \"%y%m%d-%H%M%S\")"}
```

Nothing downstream needs to guess it afterwards, because the review queue's
`on-select` handler is what populates the selected-plan control.

## `values` formulas have no row context when the trigger is a button

**A `values` entry of `type: "formula"` cannot reference the target row's own
columns when the action is fired from a button.** Sigma's docs list the value
sources for Update row(s) as static value, *column from the trigger element*,
control, and formula — and a button is not a row-bearing trigger, so there is
no row to evaluate a per-row expression against. This fails at click time, not
at write time — the spec passes `verify`, saves, round-trips, and every
element compiles SQL; the only symptom is a toast when a user actually clicks
("Unknown column [X] is invalid"). `whichRows` is a different context (a row
filter over the element, so `[Powertrain] = "BEV"` there is fine) — only
`values` is scalar-only. **Model any bulk what-if lever as a computed column
reading a control instead** (see `scenario-modeler-pattern.md`) — it resolves
per row at query time, is instant, and cannot partially fail.

## Modal footer CTAs must be hidden

Overlay-level actions cannot resolve controls, so a modal that writes anything
needs `button` elements inside the modal page. The built-in footer CTAs are
dead weight, and if left visible the user sees a second, non-functional pair
of buttons beside the working ones:

```json
{"id": "m-create", "type": "modal", "name": "Create plan",
 "modal": {"width": "small",
           "header": {"title": "Create plan", "showCloseIcon": "shown"},
           "footer": {"primaryCta": {"visible": "hidden"},
                      "secondaryCta": {"visible": "hidden"}}}}
```

`width` accepts `x-small` / `small` / `large` — use `small`/`x-small` for a
form of a few fields; `large` renders as a full-width sheet. `header.title`
cannot be an empty string (crashes the overlay) — use `" "` for a
deliberately blank bar.

**Don't source `selected_plan_id` implicitly across pages.** The first version
of this example had the Forecast page's "Submit for review" button target
whatever `selected_plan_id` happened to hold — which is only reliably set by
the create-plan flow, or by having already visited the Review page and
clicked a row. Land on the Forecast page for a plan you didn't just create,
and Submit silently targets the wrong row (or none). Fixed by adding an
explicit `submit_plan_id` text control on the Forecast page itself: the
planner types/pastes the Plan ID they mean to submit, and the button's
`whichRows` formula references that control instead. Explicit beats implicit
cross-page state for any action a user can reach from more than one place.

**Forecast Entries also needs a button+modal insert, not raw cell typing** —
see the `inputMode` section above. The fixed example adds an "Add forecast
entry" button opening a modal with Plan ID / Period (date control) / Dimension
/ Baseline / Proposed (number controls) / Planner Comments, inserting via the
same `insert-rows` pattern as Create Plan, followed by
`refresh-element` on `it-forecast`.

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

