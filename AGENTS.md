# Project instructions — StudyFlow Planner

## Objective and authority

Build the bounded product in brief/PRODUCT.md. It replaces the earlier IA idea that
relied on handwritten-assessment diagnosis. The student's old IA draft is historical
context, NOT the implementation specification. Do not restore its AI-native,
OpenAI, OCR, automatic quiz or mandatory Calendar requirements.

Respect higher-priority instructions and the environment's permissions. Operate only
in this new project workspace. At startup inspect the root and current progress.
If unrelated application code is present, do not overwrite it. Do not inspect or
modify the previous project elsewhere on the computer without authorization.

## Sequential execution

Read brief/PLAN.md and execute one stage at a time. Before each stage, read its file,
relevant domain rules, the test contract and docs/PROGRESS.md. Write a short task plan
with observable outcomes. Do not stop after planning; implement it.

At every gate:
1. Run targeted tests and then the accumulated regression suite.
2. Read failures and fix the cause. Keep tests that expose genuine defects.
3. Review the diff against the product scope and the algorithm invariants.
4. Update progress, decisions, actual commands, results and remaining issues.
5. Proceed automatically to the next stage if the gate passes.

Create small, reviewable changes. Avoid a giant rewrite at the end. Do not begin
optional extensions after completing the required stages; finish verification and
handover instead. If interrupted, resume from recorded state, not from scratch.

## Autonomy with limits

Routine local coding, test execution, temporary test databases and dependency setup
in a project virtual environment are authorized within available permissions. Do not
ask the user to manually click through every intermediate build.

A prompt is not permission to bypass the sandbox. Do not weaken security settings,
use sudo, expose a public server, make paid requests, push to a remote repository,
open private accounts, or delete unrelated files. Use standard package registries
and official documentation. Install only project dependencies and the isolated
Playwright test browser; do not replace the user's installed browsers.

Use bounded command timeouts. After three materially different unsuccessful attempts
at an environment/setup blocker, record the exact issue rather than retrying the
same command forever. Continue genuinely independent work where safe, but keep the
blocked gate incomplete. Never report unavailable browser testing as passed.

## Quality rules

- The real application must be tested, not only helper functions or hard-coded demo output.
- Preserve user isolation, foreign-key integrity, transactional updates and task accounting.
- Keep algorithms readable, deterministic and separate from Flask routes.
- Inject the clock into date-dependent services. Use explicit timezones and fixed test dates.
- Use a temporary database and upload directory per test; never reset a user's database.
- Use meaningful assertions with independently worked examples. Do not compute expected
  answers by calling the production function being tested.
- Add a regression test for every substantive bug found during development.
- Do not change the agreed scope or test expectations to hide a failure. A demonstrably
  wrong test may be corrected, but record the evidence and rationale.
- Run property tests with recorded settings/seeds where applicable. Preserve failing cases.
- No stubs or success-shaped fake data on required paths. Label demo records as synthetic.
- Do not claim academic mastery, validated educational weights, optimal scheduling,
  improved exam results or human usability from software tests alone.

## Living records

Update docs/PROGRESS.md at each gate. Create docs/DECISIONS.md for concise engineering
choices and docs/AI_ASSISTANCE.md for an honest record of agent-assisted work. Record
relevant function/file locations so the student can later inspect and explain them.
Do not write Criterion A–E submissions, fabricate personal development experiences,
or claim that this generated code was independently authored by the student.

## Definition of done

All required acceptance cases in brief/TEST_CONTRACT.md are implemented and actually
run. Unit, integration, randomized invariant and Chromium end-to-end tests pass.
The app works with a fresh database and does not depend on demo data. Setup and test
commands are documented and checked. Final evidence includes test outcomes, browser
screenshots, known limitations, algorithm explanations and a short first-use guide.
A core blocker or unexecuted mandatory test means the product is not fully verified.
