# Handoff — the one-name-in, working-data-app-out generator

Paste this whole file into a new session. It is the complete context: what the
asset is, where every file lives, how the generator works, every verified API
fact and gotcha, the running inventory, and what is still broken.

Written 10 Aug 2026 by Claude, for Connor Miller (Sigma SE, cmiller@sigmacomputing.com).

---

## 0. TL;DR for a cold session

You are working on a **Claude skill + Python generator that turns one company
name into a complete, branded, working Sigma data app** — 3 pages, ~200
elements, real segment names, a configured AI agent, cross-filtering, a
write-back scenario modeler, a bespoke plugin, and a pixel-perfect PDF report.

- **Everything is driven by one dict per company** in `scripts/company.py`.
  Adding a prospect = writing one config block. The builder is never edited.
- **Seven companies exist today**: sofi, boa, elevance, mcd, abry, nuvia, delta.
- **Run it**: `COMPANY=delta python3 build_sofi.py create`
- **Nothing is in git.** `~/Desktop/Prospects/SoFi-2026` is not a repo. First
  thing worth doing is `git init`.
- **The purpose is the WOW MOMENT**, not POV building. First call, exec readout,
  bake-off. It is explicitly *not* how you build a POV.
- **The thesis** (credit Khush): Claude alone gives you a *static orphaned
  asset*. Sigma + Claude gives you a *living* one — drillable because it sits on
  semantics, shareable because governance is inherited, iterable because the
  recipient can change it with custom views without coming back to you.

---

## 1. Where everything lives

### The project (NOT in git — fix this)
```
~/Desktop/Prospects/SoFi-2026/
  scripts/
    company.py          1,424 lines — THE ONLY FILE THAT CHANGES PER PROSPECT
    build_sofi.py       1,692 lines — the universal 3-page workbook builder
    build_statement.py    405 lines — the pixel-perfect PDF report builder
    sigmaapi.py           178 lines — auth + REST helpers
    brand.py                       — palette/logo binding, B.apply(cfg)
    shot.py               115 lines — headless PNG export of a workbook
    shot_report.py         82 lines — report -> PDF -> PNG via swift/CoreGraphics
    qa_pg1.py              82 lines — clone-with-plugins-stubbed, renders page 1
    rc_matrix.py          186 lines — repeated-container binding test matrix
    add_notifications.py           — one-off
  sql/                  10 files, ~500 lines — portable SQL, __PRODUCTS__ /
                        __STATES__ substitution points
  assets/               fetched logos + white/navy datauri recolours
  shots/                render QA output (delta4/, nuvia3/, delta-report/ ...)
  specs/                report_id.txt etc.
  deck/                 the SE presentation (see §12)
  HANDOFF.md            this file
```

### The skill (IS in git, has uncommitted changes, nothing pushed)
```
~/Desktop/millersigma/          public GitHub repo, branch main, in sync w/ origin
  skills/
    sigma-company-dashboard/    the entry-point skill
      SKILL.md
      reference/one-generator-many-prospects.md
    sigma-workbook-conventions/
      reference/silent-layout-failures.md
      reference/schema-2026-08-breaking-changes.md
    branded-dashboard-format/ · sigma-app-design/ · sigma-cohort-builder-app/
    sigma-input-table-app/ · sigma-plugin-development/ · sigma-plugin-patterns/
    sigma-embed-portal/ · sigma-use-cases/ · sigma-workbook-styling/
  plugins/                      ~48 authored plugins
  scripts/fetch_logo.py         logo fetcher with Wikipedia fallback
```

### Plugin hosting (localhost only — see §10)
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

**The report** (separate object): a dense two-column pixel-perfect statement,
`document.kind: "report"`, header/footer panels, PDF-only export.

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
| `fee_base` | ancillary revenue, **MONTHLY, in $MM** | ×12 in the SQL — see §9 trap |
| `provision_rate` | credit/refund provision | |
| `delinq_rate` | the risk metric → `driver_risk` | |
| `opex_ratio` | overhead | |
| `units_base` | the count metric → `kpi_units` | **displayed ≈ units_base × 0.043** |
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
trend shock are the same cross-join against the same editable driver grid. That
is the strongest single proof the abstraction is real.

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

### Other tables
- `SEGMENTS[key]` — maps generic band literals (Near Prime/Prime/Super
  Prime/Exceptional, Daily/Weekly/Monthly/Dormant) to domain bands. Applied by
  global string replace across `member_population.sql`, because each literal
  appears in both the assignment CASE and the downstream economics CASEs.
- `VOCAB[key]` — `econ`, `metrics`, `bands`, `cohort_report`. Fed to agents.
- `FOOTPRINTS[key]` — `[(state, share), ...]`, ~15 states. Partial sums are fine.
- `POP[key]` — per-unit economics for the cohort page: `bases` (4 band values in
  DOLLARS), `rev_rate`, `fee_per_product`. **Override this or the cohort KPIs
  read as nonsense** (a dental patient with $1,825 lifetime value).
- `PLUGINS[key]` — `hero`, `hero_label`, `ticker`, optional `hero_table` +
  `hero_config` (see §10).
