---
name: stories
description: Decompose the approved PRD into user stories with acceptance criteria (harness/02-USER-STORIES.md), each traced to a PRD functional requirement, using templates/USER-STORIES.md. Use after the PRD gate passes.
---

# /sdlc:stories — User Stories

## Preconditions
- `gates.prd: approved` in `harness/STATE.md`. Otherwise stop and tell the user to run
  `/sdlc:gate` on the PRD first.

## Steps
1. Read `harness/01-PRD.md`. Load `templates/USER-STORIES.md`.
2. Decompose every functional requirement (FR-#) into one or more stories **US-1, US-2, …**.
   - Standard form: "As a <role>, I want <capability>, so that <benefit>."
   - Each story: a **Traces to: FR-#** line and **acceptance criteria AC-#.#** in
     Given/When/Then form. ACs must be concrete and testable.
3. Fill the Story Index table (US-# | Title | PRD refs | Priority).
4. **Coverage check:** every FR must be covered by >=1 story. List any FR not yet covered and
   fix it — do not leave gaps.
5. Write `harness/02-USER-STORIES.md`; set `current_stage: stories`, `gates.stories: pending`.
6. Tell the user to review, then run `/sdlc:gate`, then `/sdlc:trd`.

Keep ACs minimal but sufficient — they are the definition of done for implementation and tests.
