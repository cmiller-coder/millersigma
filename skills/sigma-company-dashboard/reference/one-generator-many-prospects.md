# One generator, many prospects

A prospect dashboard is worth building twice as fast the second time. The way to
get there is to keep **layout universal and language configurable**, so
retargeting is a config edit rather than a rebuild.

Proven across three live builds from a single generator: SoFi (consumer
fintech), Bank of America (universal bank), Elevance Health (healthcare payer).

---

## The split

**Universal** — never changes between prospects:
page structure, persona tabs, KPI band, alert rail, product-card grid, the
baseball-card modal, the cross-join scenario modeler, agent wiring, and the SQL
*shape*.

**Per-prospect** — one dict:

```python
COMPANY = {
    "key": "elevance",
    "name": "Elevance Health",
    "title": "Membership & Medical Cost Command Center",
    "unit_noun": "member",
    "logo_domain": "elevancehealth.com",
    "palette": {"navy": ..., "primary": ..., "mint": ...},
    "products": [  # name, order, type, volume, yield, cost, fee, provision,
                   # risk, opex_ratio, growth, units, phase, tagline,
                   # rate_label, goal_pct, status
        ("Medicare Advantage", 2, "Fully insured", 28600, .1104, .0961, 38.0, ...),
    ],
    "subs": {"Medicare Advantage": [("MAPD HMO", .512, -30, 9.2, "Ahead"), ...]},
    "alerts": [("critical", "Medical loss ratio breach", "...", "31m ago",
                "Actuarial", 380, "bps over target")],
}
```

## Generate the SQL, don't author it

Hand-written per-prospect SQL is where consistency dies. Generate every table
from the same product constants so the P&L reconciles by construction:

```
volume x yield - volume x cost + fees - provision - opex  ==  headline KPI
```

If the card grid and the KPI band are generated from one list, they cannot
disagree — and the first analyst in the room checks exactly that.

Files that are pure config (`product_cards`, `notifications`, `product_skus`)
get emitted whole. Files with real logic (`loan_book`, `scenario_base`) keep a
`__PRODUCTS__` substitution point for the constants CTE.

## Domain language is a SECOND config

This is the part that is easy to miss and the most visible when wrong. The
schema templates cleanly; the **words do not**. A payer has no "Finance" tab and
no "Avg balances".

```python
LABELS = {
    "elevance": {
        "personas": ["Executive", "Actuarial"],
        "modeler_page": "Trend & Pricing",
        "shock_label": "Medical cost trend shock (bps)",
        "kpi_volume": "Member months (K)",
        "driver_risk": "Denial overturn rate",
    },
}
```

Anything a human reads — tab names, page names, KPI labels, driver labels, the
shock control, agent instructions — comes from here. **Feed the agent the real
product names too**, or a health insurer's copilot will offer to explain Credit
Card delinquency.

## Cross-industry mapping

The economics translate because the *shape* of the question is constant. Only
the nouns move:

| Generic slot | Bank | Healthcare payer | Oil & gas refining |
| --- | --- | --- | --- |
| product | line of business | benefit plan | refinery / crude grade |
| volume | avg balances | member months | throughput (kbd) |
| yield | asset yield | premium PMPM | crack spread |
| cost | cost of funds | medical cost PMPM | feedstock cost |
| spread | net interest margin | **medical loss ratio** | refining margin |
| risk | delinquency | denial overturn rate | unplanned downtime |
| shock | +50 bps parallel | medical trend bps | $/bbl crack spread |

The scenario modeler needs **no change at all** — a rate shock and a medical
trend shock are the same cross-join against the same editable driver grid.

## What does NOT template

- **The bespoke plugin.** A balance flywheel is a lending metaphor. Each
  industry wants its own visual, and that is authored, not configured. Say so
  out loud — it is the honest boundary of the approach.
- **Number magnitude.** Format strings tuned to one company's scale break on
  another: BofA's trillions rendered as `$1,050.00` under a billions format.
  Derive the format from magnitude, or set it per config.

## Traps found the hard way

**Never blanket-rename a label string.** Replacing `"Members (K)"` everywhere
also renamed the *SQL column*, and the build failed with
`Dependency not found: 'custom sql/clients (k)'`. Display labels are config;
underlying column names are fixed contract.

**Regenerating destroys UI-built work.** Page headers (`panels`), true repeated
containers and API actions are UI-only, and a full spec `PUT` wipes them. Either
build those last, or work additively off `GET /spec`.

Worked reference: `~/Desktop/Prospects/SoFi-2026/scripts/company.py`.


---

# The actual workflow: one company name in, whole app out

The user types **"McDonald's"**. That is the entire input. Everything below is
your job, not theirs — do not make them specify a schema.

## 1. Ask only what you cannot infer

Two questions, via `AskUserQuestion`, and nothing else:

- **Which surfaces?** Command center only, or plus a scenario modeler, plus a
  cohort/segment builder. (Drives how many pages.)
- **Demo org or prospect org?** Feature availability differs — headers, repeated
  containers and API actions are UI-only, so a prospect org may not have them.

Everything else you derive. Do **not** ask for products, colours, metrics or
KPI names — inferring those is the value of the skill.

## 2. Derive the config

Write a `company.py` entry from what you know about the business:

| Field | How to derive it |
| --- | --- |
| `products` | Their real reporting segments. McDonald's → US, International Operated, International Developmental License. A bank → lines of business. A payer → benefit plans. **Use their actual 10-K segment names** — this is the single biggest credibility lever. |
| `bal_base` | The volume the P&L scales with: system-wide sales, average balances, member months, throughput. |
| `yield_rate` / `funding_rate` | Whatever spread drives their margin: royalty rate vs company-operated cost, asset yield vs cost of funds, premium PMPM vs medical cost PMPM. |
| `unit_noun` | member / client / guest / patient / subscriber. |
| `palette` | Sample from the fetched logo — do not guess hexes. |
| `alerts` | Five operational alerts a real operator in that industry would see this morning. Specific beats plausible: "2,140 authorizations past the 72-hour standard" not "high volume detected". |
| `LABELS` | Persona names, page names, KPI labels, shock control. A payer has no "Finance" tab; it has Actuarial and Trend & Pricing. |

Sanity-check the scale against public figures before building. A number that is
off by 100x is the thing the room notices.

## 3. Pick the plugin yourself

The bespoke plugin is the one thing that does **not** template — choose it from
the industry, do not reuse the last one:

| Industry | Ticker strip | Hero plugin |
| --- | --- | --- |
| Banking / fintech | Live Treasury yields (CORS-open) | Balance flywheel — deposits fund lending |
| Healthcare payer | Medical cost trend | Premium-vs-medical-cost flow, MLR by plan |
| Restaurant / retail | Commodity or traffic index | Day-part heatmap, store performance grid |
| Oil & gas | Crude / crack spread | Refinery throughput or crude-flow map |
| Airline | Jet fuel price | Route profitability map |

Reusing a lending flywheel on a health insurer is the tell that it is a
reskinned template rather than a build.

## 4. Build, lint, render, look

`create` → run the layout linter → render to PNG → **actually look at the
image** → fix. The render step catches nearly everything; skipping it is how
silently-collapsed elements ship.

## What still needs a human

Say these out loud rather than pretending otherwise:

- **Page headers, true repeated containers, API actions and published-mode input
  tables** are UI-only and are destroyed by the next full `PUT`. Do them last.
- **The hero plugin** is authored per industry.
- **Number formatting** must match the company's magnitude — billions vs
  trillions is a real break, not a nit.
