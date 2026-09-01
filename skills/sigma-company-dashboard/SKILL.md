---
name: sigma-company-dashboard
description: >-
  START HERE — the FLAGSHIP end-to-end builder for a branded Sigma workbook /
  dashboard / POV / demo for a NAMED company or prospect, via the workbooks-as-code
  API (POST /v2/workbooks/spec). ONE skill does the whole thing: reshape sample data
  with custom SQL into the company's domain, fetch their REAL logo, a brand-gradient
  header, COMPARATIVE gradient KPI cards, a LIVE CallText AI insight, charts + filters,
  a bespoke domain-specific plugin (hosted on localhost + registered), and a second
  interactive page — a scenario modeler OR a cohort/segmentation builder, whichever
  fits the prospect (this skill asks). USE THIS SKILL — not the building-block skills
  (branded-dashboard-format, sigma-workbook-styling, sigma-workbook-conventions,
  sigma-input-table-app, sigma-cohort-builder-app); it composes them for you — whenever anyone wants to "build /
  make / spin up a Sigma dashboard / workbook / POV / demo for [company or prospect]",
  a "branded dashboard for [company]", "reshape sample data into [industry]", or a
  personalized Sigma demo. Driving a company build from the building blocks instead
  yields a generic dashboard with no fetched logo and no bespoke plugin — use this.
  Encodes the VERIFIED current-API element shapes + masked-error gotchas; always clone
  shapes from a recent GET-back, not from stale docs.
---

# Sigma Company Dashboard — end-to-end builder

Given a company name, produce a polished branded Sigma workbook + a domain plugin,
entirely from code. Proven across multiple retail, CPG, and tech companies.

> ### The spec envelope changed in August 2026 — read this before writing any spec
>
> See **`sigma-workbook-conventions/reference/schema-2026-08-breaking-changes.md`**.
> Short version: everything except `name`/`folderId` lives under **`document{}`**,
> `document.pages[].elements` is **gone** (elements are a flat `document.elements`
> list), the layout tags are now **`<Element>`/`<Container>`** (the old names fail
> with a *masked 500*), and modals/drawers live in **`document.overlays`**.
>
> `examples/build_company_command_center.py` has been migrated and re-verified
> against this schema — clone it, don't reconstruct from memory.
>
> **New things worth putting in a build:** a **drawer** for row-level drill,
> `navigate` buttons between pages, `select-tab` to drive a tabbed container,
> `update-rows`/`delete-rows` on input tables, `successToast` on any action,
> conditional `on-select` triggers, and **`open-document`** to hand off from the
> interactive app to a pixel-perfect **report** — reports are now code-representable
> too, same envelope with `kind: "report"`.
>
> Also: **`POST /spec/verify` is weaker than `create`** — it skips SQL resolution and
> duplicate/dangling-id checks. Always create or update to truly validate.
>
> And **every input table you build gets `inputMode: "view"`**. `inputMode` IS the
> data-entry permission, and the default `"edit"` means *workbook editors only, in
> draft mode* — so a published scenario modeler looks broken to a viewer, and any
> button or agent `insert-rows` / `update-rows` against it silently fails for
> everyone but you. Enum: `edit` (editors, draft only) · `explore` (explore-or-
> greater, published) · **`view` (everyone, published — use this)**.

## The shape of this skill: one name in, whole app out

The user says **"McDonald's"** and that is all they should have to say. You
infer their segments, economics, palette, alerts, persona names and plugin —
asking for those defeats the point. See
**`reference/one-generator-many-prospects.md`** for the derivation table, the
per-industry plugin picker, and what genuinely still needs a human.

Keep company specifics in ONE config dict and the layout universal, so the same
generator retargets with a config edit. Proven across three live builds — a
consumer fintech, a universal bank and a healthcare payer — from one codebase.

## STOP — prompt the user before you build

**This is a hard gate, not a suggestion.** Before writing any spec, call
**`AskUserQuestion`** with the two questions below and wait for real answers.
Do not infer them from the request, do not pick a default and mention it, and do
not start generating "while you wait". Getting either wrong wastes an entire
build.

Ask both in a single `AskUserQuestion` call — two questions, one round trip:

