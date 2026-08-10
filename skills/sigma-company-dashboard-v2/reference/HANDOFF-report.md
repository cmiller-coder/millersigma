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

---

## Rendering

macOS has no `pdftoppm`, and `qlmanage` only renders page 1 correctly.
`shot_report.py` rasterizes via `swift` + CoreGraphics.

```bash
python3 shot_report.py <report-id> <page-number> <out.png>
# e.g.:
python3 shot_report.py ca716231-57e1-49a0-8729-ea286d1de7c3 1 ../shots/delta-report/p1.png
```
