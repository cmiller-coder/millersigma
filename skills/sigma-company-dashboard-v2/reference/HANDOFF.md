# Handoff — the one-name-in, working-data-app-out generator

Written 10 Aug 2026 by Claude, for Connor Miller (Sigma SE, cmiller@sigmacomputing.com).

---

## 0. TL;DR for a cold session

You are working on a **Claude skill + Python generator that turns one company
name into a complete, branded, working Sigma data app** — 3 pages, ~200
elements, real segment names, a configured AI agent, cross-filtering, a
write-back scenario modeler, a bespoke plugin, and a pixel-perfect PDF report.

- **Everything is driven by one dict per company** in `scripts/company.py`.
  Adding a prospect = writing one config block. The builder is never edited.
- **Eight companies exist today**: sofi, boa, elevance, mcd, abry, nuvia, delta, marriott.
- **Run it**: `COMPANY=delta python3 build_sofi.py create`
- **Nothing is in git.** `~/Desktop/Prospects/SoFi-2026` is not a repo.
- **The purpose is the WOW MOMENT**, not POV building. First call, exec readout,
  bake-off. It is explicitly *not* how you build a POV.
- **The thesis** (credit Khush): Claude alone gives you a *static orphaned
  asset*. Sigma + Claude gives you a *living* one — drillable because it sits on
  semantics, shareable because governance is inherited, iterable because the
  recipient can change it with custom views without coming back to you.
- **For PDF builds**, also read `reference/HANDOFF-report.md`.

---

## 1. Where everything lives

### The project (NOT in git — fix this)
```
~/Desktop/Prospects/SoFi-2026/
  scripts/
    company.py          — THE ONLY FILE THAT CHANGES PER PROSPECT
    build_sofi.py       — the universal 3-page workbook builder
    build_statement.py  — the pixel-perfect PDF report builder
    sigmaapi.py         — auth + REST helpers
    brand.py            — palette/logo binding, B.apply(cfg)
    shot.py             — headless PNG export of a workbook
    shot_report.py      — report -> PDF -> PNG via swift/CoreGraphics
    qa_pg1.py           — clone-with-plugins-stubbed, renders page 1
    rc_matrix.py        — repeated-container binding test matrix
  sql/                  10 files, ~500 lines — portable SQL, __PRODUCTS__ /
                        __STATES__ substitution points
  assets/               fetched logos + white/navy datauri recolours
  shots/                render QA output
  specs/                report_id.txt etc.
```

### The skill
```
~/Desktop/millersigma2/skills/sigma-company-dashboard-v2/
  SKILL.md
  scripts/    (copies of the above)
  sql/
  reference/HANDOFF.md        (this file — workbook builds)
  reference/HANDOFF-report.md (PDF report guide — read only for PDF builds)
```

### Plugin hosting (localhost only — see §9)
```
~/Library/Application Support/millersigma-plugins/   48 plugin dirs
launchd agent: com.millersigma.plugins  ->  http://localhost:8080
```

### Credentials
```
~/.sigma-portals/staging.env    written under umask 077. Also: paperbricks.env,
                                sidecar.env, cte-global.env
```
Org: **papercranestaging** on `https://staging.sigmacomputing.io`,
API `https://api.staging.sigmacomputing.io`.

---

## 2. What the generated app actually contains

Three pages, ~200 elements, 3 overlays (modals), 3 agents.

**Page 1 — Command Center**
- Brand-gradient header with the company's REAL logo, recoloured white, plus
  in-header page navigation
- 4 comparative KPI cards (current vs prior TTM, sparkline, delta chip)
- A live-data ticker plugin strip *or* a native marker strip
- An AI-insight band (LLM-authored narrative, generated at build time)
- Global controls: Period, Product, Date grain (quarter/month/week), Colour by
- A tabbed container with persona tabs (e.g. Executive / Network Operations)
- `region-map` of US states, colour-scaled to plan attainment, **click a state
  and it cross-filters everything**
- Stacked time-series bar chart with dynamic grain + dynamic colour-by
- Ranked performance table by product
- The bespoke hero plugin
- Product "baseball cards" → click → modal → "Model in Planning" drill-through

