---
name: sigma-company-dashboard-v2
description: >-
  START HERE — the FLAGSHIP end-to-end generator for a branded Sigma workbook
  (command center + scenario modeler + cohort builder), PLUS a pixel-perfect
  PDF report, for a NAMED company or prospect, via the workbooks-as-code API
  (POST /v2/workbooks/spec, POST /v2/reports/spec). ONE company config dict
  drives EVERYTHING — the builder scripts (scripts/build_sofi.py,
  scripts/build_statement.py) are never edited per prospect. Supports building
  only a subset of surfaces (SURFACES=command / command,model / command,cohort
  / command,model,cohort env var). Proven across seven companies spanning
  fintech, banking, healthcare payer, QSR, private equity, dental and airline.
  Composes the same building blocks as sigma-company-dashboard v1
  (branded-dashboard-format, sigma-workbook-conventions, sigma-workbook-styling,
  sigma-input-table-app, sigma-cohort-builder-app) but replaces its hand-authored
  per-prospect scripts with ONE reusable generator plus a config file. Use this
  — not v1 — for any new "build a Sigma dashboard/workbook/POV/demo for
  [company]" request. Read reference/HANDOFF.md FIRST, in full, before writing
  any code.
---

# Sigma Company Dashboard v2 — one config, whole app

This is a full working generator, not a set of instructions to follow from
scratch. Given a company name, it produces a 3-page branded Sigma workbook and
(optionally) a pixel-perfect PDF statement, entirely from one Python config
block plus two builder scripts that never change.

## Read this first

**`reference/HANDOFF.md`** is the complete guide — architecture, every
verified API fact and gotcha, the config field reference, the cross-industry
mapping table, plugin authoring rules, cost economics, and the full inventory
of what's been built. It is long on purpose. Read it in full before touching
any script; skimming it is how the four-times-repeated display-label trap
(§8) gets hit a fifth time.

## The one thing to internalize

**`scripts/company.py` is the only file that changes per prospect.**
`scripts/build_sofi.py` (the workbook) and `scripts/build_statement.py` (the
report) are universal builders. If you find yourself editing either builder
script to make a new company work, stop — the fix almost always belongs in
`company.py` as a new config key, not as a per-company branch in the builder.
(The one exception this session: the hero-plugin binding and the surface
gating genuinely needed builder changes, because they're capabilities, not
company facts. See HANDOFF §5b, §9.)

## Quick start

```bash
cd scripts
COMPANY=<key> python3 build_sofi.py verify          # cheap but nearly worthless
COMPANY=<key> python3 build_sofi.py create           # the real validation
SURFACES=command COMPANY=<key> python3 build_sofi.py create   # command center only
COMPANY=<key> python3 build_statement.py create      # the pixel-perfect PDF, if configured
```

Existing companies: `sofi, boa, elevance, mcd, abry, nuvia, delta` — read their
blocks in `scripts/company.py` before writing a new one; copy the nearest
analog rather than starting blank.

## Adding a company

Ask the user only what cannot be inferred (surfaces wanted, demo vs prospect
org, whether a bespoke plugin is in scope for this call — it only renders from
the machine hosting `plugins/`). Do not ask for products, colors, or metric
names — deriving those from the company's real public segment reporting is
the entire value of this skill. Full workflow in HANDOFF.md §5.

## What this composes (and what it replaces)

Same building-block skills as v1's `sigma-company-dashboard`:
`branded-dashboard-format`, `sigma-workbook-conventions`,
`sigma-workbook-styling`, `sigma-input-table-app`, `sigma-cohort-builder-app`.
What's different is that v1 hand-authors a fresh generator script per company;
v2 has ONE generator and a config file, so a new company is an edit to
`company.py`, not a new Python file. See HANDOFF.md §17 for the standing
conventions this inherited from v1 and from Ryan Lauderback's
`ryan-workbook-skill` (the unrelated project `sigma-workbook-conventions` was
originally forked from — no runtime dependency, historical lineage only).

## Plugins

`plugins/` holds the 8 bespoke plugins this generator's seven companies
actually reference (not the full 48-plugin millersigma library). They must be
served from a local HTTP host for their `pluginId` to resolve — see
HANDOFF.md §10 for hosting and the registration workflow. **They only render
from whichever machine is hosting them**; this is the biggest open gap, not a
per-plugin issue.
