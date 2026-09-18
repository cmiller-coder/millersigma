# Groma cockpit — live QA findings (2026-09-18)

Verified in a real authenticated browser session (Playwright + SSO), not from
a passing API `verify`. Recorded because several of these are platform facts
that cost real time to establish.

## 1. Input-table write-back: the demo-critical one

**Symptom:** clicking *Submit budget* in the published view threw
`Error in Insert row(s) into 'Budget Approval History' - Edits can only be
made in draft mode`, and typing in a peach cell silently did nothing. The
Approval History table was empty, so the centrepiece of the pitch failed in
front of an audience.

**It was not** a connection write-access grant. `GET /v2/connections` shows
`a9d45cfe-...` with `writeAccess: true`.

**It was not** `inputMode`. The spec had `inputMode: "view"`, which looks
exactly like "editable while viewing" and does nothing. `inputMode` accepts
`"view"` and `"edit"` and rejects `"published"`; setting `"edit"` and
publishing changed nothing, and the value was normalised back to `"view"`.

**Actual cause:** each input table has a per-element **Data entry permission**
setting, reachable from a badge next to the element title in Edit mode:

- `Editable in draft` (default) - only users who can edit the workbook
- `Editable in published version (restricted)` - explore or edit access
- `Editable in published version (all access levels)`

Setting it to a published option fixes both the button action and direct cell
editing in view mode. **This setting does not appear anywhere in the workbook
spec** - it is invisible to workbooks-as-code, cannot be set through the API,
and must be re-checked after any spec push.

**Verified after the fix, in the published view:** typing a PM forecast moved
Forecast REIT NOI $6.91M -> $7.25M and value sensitivity $132M -> $138M, and
Submit wrote an audit row with a real `CurrentUserEmail()` and `Now()`.

## 2. Recurring capex was two different numbers

The Property Scorecard deducted **$6.43M** of recurring capex while the 15xx
queue only totalled **$1.31M** ($606k recurring) - the property layer's
`recurring_capex` was typed independently of the capex lines it was supposed
to summarise. Fixed by deriving `recurring_capex` from the tagged lines, so
the two can no longer disagree. Portfolio recurring is now $1.62M (15.6% of
NOI) across 36 lines.

## 3. Capex budget was value-scaled nonsense

`capex_budget` ran $4.99M-$23.8M per building (~0.8x acquisition cost),
producing a **"Capex budget remaining $106M"** headline against a $67.4M REIT
NAV. Rebuilt on the blueprint's candidate definition - $1,500/unit reserve
plus approved project capex plus 10% contingency - giving $3.29M of budget and
$1.67M remaining.

## 4. Controls page could only show green

Four KPIs all read `$0` and every row read `Tied`, so there was nothing to
click and nothing proven - which the project's own brief warns against. Seeded
one explainable break (Chelsea Commons, $24,600, named reason) so the NOI tie
delta, the Review status and the "properties requiring review: 1" KPI all
demonstrate the control actually catching something.

## 5. Agent spec shape (determined empirically)

```
document.agents[] = {
  id, name, instructions,
  greeting:    {mode: "static", message: str},   # "generated"/"dynamic" rejected
  dataSources: [{kind: "table", elementId: str}] # kind is required; "element" rejected
}
```

- `pageId` passes validation but is **silently dropped** - it does not bind an
  agent to a page.
- An agent is rendered by a **separate element of `kind: "chat"`** carrying
  `agentId`, which is then placed in the layout.
- Placing the *agent id* directly in the layout **passes `verify` and fails
  `update`** with `layout for page 'pg-nav' references unknown element`. One
  more case where verify passing means nothing.

## 6. bar-chart supports `orientation: "horizontal"`

`orientation: "horizontal"` validates; `"vertical"` is rejected, which proves
the field is real and enum-checked rather than silently ignored. This fixes
property names being rotated 90 degrees and truncated to "Seaport Reside...".

## 7. API spec PUTs land without a separate publish step

The `Publish` button was already clear after each `PUT /v2/workbooks/{id}/spec`
and the changes were live in the published view, so no UI publish was needed
for spec changes. The Data entry permission in (1) is the exception, because it
lives outside the spec.
