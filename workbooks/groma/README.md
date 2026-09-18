# Groma NAV REIT — Property Budget & Valuation Cockpit

Sigma staging proof of value based on the June 30, 2026 REIT Cockpit
specification.

The workbook compresses twenty-four decision tabs into a five-page demo path:

1. **NAV Control Room** — fund NAV, raw NOI, cash contribution, leverage, and
   the equity-method JV treatment.
2. **Property Scorecard** — the per-property cash ladder with explicit
   master-lease and ownership handling.
3. **Property Budget App** — editable property-manager forecasts, capex
   budgets, management scenarios, and submit/approve history.
4. **Capex Review** — transaction-level recurring versus value-add
   classification with persistent manual overrides.
5. **Controls & Lineage** — independent NOI, valuation, and debt tie-outs plus
   the complete twenty-four-tab source map.

The source layer contains deterministic synthetic data shaped to the supplied
blueprint. It is not production Groma, Buildium, ownership, loan, valuation,
tenant, or investor data. Layer 3—the external appraiser market and cap-rate
model—remains out of scope; the budget page's value output is explicitly a
management sensitivity.

## Accuracy rules demonstrated

- Equity-method JV debt remains inside the LLC and is excluded from REIT debt.
- Recurring capex is nature-based, not amount-based.
- NOI is raw Buildium TTM with no normalizations or add-backs.
- Master-tenant rent expense is explicitly allocated for master leases.
- Every REIT-share field uses quarter-specific ownership.

## Usage

Credentials are read from gitignored `/workspace/.env`.

```bash
python3 workbooks/groma/build_groma.py verify
python3 workbooks/groma/build_groma.py create
python3 workbooks/groma/build_groma.py update <workbookId> --expected-version <n>
```
