# Scenario modeler — the cross-join pattern

A driver-based modeler supporting **multiple named scenarios**, built entirely
from code. Verified rendering on papercranestaging 2026-08-08.

> **Do not build this as a single linked input table off a pivot.** That produces
> an editable grid with exactly one implicit scenario — no Base Case, no
> comparison, no lifecycle. It looks like a modeler and isn't one. The mechanic
> that makes this work is the **cross join**.

The chain:

```
base table (ONE row per thing)
   ×  scenarios input table          ← cross join, left-outer on a constant
   =  scenario pivot                 ← Coalesce(name, "Base Case")
   →  assumptions (linked input table)   ← editable drivers + computed columns
   →  book (plain table)             ← what every KPI/chart reads
   →  scenario selector control      ← filters book
```

---

## 1. Base table — exactly one row per thing

```json
{"id": "sbase", "kind": "table", "name": "Product Base", "visibleAsSource": true,
 "source": {"connectionId": "<conn>", "kind": "sql", "statement": "<one row per product>"},
 "columns": [{"id": "sb-prod", "formula": "[Custom SQL/Product]", "name": "Product"},
             {"id": "sb-rev",  "formula": "[Custom SQL/Revenue]", "name": "Revenue"}]}
```

**This must genuinely be one row per thing.** A cross join runs against the
*underlying* rows, so pointing it at a grouped view of a monthly fact table
replicates each product once per month and inflates every downstream number by
the row multiple — 24 months gave a 24× overstatement that still looked
internally consistent. Aggregate in SQL before the join, not in a `groupings`
block after it.

## 2. Scenarios — a standalone input table

```json
{"id": "scenarios", "kind": "input-table",
 "source": {"kind": "empty", "connectionId": "<conn>"},
 "inputMode": "view", "name": "Scenarios",
 "columns": [{"id": "sc-name", "type": "text", "name": "Scenario Name"},
             {"id": "sc-status", "type": "text", "name": "Status",
              "values": ["Draft", "Submitted", "Approved"],
              "pills": "color-by-option"}]}
```

Standalone (`kind: "empty"`), because rows get **added** here — that's what a new
scenario is.

## 3. The cross join

```json
{"id": "spivot", "kind": "pivot-table", "name": "Scenario Pivot", "visibleAsSource": true,
 "source": {"kind": "join",
            "joins": [{"left":  {"elementId": "sbase", "kind": "table"},
                       "right": {"elementId": "scenarios", "kind": "table"},
                       "columns": [{"left": "1", "right": "1"}],
                       "joinType": "left-outer"}],
            "primarySource": {"elementId": "sbase", "kind": "table"}},
 "columns": [{"id": "pv-prod", "formula": "[Product Base/Product]", "name": "Product"},
             {"id": "pv-scen", "formula": "Coalesce([Scenarios/Scenario Name],\"Base Case\")",
              "name": "Scenario"},
             {"id": "pv-rev",  "formula": "Sum([Product Base/Revenue])", "name": "Baseline Revenue"}],
 "rowsBy": [{"id": "pv-prod"}], "values": ["pv-rev"]}
```

Two things doing the work:

- **`columns: [{"left": "1", "right": "1"}]`** — joining on a constant *is* the
  cross join. Every base row is paired with every scenario row.
- **`Coalesce(..., "Base Case")`** with **`left-outer`** — with zero scenarios
  created you still get a complete Base Case row set, so the page is never empty
  on first open.

## 4. Assumptions — the editable grid

```json
{"id": "assum", "kind": "input-table",
 "source": {"kind": "linked", "from": "spivot"},
 "inputMode": "view", "name": "Assumptions",
 "columns": [
   {"id": "ia-prod",   "key": "pv-prod"},
   {"id": "ia-scen",   "key": "pv-scen"},
   {"id": "ia-rev",    "key": "pv-rev"},
   {"id": "ia-growth", "type": "number", "name": "Balance Growth %"},
   {"id": "ia-prev",
    "formula": "[Baseline Revenue] * (1 + Coalesce([Balance Growth %], 0) / 100)",
    "name": "Projected Revenue"}],
 "order": ["ia-scen", "ia-prod", "ia-rev", "ia-growth", "ia-prev"]}
```