**Page 2 — Scenario modeler** (`modeler_page`)
- Segmented shock control, Active-scenario dropdown, Submit/Approve/New buttons
- Cross-join chain: `sbase × scen2 → spivot → assum → book`
- `assum` is an **input table with computed columns** — edit a driver, projected
  revenue moves, writes back to the warehouse
- Projected-vs-baseline bar chart, 3 uplift KPIs
- A Scenario Copilot agent with a `set-control-value` action tool

**Page 3 — Cohort builder** (`cohort_page`)
- 6 filter controls + a min/max range + a name box + Save cohort
- 4 reactive cohort KPIs
- Distribution charts, member list, saved cohorts (tabbed)
- A Cohort Copilot with one action tool per filter

**Hidden pages**: `pgData` (all SQL source tables must be placed in layout
somewhere), plus overlay pages for the modals.

---

## 3. The architecture — why it templates

### The split
**Universal (never edited per prospect):** page structure, persona tabs, KPI
band, alert rail, product-card grid, baseball-card modal, cross-join modeler,
agent wiring, cohort builder, the *shape* of the SQL, all layout XML.

**Per-prospect (one dict):** palette, product list with economics, sub-products,
5 alerts, agent instructions, plus 27 `LABELS` keys, `SEGMENTS`, `VOCAB`,
`FOOTPRINTS`, `PLUGINS`, `POP`, `STATEMENTS`.

### ONE BASE TABLE — the most important decision in the build
Every control filters everything **only because every element sources from one
base table** (`tbl-lb`, "loan book"). An earlier version had five separate SQL
tables and cross-filtering silently stopped working. **A control can only filter
a table that has the dimension. Adding a control does not create a join.** If
the map must filter the bars, the base table needs a state column.

### Generate the SQL, don't author it
Hand-written per-prospect SQL is where consistency dies. Every table is
generated from the same product constants so the P&L reconciles by construction:
```
volume×yield − volume×cost + fees − provision − opex  ==  headline KPI
```
If the card grid and the KPI band come from one list they cannot disagree — and
that is exactly what the first analyst in the room checks.

Pure-config files are emitted whole (`product_cards`, `notifications`,
`product_skus`, `geo`, `hub_banks`, and the three statement sources). Files with
real logic (`loan_book`, `scenario_base`, `member_population`) keep
`__PRODUCTS__` / `__STATES__` substitution points.

### Domain language is a SECOND config
The schema templates cleanly; **the words do not.** A payer has no "Finance"
tab. An airline has no "balances". Anything a human reads — tab names, page
names, KPI labels, driver labels, the shock control, column headers, agent
instructions — comes from `LABELS` / `VOCAB`. Get this wrong and the demo reads
as a reskin, which is the exact failure the asset exists to avoid.

---

## 4. `company.py` reference

### The product tuple — 17 positional fields
```python
(name, order, balance_type, bal_base, yield_rate, funding_rate, fee_base,
 provision_rate, delinq_rate, opex_ratio, annual_growth, units_base, phase,
 tagline, rate_label, goal_pct, status)
```
| field | meaning | notes |
|---|---|---|
| `bal_base` | the volume the P&L scales with, in $MM | drives `scale()` |
| `yield_rate` | revenue rate on volume | asset yield / premium PMPM / RASM |
| `funding_rate` | cost rate on volume | cost of funds / medical cost / CASM |
| `fee_base` | ancillary revenue, **MONTHLY, in $MM** | ×12 in the SQL — see §8 trap |
| `provision_rate` | credit/refund provision | |
| `delinq_rate` | the risk metric → `driver_risk` | |
| `opex_ratio` | overhead | |
| `units_base` | the count metric → `kpi_units` | **displayed ≈ max(units_base) × max(state_share) × 1.157** |
| `phase` | seasonal phase offset | 0.0–2.2 |
| `goal_pct` | plan attainment, drives map colour + status | ~0.87–1.09 |

