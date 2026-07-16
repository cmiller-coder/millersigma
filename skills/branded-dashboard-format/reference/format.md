# The Format — canonical page + element checklist

The recurring composition. One page does the job for most asks; add drill pages
(Trend / Detail / Exceptions) only when the question demands it. Defer to
`sigma-workbook-conventions` for field shapes, layout XML, and the division/`nullif`
and KPI/pivot/control gotchas — this file is about *what goes where*.

## Element inventory (single overview page)

| Block | Element(s) | Required | Notes |
|-------|-----------|----------|-------|
| Header | `container-header` | ✅ | Holds logo+title (left), Date Range + grain control (right). |
| — logo | `image` element | ✅ | `{kind:"image", url:"…"}` in the header (NOT a markdown image — `text` doesn't render those). See brand-kit. |
| — title | `text` (markdown) | ✅ | `## **<Title>**` + one-line subtitle (omit brand name when the logo is present). |
| — date range | `control` `date-range` | ✅ | Bound to the base table's date column. |
| — grain | `control` `segmented` | ✅ | `controlId: c-dategrain`, values `Day/Week/Month`, default `Month`. Drives the trend's `DateTrunc`. |
| Filters | `container-filters` | ✅ | A single row of `list` controls, all bound to the base table. |
| KPI band | `kpi-chart` ×N | ✅ | Headline/funnel KPIs first row; rate KPIs second. Each has a date dim for sparkline. |
| Trend | `line-chart` (or combo) | ✅ | x = `DateTrunc([c-dategrain], [<base>/<Date>])`; y = the funnel/headline series. |
| Detail | `pivot-table` (wide) | ✅ | Analytical dimensions as `rowsBy`; every metric in `values`; grand totals on. |
| Base | `table` (the source) | ✅ | The two-tier root; placed bare at the bottom (acts as drill/detail + source). |

## Two-tier sourcing (the spine)

```
warehouse-table | data-model element
        └─ tbl-base  (kind: table)         ← the ONE base; controls bind here
              ├─ kpi-*        (source: table → tbl-base)
              ├─ chart-trend  (source: table → tbl-base)
              └─ pivot-*      (source: table → tbl-base)
```

Why: page controls bound to `tbl-base` cascade to every descendant automatically.
Metrics (`[Metrics/…]`) resolve through the chain when the root is data-model-sourced.
This is the single most important structural rule — get it wrong and filters
don't propagate.

## Layout grid (24-col, the proportions we use)

- Header container: `gridRow 1 / 4`, full width. Title `1 / 13`, Date `13 / 20`, Grain `20 / 25`.
- Filters container: `gridRow 4 / 7`, full width; list controls split evenly (`1/5,5/9,…`).
- KPI row 1 (≤6 tiles): `gridRow 7 / 15` (8 rows tall — sparkline needs the height).
- KPI row 2 (rates): `gridRow 15 / 23`.
- Trend: full width, `gridRow 23 / 38`.
- Detail pivot: full width, tall (`38 / 62`).
- Base table: full width at the very bottom.

## KPI band conventions

- **Order tells the story**: top row = the funnel / headline counts in funnel
  order; second row = the rates (Coverage, CTR, CVR, CPC, RPC, …).
- Each KPI `columns` = `[ DateTrunc("month", [<base>/<Date>]) , [Metrics/<X>] ]`
  and `value: { columnId: <the metric col> }`. The date dim is what produces the
  sparkline + period delta.
- Don't ship a bare number — a KPI with no comparison is a defect.

## The wide detail pivot (the part people love)

- `rowsBy` = the analytical dimensions, coarse → fine (e.g. Publisher → Placement
  → Geo → Intent). `columnsBy: []` (must be `[]` at POST, not null).
- `values` = **every** metric as an id string. Bias wide: stakeholders pull from
  this table and reshape it themselves, so include counts *and* rates.
- Turn on grand totals / subtotals (position first) — configured in the UI; the
  spec computes the totals, the UI sets where they render.

## Drill pages (only when asked)

Overview → **Trend** (period-over-period, comparison controls) → **Detail**
(row-level) → **Exceptions** (anomaly/threshold list). Same two-tier spine, same
brand. Don't pre-build these; add when the question needs them.
