# Examples

- **build_template.py** — a full working generator (the NVIDIA build): custom-SQL
  reshape, light-canvas + dark-accent theme, 3 composite gradient KPI cards, a
  CallText AI-summary in a light-tint container, a segment bar, a plugin
  placeholder panel, a detail table, and a synthetic "GPU Fleet" element. Copy it,
  swap the brand config (colors/logo/name), the reshape SQL, and the AI prompt.
  Run: `python3 build_template.py <folderId>` → writes a spec.json → POST via curl.
  (Needs a hero image `*-sm.jpg` in the same dir; generate one or use a solid header.)
- **plugin-heatmap.html** — a full hosted Sigma plugin (GPU cluster utilization
  heatmap): single-file, `@sigmacomputing/plugin` CDN SDK, editor-panel config,
  synthetic fallback. Deploy to any static host (Netlify) and register in Sigma.
