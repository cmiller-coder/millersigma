# Code representation: the 2026-08 schema (verified live)

Everything below was verified against `api.staging.sigmacomputing.io`
(papercranestaging) on **2026-08-07** by building a 107-element, three-page
workbook plus a two-page pixel-perfect report from scratch.

**If a spec that used to work now fails, read this file first.** The envelope,
the layout XML tag names, and several enums all changed as code rep moved toward
public beta.

---

## 1. The `document{}` envelope

Only `name` and `folderId` stay at the top level. Everything else moved inside
`document`:

```json
{
  "name": "My Workbook",
  "folderId": "<uuid>",
  "document": {
    "schemaVersion": 1,
    "kind": "workbook",
    "elements": [ ... ],
    "pages":    [ {"id": "pg1", "name": "Overview"} ],
    "overlays": [ ... ],
    "agents":   [ ... ],
    "settings": {"theme": {"overrides": { ... }}},
    "layout":   "<?xml ...?>..."
  }
}
```

Endpoints are unchanged: `POST /v2/workbooks/spec`,
`PUT /v2/workbooks/{id}/spec`, `GET /v2/workbooks/{id}/spec`,
`POST /v2/workbooks/spec/verify`.

## 2. `document.pages[].elements` is gone — elements are FLAT

Elements now live in a single `document.elements` array. Page membership comes
**only** from the layout XML. The error is explicit:

```
document.pages[].elements is no longer supported.
Move elements to document.elements instead.
```

Page objects are just `{id, name}`, plus optional
`visibility` (`"hidden"` or `{kind: "specific-users-and-teams", assignments}`),
`backgroundImage`, `backgroundColor`, and `pageWidth`.

This makes workbooks and reports structurally the same shape.

## 3. Layout XML tags were RENAMED

| Old | New |
| --- | --- |
| `<LayoutElement>` | `<Element>` |
| `<GridContainer>` | `<Container>` |

`<TabbedContainer>` and `<Tab>` are unchanged.

```xml
<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg1">
  <Container elementId="c-hdr" type="grid" gridColumn="1 / 25" gridRow="1 / 8"
             gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <Element elementId="logo" gridColumn="1 / 7" gridRow="1 / 4"/>
  </Container>
  <TabbedContainer elementId="tc" type="tabbed-container" gridColumn="1 / 18" gridRow="8 / 40">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <Element elementId="bar" gridColumn="1 / 25" gridRow="1 / 17"/>
    </Tab>
  </TabbedContainer>
</Page>
```

> **The single worst trap in the new schema.** Using `<LayoutElement>` does not
> produce a validation error — it returns a **masked 500**:
> `"An error has occurred. Please try again later (incident-id=...)"`.
> Any time you see that message, suspect the layout XML before anything else.

## 4. Modals and drawers live in `document.overlays`

They are no longer pages with `type: "modal"`. Overlay ids still get their own
`<Page id="...">` block in the layout XML.

```json
"overlays": [
  {"id": "modalScenario", "type": "modal", "name": "New Scenario",
   "modal": {"width": "small",
             "header": {"title": "Create a scenario", "showCloseIcon": "shown"},
             "footer": {"primaryCta": {"visible": "hidden"},
                        "secondaryCta": {"visible": "hidden"}}}},

  {"id": "drawerLob", "type": "drawer", "name": "Detail",
   "drawer": {"width": "medium", "position": "end", "showShadow": "shown",
              "header": {"title": "Line of business detail", "showCloseIcon": "shown"}}}
]
```

`width` ∈ `x-small | small | medium | large | x-large`; drawer `position` ∈
`start | end`. **Drawers are new to code rep** (UI beta shipped 2026-08-07).

## 5. Action effects — all 13

`open-url`, `open-overlay`, `close-overlay`, `set-control-value`,
`clear-control`, `insert-rows`, `update-rows`, `delete-rows`, `refresh-element`,
`navigate`, `select-tab`, `open-document`, `sequence`.

Previously-documented-as-unsupported and now **confirmed working**:

```json
{"effect": "navigate",  "target": {"type": "page", "page": "pg2"}}

{"effect": "select-tab", "tabbedContainerElementId": "tc-main",
 "selectedTab": {"type": "tab", "index": 1}}
// or {"type": "direction", "direction": "next" | "previous"}

{"effect": "update-rows", "tableElementId": "it-drivers",
 "whichRows": {"type": "formula", "formula": "True"},
 "values": {"d-growth": {"type": "formula", "formula": "... + 2"}}}

{"effect": "delete-rows", "tableElementId": "it-segments",
 "whichRows": {"type": "formula", "formula": "True"}}

// Cross-document navigation — can target a REPORT, not just a workbook.
{"effect": "open-document", "documentId": "<reportId>",
 "documentType": "report", "openTarget": "_blank"}
```

