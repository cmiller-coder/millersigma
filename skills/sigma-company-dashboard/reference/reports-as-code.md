# Pixel-perfect reports as code

Reports became code-representable in August 2026 (staging first). They are the
print/PDF deliverable that pairs with an interactive workbook: fixed page size,
repeating header and footer, absolute element placement.

Endpoints — note the shape mirrors workbooks exactly, with `kind: "report"`:

| Action | Call |
| --- | --- |
| Create | `POST /v2/reports/spec` |
| Update | `PUT  /v2/reports/{reportId}/spec` |
| Read   | `GET  /v2/reports/{reportId}/spec` |
| List   | `GET  /v2/reports` |

## Skeleton

```json
{
  "name": "Acme — Performance Report",
  "folderId": "<uuid>",
  "document": {
    "schemaVersion": 1,
    "kind": "report",
    "elements": [ ... ],
    "pages": [
      {"id": "p1", "name": "Executive Summary"},
      {"id": "p2", "name": "Detail"},
      {"id": "pdata", "name": "Data", "visibility": "hidden"}
    ],
    "panels": [
      {"id": "global-header", "type": "header", "title": "Report header",
       "config": {"height": 104, "backgroundColor": ""}, "pages": ["p1", "p2"]},
      {"id": "global-footer", "type": "footer", "title": "Report footer",
       "config": {"height": 48, "backgroundColor": ""}, "pages": ["p1", "p2"]}
    ],
    "settings": {"theme": {"overrides": { ... }}},
    "config": {"margin": 36, "pageHeight": 1056, "pageWidth": 816},
    "layout": "..."
  }
}
```

## Page geometry

`document.config` is the page setup. Sigma works in CSS pixels at 96 dpi:

| Paper | Portrait | Landscape |
| --- | --- | --- |
| US Letter | 816 × 1056 | 1056 × 816 |
| US Legal | 816 × 1344 | 1344 × 816 |
| A4 | 794 × 1123 | 1123 × 794 |

With `margin: 36` (0.375") the usable width on Letter portrait is
`816 - 72 = 744`. Budget vertical space as
`pageHeight - margin*2 - headerHeight - footerHeight`.

## Layout is absolute, not a grid

`<Panel>` blocks are siblings of `<Page>` at the root of the layout XML, and
panel coordinates are relative to the panel — not the page.

```xml
<?xml version="1.0" encoding="utf-8"?>
<Page id="p1">
  <Element elementId="p1-h1"  x="36" y="0"   width="744" height="34"/>
  <Element elementId="p1-bar" x="36" y="170" width="744" height="240"/>
</Page>
<Panel id="global-header" type="header">
  <Element elementId="h-logo" x="36" y="22" width="250" height="34"/>
</Panel>
<Panel id="global-footer" type="footer">
  <Element elementId="f-note" x="36" y="14" width="744" height="26"/>
</Panel>
```

Drive the y-cursor from code rather than hand-typing offsets, so inserting a
block reflows the page:

```python
y = 0
add(heading, "p1", MARGIN, y, CONTENT_W, 34); y += 42
add(chart,   "p1", MARGIN, y, CONTENT_W, 240); y += 252
```

## Rules that will bite

* **Every element must be placed in the layout**, including the custom-SQL table
  that only exists to feed charts: `element 'src' is not placed in layout`. Park
  it on a page with `"visibility": "hidden"` — do not omit it.
* Restrict header/footer `panels[].pages` to the **printed** pages, so the hidden
  data page does not get furniture.
* **Not supported in reports:** containers, tabbed containers, navigation,
  drawers/modals, page numbers, element layering, report-level theming beyond
  `settings.theme`, and CSV input tables. Supported: tables, pivots, controls,
  text, image, divider, plugin, embed, and every chart the workbook supports.
* Reports have no grid, so there is no `gridColumn`/`gridRow` — passing them is
  silently useless.

## Pairing a report with a workbook

Use the `open-document` effect on a workbook button to hand off:

```json
{"effect": "open-document", "documentId": "<reportId>",
 "documentType": "report", "openTarget": "_blank"}
```

Build the report first so the id exists, then reference it from the workbook.

## Worked example

`~/Desktop/Prospects/JPMC-2026/scripts/build_report.py` — a two-page US-Letter
JPMorganChase franchise report with a logo/title/rule header panel, a footer
disclaimer, four comparative KPI cards, a bar chart, a grouped table and a
pivot, all positioned from a y-cursor. It shares `brand.py` and `sigmaapi.py`
with the workbook generator next to it.
