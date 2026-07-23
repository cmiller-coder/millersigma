# Styled workbook examples

Clone-and-modify reference specs of a polished Sigma workbook, used by
`sigma-workbook-styling`. Treat as immutable references — clone the blocks you
need; don't edit in place.

| File | Why it's here |
|---|---|
| `branded-company-dashboard.json` | A full end-to-end branded dashboard spec: a hero masthead container (data-URI image), a gradient KPI-card row (each card a composite of title image + current/prior KPIs + a white in-card sparkline), a tinted CallText AI-insight box, a color-by-category bar chart, a filter cluster, an embedded plugin element, and a detail table. Shows the layout XML, `themeOverrides`, and the load-bearing color rules in one place. |

The connection and folder IDs in the spec are placeholders
(`REPLACE_WITH_YOUR_CONNECTION_ID`, `REPLACE_WITH_YOUR_FOLDER_ID`) — swap in your
own before POSTing. Generate it from the `sigma-company-dashboard` generator
(`skills/sigma-company-dashboard/examples/build_cava.py`).

Add new beautiful specs here as you build them — especially any using **buttons**
(open link / set control / open Sigma doc), since that shape isn't yet captured.