- `STATEMENTS[key]` — every string in the PDF report (see §11).
- `scale(cfg)` — derives magnitude formatting from `sum(bal_base)`:
  ≥1,000,000 → T; ≥1,000 → B; else M. BofA's trillions once rendered as
  `$1,050.00` under a billions format.

---

## 5. How to run it

```bash
cd ~/Desktop/Prospects/SoFi-2026/scripts

COMPANY=delta python3 build_sofi.py verify        # NEARLY WORTHLESS — see §6
COMPANY=delta python3 build_sofi.py create        # the real validation
COMPANY=delta python3 build_sofi.py update <id>
COMPANY=delta python3 build_sofi.py dump          # print the layout XML

COMPANY=delta python3 build_statement.py create   # the PDF report
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
1. `python3 ~/Desktop/millersigma/scripts/fetch_logo.py <domain> --out x.svg`
   → recolour white by filling the **class fills / paths**, never the `<svg>`
   root (root fill renders BLACK in Sigma). If the mark is a single-colour
   raster, recolour opaque pixels and keep alpha. **Sample the palette from the
   logo; do not guess hexes.** If no logo can be found, say so out loud — do not
   hand-draw a wordmark.
2. Write the config block. Use their **real 10-K segment names** — the single
   biggest credibility lever.
3. Sanity-check scale against public figures BEFORE building. Off by 100× is the
   thing the room notices.
4. Pick the plugin from the industry — never reuse the last one (§10).
5. `create` → run the linter → render → **look at the PNG** → fix.

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

**How the gating works, and why it needed four passes to get right.** The LAYOUT
is the source of truth for placement, so gating deletes whole `<Page>` blocks and
then removes everything left dangling. Dangling references are a hard rejection
at create and they come in **four** flavours, each of which failed separately:

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
page 1 for any company that has both a `STATEMENTS` entry and that id file. The
button label comes from `STATEMENTS[key]["button_label"]`.

### What the skill should ask
Offer these as multi-select, then run the matching commands:
- [ ] Command center *(always)*
- [ ] Financial / scenario modeling → `model`
- [ ] Cohort builder → `cohort`
- [ ] Pixel-perfect PDF → `build_statement.py`

---

## 5c. Cost per piece — measured

**The pieces are not where the money goes.** Running the generator is a
deterministic script: seconds, and effectively zero tokens.

| piece | build wall clock | elements | what must be authored first |
|---|---|---|---|
| Command center | **12s** | 158 | the config block (shared by all pieces) |
| + Financial modeling | **6s** | 173 | nothing extra — `col_*` labels only |
| + Cohort builder | **4s** | 186 | a `POP` override, or the KPIs read as nonsense |
| Pixel-perfect PDF | ~10s | 36 | a `STATEMENTS` block: ~60 lines of copy + 3 SQL generators |

**The real cost is authoring and QA, not building.** Two cost centres:

1. **Config authoring (one-time per company, shared across every piece).**
   Research the segments, derive the economics, fetch and recolour the logo,
   sanity-check scale. This is the bulk of a new company.
2. **One QA cycle per surface** — render the page, *look at the PNG*, fix.
   Measured: **282 seconds** for one render-plus-look cycle. In this session that
   cycle cost **~$7.50**, but 99% of it was cache reads on a very long
   conversation. In a fresh session the same cycle is roughly **$1–3**.

Observed QA cycles per piece on the Delta build:
| piece | QA cycles needed | why |
|---|---|---|
| Command center | 2 | the RASM/CASM mislabelling and the passenger scale |
| Financial modeling | 1 | banking labels leaking into the driver grid |
| Cohort builder | 1 | clean first time once `POP` was set |
| **Pixel-perfect PDF** | **4** | invisible logo, SoFi prose, clipped tables, cents on MQDs |

So: **the PDF is the most expensive surface** despite being the smallest, because
every string is bespoke copy and the layout is absolute-positioned, which clips
silently. The modeler and cohort pages are nearly free once the config exists.

### Whole-build numbers (measured from the session transcript)
| window | wall clock | API calls | tokens | list-price |
|---|---|---|---|---|
| Delta: workbook + plugin + report + all QA | 25m 32s | 114 | 48.4M | ~$85 |
| Delta: the above + surface selection feature | ~44m | 159 | 70.6M | ~$147 |
| the surface-selection feature alone | ~5m | 9 | 4.5M | ~$7.50 |

**85–99% of every one of those figures is cache reads** — re-reading a long
conversation on each call, not doing the work. **A cold session builds a company
for roughly $10–15.** The cost driver is session length, not the asset, which is
the single strongest argument for the click-through direction: a form that
invokes the skill fresh never accumulates 48M cache reads.


---

## 6. Verified API facts (this is the expensive knowledge)

### `verify` passing means nothing
`POST /v2/workbooks/spec/verify` skips SQL resolution, dangling element ids,
duplicate ids, layout placement and workspace feature flags. It has passed while
`create` failed on all of those. **Always create or update to validate.** Five
separate instances this session, most recently `tbl-hero` not placed in layout.

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
Walks the generated XML, reports overlapping siblings and row overflow. **It
caught three real defects in this build.** Wire it into every generate.

### UI-only — exists in the product, not writable from code
All verified on staging 9–10 Aug 2026.
1. **Page headers / sidebars.** `document.settings.navigation` → "workbook
   navigation settings are not enabled for this workspace". Matt deployed it and
   it still did not work for Connor or TJ. Also **a UI-built header does not
   round-trip** — GET returns `settings.navigation: null` and the page comes back
   as bare `<Page/>`, so the next full PUT **wipes Connor's hand-built header**.
   `<Container type="header">` is accepted then silently rewritten to
   `type="grid"`. Matt says there is an XML type called `panel`.
2. **Repeated containers with per-card values — invisible to code in BOTH
   directions.** The write schema has no `name` field (union is `arrangement,
   cardGap, cardSize, cardSpacing, cardStyle, elementGap, elementSpacing,
   filters, id, kind, noDataText, scroll, sort, source, style`), so the
   repeater-qualified `{{[Repeater/Col]}}` reference the docs require cannot be
   written. Setting `name` is silently dropped. AND card children built in the UI
   do not serialize back out. Everything tried: source-table name → "Multiple
   values"; `{{[Repeated container/Col]}}` → Dependency not found; elementId →
   Dependency not found; bare `{{[Col]}}` → writes clean, `Unknown column` at
   query; aggregate wrappers → resolve but not row-scoped. **The product cards in
   every build are six hand-built containers, not a repeater. Say so if asked.**
   (`rc_matrix.py` is the reproducible test matrix.)
3. **API actions.** The effect enum has twelve entries and `call-api` is not one,
   despite public beta in Feb 2026 with 50 connectors on the org.
4. **Input tables editable when published.** `inputMode: "view"` stores,
   validates and round-trips; the runtime still enforces draft-only.
   Reproducible on an API-only workbook: `448eed8a-...`, element `scen2`.

### Other verified facts
- `POST /v2/workbooks/spec`, `PUT /v2/workbooks/{id}/spec`,
  `GET /v2/workbooks/{id}/spec`, `POST /v2/workbooks/spec/verify`
- Reports: `POST /v2/reports/spec`, `document.kind: "report"`,
  `document.panels` for header/footer, PDF-only export with `format.layout`
- **`DELETE /v2/workbooks/{id}` returns 404 on staging. `DELETE /v2/files/{id}`
  works.**
- `image` requires `source: {kind: "url", url}` — the skill docs wrongly show a
  bare `url` (Matt confirmed the doc bug)
- `plugin.style` accepts `backgroundColor` only, and it must be a HEX —
  `"transparent"` is rejected (working as intended; the UI's "None" option is a
  UI/API inconsistency, not a bug)
- `arrangement` on repeated-container rejects a string, enum undocumented
- `DateTrunc(Lower([Grain]), ...)` → Invalid Query. First arg must be a
  date-part literal or a control holding one, so control values must be
  `quarter`/`month`/`week`
- **PNG export never completes for a page with a plugin that fetches externally
  or animates** — the renderer waits for idle forever. Every other page ~30s.
  Hence `qa_pg1.py`.
- `dynamic text` failing to round-trip: reproduced by TJ/Neil, ticketed by Rick
- Legend controls appear in OpenAPI but live verification rejects them (TJ)
- Box charts absent from OpenAPI and rejected (TJ)
- Grouped join legs verified working (TJ)
- OpenAPI source of truth:
  `https://assets.sigmacomputing.com/openapi/public-rest-api/sigma-computing-public-rest-api.json`

