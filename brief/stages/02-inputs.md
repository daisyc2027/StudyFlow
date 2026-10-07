# Stage 02 — input workflow and relational records

## Build

Read DOMAIN_RULES.md before finalizing the schema, especially finite workload and
session accounting. Create migrations for the minimal records needed by the product.
Document relationships and constraints in docs/DATA_MODEL.md.

Implement user-owned subjects, feedback notes, practice targets, exams, recurring
weekly capacity and per-date overrides. A single feedback note can support several
targets. Overall marks stay on the feedback note. No automatic text interpretation.

Target creation should be short: topic/skill, actionable practice goal, starting
practice need, optional exam; default the practice budget to 60 minutes and allow an
edit. An unknown starting need is valid. Set helpful labels and explanations, not a
raw database editor. Allow editing/archive without destroying referenced history.

Seed an opt-in synthetic Maths/Economics example with dates relative to a supplied
seed date. Do not silently create demo users on production startup. User-facing subject
support is not restricted to those examples and no official syllabus coverage is claimed.

## Gate

Browser and HTTP tests create/edit the inputs and retrieve them after restart. Test
zero override, duplicate weekly day, invalid minutes/marks, foreign user IDs and correct
exam ownership/subject linkage. No ORM relationship silently joins another user's data.
Core flow works without files, AI or external accounts. Update progress and proceed.
