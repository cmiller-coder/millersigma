# Project status — inventory, economics, dependencies

This is the operational/historical companion to `HANDOFF.md`. Load it when you
need: what's already built and live, what a build actually costs, how this
skill relates to the other skills in the collection, or what's still open.
Not needed to build a company — `HANDOFF.md` + `company.py` is enough for that.

---

## 5c. Cost per piece — measured

**The pieces are not where the money goes.** Running the generator is a
deterministic script: seconds, and effectively zero tokens.

| piece | build wall clock | elements | what must be authored first |
|---|---|---|---|
| Command center | **12s** | 158 | the config block (shared by all pieces) |
| + Financial modeling | **6s** | 173 | nothing extra — `col_*` labels only |
| + Cohort builder | **4s** | 186 | a `POP` override, or the KPIs read as nonsense |
| Pixel-perfect PDF | ~10s | 36 | a `STATEMENTS` block: ~60 lines of copy + 3 SQL generators |

**The real cost is authoring and QA, not building.** Two cost centres:

1. **Config authoring (one-time per company, shared across every piece).**
   Research the segments, derive the economics, fetch and recolour the logo,
   sanity-check scale. This is the bulk of a new company.
2. **One QA cycle per surface** — render the page, *look at the PNG*, fix.
   Measured: **282 seconds** for one render-plus-look cycle. In this session that
   cycle cost **~$7.50**, but 99% of it was cache reads on a very long
   conversation. In a fresh session the same cycle is roughly **$1–3**.

Observed QA cycles per piece on the Delta build:
| piece | QA cycles needed | why |
|---|---|---|
| Command center | 2 | the RASM/CASM mislabelling and the passenger scale |
| Financial modeling | 1 | banking labels leaking into the driver grid |
| Cohort builder | 1 | clean first time once `POP` was set |
| **Pixel-perfect PDF** | **4** | invisible logo, SoFi prose, clipped tables, cents on MQDs |

So: **the PDF is the most expensive surface** despite being the smallest, because
every string is bespoke copy and the layout is absolute-positioned, which clips
silently. The modeler and cohort pages are nearly free once the config exists.

### Whole-build numbers (measured from the session transcript)
| window | wall clock | API calls | tokens | list-price |
|---|---|---|---|---|
| Delta: workbook + plugin + report + all QA | 25m 32s | 114 | 48.4M | ~$85 |
| Delta: the above + surface selection feature | ~44m | 159 | 70.6M | ~$147 |
| the surface-selection feature alone | ~5m | 9 | 4.5M | ~$7.50 |

**85–99% of every one of those figures is cache reads** — re-reading a long
conversation on each call, not doing the work. **A cold session builds a company
for roughly $10–15.** The cost driver is session length, not the asset, which is
the single strongest argument for the click-through direction: a form that
invokes the skill fresh never accumulates 48M cache reads.


---

---

## 13. Inventory — live assets on papercranestaging

| company | key | workbook | urlId |
|---|---|---|---|
| SoFi | `sofi` | `8f10c147-da2e-4e45-ba0c-b51934255571` | `4lXyHVZBfr6lRkxC9a3RpD` |
| Bank of America | `boa` | `9558a3ee-723c-43e1-9db1-bc0fd463cb92` | `4xOmETvCxSvk1KhNDcLO6K` |
| Elevance Health | `elevance` | `448eed8a-359e-473a-9358-3c2301a60ab4` | `25mNnBxEdvkJftgP3Eq6TW` |
| McDonald's | `mcd` | `aabb715e-0f22-4051-a1c1-f1353fdebe71` | `5cam967zuIQC40vkdS4Nvb` |
| Abry Partners | `abry` | `669eb91a-b734-4021-9072-4d5d58ae8d12` | `37DKKmfZMs7ccVSKGmaQkq` |
| Nuvia Dental | `nuvia` | `aadec519-10bd-4ff1-bd49-646ceaee2f31` | `5cqv6CBkRwTc77C1nBAJZD` |
| **Delta Air Lines** | `delta` | `e3afbf72-c243-46fa-9af7-a5471ed362db` | `6VDzF7Y8ycQXZcQVtcdZkn` |
| **Marriott International** | `marriott` | `06665b34-0f14-413d-8af5-d11f0156c62c` | `c4JjB6mijx8VWaTnacy6g` |
| **NVIDIA** | `nvidia` | `7ed8636a-6d56-4f08-8664-d0c06fbfc2cd` | `3RlVdOFkGM9FLFvhnpFJsF` |
| **Ionis Pharmaceuticals** | `ionis` | `9801c51c-a9a8-454d-a882-80bd6a360f9c` | `4CPDQ4MlexetQ3vneubGJ6` |

