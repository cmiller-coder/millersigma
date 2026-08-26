# Barton — Assignment Booked Last 5 Weeks

Recreation of Barton's "Assignment Booked Last 5 Weeks" dashboard as a Sigma
workbook built entirely from code.

## Build

```bash
python3 workbooks/barton/build_booked_dashboard.py
```

Creates the workbook on first run and updates it in place afterwards (the id is
tracked in `booked-dashboard.json`). Every run also exports the rendered page to
`artifacts/booked-dashboard.png`, which is the only way to visually verify a
build without a browser session.

Requires a `.env` at the repo root with `SIGMA_BASE_URL`, `SIGMA_CLIENT_ID`,
`SIGMA_CLIENT_SECRET`, and `SIGMA_TOKEN_FETCHER`.

## Data

`BARTONDB.GOLD.ASSIGNMENT_PROD` on the *Snowflake POC* connection.

| Dashboard label | Warehouse column | Notes |
|---|---|---|
| Assignment Type | `Reassignment` | Extension / New Assignment / Reassignment. The SF `Assignment Type` column holds Regular / Telehealth / Consults and is a different concept. |
| Provider Type | `SF Long Provider Type` | Physician / Advanced Practice Nurse / Physician Assistant / Other. The raw `Provider Type` column holds credentials (MD, DO, NP…). Blanks are bucketed as "Other". |
| AE Entity | `AE Company` | Barton / Wellhart |

Derived measures, matched against the source dashboard:

```
Week Ending       = DateAdd("day", 5, DateTrunc("week", [Assignment Created Date]))   -- Friday
Projected Billing = [Bill Rate] * [Assignment LOA] * 8
GM Dollars        = ([Bill Rate] - [Pay Rate]) * [Assignment LOA] * 8
GM Percent        = [GM Dollars] / NullIf([Projected Billing], 0)
```

Scope is production assignments (`prod_assignment = "Yes"`) booked in the
trailing five week-ending buckets.

## Row scoping is done by a control, not a filter

Sigma's spec API **silently drops** element-level `where` and `filter` fields —
they pass validation and then do nothing. Verified by building three identical
tables (unfiltered, `where`, `filter`) and exporting all three: same row counts.

What does work: a **list control with a default value**, whose filter cascades to
every child element. Verified against known ground truth — a child element of a
control-filtered table returned 81,569 rows against an unfiltered total of
91,994, exactly matching the targeted subset.

So the base table carries a `Booking Scope` column (`"Last 5 Weeks"` /
`"Excluded"`) and `ctrl-window` defaults to `"Last 5 Weeks"`. Clearing that
control widens the page to all history.

## Spec-API constraints found on this org

| Feature | Status |
|---|---|
| `pie-chart` / `donut-chart` | Supported, but only with the legacy `color: {id}` / `value: {id}` shape — `columnId` is rejected. |
| Bar/line/area/combo axes | Require `xAxis: {columnId}` / `yAxis: {columnIds: [...]}`. |
| Series breakout | `color: {by: "category", column: "<bare id>"}`. `stacking` accepts `none` / `stacked`; `grouped` is rejected. |
| Axis sort | `xAxis: {sort: {by: "<id>", direction: "descending"}}`. The `columnId` form is silently ignored. |
| Map charts | **Not code-representable.** `map-region`, `map-point`, `map-geography` were each rejected across ~200 field-shape combinations. The state tile is a ranked bar chart; switch it to Map - Region in the UI. |
| Table `groupings` | Rejected — the detail table is flat and sorted rather than grouped with subtotals. |
| `pivot-table` | Rejected. |
| Link-formatted columns | No accepted `format` shape, so the source dashboard's "File Links" column is omitted. |
| Custom SQL sources | Rejected — only `warehouse-table` sources work. |

Note that "Invalid kind" is Sigma's generic message for a bad field shape, not
proof that an element kind is unsupported. Every conclusion above came from
sweeping shapes until something validated.

## Text bindings

The narrative line under the charts uses `{{[Element Name/Column Name]}}`
bindings against the KPI elements in the footer band. Those bindings do
round-trip and render.