```
Q1 header "Target org"  → Demo org (ours) | Prospect's org
Q2 header "Pages"       → Command center | + Scenario modeler |
                          + Cohort builder | All three
                          (multiSelect: true)
```

The only time you may skip the gate is when the user has *already* stated both
answers explicitly in their message.

### 1. Demo org, or the prospect's org?

The answer decides which feature set is safe to use, because **feature
availability is per-workspace** — a spec that builds fine in our staging org gets
rejected in theirs with `... is not enabled for this workspace`.

| | **Demo org** (ours) | **Prospect org** |
|---|---|---|
| Newest kinds — `waterfall-chart`, `progress`, `repeated-container`, `navigation` | use freely | confirm first, or avoid |
| Drawers / modals (`document.overlays`) | yes | usually yes — verify |
| Page headers / sidebars (`settings.navigation`) | only where enabled | assume **no** |
| Agents + `chat` elements | yes | **often not enabled** — have the no-agent fallback ready |
| Reports as code | staging only today | assume **no** |
| Registered bespoke plugin | yes | needs someone with plugin-registration rights in *their* org |

**How to find out rather than guess:** build the feature-rich version, and if a
create fails with a "not enabled for this workspace" error, drop that feature and
re-post. Keep the two variants in one generator behind a flag (e.g.
`RICH = os.environ.get("DEMO_ORG") == "1"`) so the same script produces both —
don't fork the file.

### 2. Which pages do they want?

> *"Command center, scenario modeler, cohort builder — or a combination?"*

Never assume all three. Each is a real chunk of build time and they suit
different audiences:

- **Command center** — the branded overview. Almost always wanted; this is the
  page that carries the logo, KPI cards, AI insight and the bespoke plugin.
- **Scenario modeler** — project a number forward under adjustable drivers.
  Finance, manufacturing, insurance, supply chain, lending.
- **Cohort / segment builder** — filter a population down to a saveable segment.
  Marketing, healthcare, HR, education, SaaS, consumer fintech.

If they say "all three", confirm it's worth the build time before starting.

---

## The flow (four moves)
1. **Data model** — reshape a sample warehouse table (e.g. Big Buys POS) into the
   company's domain via **custom SQL** so the data "makes sense."
2. **Themed workbook** — company theme (colors, logo, hero), gradient KPI cards,
   a **CallText AI summary**, charts, laid out cleanly. POST via the spec API.
3. **Domain plugin** — a bespoke, *operational* visual a person at that company
   would want (NOT a KPI reskin). Build it single-file (`@sigmacomputing/plugin`
   SDK — see `plugins/cava-daypart/`), then **host + register it in YOUR org**
   (a plugin is never auto-built by a workbook; it must exist in the org first):
   - **Fastest (no hosting — makes "name a company → it builds" work instantly):** a
     ready-hosted example plugin is live at `https://scintillating-madeleine-4aceba.netlify.app`
     (source `examples/plugin-heatmap.html`). Just register THAT url and embed it — no local
     server, works from any org. Build + host your own only when you want a bespoke one.
   - **Host your own**: simplest is local — `python3 -m http.server 8080` inside `plugins/`,
     giving `http://localhost:8080/<folder>/` (Sigma allows the http-localhost iframe
     on your own machine). Or deploy to any static host (Netlify).
   - **Register** (one-time, per org): `python3 scripts/register_plugin.py <BASE_URL>
     <TOKEN> "<name>" "<hosted-url>"` → prints a `pluginId`. (403 → your role can't
     register plugins; an org admin must.) `export DAYPART_PLUGIN_ID=<pluginId>`.
4. **Wire it up** — embed `{kind:"plugin", pluginId, config:{source:{kind:"element",
   elementId}, <var>:"<columnId>"}}` with **your** `pluginId` (the example reads it
   from `DAYPART_PLUGIN_ID`). Bindings are **bare columnId strings**; keys match the
   plugin's `configureEditorPanel` variable names. Bind it to a dedicated data element.

Build the workbook with a **Python generator that emits `spec.json`**, then
`POST` it with curl. See `examples/build_company_command_center.py` — **THE
canonical current-standard generator, clone THIS one** (not `build_cava.py`, which
predates several current conventions incl. the tabbed left-column layout — it's kept
for reference but is not the clone target) — and `plugins/cava-daypart/` for a
matching bespoke plugin example. Read `reference/api-cheatsheet.md` before
authoring — it has every verified shape and gotcha. **Clone shapes from a recent
GET-back spec, never from memory or old docs.**

