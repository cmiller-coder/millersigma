# Comparison KPI Card — Sigma plugin

A polished KPI card: current-vs-prior value with ▲/▼ RAG delta, a sparkline, and
a gradient background — the composite KPI look that's awkward to build with native
Sigma elements. Single-file, vanilla JS, `@sigmacomputing/plugin` SDK from CDN
(no build step). Renders synthetic data when opened standalone (preview).

**Hosted:** https://sigma-kpi-card-plugin-bb.netlify.app

## Use in Sigma
1. Admin → Plugins → Add plugin → paste the hosted URL.
2. In a workbook, add the plugin element; in the editor panel set: **source** element,
   **Trend order** (date/x column), **Measure**, **title**, **format** (currency/number/percent),
   **comparison** mode, **accent color**.

## Deploy updates
`netlify deploy --prod --dir . --site 476b3282-81e4-4993-b60b-f822129675c5`