### Cross-industry mapping (proven)
| generic slot | bank | healthcare payer | QSR | dental | PE | airline |
|---|---|---|---|---|---|---|
| product | line of business | benefit plan | market | treatment line | sector | cabin product |
| volume | avg balances | member months | system-wide sales | case value | invested capital | ASMs |
| yield | asset yield | premium PMPM | royalty rate | net collection | EBITDA margin | RASM |
| cost | cost of funds | medical cost PMPM | restaurant opex | implant + lab | cost of debt | CASM |
| **spread** | net interest margin | **medical loss ratio** | franchise margin | contribution | value-creation | unit margin |
| risk | delinquency | denial overturn | below plan | revision rate | covenant trips | cancellations |
| shock | +50bps parallel | medical trend bps | food & paper | implant & lab | EBITDA growth | jet fuel |

**The scenario modeler needs NO change at all** — a rate shock and a medical
trend shock are the same cross-join against the same editable driver grid.

### The 27 `LABELS` keys
```
personas, modeler_page, cohort_page, modeler_title, shock_label,
kpi_revenue, kpi_margin, kpi_volume, kpi_units,
driver_nim, driver_risk, driver_cost, driver_eff,
seg_product, seg_credit, seg_dd, seg_engage, seg_held,
cohort_name, kpi_cohort_size, kpi_cohort_vol, kpi_cohort_rev, kpi_cohort_risk,
col_volume, col_growth, col_yield, col_cost
```
`lab(cfg, key)` falls back to `LABELS["sofi"][key]`, so **any new key must be
added to the sofi entry too** or every other company KeyErrors.

### Other config tables
- `SEGMENTS[key]` — maps generic band literals (Near Prime/Prime/Super
  Prime/Exceptional, Daily/Weekly/Monthly/Dormant) to domain bands. Applied by
  global string replace across `member_population.sql`.
- `VOCAB[key]` — `econ`, `metrics`, `bands`, `cohort_report`. Fed to agents.
- `FOOTPRINTS[key]` — `[(state, share), ...]`, ~15 states. Partial sums are fine.
- `POP[key]` — per-unit economics for the cohort page: `bases` (4 band values in
  DOLLARS), `rev_rate`, `fee_per_product`. **Override this or the cohort KPIs
  read as nonsense** (a dental patient with $1,825 lifetime value).
- `PLUGINS[key]` — `hero`, `hero_label`, `ticker`, optional `hero_table` +
  `hero_config` (see §9).
- `STATEMENTS[key]` — every string in the PDF report (see HANDOFF-report.md).
- `scale(cfg)` — derives magnitude formatting from `sum(bal_base)`:
  ≥1,000,000 → T; ≥1,000 → B; else M. BofA's trillions once rendered as
  `$1,050.00` under a billions format.
- `CFG["base_table"]` — the display name for the base data table (defaults to
  `"Loan Book"` — override for non-banking companies or the agent greeting
  says "loan book").

---

## 5. How to run it

```bash
cd ~/Desktop/Prospects/SoFi-2026/scripts

COMPANY=delta python3 build_sofi.py verify        # NEARLY WORTHLESS — see §6
COMPANY=delta python3 build_sofi.py create        # the real validation
COMPANY=delta python3 build_sofi.py update <id>
COMPANY=delta python3 build_sofi.py dump          # print the layout XML

COMPANY=delta python3 build_statement.py create   # the PDF report (see HANDOFF-report.md)
COMPANY=delta python3 build_statement.py update <report-id>

python3 shot.py workbook <id> ../shots/out        # renders every page EXCEPT p1
WORKBOOK=<id> python3 qa_pg1.py ../shots/out      # page 1, plugins stubbed
python3 shot_report.py <report-id> 1 ../shots/out/p1.png
```

