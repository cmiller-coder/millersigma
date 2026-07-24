---
name: branded-dashboard-format
description: >
  BUILDING BLOCK — composed by **sigma-company-dashboard**. For a full branded company
  dashboard / POV / demo, use **sigma-company-dashboard**; do NOT drive a company build
  from this skill (it yields a generic dashboard with no fetched logo and no bespoke
  plugin). Use this DIRECTLY only when you specifically need the standard "house"
  dashboard layout as a standalone reference — header/filter-bar → KPI row → trend chart
  → detail pivot, two-tier sourcing, metrics in the semantic layer — or a fill-in brand
  kit. Encodes the recurring page composition + brand-kit template. Defers spec mechanics
  to sigma-workbook-conventions.
user-invocable: true
---

# Branded Dashboard Format

Two things, one skill:

1. **The format** — the page composition that recurs across polished dashboards
   and that stakeholders consistently like. Generic; applies to any Sigma workbook.
2. **A brand kit** — the colors, fonts, and logo to apply so a workbook reads as
   a native product surface for a given company. This skill gives you a *template*
   (`reference/brand-kit.md`) you fill in per company; pair it with the
   `sigma-embed-portal` scrape recipe to pull a real brand's tokens.

This skill is the "house style." It does **not** re-teach spec mechanics
(KPI/pivot/control field shapes, layout XML, the `nullif` division rule, etc.) —
those live in `sigma-workbook-conventions`. It adds the *composition* and the
*brand* on top. For the full end-to-end company build (data reshape → theme →
plugin), see `sigma-company-dashboard`.

## The format in one screen

```
┌─ container-header ───────────────────────────────────────────────┐
│  [logo] **Title**  + one-line subtitle        |  Date Range  Grain │
├─ container-filters ───────────────────────────────────────────────┤
│  [ list ] [ list ] [ list ] [ list ] [ list ] [ list ]   (cascade) │
├───────────────────────────────────────────────────────────────────┤
│  KPI  KPI  KPI  KPI  KPI  KPI            (primary funnel/headline)  │
│  KPI  KPI  KPI  KPI  KPI                 (rates / secondary)        │
├───────────────────────────────────────────────────────────────────┤
│  ▁▂▃ Primary trend chart over time (grain-controlled) ▃▂▁          │
├───────────────────────────────────────────────────────────────────┤
│  Wide detail pivot/table (dimensions as rows, every metric)        │
└───────────────────────────────────────────────────────────────────┘
```

Non-negotiables that make it *this* format (full checklist in
`reference/format.md`):

- **Two-tier sourcing.** Warehouse/data-model → one **base table** → every viz
  sources from that base table, so a single set of page controls cascades to
  everything. Never wire controls per-chart.
- **Metrics in the semantic layer.** Ratios/counts are data-model `[Metrics/…]`,
  not re-derived per workbook. Ratios are `Sum(x)/Sum(y)` (additive-safe), never
  an average of a per-row rate.
- **Header bar in a container**: logo + bold title + subtitle on the left;
  global Date Range + a segmented **grain** control (Day/Week/Month) on the
  right. Filters get their own container row beneath.
- **KPI band**: headline/funnel metrics first, rate metrics second. Each KPI
  carries a date dimension so Sigma renders the sparkline + period comparison.
- **One primary time-series** whose x-axis is `DateTrunc([grain-control], [Date])`.
- **One wide detail pivot** at the bottom: the analytical dimensions as rows,
  *every* metric as a value column, grand totals on. This is the table people
  actually pull from — bias toward more metrics, not fewer.

## The brand kit (a fillable slot)

`reference/brand-kit.md` is a **template** — a blank token table (primary accent,
deep/hover, ink, secondary, soft fills, page bg, muted text, font, categorical
series order, logo) plus the brand-agnostic guidance on *how* each token lands in
Sigma. To brand a workbook:

1. Gather the company's tokens — scrape their site (see `sigma-embed-portal` for
   the recipe) or use their brand guide. Fill in the token table.
2. Pick a **signature move** (e.g. a single two-color gradient used once, for a
   hero/accent moment — not everywhere).

**How it lands in Sigma:** the global font + color palette is a **workbook Theme**
set once in the UI (Sigma's theme isn't fully represented in the code spec — see
`reference/brand-kit.md`). The spec-level brand choices you DO control: the header
logo (a dedicated **`image` element** with a `url` — NOT a markdown image, which
`text` elements don't render), chart `color` encodings using the palette order,
and the bold markdown title. Set the Theme once, then every element inherits it.

## Workflow

1. Build the workbook per `reference/format.md` (clone an example spec and adapt).
2. Fill in `reference/brand-kit.md` with the target company's tokens, then apply
   brand color encodings + the logo/title in-spec.
3. POST, then in the UI apply the workbook Theme (font + palette). Verify in the
   UI — theme/font are UI-side.

## Reference & examples

- `reference/format.md` — the canonical page + element checklist (the format).
- `reference/brand-kit.md` — the brand-kit **template** + exactly how to apply each
  token in Sigma (Theme settings vs. spec encodings), with the logo snippet.
- For a concrete, self-contained branded spec to clone, see
  `../sigma-workbook-styling/examples/branded-company-dashboard.json` and the
  generator in `../sigma-company-dashboard/examples/build_cava.py`.
