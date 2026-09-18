# Groma NAV REIT cockpit — demo script

Workbook: https://staging.sigmacomputing.io/papercranestaging/workbook/2spqOczwpYSanDiTgNhfCK

Everything below was verified live in a real authenticated browser session on
2026-09-18. Where something does not work, it says so.

---

## Before you open your mouth (2 min of setup)

1. Open the workbook in a **published view** (the normal URL, not Edit).
2. Land on **NAV Control Room**.
3. Check the Budget App page shows an **"Edit data"** button next to *Live
   Property Budget*. If it does not, the input-table permission got reset —
   see "If write-back breaks" at the bottom. **Do this check every time**, it
   is the one thing that can silently kill the demo.
4. If you want a clean approval log, the history table will already have rows
   from testing. Either leave them (they look like prior activity, which is
   realistic) or clear them in Edit mode first.

**The one-line framing:** *"Groma's problem isn't a shortage of charts. It's
that the acquisition model doesn't govern how the buildings are actually run,
and the construction remaining lives in somebody's head."*

---

## 1. NAV Control Room — trust the number (3 min)

Read the four KPIs left to right: REIT NAV **$67.4M**, raw TTM NOI (REIT share)
**$6.91M**, cash contribution (REIT share) **$4.56M**, look-through LTV
**43.8%**.

Then go straight to the **Holdings scorecard** and put your finger on the
**Seaport Residential JV** row:

- Ownership **43%**
- 100% debt **$26.8M**, but **REIT Debt $0**
- REIT Equity **$20,425,000** = REIT Value
- Treatment pill: **"Equity method — in-LLC debt excluded"**

> **Say:** "Every other building here is consolidated, so we take our
> ownership share of the mortgage. This one is an equity-method JV — the
> mortgage sits inside the LLC, below the REIT. If you pro-rated that
> $26.8M the way you would any other property, you'd double-count a
> mid-eight-figure balance and understate NAV. This single rule is the whole
> difference between a naive property split and the right fund number."

**Then let the AI make the point for you.** In the copilot on the right, ask:

> `Why is Seaport Residential JV's REIT debt zero?`

It comes back with the arithmetic ($0 not 43% × $26.8M, equity = value because
there is no REIT-side debt to net) and *offers* to show what NAV would look
like if the in-LLC debt were incorrectly pro-rated. Take it up on that offer.
That is the strongest 30 seconds in the demo: the rulebook is not buried in
someone's R script, it can explain itself.

---

## 2. Property Scorecard — understand the building (3 min)

Read the cash ladder left to right on one row:
Buildium income → Buildium expense → **master rent allocation** → raw NOI →
cash interest → recurring capex → REIT share.

Point at **Broadway Lofts** and **Dudley Terrace** — treatment
*"Consolidated — master rent allocated"*, with a non-zero Master Rent
Allocation column.

> **Say:** "These two book rent on the entity while the offsetting
> master-tenant rent expense sits somewhere else. A naive account sum
> overstates their NOI. We allocate it explicitly, and — this matters — the
> independent check on the Controls page uses the same allocated basis, so we
> don't produce fake exceptions."

Note there are **no normalizations and no add-backs**: NOI is raw
Buildium income minus expense. Any divergence is a data problem, fixed at the
source.

---

## 3. Property Budget App — act in the live system (5 min, the centerpiece)

This is the page that makes it a data application rather than a dashboard.

1. Switch **Management scenario**: Current Plan → Lease-up Upside → Cost
   Pressure. The three KPIs and the property chart move.
2. Click **"Edit data"** on *Live Property Budget*.
3. Type a **PM Forecast NOI** into the peach cell for one property — e.g.
   `900000` on Centre Street Homes.
4. Press Enter and stop talking for a second.

**Verified effect:** Forecast REIT NOI goes **$6.91M → $7.25M** and Management
value sensitivity goes **$132M → $138M**, immediately, in the published
version.

5. Type a workflow comment, click **Submit budget**, then **Approve budget**.
   A row lands in **Budget Approval History** with the real user email and a
   real timestamp.

