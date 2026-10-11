# Authorized Today-first UI redesign

Approved by the user on 2026-10-07 after reviewing work/design/studyflow-new-vision.html.
This extends the completed original and review stages; it does not replace them.

| Stage | Smallest deliverable | Acceptance gate |
|---|---|---|
| U1 Baseline | Inspect actual routes/tests; record scope and starting verification | Full existing verification passes |
| U2 Foundation / Today | Local design system, sidebar/mobile navigation, real next action and setup states | HTTP next-action tests, responsive browser smoke, regressions |
| U3 Subjects / setup | Subject overview/detail; contextual goals, feedback and exams; concise forms | Ownership, persistence, archive/upload and browser inputs |
| U4 Practice | Start, focus, finish and optional outcome; secondary options | Lifecycle, unrated/rated completion, timer and review loop |
| U5 Supporting screens | Scan-friendly Plan, separate Progress, study-time Settings | Capacity/conflicts/manual changes, review controls, mobile layouts |
| U6 Release | Complete real browser journeys, fresh/existing SQLite verification, handoff | Full lint/unit/HTTP/property/Chromium/WebKit/fresh-launch suite |

Each gate records intended work, tests, actual commands/results and scope review in
docs/PROGRESS.md. Targeted tests precede accumulated regressions. Browser selectors and
literal copy assertions may change for the approved navigation and terminology; their
behavioural checks must remain. No core scheduler, review or database mocks in journeys.

Keep deterministic greedy placement, adaptive repair, authentication, transactional
mutations, finite ordinary budgets and separate recurring reviews. No schema changes,
new dependencies, external services, generated learning content or IA writing planned.
Teacher feedback remains verbatim, with a short preview and expandable original text.
Details/history remain accessible. Completion alone never implies a learning outcome.
