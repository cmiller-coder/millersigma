# Regional Signal Map — build pipeline

`../index.html` is **generated**, not hand-edited. It is a single self-contained
file with the projected US geometry inlined (~300KB, ~80KB gzipped over the CDN).

## Why a build step

Earlier revisions of this plugin hand-authored the US outline as a ~45-point
polygon. It never actually read as the United States, no matter how the curve
smoothing was tuned — the problem was the geometry, not the rendering. This
version uses real geodata instead:

- **`us-atlas`** (Natural Earth / TIGER-derived) `states-10m.json` + `nation-10m.json`
- **`d3-geo`** `geoAlbersUsa()` — the standard composite US projection, which
  insets Alaska and Hawaii the way every good US dashboard map does
- **`topojson-client`** `mesh()` for borders, so each shared state edge is drawn
  exactly once (naively stroking every state polygon double-strokes interior
  borders, which reads visibly heavier than the coastline — the usual tell of a
  sloppy choropleth)

Everything is pre-projected at build time into a fixed `960x600` viewBox, so the
plugin ships zero runtime map dependencies: no CDN fetch for geodata, no d3 in
the browser, no projection math per render.

## Files

| file | role |
| --- | --- |
| `gen.js` | fetches the atlas from `node_modules`, projects it, writes `us-map-data.js` |
| `us-map-data.js` | generated: per-state paths + region assignment, region centroids, border meshes, nation outline |
| `template.html` | the actual plugin source — edit **this**, not `../index.html` |
| `build.js` | inlines `us-map-data.js` into `template.html` → `../index.html` |

## Regenerating

```sh
cd build
npm install d3-geo@3.1.0 topojson-client@3.1.0 us-atlas@3.0.1
node gen.js                 # only needed if changing projection / region mapping
node build.js ../index.html # needed after ANY template.html edit
```

Then redeploy (same Netlify site, so the registered pluginId and the workbook's
element config never change):

```sh
cd ..
netlify deploy --prod --dir . --site 2e5daf88-dfef-48de-bb8b-28c8e0f95de4
```

## Region mapping

The five regions match the workbook's `tbl-region` source rows exactly
(West / Southwest / Midwest / South / Northeast). All 50 states + DC are
assigned — `gen.js` prints any unassigned state names as a build warning, so a
typo in the mapping can't silently leave a state uncolored. Alaska and Hawaii
are part of **West**.

The map is a choropleth over the real 5-row source data — it deliberately does
**not** invent per-state or per-store numbers.
