---
name: sigma-cohort-builder-app
description: >-
  BUILDING BLOCK for interactive Sigma "cohort builder" data apps from code
  (workbooks-as-code, POST/PUT /v2/workbooks/spec) — an agent-driven population
  SEGMENTATION tool: filter a population of individual records (customers, patients,
  employees, students, members, accounts) down to a named, saveable cohort, see live
  size/rate KPIs and distributions, then compare saved cohorts against each other. For
  a full branded company dashboard / POV (which already includes page 1), use
  **sigma-company-dashboard** — it will ASK which of this skill or
  **sigma-input-table-app** (scenario modeling) fits the prospect before building page
  2. Use this DIRECTLY when the deliverable is specifically "build a customer/patient/
  member cohort", "segment a population", "let an agent narrow down a cohort by
  filters", or similar — population segmentation, NOT numeric projection under
  assumptions (that's sigma-input-table-app). Encodes the VERIFIED tabbed-container,
  agent-tool-per-filter, wide-snapshot-save, and grouped-table-sort shapes plus the
  hard limits, so it comes out right the FIRST time.
---

# Sigma Cohort Builder — population segmentation app

Given "let a user (or an agent) filter a population down to a named cohort, save it,
and compare saved cohorts," build this via `POST/PUT /v2/workbooks/spec`. Reverse-
engineered from a real production workbook (demeng org's Marketing Control Center,
"Cohort Construction App" page) and verified end-to-end on staging. Pair with
`sigma-company-dashboard` for the read-only dashboard half, and see
`[[sigma-code-rep-interactivity]]` / `[[agent-cohort-builder-pattern]]` (memory) for
the deeper gotcha history this skill is distilled from.

## When to use this vs. sigma-input-table-app

Ask the user which fits before building — don't guess (some prospects are genuinely
ambiguous, e.g. a retailer could plausibly want either):

- **Cohort Builder (this skill)** — filter a POPULATION of individual records down to
  a named, saveable segment. Fits marketing (campaign segments), healthcare (patient
  risk/diagnosis cohorts), HR (attrition-risk employee groups), education (at-risk
  student groups), SaaS (churn-risk user segments), nonprofit (donor segments).
- **Scenario Modeler (`sigma-input-table-app`)** — project a NUMBER forward under
  adjustable drivers/assumptions. Fits finance, manufacturing, insurance, supply
  chain, energy.
- **Both** is a valid answer — build a dashboard page-1, then one page each.

## The architecture (4 pieces)

1. **A population base table** (`kind:"table"`, custom SQL or `GENERATOR`-based
   synthetic data) with the dimensions worth segmenting by — age/demographic band,
   region, a lifecycle/condition/segment category, a binary flag worth isolating
   ("Is Lapsed" / "Care Gap" / "At Risk"), and a cost/revenue/value measure. An
   independent, UNFILTERED **baseline** copy of the same query (a separate element id)
   gives you an always-on "vs total population" comparison.
2. **One filter `control` per dimension** — ordinary `controlType:"list"` with
   `selectionMode:"multiple"`, each with the standard `filters:[{source:{kind:"table",
   elementId:"population"},columnId}]` binding, PLUS a numeric floor/threshold control
   (`controlType:"number"`) and text controls for the cohort's Name/Description.
3. **ONE AGENT TOOL PER FILTER DIMENSION** — the actual trick. Instead of one tool
   with many params, a separate tiny `action` tool per filter, each just ONE
   `set-control-value` effect with `value:{type:"agent-input",inputName:"..."}`
   (`selectionMode:"add"` on the multi-select ones so the agent can build up a filter
   across turns without wiping prior selections). Add a "set cohort name & description"
   tool (2 effects) and a "save the cohort" tool (see #4).
4. **Save = a real `insert-rows` into an append-only input table** — NOT a UI-only
   Action Sequence (which cannot be authored from code; if a reference workbook's
   "Save" button turns out to be a `{"kind":"sequence","sequenceId":...}` reference,
   that ID isn't defined anywhere in the GET-back spec and can't be replicated —
   inline the real effects instead).

## Activation, not approval

`sigma-input-table-app`'s data-app patterns (scenario/reallocation/commission
modelers) all bundle the Draft → Submitted → Approved/Adjust/Rejected
approval workflow by default, because those are "propose a number → someone
signs off on it" tools. A cohort builder is a different shape — there's
nothing to approve, just a population to push somewhere — so its default
bolt-on is **activation**, not approval:
[`surfaces/cohort_activation.py`](surfaces/cohort_activation.py).

**There is no real outbound integration.** Verified against the live
OpenAPI schema 2026-08-13: a workbook action's effect is one of exactly 12
values (Open URL, Open/Close Overlay, Set/Clear Control, Insert/Update/
Delete Rows, Refresh Element, Navigate, Open Document, Select Tab) — no
`call-api`, and no native toast/notification component either. So
"Activate cohort → sent to Iterable" is **simulated**: an `insert-rows` into
a persistent Activation Log (the truthful, auditable part) plus an
`open-overlay` confirmation modal (the "toast" a demo needs). Say this out
loud to a prospect — the workbook records that an activation was requested,
it does not actually call Iterable's (or Braze's, or Salesforce Marketing
Cloud's) API. Wiring a real send means a Sigma webhook/orchestration layer
downstream of the Activation Log table, outside the workbook spec itself.

