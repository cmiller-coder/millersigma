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

## `values` formulas have no row context when the trigger is a button

**A `values` entry of `type: "formula"` cannot reference the target row's own
columns when the action is fired from a button.** Sigma's docs list the value
sources for Update row(s) as static value, *column from the trigger element*,
control, and formula — and a button is not a row-bearing trigger, so there is
no row to evaluate a per-row expression against.

This fails at click time, not at write time. The spec passes `verify`, saves
cleanly, round-trips through `GET /spec`, and every element compiles SQL. The
only symptom is a toast when a user actually clicks:

```text
144 input table edits could not be applied: numeric value
Invalid Query: Unknown column "[Baseline Units]" is invalid.
```

Rejected (per-row expression, no row):

```json
"values": {"al-prop": {"type": "formula", "formula": "[Baseline Units]"}}
```

Safe from a button — scalars only:

```json
"values": {
  "pr-status": {"type": "constant", "value": {"type": "text", "value": "Submitted"}},
  "pr-comments": {"type": "control", "control": "review_comments"},
  "al-prop": {"type": "constant", "value": {"type": "number", "value": null}}
}
```

Note that `whichRows` is a different context: it *is* a row filter over the
element, so `[Powertrain] = "BEV"` there is fine. Only `values` is scalar-only.

**The same restriction applies to a Sigma AI agent's action tools.** An
`update-rows` effect fired from an agent tool step (`document.agents[].tools[]`)
has no row-bearing trigger either, so its `values` are constants / controls /
scalar formulas only — never a per-row expression. Model any per-row transform
as a computed column (below) and have the tool set a control instead. See
`sigma-workbook-conventions/reference/workbook-spec-api.md` → "Agents & chat
(Sigma AI copilots)."

A **scalar** formula in `values` is fine, which is the clean way to stop asking
users to invent a record ID:

```json
"pr-id": {"type": "formula",
          "formula": "\"PLAN-\" & DateFormat(Now(), \"%y%m%d-%H%M%S\")"}
```

Generate the identifier on insert and never put it in the form. Nothing needs to
guess it afterwards, because the review queue's `on-select` handler is what
populates the selected-plan control.

**Do not reach for a write action to seed or transform a column from other
columns.** Model it as a computed column instead, because column formulas *can*
read both key-bound source columns and control values:

```json
{"id": "al-factor", "name": "Scenario Factor", "hidden": true,
 "formula": "If([Powertrain] = \"BEV\", 1 + [c_bev_shift] / 100, 1)"},
{"id": "al-scen", "name": "Scenario Units", "hidden": true,
 "formula": "Round([Basis Units] * [Scenario Factor])"},
{"id": "al-eff", "name": "Effective Units",
 "formula": "Coalesce([Proposed Units], [Scenario Units])"}
```

This is strictly better than a write action for what-if scenarios: it is
instant (no multi-thousand-row warehouse write to wait on), it cannot partially
fail, and `Coalesce` still lets a typed cell override the scenario — which is
what write-back is actually for. Keep one write action to *clear* overrides
(constants only) and let controls drive everything else.

## Modal footer CTAs must be hidden

Overlay-level actions cannot resolve controls, so a modal that writes anything
needs `button` elements inside the modal page. The built-in footer CTAs are
therefore dead weight, and if left visible the user sees a second,
non-functional pair of buttons beside the working ones:

```json
{"id": "m-create", "type": "modal", "name": "Create plan",
 "modal": {"width": "small",
           "header": {"title": "Create allocation plan", "showCloseIcon": "shown"},
           "footer": {"primaryCta": {"visible": "hidden"},
                      "secondaryCta": {"visible": "hidden"}}}}
```

`width` accepts `x-small` / `small` / `large`. Use `small` or `x-small` for a
form of a few fields — `large` renders as a full-width sheet. Note that
`header.title` cannot be an empty string (it crashes the overlay); use `" "` for
a deliberately blank bar.

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

## Key columns are FROZEN once a linked input table exists