`whichRows` accepts `SingleRow | CurrentRow | FormulaSelector | ColumnMatch`;
`{"type": "formula", "formula": "True"}` is the "all rows" idiom.

`clear-control` is the odd one out — it takes a **`scope`**, not a `control`:

```json
{"effect": "clear-control", "scope": {"type": "control", "controlId": "SegmentName"}}
```
`scope.type` ∈ `control | container | page | workbook`.

Value shapes for `set-control-value` / row effects:
`{"type": "constant", "value": {"type": "text"|"number"|"boolean"|"date"|..., "value": ...}}`,
`{"type": "control", "control": "..."}`, `{"type": "formula", "formula": "..."}`,
`{"type": "column", "columnId": "..."}`, `{"type": "agent-input", "inputName": "..."}`.

## 6. Conditional triggers + success toasts

A trigger can be a bare string or an object with a condition:

```json
"actions": [{
  "id": "a1",
  "trigger": {"on": "on-select",
              "condition": {"type": "column", "columnId": "dw-lob", "condition": "IsNotNull"}},
  "successToast": {"showMessage": "shown", "title": "Filtered",
                   "message": "Command center scoped to that line of business."},
  "effects": [ ... ]
}]
```

Triggers: `on-click`, `on-select`, `on-primary-cta-click`,
`on-secondary-cta-click`, `on-close`.

Condition is either
`{type: "column", columnId, condition: "IsNull"|"IsNotNull"|"="|"!="|">"|">="|"<"|"<="|"Contains"|"NotContains"|"StartsWith"|"EndsWith" (+value) | "Between"|"NotBetween" (+low/high)}`
or `{type: "constant", cond: "="|"In", value: {...}}`.

**There is no `control` condition type** — a conditional trigger needs row
context, so put it on a table's `on-select`, not on a button.

Actions also accept `name`, `state` (`enabled`/`disabled`), and `summary`.

## 7. Agents are code-representable, with real tools

```json
"agents": [{
  "id": "ag-franchise",
  "name": "Franchise Copilot",
  "description": "...",
  "instructions": "...",
  "greeting": {"mode": "static", "message": "Ask me about ..."},
  "dataSources": [{"kind": "table", "elementId": "tbl"}],
  "tools": [
    {"toolId": "t1", "kind": "action", "name": "Focus a line of business",
     "description": "...",
     "steps": [{"kind": "effect", "effect": "set-control-value",
                "control": "LineOfBusiness",
                "value": {"type": "agent-input", "inputName": "Which line of business"}}]}
  ]
}]
```

`greeting.mode` ∈ `static` (with `message`) | `generated` (with `prompt`).

Tool kinds: `action`, **`mcp-connector`** (`{connectorId, name}`),
**`warehouse-agent`** (`{connectionId, path: []}`),
**`search-service`** (`{connectionId, path: [], description}`).

An `action` tool's steps are `{kind: "effect", ...}` (any of the 13 effects) or
`{kind: "sequence", sequenceId}`. Every `agent-input` still needs `inputName`.

Surface an agent with a `chat` element: `{"id": "chat1", "kind": "chat", "agentId": "ag-franchise"}`.

## 8. Enum and field changes that bite

| Field | Correct values | Was / wrong |
| --- | --- | --- |
| `verticalAlign` (text) | `start` \| `middle` \| `end` | `top` / `bottom` |
| `button.appearance` | `filled` \| `text` \| `outline` | `outlined` |
| `groupings[].id` | a **new unique id** | reusing the column id → `Duplicate id` |
| `clear-control` | `scope: {...}` | `control: "..."` |
| control label | `name` | `label` |
| text `body` | markdown | `<p>` HTML is rejected |

Grouped tables:

```json
"groupings": [{"id": "dwg",
               "groupBy": ["dw-lob"],
               "calculations": ["dw-rev", "dw-exp"],
               "sort": [{"columnId": "dw-rev", "direction": "descending"}]}]
```

`direction` is `ascending`/`descending` — never `asc`/`desc`.

## 9. Control shapes (each type has required fields)

