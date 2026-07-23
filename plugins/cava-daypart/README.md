# CAVA Day-part Heatmap — Sigma plugin

A 7-day × 24-hour revenue-intensity heatmap for restaurant day-part analysis. Single-file
vanilla JS on the `@sigmacomputing/plugin` SDK; synthetic fallback so it previews standalone.

## Editor-panel config
- **source** — the data element (one row per day/hour)
- **day** — day-of-week column (`Mon`…`Sun`)
- **hour** — hour column (`0`–`23`)
- **value** — revenue (or any intensity metric)

## Register + embed
1. Host `index.html` (e.g. `http://localhost:8080/cava-daypart/` or a static host).
2. Register: `POST /v2/plugins {name,description,url,type:"element"}` → returns `pluginId`.
3. Embed in a workbook spec: `{kind:"plugin", pluginId, config:{source:{kind:"element",elementId}, day:"<colId>", hour:"<colId>", value:"<colId>"}}` (bindings are bare columnId strings that match the editor-panel names).

Bind to a 7×24 day-part source (see `skills/sigma-company-dashboard/examples/build_cava.py` for a full 2-page workbook generator that builds the source, KPIs, agents, and this plugin).
