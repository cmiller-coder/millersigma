# Anatomical Imaging Body Map — OneMedNet

A data-bound anatomical figure for exploring imaging real-world-data coverage. Regions of an
anterior + posterior human figure are shaded by licensed study volume (or distinct patients, or
EHR-linkage completeness), driven by DICOM `BodyPartExamined` values coming out of a Sigma element.
Clicking a region pushes the underlying warehouse value into a workbook control so the rest of the
dashboard filters.

Single self-contained `index.html` (~48 KB), no build step, no npm install — the
`@sigmacomputing/plugin` SDK is loaded from the unpkg CDN.

---

## Rendering: four-layer composite

The credibility of a body map lives almost entirely in the outer silhouette. Region boundaries
inside a convincing outline read as schematic and are forgiven; a bad outline poisons everything.
So the effort went into one path, and the regions are cheap.

1. **Silhouette** — only the **right half** of the outline is authored, as a single open path
   `#edgeR` in local space `0 0 300 780` with the midline at `x=150`. It is mirrored with
   `transform="translate(300,0) scale(-1,1)"`, which makes perfect bilateral symmetry *structural*
   rather than something to get right by hand. Asymmetry is the number-one tell of hand-drawn
   anatomy; this removes the failure mode.

   The path is **open** (vertex → crotch). The closed version used for fill and clipping is derived
   in JS by appending ` L 148 412 L 148 16 Z`, i.e. the midline edge is pushed 2 units *past* the
   midline so the two mirrored halves overlap by 4 units and there is no antialiasing seam. The
   stroke uses the open path only, so no midline line is ever drawn down the middle of the body.

2. **Region tiles, clipped** — `<clipPath id="bodyClip">` is built from the same closed half-path
   plus a mirrored copy. Every tile lives inside `<g clip-path="url(#bodyClip)">`, so tiles can be
   forgiving primitives (rounded rect, ellipse, lozenge, 4-point path) and still land exactly on the
   body edge. Tiles are deliberately drawn *larger* than the visible region where that helps
   hittability — the clip trims the excess for free.

3. **Skeleton hint** — stroke-only, `pointer-events:none`, `opacity .16`, drawn above the fills:
   cranial vault, mandible, clavicle pair, scapula hint, five rib arc pairs, vertebral tick ladder,
   sacrum, pelvic ring + obturator + femoral head, patella, and long-bone centrelines (humerus,
   radius/ulna, femur, tibia). This is what flips the read from "body shape" to "radiographic
   figure". Toggleable via `showSkeleton`.

4. **Labels layer** — gutter leader lines, value chips, view captions.

The root SVG is authored in markup with `xmlns` present and
`preserveAspectRatio="xMidYMid meet"`; children are created with `document.createElementNS`. The
viewBox width changes with the responsive tier but the aspect ratio is always preserved — there is
no `preserveAspectRatio="none"` stretching, which would deform the anatomy.

Two figure groups share the same local space: anterior at `translate(8,0)` (or `translate(10,0)`
single-figure), posterior at `translate(332,0)`.

### Proportions

The silhouette was built from a 7.5-head canon landmark table (vertex 17, max cranial width 59,
mandibular angle 100, neck 121–148, acromion 162, nipple line 206, xiphoid 262, umbilicus/waist 316,
iliac crest 348, pubic symphysis 412, elbow 297, wrist 400, fingertips 455, knee 552, ankle 700,
plantar 755). **Arms are abducted ~15°** so extremity regions are actually hittable and the axillary
wedge reads.

---

## Regions

13 anterior + 3 posterior regions, each mapped to real DICOM `BodyPartExamined` synonyms.

