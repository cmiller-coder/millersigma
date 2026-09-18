# Claude brief — Groma NAV REIT cockpit

Use this as context before editing, demoing, or extending the Groma Sigma
workbook. Prefer this file over inventing a new architecture.

## What this asset is

A Papercrane staging Sigma workbook that proves Sigma can reproduce Groma's
REIT cockpit **faithfully**, not just quickly.

Groma's explicit fear: a tool that treats every property the same will be
**fast and wrong** on the equity-method JV, master leases, and capex split.

Live workbook:

- URL: https://staging.sigmacomputing.io/papercranestaging/workbook/2spqOczwpYSanDiTgNhfCK
- Workbook ID: `50c50986-7e82-4f6a-8575-d387a118dbe6`
- Builder: `workbooks/groma/build_groma.py`

Source of truth for the rules is the uploaded REIT Cockpit Blueprint
(figures as of 2026-06-30). Layer 3 (external appraiser market / cap-rate
model) is **out of scope**.

## Business problem we designed against

Current state:

- R-coded valuation runs quarterly on large CSVs, then a human sense-check.
- Acquisition model lives in a spreadsheet disconnected from daily work.
- Construction budget is split across 5+ files.
- Property managers see the model once and forget it.
- CEO answers require stitching Buildium, Sheets, and Claude.
- No live budget vs actuals, no accessible historical valuation database.

Desired state:

- Property managers enter data in a live system.
- Leadership sees operating, construction remaining, and valuation context
  immediately.
- One governed Layer 1 property-quarter dataset feeds every decision tab.

The demo therefore has to show **governed numbers**, **special-case
accounting**, **writeback**, and **tie-outs** — not a pretty dashboard of
identical properties.

## Why we did not build 24 pages

The blueprint has 24 Layer 2 tabs. A 24-page Sigma clone would fail a sales
demo: too much navigation, no through-line, and it would look like a report
port rather than a system.

Instead:

1. One Layer 1 grain (property × quarter).
2. Five decision pages that unlock the jobs of those 24 tabs.
3. A complete 24-tab lineage table on Controls so Groma can see nothing was
   dropped.

Mapping:

| Blueprint group | Demo page | Why this page exists |
|---|---|---|
| Dashboard, REIT NAV & Holdings, SREO | NAV Control Room | Trust fund NAV, REIT share, leverage, JV exception |
| Portfolio, Property Cash Flow, Operating Scorecard, REIT Drivers | Property Scorecard | Show the cash ladder and special treatments at building grain |
| Budget vs actuals, open Budgeted Capex question, Process | Property Budget App | The “data application” — PMs write, leadership sees |
| Capex Review, Capex Transactions | Capex Review | Nature-based tagging with persistent overrides |
| Sources & Open Items, Policy, Process | Controls & Lineage | Second-source tie-outs + 24-tab map + quarterly commit path |
| CAD, Dividend, Capital Allocation, Debt, Peers, Fund Performance | Named on the 24-tab map, not full pages | Honest: not enough production sources to fake those well |

Do **not** expand to 24 pages unless Groma asks. If they ask, add pages that
still read Layer 1; do not fork new math.

## Why synthetic data, not invented “production”

The two named CSVs were never supplied:

- `groma_layer1_property_quarter.csv`
- `groma_capex_transactions.csv`

So the SQL in `build_groma.py` is **deterministic synthetic** Boston-scale
residential inventory. Every page banner says that.

Do not:

- relabel it as Groma production
- invent real investor, tenant, or loan identifiers
- “fix” numbers to match an unpublished NAV file

When real files arrive, replace the SQL VALUES blocks and keep the same
column names, formulas, and special-case flags.

## The five accuracy rules — and how they show up

These are the whole point. The math is arithmetic. The value is in joins,
classification, and ownership.

### 1. NOI is raw

`Raw NOI = Buildium TTM income − Buildium TTM expense − explicit master-tenant allocation`.

No occupancy add-backs, no “normalized NOI”, no plugs. The Property
Scorecard reads left to right so a finance user can see the formula without
opening SQL.

### 2. REIT share = × ownership %