### The Aug 2026 breaking changes (Matt Jones)
`document` now has a flat `elements` key instead of nesting them inside pages;
`layout` is now REQUIRED and is the source of truth for nesting;
`LayoutElement` → `Element`; `GridContainer` → `Container`. Three breaking
structural changes shipped in one week.

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
tracked id**. Never delete by name pattern — this is a shared org and a wildcard
delete was blocked by the permission classifier for good reason.

---

## 8. Real bugs the render caught (worth knowing the shape of)

| build | defect | root cause |
|---|---|---|
| Nuvia | revenue $308M > production $177M | `fee_base` is MONTHLY and gets ×12 — mine were ~10× too big |
| Nuvia | "Value per patient" $1,825 | `POP` per-unit economics were retail-banking dollars |
| Nuvia | "$93,300,131" | cohort volume sums DOLLARS; needed a compact format (`$,.3s`) |
| Nuvia | "Line of business" on a dental app | ranked-list labels were hardcoded |
| Delta | contribution = 88% of revenue | **the column called "Net Revenue" is `income − cost + fees`, i.e. a SPREAD.** For a bank that IS the headline; for an airline that's operating *income*. Relabel, don't fudge |
| Delta | 558M passengers vs real ~200M | `units_base` scale (displayed ≈ input × 0.043) |
| Delta | statement logo invisible | `logo_navy()` silently falls back to the WHITE datauri; a light header needs its own recolour |
| Delta | SkyMiles page carried SoFi late-payment warnings | statement prose was not config-driven |
| all | KPI title truncated | "Contribution after overhead ($M)" too long for the card |

### The display-label-vs-column-name trap — hit FOUR times
For input tables and pivots, **the column `name` IS the formula reference key.**
Renaming a label renames the reference. `"Members (K)"` blanket-renamed broke
`LB_COLS`; a cohort chart label used as a column ref gave `Dependency not found:
'member population/risk band'`; renaming the modeler's `Product` column cascaded
through `spivot → assum → book → charts` and broke the build twice.

