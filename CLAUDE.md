# CLAUDE.md - standing instructions for the `concretecalc` build

## Ground rules (verbatim from the owner's task, section 1; non-negotiable)

1. ENGINE PURITY. Package `concretecalc` never imports streamlit, matplotlib or any UI code. Only the calibration dataset loader may import pandas. Dependencies: core = numpy only; extras: dev = pytest, hypothesis; calibration = pandas, openpyxl; app = streamlit, matplotlib. No other dependency or tool without asking. A test must fail if anything under src/ imports streamlit or matplotlib.
2. SI INSIDE. Internal units: kg, m3, mm, MPa, kg/m3, percent as plain numbers (2.0 means 2 %). Every variable/parameter name carries its unit (cement_kg_m3, strength_mpa, nmas_mm, absorption_pct). Unit conversion happens only at boundaries (units.py, UI adapters).
3. PURE + TYPED. Engine functions are pure, fully type-hinted, with docstrings stating units, equation and source. Results are frozen dataclasses. Warnings are DATA (flags returned in results), never prints and never UI calls. Exceptions only for invalid input (hard-validation failures) or programmer errors.
4. NEVER A DESIGN VALUE. Outputs are "estimated mean strength (research prediction; NOT a certified structural design value)". Define one DISCLAIMER constant in the package; every report object carries it; the UI shows it permanently.
5. DATA, NOT CODE. All reference numbers live in versioned JSON files in src/concretecalc/data/. Take values ONLY from section 8 of this prompt; never from memory. If you think a value is wrong, record it in OPEN_QUESTIONS.md and leave it unchanged.
6. CONSTANTS ARE NOT TRUTH. Abrams A/B, Bolomey K, Feret K, age coefficients are calibratable parameters. Every prediction returns the constants used, their source, and a `calibrated: bool`.
7. SIMPLE CODE. The owner must be able to explain every line. No metaclasses, no clever one-liners, no decorators other than @dataclass, @lru_cache and pytest fixtures. Prefer explicit loops and named intermediate variables. Comments say WHY.
8. NO SCOPE CREEP. Do not add features, files, abstractions or dependencies beyond this prompt and the approved PLAN.md. Do not change a public signature after its milestone is approved without asking.
9. ASK, DON'T GUESS. If something is ambiguous, contradictory or missing, stop and ask. Record every assumption you do make in ASSUMPTIONS.md.
10. NUMERIC HYGIENE. No silent rounding. Test tolerances are explicit (pytest.approx with abs/rel). Round only for display.
11. ENVIRONMENT. Windows PowerShell, Python 3.10+, virtualenv at .venv. Commands you give the owner must work in PowerShell.

("this prompt" / "section 8" refer to the owner's original task text; its section 8 data are
reproduced in PLAN.md, milestone M3, and are the only allowed source of table values.)

## Workflow (from the owner's task, section 0)

- Implement ONE milestone at a time (see PLAN.md). Per milestone: (a) tests first, (b) implement,
  (c) run the FULL suite, (d) write docs/walkthrough/Mxx-<name>.md (incl. 3 hand exercises),
  (e) commit "Mxx: <title>", (f) report and STOP until the owner says "go".
- Report format: files changed; tests added/passing; deviations from PLAN.md; new assumptions;
  new open questions; "numbers the owner should verify by hand".
- Never batch two milestones. Never rewrite history. Never commit .venv.

## Session decisions made by the owner (2026-11-01)

- Branch: work on `claude/loving-allen-8w5d2q` (NOT `build-engine`) and push it after each
  milestone commit, because the cloud container is ephemeral. No pull requests unless asked.
- Layout: `src/concretecalc/` lives beside the owner's existing `src/concrete_ml/`.
  `concrete_ml`, `tests/test_engineering.py`, `requirements.txt` are owner baseline: never edit.

## Commands (PowerShell, from repo root)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```
