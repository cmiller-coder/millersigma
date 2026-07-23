# Examples

- **build_cava.py** — THE canonical generator (current standard). A full CAVA
  restaurant POV: two pages (command center + scenario modeler) on light surfaces,
  comparative **gradient KPI cards with native, colorable titles** (no SVG-title
  hacks), a CallText AI insight, control-driven `Switch`/`DateTrunc` filters, a
  stacked bar, **side-by-side pivots**, a **bespoke data-bound plugin in a
  container below the bar**, and **two agents** (read-only analyst + a Scenario
  Copilot with an insert-rows tool). Copy it; swap the brand config
  (colors/logo/name), the reshape SQL, the AI prompt, and register your own plugin.
  Run: `python3 build_cava.py <SIGMA_BASE_URL> <TOKEN> <CONNECTION_ID> <FOLDER_ID>`.
- The matching bespoke plugin lives at **`plugins/cava-daypart/`** — a 7×24
  day-part heatmap (`@sigmacomputing/plugin` SDK, synthetic fallback). Register via
  `POST /v2/plugins` → `pluginId`, host it, and embed it bound to a synthetic
  operational source (see the generator).

## Quick-start alternatives (also restored)

- **build_template.py** — a lighter starter generator (emits `spec.json`; `CONN` from
  `SIGMA_CONNECTION_ID`, folder as argv). Its plugin panel points at a **ready-hosted**
  plugin so you don't have to host anything — register the live URL and embed.
- **plugin-heatmap.html** — that ready-hosted plugin (GPU utilization heatmap), live at
  `https://scintillating-madeleine-4aceba.netlify.app`. Register its URL (`scripts/register_plugin.py`)
  → `pluginId` → embed. Zero hosting; works from any org.
