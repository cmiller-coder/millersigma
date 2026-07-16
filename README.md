# millersigma

A Claude Code **plugin** bundling Chris Miller's Sigma Computing skills — one
home for everything that helps Claude build Sigma workbooks, dashboards, embed
portals, and plugins. Install it once and every skill below becomes available
in any project.

## Skills

| Skill | What it does | Dependencies |
|---|---|---|
| **sigma-workbook-conventions** | Authoring/editing/reviewing Sigma workbook & data-model JSON specs — input resolution, naming, layout, control catalog, ID semantics, and the POST-time gotchas. The flagship skill. | Uses `scripts/` (see [Working with the scripts](#working-with-the-scripts)); pairs with the upstream `sigma-api` / `sigma-data-models` skills. |
| **sigma-workbook-styling** | The visual-craft layer — containers as design blocks, images/logos, buttons & actions, and color/spacing/typography to make a workbook look *designed*, not just correct. Honest about what round-trips via spec vs what needs UI finishing. | Pairs with `sigma-workbook-conventions` (mechanics) and `branded-dashboard-format` (brand). |
| **branded-dashboard-format** | The house dashboard format (header/filter-bar → KPI row → trend → detail pivot) + the adMarketplace brand kit. | Prereq: `sigma-workbook-conventions`. |
| **sigma-embed-portal** | Scrape a prospect's site, build a branded Sigma embed portal, deploy via Netlify. Self-contained. | — |
| **sigma-plugin-development** | Full reference for building Sigma plugins with the `@sigmacomputing/plugin` SDK — editor panel, element data, variables, actions, hosting. | — |
| **sigma-plugin-patterns** | Architectural recipes for plugins (JSON settings pattern, etc.). | Pairs with `sigma-plugin-development`. |

## Install as a plugin

This repo is both a plugin and a single-plugin marketplace, so you can install
it directly from GitHub:

```
/plugin marketplace add cmiller-coder/millersigma
/plugin install millersigma@millersigma
```

Skills are auto-discovered from `skills/`. Once installed, they trigger by
description or can be invoked by name.

## External dependency: Sigma's official skills

`sigma-workbook-conventions` and `branded-dashboard-format` build on Sigma's
own agent skills — **`sigma-api`** (OAuth → bearer token) and
**`sigma-data-models`** (data-model spec round-trips). Those ship in Sigma's
official marketplace plugin, not here. Install that separately for full
workbook-authoring capability.

## Authentication

The `scripts/` here call the Sigma REST API and MCP server. They self-bootstrap
from a `.env` file (never committed — see `.gitignore`):

```
SIGMA_BASE_URL=...
SIGMA_CLIENT_ID=...
SIGMA_CLIENT_SECRET=...
```

On first call, `scripts/api/_env.sh` loads `.env`, fetches an OAuth token via
the `sigma-api` skill, and caches it at `/tmp/.sigma_token` (0600, 55-min TTL).
Secrets live only in `.env` and the `Authorization` header — never in specs,
prompts, or notes.

## Working with the scripts

`sigma-workbook-conventions` was authored to run **with a workbook project as
the working directory** — it invokes `scripts/api/*.sh` and
`python3 scripts/*.py` by relative path. Two ways to use it:

1. **Clone-and-work (matches original design).** Clone this repo, add your
   `.env`, and run Claude Code with the repo as the working directory. Scripts
   resolve as-is. Merge `skills/sigma-workbook-conventions/recommended-permissions.json`
   into your `.claude/settings.json` so discovery calls run without prompts.
2. **Installed plugin.** The reference/pattern skills (both plugin skills,
   `sigma-embed-portal`, and the guidance in `branded-dashboard-format`) work
   fully when installed. For the script-driven parts of
   `sigma-workbook-conventions`, reference the plugin's copy via
   `${CLAUDE_PLUGIN_ROOT}/scripts/...` or keep a project checkout per option 1.

> Making the scripts fully path-independent (via `${CLAUDE_PLUGIN_ROOT}`) so the
> workbook skill runs seamlessly as an installed plugin is a planned follow-up.

## Layout

```
millersigma/
├── .claude-plugin/
│   ├── plugin.json         # plugin manifest (skills auto-discovered from skills/)
│   └── marketplace.json    # makes the repo self-installable via /plugin
├── skills/                 # one folder per skill, each with SKILL.md
├── scripts/                # Sigma API/MCP helpers used by the workbook skill
│   ├── api/                # auth-bootstrapped REST + MCP wrappers
│   ├── sigma-resolve.py    # messy-input → resolved IDs
│   └── validate-spec.py    # pre-POST spec validator
├── docs/                   # conventions, iteration playbook, skill-authoring guide
└── README.md
```

## Adding new skills

1. Create `skills/<new-skill-name>/SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: <new-skill-name>
   description: >-
     One or two sharp sentences on WHEN to use it — this is what Claude
     matches against, so lead with trigger conditions.
   ---
   ```
2. Add `reference/`, `examples/`, or `assets/` subfolders as needed.
3. Bump `version` in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
4. Commit and push. Installed users pick it up with `/plugin marketplace update millersigma`.

See `docs/skill-authoring.md` for the authoring pattern (sharp descriptions,
`reference/` split by domain, `examples/` with at least one known-good spec).

## Provenance

Consolidated from two upstream repos, now maintained here:
- Workbook/dashboard/embed skills + scripts — originally `RyanLauderback/ryan-workbook-skill`.
- Plugin skills — originally `neil-oliver/sigma-plugin-skills` (frontmatter added here).