### Adding a company — the actual workflow
The user types **one company name**. Ask only what you cannot infer, via
`AskUserQuestion`, and nothing else:
1. **Which surfaces?** command center only / + modeler / + cohort builder
2. **Demo org or prospect org?** (feature availability differs)
3. **Bespoke plugin?** (it only renders from Connor's machine — say so)

Do **not** ask for products, colours, metrics or KPI names. Inferring those is
the entire value of the skill.

Then:
1. `python3 ~/Desktop/millersigma/scripts/fetch_logo.py <domain> --datauri-file x.txt`
   (use `--datauri-file`, not `--out` — `--out` writes raw binary and the
   builder does `f.read_text().strip()` on the asset, so raw bytes corrupt it)
   → recolour white by filling the **class fills / paths**, never the `<svg>`
   root (root fill renders BLACK in Sigma). If the mark is a single-colour
   raster, recolour opaque pixels and keep alpha. **Sample the palette from the
   logo; do not guess hexes.** If no logo can be found, say so out loud — do not
   hand-draw a wordmark.
2. Write the config block. Use their **real 10-K segment names** — the single
   biggest credibility lever. Set `CFG["base_table"]` to a domain-appropriate
   name (e.g. "Revenue Book", "Member Population", "Fleet").
3. Sanity-check scale against public figures BEFORE building. Off by 100× is the
   thing the room notices.
4. Pick the plugin from the industry — never reuse the last one (§9).
5. `create` → run the linter → render → **look at the PNG** → fix.

---

## 5a. `update` refuses to silently overwrite a hand-edited workbook

**The problem this closes:** Sigma's spec API has no partial update — every
`PUT /v2/workbooks/{id}/spec` sends the COMPLETE representation. If a real
person opens the workbook and hides a column, resizes something, or adds a
filter via the UI, then someone re-runs `build_sofi.py update` afterward
(the normal "reprompt to make a change" workflow), that full-overwrite push
silently erases every UI edit with no warning. Reported as "still seeing
hidden columns" and "my UI changes disappear" — same root cause both times.

**What's actually built (a safety gate, not a merge):** a genuine three-way
merge of arbitrary UI edits into a freshly regenerated spec is a real, risky
engineering problem — Sigma's API gives no diff/patch primitive to build it
on. What's implemented instead: `update` checks whether the workbook changed
since *our own* last push, and refuses if so, rather than overwriting blind.

- `sigmaapi.get_workbook_meta(id)` calls `GET /v2/workbooks/{id}` (no `/spec`)
  — returns `latestVersion` / `updatedAt` / `updatedBy` without paying for the
  full spec body. This is the cheap check.
- Each company's last-known-pushed version is tracked locally in
  `specs/wb_state_<key>.json`.
- `update` compares live `latestVersion` to that local baseline:
  - **Unchanged** → push proceeds normally, baseline advances.
  - **Live version is ahead** (someone edited it since our last push) →
    **refuses**, prints who edited it and when, and requires `FORCE=1` to
    overwrite anyway.
  - **No baseline file yet** (first `update` from this checkout, or state was
    cleared) → same refusal, `FORCE=1` bootstraps the baseline.
- After any successful push, the new `latestVersion` is saved as the baseline.

Verified live against Nuvia's real workbook: no-baseline refusal, `FORCE=1`
bootstrap, a clean re-run with no live changes, and an out-of-band edit
(simulated via a second script re-pushing the same spec) correctly detected
and blocked on the next `update` — all four cases behaved as designed.

**What this does NOT do:** it does not preserve the UI edit and merge it in.
If someone hides a column and you `FORCE=1` past the warning, that hide is
still gone. The gate's entire job is making the overwrite a decision someone
makes on purpose, not something that happens silently.

---

## 5b. Surface selection — building only the pieces you want

```bash
SURFACES=command                    COMPANY=delta python3 build_sofi.py create
SURFACES=command,model              COMPANY=delta python3 build_sofi.py create
SURFACES=command,cohort             COMPANY=delta python3 build_sofi.py create
SURFACES=command,model,cohort       COMPANY=delta python3 build_sofi.py create   # default
COMPANY=delta python3 build_statement.py create        # the pixel-perfect report
```
All four combinations verified with a real `create`. Element counts:
command 158 · +model 173 · +cohort 186 · all 201.

**How the gating works.** The LAYOUT is the source of truth for placement, so
gating deletes whole `<Page>` blocks and then removes everything left dangling.
Dangling references are a hard rejection at create and they come in **four**
flavours, each of which failed separately:

1. elements no longer placed in any layout page
2. action effects that **navigate to a dropped page** — the baseball card's
   "Model in Planning" drill-through. The page id is nested
   (`navigate → target → page`), so a top-level value scan misses it
3. action effects that **set a control that lived on a dropped page**
   (`scenarioSelect`)
4. **dependency closure** — the modeler's data chain spans pg2 (`assum`) and
   pgData (`sbase`/`spivot`/`book`/`scen2`), so dropping the page orphans the
   rest. Elements whose `source.elementId` / `source.from` is gone must go too

The implementation iterates to a fixed point (max 6 passes) rather than trying to
order the fixes by hand, and also drops now-dead buttons, agents whose page is
gone, agent `dataSources` pointing at removed tables, and navigation options
pointing at dropped pages.

**The report is a separate object**, so it is not a `SURFACES` value — it is a
second script invocation. `build_statement.py create` writes
`specs/report_id_<key>.txt`, and `build_sofi.py` shows the statement button on
page 1 for any company that has both a `STATEMENTS` entry and that id file.

### What the skill should ask
Offer these as multi-select, then run the matching commands:
- [ ] Command center *(always)*
- [ ] Financial / scenario modeling → `model`
- [ ] Cohort builder → `cohort`
- [ ] Pixel-perfect PDF → `build_statement.py` (read HANDOFF-report.md first)

---

## 6. Verified API facts (this is the expensive knowledge)

### `verify` passing means nothing
`POST /v2/workbooks/spec/verify` skips SQL resolution, dangling element ids,
duplicate ids, layout placement and workspace feature flags. It has passed while
`create` failed on all of those. **Always create or update to validate.**

### Error messages that mislead
| symptom | actual cause |
|---|---|
| `Invalid kind: "button"` | an unrecognised **field** on the element, not a bad kind |
| masked 500 on PUT | an unrecognised layout XML **tag**, or an unsubstituted `__PLACEHOLDER__` left in the XML |
| `Dependency not found: 'x/y'` | a display label was renamed but a downstream formula still references the old name |
| overlay renders "New Modal" | `header.title` omitted. `""` **crashes** the overlay (Sentry); `" "` gives a blank bar. The header cannot be hidden |
| `Invalid Query: Unknown column` | wrote clean, fails at query time — classic repeated-container symptom |

### THE FOUR SILENT LAYOUT FAILURES — render as *nothing*
No error, no empty box, no console warning. Together these cost more debugging
time than every documented error combined, because the natural assumption is
"my data is wrong" when the data is fine.

1. **A container's internal rows must not exceed the span its parent grants.**
   Rule: `max(child end row) − 1 <= (parent end − parent start)`. Needs ten
   rows, granted five → collapses to zero. **The most expensive one.**
2. **`text` has no `source` field.** Its fields are `body, id, kind, overflow,
   verticalAlign`. A `{{formula}}` inside one resolves only against a **sourced
   data element sharing its container**. That is why the alert cards carry a KPI
   — it is not decoration, it is what makes the text bind.
3. **Overlapping siblings drop silently.** Which one vanishes is not
   predictable. `create` reports `Element collisions found` only sometimes.
4. **`1fr` row tracks collapse inside an auto-height `<Tab>`.** Use
   `gridTemplateRows="auto"` inside tabs.

### The linter — catches #1 and #3 statically
Lives in `millersigma/skills/sigma-workbook-conventions/reference/silent-layout-failures.md`.
Walks the generated XML, reports overlapping siblings and row overflow. Wire it
into every generate.

### UI-only — exists in the product, not writable from code
All verified on staging 9–10 Aug 2026.
1. **Page headers / sidebars.** `document.settings.navigation` → not enabled.
   A UI-built header does not round-trip — GET returns `settings.navigation: null`
   and the next full PUT **wipes the hand-built header**.
   `<Container type="header">` is accepted then silently rewritten to `type="grid"`.
2. **Repeated containers with per-card values — invisible to code in BOTH
   directions.** The write schema has no `name` field, so the repeater-qualified
   `{{[Repeater/Col]}}` reference cannot be written. **The product cards in
   every build are six hand-built containers, not a repeater. Say so if asked.**
3. **API actions.** The effect enum has twelve entries and `call-api` is not one.
4. **Input tables editable when published.** `inputMode: "view"` stores and
   validates; the runtime still enforces draft-only.

### Other verified facts
- `POST /v2/workbooks/spec`, `PUT /v2/workbooks/{id}/spec`,
  `GET /v2/workbooks/{id}/spec`, `POST /v2/workbooks/spec/verify`
- **`DELETE /v2/workbooks/{id}` returns 404 on staging. `DELETE /v2/files/{id}`
  works.**
- `image` requires `source: {kind: "url", url}` — the skill docs wrongly show a
  bare `url` (confirmed doc bug)
- `plugin.style` accepts `backgroundColor` only, and it must be a HEX —
  `"transparent"` is rejected
- `arrangement` on repeated-container rejects a string, enum undocumented
- `DateTrunc(Lower([Grain]), ...)` → Invalid Query. First arg must be a
  date-part literal or a control holding one, so control values must be
  `quarter`/`month`/`week`
- **PNG export never completes for a page with a plugin that fetches externally
  or animates** — the renderer waits for idle forever. Hence `qa_pg1.py`.
- OpenAPI source of truth:
  `https://assets.sigmacomputing.com/openapi/public-rest-api/sigma-computing-public-rest-api.json`

### The Aug 2026 breaking changes (Matt Jones)
`document` now has a flat `elements` key instead of nesting them inside pages;
`layout` is now REQUIRED and is the source of truth for nesting;
`LayoutElement` → `Element`; `GridContainer` → `Container`.

---

## 7. The QA loop — the single most transferable practice

```
generate → lint → push → export PNG → ACTUALLY LOOK AT THE IMAGE → fix
```
Nearly every defect found in this project came from looking at a PNG, not from
reading the spec. Four of the failure modes are invisible in the spec and obvious
in a screenshot. **Skipping the look is how you ship elements that rendered as
nothing while the API said 200.**

`qa_pg1.py` exists because page 1 carries live plugins that never idle: it clones
the live spec into a throwaway workbook, replaces each plugin element with an
inert text tile of the same id, renders that, deletes the clone by **exact
tracked id**. Never delete by name pattern — this is a shared org.

---

## 8. Real bugs the render caught (worth knowing the shape of)

| build | defect | root cause |
|---|---|---|
| Nuvia | revenue $308M > production $177M | `fee_base` is MONTHLY and gets ×12 — mine were ~10× too big |
| Nuvia | "Value per patient" $1,825 | `POP` per-unit economics were retail-banking dollars |
| Nuvia | "$93,300,131" | cohort volume sums DOLLARS; needed a compact format (`$,.3s`) |
| Nuvia | "Line of business" on a dental app | ranked-list labels were hardcoded |
| Delta | contribution = 88% of revenue | **the column called "Net Revenue" is `income − cost + fees`, i.e. a SPREAD.** For an airline that's operating *income*. Relabel, don't fudge |
| Delta | 558M passengers vs real ~200M | `units_base` scale (displayed ≈ max × max(state_share) × 1.157) |
| Delta | statement logo invisible | `logo_navy()` silently falls back to the WHITE datauri; a light header needs its own recolour |
| all | KPI title truncated | "Contribution after overhead ($M)" too long for the card |

### The display-label-vs-column-name trap — hit FOUR times
For input tables and pivots, **the column `name` IS the formula reference key.**
Renaming a label renames the reference. `"Members (K)"` blanket-renamed broke
`LB_COLS`; renaming the modeler's `Product` column cascaded through
`spivot → assum → book → charts` and broke the build twice.

**Rule: separate the fixed contract from the display label.** Rename in tandem
with every reference (as `col_volume`/`col_growth`/`col_yield`/`col_cost` now
do), or leave the contract alone. `Product` in the modeler chain is deliberately
NOT renamed for this reason.


### "Net Revenue" being a SPREAD, not income — hit TWICE (Delta, then NVIDIA)
The generator's base-table column labelled "Net Revenue" is
`income - cost + fees`, i.e. a spread. For a bank that IS the headline metric.
For anything else, treat `yield_rate`/`funding_rate` as a genuine rate pair
computing a real margin -- NOT as "revenue rate" and "zero." **Documenting
this once did not stop it recurring**: NVIDIA's build read this exact warning
and still modeled it wrong on the first pass, because recognizing a COGS/
gross-margin business as "the same trap as Delta's RASM/CASM" required seeing
past the different domain, not just reading the paragraph. Before writing
`products`, ask: is this company's revenue = volume x rate, or does the
generator's income-minus-cost formula actually compute this business's real
spread? If yes to the second, set `funding_rate = 0` and let `yield_rate`
alone equal the true margin (the pattern already used for SoFi Money's
fee-only line).

### `bal_base` -> headline-revenue scaling is undocumented and non-obvious
The KPI compounds `bal_base` through
`(1 + annual_growth/12) ** month_index` over the current-period months (12-23),
summed across every `FOOTPRINTS` state share. Every company built so far used
a modest `annual_growth`, so nobody had to reverse this. NVIDIA's realistic
growth rate overshot the real revenue target by 35-80% until `bal_base` was
back-solved numerically against a standalone Python reproduction of
`loan_book.sql`'s math. **Any future company with an aggressive growth rate
will hit this too** -- budget time to write that reproduction rather than
guessing and re-rendering repeatedly.

### `navy` double-duty as text color AND chart color #3
`navy` is both `TEXT_DARK` (all body/header text) and the 3rd
`CATEGORICAL` chart color. A company whose brand navy is dark enough reads as
a near-black, low-contrast legend swatch. **This is shared-code behavior, not
a per-company bug** -- confirmed across all 9 companies' navy values clustering
in the same darkness class. Do not spend time trying to lighten one company's
navy to fix its chart legend; it will just make that company's text look
off-brand. The real fix belongs in the generator (split text color from
categorical color #1), not in `company.py`.

---

## 9. Plugins

48 authored total; served two ways depending on age.

### Hosting — FIXED for every plugin v2's companies actually use
The old blocker ("plugins are localhost:8080-only, every workbook with a
plugin looks broken from anyone else's machine") is **resolved for the 10
plugins v2 companies reference** (sofi-flywheel, sofi-rates-ticker,
payer-cost-flow, payer-cost-ticker, mcd-daypart, mcd-commodity-ticker,
nuvia-arch-map, delta-hub-banks, alnylam-rnai-pathway, nvidia-gpu-heatmap).
They are now registered against **jsDelivr URLs off the public `millersigma`
repo**:
```
https://cdn.jsdelivr.net/gh/cmiller-coder/millersigma@main/plugins/<folder>/index.html
```
No local server, no launchd agent, works from any machine, permanently — the
repo is already public, this just makes the plugin files reachable by URL.
**Every new plugin should register this way by default** — see the updated
registration line below. The Sigma Plugins API has **no update/PATCH
endpoint** (confirmed empirically, 404), so an already-registered `pluginId`
can never be repointed to a new URL in place — a hosting-URL change always
means registering a *new* `pluginId` and updating every `company.py`
reference to it (`PLUGINS[key]["hero"/"ticker"]`), then re-pushing every
already-built workbook with `build_sofi.py update <id>` so the live spec picks
up the new id. Verify the swap landed by `GET`-ing the live workbook's spec
and checking the plugin element's `pluginId` directly — a successful `update`
response does not by itself prove the new id is what's actually bound.

The remaining 38 plugins (not used by any v2 company) are still
localhost:8080-only, served by the launchd agent
`com.millersigma.plugins` from `~/Library/Application Support/millersigma-plugins/`.
Migrate one to jsDelivr the same way, on demand, the first time a v2 company
needs it.

**Known gap:** `nvidia-gpu-heatmap` is registered on jsDelivr but **not wired
into `PLUGINS["nvidia"]`** — it needs a bespoke `hero_table` SQL source (node
id / utilization % / temp / GPU model), the same pattern as Delta's
`hub_banks.sql`, which doesn't exist yet. Don't wire the `pluginId` in without
also building that table, or the plugin will render with no data.

### Authoring pattern
```html
<script src="https://unpkg.com/@sigmacomputing/plugin"></script>
...
var client = window.sigmaComputing.plugin.client;
client.config.configureEditorPanel([
  {name:'source', type:'element'},
  {name:'x', type:'column', source:'source', allowedTypes:['number'], label:'X'}
]);
client.config.subscribe(function(cfg){
  if (unsub) unsub();
  if (cfg && cfg.source)
    unsub = client.elements.subscribeToElementData(cfg.source, function(d){ ... });
});
```
Rules:
- **`ResizeObserver` on the stage element, not a window resize listener.**
- **No infinite animation loop** or headless PNG export never reaches idle.
- Inline SVG needs an explicit `xmlns`.
- Always ship a `synth()` fallback so the plugin looks right unbound.
- **Register with `POST /v2/plugins` using the jsDelivr URL**, not localhost:
  `{name, url: "https://cdn.jsdelivr.net/gh/cmiller-coder/millersigma@main/plugins/<folder>/index.html", description, type:"element"}`.
  The file must already be pushed to `main` on the public repo before you
  register it — jsDelivr serves whatever's on `main` right now, with its own
  CDN cache (~12hr) on top, so a same-day edit-and-re-register cycle may still
  serve the stale file for a while.

### The hero-plugin generalization
Most hero plugins bind to the product-card table with `product/balance/members/
goal`. Some need a different shape. Declare it in the config:
```python
PLUGINS["delta"] = {
  "hero": "<pluginId>", "hero_label": "ATL CONNECTION BANKS", "ticker": None,
  "hero_table": {"name": "Hub Banks", "file": "hub_banks.sql", "prefix": "h",
                 "cols": ["Hour","Direction","Flights","Seats","Connections"]},
  "hero_config": {"hour":"h0","direction":"h1","flights":"h2","seats":"h3",
                  "connections":"h4"},
}
```
`build_sofi.py` builds `tbl-hero` and substitutes `__HERO_TBL_SLOT__` in the
layout. **Always substitute that placeholder, even to empty string** — an
unreplaced `__PLACEHOLDER__` is a masked 500.

Ticker and hero are gated **independently** (`NO_TICKER` / `NO_HERO`).

### Industry picker — never reuse the last one
| industry | ticker | hero |
|---|---|---|
| banking / fintech | live Treasury yields (CORS-open) | balance flywheel |
| healthcare payer | medical cost trend | premium-vs-cost flow, MLR by plan |
| QSR / retail | commodity index | day-part heatmap |
| dental | — | arch placement map |
| airline | — | ATL connection banks |
| PE | — | maturity wall |
| oil & gas | crack spread | refinery throughput |

Reusing a lending flywheel on a health insurer is the visible tell that it is a
reskin.

---

## 11. Agents

Three per workbook. Config: `instructions`, `dataSources`, `tools`,
`greeting: {mode: "generated"}` (beats hardcoded chips).

Action tools use `{"kind": "effect", "effect": "set-control-value", "control":
"X", "value": {"type": "agent-input", "inputName": "..."}}`.

**Feed the agent the real product names and `VOCAB`, and set `CFG["base_table"]`
to a domain-appropriate name** — or a health insurer's copilot offers to explain
Credit Card delinquency, and the greeting says "loan book".

The cohort-builder pattern (N filters + one action tool per filter + reactive
KPIs) was reverse-engineered from demeng's Marketing Control Center.

---

## 17. Standing conventions (from prior sessions — do not relitigate)

- **Every prospect build = dashboard page + scenario-modeler/data-app page**,
  automatically. Never auto-add a Sankey plugin.
- **Header style**: clean brand-gradient header + the REAL logo fetched from the
  company site, recoloured white by filling the PATHS. Native-title Current/Prior
  KPI cards, never SVG-image titles. Flat wordmark and photo-hero were both
  rejected.
- **eBay is the one deliberate exception** — its multi-colour wordmark stays
  as-is on a white chip.
- **Aesthetics is priority #1.** Follow dashboard best practice. Produce an HTML
  mockup BEFORE building in Sigma when the design is uncertain.
- Don't rebuild the LinkedIn batch (Snyk, USA Swimming, DoorDash,
  1-800-Flowers, Baseten) or batch 2 (Nike, Ford, Home Depot, eBay, Samsung)
  without being told to.
- Delete workbooks **only by explicit tracked ID**, never by name pattern.
  `papercranestaging` is shared.
