---
name: implement
description: Build the code per the approved TRD, one user story at a time, delegating each story to the implementer sub-agent. Use after the TRD gate passes.
---

# /sdlc:implement — build per TRD

## Preconditions
- `gates.trd: approved` in `harness/STATE.md`.

## Steps
1. Read `harness/03-TRD.md` and `harness/02-USER-STORIES.md` (and, if `ui: true`,
   `harness/04-UX-SPEC.md`). Build the ordered list of stories (respect priority / dependencies).
2. For **each story**, dispatch the **implementer** sub-agent with: the story + its ACs, the
   relevant TRD sections, and the intake/codebase-map conventions. One story per dispatch so
   changes stay scoped and traceable. For UI stories, hand it the relevant UX-spec screens/states/
   tokens — it must build every state (loading/empty/error/success), not just the happy path.
3. After each story returns, note the files changed in a running list. If the implementer
   flags a needed new dependency or a TRD gap, **stop and surface it to the user** — do not
   auto-approve dependencies.
4. When all stories are implemented, summarize: story -> files table. Set
   `current_stage: implement`, `gates.implement: pending`.
5. Tell the user to review the code, run `/sdlc:gate`, then `/sdlc:test`. (Infrastructure is NOT
   built here — for `deploy: true` projects it comes after review, via `/sdlc:iac`.)

## Rules
- Never let implementation touch unrelated code (esp. brownfield). Build strictly from
  artifacts; no invented APIs; no secrets/PII; dummy data only.