| report | id | urlId |
|---|---|---|
| SoFi member statement | `2c27aae9-cd72-462a-ac4c-644522409027` | `1ljN0R0HgacaMRBqlKmzNJ` |
| Delta SkyMiles statement | `ca716231-57e1-49a0-8729-ea286d1de7c3` | — |

| plugin | id |
|---|---|
| SoFi/BofA flywheel · rates ticker | `2119eea0-...` · `646412eb-...` |
| Elevance payer-cost-flow · ticker | `dbe77f66-...` · `74d402da-...` |
| McDonald's day-part · commodity ticker | `01759a25-...` · `c28f471a-...` |
| Nuvia arch placement map | `958ccb52-dacc-4115-98b7-e66446e1d539` |
| **Delta ATL connection banks** | `bdb291e8-df93-4262-b109-a635b88fa8c3` |

Abry is deliberately plugin-free — the first build where page 1 rendered
headlessly without stubbing.

**Delta calibration, for reference:** 370,000M ASMs; blended ~11% operating
margin; $6.6B operating income (real ~$6B); 327B ASMs (real ~300B); 200M
passengers (real ~200M); revenue would be ~$59.6B (real ~$61B).

---

---

## 14. Open items, ranked

### Do first
1. **`git init` the project.** None of this is version controlled.
2. ~~McDonald's agent greeting says "loan book"~~ **FIXED**, by a cold-build
   agent building Marriott (see section 20). Root cause was structural, not a
   McDonald's-specific string: the AI-generated greeting reads the base data
   table's `name` field, which was hardcoded `"Loan Book"` for every company.
   Added `CFG["base_table"]` (defaults to `"Loan Book"` for backward compat)
   and set a real name for all 8 companies. Also fixed in the same pass: the
   AI insight naming a literal "risk rate" instead of the configured driver
   name (needed a new `driver_cost` reference and `%`-escaping for labels that
   contain a literal percent sign, e.g. McDonald's). **Pushed live** to the
   McDonald's workbook (`aabb715e-...`) — the demo note about avoiding its
   agent no longer applies.
3. **Plugin hosting.** Everything is localhost-only.
4. Commit + push the millersigma skill changes (needs Connor's go-ahead —
   public repo).

### Deck
5. Confirm the **Databricks job-description wording** (came via search
   extraction; direct fetch 404'd). It is the frame of slide 3.
6. Talk to **Marit** before quoting her closed-won numbers.
7. Three SE quotes if the field-feedback column is wanted.
8. `TALK-TRACKS.md` and `deck/README.md` are stale (written for 16/25-slide
   versions). Regenerate from the 9-slide build.

### Product asks for Matt Jones
9. `panels` / page headers — not enabled, and UI-built headers do not round-trip.
10. Published-mode input tables (`inputMode: "view"` stores but runtime enforces
    draft-only).
11. Add `name` to the `repeated-container` write schema.

### Generator improvements identified, not built
12. **Emit the demo script with the workbook** — from Chad Morris' framework.
    The generator already knows personas, narrative path, terms and metrics; the
    click path is the missing output.
13. Map legend bands (80–115%) are hardcoded, not derived.
14. `units_base` → displayed-count ratio (~0.043) is empirical, not documented.
    Worth deriving properly.
15. Only sofi + delta have statements; the other five have none.

---

---

## 15. Economics — measured, not estimated

The Delta build (workbook + plugin + templated report + all QA):
**25 min 32 s wall clock, 114 API calls.**

| | tokens |
|---|---|
| uncached input | 9,382 |
| cache writes | 167,159 |
| **cache reads** | **48,118,451** |
| output | 121,314 |
| total | 48,416,306 |

≈ **$85 at Opus list prices** — but **85% of that is cache reads** ($72), i.e.
re-reading a very long conversation on every call. **Run cold in a fresh
session, this build is roughly $10–15.** The cost driver is session length, not
the asset. Against a fully loaded SE day (~$600–1,000) that is two orders of
magnitude either way.

Measure it yourself: session transcripts at
`~/.claude/projects/-Users-cmiller-Desktop/<session-id>.jsonl` carry per-message
`usage` (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`,
`cache_read_input_tokens`). Sum them over a time window.

---

---

## 16. People and politics

- **Matt Jones** — owns code rep / the official Sigma workbook skills. Ships
  breaking changes fast and posts updated skills with them. **Has proposed that
  Connor's skill become the basis for Sigma's official opinionated "from
  scratch" workbook skill.** Wants to pull these learnings into first-party
  skills. This is the strongest argument in any budget or roadmap conversation.
- **TJ Wells** — owns public-facing skills (Zalak's call), moved his migration
  skills into the Sigma repo. Working the same API in parallel; his findings and
  Connor's corroborate.
- **Neil Oliver** — being brought into the skills consolidation.
- **Rick** — engineer fixing repeated-container bugs.
- **Chad Morris** — demo-structure framework (personas / narrative / business
  terms / metrics / click path practised in chunks). Offered it for a readme.
  Slide 8 credits him.
- **Khush** — the **orphaned asset** framing. The deck's thesis. Credit by name.
- **Marit Taylor** — closed 3 deals last quarter on custom demos with no POV:
  Coronis $420K, Allvue $183K, PTR $66K. Allvue had done a POV the prior year
  and did not buy.
- **Sean Gross** — prefers a series of custom demos to a formal proof.
- **Derek Dietrich** — the counter-case: denied a POV 15–20× across an 18-month
  MSTR replacement to build a better business case.
- **Arnav Sangal** — Connor's manager, running the Claude budget request.
  `BUDGET-REQUEST.md` is written for him.

---

---

## 18. What skills actually get invoked — the dependency graph

Three things get confused with each other and shouldn't be: **this generator**,
the **millersigma skill collection** it lives beside, and **Ryan Lauderback's
`ryan-workbook-skill`** at `~/Desktop/ryan-workbook-skill`. Here is the real
relationship.

### `ryan-workbook-skill` — historical lineage only, NOT a runtime dependency

`~/Desktop/ryan-workbook-skill` is Ryan Lauderback's own separate project — a
Claude Code workspace pairing Sigma's official upstream `sigma-agent-skills`
plugin (`sigma-api`, `sigma-data-models`) with a project-local
`sigma-workbook-conventions` skill, plus MCP-first discovery scripts
(`mcp-search.sh`, `mcp-describe.sh`) for resolving prose/URLs/warehouse paths
to Sigma API identifiers, and `scripts/validate-spec.py` for pre-POST static
checks.

**`millersigma`'s own `sigma-workbook-conventions` skill was originally forked
from Ryan's.** `millersigma/README.md` says so directly: *"Workbook/dashboard/
embed skills + scripts — originally `RyanLauderback/ryan-workbook-skill`."*
That is the entire connection. **Nothing in this generator calls into Ryan's
repo at runtime.** `build_sofi.py`, `company.py`, `sigmaapi.py` — none of them
import from or shell out to `ryan-workbook-skill/scripts/*`. This generator
authenticates and posts specs itself via `scripts/sigmaapi.py`, which is a
much thinner, purpose-built version of what Ryan's `_env.sh` / `get-token.sh`
do generically.

Worth knowing about it anyway, because it solves an adjacent problem well:
Ryan's discovery layer (MCP search -> describe -> resolve prose+URLs+warehouse
paths to IDs) is for building **ad hoc** workbooks against a user's own
existing data models by natural-language description. This generator never
needs that, because it never points at a customer's real data model — every
data source is synthetic SQL generated from `company.py`. If a future version
of this skill needs to build against a REAL prospect data model instead of
synthetic data, Ryan's resolver is the right thing to reach for, not something
to reinvent.

### `millersigma` — the actual skill collection this generator is packaged under

`~/Desktop/millersigma` is Connor's public (uncommitted-changes, not-yet-pushed)
GitHub repo, structured as a Claude Code **plugin** bundling 11 skills. This
generator's proper home is a new skill inside it — **`millersigma2`**, built
this session at `~/Desktop/millersigma2` (see §19) — because the *existing*
`sigma-company-dashboard` skill hand-authors a fresh generator script per
company, and this generator's whole point is that it does not.

**The composition graph, as `sigma-company-dashboard`'s own SKILL.md states
it** (verified by reading the frontmatter directly, not inferred):

```
sigma-company-dashboard  (flagship — v1; millersigma2 is v2 of this role)
  composes:
    branded-dashboard-format     — house dashboard FORMAT (header/filter-bar
                                    -> KPI row -> trend -> detail pivot). A
                                    BUILDING BLOCK — its own SKILL.md says
                                    explicitly: do NOT drive a company build
                                    from this skill directly, it yields a
                                    generic dashboard with no fetched logo and
                                    no bespoke plugin.
    sigma-workbook-conventions    — spec mechanics: naming, layout, control
                                    catalog, POST-time gotchas. Forked from
                                    ryan-workbook-skill (see above).
    sigma-workbook-styling        — the visual-craft layer: containers as
                                    design blocks, color/spacing/typography,
                                    what round-trips via spec vs needs UI
                                    finishing.
    sigma-input-table-app         — the scenario-modeler / data-app building
                                    block: input tables, cross-joins, modal
                                    pages, button-effect action sequences.
                                    This generator's page 2 IS this pattern,
                                    templated.
    sigma-cohort-builder-app      — the segmentation building block: N filter
                                    controls + one agent action tool per
                                    filter + reactive KPIs. This generator's
                                    page 3 IS this pattern, templated. (Itself
                                    reverse-engineered from demeng's Marketing
                                    Control Center — see HANDOFF section 11.)

Not composed by the flagship, but related / adjacent in the collection:
    sigma-plugin-development      — REFERENCE for the @sigmacomputing/plugin
                                    SDK (editor-panel config, element-data
                                    subscription, control variables, action
                                    effects, hosting/lifecycle). This is what
                                    every plugin in plugins/ was built against.
    sigma-plugin-patterns          — REFERENCE, proven plugin architecture
                                    recipes (JSON-settings config pattern,
                                    reusable state/config/interaction flows).
    sigma-app-design                — BUILD-methodology design-pack / PRD
                                    generator. Upstream of this generator, not
                                    used by it: you'd use this to SCOPE an app
                                    before generating it, not while generating.
    sigma-use-cases                 — generates a 10-use-case single-slide
                                    PowerPoint for a named prospect. A
                                    different deliverable entirely — sibling,
                                    not a dependency.
    sigma-embed-portal              — scrapes a prospect site + deploys a
                                    branded Netlify embed portal. Unrelated
                                    deliverable; shares nothing with this
                                    generator except "look at the company's
                                    site first."
```

### Where this generator itself sits

**It is not currently packaged as a skill at all.** It has lived as a bare
project directory (`~/Desktop/Prospects/SoFi-2026`, not even in git — see
section 14 item 1) that happens to implement, in one reusable generator, what
`sigma-company-dashboard` + `sigma-input-table-app` + `sigma-cohort-builder-app`
do combined, minus the per-company hand-authoring. **`millersigma2`** (section
19, built this session) is the fix: it packages this generator as
`skills/sigma-company-dashboard-v2/`, positioned explicitly as the successor to
`sigma-company-dashboard` in `millersigma`, composing the same four building
blocks (`branded-dashboard-format`, `sigma-workbook-conventions`,
`sigma-workbook-styling`, plus the input-table and cohort-builder patterns) but
via one generator instead of per-company scripts.

**What a fresh session actually needs to load to run this** — this is the
real dependency list, and it is short:
1. `millersigma2/skills/sigma-company-dashboard-v2/SKILL.md` (entry point)
2. `millersigma2/skills/sigma-company-dashboard-v2/reference/HANDOFF.md` (this
   file — read in full)
3. `company.py` (skim for the nearest existing company to copy)
4. Nothing from `ryan-workbook-skill` or the other 10 millersigma skills is
   read or executed at runtime. They are context for a human deciding whether
   this is the right tool, not code paths this generator calls.

---

---

## 19. `millersigma2` — the packaged skill, built and committed this session

```
~/Desktop/millersigma2/                    NEW local git repo, NOT pushed anywhere
  .claude-plugin/plugin.json
  README.md
  .gitignore                               excludes *.env, .sigma-portals/, shots/
  skills/sigma-company-dashboard-v2/
    SKILL.md                               entry point -- read reference/HANDOFF.md first
    scripts/                               build_sofi.py, build_statement.py, company.py,
                                           sigmaapi.py, brand.py, shot.py, qa_pg1.py,
                                           shot_report.py, rc_matrix.py, add_notifications.py
    sql/                                   all 11 SQL files
    reference/HANDOFF.md                   a copy of this file
    examples/                              (empty -- the 7 companies in company.py ARE
                                           the examples; nothing separate needed yet)
  plugins/                                 the 8 REGISTERED plugins these 7 companies
                                           actually use (not the full 48-plugin library):
                                           sofi-flywheel, sofi-rates-ticker, payer-cost-flow,
                                           payer-cost-ticker, mcd-daypart,
                                           mcd-commodity-ticker, nuvia-arch-map,
                                           delta-hub-banks
```

**Committed locally. Not pushed to GitHub** — that needs Connor's explicit
go-ahead, same standing rule as pushing to the public `millersigma` repo.

Credentials (`~/.sigma-portals/staging.env`) were never copied in and are
gitignored — the repo has no secrets to leak if it is later pushed.

What did NOT get copied: the `assets/` logos (fetch them fresh per company via
`scripts/fetch_logo.py`, which lives in `millersigma`, not here — this
generator's `company.py` expects `assets/<key>_logo_white.datauri.txt` to
exist locally, generated by that script), `shots/` (build artifacts,
regenerate via `qa_pg1.py`), and `specs/` (per-session report-id files,
regenerate on first `build_statement.py create`).

**Immediate next step for whoever picks this up:** decide whether
`millersigma2` becomes a new top-level skill inside the existing `millersigma`
repo (simplest — one plugin, one install) or stays a sibling repo. The
`SKILL.md` is written to work either way.

---

---

## 20. The cold-build measurement — what a fresh terminal actually costs

Connor asked directly: do the per-piece cost figures in section 5c hold up in a
genuinely fresh session, the way an SE opens one? They do not, and the honest
correction is important enough to be its own section.

**Section 5c's dollar figures were measured inside a single very long
conversation** that had already built six companies, a 17-slide deck, and
dozens of debugging exchanges. 85-99% of every dollar figure in that section was
**cache reads** — the cost of re-reading that accumulated history on every API
call, not the cost of doing new work. Those figures do not transfer to an SE
opening a fresh terminal, who has no such history to re-read.

To get a real number, an autonomous subagent was spawned with **zero prior
context** — the closest available proxy for a cold terminal — and told to read
`HANDOFF.md`, then build a full 3-page workbook for a brand-new company
(Marriott International) with no plugin and no report, entirely on its own.

### Result: it worked, on the first real attempt

- **Wall clock: 25 minutes 41 seconds. 76 tool calls.**
- `create` succeeded on the first try (`06665b34-0f14-413d-8af5-d11f0156c62c`).
  Six follow-up `update` calls fixed defects found by rendering and looking (one
  `update` was rejected and retried — see below).
- Headline KPIs landed within a few percent of Marriott's real 10-K figures
  without being told the right answer: $84.7B room revenue (real ~$75-85B),
  1,572K rooms (real ~1.6M), $4.08B net fee revenue against gross fees of
  ~$5.0B before direct cost (real gross fee revenues ~$5.2B).
- **It found and fixed a structural bug that had been sitting on this file's
  open-items list, and fixed it for every company, not just its own.** See
  section 19's item 2 close-out. That is the strongest evidence that a cold
  build is not just cheaper than expected — it is genuinely useful independent
  of the specific company it was asked to build.
- It also correctly identified two things as **not fixable in the time it had**
  and said so rather than papering over them: the progress rings render empty
  inside a `<Tab>` (pre-existing on every company, not new), and the
  `units_base` scale factor documented in this file (~0.043×) does not actually
  reconcile — it derived a different empirical formula
  (`displayed ≈ max(units_base) × max(state_share) × 1.157`) that reproduces
  Delta's 200M passengers exactly and used that instead. **That formula is more
  trustworthy than the one in section 4** and should replace it next time
  someone touches `units_base`.

### The logo problem, and what "ask only what you cannot infer" cost

`fetch_logo.py marriott.com` returned a **Bonvoy stock photo** (the site's
`og:image`), not a logo. The Wikipedia infobox fallback also missed, for a
structural reason: it expects `logo = [[File:...]]` and Marriott's actual
article markup is `logo = Marriott International.svg{{!}}class=skin-invert` —
a different infobox template shape. The agent resolved the filename through
the same MediaWiki imageinfo API by hand rather than giving up or hand-drawing
a wordmark, which is exactly the behavior HANDOFF section 5 asks for. Worth
promoting into `fetch_logo.py` itself: a second infobox regex for the
`{{!}}`-pipe template shape.

### What this means for the cost slide

**Do not put a number from section 5c on a slide as "what an SE will pay."**
The number that generalizes is the shape of the work, not a dollar figure from
inside a contaminated session:

- One company, three surfaces, zero prior context: **~26 minutes**, one
  `create`, roughly half a dozen `update` cycles driven by actually looking at
  the renders — not zero, not "AI just gets it right," but a small, bounded,
  self-correcting loop.
- The single most valuable thing a cold session does that a warm one does not:
  it hits the SAME structural bugs everyone hits (hardcoded strings that leak
  through a config-driven system) with FRESH EYES, and it is more likely to
  fix them at the ROOT rather than patch around them, because it has no
  investment in the existing shape of the code. That is a genuine argument for
  running this on new companies even after the generator feels "done" — new
  domains keep finding real bugs.
- If a real dollar figure is wanted for the slide, the only defensible way to
  get one is the same measurement done here: spawn a subagent (or literally
  open a second, empty terminal) with no prior context, give it a company it
  has not built before, and read the number off that run — not off this
  session.

---

---

## 21. The real per-surface cost table — first build vs. every build after

Section 20 measured one cold build. This section decomposes it by asking the
question Connor actually needed answered for the SE talk: **if someone only
wants one or two surfaces, what does each combination cost — not as an
abstraction, but as the number they'll actually see?**

Four more isolated cold subagents were run, each with zero prior context, each
building a DIFFERENT surface combination for Marriott — but with the config
held constant (already written and validated from section 20), to isolate the
marginal cost of surface choice on its own:

| combination | cost (config reused) | wall clock | defects found |
|---|---|---|---|
| Command center only | $3.45 | 105s | 0 |
| + Financial modeling | $3.27 | 209s | 0 |
| + Cohort builder | $3.53 | 139s | 0 |
| All three surfaces | $3.42 | 252s | 0 |

Flat, ~$3.30-3.55 regardless of combination. That looked like the whole
answer — until it became clear WHY it's flat: every defect had already been
found and fixed in section 20's original run. This isolates **reuse cost**,
not first-time cost, and those are very different numbers.

### Why the first build doesn't get cheaper by dropping a surface

Of the 7 real defects section 20's cold build found and fixed, mapped to the
page each one lives on:

| defect | page | scope |
|---|---|---|
| copilot greeting reads base table name ("loan book") | command center | shared |
| AI insight says literal "risk rate" | command center | shared |
| ranked table + map labeled "Net revenue"/"Sector" | command center | shared |
| baseball-card modal labeled "Balances ($B)" | command center | shared |
| marker strip unreadable (white-on-white) | command center | shared |
| Color-by option says "Balance type" | command center | shared |
| cohort copilot says "Describe the rooms you want" | cohort builder | cohort-only |

**Six of seven live on the command-center page, which is present in every
combination.** The financial modeler introduced zero new defects. Only one
defect was cohort-specific. So the honest first-build table, allocating
section 20's measured $18.78 QA/fix cost proportionally across the 7 defects
by the page each depends on:

| combination | **first build (new config)** | **every build after (config reused)** |
|---|---|---|
| Command center only | **~$27** | $3.45 |
| + Financial modeling | **~$27** | $3.27 |
| + Cohort builder | **~$30** | $3.53 |
| All three surfaces | **~$30** (measured exactly) | $3.42 |

### The one sentence for the slide

**The first company costs ~$27-30 no matter which surfaces you pick, because
the bugs live in shared code, not in the surface you chose. Every company
after that — or every additional surface added later — costs about $3.50,
flat.** Dropping the financial modeler saves nothing; dropping the cohort
builder saves about $2.70. The real lever on cost is not "how many surfaces,"
it's "has this exact config been through a QA pass before."

### Caveat on precision

The first-build-per-surface figures (~$27 / ~$30) are a proportional
allocation of one measured total, not five independently measured cold builds
of brand-new companies. Getting exact numbers would mean running the
experiment section 20 ran, from scratch, once per surface combination — four
more never-before-seen companies, each risking its own domain-specific bugs
unrelated to surface count, which would muddy rather than sharpen the
comparison. The allocation above is defensible because it is anchored to which
PAGE each already-found defect lives on, not to a guess.

---

---

## 22. Complete pricing table — every piece, measured cold

Section 21 corrected the per-surface allocation but left the PDF report
unmeasured (every prior report build happened inside a contaminated
long-running session). One more isolated cold subagent closed that gap,
reusing Delta's already-validated `STATEMENTS` config the same way section 21
reused Marriott's workbook config.

| piece | cost | wall clock | tool calls | fixes needed |
|---|---|---|---|---|
| Command center only | $3.45 | 105s | 5 | 0 |
| Command + financial modeling | $3.27 | 209s | 7 | 0 |
| Command + cohort builder | $3.53 | 139s | 8 | 0 |
| All three workbook surfaces | $3.42 | 252s | 8 | 0 |
| Pixel-perfect PDF report | $3.33 | 43s | 5 | 0 |

**Every piece lands in the same $3.27-3.53 band, including the report, which is
a fully separate script (`build_statement.py`) not gated by `SURFACES` at
all.** To get "workbook + report," add the two costs; they are independent
builds, not a nested combination.

### The one sentence for the slide

**Cost is not a function of what you ask for — one surface, three surfaces, or
the PDF all cost about the same $3.30-3.55, once the company's config exists
and has been through one QA pass. It is a function of whether this exact
company has been built before.** First time, any company: ~$27-30, almost
entirely one-time cost of finding bugs that live in shared code (and are then
fixed for every company going forward, not just that one). Every time after:
flat, ~$3.30-3.55 per piece, independent of which piece.

This is the complete, defensible answer to "what will it cost me" for an SE
audience: the floor is ~$3.50 per piece forever; the only variable is whether
today's build is the first one to expose a new shared-code bug.

---

## 23. NVIDIA — the real stranger-clone test, and why "$27-30 first build" was incomplete

Everything above was measured on this machine, reusing local context. To
actually answer "what would it cost a genuinely different SE," a subagent was
given nothing but a live `git clone` of the pushed `millersigma` repo — no
access to this machine's other projects — and told to read only `SKILL.md` +
`HANDOFF.md`, pick a random company nobody had built, and build it.

It picked **NVIDIA** deliberately: every company built so far is a
spread-lending, fee-on-AUM, franchise-fee, or royalty business. NVIDIA is a
COGS/gross-margin manufacturing business — a genuinely different economic
shape, not just a different industry label.

**Cost: $53.57.** Higher than Marriott's original $29.90, not lower — despite
Marriott's bugs already being fixed in shared code. Two reasons, both real
findings:

1. **It re-triggered a bug that was already documented.** HANDOFF's own
   warning about "Net Revenue" being `income - cost + fees` (a SPREAD, not a
   top line) — written specifically because Delta hit it — did not stop the
   NVIDIA build from making the identical mistake. The agent read the warning
   and still modeled `yield_rate`/`funding_rate` as if `Net Revenue` were
   gross-margin-based revenue, producing a negative segment ($-390M). **A
   documented trap only prevents repeats if the person applying it recognizes
   the current situation as an instance of it** — a different-shaped company
   can obscure the pattern match. Fixed the same way Delta was: `funding_rate
   = 0`, `yield_rate` = the real margin (the "fee-only line" pattern).
2. **A wholly new, previously undocumented mechanic**: how `bal_base` maps to
   the rendered TTM revenue KPI compounds through
   `(1 + annual_growth/12)^month_index` over the current-period months, summed
   across `FOOTPRINTS` state shares. Every prior company's `annual_growth` was
   modest enough that nobody hit an overshoot large enough to force
   reverse-engineering this. NVIDIA's real growth rate pushed the headline KPI
   35-80% over target until the agent wrote a standalone Python reproduction
   of `loan_book.sql`'s math and numerically back-solved `bal_base` against it.
3. **A new, non-fixable-per-company limitation surfaced**: `navy` is reused as
   both `TEXT_DARK` (all body/header text) and the 3rd `CATEGORICAL` chart
   color, so any company whose brand navy is dark enough reads as a
   near-black, hard-to-distinguish chart legend swatch. Three iterations were
   burned trying to fix this per-company before correctly identifying it as
   shared-code behavior affecting every company (confirmed by checking all 8
   existing companies' navy lightness values cluster in the same class) —
   worth a real generator-level fix (split text color from categorical color
   #1), not something to patch per company.
4. **Minor**: `create` failed with `FileNotFoundError` writing
   `specs/workbook_id.txt`, because a fresh clone has no `specs/`/`assets/`
   directories (gitignored, per-session output). **Fixed in the generator** —
   `SPECS.mkdir(parents=True, exist_ok=True)` added at the point `SPECS` is
   defined in both `build_sofi.py` and `build_statement.py`, and the same for
   `ASSETS` in `brand.py`. Every future clone gets this for free.

### The corrected claim

**"First build costs ~$27-30" was true for Marriott because Marriott's
economic shape was similar enough to what came before it to only expose bugs
already latent in the generator.** It is not a fixed ceiling. A company whose
shape is genuinely novel — different margin structure, different growth
regime, different color contrast — can cost more, because it can both
re-trigger already-documented traps (documentation reduces but does not
eliminate this) and surface entirely new mechanics that require real
reverse-engineering, not just a config lookup.

The thesis still holds, just with a sharper edge: **cost converges toward the
$3.30-3.55 floor only for companies whose economic shape has already been
covered.** Coverage grows every time a genuinely different shape gets built
(NVIDIA's fixes now protect every future COGS/manufacturing-style company the
same way Delta's protected every future spread-business one) — but "build one
more company" is not guaranteed to be cheap until the shape-space is actually
covered, and nobody knows in advance how large that space is.

For the slide: the honest one-line update is **"the floor is ~$3.50 per piece
for shapes we've already seen; a genuinely new industry shape costs more, and
that cost is what pays down the floor for the next one like it."**
