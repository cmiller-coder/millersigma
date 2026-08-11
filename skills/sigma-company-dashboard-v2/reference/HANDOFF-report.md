# Reports as code — pixel-perfect PDF

Reference for `build_statement.py`. Load this doc only when building a PDF report.

---

## Running the report

```bash
cd ~/Desktop/Prospects/SoFi-2026/scripts

COMPANY=delta python3 build_statement.py create      # creates new report object
COMPANY=delta python3 build_statement.py update <id> # updates existing
python3 shot_report.py <report-id> 1 ../shots/out/p1.png  # render page 1
```

The report ID is written to `specs/report_id_<key>.txt`. Once that file exists,
`build_sofi.py` shows a statement button on page 1.

---

## Spec shape

`document.kind: "report"`, absolute x/y/w/h positioning, `<Panel type="header">`
and `type="footer"` for global furniture, `pdata` hidden page for SQL plumbing.
Export is PDF-only.

---

## STATEMENTS config key

Every string in the report plus the headline formula bindings:
```python
STATEMENTS["delta"] = {
    "button_label": "View SkyMiles Statement",
    "h_formulas": [
        (source_elementId, formula, "MONEY"),   # "MONEY" | "MONEY0" | "NUM0"
        ...
    ],
    # ... all prose strings
}
```

Fixed column contracts — **do not rename these**:
- activity table: `Transaction Date, Post Date, Merchant Name or Transaction Description, Category, Amount, Points Earned`
- rewards table: `Line Order, Description, Points`
- summary table: `Line Order, Metric, Value`

`statement_activity_sql` / `rewards_summary_sql` / `account_summary_sql` return
`None` for companies without an override, falling back to the on-disk SoFi files.
**Only sofi and delta have full statement configs so far.**

---

## Layout gotchas

- Tables clip their last row silently if the height is too short (7 rows needed
  252px, not 210px — add ~6px per extra row)
- An `H1` needs more box height than its font size or glyphs clip and the next
  element overlaps
- `logo_navy()` silently falls back to the WHITE datauri; if the report header is
  light-coloured, generate a separate navy recolour for the logo
- **Never hand the header/footer columns fixed magic-number x-offsets** (e.g.
  `MARGIN + 630`). They silently drift out of sync with column widths the
  moment either is edited — this shipped for a while with the last header
  column overlapping its neighbor by 5px and overflowing the page's right
  margin by 34px (4px past the physical page edge), which reads as "content
  looks off-center / cramped on the right" in a render, not as an API error.
  `build_statement.py`'s header now computes `h_col_x` from a `H_COL_W` list
  plus a fixed `H_GAP`, with an `assert` that the row fits inside
  `PAGE_W - MARGIN`. Do the same for any new fixed-width row you add — never
  place a column at a literal `MARGIN + <number>`.
- **The report UI's own "Page Layout &gt; Margins" field is a different thing
  entirely** — it's a print-safety border around the whole page, not a lever
  on individual element positions. Every element in the spec is absolutely
  positioned (`x`/`y`/`width`/`height`), so this UI field cannot move, resize,
  or de-overlap a column — it can only pad the outside of the finished page.
  Don't mistake "I nudged the margin slider and it looked better" for a fix;
  if columns are overlapping or overflowing, the bug is in the element
  `x`/`width` math in `build_statement.py`, not in this UI setting.

---

## Rendering

macOS has no `pdftoppm`, and `qlmanage` only renders page 1 correctly.
`shot_report.py` rasterizes via `swift` + CoreGraphics.

```bash
python3 shot_report.py <report-id> <page-number> <out.png>
# e.g.:
python3 shot_report.py ca716231-57e1-49a0-8729-ea286d1de7c3 1 ../shots/delta-report/p1.png
```
