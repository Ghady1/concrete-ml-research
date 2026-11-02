# Future constituents and ML: interface boundaries

Implemented today: one cement Binder, optional SCM binders, explicit aggregate
properties, mass basis, absolute volumes, w/c and w/cm. SCM volumes/masses are
accounted for by the engine but their strength effects are not modeled. The
current UI deliberately does not imply support for sustainable-material laws.

Before adding fly ash, slag, glass, recycled aggregate, rubber or another
constituent, define a versioned research record with:

- stable material ID, name, category and source/batch metadata;
- entered mass and basis; measured SG and its basis;
- replacement reference and mass/volume basis (an explicitly proposed recipe,
  not an inferred equivalence);
- applicable absorption/total moisture and measurement methods;
- measured properties with units, provenance and measurement/assumption status;
- specimen, curing and experimental protocol context.

Do not change the stable lab CSV column meaning. Add a versioned constituent
table/extension and an explicit migration when experiments justify it. Preserve
the existing deterministic model interface; a future ML adapter should consume
a validated feature contract and return prediction plus model/version/domain
metadata. Training, dataset splitting, file loading and UI remain boundaries.

Replacement and model applicability must be established with the professor.
No arbitrary efficiency factor, strength bonus, carbon saving or sustainability
ranking is implemented. Lifecycle comparisons require sourced inventory data and
an explicit functional unit/system boundary, not a material name alone.
