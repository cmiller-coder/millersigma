# Barton — Assignment Booked Last 5 Weeks

Recreation of Barton's "Assignment Booked Last 5 Weeks" dashboard as a Sigma
workbook built entirely from code. Follow-up from the Aug 27 working session
with Megh Poudel: native linear regression, US-only region map, Salesforce
file links, in-page AI chat, and a pixel-perfect PDF report.

## Build

```bash
python3 workbooks/barton/build_booked_dashboard.py
python3 workbooks/barton/build_booked_report.py
```

Creates the workbook / report on first run and updates in place afterwards
(ids in `booked-dashboard.json` and `booked-report.json`). The dashboard build
also exports `artifacts/booked-dashboard.png`.

Requires `SIGMA_CLIENT_ID` / `SIGMA_CLIENT_SECRET` for the **Barton** org and
`SIGMA_BASE_URL` for that org's API host (or a `.env` at the repo root).
The cloud-agent default token is Sigma staging and cannot publish into Barton's
folder.

## Data

`BARTONDB.GOLD.ASSIGNMENT_PROD` on the *Snowflake POC* connection.

| Dashboard label | Warehouse column | Notes |
|---|---|---|
| Assignment Type | `Reassignment` | Extension / New Assignment / Reassignment. The SF `Assignment Type` column holds Regular / Telehealth / Consults and is a different concept. |
| Provider Type | `SF Long Provider Type` | Physician / Advanced Practice Nurse / Physician Assistant / Other. The raw `Provider Type` column holds credentials (MD, DO, NP…). Blanks are bucketed as "Other". |
| AE Entity | `AE Company` | Barton / Wellhart |
| File Links | `link.kind: formula` on Assignment Number | Display text is "Click to view file". URL pattern assumes Lightning `Assignment__c`. Swap in the UI if Assignment Number is not the Salesforce id. |

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

## Aug 27 follow-ups

| Ask | How it is encoded |
|---|---|
| Linear regression (not a combo duplicate of the same series) | `trendLine: {kind: "linear"}` on booked, GM$, GM%, avg LOA |
| US-only state map with labels | `kind: "region-map"`, `region: {id, regionType: "us-state"}`, `dataLabels` on |
| Custom summary sentence | Unchanged `{{[KPI/Value]}}` text binding above the table |
| Hyperlink to Salesforce | Display "Click to view file" with `link: {kind: "formula", formula: Concat(...)}`. `Hyperlink()` is not a Sigma function; `format.kind: link` is rejected. |
| AI chat on charts + base table | `kind: "chat"` + `agents[]` with those data sources |
| Pixel-perfect / scheduled PDF | Separate report object from `build_booked_report.py`. Schedule the email in the UI. |

## Spec-API constraints found on this org

| Feature | Status |
|---|---|
| `pie-chart` / `donut-chart` | Supported, but only with the legacy `color: {id}` / `value: {id}` shape — `columnId` is rejected. |
| Bar/line/area/combo axes | Require `xAxis: {columnId}` / `yAxis: {columnIds: [...]}`. |
| Series breakout | `color: {by: "category", column: "<bare id>"}`. `stacking` accepts `none` / `stacked`; `grouped` is rejected. |
| Axis sort | `xAxis: {sort: {by: "<id>", direction: "descending"}}`. The `columnId` form is silently ignored. |
| Region map | Supported as `region-map` (not `map-region`) with `region: {id, regionType: "us-state"}`. |
| Table `groupings` | Rejected — the detail table is flat and sorted rather than grouped with subtotals. |
| `pivot-table` | Rejected. |
| Link-formatted columns | `format: {kind: "link"}` is rejected; use a `Hyperlink()` formula. |
| Custom SQL sources | Rejected — only `warehouse-table` sources work. |

Note that "Invalid kind" is Sigma's generic message for a bad field shape, not
proof that an element kind is unsupported.

## Text bindings

The narrative line under the charts uses `{{[Element Name/Column Name]}}`
bindings against the KPI elements in the footer band. Those bindings do
round-trip and render.
