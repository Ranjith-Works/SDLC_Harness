---
name: trd
description: Produce the Technical Requirements Document (harness/03-TRD.md) from the PRD + user stories, including architecture, data model, API design, a story->implementation map, and testing strategy, using templates/TRD.md. Use after the stories gate passes.
---

# /sdlc:trd — Technical Requirements Document

## Preconditions
- `gates.stories: approved` in `harness/STATE.md`.
- If `ui: true`, also `gates.design: approved` (the TRD builds on the UX spec).

## Steps
1. Read `harness/01-PRD.md`, `harness/02-USER-STORIES.md`, the intake source
   (`00-INTAKE.md` or `00-CODEBASE-MAP.md`), and — if `ui: true` — `harness/04-UX-SPEC.md`.
   Load `templates/TRD.md`.
2. Design the technical solution grounded in the chosen/existing stack. For **brownfield**,
   match the architecture and conventions in the codebase map; add a Rollout/Migration
   section describing safe integration.
3. Fill every section. The **Story -> Implementation Map** table is mandatory: each US-# maps
   to the specific components/files that will satisfy it. Every story must appear.
4. Specify the exact **test command** and per-AC testing approach in Testing Strategy.
5. Fill **Non-Functional Design**: for each NFR-# in the PRD, give the architectural provision +
   how it's verified (reference every NFR-# so traceability holds). If `deploy: true`, also fill
   **Deployment & Infrastructure** (deploy target, IaC tool, CI/CD platform, environments) — the
   concrete files come later in `/sdlc:iac`.
6. Do not invent libraries/APIs. Flag any needed new dependency explicitly for user approval
   (do not assume it).
7. Write `harness/03-TRD.md`; set `current_stage: trd`, `gates.trd: pending`.
8. Tell the user to review, run `/sdlc:gate`, then `/sdlc:implement`.
