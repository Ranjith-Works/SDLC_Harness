---
name: gate
description: Tollgate between SDLC stages. Validates the current stage's artifact (structure + content) and requires explicit human approval before advancing. Records the approval in harness/STATE.md. Use after finishing each stage.
disable-model-invocation: true
---

# /sdlc:gate — validate + approve the current stage

Only the user invokes this. It is the human-in-the-loop tollgate.

## Steps
1. Read `harness/STATE.md`; determine `current_stage` and its artifact.
2. **Validate structure** (for doc artifacts PRD/US/TRD/REVIEW):
   `python <plugin>/scripts/validate_artifact.py "<artifact path>"`
   (hand the user the command if sandbox Python fails). Report missing sections / stub warnings.
3. **Validate content** yourself: does the artifact actually satisfy this stage's intent?
   - prd: FRs atomic & testable; goals/non-goals present.
   - stories: every FR covered; ACs concrete.
   - trd: story->impl map complete; test command specified.
   - implement: files exist; scoped to stories.
   - test: ACs mapped to tests; report present.
   - review: verdict computed; PASS requires ≥80 and no hard gate.
4. Present a short validation summary and the go/no-go recommendation.
5. **Ask the user to approve.** Only on explicit approval, set `gates.<stage>: approved` in
   `harness/STATE.md` and append a line to the STATE Log. If not approved, leave `pending` and
   tell them what to fix.
6. Name the next stage command.

Never advance a stage without the user's explicit approval. Never approve a failing review.
