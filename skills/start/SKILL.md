---
name: start
description: Entry point for an SDLC harness run. Detects or asks whether the project is greenfield or brownfield, scaffolds the working harness/ directory + STATE.md in the target, and routes to intake. Use at the very beginning of driving a project through the lifecycle.
disable-model-invocation: true
---

# /sdlc:start — begin an SDLC run

You are starting a governed SDLC run. Artifacts live in `<target>/harness/`. Stages advance
only through `/sdlc:gate` (human-approved tollgates).

## Steps
1. **Determine the target directory** (default: current working dir). Confirm with the user.
2. **Determine mode:**
   - If the target already contains source code / manifests (package.json, requirements.txt,
     pyproject.toml, go.mod, existing app dirs) → **brownfield**.
   - If empty or only docs → **greenfield**.
   - State your detection and ask the user to confirm greenfield vs brownfield. Do not guess
     silently.
3. **Pick the eval toolchain.** Set STATE.md `stack:` and, for anything other than a built-in
   (`python`/`js`), write **`harness/eval.config.json`** declaring the project's own
   test / complexity / security commands (see the schema in the plugin README "Works with any
   stack"). For brownfield, take these commands from the codebase-analyzer's map. For
   greenfield, they come from the intake interview (default `python` now; update if it changes).
   The eval degrades gracefully and reports any criterion with no tool as skipped — so a stack
   without a security/complexity tool still runs, it just flags those.
4. **Scaffold the harness** by running:
   `python <plugin>/scripts/init_harness.py --target "<target>" --mode <mode> --stack <stack>`
   (On this machine, prefer running Python via the user's terminal if the sandbox Python
   fails — hand them the exact command.)
5. **Route to intake:**
   - greenfield → tell the user to run `/sdlc:intake-greenfield`
   - brownfield → tell the user to run `/sdlc:prd` after you dispatch the **codebase-analyzer**
     sub-agent to produce `harness/00-CODEBASE-MAP.md` (do that dispatch now).
6. Print the pipeline order and remind them each stage ends at `/sdlc:gate`.

Keep output short. Never begin PRD work here — this skill only sets up state and routes.