Every REIT column is `100% figure × quarter-specific ownership`. The demo
uses one report quarter (Q2 2026). Do not hard-code a single fund-wide
percentage.

### 3. Equity-method JV (material)

One holding is **not** a consolidated building. Mortgage sits **inside the
LLC**.

Correct:

- `REIT Debt = $0`
- `REIT Equity = REIT Value = 100% value × equity-method rate`

Naive (wrong):

- `REIT Debt = 100% debt × ownership %` → double-counts mid-eight-figure
  debt and understates NAV.

Demo object: **Seaport Residential JV** / Harbor Equity JV LLC.

- 100% debt ≈ $26.8M
- Ownership 43%
- REIT debt **$0**
- Accounting treatment pill: `Equity method — in-LLC debt excluded`

This is the first click of the demo. If you “simplify” it away, the
workbook no longer answers Groma.

### 4. Master-lease properties

A few buildings book rent on the entity while offsetting master-tenant rent
expense sits elsewhere. A naive account sum **overstates NOI**.

Demo objects: **Broadway Lofts**, **Dudley Terrace**.

They carry a non-zero `Master Tenant Expense` and treatment
`Consolidated — master rent allocated`.

The independent API tie-out must use the **same** allocated NOI basis. An
earlier bug subtracted master rent twice on the check side and produced
false Review flags. Do not reintroduce that.

### 5. Capex classification is nature-based

Recurring vs value-add is **not** dollar size.

Rules encoded in the transaction queue:

- Description (roof / life-safety / envelope → recurring; gut reno /
  amenity / reconfiguration → value-add)
- Auto-recurring floor at **$2,500**
- Manual picks that persist across republish

Demo contrast:

- Harbor House roof membrane **$118k = Recurring** (keeps units rentable)
- Maverick Flats unit gut reno **$94k = Value-add** (changes unit basis)

Only recurring hits cash contribution / AFFO deduction. Value-add is shown
but not deducted. Peach override cells exist so a reviewer can re-tag a
line and watch the headline move.

## Why the Budget App is the center of the Sigma pitch

Groma’s gap is not “need more charts.” It is that the acquisition model
does not govern how buildings are run, and construction remaining lives in
someone’s head.

The Budget page is the data-application:

- Peach cells: PM forecast NOI, revised capex budget, owner, note, status
- Scenario control: Current Plan / Lease-up Upside / Cost Pressure
- Live KPIs: forecast REIT NOI, capex remaining, **management value
  sensitivity**
- Submit / Approve buttons write user + timestamp + comment into
  `Budget Approval History`

Blank overrides fall back to scenario-scaled Layer 1 actuals via
`Coalesce(...)`. That is intentional: a PM can touch one building without
retyping the book.

**Critical wording:** the gold KPI is a **management value sensitivity**,
not the approved mark and not Layer 3. Approved quarterly value stays on
NAV / Controls. If you rename that KPI to “NAV” you recreate the orphaned
spreadsheet problem.

## Why drawers, not just grouped tables

Groma asked for drillable columns and an app-like flow. Selecting a
property on NAV charts, holdings, the cash ladder, or the budget chart
opens a drawer with:

- Buildium ID (canonical key)
- accounting treatment
- 100% vs REIT blocks
- tie status
- the JV rule in plain language

Do not remove the drawer to “clean up the spec.” The demo line is: the
headline and the exception live on the same object.

## Why conditional formatting is loud

Finance users trust exceptions they can see.

- Gold / peach = judgment or editable
- Green Tied = primary and independent source agree within $500
- Red Review = break (should currently be empty after the master-lease
  check fix)
- Equity-method and master-lease treatments are highlighted so they cannot
  be skipped in a scroll

Do not mute this into a grey theme. The product story is “visible config,
not buried in R.”

## Why tie-outs are a whole page

Blueprint rule: no important number rides on one file.

| Figure | Primary | Independent check |
|---|---|---|
| NOI | Income-statement TTM (raw) | Buildium API check |
| Property value | Current Qtr Approved Value | NAV tracker |
| Debt | Loan database | Mortgages Control Center |