| id | Label | Example synonyms |
|---|---|---|
| `head` | Head / Brain | HEAD, BRAIN, SKULL, ORBIT, SINUS, TEMPORALBONE, PITUITARY, HEADNECK |
| `neck` | Neck / soft tissue | NECK, THYROID, CAROTID, LARYNX, PAROTID, NASOPHARYNX |
| `chest` | Chest / Thorax | CHEST, THORAX, LUNG, MEDIASTINUM, PLEURA, RIBS, STERNUM, AORTA, CHESTABDOMEN |
| `heart` | Cardiac | HEART, CARDIAC, CORONARY, ECHO, PERICARDIUM |
| `breast` | Breast | BREAST, MAMMO, AXILLA, NIPPLE |
| `abdomen` | Abdomen | ABDOMEN, LIVER, KIDNEY, PANCREAS, SPLEEN, BOWEL, COLON, ABDOMENPELVIS |
| `pelvis` | Pelvis | PELVIS, PROSTATE, UTERUS, OVARY, BLADDER, RECTUM |
| `shoulder` | Shoulder / upper arm | SHOULDER, CLAVICLE, SCAPULA, HUMERUS, ACROMION, UPPERARM |
| `arm` | Elbow / forearm / hand | ELBOW, FOREARM, RADIUS, ULNA, WRIST, HAND, FINGER, SCAPHOID |
| `hip` | Hip / femur | HIP, FEMUR, THIGH, FEMORALHEAD |
| `knee` | Knee / lower leg | KNEE, TIBIA, FIBULA, PATELLA, CALF |
| `foot` | Ankle / foot | ANKLE, FOOT, CALCANEUS, HEEL, TOE, METATARSAL |
| `wholebody` | Whole body (PET-CT) | WHOLEBODY, PETCT, TOTALBODY, SKULLTOTHIGH — rendered as a dashed halo, not a tile |
| `cspine` | Cervical spine | CSPINE, CERVICALSPINE, CTSPINE, ODONTOID (posterior) |
| `tspine` | Thoracic spine | TSPINE, THORACICSPINE, TLSPINE (posterior) |
| `lspine` | Lumbar spine / sacrum | LSPINE, LUMBARSPINE, SACRUM, COCCYX, SIJOINT (posterior) |

### Design decision: laterality is deliberately merged

One `arm` region covers **both** arms; likewise `shoulder`, `hip`, `knee`, `foot`, `breast`. Both
paths of a pair carry the same region id, so hovering or selecting either highlights both. This is
domain-correct: DICOM `BodyPartExamined` carries no side — laterality lives in
`ImageLaterality` / `Laterality` / the study description, not in the body-part attribute. Splitting
the figure left/right on a column that cannot express it would be a lie.

**v2 could un-merge** by adding an optional `laterality` config column (`L`/`R`/`B`) and giving each
paired path its own `data-k` suffix (`arm:L` / `arm:R`), falling back to the merged behaviour when
the column is unbound.

### Z-order

Tiles are appended in strictly **descending tile area** — chest → head → abdomen → hip → shoulder →
arm → pelvis → knee → foot → neck → heart → breast — so the small tiles land on top and stay
hittable. Verified by hit-probing every region: chest does **not** steal `heart` or `breast`.

**Volume is never encoded in region size.** Resizing anatomy reads as broken to a clinician.

---

## Four data states, differentiated by texture

Three shades of grey collapse at 400 px panel height, so the states differ in *texture*:

| State | Meaning | Treatment |
|---|---|---|
| Value present | licensed studies exist | ramp-bin fill, 0.9 px `#0E2430` stroke @ 0.25 |
| Zero | in result set, value `0` | flat `#EDF1F3`, solid 1 px `#B4C0C7` stroke, centred `0` glyph when the tile is big enough |
| No licensed data | absent from result set / NULL | 45° hatch pattern on `#F6F8F9`, `stroke-dasharray="3 3"` |
| Suppressed | present but `patients < suppressUnder` | fine dot stipple; tooltip explains the de-identification threshold |

The ramp's bottom stop `#CFE3EE` is clearly tinted, not near-white, so "low volume" can never be
mistaken for "zero".

**Pattern-scaling gotcha.** `patternUnits="userSpaceOnUse"` means pattern spacing scales with the
viewBox — a fixed 6 px hatch becomes ~2.5 px at 0.42 scale and moirés. `tunePatterns(scale)`
recomputes the tile size, line width, dot radius and dot offsets on every draw. Below scale ≈ 0.5 the
patterns are abandoned entirely in favour of a solid mid-grey fill plus a distinct dash pattern
(`3 3` for no-data, `1.6 2.2` for suppressed) so the two states stay tellable apart.

---

## Ranked region rail