## Logo & hero (reusable — don't Google, don't hand-draw)
**⚠ You MUST actually run this script and wire its output into `logo_uri`.** Do NOT
write your own SVG wordmark/text-as-logo "as a best try" — that has shipped as a bug
before (a session skipped this step entirely and hardcoded a hand-built font
approximation into `logo_uri`, even though this file explicitly forbids it). If you
find yourself typing a company's name into an SVG `<text>` element as their "logo,"
stop — call `fetch_logo.py` first, every time, no exceptions.

Get the prospect's **real logo** automatically:
```
python3 scripts/fetch_logo.py <domain> --out logo.png     # e.g. acme.com
```
Strategy (verified 2026-07-27, Amazon): (1) scrape the company's OWN site's header/
footer logo (prefers `.svg`, then @2x raster), falling back to apple-touch-icon /
og:image; (2) if the site returns nothing parseable at all — some corporate sites
(confirmed: amazon.com) return an empty `202 Accepted` body to every homepage variant,
an anti-bot measure, not a script bug — fall back to **Wikipedia's own API**: resolve
the company's article, read its infobox `logo =` field from the raw wikitext (NOT the
`pageimages` API, which picks whatever image its own heuristic likes — for a company
article that's often a HQ building photo or exec headshot, not the logo), then resolve
that filename to a direct Commons URL. Still a REAL, official brand asset (public-
domain-in-the-US trademark file), never a redraw. Prints/embeds a data URI either way.

Embed it as an `image` element — and **actually wire it into `logo_uri`; don't fetch it
then leave a hand-drawn placeholder** (a fake logo gets called out instantly).
**To put it white on a dark/gradient header, set `fill="#FFFFFF"` on EVERY `<path>`/
`<polygon>` (and replace existing `fill=`/`fill:` in styles) — NOT just the `<svg>` root.**
Browsers honor root-fill inheritance so it looks white in preview, but **Sigma's renderer
ignores root fill → the logo draws BLACK on the header = invisible** (the "you forgot the logo"
bug). If fetch_logo grabs a decorative asset (e.g. DoorDash), scrape the nav or use
worldvectorlogo. Never ship a crude hand-drawn approximation as "the logo."

**Current header standard:** a clean **brand-color gradient band** (baked SVG background) +
the real white logo (left) + a centered white title/subtitle (baked-white SVG image, since a
native `text` over the gradient renders dark) + a subtle radial glow. NOT a flat light wordmark,
and NOT a photographic hero (both were rejected).

**Hero image:** generate a photorealistic, on-industry BACKGROUND with Gemini
(`gemini-2.5-flash-image`, key in `.env`) — prompt hard for "NO text, NO logos,
NO letters," left third dark for a scrim; resize/crop/scrim with PIL; embed as a
base64 JPEG in the masthead `backgroundImage`. **Never ask an image model to draw
a company's logo — it garbles trademarks every time.** Scene from Gemini, logo
from `fetch_logo.py`.

## KPI, formatting & control defaults (bake these in)
- **Gradient KPI cards MUST be comparative — do not regress this.** Each card's kpi-chart carries
  a **value column AND a comparison column**: `columns:[{value},{prior}]`, `value.color:"#FFFFFF"`,
  `comparisonColumn:{columnId:<prior>}`, `comparison:{display:"delta",colorGood,colorBad}`. That renders
  the Current value big + a **Δ-vs-prior badge** (the comparative metric). Show the Prior value big
  beside it in a second kpi-chart (Current | Prior side-by-side), plus a sparkline. Dropping the
  comparison column = a KPI with no comparative metric (a regression users notice immediately).