The demo currently ties all properties after the master-lease check fix.
Keep at least one **path** to surface a break (status column + count KPI)
even if the synthetic book is clean. A cockpit that can only show green
is not a control room.

## Demo path (keep this order)

1. **NAV** — read $ NAV, REIT NOI, cash, LTV. Click Seaport Residential JV.
   Line: treating every property identically is fast and wrong.
2. **Properties** — walk income → expense → master allocation → raw NOI →
   interest → recurring capex → REIT %. Point at Broadway Lofts / Dudley.
3. **Budget App** — switch scenario, type one peach forecast or capex cell,
   Submit then Approve. Line: the model now governs daily work.
4. **Capex** — $118k roof vs $94k reno. Override a class. Line: nature, not
   size.
5. **Controls** — $0 / $0 / $0 deltas, then the 24-tab map. Close: one
   refresh, one rulebook, one quarterly commit, live decisions between
   quarters.

Full spoken script: `workbooks/groma/DEMO-SCRIPT.md`.

## What you must not claim

- Synthetic figures are production Groma / Buildium / loan / NAV data.
- The management value sensitivity is the external appraiser model.
- The workbook is connected to Groma systems.
- Workbook filters are security or SOX controls.
- Sigma replaces Buildium, the R valuation model, or close.
- Address→ID matching is solved. Canonical key is Buildium ID; financial
  exports in production key on **normalized address**. That hop is the
  silent failure point and is **not** implemented here because we have no
  ID-less IS export.

## Technical constraints (do not fight the API)

- Workbooks-as-code: `POST/PUT /v2/workbooks/spec`. Verify before create.
- Snowflake SQL connection ID is the same Papercrane sample used by
  Archtop: `a9d45cfe-ff65-4515-8193-a7072602a1ee`.
- `visibleAsSource` is data-model only. Do not set it on these tables.
- Chart color channels cannot reuse an x-axis column; use a dedicated
  `*-color` column.
- Drawers do not accept `position`; they anchor trailing-edge.
- Linked input tables ignore `order` for source keys; hide unused keys so
  peach fields appear first.
- Insert-row actions use `tableElementId`.
- Text `verticalAlign` is `center` / `middle` only.
- `PUT` needs current `latestVersion` as `--expected-version`.
- Empty `POST /spec` bodies can return 200 with no JSON; persist
  `workbookId` from a follow-up list/get.

Do not copy Archtop Fiber branding, FCC pages, or telecom SQL into this
workbook. That is a different deal.

## Files

| File | Role |
|---|---|
| `workbooks/groma/build_groma.py` | Spec + publish CLI |
| `workbooks/groma/README.md` | Operator notes + IDs |
| `workbooks/groma/DEMO-SCRIPT.md` | Spoken demo |
| `workbooks/groma/workbook_id.txt` | Staging ID |
| This file | Decision record for Claude |

PR: https://github.com/cmiller-coder/millersigma/pull/11
Branch: `cursor/groma-reit-cockpit-7d37`

## Open items if you continue the work

1. Swap synthetic VALUES for real Layer 1 / capex CSVs when provided.
2. Implement address-normalize → Buildium ID join and entity-suffix traps
   once an ID-less income statement exists.
3. Interactive UI verification (drawers, peach cells, Submit/Approve)
   requires Sigma SSO; API PNG export only proves render + SQL compile.
4. Do not recreate workbook `51ed4fcb-6e58-424e-a611-5039c8812128`; it was
   a duplicate and was deleted.
5. CAD, dividend, debt maturity, and peer comps remain map-only until
   fund refs / loan / Green Street inputs exist.
6. Budgeted Capex and Capex Vault are still open definitions in the
   blueprint; the Budget App treats budget as an **editable** per-property
   input, which is one of the blueprint’s candidate answers.

## If asked to change it

Preserve, in order:

1. Special-case accounting (JV, master lease, nature-based capex, raw NOI,
   ownership %).
2. One Layer 1 grain.
3. Writeback on budget and capex judgment.
4. Independent tie-outs.
5. Explicit synthetic disclaimer.

Everything else (theme, page count, extra charts) is secondary.
