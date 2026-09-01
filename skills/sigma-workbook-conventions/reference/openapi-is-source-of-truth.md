# The OpenAPI is the source of truth — query it, don't trust this repo's tables

Sigma publishes a single machine-readable description of the whole API, generated
from their own code:

```
https://assets.sigmacomputing.com/openapi/public-rest-api/sigma-computing-public-rest-api.json
```

Plain GET, no auth, no expiry, ~6.5 MB. **When it and anything in this repo
disagree, the OpenAPI wins.** Sigma's own official `sigma-workbooks` skill takes
the same position, and it's the reason that skill doesn't go stale between
releases while hardcoded shape tables do.

> Use the `assets.sigmacomputing.com` URL above. Do **not** read the hashed asset
> the Fern docs viewer fetches — it's presigned (so it expires mid-session) and it
> lags the real surface.

## Fetch once per session

```bash
curl -s "https://assets.sigmacomputing.com/openapi/public-rest-api/sigma-computing-public-rest-api.json" \
  > /tmp/sigma-api.json

# a dead URL returns an HTML error page, which would make every jq below fail
# silently and leave you guessing again
jq -e . /tmp/sigma-api.json >/dev/null 2>&1 \
  || echo "⚠️ not JSON — fall back to GET /v2/workbooks/{id}/spec on a real workbook"
```

## The queries that actually answer questions

**Every valid element kind** — an element is the one thing requiring both `id` and
`kind`, which excludes nested source/control/format kinds that also use `kind`:

```bash
jq -r '[.. | objects
        | select(((.required // []) | index("id"))
             and ((.required // []) | index("kind"))
             and .properties.kind.enum?)
        | .properties.kind.enum[0]] | unique[]' /tmp/sigma-api.json
```

As of 2026-08 that returns exactly 30: `area-chart, bar-chart, button, chat,
combo-chart, container, control, divider, donut-chart, embed, form,
geography-map, image, input-table, kpi-chart, line-chart, navigation, page-break,
pie-chart, pivot-table, plugin, point-map, progress, region-map,
repeated-container, scatter-chart, tabbed-container, table, text,
waterfall-chart`.

**Every field a kind accepts.** Element variants are `allOf` compositions, so
reading only the branch that carries the `kind` enum gives you a misleadingly
short list — you have to union the `allOf` members:

```bash
jq --arg k repeated-container '
  [.components.schemas.WorkbookElement.oneOf[]
   | select([.allOf[]?.properties.kind.enum[0]?] | index($k))
   | .allOf[].properties] | add | keys' /tmp/sigma-api.json
```

This is the query that settles arguments. It's how we established that
`repeated-container` has **no `name` field** — which is why the repeater-qualified
`{{[Name/Column]}}` reference its own docs require can't be written from code.

## What this repo is for

Everything here is **commentary layered on top of the OpenAPI**: house style,
brand, plugin workflow, page patterns, and the field-discovered behaviours the
spec cannot express. Specifically, the OpenAPI will never tell you:

- which fields are accepted on write and then **silently dropped** on read-back
  (diff your POST body against the GET-back — a vanished key is a finding)
- that `POST /spec/verify` is **weaker than create** — it skips SQL resolution,
  duplicate-id and dangling-reference checks, and workspace feature flags
- that an unrecognised layout XML tag returns a **masked 500**, not a validation error
- that `Invalid kind: "x"` almost always means *a required field is missing*, not
  that the kind is unsupported
- which features are gated per workspace

So: **shapes from the OpenAPI, behaviour from here.** If you find yourself about
to hardcode a field list into this repo, write the `jq` query instead.
