---
name: sigma-workbook-styling
description: >-
  Use whenever the goal is to make a Sigma workbook look polished and
  visually designed — not just correct. Covers containers as design blocks,
  hero images / logos, buttons and their actions, and the color / spacing /
  typography choices that separate a "pretty" dashboard from a functional
  one. Trigger on phrases like "make this workbook beautiful", "clean up the
  layout", "add a header with our logo", "add a button that links to X",
  "style this dashboard", "make it look designed", or any request about the
  visual craft of a workbook. Pair with sigma-workbook-conventions (spec
  mechanics/correctness) and branded-dashboard-format (the house layout
  template + a specific brand kit); this skill is the reusable visual-craft
  layer that applies to ANY workbook regardless of brand.
---

# Sigma Workbook Styling

Make Sigma workbooks look *designed*, not just functional. This skill is the
visual-craft layer: how to compose containers into clean blocks, place images
and logos, add buttons with actions, and apply color/spacing/typography so a
dashboard reads as intentional and premium.

It assumes the mechanics are handled elsewhere:
- **`sigma-workbook-conventions`** — spec correctness, element kinds, the
  24-col `<GridContainer>` layout XML, POST-time gotchas. Read its
  `reference/workbook-spec-api.md` before authoring layout XML.
- **`branded-dashboard-format`** — the standard house composition and the
  adMarketplace brand kit. Use that when the ask is "our standard format";
  use *this* when the ask is "make it beautiful" in general.

## The one thing to internalize first: spec-as-code vs UI finishing

Sigma's visual polish lives in two places, and knowing which is which saves
hours of confusion:

| Expressible in the spec (round-trips via API) | Applied in the UI (often NOT in the round-trip spec) |
|---|---|
| Element **placement** — `gridColumn`, `gridRow`, `gridTemplateColumns`, `gridTemplateRows` on `<GridContainer>` | Container **background color**, border, corner radius, shadow |
| **Structure** — nested containers, the 24-col grid | Workbook/page **theme** (fonts, accent colors, dark/light) |
| **Images** (`{kind:image, url}`) and their placement | Fine **padding/margins** and element-level color overrides |
| **Buttons** and their **actions** (open link, set control, open Sigma doc) | Button **color/variant** styling |

**Verified from real specs:** the layout XML in existing workbooks uses only
grid-positioning attributes — no `backgroundColor`/`border` attributes appear.
So don't hand-author color styling into the layout XML expecting it to render;
it will be silently ignored. The reliable workflow:

1. **Author structure + placement + images + buttons as code.** Get the
   composition right — blocks, spacing rhythm, where the logo and buttons sit.
2. **Publish, then finish theming in the UI** — background colors, theme,
   fonts, button variants — the things the spec doesn't carry.
3. **GET the spec back** (`scripts/api/publish-workbook.sh get-spec <id>`) and
   commit it as the new source of truth. GET-back captures whatever styling
   the API *does* round-trip, so future edits preserve it.
4. **Always verify visually in the workbook** — the API validates neither
   cross-element resolution nor visual quality.

When you hand a workbook back, be explicit about which polish steps are
code-applied and which need a UI pass, so nobody expects the spec alone to
produce the finished look.

## Containers as design blocks

Containers are the primary tool for making a page read as composed blocks
rather than a flat scatter of tiles. At the element level a container is
minimal — `{ "id": "container-header", "kind": "container" }` — the *design*
comes from how you nest them and lay out the grid.

Patterns that consistently read as "designed":

- **Header bar.** A full-width container holding the logo (left) + title
  (center/left) + optional buttons/filters (right). Give it a distinct row so
  it reads as a masthead.
- **KPI row.** One container wrapping the KPI tiles, with
  `gridTemplateColumns` splitting it evenly (e.g. four KPIs →
  `gridTemplateColumns="1fr 1fr 1fr 1fr"`). Even columns are what make a KPI
  row look aligned rather than ad hoc.
- **Body grid.** A container for the main chart(s); use `gridTemplateColumns`
  to create a 2/3 + 1/3 split (primary chart + side panel) instead of stacking
  everything full-width.
- **Detail band.** A container at the bottom for the detail table / exception
  list, visually separated from the analytical blocks above.

Rhythm rules of thumb:
- Consistent gutters — pick one column-gap rhythm and reuse it; mixed gaps look
  accidental.
