# Archtop Fiber demo flow

Audience: Rob's FP&A team plus Devin / IT. Keep the workbook portion to about
25 minutes and lead with the workflow, not platform architecture.

## 1. FP&A Control Room — 8 minutes

Open here.

1. Establish the grain: month × market × legacy company × billing source ×
   package.
2. Read the four cards: MRR, ARPU, subscribers and billing-to-GL variance.
3. Filter **Source system → Legacy CSV**.
4. Point to the reconciliation workbench: billing, GL, duplicate rows and
   address completeness are together. Drill market → package.

Line: **"This replaces the Python merge and exported workbook, not Excel
thinking."**

## 2. Growth Planner — 10 minutes

This is the data-application moment.

1. Show the live Base Case: clean opportunity locations, projected net adds,
   incremental ARR and blended CAC.
2. In Hudson, type a new **Take Rate Override** (try `7%`) and change
   **Promo Budget**.
3. Watch projected adds, ARR, CAC and the market bars update.
4. Add an FP&A note.

Tie it to their questions:

- What makes money today?
- Which build from three years ago is underpenetrated?
- Which promotion should run in which serviceable area?
- What changes after cleaning false passings?

## 3. FCC Reporting — 7 minutes

1. Open the BDC filing summary.
2. Filter **Review status → Needs review**.
3. Show the same source driving the submission summary and the exception queue.
4. Type a review owner, resolution and certification status.

Line: **"The report is no longer a once-a-quarter archaeology project."**

The support-at-risk card is explicitly illustrative. Do not present it as an
actual government fee, subsidy or liability.

## Close

Snowflake centralizes the data; Sigma makes FP&A able to reconcile it, model a
decision and complete a reporting workflow without rebuilding the dataset in
Power BI, Python and Excel.

## Do not claim

- The synthetic numbers are production Archtop figures.
- The workbook replaces Gaiia, Vetro or NetSuite.
- Workbook filters are security controls.
- New Jersey is confirmed in Archtop's current public rollout; the public site
  currently confirms New York, Massachusetts and Pennsylvania.
