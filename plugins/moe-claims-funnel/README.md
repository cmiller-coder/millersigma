# Claims Pipeline Funnel

A stage-funnel for an insurance Sigma dashboard (built for the Mutual of Enumclaw
POV). Renders claim volume flowing through pipeline stages (FNOL → Open →
In Adjusting → Settled → Closed) as green-graded bars, each showing count,
% of the first stage, drop-off vs. the prior stage, and an avg-days-in-stage
badge, plus a settle-rate readout.

- Single-file `index.html`, vanilla JS + `@sigmacomputing/plugin` CDN SDK.
- **Config:** source element + `stage`, `claims`, `days`, `order` columns.
- Sorts by the `order` column so stages stay in pipeline sequence (not by count).
- Synthetic fallback renders standalone; bind to a small stage table
  (stage / claims / avg days / order).

Run locally: `python3 -m http.server 3002` and register `http://localhost:3002/`
as the plugin URL, or host it statically anywhere.
