# Grand Exchange Merchanting Desk — build

A RuneScape-themed Sigma workbook on **live** Old School RuneScape Grand Exchange
data, plus the bespoke offer-grid plugin in the parent folder.

Workbook: `Grand Exchange — Merchanting Desk` on the **demeng** org
(`aws-api.sigmacomputing.com`), workbookId `322a135b-9c7c-49e8-9a6f-1d4f8db8e959`.
Plugin id on demeng: `7fa7ca6f-f33b-404b-874a-f62813d742de`.

## Pipeline

```bash
# 1. pull live prices (no key needed; the wiki asks only for a User-Agent)
curl -H "User-Agent: <you>" https://prices.runescape.wiki/api/v1/osrs/latest  -o /tmp/osrs_latest.json
curl -H "User-Agent: <you>" https://prices.runescape.wiki/api/v1/osrs/mapping -o /tmp/osrs_map.json
curl -H "User-Agent: <you>" https://prices.runescape.wiki/api/v1/osrs/24h     -o /tmp/osrs_24h.json

python3 prep_data.py      # -> market_layer.sql, plan_base.sql, top_flips.json, meta.json
python3 fetch_sprites.py  # -> sprites.json (240 real item icons, base64)
python3 make_plugin.py    # -> ../index.html with sprites + a real-data fallback
python3 build_runescape.py create          # or: update <workbookId>
```

`build_runescape.py` reads a bearer token from `../../../../awsapi_token.txt`-style
path (see the constant at the top); regenerate it from the org's client
credentials before running.

## Game mechanics modelled exactly

* **Sale tax** — 2% of the sale price, floored, capped at 5,000,000 gp, zero below
  100 gp and zero on the exempt list (bond + basic tools).
* **Buy limits** — the real per-item 4-hour limit from the wiki `mapping` payload;
  realisable profit is margin × units you can actually buy, six cycles a day max.
* **Two margin bases** — the live tick (what you can transact on this second, often
  crossed) and the 24h average (what a patient limit order earns). Both are carried
  because they disagree, and that disagreement is the point.

The headline finding on the captured snapshot: of 240 liquid items, **164 have a
spread the 2% tax eats entirely** — only 76 are profitable instant flips.

## Sigma code-rep shapes verified on this org (Sept 2026)

Everything below was probed live, not guessed. `Invalid kind: "<kind>"` is a masked
error — it fires when a *field* on a known kind is wrong, so it never means
"unsupported".

| Thing | Shape |
|---|---|
| inline custom SQL | `source {kind:"sql", connectionId, statement}`; columns reference `[Custom SQL/<ALIAS>]` |
| element title with colour | `name {text, color, fontWeight}` — the **only** way to get light text on a dark card |
| text element colour | inline `<span style>` in `body`; only `color`, `background-color`, `font-size`, `font-family` are allowed, and element `style` is silently dropped |
| image | `source {kind:"url", url:<https or data uri>}` |
| conditional format | needs `type:"single"`, and styling goes in **`style`**, not `format` (a `format` block is dropped silently) |
| table sort | `sort: [{columnId, direction, nulls}]` — **`sorts` is silently dropped** |
| linked input table | `source {kind:"linked", from:<pivot elementId>}` — the `from` must be a pivot |
| insert-rows | `{effect:"insert-rows", tableElementId, values:{colId: …}}` (renamed from `table` on 2026-08-26) |
| action value sources | `{type:"constant"|"control"|"formula"}`; `control` keeps the field name **`control`**, NOT `controlId` |
| number parameter | works here: `{controlType:"number", mode:"=", value:N, includeNulls:"always"}` |
| text control | `includeNulls` is a **string** enum (`"when-no-value-is-selected"`), not a boolean |
| every element | must appear in the layout XML or create fails |
| valid `source.kind` | `warehouse-table, csv-table, metric-view, semantic-view, sql, table, data-model, code-output, join, union, transpose, unnest` |

Also verified: a scatter/bar axis takes `format.scale.type:"log"` (**not**
`"logarithmic"`, which fails masked), and conditional-format `style` survives while
`format` does not.

Known platform gaps hit:

* **Plugin element DATA is never delivered.** `subscribeToElementColumns` fires and
  returns the right column ids, but `subscribeToElementData` **and**
  `subscribeToIncrementalElementData` both go uncalled indefinitely — with a config
  that `config.get()` proves is correct, and regardless of whether the source
  element is scrolled into view. It delivered exactly once across ~8 runs, so it is
  not simply unimplemented; it is unreliable. The grid therefore runs on a captured
  real-data snapshot, labelled with its capture time in the panel header.
* `config.subscribe()` emits **once, early** — a handler registered after any real
  work (even painting a fallback grid) never hears it. Register it before touching
  the DOM.
* `chat.name` is dropped, so chat panels render as "New chat" with no agent name.
* `clear-control` rejects every field shape tried.
* `visibleAsSource` is data-model-only.
* Export is data-only — no server-side PNG/PDF render, so pixels must be checked in
  a browser.
* **A text element can be silently deleted by the UI.** Two `kind:"text"` elements
  present through version 5 (the last API write) were gone in version 6, which no API
  call made — the render path stripped them and persisted the removal as a new
  version. Re-add and re-verify with a GET after opening a workbook in the UI.
