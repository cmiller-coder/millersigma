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

## Live publish (this session)

- workbookId: `28b6ce84-62bb-44ac-88a8-cea9784bfd24`
- urlId: `1ePeD6ePBhR0ZITiwehyOE`
- org: sigma-on-sigma (the reachable token). Original file
  `1tAWeYDFblZOEGu9Gq4WjW` is on papercranestaging and was not writable
  with this token — re-run `create` there to replace it.

Verified exports: EV waitlist 4,120 vs 3,720; ranked bar SW→South;
pending approvals 2 / 508 units.
