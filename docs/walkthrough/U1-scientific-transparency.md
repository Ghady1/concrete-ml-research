# U1 — scientific transparency and field influence

`form.ts` now explains record-only and conditional inputs. `TextField` exposes
optional certificate examples and accessible help. `workbench.tsx` labels
intended batch yield, identifies starting defaults and treats incomplete numeric
edits as stale. No input automatically rebalances another constituent.

`engineering-notes.tsx` displays existing report intermediates for moisture,
water/cement, volumes, constants and age. It does not implement model equations.
Research context separates closure, applicability and parameter evidence.
The summary labels workability heuristic; unsupported admixture conditions
suppress its primary numerical illustration, retaining raw legacy data/exports.

`scientific-audit.md` records source scope, equations and remaining scientific
questions. No reference values or core equations changed. Six independent
contract tests cover hand arithmetic, the additional 50 kg cement volume,
record-only invariance, SSD mismatch and conditional air/age/admixture effects.

Verification: 671 Python tests pass. Frontend production build passes; new
browser coverage checks accessible field influence, engineering detail, three
widths, axe and incomplete-edit stale status. Full Chrome/Edge regression is
run for this checkpoint. No claim of laboratory validation or primary table
verification is introduced.

Hand exercises:
1. At SG=3.15, verify 50 kg extra cement occupies 1/63 m3; sand is unchanged.
2. CA=1050 kg, MC=5%, Abs=2%: calculate 1000 kg OD and 30 kg free water.
3. Rename cement and enter a certificate designation; verify all predictions
   remain unchanged, then change age and observe only age-adjusted outputs.