Three column forms, and mixing them up is the most common failure:

| form | use |
| --- | --- |
| `{"id", "key"}` | inherited from the pivot — name comes with it |
| `{"id", "type", "name"}` | new, user-editable |
| `{"id", "formula", "name"}` | computed **inside** the input table |

Computed columns use **bare, unqualified refs** — `[Baseline Revenue]`,
`[Balance Growth %]` — because they resolve within the table. Wrap every driver
in `Coalesce(..., 0)` so an untouched grid projects to exactly the baseline
rather than null.

### `inputMode` is the data-entry permission

| value | who | where |
| --- | --- | --- |
| `edit` *(default)* | workbook editors only | **draft only** |
| `explore` | explore-or-greater | published |
| **`view`** | **everyone** | **published** |

Leave the default and the published modeler is read-only, and every button/agent
`update-rows` silently no-ops. **A modeler that "used to work" is almost always
this.** The product states it directly: *"To update row(s) in published version,
the selected input table's data entry permission must be changed to Editable in
published version."*

## 5. Book — the single downstream source

```json
{"id": "book", "kind": "table", "name": "Book", "visibleAsSource": true,
 "source": {"elementId": "assum", "kind": "table"},
 "columns": [{"id": "bb-scen", "formula": "[Assumptions/Scenario]", "name": "Scenario"},
             {"id": "bb-brev", "formula": "[Assumptions/Baseline Revenue]", "name": "Baseline Revenue"},
             {"id": "bb-prev", "formula": "[Assumptions/Projected Revenue]", "name": "Projected Revenue"}]}
```

Every KPI and chart reads `book`, never `assum` directly — so the scenario filter
applies once, in one place.

## 6. Scenario selector

```json
{"kind": "control", "id": "ctrl-sel", "controlId": "scenarioSelect",
 "name": "Active scenario", "controlType": "list", "selectionMode": "single",
 "mode": "include", "value": "Base Case", "values": [],
 "filters": [{"source": {"kind": "table", "elementId": "book"}, "columnId": "bb-scen"}],
 "source": {"kind": "source", "source": {"kind": "table", "elementId": "book"},
            "columnId": "bb-scen"}}
```

## 7. Create / Submit / Approve

The create button lives **inside the modal page** — overlay-level `actions`
cannot resolve controls, even ones declared in that overlay
(`Control not found: <id>`). Hide the footer CTAs and use a real button:

```json
"effects": [
  {"effect": "insert-rows", "tableElementId": "scenarios",
   "values": {"sc-name": {"type": "control", "control": "newScenarioName"},
              "sc-status": {"type": "constant", "value": {"type": "text", "value": "Draft"}}}},
  {"effect": "set-control-value", "control": "scenarioSelect",
   "value": {"type": "control", "control": "newScenarioName"}},
  {"effect": "clear-control", "scope": {"type": "control", "controlId": "newScenarioName"}},
  {"effect": "close-overlay"}]
```

Insert → select → clear, in that order, so the new scenario is active immediately.

Submit/Approve append to a separate log input table — append-only, never an edit
in place:

```json
{"effect": "insert-rows", "tableElementId": "subs",
 "values": {"su-scen":   {"type": "control", "control": "scenarioSelect"},
            "su-status": {"type": "constant", "value": {"type": "text", "value": "Submitted"}},
            "su-by":     {"type": "formula", "formula": "CurrentUserEmail()"}}}
```

## 8. Chart — `stacking: "none"`

Two y-axis series **stack by default**, so projected-vs-baseline renders their
*sum*. It looks plausible and is wrong.

```json
"yAxis": {"columnIds": ["bj-base", "bj-proj"]},
"stacking": "none"
```

## 9. Bulk-edit and reset

`delete-rows` is rejected against a linked input table — its rows come from the
pivot (`cannot delete rows from a linked input table`). Reset writes nulls:

```json
{"effect": "update-rows", "tableElementId": "assum",
 "whichRows": {"type": "formula", "formula": "True"},
 "values": {"ia-growth": {"type": "constant", "value": {"type": "number", "value": null}}}}
```

`delete-rows` is only legal against a standalone `{"kind": "empty"}` table.

### Always ship a "Reset scenarios" button

`Coalesce(..., "Base Case")` only produces Base Case while the scenarios table is
**empty**. The moment anyone types a scenario — including a junk row during a
demo — Base Case stops existing, and a selector pinned to `"value": "Base Case"`
matches nothing and every KPI renders `null`. The dashboard looks broken and the
cause is data, not code, so nothing in the spec will point at it.

Put a text button on the scenario-log tab that wipes both standalone tables and
re-points the selector:

```json
"effects": [
  {"effect": "delete-rows", "tableElementId": "scenarios",
   "whichRows": {"type": "formula", "formula": "True"}},
  {"effect": "delete-rows", "tableElementId": "subs",
   "whichRows": {"type": "formula", "formula": "True"}},
  {"effect": "set-control-value", "control": "scenarioSelect",
   "value": {"type": "constant", "value": {"type": "text", "value": "Base Case"}}}]
```

This is also the only way to clean a shared demo workbook — input-table rows are
data, not spec, so re-`PUT`ting the spec does not clear them.

## A global what-if lever: computed column reading a control

For a lever that should re-rank/re-scale *every row at once* (a "bulk shift %"
slider, say) — do not reach for `update-rows` with a per-row `formula` value;
that has no row context when fired from a button and fails only on a real
click (see `approval-workflow-pattern.md`'s section on this). Instead, add a
hidden formula column that reads the control directly, same bracket syntax as
any other column reference:

```json
{"id": "ia-shiftfactor", "hidden": true, "name": "Shift Factor",
 "formula": "1 + Coalesce([bulk_shift_pct], 0) / 100.0"},
{"id": "ia-proj", "name": "Projected Units",
 "formula": "[Baseline Units] * (1 + Coalesce([Growth %], 0) / 100.0) * [Shift Factor]"}
```

This resolves per row at query time, is instant, and cannot partially fail.

### The control must be declared BEFORE the element that references it

**Verified live 2026-08-13, papercranestaging.** `document.elements` is an
array, and a formula column's `[controlId]` reference only resolves if that
control's element appears **earlier** in the array than the element doing the
referencing. The exact same input-table definition, byte-for-byte, was created
twice — once with the control declared before it, once after — using a
disposable isolation workbook to bisect the difference:

- Control declared first → renders correctly.
- Control declared after → `Reference to errored column "[Shift Factor]"` on
  every row of the dependent column, and any chart/table downstream of it.

Both versions pass `verify` and `create` with `valid: true` / `success: true`
— **this only shows up on a real render**, same "looks fine until you click
it" shape as the row-context bug and the linked-table `key`-vs-`formula`
gotcha. The error message doesn't mention ordering at all, so if you hit
`Reference to errored column` on a column whose formula looks correct in
isolation, check whether every `[controlId]` it references is declared earlier
in `elements` before assuming the formula itself is wrong.

Practical rule: **declare every `control` element immediately after the base
table(s) it filters/drives, before any table, pivot, or input-table that
references it in a formula.** Controls only referenced by button `actions`
(not by a formula column) were not observed to have this constraint, but
declaring them early costs nothing and removes the question.

---

## Verify

1. `create`/`update` — not `verify`, which skips SQL resolution and dangling ids.
2. **Sanity-check the baseline against a known total.** The 24× inflation above
   passed every structural check; only comparing the modeler's total to the
   source book caught it.
3. Render to PNG and look (`POST /v2/workbooks/{id}/export` → poll
   `GET /v2/query/{queryId}/download`).
4. Click one cell in the published view — the only thing a render can't prove.

Worked reference: `~/Desktop/Prospects/SoFi-2026/scripts/build_sofi.py` (page 2),
and the original in `sigma-company-dashboard/examples/build_company_command_center.py`.