**Rule: separate the fixed contract from the display label.** Rename in tandem
with every reference (as `col_volume`/`col_growth`/`col_yield`/`col_cost` now
do), or leave the contract alone. `Product` in the modeler chain is deliberately
NOT renamed for this reason.

---

## 9. Plugins

48 authored, served from `~/Library/Application Support/millersigma-plugins/`
by a launchd agent `com.millersigma.plugins` on **localhost:8080**.

### THE BLOCKER
**Plugins are not publicly hosted.** Netlify deploy returns `Forbidden` with
Connor's token (Sigma Computing team blocks it). Consequence: **every workbook
with a plugin looks broken from anyone else's machine.** Options not yet taken:
Connor runs the Netlify deploy himself, or jsDelivr off the public millersigma
repo (needs his explicit go-ahead — public push).

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
Rules learned the hard way:
- **`ResizeObserver` on the stage element, not a window resize listener** —
  Sigma resizes the element, not the page.
- **No infinite animation loop** or headless PNG export never reaches idle.
- Inline SVG needs an explicit `xmlns`.
- Always ship a `synth()` fallback so the plugin looks right unbound.
- Register with `POST /v2/plugins` `{name, url, description, type:"element"}`.

### The hero-plugin generalization (new this session)
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

Ticker and hero are gated **independently** (`NO_TICKER` / `NO_HERO`). They used
to share one flag, so a company with a hero but no sensible ticker silently lost
its hero too.

### Industry picker — never reuse the last one
| industry | ticker | hero |
|---|---|---|
| banking / fintech | live Treasury yields (CORS-open) | balance flywheel |
| healthcare payer | medical cost trend | premium-vs-cost flow, MLR by plan |
| QSR / retail | commodity index | day-part heatmap |
| dental | — | **arch placement map** (angle = arches, thickness = production, fill = goal) |
| airline | — | **ATL connection banks** (arrivals up, departures down, by hour) |
| PE | — | maturity wall |
| oil & gas | crack spread | refinery throughput |

Reusing a lending flywheel on a health insurer is the visible tell that it is a
reskin. It happened once and had to be caught.

---

## 10. Reports as code (pixel-perfect PDF)

`build_statement.py`, 405 lines. `document.kind: "report"`, absolute x/y/w/h
positioning, `<Panel type="header">` / `type="footer"` for global furniture,
`pdata` hidden page for SQL plumbing. Export is PDF-only.

**Now templated** via `STATEMENTS[key]` — every string plus the headline formula
bindings:
```python
"h_formulas": [(source_elementId, formula, "MONEY"|"MONEY0"|"NUM0"), ...]
```
Fixed column contracts (do not rename):
- activity: `Transaction Date, Post Date, Merchant Name or Transaction
  Description, Category, Amount, Points Earned`
- rewards: `Line Order, Description, Points`
- summary: `Line Order, Metric, Value`

`statement_activity_sql` / `rewards_summary_sql` / `account_summary_sql` return
`None` for companies without an override, which falls back to the on-disk SoFi
files. **Only sofi and delta have statements so far.**

Layout gotchas: tables clip their last row silently if the height is short (7
rows needed 252, not 210); an `H1` needs more box than its font size or glyphs
clip and the next element sits on top.

Rendering: macOS has no `pdftoppm`, and `qlmanage` only does page 1, so
`shot_report.py` rasterizes via `swift` + CoreGraphics.
**Usage: `shot_report.py <report-id> <page> <out.png>`.**

---

## 11. Agents

Three per workbook. Config: `instructions`, `dataSources`, `tools`,
`greeting: {mode: "generated"}` (beats hardcoded chips).

Action tools use `{"kind": "effect", "effect": "set-control-value", "control":
"X", "value": {"type": "agent-input", "inputName": "..."}}`.

**Feed the agent the real product names and `VOCAB`** or a health insurer's
copilot offers to explain Credit Card delinquency. This is still broken on
McDonald's — the greeting says "loan book" (see §14).

The cohort-builder pattern (N filters + one action tool per filter + reactive
KPIs) was reverse-engineered from demeng's Marketing Control Center.

---

## 12. The deck (`deck/`)

For a **30-minute internal talk to Sigma SEs**. 9 slides, full spoken script in
the speaker notes, built by `build_deck.py` (python-pptx).

```
deck/build_deck.py                       9 slides, notes on all
deck/one-name-in-working-app-out.pptx    233KB, images embedded — USE THIS
deck/one-name-in-working-app-out-upload.pptx  63KB, NOIMG=1, placeholders
deck/storyboard.html                     visual storyboard, on-slide text vs script
deck/TALK-TRACKS.md                      scripts as editable text (STALE: 16-slide era)
deck/README.md                           index + open items (STALE: pre-8-slide)
deck/img/                                karpathy, enrichlead-launch, enrichlead-attack,
                                         lemkin-day8, masad-response, + strip-* crops
```

