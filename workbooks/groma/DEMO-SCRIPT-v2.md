# Groma NAV REIT — Decision Cockpit (v2) — demo script

Workbook: https://staging.sigmacomputing.io/papercranestaging/workbook/1qli8qN4jMK3uXbS7TLWKr

150 properties · 3,574 units · $1.25B at 100% · $466M REIT NAV · 49% look-through LTV

Four pages, each named after a decision. Verified live on 2026-09-18.

---

## Pre-flight (30 seconds, every time)

Open page **3 · Decide** and confirm the input tables show an **"Edit data"**
button. If they say *Editable in draft* instead, the write-back will throw in
front of the customer — see "If write-back breaks" at the bottom. This setting
is UI-only and is not carried in the workbook spec, so it can be lost on a
rebuild.

**Framing line:** *"Groma's problem isn't a shortage of charts. It's that the
acquisition model doesn't govern how the buildings are actually run, and the
construction remaining lives in somebody's head."*

---

## 1 · Worth — "What is the REIT worth, and can I trust it?"

Four numbers: **REIT NAV $466M**, **NAV protected by the equity method
$11.5M**, **raw TTM NOI (REIT share) $49.6M**, **look-through LTV 49.0%**.

Then the bridge — *How $1.25B of property becomes REIT NAV*:
property value → less debt → less minority → **JV add-back** → NAV.

> **Say:** "Four steps from a billion and a quarter of real estate to the
> number that belongs to shareholders. Watch the fourth bar — it's small on
> this axis and it's worth $11.5M. Seaport Residential JV is an equity-method
> joint venture: the mortgage sits inside the LLC, below the REIT. Pro-rate
> that debt the way you would any other building and you've just erased $11.5M
> of NAV. One holding, one rule."

Then the copilot, on the same page:

> `Why is Seaport Residential JV's REIT debt zero?`

It returns the arithmetic and offers to show what NAV looks like if the in-LLC
debt were incorrectly pro-rated. Take the offer.

Close the page on the **holdings roll-up**: seven LLCs, 150 properties, the
equity-method row highlighted.

---

## 2 · Attention — "Which buildings need me this quarter?"

This is the page a spreadsheet cannot do, and the reason scale matters.

Four exception counts: **15 below their neighbourhood cohort**, **43 over their
recurring capex plan**, **33 still in lease-up**, **2 failing a tie-out**.

The scatter is all 150 properties — NOI margin against value per unit,
coloured by maturity.

> **Say:** "Every building in the book is on this chart. I'm not looking for
> the average, I'm looking for the ones that don't belong. Lease-up assets sit
> low by design — that's fine. What I care about is a seasoned asset sitting
> below its own neighbourhood's cohort."

Filter **Cohort position → Below cohort**, then read the **action queue**,
sorted widest-negative-gap first. Point out that the gap is measured against
the *neighbourhood* cohort, not the portfolio average — Somerville and
Dorchester are not comparable.

> `Which five properties are furthest below their neighborhood cohort?`

---

## 3 · Decide — "Decide and commit" (the centrepiece)

1. Switch **Management scenario**: Current Plan → Lease-up Upside → Cost
   Pressure. KPIs move.
2. Click **Edit data** on *Live Property Budget*.
3. Type a **PM Forecast NOI** into a peach cell. Press Enter. Stop talking.
   Forecast REIT NOI and the value sensitivity both move immediately.
4. Add a workflow comment, click **Submit budget**, then **Approve budget**.
   A row lands in **Budget Approval History** with the real user and timestamp.
5. Scroll to the **15xx Capex Review Queue** (468 lines). Harbor House's
   **$118k roof is recurring**; Maverick Flats' **$94k gut renovation is
   value-add**. Re-tag one in the peach override column and watch the AFFO
   deduction change.

> **Say:** "Dollar size is not the rule — the nature of the work is. A
> six-figure roof keeps units rentable, so it's maintenance. A smaller gut
> renovation changes the unit basis, so it's value-add and it does not hit
> cash. And the number this page deducts is the same number the capex queue
> sums. It's derived from the tagging, not typed beside it."

**Guardrail, say it out loud:** the gold figure is a **management value
sensitivity** for internal steering. It is not the approved quarterly mark and
not the external appraiser's model.

---

## 4 · Prove — "Prove it"

**NOI net tie delta $42,800 · value $0 · debt $0 · 2 properties requiring
review.**

The tie-out table is 150 rows sorted exceptions-first: Broadway Lofts
($24,600) and Hyde Park Flats ($18,200) sit at the top in red with named
reasons; the other 148 are Tied.

> **Say:** "Nothing here rides on one file. NOI is checked against a Buildium
> API pull, value against the NAV tracker, debt against the mortgage control
> centre. 148 of 150 agree to within $500. Two don't, and the workbook tells
> you which invoice batch and which re-keyed property to go look at. A cockpit
> that can only show green isn't a control room."

Finish on the **24-tab lineage** table and the quarterly commit path.

> **Close:** "One refresh, one visible rulebook, one quarterly commit — and
> live property decisions in between quarters."

---

## Do not claim

- That the figures are production Groma / Buildium / loan / NAV data.
- That the management value sensitivity is the external appraiser's model.
- That the workbook is connected to Groma's systems.
- That workbook filters are security or SOX controls.
- That Sigma replaces Buildium, the R valuation model, or the close.
- That address → Buildium ID matching is solved. It is not implemented here,
  and it is the real silent failure point. Saying so is a credibility win.

## If write-back breaks

Symptom: *"Edits can only be made in draft mode."* Fix: Edit the workbook →
click the badge beside each input table → **Editable in published version (all
access levels)** → Publish. `inputMode` in the spec does **not** control this.
Fallback: demo page 3 from Edit mode; everything else works either way.
