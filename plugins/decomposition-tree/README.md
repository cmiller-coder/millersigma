# Decomposition Tree — Sigma plugin

A generic metric decomposition tree: a Total box at top, one child box per
category below it, each showing its value, variance vs. a comparison column,
and two configurable corner metrics (e.g. a Loyalty/Non-Loyalty split).
Clicking a box (or the Total box to clear) writes the category to a bound
control variable, so the rest of the workbook can filter/highlight off the
drill selection. Single-file vanilla JS on the `@sigmacomputing/plugin` SDK.

## Editor-panel config
- **source** — the data element (one row per category, already aggregated or raw — plugin aggregates client-side)
- **category** — the breakdown dimension (e.g. `Category`: Fuel/Merch/LFK/QSR)
- **value** — the main measure
- **aggregation** — `sum` or `avg` across rows sharing a category
- **priorValue** — comparison column for the variance arrow (optional)
- **cornerLeft** / **cornerLeftLabel** — bottom-left metric + its label (optional)
- **cornerRight** / **cornerRightLabel** — bottom-right metric + its label (optional)
- **totalLabel** — label on the Total box
- **valueFormat** — `currency` or `number`
- **clickTarget** — a bound List/Text control; clicking a box sets it, clicking Total (or the selected box again) clears it

## Register + embed
1. Host `index.html` on **GitHub Pages** off this public repo — NOT jsDelivr,
   which serves `.html` as `Content-Type: text/plain` and both renders as raw
   source text in a real workbook and hangs `/v2/workbooks/{id}/export` PNG
   export indefinitely (see HANDOFF.md §9, found 2026-08-13):
   `https://cmiller-coder.github.io/millersigma/plugins/decomposition-tree/index.html`
2. Register: `POST /v2/plugins {name,description,url,type:"element"}` → returns `pluginId`.
3. Embed: `{kind:"plugin", pluginId, config:{source:{kind:"element",elementId}, category:"<colId>", value:"<colId>", priorValue:"<colId>", cornerLeft:"<colId>", cornerRight:"<colId>", clickTarget:"<controlId>"}}` (bindings are bare columnId/controlId strings matching the editor-panel names; `aggregation`/`valueFormat`/labels are plain string values, not column bindings).
4. Unbound or before the config/data handshake resolves (including during
   headless PNG export, which snapshots before that round-trip completes),
   the plugin shows an "illustrative" synthetic Fuel/Merch/LFK/QSR tree rather
   than an empty prompt — matching the `synth()` fallback convention other
   plugins in this repo use.

Note: this is a bespoke chart, not a native Sigma element — there is no
"decomposition tree" in the workbook-spec `element.kind` enum (34 valid kinds,
verified against the public OpenAPI). A native `pivot-table` element covers
the tabular rows×columns breakdown; this plugin covers the interactive
drill-down box view.