**`destinations` has no sensible default — ask which platform(s) the
prospect actually uses** (Iterable, Braze, Salesforce Marketing Cloud,
HubSpot, an ad platform's audience API, ...) the same way you'd ask which
warehouse connection to build against. Confirmation text and the audit log
both reference the destination control live, so it updates correctly if the
prospect uses more than one platform.

## Non-negotiable defaults — build these every time

1. **Snapshot a WIDE set of scalar numbers at Save time — never try to serialize the
   filter criteria as text.** `Text()` on a MULTI-select control returns its full
   OPTIONS list, not the current selection (verified) — so storing "Age Filter" /
   "Region Filter" as `Text([ctrl])` silently captures the wrong (always-the-same)
   data. Instead compute each breakdown as a formula over the LIVE-filtered
   population at Save time (`CountDistinct(If([Population/Dim]="X",[Population/ID],
   Null))`) and store one NUMERIC column per breakdown — cohort size, total value,
   avg value/entity, a rate or two (e.g. flag-rate), and a count per bucket of your
   main demographic dimension. `insert-rows` only ever writes ONE row per action (no
   bulk insert) — this wide-row-per-save design is what makes later analysis possible
   without needing to reconstruct membership.
2. **Analyze a saved cohort with a small cross-join + `Switch` unpivot** — the same
   technique as a scenario modeler's dynamic date-grain/color-by toggle. Cross-join
   the saved-cohorts table × a tiny label table (one row per bucket of your main
   demographic dimension) via `source:{kind:"join",joins:[{left,right,columns:[{left:
   "1",right:"1"}],joinType:"left-outer"}],primarySource:left}`, then a `Switch(
   [Labels/Label],"18-24",[Saved/Age 18-24 Count],...)` formula picks the right stored
   count per label, feeding a real bar chart instead of a flat wide table.
3. **The analysis picker must carry NO `filters` block.** A `list` control's
   `filters:[...]` auto-filters EVERY element sourcing from that table — giving the
   "which saved cohort to analyze" picker a `filters` targeting the saved-cohorts
   table would silently collapse the "all saved cohorts" comparison table/chart down
   to just the one being analyzed. Instead give the picker no `filters` at all (it
   still populates its dropdown via `source`) and match it explicitly in every
   downstream formula: `SumIf(...,[Saved/Cohort Name]=[CohortPick])` / `MaxIf(...)`.
4. **Auto-select the just-saved cohort.** Both Save paths (button AND the agent's
   save tool) fire a SECOND effect right after `insert-rows`: `set-control-value` on
   the analysis picker sourced from the CURRENT Cohort Name control value
   (`{"type":"control","control":"CohortName"}`). No timestamp/Lookup needed — it's
   exactly the name just used.
5. **"Top N" table = a GROUPED table with `sort`, not a plain table's `sort`/`limit`
   (those are silently dropped).** For a "top members/customers by value" preview
   (the stand-in for a repeated-container card view, which isn't buildable from code
   yet), use `groupings:[{id,groupBy:[...all displayed dims...],calculations:[
   valueColId],sort:[{columnId:valueColId,direction:"descending"}]}]` — group by every
   displayed column at the SAME grain as the raw data (no real aggregation, just a
   sort lever) and give it a compact fixed height so only the top rows show without
   scrolling.
6. **`inputMode:"view"` on the saved-cohorts input table** (not the default
   `"edit"`; `"explore"` also works but restricts to explore-or-greater) if you want it editable by non-editor viewers in the PUBLISHED
   workbook — `"edit"` restricts writes to workbook editors in DRAFT mode only, which
   silently breaks a published agent/button Save for anyone else. `inputMode` enum:
   `edit` (editors, draft only) · `explore` (explore-or-greater, published) · `view`
   (everyone, published).

## Layout: a 2-tab tabbed container (verified working shape)

Mirror the reference's real structure: ONE page containing a `tabbed-container` with
exactly 2 tabs — "Cohort Builder" (filters + agent + a row-level detail table + Save/
Reset) and "Visualize" (comparative KPIs + distributions + the saved-cohort analysis
section). Keep a separate "Saved Cohorts" page for comparing many saved cohorts
against each other (a genuinely different function). Verified JSON element:
```json
{"id":"tc","kind":"tabbed-container","tabs":[{"name":"Tab A"},{"name":"Tab B"}],"tabBar":{"alignment":"start"}}
```
Layout XML wraps it with a real `<Tab>` child per tab, matched by POSITION (no name
attribute) — `tabs[]` in the JSON element are LABELS ONLY:
```xml
<TabbedContainer elementId="tc" type="tabbed-container" gridColumn="1 / 25" gridRow="7 / 60">
  <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="..." gridColumn="..." gridRow="..."/>
  </Tab>
  <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="..." gridColumn="..." gridRow="..."/>
  </Tab>
</TabbedContainer>
```

**⚠ GOTCHA — nesting a `<GridContainer>` INSIDE a `<Tab>` scrambles render order.**
Elements can render wildly out of their declared order with large unexplained gaps
(a chart declared LAST rendered FIRST) even though POST/PUT accepts the structure
(masked, as always). Only bare `<LayoutElement>` children of a `<Tab>` are verified to
render in the order declared. **Fix: never wrap a gradient/styled card in a
`GridContainer` inside a Tab** — apply `style.backgroundColor` directly on the leaf
element (a `kpi-chart`'s own `style`) instead of a wrapping container. A `GridContainer`
used for something structurally necessary (e.g. an agent chat panel with a header
above it) still seems fine — the risk is specifically wrapping simple KPI-style cards
that don't need a container at all.

**⚠ GOTCHA — `style.padding` only accepts the literal `"none"` or must be omitted
entirely.** `"padding":"medium"` (or any other value) is rejected — default padding is
implied by omitting the field.

**⚠ GOTCHA — a `list` control has NO code-representable default/initial selected
value.** Both `"defaultValue":{"type":"formula",...}` and `"value":{"type":"formula",
...}` POST "successfully" but are silently dropped on GET-back (the classic
masked-unknown-field trap). There is no way from code to make a picker auto-select
"the most recent row" on first page load — the auto-select-after-Save effect (#4
above) is the real, working substitute; a freshly (re)deployed/never-saved workbook
will show an empty/null analysis section until someone clicks Save once, and that's
expected, not a bug. Add a small hint line near the picker saying so instead of
leaving a bare "null" on screen.

**⚠ GOTCHA — `AvgIf` is NOT a real Sigma formula function.** `SumIf`/`CountDistinct`/
`MaxIf` are the confirmed conditional aggregates; `MaxIf` is the safe substitute for
an average whenever exactly one row is expected to match a condition (`Max` of one
value is trivially that value). Don't assume every `<Agg>If` naming pattern exists.

## Workflow

1. Ask up front: what population is being segmented, what dimensions matter, and
   whether the deliverable is standalone or part of a full company-dashboard build
   (in which case coordinate with `sigma-company-dashboard`'s theming/logo/plugin
   conventions so both pages match).
2. Build a Python generator that emits the spec; POST to create, then always PUT to
   the SAME workbook id on every subsequent edit (re-POSTing creates a duplicate
   workbook with the same name — if that happens, delete the stale one via
   `DELETE /v2/files/{workbookId}`, not `/v2/workbooks/{id}` which 404s).
3. Verify structurally after every PUT: GET the spec back, regex-parse the `<Tab>`
   blocks' `elementId` order and confirm no stray `<GridContainer>` snuck inside one,
   and confirm any `groupings[].sort` you added kept its `direction` value
   (`"ascending"`/`"descending"`, not the abbreviated `"asc"`/`"desc"` — the
   abbreviated form silently vanishes on GET-back).
4. **Render it and look at it.** Sigma renders headlessly — this is how you catch
   overlapping elements, clipped headings, cramped cards and off-page content,
   none of which are visible in the spec:

   ```bash
   # workbook -> PNG (pageId optional; omit for the whole workbook)
   curl -sS -X POST "$SIGMA_BASE_URL/v2/workbooks/$WB/export" \
     -H "Authorization: Bearer $SIGMA_API_TOKEN" -H 'Content-Type: application/json' \
     -d '{"format":{"type":"png"},"pageId":"pg1"}'
   # -> {"queryId": "..."} then poll the SAME download endpoint used for CSV:
   curl -sS "$SIGMA_BASE_URL/v2/query/$QUERY_ID/download" \
     -H "Authorization: Bearer $SIGMA_API_TOKEN" -H 'Accept: */*' -o shot.png
   ```

   Zero bytes means *not ready*, not failed — sleep ~3s and retry. Reports export
   **PDF only** (`{"format":{"type":"pdf","layout":"portrait"}}`); PNG is rejected
   and `layout` is required. A page containing a plugin that fetches externally or
   animates never reaches idle and will time out — render a plugin-free clone of
   that page instead.

## Files
- `examples/build_cohort_builder_reference.py` — the canonical generator: synthetic
  2000-row population, 6 filter controls + name/description, an 8-tool agent (one per
  filter + name-and-description + save), 2-tab tabbed container (Builder/Visualize),
  flat-stat comparative KPI cards, a value-distribution histogram, a demographic-
  distribution bar, a grouped+sorted "Top N" table, and a saved-cohorts analysis
  section (picker + cross-join/Switch unpivot + auto-select-after-save). Swap the
  population's SQL/column names for your domain — the mechanic doesn't change.
