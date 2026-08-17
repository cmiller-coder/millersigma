# Sigma Motors — Market Signal

Restyle of the EV/hybrid backlog command center so it reads like the
GA Motors / Volterra / Horizon mockups: navy chrome, white KPI cards,
tinted AI band, quick-questions rail, and the existing demand-pulse
plugin as the regional donut row.

## Publish

```bash
export SIGMA_BASE_URL=...   # Sigma API host for the target org
# optional: SIGMA_FOLDER_ID, SIGMA_CONNECTION_ID, SIGMA_PLUGIN_ID, SIGMA_PLUGIN_REF
python3 workbooks/sigma-motors/build.py create
```

`SIGMA_PLUGIN_REF` is the git ref jsDelivr should serve the plugin from
(default `main`). After this branch is pushed, create with
`SIGMA_PLUGIN_REF=<sha>` so the restyled rings load immediately.

## Org note

The cloud-agent token used to first publish this lands in **sigma-on-sigma**,
not papercranestaging. The original workbook
`Sigma-Motors-1tAWeYDFblZOEGu9Gq4WjW` is not writable with that token.
Re-run `create` against papercranestaging credentials to drop the same
spec in Connor's original org.
