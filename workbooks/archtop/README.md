# Archtop Fiber — FP&A Growth & FCC Control Room

Papercrane staging proof of value for Archtop Fiber's IT and FP&A teams.

Workbook ID: `4357e1af-f26a-4c1b-b7d4-4eb9a11a0f45`

URL ID: `234Eayu0tuMYDGw0JrV6wB`

The workbook deliberately follows the meeting's finance-first decision path:

1. **FP&A Control Room** — billing-to-GL reconciliation, ARPU, subscribers,
   duplicates and address completeness across MBS and legacy CSV sources.
2. **Budget & Forecast App** — editable market assumptions feeding projected
   ARR, EBITDA, margin and free cash flow, plus submit/approve writeback history.
3. **Growth Planner** — editable market-level campaign assumptions connected to
   serviceable locations, penetration, address quality, projected net adds,
   incremental ARR and CAC.
4. **FCC Reporting** — export-ready BDC summary plus an editable exception
   review queue.

All records are deterministic synthetic data generated in Snowflake and shaped
like the proposed Snowflake model. The workbook does not contain production
Archtop customer, billing, GIS or FCC data.

## Usage

Credentials are read from gitignored `/workspace/.env`.

```bash
python3 workbooks/archtop/build_archtop.py verify
python3 workbooks/archtop/build_archtop.py create
python3 workbooks/archtop/build_archtop.py update <workbookId> --expected-version <n>
```
