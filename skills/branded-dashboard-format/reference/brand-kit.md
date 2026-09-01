# Brand Kit Template (for Sigma)

Fill this in per company so a workbook reads as a native surface for that brand.
Gather tokens from the company's site (see `sigma-embed-portal` for the scrape
recipe) or their brand guide, then drop them into the table below.

## Tokens (fill in)

### Color

| Role | Hex | Notes |
|------|-----|-------|
| Primary accent | `#______` | the dominant brand color; drives highlights |
| Primary deep / hover | `#______` | darker shade of the accent |
| Ink — headings, axis labels | `#______` | darkest; near-black in the brand family |
| Secondary accent | `#______` | supporting color |
| Soft fill — cards, zebra rows, light KPI bg | `#______` | a very light tint |
| Section tint background | `#______` | light |
| Page background | `#ffffff` / `#______` | usually white / off-white |
| Muted text / secondary labels | `#______` | grey |
| Hairline / borders | `#______` | subtle |

**Signature gradient (optional):** pick two brand colors for a single
hero/accent moment — `#______ → #______`. Use it once, not as a general fill.

**Categorical series order** (charts, color-by): list the palette in priority
order so the most important series gets the strongest brand color. Sequential/
heat: light tint → accent → ink.

**Semantic:** reserve a warm red strictly for true alerts if it's off-brand;
otherwise lean on the accent for positive emphasis.

### Type

- **Primary font:** ______ (headings, KPI numbers, UI). Add as a custom font in
  Sigma if it's not in the default list.
- **Secondary font:** ______ (body/labels), optional.
- **Mono:** ______ (code, IDs, raw values), optional.
- Fallback stack: `<Primary>, "Helvetica Neue", Arial, sans-serif`.

### Shape & logo

- Button/chip radius, card radius + shadow, fill choices — capture the brand's
  feel (pill buttons, soft cards, etc.).
- **Logo:** host the SVG/PNG at a public URL (or upload via the UI image
  element). Keep a light-background variant for dark placements.

## How to apply each in Sigma

Sigma splits into **Theme** (global, UI-side) and **spec** (per-element). Know
which is which — this part is brand-agnostic and always applies:

### 1. Workbook Theme — set once in the UI (NOT fully in the code spec)

Sigma's font + global color palette live in the workbook **Theme**, which is
largely UI-side state and does not round-trip in the workbook spec. So:

- Create/select a custom Theme named after the company:
  - **Font:** the primary font (add as a custom font if needed, or fall back to a
    close Google Font → then a system sans).
  - **Accent / primary:** the primary accent hex.
  - **Categorical palette:** the series order above.
  - **Background:** page white/off-white; cards the soft fill.
  - **Text:** headings + body the ink color, muted the grey.
- Apply the Theme to the workbook after POST. Re-apply when cloning.

> Because the Theme is UI-side, document it here and set it in the UI — don't
> try to encode font/palette in the spec (it won't stick). This mirrors the
> "scope of the code representation" caveat in `sigma-workbook-conventions`.

### 2. Spec-level brand choices you DO control

- **Logo** = a dedicated **`image` element** (NOT markdown). ⚠️ Sigma `text`
  elements do **not** render markdown images — `![alt](url)` shows the literal
  `!` and turns the rest into a link. Use an image element with `source.url`
  (verified round-trip shape — the old top-level `url` field was rejected as a
  masked `Invalid kind: "image"` starting 2026-07-30):
  ```json
  { "id": "img-logo", "kind": "image",
    "source": { "kind": "url", "url": "https://<host>/<company>-logo.svg" } }
  ```
  Place it in the header container (e.g. `gridColumn="1 / 5"`) to the left of the
  title. SVGs are accepted (PNG/JPG/GIF/WebP too); SVGs referencing external
  styles/JS get sanitized, so if it renders oddly upload a PNG via the UI image
  element instead. A data-URI SVG works too (see `sigma-company-dashboard` for
  the wordmark/logo-as-data-URI trick). Supports a static URL or a `=`-formula
  dynamic URL in the UI.
- **Title** = a `text` element next to the logo: `## **<Dashboard Title>**` +
  a plain one-line subtitle. With the logo present, omit the brand name from the
  title text.

- **Chart `color` encodings** — when a chart breaks out by a category, the
  series pick up the Theme palette automatically; when you need a fixed order,
  set `color: { by: "category", column: <id> }` and order the dimension so the
  brand sequence lands on the most important series first.

- **Bold, on-brand titles** on every element `name` + the page title text
  element — Title Case, metric-and-slice naming (per conventions).

- **KPI emphasis** — lead with the headline KPI; the Theme accent carries the
  highlight, so you don't hand-color tiles in the spec.

### 3. What you can't brand in-spec (note + move on)

Font family, global palette, pill-radius, and card shadows are Theme/UI. Set the
Theme once; don't burn iterations trying to express them in JSON.

## Reusing for another company

This template is a generic slot. To brand for a new company: refill the token
table + logo + font with the target's (scrape their site the same way — see
`sigma-embed-portal`), keep the *format* (`format.md`) unchanged. Format is
constant; brand is the variable.
