# Barton POC — Finance Demo Talk Track

**Audience:** Finance & operations leaders  
**Duration:** ~20 minutes (15 min demo + 5 min Q&A)  
**Workbook:** **Barton Margin Tracker** (standalone — use this one)  
**URL id:** `0Gv0MxZH1k13nlbfE8XUQ` (open from Sigma → My Documents, or ask for the full link)

Legacy multi-tab POC (`POC Test`) also has a Margin Tracker tab; prefer the standalone workbook for finance demo.
**Data:** `ASSIGNMENT_POC_TEST` (prod assignments, bill/pay rates, LOA)  
**Revenue formula:** Bill Rate × Assignment LOA × 8  

---

## Before you start (30 sec)

> "This is a proof-of-concept in Sigma — same Snowflake data you’d use in production, but with interactive apps on top instead of static Domo dashboards or spreadsheets. Everything you’ll see is live on your assignment data; filters and writeback work in the browser."

**Tab order for the demo:**  
1. Assignment Overview → 2. Margin Tracker → 3. Pipeline Forecast → 4. Assignment Detail (optional)

---

## 1. Assignment Overview (~4 min)

**Open:** *Assignment Booking & Pipeline*

### Talk track

> "Finance usually asks three questions first: **how much booked**, **what’s the pipeline**, and **is it getting better or worse**. This page answers all three in one place."

**Point to KPI row (top):**

> "Each tile shows the current value **and the delta vs last month** — green up, red down — so you’re not hunting for context in a second report."

**Point to switchers (Date grain / Date basis / Trend metric):**

> "You control the time lens without IT. **Created date vs start date** matters for finance when you’re reconciling to when revenue was booked vs when work begins. **Trend metric** flips between bookings count, contract dollars, and cancellations — same chart, different question."

**Click tabs — Volume trend → Rates & geography → Cancellations:**

> "We grouped charts into tabs so the page isn’t a wall of noise. Executives get the trend first; analysts drill into specialty, state, and cancel patterns."

### Finance hook

> "This replaces the monthly Excel pack for the ‘what happened’ conversation. Period comparisons are built in — no VLOOKUP to last month."

---

## 2. Margin Tracker (~6 min) — **Lead with finance**

**Open:** *Placement Margin & Bill-Rate Tracker*

### Talk track

> "This is the use case finance told us hurts most: **bill rate, pay rate, and margin live in spreadsheets**, and low-margin deals show up after close. Here, margin is calculated on every placement from your bill and pay rates and LOA — same formula you confirmed: **Bill × LOA × 8** for contract value."

**Point to hero KPI — Avg Placement Margin %:**

> "Hero metric is **average margin percent** with month-over-month delta. Total gross margin, bill, and pay are right beside it so you can see *why* margin moved — rate change vs mix."

**Point to Low-Margin Placements KPI + threshold switcher (10% / 15% / 20%):**

> "Finance sets the **low-margin threshold** — 15% default, click 10 or 20 for sensitivity. The counter updates instantly. This is your exception queue before payroll and commission runs."

**Tab: Margin overview**

> "Trend of **gross margin dollars** over time, then margin % by specialty. You’ll often see one specialty dragging the average — that’s a pricing or pay conversation, not a reporting problem."

**Tab: Low-margin placements**

> "Every flagged placement: assignment number, specialty, bill, pay, spread, contract value, margin dollars and percent. **Margin Status** shows Low vs OK — sort by margin % to work the exception list finance would have built manually in Excel."

**Tab: Rate adjustments**

> "When finance finds a rate error, they **log the correction here** — assignment, field, original vs adjusted rate, reason. Sigma captures **who and when** automatically. That’s your audit trail; in production this can write back to Snowflake."

**Tab: Commission splits**

> "Same pattern for **commission split approvals** — recipient, split %, draft vs approved. Stops the side spreadsheet that payroll chases every month."

### Finance hook

> "One app: **see margin, flag exceptions, log fixes, approve splits**. Domo shows the chart; Sigma lets finance *work* the exceptions."

---

## 3. Pipeline Forecast (~5 min)

**Open:** *Pipeline Forecast*

### Talk track

> "Overview and margin are backward-looking. Finance also needs **‘what if’** — pipeline changes, rate moves, cancel risk. This is the scenario modeler."

**Point to scenario KPIs (Projected Contract Value with Δ vs baseline):**

> "Pick **Base Case** — drivers auto-seed from pipeline pressure — or **Create scenario** for leadership review. Projected contract value and margin update with **delta vs baseline** on every tile."

**Tab: Impact**

> "Charts show baseline vs projected by specialty, plus variance bars. The **period trend KPI** ties back to the same date controls on Overview."

**Tab: Drivers → edit a cell (if pre-seeded):**

> "Finance or FP&A can change **booking growth, bill rate, pay rate, cancel rate** per specialty. No export to Excel, no version 14 of the model."

**Submit for approval → Approve:**

> "Scenarios go through **submit and approve** — same workflow you’d use for board or leadership sign-off. Submissions log on the Approval tab."

### Finance hook

> "This is **Test Case 4** from the POV: pipeline finance + governed scenarios. With a GL feed added later, you reconcile operational pipeline to recognized revenue in the same workbook."

---

## 4. Assignment Detail (~2 min, optional)

**Open:** *Assignment Pipeline & Detail*

> "Analysts live here — specialty × status pivot and row-level detail. Tabs keep the pivot and the detail table from competing for space."

---

## Honest POC caveats (say these proactively)

| Topic | What to say |
|--------|-------------|
| **Commission math** | "Splits are captured and approved here; payroll calculation rules would connect in phase 2." |
| **GL / recognized revenue** | "Contract value is operational (bill × LOA × 8). Recognized revenue needs your finance actuals — we’d add a reconciliation input table next." |
| **Recruiter / req data** | "Not in this POC table — redeployment and req boards need ATS fields." |
| **Domo comparison** | "Domo showed static views. Sigma is the same Snowflake data with **filters, comparisons, scenarios, and writeback** in one governed app." |

---

## Q&A prep — likely finance questions

**Q: Can we export to Excel?**  
> "Yes — any table or chart exports. The goal is you don’t need to for the weekly review."

**Q: Does this write back to Snowflake?**  
> "Input tables are enabled in this POC; production would map adjustments and approvals to your gold layer with audit columns."

**Q: Who can see what?**  
> "Sigma inherits Snowflake RBAC; row-level security by specialty or region is standard in rollout."

**Q: How is margin calculated?**  
> "(Bill − Pay) × LOA × 8 at the assignment level; margin % = margin ÷ contract value. Same as your spreadsheet, but on 90k+ rows in real time."

**Q: What would you build next?**  
> "1) GL reconciliation page, 2) commission calc export, 3) period targets with off-track flags for monthly finance review."

---

## One-liner close

> "You’ve got **operational dashboards with period comparisons**, a **margin exception workflow** finance can run without Excel, and a **scenario model with approval** — all on one Snowflake dataset, branded and ready for your team to stress-test today."

---

## Deploy / refresh (internal)

```bash
python3 workbooks/barton/build_margin_workbook.py   # creates/refreshes standalone workbook
python3 workbooks/barton/add_margin_page.py       # patches Margin tab on POC Test only
```
