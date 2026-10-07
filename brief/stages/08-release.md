# Stage 08 — reproducible setup and handover

## Finish

Review all stages against PRODUCT.md. Do not add new features. Pin the dependency set
actually verified. Check setup from a clean local environment when available and a
fresh database; distinguish those two checks. Never destroy an existing user's data.
Verify runtime has no network/model/API-key dependency. Run all checks again after
final code changes.

Write the application README with exact environment, install, migrate, run, seed and
verification commands. Include how to use the app without demo records. Provide a
clear opt-in demo command and record how dates are chosen. Include configuration,
local-server security limits and known limitations.

Finalize docs/DATA_MODEL.md and docs/ALGORITHMS.md with real function/file references,
pseudocode, worked examples, complexity and trade-offs. Include a small acceptance
matrix and actual test report. These are engineering notes, not ghostwritten IA
criteria or fabricated student reflections.

Create docs/HANDOFF.md containing implemented scope, exact launch/test commands, actual
passed/failed/unexecuted checks, remaining issues, screenshots and a five-minute
first-use walkthrough. Keep an honest docs/AI_ASSISTANCE.md record. No claim that
automated tests establish real learning gains or replace later user evaluation.

## Final gate

All mandatory stages and tests have actually passed; required flows have no stubs;
fresh database onboarding works; demo data is unnecessary; documentation matches code.
Close test processes. Do not leave the test server running and imply it is deployment.
The final message states “verified locally against the listed checks” only when true,
not “bug-free”. A genuine blocker must be plainly reported with the remaining next step.
