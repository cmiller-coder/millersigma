# Campaign Flight Timeline

A Gantt-style media flight calendar for an advertising-agency Sigma dashboard
(built for the Innocean POV). Each campaign is a horizontal bar across a month
axis, colored by channel, with the spend labeled on the bar and a hover tooltip
(campaign, channel, flight dates, spend). Includes a month axis, a channel
legend, and a totals readout.

- Single-file `index.html`, vanilla JS + `@sigmacomputing/plugin` CDN SDK.
- **Config:** source element + `campaign`, `channel`, `start`, `end`, `spend` columns.
- Synthetic fallback renders standalone (open the file directly).
- Bind to a table of flight rows (campaign / channel / start date / end date / spend).

Run locally: `python3 -m http.server 3000` and register `http://localhost:3000/`
as the plugin URL, or host it statically anywhere.