- Give KPI tiles enough height (~8–10 grid rows) so sparklines and comparison
  values breathe (from `sigma-workbook-conventions`).
- Don't over-nest. Two levels (page → block containers → elements) is usually
  enough; deeper nesting rarely improves the look and complicates the layout XML.

For the exact `<Page>` / `<GridContainer>` / `<LayoutElement>` XML on the
24-column grid, defer to `sigma-workbook-conventions` →
`reference/workbook-spec-api.md` (the "Layout" and "page-structure pattern"
sections). This skill governs the *design intent*; that reference governs the
*syntax*.

## Images and logos

The image element is simple and round-trips cleanly:

```json
{ "id": "img-logo", "kind": "image", "url": "https://.../logo.svg" }
```

Guidance:
- **Host at a stable, public URL.** SVG is ideal for logos (crisp at any size).
  A CDN or the brand's own asset URL is fine; avoid ephemeral links.
- **Place inside the header container**, not floating on the page grid, so it
  moves with the masthead.
- **Hero/background imagery** is applied in the UI, not the spec — treat it as
  a UI-finishing step.
- For brand logos and palettes tied to a specific company, see
  `branded-dashboard-format`'s `reference/brand-kit.md` and `assets/`.

## Buttons and actions

Buttons turn a dashboard into something navigable and interactive. Add a button
via the workbook's **UI** elements, then configure behavior in the **Actions**
tab. The action types (from Sigma's docs):

- **Open link.** Navigate to an external page or a Sigma destination. URLs can
  be **dynamic** — type `=` in the Link URL to open the formula bar and
  reference:
  - a control value: `[<control-ID>]` (e.g. `[search-control]`)
  - a column selection: `[Selection/<Column Name>]` (e.g. `[Selection/Name]`)
  - all values in a column: `[<Element name>/<Column name>]`
  - functions apply, e.g. `Max([Vendors/Portal])`.
  Choose **New / Same / Parent window** (Parent matters for embeds).
- **Set control value.** Update a target control on click — static values, a
  column, another control, or a formula; and replace / add to / remove from the
  existing selection. Great for "reset filters" or preset views.
- **Open Sigma doc.** Navigate to another workbook and **pre-populate its
  controls** (map source → destination controls). The backbone of guided,
  multi-workbook flows.

Alternatively, controls can be pre-populated straight from a workbook URL via
query params (`...?Region=Metro%20West&Year=2022`, URL-encoded) — note this
does **not** fire change-actions on those controls.

> Spec-shape caveat: buttons and their actions are configured in the UI; the
> exact round-trip JSON shape for a button element isn't yet verified in this
> repo's example specs. When you build one, GET the spec back to capture the
> shape, then add it to `examples/` here so future builds can author it as code.

## Color, spacing, and typography

The taste layer. Most of this is UI-applied (theme + element overrides), but
the *decisions* are what make it look premium:

- **Restraint.** One accent color plus neutrals beats a rainbow. Let the accent
  mark the primary metric / CTA; keep everything else grayscale.
- **Alignment over decoration.** Even grid columns, consistent gutters, and a
  clear top-to-bottom hierarchy (masthead → KPIs → analysis → detail) do more
  for "pretty" than any single color.
- **Whitespace is a feature.** Don't fill every grid cell. Breathing room reads
  as intentional and expensive.
- **Typographic hierarchy.** A clear page title, section labels above each
  block, and readable KPI value/label sizing. Every page gets a visible title
  `text` element (the workbook `name` is metadata, not a heading).
- **Match the brand when there is one.** If a company palette/font is in play,
  pull it from `branded-dashboard-format` rather than reinventing.

## Workflow summary

1. Compose structure as code: block containers, even grid splits, logo in the
   header, buttons where navigation/interaction belongs.
2. Publish (`scripts/api/publish-workbook.sh post ...`).
3. Finish theming in the UI: backgrounds, theme, fonts, button variants.
4. GET the spec back and commit it as the new source of truth.
5. Verify visually; state clearly which polish is code vs UI.

## Examples

`examples/` holds known-good *styled* specs to clone from. Seed it with
GET-back specs of workbooks you consider beautiful — especially any using
buttons or captured container styling — so this skill grows from real,
rendered designs rather than invented shapes. Treat them as immutable
references: clone-and-modify, don't edit in place.
