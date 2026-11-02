# M16 - final setup, packaging and verification

`README.md` documents Windows PowerShell setup/run, both modes, calibration,
stable SI exports, architecture, reference verification and adding a future model
through the common registry. `pyproject.toml` adds the explicitly approved
pytest-cov dev dependency (D-5). `.gitignore` excludes local calibration JSON,
temporary files, coverage output and build artifacts. The original owner code,
engineering tests and requirements snapshot remain unchanged.

`CLAUDE.md` records the owner's instruction to continue milestones and push
each without an approval pause, and the authorized recreation of the deleted
Desktop checkout in CodeBase. Original ground rules remain intact.

## Final checks

- Full suite with all extras installed: **655 passed, no skips** on Windows,
  Python 3.12.8. Includes Hypothesis properties, independent course examples,
  Excel import, architecture scans and Streamlit interactions.
- Statement coverage (`--cov=concretecalc --cov=app`): **96%**, 2348 statements,
  99 not covered after final reporting review. This is statement coverage, not branch coverage.
- `pip check`: no broken requirements.
- `git diff --check`: clean. Comparison against original baseline `2707be6`
  for `src/concrete_ml`, `tests/test_engineering.py` and `requirements.txt`: empty.
- Built the distributable wheel, installed it without dependencies into a new
  temporary directory and used isolated Python (`-I`) to import that installed
  package. Asserted the imported package path came from the isolated install.
  All **18** packaged reference JSON files loaded through their proper loaders.
  Mode B and strict `json.dumps(..., allow_nan=False)` export passed. No
  Streamlit, matplotlib, pandas or openpyxl module was imported by that engine run.
- Optional dataset/UI tests skip when their extras are absent. Full verification
  above installed all extras and exercised them.

## Coverage inventory

| Area | Statement coverage |
|---|---:|
| Unit conversion, schemas, moisture, flags, age | 100% |
| Table models and interpolation | 100% |
| Domain lookups | 98% |
| Validation, Mode A | 97% |
| Volumes, Mode B | 96% |
| Display adapters | 95% |
| Streamlit pages | 94% |
| Parametric fitting | 92% |
| Dataset import | 90% |
| Calibration persistence | 88% |

Uncovered lines mainly concern additional error paths or optional widget choices.
The suite is not a substitute for primary-source table review or laboratory
validation. No table has been declared primary-verified and no coefficient is
presented as universally valid. Professor questions remain in OPEN_QUESTIONS.md.

## Three hand exercises

1. Launch the README command, enter the M11 example and confirm effective
   w/c=200/315 and total absolute volume=1 m3. Switch to US units and back.
2. Follow the independent Example 2 at NMAS 25/severe exposure: confirm
   minimum cement=334 kg/m3 and final w/c=148/334. Compare the strict and
   course field weights rather than mixing their bases.
3. Generate three exact strengths with f=100/10**wc at wc .3/.4/.5. Record
   matching physical inputs in the lab schema, fit and confirm A~100, B~10;
   save, select the material set and inspect its source/hash and calibrated label.

## Retained limits and approved decisions

The combined Feret fit uses K=230.00330523607096 and approved pointwise
tolerance 3.2 MPa; the AE 41 MPa point discrepancy is openly recorded. Literal
steam Type I at 28 days differs by 1.449%; optional normalization is explicit.
Course/strict moisture differences, unverified literature presets, placeholder
slump/flag thresholds, model applicability, and SCM/SP limitations remain visible.
No new civil assumptions or unresolved implementation decisions were introduced
in this hardening milestone. Runtime calibration records stay local and require
the user's own backup process.

## Completion review

Rechecked the original requirements and added the explicit signed comparison of
each predicted 28-day mean against Mode A's required mean. It uses the selected
display units and is tested in the Mode A prediction-back interaction. Clarified
the sidebar help: the course/strict selector controls Mode A field batching;
Mode B uses the explicit aggregate basis. No engine equation, public engine
signature, dependency or reference value changed.

Repeated full coverage run: **655 passed, 96% statements**. Started the documented
Streamlit command headlessly on a temporary loopback port, confirmed HTTP 200
for both `/` and `/_stcore/health` (`ok`), then stopped the temporary server.
