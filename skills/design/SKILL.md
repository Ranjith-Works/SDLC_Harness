---
name: design
description: Produce the UX specification (harness/04-UX-SPEC.md) from the user stories — screens, component inventory, all states, accessibility, responsive behavior, and design tokens. Only for projects with a UI (STATE.md ui:true). Runs after the stories gate, before the TRD, which it feeds.
---

# /sdlc:design — UX specification

## Preconditions
- `ui: true` in `harness/STATE.md` (this stage only exists for projects with a UI).
- `gates.stories: approved` in `harness/STATE.md`.

## Steps
1. Read `harness/02-USER-STORIES.md` (and `00-INTAKE.md` for product/brand context). Every screen
   must trace to the stories it serves — reference US-# ids.
2. Fill `templates/UX-SPEC.md` into `harness/04-UX-SPEC.md`:
   - **Screens** (each traced to US-#), **Component Inventory**, **States** (loading/empty/error/
     success for each), **Accessibility** (keyboard, contrast, aria), **Responsive** (breakpoints),
     **Design Tokens**, and the **Visual / a11y Test Approach**.
   - Do NOT skip the non-happy states — they are the most common gap and are scored in review.
3. Decide the visual/a11y tooling (e.g. Playwright screenshots, axe, Lighthouse) and record the
   command in the spec so `/sdlc:test` and `/sdlc:review` can run it. If tooled, declare it in
   `harness/eval.config.json` under the `ux` slot so the `ux` mechanical check scores it. Example:
   ```json
   { "ux": { "cmd": "npx playwright test", "kind": "exit-code" } }
   ```
4. Set `current_stage: design`, `gates.design: pending`.
5. Tell the user to review `04-UX-SPEC.md`, run `/sdlc:gate`, then `/sdlc:trd` (the TRD builds on it).

## Rules
- Spec, not code — describe the UI; implementation happens in `/sdlc:implement`.
- Ground every screen in a user story; flag any story with a UI need the spec doesn't cover.
