# StudyFlow Planner — launch prompt

Paste the following into Codex after opening this folder as a new project workspace.
This is a build brief, not an implemented application. The stages begin NOT STARTED.

---

Build the StudyFlow Planner application described in this workspace. This is a NEW,
smaller project: a feedback-informed adaptive study scheduler, not an assessment
recognition or automatic marking system.

First read AGENTS.md, brief/PRODUCT.md and the stage index in brief/PLAN.md. Then
execute stages 01–08 in order. Read each stage's detailed instructions when reaching
that stage, rather than implementing every subsystem simultaneously. Consult
brief/DOMAIN_RULES.md and brief/TEST_CONTRACT.md as required by the current stage.

I am authorizing routine development, local dependency setup and automated testing
inside this project, within your existing tool permissions. Do not stop between
stages to ask whether to continue. Make small, reversible implementation decisions
using the supplied defaults, record them, and continue until every stage passes its
gate or a genuine blocker prevents further progress.

Do not just produce a plan, scaffold or mock dashboard. Build a functioning app.
For each stage: write a short execution plan and expected outcomes; implement a
small working slice; run the relevant tests; fix failures; rerun the regression
suite; check the changes against the approved scope; update docs/PROGRESS.md with
actual commands/results; then move to the next stage automatically.

Use real unit, database, HTTP integration and headless-browser tests. Test the
scheduler's invariants and failure cases, not only happy paths. Do not mock the core
algorithms in the end-to-end tests. Never remove a valid assertion, skip a required
test or invent a passing result to mark a stage complete.

Keep the original project, student records and IA documents untouched. Do not add
OCR, an LLM, automatic essay diagnosis, generated quizzes, Google OAuth or other
features excluded by brief/PRODUCT.md. The app must function locally without API
keys, model downloads or account connections.

Use synthetic data for testing. Maintain concise implementation and AI-assistance
records, not fabricated first-person IA reflections. Preserve progress so an
interrupted run can resume from the first incomplete stage.

Before finishing, run the complete verification command, exercise the full workflow
in a browser, check a fresh database/setup, and produce docs/HANDOFF.md. Report what
actually passed, what could not be tested, any remaining blockers, and exact run
commands. Do not call an untested or partially implemented product finished.

Start Stage 01 now and continue through the later stages without routine approval
checkpoints.
