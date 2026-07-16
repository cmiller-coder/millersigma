# Styled workbook examples

Real GET-back specs of beautiful Sigma workbooks, used as clone-and-modify
sources by `sigma-workbook-styling`. These are immutable references — clone the
blocks you need; don't edit in place.

| File | Why it's here |
|---|---|
| `marketing-control-center.json` | Gradient KPI card row, AI insight banner, control cluster, a repeated container ("Repeater Base"), CDN + data-URI SVG images. |
| `cold-provisions.json` | Richest example — 135 containers, repeated cards and list rows, column-bound images, dividers, styled tables. Best repeater source. |
| `demand-planning.json` | Leaner, input-table-driven layout with themed containers and KPIs. |

All three are from the `demeng` workspace (org `752dac5c-…`), pulled via:

```bash
scripts/api/publish-workbook.sh get-spec <workbookId> | jq . \
  > skills/sigma-workbook-styling/examples/<name>.json
```

Add new beautiful specs here as you build them — especially any using **buttons**
(open link / set control / open Sigma doc), since that shape isn't yet captured.