- **Titles are NATIVE, never SVG images.** Put the metric title in the kpi-chart's own
  `name:{text,color:"#FFFFFF",fontSize}` — the KPI `name` color IS honored (renders white on the
  gradient). Do NOT bake KPI titles/labels as `data:image/svg+xml` images. (SVG-image text is only
  for a banner title sitting over a gradient header, where there's no native-titled element.)
- Also give cards a **date-axis trend line** (sparkline).
  For "a line chart with the dates," show the x-axis (labels are shown by default; only
  `xAxis.format.labels:"hidden"` hides them) — but **give the date column an explicit
  `format:{"kind":"datetime","formatString":"%b %Y"}`** or the axis renders raw timestamps
  (`2022-07-01 00:00:00`). **The trend line color = `categoricalScheme[0]`**
  — set that to a CONTRASTING color (e.g. white) or the line blends into a same-hue gradient
  card; give category-colored bars their own explicit `color.scheme` so they aren't affected.
- **Uniform card geometry.** Card containers must use `gridTemplateRows:"repeat(N,1fr)"`, NOT
  `"auto"` (auto sizes rows to content, so a longer value or an extra delta row makes one card
  taller/mis-centered). Give the hero value the FULL card width + a shared `value.fontSize`, and
  emit the SAME row skeleton on every card (reserve the delta/subline band even when a card has no
  natural delta). This is the fix for "KPIs look differently sized / unevenly placed."
- **XML-escape any baked-text SVG image + validate before POST.** Titles/labels baked into a
  `data:image/svg+xml` (to get white text on dark cards) break with a raw `&`/`<`/`>` ("Invalid
  image URL"). Escape in the helper and run a pre-POST gate that XML-parses every `data:image/svg+xml`.
- **Never hard-code a number scale.** Use format objects (`$.3~s` = auto K/M/B). In a
  CallText/AI-summary formula, divide by the SAME scale the KPI cards use (or don't divide and
  let `$.3~s` format it) — hard-coding `/1000000000` desyncs the summary ("$10.3B") from the
  cards ("$139M"). **All headline numbers (cards + AI + any modeler baseline) must share one scope,
  or they contradict on screen.** And **ratio KPIs expose fake data** — model a `$/unit` denominator
  from realistic per-segment prices so the ratio is sane by construction, don't let a revenue
  scale-up leak into it.
- **Make toggles DO something via control-driven formulas, not button actions.** A `segmented`
  control's value drives a chart's dimension/color formula, which recomputes reactively:
  dynamic date grain = `Switch([DateGrain],"Quarter",DateTrunc("quarter",[T/Date]),"Week",…,DateTrunc("month",[T/Date]))`
  (⚠ `DateTrunc` arg1 must be a literal — wrap literal DateTruncs in a Switch); dynamic color =
  `Switch([ColorBy],…)`. Give each segmented control a default `value`.
- **Stacked bar + labels:** `color:{by:"category",column,scheme:[…]}` + `stacking:"stacked"` +
  `dataLabel:{labels:"shown",anchor:"middle",fontSize}` (singular `dataLabel`).
- **Interactive counterpart — ASK which pattern fits, don't default to one:** before
  building page 2, ask the user which of two interactive patterns the prospect needs
  (some are genuinely ambiguous — e.g. a retailer could plausibly want either):
  - **`sigma-input-table-app`** — scenario modelers / forecast entry / adjust-via-modal /
    change-log data apps: PROJECT A NUMBER forward under adjustable drivers. Fits finance,
    manufacturing, insurance, supply chain, energy.
  - **`sigma-cohort-builder-app`** — an agent-driven population SEGMENTATION tool: filter
    a population of individual records (customers/patients/employees/students/members)
    down to a named, saveable cohort. Fits marketing, healthcare, HR, education, SaaS.
  "Both" is a valid answer too (one page each, on top of the same dashboard page 1).
  Whichever is chosen still gets the SAME brand theming/logo/header conventions as page 1.

## Data reshape pattern (Snowflake)
Map a sample column onto domain labels deterministically:
```sql
GET(ARRAY_CONSTRUCT('Data Center','Gaming','Automotive','OEM & Other'),
    MOD(ABS(HASH(PRODUCT_FAMILY)),4))::string AS SEGMENT
```
Compute additive metrics in SQL (`QUANTITY*PRICE AS REVENUE`, `QUANTITY*(PRICE-COST) AS MARGIN`);
keep ratios (margin %) as aggregate `Sum(margin)/Sum(revenue)` in the workbook.
Tag periods with a `CASE` on `DATE_TRUNC('month',DATE)` vs `MAX(...)`/`DATEADD('year',-1,...)`
→ `PERIOD_NAME` = 'Current Period' / 'Prior Year'. A base `table` element sources
this: `source:{connectionId, statement:<SQL>, kind:"sql"}`, columns reference
`[Custom SQL/<OUTPUT_COL>]`. Synthetic operational data for a plugin: standalone
`SELECT ... FROM TABLE(GENERATOR(ROWCOUNT=>N))` with `SEQ4()`/`SIN()`.

## Theme & the load-bearing color rule
- Theme lives in top-level `themeOverrides` (`colors.highlight`, `colorOverrides`,
  `categoricalScheme`, `fonts`). Set `categoricalScheme[0]="#FFFFFF"` so in-card
  sparklines are white on gradient cards.
- **Standalone `text` elements are theme-dark; a kpi-chart's `name` is NOT.** A `text`
  element's `style.color` is ignored (renders `themeOverrides.colors.text`), so a colored
  callout / AI box must be a **light-tint container** with default dark text — never a dark box.
  BUT a **kpi-chart `name:{color}` IS honored** — use it for white KPI titles on gradient cards
  (verified). Only a banner title over a gradient HEADER (no native-titled element there) needs a
  baked-white SVG image. Use a **LIGHT canvas + dark/gradient accent cards + header**.
- **A fully-dark canvas breaks Sigma's control dropdowns** (white popup + light
  theme-text = invisible). Keep the canvas light; make hero/KPI-cards/plugin
  panels the dark accents.

## CallText AI summary (live LLM insight)
A `text` element whose `body` is a `{{formula}}` — no `source` needed:
```
{{ Replace(CallText("SNOWFLAKE.CORTEX.COMPLETE","CLAUDE-4-SONNET",
   "You are a <role>. In two sentences summarize: Revenue $" &
   Text(Round(Sum([<Table>/Revenue])/1000000,0)) & "M ...") , '"', "") }}
```
Wrap it in a **light-tint container** (text color is theme-dark → readable).
The connection name + model must be valid for the org (confirm the exact strings).

## Plugin (domain-specific, hosted, embedded LIVE)
Single-file `index.html`, vanilla JS + `<script src="https://unpkg.com/@sigmacomputing/plugin">`,
`client.config.configureEditorPanel([...])`, subscribe to element data, render;
**always include a synthetic fallback** so it previews standalone.
**Always attach a `ResizeObserver` on the render container and redraw on fire** (don't just
draw once on load) — Sigma sizes the panel AFTER your script's first paint, so a load-time-only
measurement (`clientWidth`/`clientHeight`) draws at a stale size: half-width charts, or for any
multi-item layout (gauge clusters, card grids, anything that can wrap to a new row) clipped/
ghost/overlapping elements. This is the #1 cause of a "wonky" freshly-authored plugin — see
`sigma-plugin-development`'s Tips section for the snippet. Preview the plugin standalone at a
couple of viewport widths before wiring it into the workbook. Host on Netlify
(authed CLI): `netlify api createSite --data '{"name":"<unique>","account_slug":"<slug>"}'`
→ `netlify deploy --prod --dir <folder> --site <id>` (ALWAYS pass an explicit
`--site`; empty deploys to the wrong linked site).

**Register from code — no admin UI needed:** `POST /v2/plugins {name,description,url,type:"element"}`
returns a `pluginId` (list with `GET /v2/plugins`). Then embed it live in the spec:
`{kind:"plugin", pluginId, config:{source:{kind:"element",elementId}, <binding>:"<columnId>"}}`.
**Column bindings are BARE columnId strings** — the `{kind:"column",...}` object form is
rejected (masked as `Invalid kind:"plugin"`). Binding keys must match the plugin's
`configureEditorPanel` variable names. Feed it a **dedicated data element** (its own
custom-SQL `table`, e.g. synthetic flight/ops rows) so it visualizes *operational*
data, not the KPI numbers. Ideate a visual matched to the domain (GPU-utilization
heatmap for a chipmaker, pace-to-target pour for a brewer, a campaign flight/Gantt timeline
for an ad agency, activity rings) — never a KPI reskin. This full live-embed is the
proven move: build → host → API-register → wire bound to its own data element.

**Local dev instead of hosting.** For fast iteration (or when you don't want to
deploy), serve the plugin from localhost and register THAT as the url:
`cd <plugin-dir> && python3 -m http.server <port>` → `POST /v2/plugins {url:"http://localhost:<port>/"}`
→ point the workbook element at that pluginId. Edit the file, refresh the workbook,
changes show instantly — no redeploy. Caveats: the `url` is set-once (create a new
registration to change it, PATCH won't); it only renders in a browser that can reach
that localhost while the server runs (not shareable — for dev/personal demos, not
teammates); Sigma is HTTPS loading an HTTP-localhost iframe, which browsers permit as
a secure-context exception (blank panel ⇒ check that first). Keep verified plugin
examples in `plugins/` (flight-timeline Gantt, territory choropleth, claims funnel).

## Command-center layout — left column is a TABBED CONTAINER (current standard)
The left content column (bar/trend chart, the bespoke plugin, and the pivot detail
tables) now goes in ONE `tabbed-container` — NOT stacked vertically. Typical 3 tabs:
"Cost Trend" / "<Plugin concept>" / "Detail Tables" (the two pivots side-by-side in
the last tab). The agent rail sits beside it (unchanged), spanning the SAME full row
range as the tabbed container so both reach the same height. Verified shape:
```json
{"id":"tc","kind":"tabbed-container","tabs":[{"name":"Cost Trend"},{"name":"Plugin"},{"name":"Detail Tables"}],"tabBar":{"alignment":"start"}}
```
```xml
<TabbedContainer elementId="tc" type="tabbed-container" gridColumn="1 / 18" gridRow="20 / 60">
  <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto"><LayoutElement elementId="bar" gridColumn="1 / 25" gridRow="1 / 22"/></Tab>
  <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto"><LayoutElement elementId="plugin" gridColumn="1 / 25" gridRow="1 / 22"/></Tab>
  <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto"><LayoutElement elementId="heat" gridColumn="1 / 13" gridRow="1 / 22"/><LayoutElement elementId="book" gridColumn="13 / 25" gridRow="1 / 22"/></Tab>
</TabbedContainer>
```
`tabs[]` in the JSON element are LABELS ONLY, matched by POSITION to the `<Tab>`
children in the layout XML (no name attribute on `<Tab>`). **⚠ Never nest a
`<GridContainer>` inside a `<Tab>`** — verified to scramble render order (elements can
render out of declared order with large gaps, even though POST/PUT accepts it,
masked). Each tab here only needs bare `<LayoutElement>` children (a chart, a plugin,
or two side-by-side tables), so this risk never comes up on this page. See
`sigma-cohort-builder-app`'s SKILL.md for the full tabbed-container gotcha list
(padding, control default-values, grouped-table sort) if you need a tab elsewhere too.

## Workflow rules
- **Ask before building the plugin** — propose 2–4 domain concepts and let the user pick.
- Reshape realistically (weight the dominant segment) so the data is believable.
- POST with direct curl (a stale local validator may flag `format`, which the API
  actually accepts). Get the URL from `GET /v2/workbooks/{id}`.
- **Render after every POST and look at the image.** `POST /v2/workbooks/{id}/export`
  with `{"format":{"type":"png"}}` then poll `GET /v2/query/{queryId}/download`
  (zero bytes = not ready, retry). Layout defects are invisible in the spec — a
  valid spec with valid SQL can still render clipped, overlapping or off-page.

## Files
- `reference/api-cheatsheet.md` — verified element shapes + every gotcha. READ FIRST.
- `examples/build_company_command_center.py` — **THE canonical current-standard generator** (clone this).
  Gradient header + real white logo + **comparative native-title KPI cards (Current + Δ + Prior + sparkline)**
  + AI insight + Color-By/filters + bar + bespoke plugin full-width + side-by-side pivots + a scenario-modeler
  page with two agents (one with an insert-rows tool). Worked example = DoorDash; swap the marked pieces.
- `examples/build_cava.py` — earlier full generator (still valid; predates the gradient-header/native-title standard).
- `plugins/` — bespoke plugin examples (cava-daypart heatmap, etc.). Register via `scripts/register_plugin.py`.
