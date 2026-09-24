# Grand Exchange Merchanting Desk — RuneScape theming

Workbook ID: `bc2978db-3a8e-4a2b-adf2-f0b105326016`

URL: https://staging.sigmacomputing.io/sigma-on-sigma/workbook/5J3vDuzqKUuO3MQGcO9g46

Four pages — Exchange, Offers, Ledger, Scanner — built to carry an Old School
RuneScape look as far as the Sigma spec allows.

## The look

The Grand Exchange interface is tanned parchment inside oiled-leather framing,
so the workbook is built the same way:

- **Leather masthead** per page: near-black panel, gold border, amber title, a
  gold-coin mark, and pill navigation in soft gold.
- **Parchment backplate** behind every page, with a bronze rule under each
  section heading.
- **Leather KPI tiles** — the only dark surfaces in the body, so the gold
  numerals read as the focal point.
- **Parchment tables** with dark ink, tier and status pills in amber, rune
  blue, moss green and oxide red, and bronze data bars.

## Constraints found on this host

These were discovered by writing the spec and reading it back; each one shaped
the design.

| Intent | Result | What the workbook does instead |
|---|---|---|
| `divider` element | Rejected: `Invalid kind: "divider"` | Thin styled container as a bronze rule |
| Theme `backgroundColor` / `elementBackgroundColor` | Accepted, silently dropped | Full-page container acts as the backplate |
| Theme `canvasBackground` / `backgroundCanvas` | Accepted, silently dropped | Same backplate container |
| `colorOverrides` wrapper | Rejected: `Invalid ColorOverrides` | Keys sit directly on `overrides` |
| Table header colours (`headerStyle`, `header`, `headerBackgroundColor`, `columnHeaderStyle`) | Accepted, none round-trip | Palette is light-on-parchment so the default light header reads correctly |
| Table cell background | Not reachable from the theme | Catch-all conditional format, appended last |
| `style` on text elements | Dropped | Inline colour markup in the body; theme text colour elsewhere |
| `style.padding` with borders | Rejected | Padding omitted wherever a border is set |

Two ordering and formula rules also matter:

- **The first matching conditional format wins.** The catch-all parchment rule
  is appended, not inserted, so status and tier rules still take precedence.
- **`Min` is an aggregate.** Row-wise minimums use `Least`, otherwise the
  column fails with `Min expected 1 argument, got 2`.

## Retheming an existing workbook

`retheme` applies this palette to a workbook that already exists, and is built
around one rule: **plugin elements are never touched.**

It fingerprints every `kind: "plugin"` element before and after the transform
and raises rather than publishing if a single byte of `pluginId`, `config` or
element id changed. Plugins are skipped entirely, not restyled.

```bash
# dry run: reports how many elements were restyled and how many plugins were preserved
python3 workbooks/grand-exchange/runescape_theme.py retheme <workbookId>

# write it
python3 workbooks/grand-exchange/runescape_theme.py retheme <workbookId> --publish
```

## Usage

Credentials come from `--env-file` or the environment
(`SIGMA_API_BASE`/`SIGMA_BASE_URL`, `SIGMA_CLIENT_ID`, `SIGMA_CLIENT_SECRET`).
Connection and folder can be overridden with `SIGMA_CONNECTION_ID` and
`SIGMA_FOLDER_ID`.

```bash
python3 workbooks/grand-exchange/runescape_theme.py verify
python3 workbooks/grand-exchange/runescape_theme.py create
python3 workbooks/grand-exchange/runescape_theme.py update <workbookId> --expected-version <n>
```

Data is synthetic. Item names, buy limits and the 2% exchange tax follow the
game's rules, but prices, volumes and flips are generated.
