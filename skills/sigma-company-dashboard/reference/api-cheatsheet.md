# Sigma workbooks-as-code — verified API cheatsheet

Hard-won from real builds. **Trust GET-back specs of recent, UI-built workbooks
over any older doc/exemplar — the spec schema has drifted.** POST to
`/v2/workbooks/spec`; `folderId` is REQUIRED at CREATE.

## The masked "Invalid kind" error
`{"message":"pages[0].elements[N]: Invalid kind: \"<kind>\""}` almost never means
the kind is unsupported — it means a **field on that element has the wrong shape**.
Bisect by element index; compare the offending element to a GET-back exemplar.

## Verified element shapes (CURRENT schema)
- **table (from custom SQL):** `{kind:"table", source:{connectionId, statement, kind:"sql"}, columns:[{id, formula:"[Custom SQL/<OUT>]", name}], name, order:[...]}`.
- **kpi-chart:** `{kind:"kpi-chart", source:{elementId, kind:"table"}, columns:[{id, formula, name, format?}], value:{columnId, color}, name:{visibility:"hidden"} | {text,fontWeight,fontSize}, layout:{anchor:"middle"}, style?}`. Comparative KPI: `timeline:{columnId}` + `periodComparison:"month"`. **Encoding uses `columnId`, NOT `id`** (old `value:{id}` → masked Invalid kind).
- **bar/line/area:** `xAxis:{columnId, sort?, format?}`, `yAxis:{columnIds:[...], format?}` (an OBJECT with `columnIds`, not `[{id}]`). `name`/`legend` accept `{visibility:"hidden"}`. line: `lineAreaStyle:{interpolation:"monotone"}`.
- **series/bar color:** `color:{by:"category", column:<COL-ID>, scheme:[...]}`. `column` must be a SEPARATE column (can't reuse the x/y column). Uniform-color bars → add a duplicate dimension column and color by it (scheme one color) + hide legend.
- **single-line color:** no per-line override — comes only from `themeOverrides.categoricalScheme[0]`.
- **region-map:** `{kind:"region-map", source:{elementId,kind:"table"}, columns:[{id,formula},...], region:{id:<stateColId>, regionType:"us-state"}, color:{by:"scale", column:<metricColId>}}`.
- **pivot-table:** `rowsBy:[{id}]`, `columnsBy:[{id}]`, `values:["<colId>"]` (exact — objects-as-values rejected).
- **container:** `{kind:"container", style?, backgroundImage?}`. Its children are placed INSIDE its `<GridContainer>` in the layout XML.
- **image:** `{kind:"image", url:"<https or data-URI>", style:{fit:"cover"|"scale-down"}}`.
- **text:** `{kind:"text", body:"<markdown, supports {{formula}} incl CallText>", verticalAlign:"middle"}`.
- **control:** `{kind:"control", controlId (workbook-unique), controlType:"list"|"date-range"|"text-area"|..., filters:[{source:{kind:"table",elementId},columnId}], source:{kind:"source",source:{...},columnId}}`.
- **plugin (needs a registered pluginId):** `{kind:"plugin", pluginId, displayName, config:{source:{kind:"element",elementId}, <binding>:{kind:"column",columnId,source}}}`.

## style vocabulary (rounds-trips on containers/kpi/chart/image)
`backgroundColor` (hex or `{kind:"theme",ref:"colors-..."}`), `borderColor`,
`borderWidth` (0/1/3), `borderRadius` (`"pill"|"round"|"square"`), `padding` (only
`"none"`), `backgroundImage` (top-level, `{url, style:{fit}}`), `fit`, `color`,
`strokeStyle`, `textWrap`, `align`, `bold`, `fontSize`/`fontWeight` (on kpi/chart `name`).

## Column format (POSTS FINE — the "format is rejected" doc is stale)
Currency `{"kind":"number","formatString":"$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}`;
percent `{"kind":"number","formatString":".1%"}`; datetime axis `{"kind":"datetime","formatString":"%b %Y"}`.

## Layout
Top-level `layout` XML string; one `<Page>` per page (multiple `<Page>` siblings =
tabs). Every element `id` must appear as a `LayoutElement`/`GridContainer` in it,
and every `container` needs a matching `<GridContainer>` WITH nested children.
`<Page type="grid" gridTemplateColumns="repeat(24,1fr)" ...>`. **Cross-page
element sourcing works** (a chart on page A can source a table on page B).

## The big gotchas
- **Text color = theme, not element.** `style.color` on text (and the kpi `name`)
  is ignored → renders `themeOverrides.colors.text`. White text on a dark surface
  must be a **data-URI SVG image**; a colored callout must be a **light-tint
  container** (dark theme-text reads). Dark box + text = invisible.
- **Dark canvas breaks control dropdowns** (white popup + light theme-text). Use a
  LIGHT canvas + dark accent cards (hero, gradient KPI cards, plugin panel).
- **Sparklines:** stable metrics render flat unless the y-axis auto-fits →
  `yAxis.format.scale = {type:"linear", zero:false, hideZeroLine:true}`. Give each
  KPI card its OWN trend formula (don't reuse revenue for all).
- `verticalAlign` on text: only `"middle"` (top/bottom → masked Invalid kind).
- **UI-only (NOT spec-able), even after enabling in the UI:** `chat` element and
  `tabbed-container` — the API rejects both. Use a styled placeholder + pages-as-tabs.
- Composite KPI card = a gradient `container` (backgroundImage) holding: a white
  SVG title image, "Current/Prior" white SVG label images, two transparent
  `kpi-chart`s (`value.color:"#fff"`, `style.backgroundColor:"transparent"`), and a
  transparent sparkline line-chart. All children nested in the container's GridContainer.

## Auth / hosting
Token via `scripts/get-token-staging.sh` (client_credentials → bearer); clear
`/tmp/.sigma_token` when switching creds. Netlify CLI authed; create a UNIQUE
site then deploy with an explicit `--site`.
