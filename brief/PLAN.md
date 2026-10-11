# Sequential execution plan

Execute all eight stages in order. Each has a separate brief so detailed work is loaded
when needed. A stage is complete only after its required gate actually runs and passes.
Routine progress updates are informational, not requests for human approval.

| Stage | Brief | Deliverable |
|---|---|---|
| 01 | stages/01-foundation.md | Running application, auth, isolated test harness and browser smoke test |
| 02 | stages/02-inputs.md | Simple feedback, targets, exams and availability workflows |
| 03 | stages/03-evidence-priority.md | Tested evidence aggregation and inspectable planning priorities |
| 04 | stages/04-scheduler.md | Finite-budget, capacity/deadline-aware initial study plan |
| 05 | stages/05-adaptation.md | Session lifecycle, bounded repair and transactional feedback loop |
| 06 | stages/06-experience.md | Complete student-facing UI, progress and optional reference attachments |
| 07 | stages/07-adversarial-testing.md | Full browser acceptance, randomized checks and baseline evaluation |
| 08 | stages/08-release.md | Fresh-setup verification, documentation and honest final handover |

Read PRODUCT.md once at startup, then revisit scope at every gate. Read DOMAIN_RULES.md
before designing the schema and implementing algorithms. TEST_CONTRACT.md applies
throughout, not only at Stage 07.

For each stage record a short plan, implementation decisions, relevant files, tests,
actual results and the next stage in docs/PROGRESS.md. Keep completed evidence when
updating the file. If a new discovery changes an implementation detail, update the
relevant documentation and regression tests without changing the approved product.

When blocked, identify the exact dependency. Safe independent work may continue, but
do not mark dependent gates complete. On resumption, inspect the current code/tests,
not merely an old completion checkbox. Do not regenerate already working components.

## Authorized extension

Base stages 01–08 are retained as complete. Execute R1–R6 in REVIEW_EXTENSION.md
sequentially, reusing stages 05–08 services and acceptance checks. Every gate records
its actual targeted/regression results in docs/PROGRESS.md.

## Authorized interface redesign

Original and review stages remain complete. Follow U1–U6 in [UI_REDESIGN.md](UI_REDESIGN.md)
for the user-approved Today-first interface; preserve every original domain requirement.
