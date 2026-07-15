---
name: test
description: Author and run tests keyed to acceptance criteria, delegating to the test-author sub-agent, and record harness/05-TEST-REPORT.md. Use after the implement gate passes.
---

# /sdlc:test — author + run tests

## Preconditions
- `gates.implement: approved` in `harness/STATE.md`.

## Steps
1. Dispatch the **test-author** sub-agent. It reads the stories/ACs, TRD testing strategy, and
   the implemented code; writes tests in the project's framework; runs the test command; and
   writes `harness/05-TEST-REPORT.md` with an AC -> test map and pass/fail totals.
2. If tests fail because of a real code defect, report it to the user and recommend re-running
   `/sdlc:implement` for the affected story — do NOT weaken tests to make them pass.
3. Set `current_stage: test`, `gates.test: pending`.
4. Tell the user to review the test report, run `/sdlc:gate`, then `/sdlc:review`.

## Rules
- Every acceptance criterion should map to at least one test. Flag any AC left uncovered.
