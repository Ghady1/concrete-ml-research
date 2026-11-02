# M22 — local calibration workspace (Studio 2.0 U0 stabilization)

The inherited calibration changes now have a verified checkpoint. `api.py`
validates CSV/XLSX into typed rows, stores temporary upload/fit handles in memory,
fits the existing equations and explicitly saves existing-format parameter files.
`calibration.tsx` shows row errors, eligible observations, in-sample parity and
residual plots, and invalidates pending fits after selection changes. The seeded
12-row demonstration is labelled synthetic. Failed demo fetches now show errors.

OpenAPI and generated TypeScript share the same row/fit/diagnostic contracts.
Diagnostic preparation calls existing moisture, volume and strength functions
without generating the full curve bundle for every uploaded observation.

Verification: 665 Python tests pass. The ordinary pytest temporary directory was
inaccessible on this Windows session, so the suite used a new workspace-local
`--basetemp=artifacts/pytest-u0-20261102`. Twelve Chrome/Edge browser tests pass,
including upload→fit→save→select and pending-fit invalidation. Production build
passes. No core equations/reference tables/owner baseline changed. Diagnostics
remain in-sample; there is no new validation claim.

Hand exercises:
1. Check the seeded Abrams demo equation A=100, B=10 at w/c=0.5 before noise.
2. For measured 30 and predicted 32 MPa, verify the displayed residual sign
   against the labelled residual definition (predicted minus measured).
3. Change the age policy after fitting and verify Save becomes unavailable until
   refitting; restarting the server requires re-uploading the source.
