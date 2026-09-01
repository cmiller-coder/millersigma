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
  / command,model,cohort env var). Proven across eleven companies spanning
  fintech, banking, healthcare payer, QSR, private equity, dental, airline,
  hospitality, semiconductors, interactive entertainment and biotech/pharma.
  Use this — not v1 — for any new "build a Sigma dashboard/workbook/POV/demo
  for [company]" request.
---

# Sigma Company Dashboard v2 — one config, whole app

This is a full working generator, not a set of instructions to follow from
scratch. Given a company name, it produces a 3-page branded Sigma workbook and
(optionally) a pixel-perfect PDF statement, entirely from one Python config
block plus two builder scripts that never change.

## Read this first

**`reference/HANDOFF.md`** is the complete build guide — architecture, verified
API facts and gotchas, the config field reference, the cross-industry mapping
table, and plugin rules. Read it before writing any code; skimming it is how
the display-label trap gets hit a fifth time.

**For PDF builds only**, also read **`reference/HANDOFF-report.md`** — it has
the `STATEMENTS` config shape, fixed column contracts, and layout gotchas
specific to the report.

**For what's already built, what it costs, and how this skill relates to
the rest of the collection**, read **`reference/HANDOFF-status.md`** — not
needed to build a company, but read it before quoting a cost number or
claiming a company hasn't been built yet.

**Do not read `scripts/build_sofi.py` or `scripts/build_statement.py`** unless
you are debugging or modifying the builder itself. Those scripts are never
edited per prospect — reading them for a new company is wasted tokens.

## The one thing to internalize

**`scripts/company.py` is the only file that changes per prospect.**
`scripts/build_sofi.py` (the workbook) and `scripts/build_statement.py` (the
report) are universal builders. If you find yourself editing either builder
script to make a new company work, stop — the fix almost always belongs in
`company.py` as a new config key, not as a per-company branch in the builder.

## Quick start

```bash
cd scripts
COMPANY=<key> python3 build_sofi.py verify          # cheap but nearly worthless
COMPANY=<key> python3 build_sofi.py create           # the real validation
SURFACES=command COMPANY=<key> python3 build_sofi.py create   # command center only
COMPANY=<key> python3 build_statement.py create      # the pixel-perfect PDF, if configured
```

Existing companies: `sofi, boa, elevance, mcd, abry, nuvia, delta, marriott,
blizzard, nvidia, alnylam, ionis` — skim the nearest-industry block in
`scripts/company.py` before writing a new one; copy it rather than starting
blank.

## Standalone technique examples

`examples/` (see [`examples/README.md`](examples/README.md)) holds
self-contained, single-prospect builders that are **not** part of the
`company.py`/`build_sofi.py` config-driven flow above — copy the nearest one
rather than trying to fold a new prospect into `company.py` if what you need
is closer to what these demonstrate:

- [`build_honda_ev_allocation.py`](examples/build_honda_ev_allocation.py) —
  two-page allocation planner: control-driven scenario levers (not
  `update-rows`, which has no row context from a button — see
  `sigma-input-table-app/reference/approval-workflow-pattern.md`), a
  volume-neutral BEV/ICE trade, live Snowflake Cortex insight bound to the
  active scenario, and an optional bespoke plugin.
- [`build_shiftkey_marketplace_control_tower.py`](examples/build_shiftkey_marketplace_control_tower.py) —
  three-page marketplace command center: a full region→state→market→facility
  drill (grouped `table` with `groupings`, not `pivot-table` — see the
  "Pivot-table element shape" note in `sigma-workbook-conventions`), an
  account/supply action queue with an embedded chat agent, and a commission
  scenario modeler with tiered payout logic. Both scripts refuse to write
  outside papercranestaging (check `/v2/whoami` before POSTing).

## Adding a company

