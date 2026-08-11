# Recreating an existing Sigma app from its live spec

The move: point at any live Sigma workbook, pull its real spec via the API,
and rebuild a **distilled** version from scratch as code — rather than
guessing at a design from a screenshot, or (worse) re-POSTing the GET-back
directly (see the standing rule in `../SKILL.md`: never re-POST a UI-built
workbook's GET-back — round-tripped specs carry stale/UI-only fields that
reject on write).

## Workflow

1. **Resolve the workbook.** `GET /v2/workbooks/{urlId}` accepts the
   `workbookUrlId` straight out of the app URL (`.../workbook/<Name>-<urlId>`)
   and returns the real `workbookId` — no search needed.
2. **Pull the spec.** `GET /v2/workbooks/{workbookId}/spec` returns the full
   YAML. Production apps run into the thousands of lines (multi-page,
   multi-modal, plan/lifecycle machinery) — read it in chunks, don't try to
   hold the whole thing in context at once.
3. **Identify the core interaction loop**, separate from the incidental
   scaffolding. A real demand-planning app example had: (a) an
   actuals-vs-forecast chart + accuracy/bias KPIs, (b) an editable
   assumptions grid feeding an adjusted forecast, (c) multi-plan
   create/submit/approve lifecycle, (d) an AI insight panel. (a) and (b) are
   the mechanic; (c) and (d) are product depth that a "lite" rebuild can
   drop entirely.
4. **Rebuild (b)+(a) using the verified patterns in this skill** —
   `scenario-modeler-pattern.md`'s linked-input-table chain is almost always
   the right shape for "editable assumption → reactive chart/KPI." Don't
   invent a new mechanic (e.g. a standalone slider control referenced
   directly in an unrelated chart's formula) without checking whether it's
   actually a documented, verified primitive first — it likely isn't; Sigma
   controls talk to other elements through `filters` or `effects`
   (`set-control-value`/`update-rows`), not through bare formula references
   to the control's live value.
5. **QA every element** (see `../SKILL.md` Workflow step 4) before calling it
   done, even for a "lite" build — the following gotchas were all first
   caught this way.

## Gotchas hit rebuilding a real Demand Planning app (new, 2026-08-11)

- **A bare `[col]` formula does NOT reach the raw SQL output on a custom-SQL
  table that hand-authors its own `columns` array — it needs
  `[Custom SQL/col]` (the raw query result has an implicit source name
  `"Custom SQL"`, even referenced from inside the very element that IS the
  SQL source).** Getting this wrong is dangerously silent at POST/PUT time —
  the spec saves fine — and only shows up when someone actually opens the
  workbook: every cell in that column renders the literal string
  `Unknown column "[col]"`, and every DOWNSTREAM element (a linked input
  table, a chart, a KPI) shows an unrelated-looking cascade error —
  `"Invalid Argument: Join key contains type error"` — pointing at the wrong
  element entirely. **If you see that error on a linked-input-table/chart,
  go check the upstream custom-SQL table's own column formulas first**,
  even though the error text doesn't mention it. This is exactly the kind of
  bug POST-time validation and even export-based QA (see below) will not
  catch — only opening it in-browser (or a screenshot from someone who did)
  surfaced it here.
- **Circular column reference is a related but distinct trap.** Declaring a
  passthrough/aggregate column with `formula:"[demand_fcst]"` AND
  `name:"demand_fcst"` (same string) makes the bare bracket resolve to the
  sibling column itself — Sigma rejects it: `"Circular column reference to
  [demand_fcst]"`. **Fix: always give a declared column a display `name`
  that's textually different from the raw column name in its own `formula`
  bracket** (and, per the bullet above, qualify the SOURCE side with
  `Custom SQL/` when it's a same-element raw-SQL reference).
- **Once a linked input table's column type has materialized wrong (e.g.
  inferred as `text` because its upstream source was erroring), a later PUT
  that fixes the upstream and would change that column to `number` is
  rejected: `"type change is not supported... Drop and re-add the column to
  change its type."`** PUT can't silently retype a column in place. Give the
  WHOLE input-table element a fresh id (forcing Sigma to treat it as a new
  element, re-inferring types clean) rather than trying to patch the
  existing one. This only bites when iterating on a spec that already got
  PUT once with an upstream bug — a correct from-scratch build won't hit it.
- **`controlId` can't contain dots on POST-create.** Must match
  `^[a-zA-Z0-9_-]{1,64}$`. Some UI-built production workbooks GET-back with
  dotted controlIds (`c.relative_month`) — that's legacy/UI-only naming; a
  fresh API-created control can't reuse that convention. Use underscores.
- **`controlType:"slider"` does not exist.** Valid types (confirmed across
  this skill's examples): `list`, `number`, `text`, `text-area`, `date`,
  `segmented`, `checkbox`. For a bare numeric input, use
  `controlType:"number", mode:"="`.
- **A standalone control's live value is NOT bracket-referenceable from an
  arbitrary other element's formula.** There's no verified `[ControlName]`
  formula primitive for "read whatever this slider is currently set to" outside
  of the control's own `filters`/`source` wiring. If you want a value a user
  adjusts to flow into a chart/KPI, route it through an editable **input
  table column** (per `scenario-modeler-pattern.md`), not a bare control.
- **Every element must appear in the layout XML in this environment,
  including pure "backend" tables** that exist only as sources for other
  elements (a base SQL table, a downstream "Book" read-surface). Omitting one
  is a hard validation error (`element 'X' is not placed in layout`) — this
  contradicts guidance from a different Sigma environment that unplaced
  elements "auto-stack." Give every element a real (even tiny/out-of-the-way)
  `<Element>` placement.
- **`<br>` is not an allowed inline tag in a `text` element's `body`.**
  Allowed set: `<u>`, `<sub>`, `<sup>`, `<span>`, `<a>`. Use separate `text`
  elements (or a single line) instead of a manual line break.
- **The `00000000-0000-0000-0000-000000000000` "My Documents root" folderId
  convention is NOT universal.** In one org it resolved to an *archived*
  folder literally named after the org (`"Folder \"demeng\" archived"`).
  Look up the real folder id: `GET /v2/files?typeFilters=folder&search=<name>`
  and use an entry whose `path` is exactly `"My Documents"` (its `parentId`
  is the org's true My-Documents root).
- **Don't conclude "export/live-query is broken for this token" too early —
  first rule out a real spec bug.** Every custom-SQL element on one
  connection, including a trivial `SELECT 1` probe, initially failed export
  with a generic masked 500 (`"Export failed ... with errors"`), which read
  like the known "API service token can't carry interactive OAuth" limit
  seen in other environments. It wasn't that — it was the `[Custom SQL/col]`
  qualification bug above; once fixed, export worked cleanly end-to-end,
  including through the linked input table. A masked 500 on a *trivial*
  probe query is genuinely ambiguous between "this token/connection can't
  run live queries" and "something upstream in this exact spec silently
  errors" — don't commit to either conclusion without independent
  confirmation (e.g. a DIFFERENT, definitely-correct element on the same
  connection exporting fine).
