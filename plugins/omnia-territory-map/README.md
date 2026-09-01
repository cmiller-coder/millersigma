# Service Territory Map

A US choropleth for a field-services / home-improvement Sigma dashboard (built
for the Omnia Exterior Solutions POV). States are shaded by a metric (bookings)
using a blue intensity scale, with hover tooltips (bookings + jobs), a
"Top territories" side list, and a legend.

- Single-file `index.html`, vanilla JS + `@sigmacomputing/plugin` CDN SDK.
- Uses **d3** + **topojson-client** + **us-atlas** (all from CDN) for the map.
- **Config:** source element + `state` (full state name), `bookings`, `jobs` columns.
- Matches state features by `properties.name`, so bind a column of full state
  names ("Texas", not "TX").
- Best fed an aggregated table (one row per state); synthetic fallback renders standalone.

Run locally: `python3 -m http.server 3001` and register `http://localhost:3001/`
as the plugin URL, or host it statically anywhere.
