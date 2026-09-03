# OneMedNet iRWD Intelligence Layer

Live workbook: Papercrane staging, URL ID `3OCeIV1S7bV6fybbrXUBqK`.

Workbook ID: `7d65161f-037e-4ea9-a156-32d6d0f63dde`

## Functional repair

`fix_functionality.py` fetches the latest live spec and applies targeted repairs
without replacing unrelated workbook content:

- high-contrast KPI cards on all four persona pages;
- coherent, non-zero trial-feasibility defaults;
- working therapeutic-area, drug-class, site, encounter-class and therapy-line
  filters;
- cohort detail scoped to the active feasibility protocol;
- accurate proof-of-value governance language;
- writeback language aligned with the values actually saved.

The workbook intentionally remains a synthetic proof-of-value. It demonstrates
the intended product workflows on Snowflake-generated records; it does not claim
to enforce production OneMedNet licensing or row-level security.

## Usage

Credentials must be supplied through a gitignored environment file. The default
is `/workspace/.env`; override it with `--env-file`.

Dry run:

```bash
python3 workbooks/onemednet/fix_functionality.py
```

Publish only after confirming the expected live version:

```bash
python3 workbooks/onemednet/fix_functionality.py \
  --publish \
  --expected-version 11
```

The version check prevents overwriting newer UI edits.
