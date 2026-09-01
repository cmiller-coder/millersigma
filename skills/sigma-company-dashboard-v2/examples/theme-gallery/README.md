# Dashboard Theme Gallery

Five dashboard aesthetics for the `sigma-company-dashboard-v2` selection flow.
All examples show the same forecasting command center so the user compares
visual systems rather than different dashboard content.

Open any HTML file directly:

| Option | Theme | Best fit |
|---|---|---|
| 1 | [Executive Gradient](01-executive-gradient.html) | Default branded POV, forecasting, executive command center |
| 2 | [Editorial Minimal](02-editorial-minimal.html) | Board, finance, strategy, professional services |
| 3 | [Operations Control Room](03-operations-control-room.html) | Manufacturing, logistics, network/real-time operations |
| 4 | [Aurora Glass](04-aurora-glass.html) | AI applications, innovation demos, technology |
| 5 | [Field & Natural](05-field-natural.html) | Food/agriculture, field service, sustainability, healthcare ops |
| 6 | Editorial Ops (`theme-presets.json` only) | Exec overview paired with a data-app page — Editorial structure, Control Room density, light surfaces. Built for [`../build_honda_ev_allocation.py`](../build_honda_ev_allocation.py). |

`theme-presets.json` is the machine-readable contract for a future theme
selector. The HTML uses `theme-gallery.css` for the richer browser preview;
the `sigma` object in each preset contains only tokens that map to Sigma:

- Theme colors and categorical scheme
- Gradient/flat header asset
- KPI card treatment
- Native title/value colors and sizes
- Border radius and spacing
- Table preset

## Intended end-user flow

```text
1. What customer/company is this for?
2. What data app do you want?
   - Forecasting / scenario planning
   - Cohort builder
   - Reconciliation
   - Operational write-back
   - Other
3. What dashboard style do you want?
   1–5, with these HTML previews
4. Builder composes:
   workflow archetype + selected theme + customer brand palette
```

The workflow and theme remain separate. For example, Forecast Approval can be
combined with any of the five themes without changing its input tables,
actions, controls, formulas, or approval state machine.

## Design invariants across all themes

The options are visually distinct, but they deliberately preserve the same
best-practice structure:

1. **Decision first.** The page names the decision/question rather than merely
   naming the data source.
2. **Three-second hierarchy.** Header → 3–5 headline KPIs → one dominant trend
   and one explanatory view → detail table.
3. **Comparison context.** KPI values include delta/target context, not naked
   numbers.
4. **Predictable grid.** Consistent alignment and gutters reduce scan effort.
5. **Restrained color.** Neutral surfaces dominate; saturated color highlights
   hierarchy, status, or a selected category.
6. **No color-only meaning.** Status uses labels/symbols as well as color.
7. **Accessible contrast.** Text/color combinations target WCAG AA (4.5:1 for
   body text, 3:1 for large text and graphical elements).
8. **Honest charts.** No 3D decoration, minimal gridlines, direct labels, and
   consistent category colors.
9. **Details remain available.** Every analytical page ends in a readable data
   table rather than hiding source values behind charts.
10. **Responsive degradation.** The browser mockups collapse cleanly; a Sigma
    implementation should use separate page designs where mobile use matters.

## Research basis

The patterns above align with:

- [Tableau — Best Practices for Effective Dashboards](https://help.tableau.com/current/pro/desktop/en-us/dashboards_best_practices.htm):
  audience/purpose first, key content top-left, and limit competing views.
- [Tableau Blueprint — Visual Best Practices](https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm):
  logical visual flow, neutral base colors, restrained brand accents, and
  accessibility.
- [Microsoft Fabric accessibility guidance](https://github.com/microsoft/skills-for-fabric/blob/main/skills/powerbi-report-design/references/accessibility.md):
  color cannot be the sole signal; contrast, focus order, accessible names,
  and table fallbacks.
- [DataCamp dashboard design tutorial](https://www.datacamp.com/tutorial/dashboard-design-tutorial):
  Z-pattern hierarchy, whitespace as structure, consistent grid, and visible
  focus states.

## Mapping the browser preview to Sigma

| HTML treatment | Sigma implementation |
|---|---|
| Gradient hero | Container `backgroundImage` with generated SVG data-URI |
| Gradient KPI card | Container background image + native `kpi-chart` title/value |
| Flat/editorial KPI | Light container or bare KPI + border rule |
| Navigation pills | `navigation` element with `optionStyle.style: "pill"` |
| Glass effect | Dark translucent-looking SVG background (true CSS blur is not available) |
| Card panels | `container` with background, border, radius, spacing |
| Theme palette | `settings.theme.overrides` + chart categorical scheme |
| Compact/dense tables | `tableStyle.preset`, `cellSpacing`, banding/gridlines |
| Semantic status | Conditional colors plus visible labels/icons |

Do not copy browser-only effects literally when Sigma cannot represent them.
The preview establishes hierarchy, palette, density, and composition; the
Sigma implementation uses supported code-rep primitives.

## Company-branded examples

`companies/` holds fully branded, content-customized previews — not just the
neutral theme picker. Each file picks one theme, overrides the identity CSS
variables (`--primary`, `--hero-end`) with the company's real brand colors
(the same `COLORS` dict pattern used in `sigma-company-dashboard`'s
`company.py`), and swaps in industry-specific KPIs, categories, and table
rows via `window.THEME_CONTENT` (read by `theme-gallery.js`, falling back to
the Northstar Foods defaults when absent).

- [`companies/honda.html`](companies/honda.html) — Operations Control Room
  (its `bestFor` tag is literally "manufacturing") + Honda red (`#E4002B`) as
  `--primary`, with a production/quality/plant-yield command center instead
  of demand planning.

**Adding a new company preview:** copy the nearest example in `companies/` —
swap the theme class, the brand color override, and the `THEME_CONTENT`
object's KPIs/categories/table rows to that company's real segments. Only
override `--primary` (and optionally `--hero-end`) for brand identity; leave
`--good`/`--bad`/`--warn` alone so status badges and risk dots keep their
theme-default semantic meaning. `theme-gallery.js` also dynamically scales
the trajectory chart's Y-axis off each dataset's own min/max — the original
hardcoded scale broke silently on Honda's larger unit values (220-281 vs.
Northstar's 6.5-11.6), sending the lines off the top of the chart.