Region areas differ by ~20×, so fill colour is confounded by area — the genuine weakness of every
body map. The rail (region name · mini bar · value · modality-mix microbar) fixes it, gives the
spine, suppressed, zero and no-data regions a reachable home, and highlights bidirectionally with
the figure. Regions that live on the posterior figure are marked `·P`.

Unmatched body-part values accumulate into an **"Unmapped (n)"** chip at the bottom of the rail whose
tooltip lists the top offenders. They are counted in the header totals and never silently dropped —
a real extract will contain `TMJ`, `DENTAL`, `SI JOINT`; surfacing them reads as competence, dropping
them reads as a bug the moment totals stop tying.

---

## Responsive tiers

Tiers are decided from `#stage` clientWidth while the ResizeObserver watches `#wrap`.

| Stage width | Layout |
|---|---|
| ≥ 880 | anterior + posterior + rail + gutter leader labels |
| 760–879 | anterior + posterior + rail, no gutter labels |
| 620–759 | anterior + posterior, no rail (spine visible on the posterior figure) |
| < 620 | anterior only + rail (spine lives in the rail) |

Gutter labels additionally require `#figs` height ≥ 420 px; in-body value chips require scale ≥ 0.46.
There are **no in-body text region labels at any tier** — they would render at ~4 px.

The legend is a single row that never wraps: numeric bin edges drop below 700 px, and below 640 px
the four state chips shrink to short labels — but all four chips are always kept, because they are
load-bearing.

---

## Configuration

```javascript
{name:'source',        type:'element'}
{name:'region',        type:'column', source:'source'}   // DICOM BodyPartExamined
{name:'studies',       type:'column', allowedTypes:['number','integer']}   // drives shading
{name:'patients',      type:'column', allowedTypes:['number','integer']}   // optional, drives suppression
{name:'modality',      type:'column'}                                      // optional
{name:'completeness',  type:'column', allowedTypes:['number','integer']}   // optional
{name:'firstStudy',    type:'column', allowedTypes:['datetime']}           // optional
{name:'lastStudy',     type:'column', allowedTypes:['datetime']}           // optional
{name:'sites',         type:'column', allowedTypes:['number','integer']}   // optional
{name:'regionVar',     type:'variable'}                                    // click -> control
{name:'onRegionSelect',type:'action-trigger'}                              // optional
{name:'shadeBy',       type:'dropdown', values:['Study volume','Distinct patients','Data completeness %']}
{name:'views',         type:'dropdown', values:['Anterior + posterior','Anterior only']}
{name:'scaleMode',     type:'dropdown', values:['Quantile (5 bins)','Linear','Log']}
{name:'suppressUnder', type:'dropdown', values:[0,11,20,50]}
{name:'showRail',      type:'toggle'}
{name:'showSkeleton',  type:'toggle'}
```

`scaleMode` defaults to **Quantile** because imaging volume is brutally long-tailed — chest
radiography alone is 5–10× the next region, and a linear ramp collapses everything else into the
palest bin.

**String-coercion discipline.** Dropdown values arrive from Sigma as **strings** even when declared
numeric (`suppressUnder` posts as `"11"`). Everything goes through
`cfgInt(name, default)` / `String(...)` comparisons — never `===` a dropdown against a number.
Verified by driving all dropdown permutations with string values.

---

## Data contract

One row per **(region × modality)**, long/tidy. Aggregation within a region:

- `studies` → **SUM**
- `patients` → **MAX**, never summed. It is a distinct count; summing it across modalities
  double-counts every patient who had both a CT and an MR. Labelled "patients (distinct,
  region-level)".
- `completeness`, `sites` → **MAX**
- `firstStudy` → **MIN**, `lastStudy` → **MAX**

Region-grain-only data (no `modality` bound) works unchanged — these rules degenerate to identity.

Region matching normalises with `String(v).toUpperCase().replace(/[^A-Z]/g,'')` and then looks up the
built-in synonym map, so `SI JOINT`, `si-joint` and `SIJoint` all land on `lspine`.

Values that genuinely span two regions (`ABDOMENPELVIS`, `CHESTABDOMEN`, `HEADNECK`, `CTSPINE`) are
assigned to the **primary** region and the matched synonym list is printed in the tooltip, so a
radiologist can see exactly what got counted. They are **not** split fractionally.

