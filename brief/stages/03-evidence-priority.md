# Stage 03 — evidence and priority algorithms

## Build

Implement the domain evidence/need and priority rules as pure, typed, documented Python
functions with explicit clock inputs. Keep source evidence, overall grades, ordinal
planning need and scheduling priority distinct. Expose a brief readable reason per
target; put numerical components under optional Details.

Wire initial target ratings and later explicit ratings into these functions. Store
updates through services rather than embedding formulas in views. Keep corrections
and request identity so retrying a request does not add another observation.

Write docs/ALGORITHMS.md with the actual formulas, worked examples, assumptions and
limitations. Explain that the weights are configurable planning choices, not validated
measures of ability. Do not create an algorithm for every CRUD route.

## Gate

Run independent example tests for zero/one/two/three observations, ordering, superseded
entries, unknown evidence, bounds, deadlines and waiting time. Assert monotonic priority
behaviour when one relevant input changes and other inputs remain fixed. Add randomized
bounds checks. Prove completion/missed work without a rating cannot alter need. Verify
priorities are computed from stored user-specific records, not demo constants.
