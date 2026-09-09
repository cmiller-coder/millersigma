# Origin Investments — Model of Record

Papercrane staging POV for Dayna McCue (Origin Data and AI Enablement).

Workbook name: **Origin Investments — Model of Record**

`DEMO-SCRIPT.md` is the walkthrough. `build_origin.py` creates or updates the
workbook via the workbooks-as-code API.

## What it is

Three pages aimed at the 3 Sep 2026 intro call, not a generic PE command center:

1. **Model of Record** — IM / investor services transparency. Property grid plus
   a quarter-end chase list of desktop Excel files.
2. **Sales & Marketing** — one-click fundraising pacing, pipeline, campaigns.
3. **Quarter-end Writeback** — spreadsheet UI on a published baseline. Type
   occupancy; NOI and variance move.

Data is **synthetic** Snowflake SQL shaped like a Redshift multifamily book.
It is not production NAV. AskSimon remains the chat layer.

## Usage

Credentials in gitignored `/workspace/.env` (`SIGMA_PAPERCRANE_*`).

```bash
python3 workbooks/origin/build_origin.py verify
python3 workbooks/origin/build_origin.py create
python3 workbooks/origin/build_origin.py update <workbookId> --expected-version <n>
```
