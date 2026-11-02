# Concrete Research Studio: approved M17-M24 redesign

Owner-approved scope: custom React/TypeScript interface, existing Python engine,
local/offline demo, explicit Run analysis. No ML, cloud hosting or accounts.
Keep Streamlit fallback and original concrete_ml owner baseline intact.

## Design specification

Tokens: paper #f7f5f0, surface #fffefb, ink #25332f, muted #5c6961,
teal #2a6257, terracotta #a45436, border #dcded5. Source Sans 3 body/numerals,
Source Serif 4 headings. 8px spacing grid; max content width 1240px; comfortable
44px minimum controls. Charts use teal, slate, terracotta and ochre with labels
and different markers, never color alone. Dark text on light surfaces.

Welcome: compact navigation, editorial heading, genuine concrete photograph,
original SVG aggregate/water/specimen mark, immediate actions, material story,
workflow preview and worked example. One-shot 800ms mark animation, no splash
gate; reduced-motion preference and manual motion toggle.

Workbench: section navigation and one document scroll; materials, moisture,
conditions, optional advanced settings; contextual definitions and explicit units.
Results: summary first, then Strength / Water and workability / Composition and
checks. Show tables and image exports with each chart. Preserve draft strings
separately from submitted SI snapshots. Changed inputs mark results stale.
Exports always contain calculated inputs, not edited drafts.

Controls: text + decimal inputmode, never native numeric spinners. Nonmodal
Headless UI listboxes. No wheel interception, scroll-zoom, nested form scrolling
or scroll-locking dropdowns. Keyboard and touch remain supported.

Quantitative visuals: model dot comparison, w/c curves, age curves, signed water
waterfall, absolute volumes with a 1 m3/m3 line, schematic slump with placeholder
band, density/packing reference comparisons, design constraints and moisture
conventions, calibration parity/residual plots. No invented physical simulation,
model averaging, confidence intervals or sustainability scores.

## Interfaces and implementation

web/ holds Vite frontend. concretecalc_web is an optional FastAPI/Uvicorn package
serving a same-origin compiled frontend. Existing dataclasses define canonical SI
requests and full reports. OpenAPI generates TS types. Chart preparation calls
existing functions; no engineering equations are copied into JavaScript.
Uploaded CSV/XLSX is temporary and capped at 10 MiB / 5000 rows. Calibrations
retain the existing file format/directory. Drafts/snapshots use versioned session
storage; uploads do not. Runtime fonts/photos/icons have no network dependency.

Local start after setup/build: .venv/Scripts/python -m concretecalc_web.
Every milestone is committed and pushed separately to the existing approved branch.

## Status

- M17: baseline/design specification â€” in progress.
- M18: typed Python web boundary and chart data â€” pending.
- M19: branded shell and scroll-safe controls â€” pending.
- M20: complete evaluate workflow â€” pending.
- M21: design and three-snapshot comparison â€” pending.
- M22: calibration and diagnostics â€” pending.
- M23: examples, print/export and offline demonstration package â€” pending.
- M24: numerical/API/browser/accessibility/visual/offline release audit â€” pending.

Acceptance: preserve all 655 tests; API/direct-engine numerical parity; browser
wheel/focus/unit/stale/export tests; all three workflows; accessibility and
responsive inspection at 1440/1280/768/390; offline rehearsal. Capture actual
browser/asset limitations rather than claiming unrun checks.

## M17 observed baseline

Reviewed the running Streamlit app in the in-app browser on localhost. Its main
scroll container is an independent `main#stMain` region, numeric fields expose
steppers, and opening a unit dropdown isolates its options in the accessibility
tree. A wheel action over a checkbox moved the main region by 100px in this
browser, so the reported trap is not universal across all hover states. The
replacement acceptance test explicitly covers focused/hovered fields, checkbox,
closed/open lists and chart boundaries rather than assuming a CSS fix suffices.
The three recorded numerical fixtures come from the existing independently
checked course examples. Full pre-change engine/Streamlit suite: 655 passed.

Assets: see web-assets.md for reviewed real photographs, exact license records
and bundled Adobe fonts. Fonts/photos total approximately 913kB.
