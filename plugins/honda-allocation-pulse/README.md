# Honda Allocation Pulse

Compact Sigma plugin for the Hybrid vs. EV Allocation example. It stays above
the Planner / Approver persona tabs and summarizes:

- BEV mix vs. 18% target
- Electrified mix (HEV + PHEV + BEV)
- Network build-capacity utilization + number of constrained plant-months
- Battery-cell commitment

## Editor panel / workbook config

```json
{
  "mixSource": {"kind": "element", "elementId": "it-alloc"},
  "powertrain": "al-pt",
  "units": "al-eff",
  "cellKwh": "al-cells",
  "capacitySource": {"kind": "element", "elementId": "tbl-load"},
  "allocated": "pl-eff",
  "capacity": "pl-cap",
  "status": "pl-flag",
  "cellUsed": "pl-cells",
  "cellContract": "pl-cellcap",
  "cellStatus": "pl-cellflag"
}
```

The plugin supports partial configuration and synthetic fallback data when
viewed outside Sigma. It subscribes independently to the allocation and
capacity sources, transposes Sigma's column-oriented data in place, and clears
Sigma's loading state after each render. Cell commitment uses the grouped
plant-month table's actual cell draw divided by the contracted cell pool — not
a heuristic based on vehicle units — and reports the number of plant-months
over contract. A `ResizeObserver` recalculates the rail whenever Sigma changes
the iframe size.

## Hosting and registration

The host **must return `Content-Type: text/html`**. jsDelivr is not a valid
HTML-plugin host: it returns `.html` as `text/plain; charset=utf-8` plus
`X-Content-Type-Options: nosniff`, so Sigma displays the plugin's source code.

Use a durable first-party host: Netlify, Vercel, GitHub Pages, or
S3/CloudFront. HTMLPreview fails inside Sigma's sandbox because it fetches and
rewrites another page at runtime (`TypeError: Failed to fetch`). raw.githack is
also unsuitable: Cloudflare intermittently returns `403` and
`X-Frame-Options: SAMEORIGIN`, so a URL that returns 200 during registration
can fail in the workbook minutes later.

When no durable host is available, do **not** register a speculative CDN URL.
Leave `HONDA_PULSE_PLUGIN_ID` unset; the Honda builder renders the same compact
metrics as a native data-bound `text` rail with no iframe dependency.

Set **both** production URL and development URL to the executable hosted URL.
If devUrl is omitted, Sigma defaults it to localhost:5173 and remote
author/edit sessions show an unreachable iframe.

On demeng, `POST /v2/plugins` and `PATCH /v2/plugins/{id}` can apply the change
and then return a masked 404. On 404, list/read the registration before retrying
or you will create duplicates.

Sigma's PNG exporter hangs on pages that contain a plugin even when the iframe
loads publicly. Validate three pieces separately:

1. Standalone plugin render with synthetic data.
2. Plugin registration and workbook config round-trip.
3. Workbook page render with the plugin temporarily removed.