```json
// list — needs mode, selectionMode, values AND a source block
{"kind": "control", "id": "ctrl-lob", "controlId": "LineOfBusiness",
 "name": "Line of Business", "controlType": "list",
 "mode": "include", "selectionMode": "multiple", "values": [],
 "filters": [{"source": {"kind": "table", "elementId": "tbl"}, "columnId": "f0"}],
 "source": {"kind": "source", "source": {"kind": "table", "elementId": "tbl"},
            "columnId": "f0"}}

// date-range
{"controlType": "date-range", "mode": "between",
 "includeNulls": "when-no-value-is-selected", "filters": [ ... ]}

// text
{"controlType": "text", "mode": "equals", "case": "insensitive",
 "includeNulls": "when-no-value-is-selected", "showOperators": false}

// segmented — options come from a manual source
{"controlType": "segmented",
 "source": {"kind": "manual", "valueType": "text", "values": ["A", "B"]},
 "value": null}

// number-range
{"controlType": "number-range", "filters": [ ... ]}
```

Confirmed control types: `list`, `date-range`, `text`, `text-area`,
`number-range`, `segmented`, `slider`. **Correction (2026-08-15): a numeric
slider DOES exist** (`controlType: "slider"`, single-handle; `range-slider`
is presumably its two-handle sibling, not yet verified) — the prior claim
here that no slider exists was wrong, caught only from a user screenshot of
the live control-picker UI, not from re-reading docs. Verified shape:
```json
{"controlType": "slider", "mode": "=", "low": -20, "high": 20, "step": 1, "value": 0}
```
The range fields are **`low`/`high`, not `min`/`max`** — `min`/`max` are
silently dropped (no validation error) and Sigma falls back to a default
`low:0, high:100`, so this fails quietly, not loudly. Always GET the spec
back (or screenshot the live control) to confirm the bounds actually landed
— `verify`/`create` succeeding is not proof the field names were right.

## 10. Element kinds

Valid: `table`, `pivot-table`, `input-table`, `control`, `container`,
`tabbed-container`, `text`, `image`, `divider`, `button`, `plugin`, `chat`,
`kpi-chart`, `bar-chart`, `line-chart`, `area-chart`, `combo-chart`,
`scatter-chart`, `pie-chart`, `donut-chart`, and the map charts.

**Correction (verified against the OpenAPI, 2026-08-08):** an earlier draft of
this file listed `repeater` and `navigation` as unsupported. That was wrong — the
kinds are **`repeated-container`** and **`navigation`** (the latter requires
`mode`), and both write fine. The mistake was mine and it is exactly the trap
documented above: `Invalid kind` almost always means a missing required field, not
an unsupported kind. Get the authoritative list from the OpenAPI rather than any
prose list, including this one — see
[openapi-is-source-of-truth.md](openapi-is-source-of-truth.md).

Genuinely absent from the 30 element kinds: `stack`, `python`, `iframe`.

**`repeated-container` is code-representable but not usable.** It writes, and it
renders one card per row, but per-card values cannot be bound: the `{{}}`
reference must be repeater-qualified, and the kind has **no `name` field** in the
write schema. Source-table-qualified renders "Multiple values", bare column
references fail at query time, and aggregate wrappers aren't row-scoped. A
UI-built repeater also doesn't round-trip — its card children are absent from
both `document.elements` and the layout on GET.

## 11. Hard-won gotchas

* **`verify` is weaker than `create`.** `POST /spec/verify` checks structure
  only — it does **not** resolve SQL, check connection health, or catch
  duplicate ids / dangling references. A spec can pass verify and still fail
  create. Always create (or update) to truly validate.
* **Every element must be placed in the layout**, including data-plumbing
  tables: `elements[0]: element 'src' is not placed in layout`. Park sources on
  a page with `"visibility": "hidden"`.
* **Linked input tables cannot `delete-rows`** — their rows come from the source
  pivot. To reset one, `update-rows` the editable columns to null.
* **Overlay-level `actions` cannot resolve any control** — not even a control
  declared inside that overlay (`Control not found: <id>`). Hide the modal
  footer CTAs and put a real `button` element inside the overlay page instead.
  Same-page element actions resolve controls fine.
* **`color.by: "value"` is rejected** on line charts. A single-measure series
  needs a constant-string category column plus
  `color: {by: "category", column: "<that column>", scheme: [...]}`.
* **GET-back is not always POST-able.** A spec fetched from a live workbook can
  contain fields the write path rejects, so clone shapes from a GET but
  re-validate rather than assuming a round trip.
* Custom-SQL sources never auto-materialise columns — always declare
  `columns: [{id, name, formula: "[Custom SQL/<col>]"}]`. Omitting `columns`
  yields the unhelpful `Invalid kind: "table"`.
