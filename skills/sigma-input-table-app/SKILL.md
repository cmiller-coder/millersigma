---
name: sigma-input-table-app
description: >-
  Build interactive Sigma "data apps" from code (workbooks-as-code, beta
  POST /v2/workbooks/spec) — scenario modelers, revenue/demand FORECASTING,
  budgeting/planning, write-back tools, and ADJUSTMENT + change-log apps (users
  edit values via a modal, every change logged). The interactive counterpart to
  sigma-company-dashboard. Use whenever someone wants users to CREATE scenarios,
  ENTER/adjust forecasts, model on top of a baseline, or "update values via a
  modal / add an adjuster / build a planning app". Encodes the VERIFIED input-table,
  linked-input-table, modal, button-action, and control-driven-formula shapes plus
  the hard limits and the non-negotiable DEFAULTS (delta/variance columns,
  comparative gradient KPIs, sensible number formatting, charts parented to the
  linked input table) so it comes out right the FIRST time. Build from scratch —
  never re-POST a UI-built workbook's GET-back.
---

# Sigma Input-Table / Data-App builder

Given "let users model / forecast / adjust / write back data," build a working
interactive app via `POST /v2/workbooks/spec`. Verified end-to-end on staging.
Pair with `[[sigma-code-rep-interactivity]]` (memory) for the raw shape cheatsheet
and `sigma-company-dashboard` for the read-only dashboard half.

## Non-negotiable DEFAULTS — build these every time (don't make me re-ask)

These are the things that were repeatedly *missing* on first builds. Include them by default:

1. **Delta / variance is always present.** The forecast/adjustment grid gets a
   **Δ column** (`[Forecast Revenue] − [Revenue]`, a row-level sibling formula —
   safe in a linked input table) and there's a **Variance chart** (`Sum(forecast) −
   Sum(baseline)` by dimension). "Effective" value is always
   `Coalesce([user entry], [baseline])` so it pre-fills at baseline and adjusts on top.
   - **Seed a LIVE "Base Case" so the modeler isn't dead-empty on load.** The editable
     column starts blank (rows only materialize via the button), so a raw `Coalesce(entry,
     baseline)` makes Projected = Baseline, Uplift = 0%, and the variance chart flat — it
     reads as broken in a demo. Instead add a **hidden formula column** `Base Case` = a
     sensible per-dimension default (e.g. `[Revenue]*Switch([Basin],"Permian",1.16,…,1.05)`),
     make every metric `Coalesce([Your entry],[Base Case])`, and show `Base Case` + `Your
     Forecast` side-by-side in the grid. Now the page shows a real scenario (uplift %, signed
     variance bars) immediately AND a user's typed value still overrides per row. Label it
     "Base Case" so it's honest, not fake actuals.
2. **KPIs are comparative gradient cards — not plain numbers.** Composite cards on
   the ONE brand gradient (white text): a hero value + a colored **Δ-vs-baseline**
   line beneath (e.g. *Projected Revenue* + "▲ $X vs Baseline"), plus *Uplift %* and
   *Baseline*. Use the `gcard()` helper in the exemplar.
3. **Parent the KPIs + charts to the LINKED INPUT TABLE** (`source.elementId` = the
   `forecast` input table), NOT a derived table — so the moment a user edits a cell,
   the KPIs and bars move. (A control can't filter the input table, so if you need a
   scenario *filter*, derive a normal `Detail` table for the control only; keep the
   charts on the input table.)
4. **Format numbers sensibly — never hard-code a scale.** Use format objects
   (`$.3~s` currency = auto K/M/B; `+,.1%` for deltas). **Do NOT write `/1000000000`
   ("billions") in a CallText/AI-summary formula** — it desyncs from the KPI cards
   (you get "$10.3B" next to "$139M"). Divide by the SAME scale the KPIs use (or don't
   divide at all and let `$.3~s` format it), so every number on the page agrees.
5. **Light theme base, dark accents.** A *dark* workbook theme makes input tables and
   dropdowns render white-text-on-white = invisible. Base the theme LIGHT
   (`backgroundCanvas #fff`, dark `text`); apply dark only to the hero/toolbar/gradient
   KPI cards, with baked light-text images on those.

## Aesthetics — match the Sales Forecasting reference (the look, not just the mechanics)

The gold-standard `sales_forecasting_reference.spec.yaml` is deliberately **restrained and
clean** — the polish is ELEMENT-level styling + composition, NOT a heavy custom theme. Copy this:

