# Studio scientific review — 2026-11-02

Scope: inspect the implemented research methods and how the web interface
describes them. This is not certification, independent laboratory validation or
verification of every course-table value against an original standard.
No reference JSON or core equation is changed by this review.

## Physical accounting

`moisture.py` uses an oven-dry denominator for absorption and total moisture.
As-received mass is divided by (1+MC/100); SSD mass by (1+Abs/100).
Free water is OD*(MC-Abs)/100, including its negative sign. On SSD entry,
effective MC is explicitly Abs, with a mismatch warning for a different entered
MC. Oven-dry entry means a dry-equivalent mass paired with the entered MC; it
does not automatically force MC to zero. The UI must explain this convention.

`volumes.py` pairs SSD aggregate mass with SSD specific gravity. Cement/water
and binder volumes use W/(SG*1000); air is entered/assumed percent divided by
100. Closure is sum-1 m3 per declared m3. The dry-rodded void indicator converts
SSD SG to OD SG before comparison. These definitions agree conceptually with
ACI E1-16 discussions of relative density and moisture (sections 3.2/3.3).
This does not establish verification of all course assumptions or table values.

Declared volume normalizes input quantities; it is not measured yield and is
not an automatic rebalancing constraint. The current computed unit weight is
mass per declared volume. With poor closure, do not interpret it as a fresh
density measurement. Actual yield would require measured fresh density.

Independent checks in test_scientific_contract.py: 1050 kg as-received CA at
5% MC yields 1000 kg OD and, at 2% absorption, 30 kg free water. Adding 50 kg
cement of SG 3.15 to a fixed declared 1 m3 adds 1/63 m3 without changing sand.

## Strength and age implementations

| Method | Equation / units | Parameters and limitations |
|---|---|---|
| ACI table | Invert required-average strength MPa versus dimensionless w/c | Stored course transcription, separate AE/non-AE columns; 19–25 mm/moist-cured basis; table values remain unverified. |
| Abrams | f28=A/B^(w/c), MPa | A in MPa, B dimensionless. Default project fit to course table, not local experiments. Fixed-material/testing assumptions; no extra entered-air penalty. |
| Bolomey | f28=K*(1/(w/c)-0.5), MPa | K in MPa. Project fit to the same table; separate AE presets; not independent evidence from Abrams/table. |
| Feret | f28=K*[Vc/(Vc+Vw+Va)]^2, MPa | K in MPa; explicit air and cement SG influence. Fit assumes provisional water/air conditions documented in OPEN_QUESTIONS Q23. |
| Age | f(t)=f28*t/(a+b*t) | t/a days, b dimensionless; literal or explicitly normalized at day 28. I/III coefficient sets; II/IV/V use I with warnings. Empirical, not measured curing history. |

Project range warnings are not experimentally established validity envelopes.
Interpolated/clamped/extrapolated status is a lookup operation, not a statement
of physical accuracy. Model agreement does not establish accuracy. No averaging
is performed. Names/strength class are records only; no product recognition.
Cube equivalence is separate from cylinder-based predictions; no factor assumed.

The existing w/c curves vary cement at fixed effective water, SG and air. They
are not closed-volume redesigned mixtures. Main lookup policy and chart-sweep
policy require explicit differentiation: curve generation currently uses the
registry default table behavior. Resolve presentation/settings consistency in U3.

## Workability decision

Keep the legacy engine result and exports for reproducibility. In the UI, call
it a heuristic water-table equivalent, remove the placeholder band from the
headline, and suppress the headline number when admixture effects are unsupported.
The raw legacy placeholder bounds remain in technical data, not confidence or
accuracy claims. Inverting a proportioning table does not identify the effects
of all relevant material, admixture and test conditions.

## Calibration and reproducibility findings for later milestones

- Current R2/RMSE are in-sample. No external validation claim is supported.
- Constant-response R2 has a custom 0/1 fallback; presentation should identify
  undefined variance rather than suggest a conventional validation metric.
- Save context should retain age conversion policy and eligible/excluded rows.
- Stored fits do not distinguish AE/material-condition strata beyond material ID.
  A mixed-condition dataset must not silently suggest a universally applicable set.
- Fit residuals in API are measured minus predicted. Any documentation/example
  using the opposite sign must be corrected without changing actual values.
- Historical snapshots need explicit engine/table/calibration versions for replay.
- Public source verification of Abrams/Bolomey/Feret presets and age coefficients
  remains unresolved. Do not substitute remembered literature coefficients.

## Public sources consulted

- ACI E1-16, *Aggregates for Concrete*, sections 3.2/3.3:
  https://www.concrete.org/Portals/0/Files/PDF/E1-16v3.pdf
- ACI, *How is workability measured and specified?*:
  https://www.concrete.org/frequentlyaskedquestions/faqid/738.aspx
- NRMCA, *Guide to Improving Specifications for Ready Mixed Concrete* (2021):
  https://www.nrmca.org/wp-content/uploads/2020/10/GuideToSpecs.pdf

These sources support conceptual interpretation. They do not mark any packaged
reference table as primary-verified. Professor questions remain in
OPEN_QUESTIONS.md, especially moisture convention, slump band/midpoint reading,
specimen conversion, age normalization and required-strength rule applicability.

## Studio 2.0 dispositions

The findings above describe the baseline. U3 now exposes curve/table coverage
and explicitly describes sweep extrapolation separately from the selected mix
lookup policy. U5 records runtime/data/parameter/input fingerprints. U6 adds
undefined constant-target R2, MAE/default comparisons, grouped internal holdout,
fit context, condition checks and atomic saved revisions. Residual documentation
now consistently uses measured minus predicted. None of these changes verify
all course data or establish external laboratory accuracy. Fits remain equally
weighted per row; n_specimens and measured strength SD are records, not weights.