* `Invalid kind: "<kind>"` almost always means *a required field is missing or
  an enum value is wrong for that kind* — not that the kind is unsupported.

## 12. Reports as code

Same envelope, `kind: "report"`, plus three report-only concepts. Endpoints:
`POST /v2/reports/spec`, `PUT /v2/reports/{id}/spec`,
`GET /v2/reports/{id}/spec`.

```json
"document": {
  "schemaVersion": 1,
  "kind": "report",
  "elements": [ ... ],
  "pages": [{"id": "p1", "name": "Executive Summary"},
            {"id": "pdata", "name": "Data", "visibility": "hidden"}],
  "panels": [
    {"id": "global-header", "type": "header", "title": "Report header",
     "config": {"height": 104, "backgroundColor": ""}, "pages": ["p1", "p2"]},
    {"id": "global-footer", "type": "footer", "title": "Report footer",
     "config": {"height": 48, "backgroundColor": ""}, "pages": ["p1", "p2"]}
  ],
  "config": {"margin": 36, "pageHeight": 1056, "pageWidth": 816},
  "layout": "..."
}
```

`config` is the page setup — **816 × 1056 is US Letter portrait at 96 dpi**
(landscape is 1056 × 816; A4 portrait is 794 × 1123).

Report layout is **absolute pixels, not a grid**, and `<Panel>` blocks are
siblings of `<Page>` at the root:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Page id="p1">
  <Element elementId="p1-h1" x="36" y="0" width="744" height="34"/>
  <Element elementId="p1-bar" x="36" y="170" width="744" height="240"/>
</Page>
<Panel id="global-header" type="header">
  <Element elementId="h-logo" x="36" y="22" width="250" height="34"/>
</Panel>
<Panel id="global-footer" type="footer">
  <Element elementId="f-note" x="36" y="14" width="744" height="26"/>
</Panel>
```

Panel element coordinates are relative to the panel, not the page.

Reports support tables, pivots, controls, text, image, divider, plugin, embed
and every chart the workbook supports. They do **not** support containers,
tabbed containers, navigation, page numbers, element layering, report-level
theming, or CSV input tables.

## 13. Worked reference build

A complete, working implementation of everything above lives at
`~/Desktop/Prospects/JPMC-2026/scripts/` — `build_jpmc.py` (three pages, modal,
drawer, 13-effect coverage, three agents, registered plugin) and
`build_report.py` (two-page US-Letter report with header/footer panels), sharing
`sigmaapi.py` and `brand.py`.


---

## What is UI-only (verified 2026-08-09, papercranestaging)

Three capabilities exist in the product but **cannot be written from code rep**.
All three are destroyed by a full spec `PUT`, so build them in the UI *last*, or
work additively off `GET /spec`.

| Capability | How it fails from code |
| --- | --- |
| **Page headers / sidebars** | `document.panels` is in the OpenAPI, but `PUT` returns `panels: page headers and page sidebars are not enabled for this workspace`. A UI-built header does **not** round-trip: `GET /spec` returns `panels: null`, so the next `PUT` silently wipes it. `<Panel>` as a layout tag is a masked 500; `<Container type="header">` and `type="panel"` both downgrade to `type="grid"` on read-back. |
| **Repeated containers with per-card values** | `repeated-container` exposes no `name` field, so the repeater-qualified `{{[Name/Column]}}` reference its own docs require cannot be written. Workaround: N hand-built containers, each reading its row with `MaxIf([T/Col], [T/Key] = "k")`. Visually identical, but do not call it a repeater in front of an audience. |
| **API actions** | The workbook-action effect enum is exactly twelve: `clear-control, close-overlay, delete-rows, insert-rows, navigate, open-document, open-overlay, open-url, refresh-element, select-tab, set-control-value, update-rows`. There is no `call-api`. Adding one rejects with `Invalid kind: "button"`. The capability shipped to public beta in Feb 2026 and connectors exist on the org — it is simply not in the spec surface. |

**To pull live external data from code, use a plugin.** A registered plugin
fetching a CORS-enabled endpoint client-side works today and is fully
code-written — e.g. the SoFi rates ticker pulling live US Treasury par yields on
every load.

## Input-table data-entry permission

`inputMode` is the only permission field on `input-table`:

| value | UI equivalent |
| --- | --- |
| `edit` | Editable in draft |
| `explore` | Editable in published version (restricted) |
| `view` | Editable in published version (all access levels) |

It round-trips correctly. If inserts fail with *"Edits can only be made in draft
mode"*, check whether the viewer is in a **Custom view** — writes are blocked
there regardless of `inputMode`.