> **Say:** "The property manager's forecast is now a governed input, not an
> email attachment. Leadership sees the portfolio impact the moment it's
> typed, and there's a user and a timestamp on the decision."

**Guardrail you must say out loud:** the gold KPI is a **management value
sensitivity**, not the approved mark and not the external appraiser's model.
The approved quarterly value stays on NAV / Controls. If you call it "NAV" you
have re-created the orphaned-spreadsheet problem you're there to solve.

Also worth saying: blank overrides fall back to scenario-scaled actuals, so a
PM can touch one building without retyping the book.

---

## 4. Capex Review — govern the judgment (3 min)

Three KPIs: capex reviewed **$2.53M**, recurring / AFFO deduction **$1.62M**,
value-add **$911k**.

The contrast is the demo:

- Harbor House **roof membrane $118,000 → Recurring** (it keeps units rentable)
- Maverick Flats **unit gut renovation $94,000 → Value-add** (it changes the
  unit basis)

> **Say:** "Dollar size is not the rule. The nature of the work is. A
> six-figure roof is maintenance; a smaller gut reno is value-add. Only the
> recurring side is deducted to reach cash contribution and AFFO."

Then re-tag one line in the **Manual Class Override** peach column and show the
cash/AFFO effect move. Point out the `$2,500` auto-floor rows and the
**Rule Reason** column — the classification always shows its reasoning.

**Say this too, because it is the credibility line:** the $1.62M recurring on
this page *is* the number deducted on the Property Scorecard. It is the same
figure, derived from these lines — not typed twice.

---

## 5. Controls & Lineage — prove it (3 min)

Four KPIs: NOI net tie delta **$24,600**, value delta **$0**, debt delta
**$0**, **properties requiring review: 1**.

Scroll the tie-out table to **Chelsea Commons** — status **Review** in red,
with a Break Reason: *"Buildium API pull missing a June maintenance invoice
batch — reconcile at the source, do not adjust the workbook."*

> **Say:** "Every important number is checked against a second, independent
> source — NOI against a Buildium API pull, value against the NAV tracker,
> debt against the mortgage control centre. Eleven properties tie to within
> $500. One doesn't, and it tells you why and where to go fix it. A cockpit
> that can only ever show green isn't a control room."

Ask the **Tie-out Copilot**: `Which properties require review and why?`

Close on the 24-tab lineage map: every decision surface has a named direct
source and rolls up from the same Layer 1 property-quarter dataset.

> **Close:** "One refresh, one visible rulebook, one quarterly commit — and
> live property decisions in between quarters."

---

## What you must NOT claim

- That the figures are production Groma / Buildium / loan / NAV data. They are
  deterministic synthetic records shaped to the June 30 2026 spec.
- That the management value sensitivity is the external appraiser's model.
- That the workbook is connected to Groma's systems.
- That workbook filters are security or SOX controls.
- That Sigma replaces Buildium, the R valuation model, or the close.
- That address → Buildium ID matching is solved. It isn't implemented here,
  and it is the genuine silent failure point in a real build. If it comes up,
  say so — it's a credibility win, not a loss.

---

## If write-back breaks

Symptom: clicking **Submit budget** throws *"Error in Insert row(s) into
'Budget Approval History' — Edits can only be made in draft mode."*

Cause: the input table's **Data entry permission** reverted to *"Editable in
draft"*. This setting is **UI-only** — it is not in the workbook spec, so any
code push can leave it behind and you cannot set it from the API.

Fix (60 seconds):

1. **Edit** the workbook.
2. On the Budget App page, click the badge next to *Live Property Budget*, then
   the one next to *Budget Approval History*.
3. Choose **"Editable in published version (all access levels)"**.
4. Do the same for the *15xx Capex Review Queue* on the Capex page.
5. **Publish**.

Note: `inputMode: "view"` in the spec looks like it does this. It does not.

## Fallback if it still won't write

Demo the Budget App from **Edit** mode — inserts succeed there. Scenario
switching, the peach-cell recalculation, the capex re-tag, and every agent all
work regardless, so you still have steps 1, 2, 4 and 5 intact.
