# Concrete Research Studio 2.0 — implementation plan

Authorized by the owner's attached Studio 2.0 brief, 2026-11-02. This evolves
the current React/TypeScript/Vite + FastAPI application; no framework migration,
ML predictor, hosting, account system, new physical model or reference-table edits.
Continue the existing branch and push each completed milestone separately.

## Actual starting point

- M17–M21 and original material companions are committed. Existing core has
  655 tests; the web boundary adds numerical parity and calibration tests.
- Evaluate, design, chart tables/SVG export, three session snapshots, offline
  assets, motion preferences and explicit analysis already exist.
- M22 calibration implementation is in the working tree, not yet committed.
  Validate and finish it separately before layering new contracts onto it.
- Examples/methods/credits routes are still placeholders. M23/M24 are unfinished;
  these gates are carried forward, not claimed complete or discarded.
- Names/strength class are not computational inputs; current UI hides this fact.
  Batch volume is declared yield, not an automatic volume constraint. Slump is
  inversion of a proportioning table, not an experimentally validated predictor.

## Milestones and completion gates

| Milestone | Concrete deliverable | Files / interfaces | Required verification |
|---|---|---|---|
| U0 — Stabilize inherited calibration | Verify/commit the pending M22 workspace and process-local fit lifecycle; handle demo-load errors. | Existing api.py, calibration.tsx, generated OpenAPI/TS, browser tests; no numerical signature changes. | Full Python suite; Chrome/Edge upload→fit→save→select and stale-fit tests; build. |
| U1 — Scientific transparency | Source-linked audit, explicit field influence/help, intended-yield explanation, honest heuristic slump labelling, report engineering explanations and applicability notes. | docs/scientific-audit.md; form.ts/components.tsx/workbench.tsx; new engineering-notes.tsx; results.tsx; scientific regression tests. Existing report is the numerical source. | Hand-derived moisture/volume checks, record-only invariance, age/air/admixture conditional behavior; unchanged engine; browser field labels, explanations and overflow; full suite/build. |
| U2 — Complete the research report | Replace placeholder methods/examples/credits, guided examples, accessible diagnostic categories/actions, inspectable original codes, provenance, print report with calculated input snapshot. | New research-pages.tsx and diagnostics.tsx; main.tsx/results.tsx; local asset manifest. Presentation categories preserve original severity and every message. | All navigation targets implemented, CC-BY attribution visible, keyboard/axe and four widths, print/PDF inspection, saved snapshot exports never use drafts. |
| U3 — Quantitative visuals and exports | Fixed per-model colors, explicit curve sweep assumptions and tabulated/extrapolated domains, selected age, actual volume discrepancy, chart PNG/SVG/CSV with units. | presentation.py typed additions if needed; OpenAPI generation; results/chart components. Any new numeric series uses engine functions. | Series reconcile with reports; null predictions/negative water/underfill/overrun; exported values full precision, display rounded; downloaded figure inspection. |
| U4 — Isolated Mix Explorer | Baseline vs hypothetical draft, one-variable water/cement/age exploration with debounce/cancellation and explicit held quantities. No original draft overwrite. | New explorer.tsx, thin typed API sweep only if needed; existing run_mode_b and constants. | Baseline immutable; stale responses cannot win; SI/US preserve quantity; invalid/extrapolated states explicit; independent finite-difference checks. |
| U5 — Scenario research notebook | Rename/describe/duplicate/delete, choose reference, absolute/percentage differences, export comparison. Versioned opt-in local storage and JSON import/export. | compare.tsx; new snapshot-store.ts; Snapshot provenance schema with migration from v1 sessions. | Legacy snapshots read; duplicate/delete safe; no uploaded lab files persisted; null/zero denominators; input/constant/setting/version retention; browser persistence/export round trip. |
| U6 — Design and calibration depth | Guided existing ten-step design; selected-model fit controls, MAE, baseline vs fit, explicit calibration/validation status. Group-aware held-out validation only when enough distinct mixes permit it. | mix_design presentation; calibration.py/TS boundary; calibration tests. Keep current CSV SI schema stable. | No split of one mix across train/test; fit uses train rows only; held-out diagnostics distinct; insufficient data states; existing independent course examples unchanged. |
| U7 — Teaching, extension and release | Expand Show the engineering, measured/assumed/default provenance; document future constituent schema (no invented effects); purposeful material reactions; finish offline package and launch docs. | docs, lightweight SVG/CSS, README, package assets and provenance manifest. | Python/API/frontend/browser tests, 1440/1280/768/390 visual review, keyboard/axe/reduced motion, offline full workflow, wheel regression, packaged build launch without Node. |

Each milestone: tests appropriate to the change, implementation, full Python
suite, frontend build and affected browser checks, walkthrough with three hand
exercises, commit/push, accurate status. Do not call a source verified simply
because a conceptual equation agrees with a public guide. Record unresolved
professor decisions. Preserve concrete_ml and the original owner files.

## Scientific audit approach

1. Compare mass basis, effective-water and absolute-volume definitions with public
   ACI E1-16 sections 3.2/3.3 and worked mixture calculations. Keep all reference
   JSON `verified_against_primary` values unchanged until actual table verification.
2. Document the implemented equations, constant provenance, units and limitations
   for all four models and the literal/normalized age equation. Distinguish a
   project fit to a course table from fitting local laboratory observations.
3. Relabel inverse-water-table slump as a heuristic. Retain raw engine values for
   reproducibility; do not display its ±25 mm placeholder as confidence or accuracy.
4. State that declared yield normalization is not measured yield. The engine's
   mass-per-declared-volume density proxy is not a substitute for a fresh density
   test. Air is assumed or entered, never inferred from entrainer dosage.
5. Add independently derived regression examples; do not generate expected values
   by calling the same calculation that is being tested.

## Decisions / deliberately deferred ideas

- Keep explicit Run analysis in research workspaces. Live calculation is confined
  to the optional Explorer and visibly hypothetical.
- No default model averaging, fake confidence bands or structural compliance status.
- No automatic yield rebalancing in U1. A later Explorer option needs a declared
  balancing constituent, mass basis, moisture handling and rejection of negative mass.
- No general numerical optimizer until objectives and validated constraints exist.
  The current documented course design is the initial guided design foundation.
- SCMs remain unsupported for non-ML strength effects. Document extensibility;
  never expose an input that suggests an unimplemented material law.
- No dataset column mapping/unit inference until stable schema validation and
  explicit conversion provenance can prevent accidental lab-data reinterpretation.
- No new animation, chart or document dependencies in the first milestones.

## Status

- Plan established; implementation begins with U0, followed by U1.
- U2–U7 remain planned, not implemented or release-audited.