Dates are parsed defensively — ISO strings, `YYYY-MM`, epoch seconds, epoch milliseconds and `Date`
objects all occur in practice.

Modality values are grouped for colour and tooltip display: CT `#2E749B`, MR `#5C4B8A`,
US `#0E7C7B`, XR/CR/DX/RF `#7A8A94`, MG `#B0567F`, PET/NM `#C77D2E`, other `#9AA7AE`.

---

## Click → Sigma control variable

```javascript
var varId = st.cfg && st.cfg.regionVar;              // the config VALUE, not the literal name
client.config.setVariable.apply(client.config, [varId].concat(vals));
```

Four things that matter:

- `client.config.setVariable(...)` is nested under `.config`, never top-level. Verified against the
  installed SDK declarations (`@sigmacomputing/plugin` v1.2.0, `index.d.cts:223`).
- Pass the **config value** (`st.cfg.regionVar`), not the literal string `'regionVar'`. Several older
  plugins in this repo pass the name and were never verified against a live control;
  `scatter-lasso-select` is the one end-to-end-verified implementation and it passes the value.
  *Fallback if a live workbook control does not update: try `client.config.setVariable('regionVar', ...)`
  with the literal name.*
- Push the **raw warehouse value**, not the display label. A Sigma list control filters on warehouse
  values, so pushing `"Chest / Thorax"` against a `CHEST` column silently matches nothing. A
  `regionKey → rawValue[]` map is built during aggregation; where a region absorbed several raw
  values (e.g. `lspine` ← `LSPINE` + `SI JOINT`) **all** of them are pushed.
- Shift / ⌘ / Ctrl-click multi-selects (variadic `.apply()` form). Clicking the same single region
  again, clicking the background, or pressing `Escape` clears via `setVariable(varId)` with no
  values. Selected regions keep a persistent 2 px ink outline and the rail row stays highlighted.

`setLoadingState` is called defensively — it is declared under `.config` but works top-level in some
builds, so both are attempted inside a `try`.

---

## Synthetic fallback

With no element bound, the plugin renders a synthetic dataset shaped to real US imaging practice —
chest radiography dominant, CT abdomen/head next, MR concentrated in spine and knee, MG for breast,
echo for cardiac, PET whole-body small. It deliberately exercises **all four** visual states plus the
synonym map and the unmapped chip:

- `WRIST` → folds into `arm` via the synonym map
- `SI JOINT` → folds into `lspine`
- `FOOT` with `studies = 0` → zero state
- `TSPINE` with `patients = 7` → suppressed (below the default threshold of 11)
- `TMJ` → unmapped chip
- `NECK` absent entirely → no-licensed-data hatch

The header shows `· preview data` whenever the synthetic set is in use.

---

## Verified

Checked at 1000×600, 1000×400, 880×520, 800×470, 700×400 and 560×360:

- Figure never clipped top or bottom, including at 400 px panel height (`getBBox` inside the viewBox)
- Bilateral symmetry exact; no midline seam
- Tier transitions clean at 880 / 760 / 620
- Legend never wraps to a second line
- Smallest on-screen region dimension at 400 px height: **15.9 px** (breast), then neck 16.1, knee 17.8,
  foot 21.2 — all above the ~14 px hittability floor
- All 16 regions individually hit-tested at the tightest tier; chest does not steal heart or breast;
  the whole-body halo is hittable
- Tooltip clamps on both axes (verified at the bottom edge and the bottom-right corner)
- Hover dims the other 12 tiles and inks the hovered one; rail highlights bidirectionally
- Click / shift-click / Escape selection cycle correct, in figure and rail
- All four data states visible simultaneously with the synthetic data
- Every dropdown permutation driven with string values; console clean throughout

## Hosting

```bash
# local (the launchd agent serves the App Support mirror, which is what Sigma loads)
cp -R ~/Desktop/millersigma/plugins/onemednet-body-map ~/Library/Application\ Support/millersigma-plugins/
# -> http://localhost:8080/onemednet-body-map/
```

Public deploy: Netlify, see the repo-level notes.
