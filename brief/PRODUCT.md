# Product contract — approved replacement scope

## Purpose

Students struggle to decide what to practise, how to distribute limited study time,
and how to recover when their plans change. Build a local web application that turns
teacher feedback and explicitly entered practice outcomes into study targets, then
creates and repairs a personalised study plan.

Core loop:
Feedback / selected target → planning need → priority → schedule → practice outcome
or changed availability → updated evidence → repaired future schedule.

The app is a planner using academic evidence. It is not an automated examiner.

## Required user experience

1. Register, log in and choose a timezone. Create subjects and optional HL/SL labels.
   Subject names are user-defined; Mathematics and Economics are illustrative demo data.
2. Enter an exam date and link relevant practice targets. Enter weekly available minutes
   and one-off date overrides, including zero availability.
3. Add an assessment/feedback note with a title, subject, pasted teacher feedback and
   optional overall grade. Optionally attach a PDF for reference only.
4. Create one or a few practice targets from the note, or directly. Main fields are
   subject, topic/skill, a plain-language practice goal and a starting practice need.
   Offer a sensible default practice budget with an optional edit. Do not ask the
   student to enter question-level marks or fill in a diagnostic schema.
5. Generate a seven-day plan of daily study blocks. Show the activity, duration and
   one short reason, plus capacity remaining and any work not scheduled.
6. Start/pause/finish/skip a session; optionally record an outcome or target-specific
   score. A session can be completed without an outcome: no new ability evidence is
   then inferred. Finishing a block records work, not mastery.
7. Adjust the plan after missed sessions, changed deadlines/availability or new
   evidence. Explain significant changes and protect completed/in-progress/locked work.
8. Show actual study time, completion, recent reported difficulty, recorded evidence
   and remaining practice. Do not label a lower priority as proof of better ability.

Use approximately these screens: Dashboard, Feedback & Targets, Study Plan, Progress,
and Settings. Put exams/availability where they naturally support plan setup. Use
progressive disclosure instead of displaying database fields. A target card should
read like “Economics · Price floors · Develop evaluation” with a next action.

## Deliberately excluded from this build

No OCR, handwriting lab, CNN, image understanding, independent essay marking, mandatory
LLM, generated quizzes, automatic free-text grading, embeddings, vector database,
external resource search, Google Calendar/OAuth, email/password-reset services,
notifications, hosted deployment, multi-agent product architecture or background
job infrastructure. Do not install model runtimes. Do not implement optional AI
feedback organisation until a separate future request authorizes it.

A PDF attachment is optional supporting material, not a prerequisite. Teacher
feedback is pasted or entered manually. A complete app must work with only manual
inputs. This is an intentional scope reduction, not a missing dependency to fill later.

## Stack and architecture

Use Python, Flask (application factory and route modules), SQLAlchemy, SQLite, Jinja,
HTML/CSS and modest vanilla JavaScript. Use standard password hashing/session tools
and CSRF protection. Use pytest, Hypothesis and Playwright's Python integration for
tests, plus a lightweight linter. Use a supported Python/dependency combination,
record actual versions and pin reproducible dependencies after checking them.

No React, mandatory frontend build system, Docker, Redis, Celery, optimiser service
or cloud database. Keep static assets local so runtime works without the internet.
A developer tool's subscription/network access is separate from app runtime costs.

Suggested service boundaries: evidence/priority, initial scheduling, schedule repair,
session lifecycle and progress queries. Pass plain data into the computational
services; routes validate/authorize, call services and persist results.

## Data design

Design a small relational schema rather than copying the previous 13-table schema.
Suggested entities are:
- User; user-owned Subject.
- FeedbackEntry (assessment title, teacher text, optional overall grade/attachment).
- Exam (user/subject/date).
- PracticeTarget (subject, topic/skill labels, practice goal, optional feedback/exam,
  optional study deadline, bounded requested minutes, active/archive state).
- EvidenceEntry (target, date, explicit outcome/rating, source, optional earned/possible
  marks, linked session/feedback, provenance and correction state).
- WeeklyAvailability and DateAvailabilityOverride.
- StudySession (target, date, planned/actual duration, lifecycle, lock, replacement link).
- SessionEvent or similarly small audit record for schedule changes.

These are suggested boundaries, not a demand for unnecessary tables. Normalize real
relationships and enforce ownership. Retain source evidence; derived scores can be
calculated or cached, but they must be reproducible. Use migrations for schema changes.
Do not create a new student record every time the schedule is recalculated.

## Historical draft reconciliation

The attached IA draft's rationale on pages 3–4 describes a multi-model AI stack and
broader success criteria. Those are superseded for this new project. Retain its
central concerns: allocating study time, exam deadlines, session completion,
rescheduling, progress and a simple interface (not automatic analysis/quiz promises).
Do not modify the draft PDF or Criterion A–C text during this coding task.

## Design values

A smaller real product is better than impressive-looking placeholders. Keep planned
workload distinct from academic performance, and source labels distinct from verified
truth. Explicitly reported practice difficulty is not an independently measured
ability percentage. A model, if added later, must remain optional to the core loop.
