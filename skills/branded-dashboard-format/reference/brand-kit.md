# adMarketplace Brand Kit (for Sigma)

Scraped from admarketplace.com (Webflow). Apply these so a workbook reads as a
native adMarketplace surface.

## Tokens

### Color

| Role | Hex | Source var |
|------|-----|-----------|
| Primary accent (indigo-blue) | `#3b45ff` | `--primary--600-new` |
| Primary deep | `#002eda` | `--primary--800` |
| Primary darker | `#101c89` | `--primary--900` |
| Darkest — headings, axis labels, ink | `#00022e` | `--primary--1000` |
| Secondary accent (purple) | `#7f56d9` | `--untitled-ui--primary600` |
| Secondary deep (purple) | `#6941c6` | `--untitled-ui--primary700` |
| Soft blue — card fills, zebra rows, light KPI bg | `#deedff` | — |
| Tint blue — section bg | `#f1f5ff` | `--primary--100` |
| Page background | `#ffffff` / `#f8f8f8` | `--primary--background` |
| Neutral surface | `#fafafa` | — |
| Muted text / secondary labels | `#758696` | — |
| Hairline / borders | `#e6e6e6` / `#d9d9d9` | — |

**Gradient (signature):** linear blue→purple, `#3b45ff → #7f56d9`. Use once
(a hero KPI strip or the title bar accent), not as a general fill.

**Categorical series order** (charts, color-by): `#3b45ff`, `#7f56d9`,
`#002eda`, `#00022e`, `#758696`, `#deedff`. Sequential/heat: light `#deedff` →
`#3b45ff` → dark `#00022e`.

**Semantic (if needed):** positive `#3b45ff` (on-brand) or a green only when
good/bad must read instantly; negative/alert `#6941c6`→ a warm red is off-brand,
so reserve red strictly for true alerts.

### Type

- **Primary: Geist** — headings, KPI numbers, UI. (Google Fonts.)
- **Secondary: Poppins** — body/labels if a second face is wanted. (Google Fonts.)
- **Mono: Geist Mono** — code, IDs, raw values.
- Fallback stack: `Geist, Poppins, "Helvetica Neue", Arial, sans-serif`.

### Shape & logo

- **Pill buttons / chips** (border-radius ~1000px), generous padding.
- Soft cards: ~8px radius, light shadow, `#deedff`/`#fafafa` fills on white.
- Logo: `../assets/admarketplace-logo.svg` (black wordmark). On dark, use the
  white variant if available; otherwise place on white/very-light only.

## How to apply each in Sigma

Sigma splits into **Theme** (global, UI-side) and **spec** (per-element). Know
which is which:

### 1. Workbook Theme — set once in the UI (NOT fully in the code spec)

Sigma's font + global color palette live in the workbook **Theme**, which is
largely UI-side state and does not round-trip in the workbook spec. So:

- Create/select a custom Theme named **"adMarketplace"**:
  - **Font:** Geist (if not in Sigma's font list, add it as a custom font, or
    fall back to Poppins → then a system sans).
  - **Accent / primary:** `#3b45ff`.
  - **Categorical palette:** the series order above.
  - **Background:** `#ffffff` (page), cards `#f8f8f8`/`#deedff`.
  - **Text:** headings `#00022e`, body `#00022e`, muted `#758696`.
- Apply the Theme to the workbook after POST. Re-apply when cloning.

> Because the Theme is UI-side, document it here and set it in the UI — don't
> try to encode font/palette in the spec (it won't stick). This mirrors the
> "scope of the code representation" caveat in `sigma-workbook-conventions`.

### 2. Spec-level brand choices you DO control

- **Logo** = a dedicated **`image` element** (NOT markdown). ⚠️ Sigma `text`
  elements do **not** render markdown images — `![alt](url)` shows the literal
  `!` and turns the rest into a link. Use an image element with a top-level
  `url` (verified round-trip shape):
  ```json
  { "id": "img-logo", "kind": "image",
    "url": "https://cdn.prod.website-files.com/64d626ea4b535c7a17b83b78/6a1e79c2d7675464a178bed9_adMarketplace-logo.svg" }
  ```
  Place it in the header container (e.g. `gridColumn="1 / 5"`) to the left of the
  title. SVGs are accepted (PNG/JPG/GIF/WebP too); SVGs referencing external
  styles/JS get sanitized, so if it renders oddly upload a PNG via the UI image
  element instead. Supports a static URL or a `=`-formula dynamic URL in the UI.
- **Title** = a `text` element next to the logo: `## **<Dashboard Title>**` +
  a plain one-line subtitle. With the logo present, omit the brand name from the
  title text.

- **Chart `color` encodings** — when a chart breaks out by a category, the
  series pick up the Theme palette automatically; when you need a fixed order,
  set `color: { by: "category", column: <id> }` and order the dimension so the
  brand sequence lands on the most important series first.

- **Bold, on-brand titles** on every element `name` + the page title text
  element — Title Case, metric-and-slice naming (per conventions).

- **KPI emphasis** — lead with the headline KPI; the Theme accent (`#3b45ff`)
  carries the highlight, so you don't hand-color tiles in the spec.

### 3. What you can't brand in-spec (note + move on)

Font family, global palette, pill-radius, and card shadows are Theme/UI. Set the
Theme once; don't burn iterations trying to express them in JSON.

## Swapping the brand (reuse for another prospect)

This kit is the adMarketplace instance of a generic slot. To rebrand: replace
the token table + logo + font with the prospect's (scrape their site the same
way — see `sigma-embed-portal` for the scrape recipe), keep the *format*
(`format.md`) unchanged. Format is constant; brand is the variable.
