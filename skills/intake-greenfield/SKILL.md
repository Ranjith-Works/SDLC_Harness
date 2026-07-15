---
name: intake-greenfield
description: Greenfield intake. Interactively interviews the user for the tech stack and key product/engineering decisions, then writes harness/00-INTAKE.md and a project CLAUDE.md. Use for a new-from-scratch project before writing the PRD.
---

# /sdlc:intake-greenfield — stack + decisions interview

Greenfield only. You are gathering just enough to ground the PRD/TRD. **Interview the user** —
ask real questions, do not assume a stack.

## Interview (ask, don't invent)
Use the AskUserQuestion tool where possible. Cover:
1. **Product idea** — one or two sentences on what we're building and for whom.
2. **Language / runtime** (e.g. Python, Node/TS, Go).
3. **Framework** (e.g. FastAPI/Flask, Express/Nest) — offer sensible options for the chosen
   language.
4. **Datastore / persistence** (in-memory, SQLite, Postgres, Redis, none).
5. **Interface** (REST API, CLI, web UI) and any auth needs.
6. **Testing framework** + how they want to run tests.
7. **Key constraints** (perf targets, deploy target, must-use or must-avoid libraries).

## After the interview
1. Write `harness/00-INTAKE.md` capturing: product idea, chosen stack, decisions + rationale,
   constraints, and the **eval stack selector** (`python` or `js`).
2. Update `harness/STATE.md`: set `stack:` to match, set `gates.intake: approved` only after
   the user confirms the intake is correct (otherwise leave `pending`). If the chosen stack is
   not a built-in (`python`/`js`), also write **`harness/eval.config.json`** with the project's
   test / complexity / security commands (schema in the README "Works with any stack") so the
   review scorer covers this stack.
3. Write/refresh a project **CLAUDE.md** in the target root with: the stack, conventions to
   follow, the test/run commands, and the harness guardrails (no secrets/PII, dummy data,
   no new deps without asking, build only from artifacts).
4. Tell the user to review `00-INTAKE.md`, run `/sdlc:gate` to approve intake, then `/sdlc:prd`.

Keep it tight. Do not start the PRD here.