Verified live 2026-08-13 on papercranestaging. A linked input table's `key`
bindings are immutable after creation. Repointing an existing linked input table
at a different source element fails the PUT:

```text
elements[7].columns[0]: Cannot change key columns on existing linked input table:
it-commission. Key column "cm-scenario" (bound to source column "jn-scenario")
does not match the existing key binding; key columns are fixed once the input
table is created.
```

This bites when you evolve a modeler — e.g. moving the grid from a plain SQL
table onto a cross-join so scenarios become user-created rows. The fix is to
**give the grid a new element `id`** and drop the old one in the same PUT. Keep
the `name` identical (`"Commission Scenarios"`) and every downstream formula,
which resolves by display name (`[Commission Scenarios/Final Payout]`), keeps
working untouched — only id references (element `source.elementId`, control
`filters`, `update-rows` `table`, agent `dataSources`, layout `elementId`) need
the rename.

⚠️ The old input table's stored rows are dropped with it. Fine for a demo or a
scenario sandbox; plan a migration for anything holding real user data.

## Scenario registries: make "create a new scenario" a real action

A scenario list seeded in SQL can be *edited* but never *extended* — users cannot
create a scenario, which is the heart of a modeling app. The working shape
(verified 2026-08-13):

1. **Baseline** — a normal `table` at the grain you model (one row per rep,
   segment, plant …). No scenarios in the SQL.
2. **Registry** — an EMPTY `input-table` (`source: {kind: "empty", connectionId}`,
   `inputMode: "view"`), one row per scenario, holding scenario-level assumptions
   plus the lifecycle columns (status pills, finance note).
3. **Cross join** — a `table` whose `source` is
   `{kind: "join", joins: [{left: baseline, right: registry, columns: [{left: "1", right: "1"}], joinType: "left-outer"}], primarySource: baseline}`.
   Resolve each assumption as `Coalesce([Registry/<Assumption>], <governed default>)`
   and the scenario label as `Coalesce([Registry/Scenario Name], "Base Plan")`.
4. **Modeling grid** — a linked input table over the join, `key`-bound to the
   join's columns, carrying the per-row overrides and `Coalesce` finals.
5. **Create** — a modal whose button does
   `insert-rows(registry) → set-control-value(scenarioSelect ← new name) → refresh-element ×3 → clear-control ×N → close-overlay`.

Three constraints that shape this:

- **There is no union/append source kind.** `kind: "union"`, `"append"` and
  `"union-all"` are all rejected (masked as `Invalid kind: "table"`), so you
  cannot concatenate a SQL seed list with a user registry. The registry has to be
  the *single* source of scenario rows.
- **`left-outer` + `Coalesce` is the empty-state guard.** With an empty registry
  the join still yields one row per baseline row labelled `"Base Plan"` at
  governed defaults, so the page is never blank before the first scenario exists.
  Note the corollary: once any scenario exists, the fallback label disappears.
- **No public API seeds input-table rows.** `/v2/workbooks/{id}/input-tables`
  and friends are 404. Ship a **"Load governed plans"** button that fires one
  `insert-rows` per starter scenario (constants only) so a fresh build is one
  click from demo-ready.

Put the lifecycle on the **registry**, not on every baseline row: status is a
property of the scenario, so `update-rows` with
`whichRows: [Scenario Name] = [scenarioSelect]` touches one row, and the grid
inherits it through the join as a read-only column.

## Ticketing / case-management pattern (dispute resolution)

