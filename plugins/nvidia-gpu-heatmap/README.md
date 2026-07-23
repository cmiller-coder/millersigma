# GPU Cluster Utilization Heatmap — NVIDIA Sigma plugin

Data-center node grid heat-mapped by GPU utilization (NVIDIA-green health scale; over-temp nodes flagged red), hover tooltips (node/model/util/temp/power), fleet-avg + hot count. Built on operational SQL (per-node utilization/temp/power), not revenue KPIs. Single-file vanilla JS + @sigmacomputing/plugin CDN SDK; synthetic fallback.

**Hosted:** https://scintillating-madeleine-4aceba.netlify.app (Netlify site bc60ad33-d800-4e1f-be05-67a1a77b0f1a)
Redeploy: `netlify deploy --prod --dir . --site bc60ad33-d800-4e1f-be05-67a1a77b0f1a`