- **Barely-there theme.** `themeOverrides` is just `{"pageWidth":"large"}` — otherwise Sigma's
  default LIGHT theme and default font. Do NOT drown it in a custom dark theme; a clean light
  canvas + a few restrained accents reads more "enterprise/bespoke" than saturated gradients.
- **Comparison-delta KPIs (this is THE KPI look).** A `kpi-chart` with `name:{text,fontSize:16}`,
  `value:{columnId,fontSize:32}`, and `comparison:{display:"delta",colorGood:"#3bb5b3",
  colorBad:"#ee465c",fontSize:14}`. The delta comes from **period comparison** — include a
  **date/time dimension column** among the KPI's `columns` (alongside the value) and Sigma renders
  the ▲/▼ vs prior period automatically. ⚠ This is why bare `comparison` failed before ("requires
  a comparison column or period comparison") — the fix is the DATE COLUMN, not `comparisonColumn`.
  Teal `#3bb5b3` = good, coral `#ee465c` = bad.
- **Accent palette:** navy **`#1e3558`** for the toolbar/header + borders; subtle grey **`#f7f7f7`**
  for secondary KPI cards; borders use the theme border ref `{"kind":"theme","ref":"colors-border"}`.
- **Pill radius everywhere:** cards/containers use `style:{borderRadius:"pill", borderColor:…,
  borderWidth:1}` (not "round"). Secondary KPIs sit on `{backgroundColor:"#f7f7f7", borderRadius:"pill"}`.
- **Dividers + section text** to structure the page (kind:`divider`); generous whitespace; `pageWidth:"large"`.

**Two aesthetics, pick by context:** this clean light + comparison-delta look is the bar for
**scenario modelers / data apps**. The saturated **gradient-KPI** command-center look (see the
marketing command-center exemplar in `sigma-company-dashboard`) is the bar for **read-only marketing/exec
dashboards**. Don't put a heavy dark gradient theme on an input-table app — it also breaks the grids.

## The verified foundation (the pattern that WORKS)

1. **Base** — a normal `table` (custom SQL), grain = what you model (e.g. product
   line, segment, asset). Keep it RAW; the pivot aggregates. More rows = a richer
   grid, so pick a dimension with real cardinality (≈8–16), not 3–4.
2. **Scenario Names** — an EMPTY `input-table` (`source:{kind:"empty",connectionId}`,
   `inputMode:"edit"`) with a `text` name column + a Status column (`values:[...]` +
   `pills:"color-by-option"`).
3. **Pivot** — `pivot-table`, `source:{kind:"join", joins:[{left:base,right:scenarios,
   columns:[{left:"1",right:"1"}],joinType:"left-outer"}], primarySource:base}`,
   `rowsBy:[<base dim only>]`, `values:[Sum(measure)]`, scenario as a plain column.
4. **Linked input table** (`source:{kind:"linked",from:"pivot"}`) — the modeling grid.
   Columns: the identifier **keys** `{id,key:"<pv base dim>"}` + `{id,key:"<pv scenario>",hidden:true}`,
   the **baseline pulled as a source-column key** `{id,key:"<pv measure>"}` (⚠ NOT a
   formula — a formula re-aggregates → "multiple values" and nulls the keys), an
   editable `{id,type:"number",name:"Forecast Revenue"}`, the **Δ formula column**, and
   optional Comments. Add `conditionalFormats` `IsNotNull`/`IsNull` to tint entered vs empty cells.
5. **Detail** (only if you need a scenario filter) — a normal `table`
   `source:{elementId:"forecast",kind:"table"}` the list control can filter.
6. **App layer** — comparative gradient KPIs + Baseline-vs-Forecast bar (grouped,
   `stacking:"none"`) + Variance bar, all sourced from `forecast`; a **Create-scenario
   modal**; optionally **Submit** → append to a status-log input table.

**Create-scenario button sequence** (the money move):
`insert-rows(scenarios,{name:control,status:"Draft"}) → set-control-value(scenarioSelect = name) → clear-control(name) → close-overlay`.

## Adjustments + change-log data app (modal-driven value edits)

For "let users adjust a value via a modal, with a change log" (Sigma QuickStart pattern):

- **Picker** — a single-select `list` control on a NORMAL aggregate table (custom-SQL
  `GROUP BY`), NOT a pivot (controls can't source a pivot). Replaces the QuickStart's
  "click a cell" (no cell-select trigger exists in code-rep).
- **Adjust button** — `set-control-value` seeds the modal controls (a_line ← picker,
  a_current ← `Text(Lookup([Planning/Revenue],[picker],[Planning/Product]))`, a_method ←
  "Absolute"), `clear-control(a_adjustment)`, then **`open-overlay` LAST**.
- **Modal page** (`type:"modal"`) — controls: `a_line`/`a_current`/`a_adjustment` as
  **`text`** controls (⚠ a number *parameter* control is rejected by the API; use text +
  `Number([ctrl])` in formulas), `a_method` as **`segmented`** (Absolute/Percent/Relative),
  a preview text, and Save/Cancel buttons. `modal.header.showCloseIcon` must be `"hidden"`.
- **Save** — `insert-rows` into an append-only **Adjustment Log** input table; values may be
  **formulas**: `ADJUSTED_VALUE = Switch([a_method],"Percent",Number([a_current])*(1+Number([a_adjustment])/100),"Absolute",Number([a_adjustment]),"Relative",Number([a_current])+Number([a_adjustment]))`,
  `KEY = MD5([a_line])`. Log columns: editable PRODUCT_LINE/ORIGINAL_VALUE/ADJUSTED_VALUE/METHOD,
  a Δ formula column, and **system columns `{id:"CREATED_AT"}` + `{id:"CREATED_BY"}`** (auto
  user+timestamp — do NOT pass them in the insert values). Then clear controls + close.
- **Baseline override** (read side) — `Coalesce(Lookup([Latest/Adjusted Value], MD5([Planning/Product]), [Latest/Key]), [Planning/Revenue])`. `update-rows` is NOT supported — append-only + derive latest-per-key.

## Control-driven dynamic charts (make toggles actually DO something)

Don't wire toggles with button actions — make the chart's dimension/color a FORMULA
that references the control by controlId; it recomputes reactively:
- **Dynamic date grain**: `Switch([DateGrain],"Quarter",DateTrunc("quarter",[T/Date]),
  "Week",DateTrunc("week",[T/Date]),"Day",DateTrunc("day",[T/Date]),DateTrunc("month",[T/Date]))`
  — ⚠ `DateTrunc` arg 1 must be a **literal** date-part; a dynamic `DateTrunc(Lower([ctrl]),…)`
  errors "Argument 1 invalid", so wrap literal DateTruncs in a `Switch`.
- **Dynamic color/stack**: `Switch([ColorBy],"Product Line",[T/Product Line],"Network",[T/Network],…)`.
- Give each `segmented` control a default `value` so the formula isn't null.

## Verified shape gotchas (don't relearn these)

- **`Invalid kind:"x"` is MASKED** — fires for unknown kind AND a known kind with a wrong
  shape/extra key. Never conclude "unsupported" from it; cross-check the OpenAPI.
- **Controls CANNOT filter/source input tables or pivots** (`Dependency not found`). Use a
  normal derived/aggregate table as the control's source/target.
- **Silently dropped keys** (POST succeeds, GET shows the field null): bar value labels are
  `dataLabel:{labels:"shown",anchor:"end|middle",fontSize}` (singular; `dataLabels:{visibility}`
  is dropped). Color a bar by a dimension with `color:{by:"category",column:<colId>,scheme:[…]}`
  + `stacking:"stacked"`. `line-chart` rejects `color:{by:"value"}` — its series color = theme
  `categoricalScheme[0]` (set that to a CONTRASTING color so a KPI sparkline doesn't blend into
  a same-hue gradient card; give any category-colored bar its own explicit scheme).
- **Element-level `categoricalScheme` on a chart is DROPPED (masked).** So a **multi-measure**
  bar/line (2+ `yAxis.columnIds`) has NO per-element color lever — every series inherits the
  THEME `categoricalScheme` in order. If `categoricalScheme[0]="#FFFFFF"` (which you set for white
  KPI sparklines), the FIRST measure series renders **white-on-white = invisible** (looks like a
  missing series). The ONLY color control that survives is `color:{by:"category",column,scheme}`.
  Two fixes: **(a) single solid color on a single-measure bar** → add a constant-string category
  column (`formula:'"Label"'`) and `color:{by:"category",column:<it>,scheme:["#hex"]}`.
  **(b) a real 2-series "A vs B" grouped bar** → don't use two measures; go **long-format** via a
  cross-join of the (linked input) table × a tiny 2-row label table (`VALUES ('Baseline',1),
  ('Projected',2)`), a `Value` formula that switches on the label, then bar-chart with ONE measure
  + `color:{by:"category",column:<seriesLabel>,scheme:["#gray","#accent"]}` + `stacking:"none"`.
  (Verified 2026-07-21 on an E&P scenario-modeler build.)
- **Date/datetime axis columns need an explicit format or they render RAW timestamps** — a KPI
  sparkline or bar over a `DateTrunc`/month column shows `2022-07-01 00:00:00` on the axis unless
  the column carries `format:{"kind":"datetime","formatString":"%b %Y"}` (`%b %d, %Y` if the grain
  varies). Add it to the axis column, not just `xAxis.format`.
- **Baked-white-text SVG images MUST be XML-escaped, and gridTemplateRows must be EXPLICIT.**
  Two card bugs that cost a rebuild each (fixed 2026-07-21):
  - *"Invalid image URL"*: the `timg()` helper (bakes white label/title text into a `data:image/svg+xml`
    URI, since text color is theme-driven) interpolates text raw. A title with a bare `&` (e.g.
    *"Production & Financial Command Center"*) makes the SVG **malformed XML** → the whole image fails.
    Escape inside the helper: `txt.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')`.
    Add a **pre-POST QA gate** that base64-decodes every `data:image/svg+xml` in the spec and
    `xml.dom.minidom.parseString`s it; abort if any fails. (base64-encoding does NOT make bad XML valid.)
  - *"differently sized" / "unevenly placed" KPI cards*: card containers with
    `gridTemplateRows="auto"` size rows to CONTENT, so a card with a longer value string or an
    extra (delta) row lays out differently from its siblings inside an identically-sized box. Fix =
    **one unified card model**: `gridTemplateRows="repeat(N, 1fr)"` (equal fractions), give the hero
    value the FULL card width + a shared `value.fontSize`, and emit the **IDENTICAL row skeleton on
    every card** (reserve the delta/subline band even when blank — e.g. a `CountDistinct`/context stat
    on the card that has no natural delta) so all values center at the same y.
- **Every headline number on the page must share ONE scope, or they contradict on screen.** KPI
  cards, the CallText AI insight, AND the scenario baseline should all be the same scope/scale
  (e.g. portfolio TOTAL). A single-period card ($1.01B) next to an all-period AI summary ($71.9B) reads
  as broken. And **ratio KPIs betray fake data**: a blanket `*7` revenue scale-up leaks straight into a
  `$/unit` ratio ($3,400/BOE — absurd). Model the denominator from realistic per-segment unit prices
  (`Production = Revenue / GET([68,32,40], streamIdx)`) so the ratio is sane BY CONSTRUCTION (~$42/BOE).
- **Data-export caps at 1,000,000 rows** — for TOTALS on a bigger table, extrapolate; **RATIOS are
  truncation-immune** (verify $/unit, %, mix there). KPI-chart sub-elements are NOT individually
  exportable (404) — export the SOURCE table and aggregate to check card values.
- **GROUPED-TABLE FAN-OUT (the subtle one — cost multiple rebuilds).** A `kind:table` groups via
  `groupings:[{id,groupBy:[dimId],calculations:[measureIds]}]` — **NOT `rowsBy`** (that's pivot-only;
  on a plain table it's ignored and the table keeps its source grain). Worse: any element that
  SOURCES a grouped table (a chart, a KPI, a cross-join) **re-reads it at the PRE-grouping source
  grain**, so a `Sum` over it multiplies by rows-per-group (e.g. 8 basins × 4 driver-rows → every
  total came out 4×). Grouping is display-only; it does not create a physical grain downstream. **Fix:**
  compute per-entity metrics **row-level over a PHYSICAL base at the target grain** (a SQL `VALUES`
  table — e.g. one wide row per basin — with NO `groupings`); then charts/KPIs/cross-joins that
  source it read the right grain. Keep any long editable grid (entity×driver) for DISPLAY only, off
  the math path.
- **Governed multi-field modal entry (click a row-ish → pop-up form → Save), code-POST reliable.**
  There is no live table-cell click in code (glyph columns render but are inert). Use: a picker
  **`list` control** (sourced from a NORMAL SQL table, give it a default `value`) + an **Edit button**
  whose effects `set-control-value` each field's TEXT control via
  `{type:formula, formula:'Text(MaxIf([grid/Effective],[grid/Key]=[picker] And [grid/Field]="X"))'}`,
  then **`open-overlay` LAST**. The modal (a `type:modal` page) holds one **TEXT** control per field
  (unbound NUMBER params are rejected). **Save** does `insert-rows` per field into an append-only log
  (`{type:formula, formula:'Number([ctrl])'}`), then `clear-control` per field, then `close-overlay`
  LAST. Apply overrides downstream with **`Lookup` + `Coalesce`**: `effective =
  Coalesce(Lookup([Latest/Value],[Latest/Key],[Base/Key],[Latest/Field],"X"), [base case])`, where
  `Latest` is a grouped table taking the newest per key (`MaxIf([Value],[Created At]=Max([Created At]))`).
  Never `update-rows` (UI-only). Empty log → Lookup null → base case shows (alive on load).
- **Comparison-delta KPI vs a baseline sibling WORKS via `comparisonColumn`.** `kpi-chart` with two
  `columns` (value + a baseline measure), `comparison:{display:"delta",colorGood,colorBad,fontSize}`,
  and `comparisonColumn:{columnId:<baseline colId>}` renders the clean ▲/▼ auto-delta — **no date
  column needed** (a date column is only for *period* comparison). This is the reference app's KPI look.
- **Dashed prior-year KPI line** needs a **`combo-chart`** (line-chart only has a global
  `lineAreaStyle`): `yAxis.columnIds:[{columnId,type:"line"}]` + `seriesLineAreaStyle:{"<col>":{line:{style:"dashed",width}}}`.
- **`refresh-element` effect shape is unverified — omit it** (derived tables recompute on reload).
- **Can't seed input-table rows from code** — rows only insert via the in-UI button. A fresh app
  is empty until the user clicks Create/Adjust once; say this, don't treat empty-on-load as a bug.
- **Do NOT re-POST a UI-built workbook's GET-back** — build from these shapes instead.

## Workflow

1. Ask up front: base metric + grain, the dimension users create (scenario/forecast/budget),
   whether there's an adjust-via-modal step, and an approval/submit step.
2. Assets: real logo via `scripts/fetch_logo.py <domain>`; hero via Gemini (key at
   `~/Desktop/millersigma/gemini.key` — NOT /tmp, which gets pruned) or a bespoke SVG.
3. Build a Python generator that emits `spec.json`; POST via curl; iterate on the
   `pages[N].elements[M]` index in masked errors.
4. **QA without eyes on it:** data-export every element
   (`POST /v2/workbooks/{id}/export {elementId,format:{type:"csv"}}` → poll
   `GET /v2/query/{qid}/download`) to confirm each resolves (no Invalid Query) and numbers are
   sane. This catches the class of bugs you can't see in a headless build.
5. The one thing you can't POST-verify is row materialization — hand the user the URL and have
   them click Create/Adjust once.

## Exemplars

**⭐ GOLD STANDARD — study & clone shapes from this real, polished app:**
`examples/sales_forecasting_reference.spec.yaml` — a GET-back of "Sigma Apps – Sales
Forecasting" (a Sigma sample app on staging), the canonical scenario-modeling app and the quality bar.
It's a full **workflow app**, not just a grid. Clone its shapes but **build your own from
scratch** (never re-POST a GET-back — it won't round-trip; e.g. its `update-rows` effects are
UI-built and update-rows is UI-only, not reliable via code — use append-only + derive latest).
What to lift:
- **Rich forecast input table** ("Target & Forecast"): editable Target + Stat Forecast; computed
  `Actuals` (Lookup to the warehouse table), an `Actuals/Forecast = If(IsNull([Stat Forecast]),
  "Actuals","Forecast")` classifier, **`Var = Coalesce([Actuals],[Stat Forecast]) − [Target]`**
  (the delta), and `SumIf` period roll-ups (YTD revenue/target, Remainder target/forecast,
  Full-year target). This is the depth a good modeler has.
- **Scenario-list input table** with metadata + **system columns** (`{id:"ID"}`, `{id:"UPDATED_AT"}`)
  and a **Submit → Approve lifecycle** (Submission Status, Submitted By/On, Approval Status,
  Approved By/On, Comments).
- **Linked input tables** for entry AND approvals via `Lookup(...)` joins back to the scenario
  list, with glyph action columns (`"🔎"` Details, `"Approve"`).
- **Modal-driven workflow with GUARD modals**: Create Forecast · Forecast Already Exists · Submit
  Forecast · Fcst Approval · Only Managers Can Approve · Forecast is approved. Button chains like
  `insert-rows → close-overlay → set-control-value → open-overlay` and validation-gate modals.
- **Onboarding / white-label** (a Customization input table: Company, Logo + Get-Started button)
  and a polished **Summary** page with comparative KPI cards + a trend line.

**Build-from-code generators (reproducible starting points):**
- `examples/build_scenario_modeler_min.py` — minimal verified modeler (foundation + comparative
  gradient KPIs + Baseline-vs-Forecast bar + Δ + Create modal).
- `examples/build_scenario_app.py` — earlier reference generator.

**Quality bar = the Sales Forecasting reference.** A bare "3 KPIs + a bar + an input table" is
NOT enough — include delta/variance columns, `SumIf` period roll-ups, the create→submit(→approve)
modal workflow, and a Summary KPI view.