A dispute/ticket workflow is a registry + an append-only comment log + a status
lifecycle. Verified live on papercranestaging 2026-08-13 (ShiftKey "Commission
Disputes", adapted from the demeng "Commissions Dispute" POV).

1. **Ticket registry** — an EMPTY `input-table` (`inputMode: "view"`), one row
   per ticket. Business fields (requestor, subject, amount, priority) plus:
   - **A generated ID written on insert**, never asked of the user:
     `"dp-ticket": {"type": "formula", "formula": "\"DSP-\" & DateFormat(Now(), \"%y%m%d-%H%M%S\")"}`.
   - **A status column** (`values: [...]`, `pills: "color-by-option"`).
   - **One `datetime` column per lifecycle stage** (In Review / Escalation /
     Resolved dates) — see the `Now()` write below.
   - **A threaded comment view** that pulls the whole log for this ticket into
     one cell:
     `Lookup(ListAgg([Comment Log/Entry Text], "\n\n"), [Ticket ID], [Comment Log/Ticket ID])`.
   - **An age column**:
     `DateDiff("day", [Created At], Coalesce([Resolved Date], Now()))`.
2. **Comment log** — an append-only EMPTY `input-table` (`inputMode: "edit"`),
   keyed by ticket id, with an author column, the comment text, the auto system
   columns `{id: "CREATED_AT"}` + `{id: "CREATED_BY"}` (do NOT write these in the
   insert), and a rendered `Entry Text` formula
   (`DateFormat([Created At], "%b %-d %-I:%M %p") & "  ·  " & [Author] & ": " & [Comment]`).
3. **Queue** — a `table` over the registry with an `on-select` action that sets a
   `selected_ticket` control and opens the detail modal (same row-select →
   control → overlay chain as a record picker).
4. **Detail modal** — a comment-thread table filtered to `selected_ticket`, a
   compose-comment control + Add-comment button (`insert-rows` into the log), and
   the lifecycle buttons.

Two mechanics worth reusing:

- **Stamp SLA dates with a scalar `Now()` in `update-rows`.** A status button
  both sets the status constant and writes the timestamp:
  `"dp-resolved": {"type": "formula", "formula": "Now()"}`. `Now()` is a scalar,
  so it is legal in `values` (unlike a per-row column expression). The `whichRows`
  filter is `[Ticket ID] = [selected_ticket]`.
- **The selected-ticket control both receives `set-control-value` and filters.**
  One `text` control (`mode: "equals"`) is set from the queue's `on-select`
  column value and carries `filters` targeting the comment log + thread table, so
  the modal shows only that ticket's trail.

Empty-state polish: `SumIf`/`Avg(If(...))` KPIs return `null` on an empty
registry and render as an ugly "null". Wrap them in `Coalesce(..., 0)`.

## Linked input tables: carry source columns as `key`, not `formula`

Verified live 2026-08-12 on a 576-row baseline. When a linked input table
(`source: {kind: linked, from: <element>}`) needs to display columns from its
source, bind them as **key** columns:

```json
{"id": "al-month", "key": "ab-month", "name": "Month"}
```

A `formula` passthrough does **not** scope to the linked row:

| Source shape | Passthrough style | Result |
|---|---|---|
| ungrouped table | `formula: "[Source/Col]"` | renders `multiple values`; wrapping in `Min()`/`Sum()` "fixes" the error but returns the **whole-table** aggregate on every row — silently wrong data |
| grouped table | `formula: "[Source/Col]"` | returns blank |
| either | `key: "<source-col-id>"` | correct per-row value |

The failure is dangerous because the aggregate-wrapped version looks plausible:
every row shows the same grand total (e.g. an Accord row reporting the entire
network's units and the wrong plant). Export the input table to CSV and confirm
row values differ before trusting the grid.

Only the editable storage columns (`type: number` / `text`) and locally-derived
formula columns belong outside the key set. Local formulas referencing the
element's own column names work normally:

```json
{"id": "al-eff", "name": "Effective Units",
 "formula": "Coalesce([Proposed Units], [Baseline Units])"}
```

## Aggregating at a group grain, not the leaf grain

A KPI sourced from a grouped table still counts **leaf** rows by default. A
`CountIf` over a per-group status column returned 96 (the leaf rows behind the
breaching groups) instead of 6 (the groups themselves). Count a
group-identifying value instead:

```json
{"formula": "CountDistinct(If([Plant Month Load/Capacity Status] = \"Over capacity\", [Plant Month Load/Plant Month], Null))"}
```

where `Plant Month` is a grouping calculation such as
`[Plant] & " · " & DateFormat([Month], "%b %Y")`.

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

