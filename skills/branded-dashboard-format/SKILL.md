---
name: branded-dashboard-format
description: >
  Use when building a Sigma workbook that should follow our standard "house"
  dashboard format (header/filter-bar → KPI row → trend chart → detail pivot,
  two-tier sourcing, metrics in the semantic layer) AND/OR apply the
  adMarketplace brand (Geist font, indigo→purple palette, logo). Trigger
  phrases: "use the standard dashboard format", "make it look like our other
  dashboards", "brand this for adMarketplace / AMP", "match the AMP look".
  Encodes the recurring page composition + the adMarketplace brand kit.
  Prerequisites: sigma-api, sigma-data-models, sigma-workbook-conventions.
  Does NOT restate spec mechanics (defer to sigma-workbook-conventions) and is
  not a domain/metric pattern (those are per-domain skills).
user-invocable: true
---

# Branded Dashboard Format

Two things, one skill:

1. **The format** — the page composition that recurs across our dashboards and
   that stakeholders consistently like. Generic; applies to any Sigma workbook.
2. **The adMarketplace brand kit** — the colors, fonts, and logo to apply so a
   workbook reads as a native adMarketplace product surface.

This skill is the "house style." It does **not** re-teach spec mechanics
(KPI/pivot/control field shapes, layout XML, the `nullif` division rule, etc.) —
those live in `sigma-workbook-conventions`. It adds the *composition* and the
*brand* on top.

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

## The brand kit in one screen

Full tokens + how to apply them in `reference/brand-kit.md`.

| Role | Token |
|------|-------|
| Primary accent (indigo-blue) | `#3b45ff` |
| Primary deep / hover | `#002eda`, `#101c89` |
| Darkest — headings/axis text | `#00022e` |
| Secondary accent (purple) | `#7f56d9`, `#6941c6` |
| Soft blue — card/zebra fills | `#deedff`, `#f1f5ff` |
| Page background | `#ffffff` / `#f8f8f8` |
| Muted text | `#758696` |
| Font (primary / secondary / mono) | **Geist** / Poppins / Geist Mono |
| Categorical series order | `#3b45ff → #7f56d9 → #002eda → #00022e → #758696` |
| Logo | `assets/admarketplace-logo.svg` |

Signature move: the **blue→purple gradient** (`#3b45ff → #7f56d9`). Use it for a
single hero/accent moment, not everywhere.

**How it lands in Sigma:** the global font + color palette is a **workbook Theme**
set once in the UI (Sigma's theme isn't fully represented in the code spec — see
`reference/brand-kit.md`). The spec-level brand choices you DO control: the
header logo (a dedicated **`image` element** with a `url` — NOT a markdown image,
which `text` elements don't render), chart `color` encodings using the palette
order above, and the bold markdown title. Set the Theme once, then every element
inherits it.

## Workflow

1. Build the workbook per `reference/format.md` (clone `examples/` and adapt).
2. Apply brand color encodings + the logo/title in-spec per `reference/brand-kit.md`.
3. POST, then in the UI apply the **adMarketplace** workbook Theme (font Geist,
   palette per the table). Verify in the UI — theme/font are UI-side.

## Reference & examples

- `reference/format.md` — the canonical page + element checklist (the format).
- `reference/brand-kit.md` — adMarketplace tokens + exactly how to apply each in
  Sigma (Theme settings vs. spec encodings), with the logo snippet.
- `assets/admarketplace-logo.svg` — the wordmark.
- `examples/amp-edm-product-funnel-spec.json` — a real GET-back that embodies the
  format on adMarketplace data (the "Product Performance (EDM)" workbook). Clone
  and adapt; treat as immutable reference.
