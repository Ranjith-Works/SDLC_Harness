---
name: prd
description: Generate the Product Requirements Document (harness/01-PRD.md) from the intake (greenfield) or codebase map + feature ask (brownfield), using templates/PRD.md. Use after intake is approved.
---

# /sdlc:prd — Product Requirements Document

## Preconditions
- `harness/STATE.md` exists and `gates.intake` is `approved`. If not, tell the user to finish
  intake and run `/sdlc:gate` first.

## Steps
1. Read the intake source: `harness/00-INTAKE.md` (greenfield) OR `harness/00-CODEBASE-MAP.md`
   (brownfield). For brownfield, also confirm the specific feature being added.
2. Load `templates/PRD.md` from the plugin and fill EVERY section with concrete, grounded
   content. Number functional requirements **FR-1, FR-2, …** — these IDs are traced downstream.
3. For brownfield: scope the PRD to the new feature; note how it fits the existing product,
   and add non-goals that protect existing behavior.
4. Write `harness/01-PRD.md`.
5. Set `harness/STATE.md` `current_stage: prd`. Leave `gates.prd: pending`.
6. Tell the user: review the PRD, then run `/sdlc:gate` to approve it before `/sdlc:stories`.

## Rules
- No invented users, metrics, or requirements beyond what intake/feature ask supports — if you
  must assume, label it under Constraints & Assumptions.
- Keep FRs atomic and testable (each maps to >=1 story later).