Ask the user only what cannot be inferred — and ask all five of these, not
just the first three (a cold run has skipped later ones before):
1. **Which surfaces?** command center only / + modeler / + cohort builder
2. **Which dashboard theme?** Show the five previews in
   [`examples/theme-gallery/`](examples/theme-gallery/README.md): Executive
   Gradient / Editorial Minimal / Operations Control Room / Aurora Glass /
   Field & Natural (plus Editorial Ops, `theme-presets.json`-only, for a
   data-app page needing light surfaces). If the user declines to choose,
   default to Executive Gradient. For a live, brand-and-content-customized
   preview before committing to a real build, copy the nearest file in
   `examples/theme-gallery/companies/` (see `honda.html`).
3. **Demo org or prospect org?**
4. **Bespoke plugin?** — default to yes and design a NEW one for this
   company's actual industry (HANDOFF.md §9's "never reuse the last one"
   table). Don't wire up whichever plugin is already sitting in `plugins/`
   just because it exists — a reused flywheel/ticker on the wrong industry is
   the single most visible "this is a reskin" tell. Registered plugins now
   host on jsDelivr off the public repo (see §9), so this renders for anyone,
   not just the machine that built it — that blocker is gone for new plugins
   registered this way.
5. **Pixel-perfect PDF report too?** — this is a separate script
   (`build_statement.py`) and, for a brand-new company, a whole new
   `STATEMENTS` config block to author (copy Delta's or SoFi's — the only two
   that exist so far). Say this cost up front rather than silently building it
   or silently skipping it.

Do not ask for products, colors, or metric names — deriving those from the
company's real public segment reporting is the entire value of this skill.
Full workflow in HANDOFF.md §5 and §5b; the PDF specifics are in
HANDOFF-report.md.

## Non-negotiable: real in-page navigation, every page, every theme

**Every top-level page needs its own `kind: "navigation"` element in the
header, listing every other top-level page — always, regardless of which
theme was picked.** This is not optional polish; skipping it ships a
workbook where a viewer literally cannot get from the BI page to a data-app
page (verified live 2026-08-13, papercranestaging: with no in-page nav
element, there was no way to navigate off the page you opened).

**Do not rely on Sigma's native page-tab bar for this**, even though
`settings.navigation.pageTabsInViewMode` defaults to `"shown"`. That native
tab bar is viewer chrome — it does not render in the shot.py/qa_pg1.py
headless PNG export, so a build can look complete in every screenshot taken
while building it and still ship without working navigation for a real
viewer. A `navigation` element is real page content: it always renders,
survives the same QA screenshots that already verify everything else, and
looks intentional instead of default-Sigma.

Verified shape (Honda's and ShiftKey's builds, light and dark themes both):

```json
{"id": "nav-<page>", "kind": "navigation", "mode": "manual", "showIcons": false,
 "style": {"backgroundColor": "transparent"},
 "optionStyle": {"textColor": "<theme textMuted>", "selectedColor": "<brand primary>",
                 "style": "pill", "orientation": "horizontal"},
 "options": [
   {"label": "Home", "destination": {"type": "page", "pageId": "page-home"}},
   {"label": "Regional Allocation Planner", "destination": {"type": "page", "pageId": "page-planner"}}
 ]}
```

An element is placed once, so a workbook with N top-level pages needs N
separate `navigation` element instances (one per page), all sharing the same
`options` list — not one shared element referenced from multiple pages.
`textColor`/`selectedColor` come from the chosen theme's token block
(`theme-presets.json`'s `text`/`textMuted` and `{brand.primary}`) so the nav
reads as designed rather than default, in every one of the six themes.

## Plugins

`plugins/` holds the bespoke plugins these companies actually reference (not
the full 48-plugin millersigma library). **Register new ones on jsDelivr off
this public repo** (`cdn.jsdelivr.net/gh/cmiller-coder/millersigma@main/plugins/<folder>/index.html`)
— that renders for anyone, permanently, no local server. The older
localhost:8080-hosted plugins still work only from the machine running that
server; migrate one to jsDelivr the first time a company needs it. See
HANDOFF.md §9 for the full registration workflow and the one confirmed API
constraint: **there is no update endpoint for an already-registered plugin**
— changing its URL means a new `pluginId` and re-pushing every workbook that
referenced the old one.
