# Pace-to-Target Pour — Budweiser Sigma plugin

A domain-specific plugin: an animated pint of beer that fills (amber + foam head)
to show a current value vs a target, with % to goal and a RAG status
(Behind / On pace / Goal hit). Beer-native and genuinely useful for volume/revenue
goal tracking on a brewer's dashboard. Single-file vanilla JS + `@sigmacomputing/plugin`
CDN SDK; renders synthetic data standalone.

**Hosted:** https://budweiser-pace-to-target.netlify.app
(Netlify site id 6e10b375-65d1-48bc-abe6-4c396dae6c1b)

## Config (editor panel)
source element · Current value column · Target column (optional) · Target-if-no-column ·
Title · format (number/currency).

## Redeploy
`netlify deploy --prod --dir . --site 6e10b375-65d1-48bc-abe6-4c396dae6c1b`