**Spine:** title → demo (8 min) → *custom per opportunity is becoming table
stakes* → filmstrip of 4 tweets in date order ("every failure was the same
layer") → Varda quote → **orphaned assets (the thesis)** → a day then minutes +
eight things that break → where the wow moment belongs → where I see this going.

Never cut: the filmstrip, Varda, orphaned assets, the eight limits.

**Cannot be uploaded to Drive by Claude.** The Drive connector takes file bytes
as a base64 tool argument; 233KB → ~318k characters, which exceeds the
per-message output limit. Connor drags the file into Drive (10s) and opens with
Google Slides — notes survive the import.

Brand rules that apply: Advercase cannot embed in Office so headings use
Instrument Serif at +20%; body DM Sans; sentence case; no trailing periods in
headlines; Sigma blue `#1A70F1` is the only accent; never distort an image (set
one dimension, derive the other).

---

## 13. Inventory — live assets on papercranestaging

| company | key | workbook | urlId |
|---|---|---|---|
| SoFi | `sofi` | `8f10c147-da2e-4e45-ba0c-b51934255571` | `4lXyHVZBfr6lRkxC9a3RpD` |
| Bank of America | `boa` | `9558a3ee-723c-43e1-9db1-bc0fd463cb92` | `4xOmETvCxSvk1KhNDcLO6K` |
| Elevance Health | `elevance` | `448eed8a-359e-473a-9358-3c2301a60ab4` | `25mNnBxEdvkJftgP3Eq6TW` |
| McDonald's | `mcd` | `aabb715e-0f22-4051-a1c1-f1353fdebe71` | `5cam967zuIQC40vkdS4Nvb` |
| Abry Partners | `abry` | `669eb91a-b734-4021-9072-4d5d58ae8d12` | `37DKKmfZMs7ccVSKGmaQkq` |
| Nuvia Dental | `nuvia` | `aadec519-10bd-4ff1-bd49-646ceaee2f31` | `5cqv6CBkRwTc77C1nBAJZD` |
| **Delta Air Lines** | `delta` | `e3afbf72-c243-46fa-9af7-a5471ed362db` | `6VDzF7Y8ycQXZcQVtcdZkn` |
| **Marriott International** | `marriott` | `06665b34-0f14-413d-8af5-d11f0156c62c` | `c4JjB6mijx8VWaTnacy6g` |

| report | id | urlId |
|---|---|---|
| SoFi member statement | `2c27aae9-cd72-462a-ac4c-644522409027` | `1ljN0R0HgacaMRBqlKmzNJ` |
| Delta SkyMiles statement | `ca716231-57e1-49a0-8729-ea286d1de7c3` | — |

| plugin | id |
|---|---|
| SoFi/BofA flywheel · rates ticker | `2119eea0-...` · `646412eb-...` |
| Elevance payer-cost-flow · ticker | `dbe77f66-...` · `74d402da-...` |
| McDonald's day-part · commodity ticker | `01759a25-...` · `c28f471a-...` |
| Nuvia arch placement map | `958ccb52-dacc-4115-98b7-e66446e1d539` |
| **Delta ATL connection banks** | `bdb291e8-df93-4262-b109-a635b88fa8c3` |

Abry is deliberately plugin-free — the first build where page 1 rendered
headlessly without stubbing.

**Delta calibration, for reference:** 370,000M ASMs; blended ~11% operating
margin; $6.6B operating income (real ~$6B); 327B ASMs (real ~300B); 200M
passengers (real ~200M); revenue would be ~$59.6B (real ~$61B).

---

## 14. Open items, ranked

### Do first
1. **`git init` the project.** None of this is version controlled.
2. ~~McDonald's agent greeting says "loan book"~~ **FIXED**, by a cold-build
   agent building Marriott (see section 20). Root cause was structural, not a
   McDonald's-specific string: the AI-generated greeting reads the base data
   table's `name` field, which was hardcoded `"Loan Book"` for every company.
   Added `CFG["base_table"]` (defaults to `"Loan Book"` for backward compat)
   and set a real name for all 8 companies. Also fixed in the same pass: the
   AI insight naming a literal "risk rate" instead of the configured driver
   name (needed a new `driver_cost` reference and `%`-escaping for labels that
   contain a literal percent sign, e.g. McDonald's). **Pushed live** to the
   McDonald's workbook (`aabb715e-...`) — the demo note about avoiding its
   agent no longer applies.
3. **Plugin hosting.** Everything is localhost-only.
4. Commit + push the millersigma skill changes (needs Connor's go-ahead —
   public repo).

### Deck
5. Confirm the **Databricks job-description wording** (came via search
   extraction; direct fetch 404'd). It is the frame of slide 3.
6. Talk to **Marit** before quoting her closed-won numbers.
7. Three SE quotes if the field-feedback column is wanted.
8. `TALK-TRACKS.md` and `deck/README.md` are stale (written for 16/25-slide
   versions). Regenerate from the 9-slide build.

### Product asks for Matt Jones
9. `panels` / page headers — not enabled, and UI-built headers do not round-trip.
10. Published-mode input tables (`inputMode: "view"` stores but runtime enforces
    draft-only).
11. Add `name` to the `repeated-container` write schema.

### Generator improvements identified, not built
12. **Emit the demo script with the workbook** — from Chad Morris' framework.
    The generator already knows personas, narrative path, terms and metrics; the
    click path is the missing output.
13. Map legend bands (80–115%) are hardcoded, not derived.
14. `units_base` → displayed-count ratio (~0.043) is empirical, not documented.
    Worth deriving properly.
15. Only sofi + delta have statements; the other five have none.

---

## 15. Economics — measured, not estimated

The Delta build (workbook + plugin + templated report + all QA):
**25 min 32 s wall clock, 114 API calls.**

| | tokens |
|---|---|
| uncached input | 9,382 |
| cache writes | 167,159 |
| **cache reads** | **48,118,451** |
| output | 121,314 |
| total | 48,416,306 |

≈ **$85 at Opus list prices** — but **85% of that is cache reads** ($72), i.e.
re-reading a very long conversation on every call. **Run cold in a fresh
session, this build is roughly $10–15.** The cost driver is session length, not
the asset. Against a fully loaded SE day (~$600–1,000) that is two orders of
magnitude either way.

Measure it yourself: session transcripts at
`~/.claude/projects/-Users-cmiller-Desktop/<session-id>.jsonl` carry per-message
`usage` (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`,
`cache_read_input_tokens`). Sum them over a time window.

---

## 16. People and politics

- **Matt Jones** — owns code rep / the official Sigma workbook skills. Ships
  breaking changes fast and posts updated skills with them. **Has proposed that
  Connor's skill become the basis for Sigma's official opinionated "from
  scratch" workbook skill.** Wants to pull these learnings into first-party
  skills. This is the strongest argument in any budget or roadmap conversation.
- **TJ Wells** — owns public-facing skills (Zalak's call), moved his migration
  skills into the Sigma repo. Working the same API in parallel; his findings and
  Connor's corroborate.
- **Neil Oliver** — being brought into the skills consolidation.
- **Rick** — engineer fixing repeated-container bugs.
- **Chad Morris** — demo-structure framework (personas / narrative / business
  terms / metrics / click path practised in chunks). Offered it for a readme.
  Slide 8 credits him.
- **Khush** — the **orphaned asset** framing. The deck's thesis. Credit by name.
- **Marit Taylor** — closed 3 deals last quarter on custom demos with no POV:
  Coronis $420K, Allvue $183K, PTR $66K. Allvue had done a POV the prior year
  and did not buy.
- **Sean Gross** — prefers a series of custom demos to a formal proof.
- **Derek Dietrich** — the counter-case: denied a POV 15–20× across an 18-month
  MSTR replacement to build a better business case.
- **Arnav Sangal** — Connor's manager, running the Claude budget request.
  `BUDGET-REQUEST.md` is written for him.

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
  mockup BEFORE building in Sigma when the design is uncertain — Connor has
  asked for this explicitly and it prevents guessing.
- Don't rebuild the LinkedIn batch (Snyk, USA Swimming, DoorDash,
  1-800-Flowers, Baseten) or batch 2 (Nike, Ford, Home Depot, eBay, Samsung)
  without being told to.
- Delete workbooks **only by explicit tracked ID**, never by name pattern.
  `papercranestaging` is shared.

---

## 18. What skills actually get invoked — the dependency graph

Three things get confused with each other and shouldn't be: **this generator**,
the **millersigma skill collection** it lives beside, and **Ryan Lauderback's
`ryan-workbook-skill`** at `~/Desktop/ryan-workbook-skill`. Here is the real
relationship.

### `ryan-workbook-skill` — historical lineage only, NOT a runtime dependency

`~/Desktop/ryan-workbook-skill` is Ryan Lauderback's own separate project — a
Claude Code workspace pairing Sigma's official upstream `sigma-agent-skills`
plugin (`sigma-api`, `sigma-data-models`) with a project-local
`sigma-workbook-conventions` skill, plus MCP-first discovery scripts
(`mcp-search.sh`, `mcp-describe.sh`) for resolving prose/URLs/warehouse paths
to Sigma API identifiers, and `scripts/validate-spec.py` for pre-POST static
checks.

**`millersigma`'s own `sigma-workbook-conventions` skill was originally forked
from Ryan's.** `millersigma/README.md` says so directly: *"Workbook/dashboard/
embed skills + scripts — originally `RyanLauderback/ryan-workbook-skill`."*
That is the entire connection. **Nothing in this generator calls into Ryan's
repo at runtime.** `build_sofi.py`, `company.py`, `sigmaapi.py` — none of them
import from or shell out to `ryan-workbook-skill/scripts/*`. This generator
authenticates and posts specs itself via `scripts/sigmaapi.py`, which is a
much thinner, purpose-built version of what Ryan's `_env.sh` / `get-token.sh`
do generically.

Worth knowing about it anyway, because it solves an adjacent problem well:
Ryan's discovery layer (MCP search -> describe -> resolve prose+URLs+warehouse
paths to IDs) is for building **ad hoc** workbooks against a user's own
existing data models by natural-language description. This generator never
needs that, because it never points at a customer's real data model — every
data source is synthetic SQL generated from `company.py`. If a future version
of this skill needs to build against a REAL prospect data model instead of
synthetic data, Ryan's resolver is the right thing to reach for, not something
to reinvent.

### `millersigma` — the actual skill collection this generator is packaged under

`~/Desktop/millersigma` is Connor's public (uncommitted-changes, not-yet-pushed)
GitHub repo, structured as a Claude Code **plugin** bundling 11 skills. This
generator's proper home is a new skill inside it — **`millersigma2`**, built
this session at `~/Desktop/millersigma2` (see §19) — because the *existing*
`sigma-company-dashboard` skill hand-authors a fresh generator script per
company, and this generator's whole point is that it does not.

**The composition graph, as `sigma-company-dashboard`'s own SKILL.md states
it** (verified by reading the frontmatter directly, not inferred):

```
sigma-company-dashboard  (flagship — v1; millersigma2 is v2 of this role)
  composes:
    branded-dashboard-format     — house dashboard FORMAT (header/filter-bar
                                    -> KPI row -> trend -> detail pivot). A
                                    BUILDING BLOCK — its own SKILL.md says
                                    explicitly: do NOT drive a company build
                                    from this skill directly, it yields a
                                    generic dashboard with no fetched logo and
                                    no bespoke plugin.
    sigma-workbook-conventions    — spec mechanics: naming, layout, control
                                    catalog, POST-time gotchas. Forked from
                                    ryan-workbook-skill (see above).
    sigma-workbook-styling        — the visual-craft layer: containers as
                                    design blocks, color/spacing/typography,
                                    what round-trips via spec vs needs UI
                                    finishing.
    sigma-input-table-app         — the scenario-modeler / data-app building
                                    block: input tables, cross-joins, modal
                                    pages, button-effect action sequences.
                                    This generator's page 2 IS this pattern,
                                    templated.
    sigma-cohort-builder-app      — the segmentation building block: N filter
                                    controls + one agent action tool per
                                    filter + reactive KPIs. This generator's
                                    page 3 IS this pattern, templated. (Itself
                                    reverse-engineered from demeng's Marketing
                                    Control Center — see HANDOFF section 11.)

Not composed by the flagship, but related / adjacent in the collection:
    sigma-plugin-development      — REFERENCE for the @sigmacomputing/plugin
                                    SDK (editor-panel config, element-data
                                    subscription, control variables, action
                                    effects, hosting/lifecycle). This is what
                                    every plugin in plugins/ was built against.
    sigma-plugin-patterns          — REFERENCE, proven plugin architecture
                                    recipes (JSON-settings config pattern,
                                    reusable state/config/interaction flows).
    sigma-app-design                — BUILD-methodology design-pack / PRD
                                    generator. Upstream of this generator, not
                                    used by it: you'd use this to SCOPE an app
                                    before generating it, not while generating.
    sigma-use-cases                 — generates a 10-use-case single-slide
                                    PowerPoint for a named prospect. A
                                    different deliverable entirely — sibling,
                                    not a dependency.
    sigma-embed-portal              — scrapes a prospect site + deploys a
                                    branded Netlify embed portal. Unrelated
                                    deliverable; shares nothing with this
                                    generator except "look at the company's
                                    site first."
```

### Where this generator itself sits

**It is not currently packaged as a skill at all.** It has lived as a bare
project directory (`~/Desktop/Prospects/SoFi-2026`, not even in git — see
section 14 item 1) that happens to implement, in one reusable generator, what
`sigma-company-dashboard` + `sigma-input-table-app` + `sigma-cohort-builder-app`
do combined, minus the per-company hand-authoring. **`millersigma2`** (section
19, built this session) is the fix: it packages this generator as
`skills/sigma-company-dashboard-v2/`, positioned explicitly as the successor to
`sigma-company-dashboard` in `millersigma`, composing the same four building
blocks (`branded-dashboard-format`, `sigma-workbook-conventions`,
`sigma-workbook-styling`, plus the input-table and cohort-builder patterns) but
via one generator instead of per-company scripts.

**What a fresh session actually needs to load to run this** — this is the
real dependency list, and it is short:
1. `millersigma2/skills/sigma-company-dashboard-v2/SKILL.md` (entry point)
2. `millersigma2/skills/sigma-company-dashboard-v2/reference/HANDOFF.md` (this
   file — read in full)
3. `company.py` (skim for the nearest existing company to copy)
4. Nothing from `ryan-workbook-skill` or the other 10 millersigma skills is
   read or executed at runtime. They are context for a human deciding whether
   this is the right tool, not code paths this generator calls.

---

## 19. `millersigma2` — the packaged skill, built and committed this session

```
~/Desktop/millersigma2/                    NEW local git repo, NOT pushed anywhere
  .claude-plugin/plugin.json
  README.md
  .gitignore                               excludes *.env, .sigma-portals/, shots/
  skills/sigma-company-dashboard-v2/
    SKILL.md                               entry point -- read reference/HANDOFF.md first
    scripts/                               build_sofi.py, build_statement.py, company.py,
                                           sigmaapi.py, brand.py, shot.py, qa_pg1.py,
                                           shot_report.py, rc_matrix.py, add_notifications.py
    sql/                                   all 11 SQL files
    reference/HANDOFF.md                   a copy of this file
    examples/                              (empty -- the 7 companies in company.py ARE
                                           the examples; nothing separate needed yet)
  plugins/                                 the 8 REGISTERED plugins these 7 companies
                                           actually use (not the full 48-plugin library):
                                           sofi-flywheel, sofi-rates-ticker, payer-cost-flow,
                                           payer-cost-ticker, mcd-daypart,
                                           mcd-commodity-ticker, nuvia-arch-map,
                                           delta-hub-banks
```

**Committed locally. Not pushed to GitHub** — that needs Connor's explicit
go-ahead, same standing rule as pushing to the public `millersigma` repo.

Credentials (`~/.sigma-portals/staging.env`) were never copied in and are
gitignored — the repo has no secrets to leak if it is later pushed.

What did NOT get copied: the `assets/` logos (fetch them fresh per company via
`scripts/fetch_logo.py`, which lives in `millersigma`, not here — this
generator's `company.py` expects `assets/<key>_logo_white.datauri.txt` to
exist locally, generated by that script), `shots/` (build artifacts,
regenerate via `qa_pg1.py`), and `specs/` (per-session report-id files,
regenerate on first `build_statement.py create`).

**Immediate next step for whoever picks this up:** decide whether
`millersigma2` becomes a new top-level skill inside the existing `millersigma`
repo (simplest — one plugin, one install) or stays a sibling repo. The
`SKILL.md` is written to work either way.

---

## 20. The cold-build measurement — what a fresh terminal actually costs

Connor asked directly: do the per-piece cost figures in section 5c hold up in a
genuinely fresh session, the way an SE opens one? They do not, and the honest
correction is important enough to be its own section.

**Section 5c's dollar figures were measured inside a single very long
conversation** that had already built six companies, a 17-slide deck, and
dozens of debugging exchanges. 85-99% of every dollar figure in that section was
**cache reads** — the cost of re-reading that accumulated history on every API
call, not the cost of doing new work. Those figures do not transfer to an SE
opening a fresh terminal, who has no such history to re-read.

To get a real number, an autonomous subagent was spawned with **zero prior
context** — the closest available proxy for a cold terminal — and told to read
`HANDOFF.md`, then build a full 3-page workbook for a brand-new company
(Marriott International) with no plugin and no report, entirely on its own.

### Result: it worked, on the first real attempt

- **Wall clock: 25 minutes 41 seconds. 76 tool calls.**
- `create` succeeded on the first try (`06665b34-0f14-413d-8af5-d11f0156c62c`).
  Six follow-up `update` calls fixed defects found by rendering and looking (one
  `update` was rejected and retried — see below).
- Headline KPIs landed within a few percent of Marriott's real 10-K figures
  without being told the right answer: $84.7B room revenue (real ~$75-85B),
  1,572K rooms (real ~1.6M), $4.08B net fee revenue against gross fees of
  ~$5.0B before direct cost (real gross fee revenues ~$5.2B).
- **It found and fixed a structural bug that had been sitting on this file's
  open-items list, and fixed it for every company, not just its own.** See
  section 19's item 2 close-out. That is the strongest evidence that a cold
  build is not just cheaper than expected — it is genuinely useful independent
  of the specific company it was asked to build.
- It also correctly identified two things as **not fixable in the time it had**
  and said so rather than papering over them: the progress rings render empty
  inside a `<Tab>` (pre-existing on every company, not new), and the
  `units_base` scale factor documented in this file (~0.043×) does not actually
  reconcile — it derived a different empirical formula
  (`displayed ≈ max(units_base) × max(state_share) × 1.157`) that reproduces
  Delta's 200M passengers exactly and used that instead. **That formula is more
  trustworthy than the one in section 4** and should replace it next time
  someone touches `units_base`.

### The logo problem, and what "ask only what you cannot infer" cost

`fetch_logo.py marriott.com` returned a **Bonvoy stock photo** (the site's
`og:image`), not a logo. The Wikipedia infobox fallback also missed, for a
structural reason: it expects `logo = [[File:...]]` and Marriott's actual
article markup is `logo = Marriott International.svg{{!}}class=skin-invert` —
a different infobox template shape. The agent resolved the filename through
the same MediaWiki imageinfo API by hand rather than giving up or hand-drawing
a wordmark, which is exactly the behavior HANDOFF section 5 asks for. Worth
promoting into `fetch_logo.py` itself: a second infobox regex for the
`{{!}}`-pipe template shape.

### What this means for the cost slide

**Do not put a number from section 5c on a slide as "what an SE will pay."**
The number that generalizes is the shape of the work, not a dollar figure from
inside a contaminated session:

- One company, three surfaces, zero prior context: **~26 minutes**, one
  `create`, roughly half a dozen `update` cycles driven by actually looking at
  the renders — not zero, not "AI just gets it right," but a small, bounded,
  self-correcting loop.
- The single most valuable thing a cold session does that a warm one does not:
  it hits the SAME structural bugs everyone hits (hardcoded strings that leak
  through a config-driven system) with FRESH EYES, and it is more likely to
  fix them at the ROOT rather than patch around them, because it has no
  investment in the existing shape of the code. That is a genuine argument for
  running this on new companies even after the generator feels "done" — new
  domains keep finding real bugs.
- If a real dollar figure is wanted for the slide, the only defensible way to
  get one is the same measurement done here: spawn a subagent (or literally
  open a second, empty terminal) with no prior context, give it a company it
  has not built before, and read the number off that run — not off this
  session.

