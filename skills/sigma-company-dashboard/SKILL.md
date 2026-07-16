---
name: sigma-company-dashboard
description: >-
  Build a complete, on-brand Sigma dashboard for a company end-to-end via the
  workbooks-as-code API (POST /v2/workbooks/spec) — reshape sample data with
  custom SQL, apply the company's theme/logo/hero, composite gradient KPI cards,
  a LIVE CallText AI summary, charts, and a bespoke domain-specific plugin
  (built + hosted on Netlify). Use whenever someone wants to spin up a branded
  Sigma workbook / POV / demo for a NAMED company ("make a Sigma dashboard for
  Apple / NVIDIA / a prospect", "build me a Sigma plugin", "reshape sample data
  into <industry>"), or reproduce this multi-step flow. Encodes the VERIFIED
  current-API element shapes and the many masked-error gotchas so you never
  relearn them — always clone shapes from a recent GET-back, not from stale docs.
---

# Sigma Company Dashboard — end-to-end builder

Given a company name, produce a polished branded Sigma workbook + a domain plugin,
entirely from code. Proven across Best Buy, Budweiser, Apple, NVIDIA.

## The flow (four moves)
1. **Data model** — reshape a sample warehouse table (e.g. Big Buys POS) into the
   company's domain via **custom SQL** so the data "makes sense."
2. **Themed workbook** — company theme (colors, logo, hero), gradient KPI cards,
   a **CallText AI summary**, charts, laid out cleanly. POST via the spec API.
3. **Domain plugin** — a bespoke, *operational* visual a person at that company
   would want (NOT a KPI reskin). Build single-file, host on Netlify, register.
4. **Wire it up** — place the plugin element in the spec once it has a `pluginId`.

Build the workbook with a **Python generator that emits `spec.json`**, then
`POST` it with curl. See `examples/build_template.py` (a full working generator)
and `examples/plugin-heatmap.html` (a full working plugin). Read
`reference/api-cheatsheet.md` before authoring — it has every verified shape and
gotcha. **Clone shapes from a recent GET-back spec, never from memory or old docs.**

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
- **Text color is THEME-driven, not per-element.** A text element's `style.color`
  and the KPI `name` are IGNORED — they render in `themeOverrides.colors.text`.
  So: use a **LIGHT canvas + dark accent cards**, and for any white text on a dark
  surface use a **data-URI SVG image** (KPI titles/labels) or make the container
  light. A colored callout (AI box) = a **light-tint container** with default dark
  text — NEVER a dark box (its text disappears).
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

## Plugin (domain-specific, hosted)
Single-file `index.html`, vanilla JS + `<script src="https://unpkg.com/@sigmacomputing/plugin">`,
`client.config.configureEditorPanel([...])`, subscribe to element data, render;
**always include a synthetic fallback** so it previews standalone. Host on Netlify
(authed CLI): `netlify api createSite --data '{"name":"<unique>","account_slug":"<slug>"}'`
→ `netlify deploy --prod --dir <folder> --site <id>` (ALWAYS pass an explicit
`--site`; empty deploys to the wrong linked site). Register in Sigma (Admin →
Plugins → paste URL) to get a `pluginId`, then the plugin is spec-able:
`{kind:"plugin", pluginId, config:{source:{kind:"element",elementId}, <binding>:{kind:"column",columnId,source}}}`.
Ideate a visual matched to the domain (GPU-utilization heatmap for NVIDIA,
pace-to-target pour for a brewer, activity rings, a 3D asset view) — not a KPI card.

## Workflow rules
- **Ask before building the plugin** — propose 2–4 domain concepts and let the user pick.
- Reshape realistically (weight the dominant segment) so the data is believable.
- POST with direct curl (a stale local validator may flag `format`, which the API
  actually accepts). Get the URL from `GET /v2/workbooks/{id}`.
- You can't render Sigma from here — after each POST, hand the user the URL and
  iterate from their screenshot.

## Files
- `reference/api-cheatsheet.md` — verified element shapes + every gotcha. READ FIRST.
- `examples/build_template.py` — full generator (theme, KPI cards, AI summary, bar, plugin panel, table).
- `examples/plugin-heatmap.html` — full hosted-plugin example.
