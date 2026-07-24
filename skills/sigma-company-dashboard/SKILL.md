---
name: sigma-company-dashboard
description: >-
  START HERE — the FLAGSHIP end-to-end builder for a branded Sigma workbook /
  dashboard / POV / demo for a NAMED company or prospect, via the workbooks-as-code
  API (POST /v2/workbooks/spec). ONE skill does the whole thing: reshape sample data
  with custom SQL into the company's domain, fetch their REAL logo, a brand-gradient
  header, COMPARATIVE gradient KPI cards, a LIVE CallText AI insight, charts + filters,
  a bespoke domain-specific plugin (hosted on localhost + registered), and a
  scenario-modeler page with agents. USE THIS SKILL — not the building-block skills
  (branded-dashboard-format, sigma-workbook-styling, sigma-workbook-conventions,
  sigma-input-table-app); it composes them for you — whenever anyone wants to "build /
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
`POST` it with curl. See `examples/build_cava.py` (the canonical full generator)
and `plugins/cava-daypart/` (the matching bespoke plugin). Read
`reference/api-cheatsheet.md` before authoring — it has every verified shape and
gotcha. **Clone shapes from a recent GET-back spec, never from memory or old docs.**

## Logo & hero (reusable — don't Google, don't hand-draw)
Get the prospect's **real logo** automatically from their own site (their public
brand asset, for a legitimate POV built for that company):
```
python3 scripts/fetch_logo.py <domain> --out logo.png     # e.g. acme.com
```
It scrapes the homepage for the header/footer logo (prefers `.svg`, then @2x
raster), falling back to apple-touch-icon / og:image; prints/embeds a data URI.
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
- **Interactive counterpart:** for scenario modelers / forecast entry / adjust-via-modal /
  change-log data apps, use the **`sigma-input-table-app`** skill (it carries the verified
  input-table, modal, and delta/variance defaults).

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

## Workflow rules
- **Ask before building the plugin** — propose 2–4 domain concepts and let the user pick.
- Reshape realistically (weight the dominant segment) so the data is believable.
- POST with direct curl (a stale local validator may flag `format`, which the API
  actually accepts). Get the URL from `GET /v2/workbooks/{id}`.
- You can't render Sigma from here — after each POST, hand the user the URL and
  iterate from their screenshot.

## Files
- `reference/api-cheatsheet.md` — verified element shapes + every gotcha. READ FIRST.
- `examples/build_company_command_center.py` — **THE canonical current-standard generator** (clone this).
  Gradient header + real white logo + **comparative native-title KPI cards (Current + Δ + Prior + sparkline)**
  + AI insight + Color-By/filters + bar + bespoke plugin full-width + side-by-side pivots + a scenario-modeler
  page with two agents (one with an insert-rows tool). Worked example = DoorDash; swap the marked pieces.
- `examples/build_cava.py` — earlier full generator (still valid; predates the gradient-header/native-title standard).
- `plugins/` — bespoke plugin examples (cava-daypart heatmap, etc.). Register via `scripts/register_plugin.py`.
