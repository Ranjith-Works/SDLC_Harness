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
3. **Pick the eval toolchain.** Infer `stack:` from the manifests you found (package.json→js,
   go.mod→go, pyproject/requirements→python, Cargo.toml→rust, pom.xml/build.gradle→java,
   Gemfile→ruby) — do NOT default silently to python. Confirm with the user. For anything other
   than a built-in (`python`/`js`/`go`/`java`/`rust`/`ruby`), write **`harness/eval.config.json`**
   declaring the project's own test / coverage / complexity / security commands (schema in the
   README "Works with any stack"). The eval degrades gracefully and reports any criterion with no
   tool as skipped — so a stack without a tool still runs, it just flags those.
4. **Determine UI + deploy scope** (they add conditional stages + scoring):
   - `ui`: does the project have a user interface? (front-end files, or the intake says "web UI").
   - `deploy`: does it have a deploy target? (Dockerfile / IaC / CI workflows, or the intake names one).
   - State your detection and confirm with the user. These are recorded as STATE.md `ui:` / `deploy:`
     flags; a UI adds the `design` stage + `ux` scoring, a deploy target adds the `iac` stage +
     deployment gate. A pure backend library sets both false and keeps the short 7-stage pipeline.
5. **Scaffold the harness** by running (add `--ui` and/or `--deploy` per step 4):
   `python <plugin>/scripts/init_harness.py --target "<target>" --mode <mode> --stack <stack> [--ui] [--deploy]`
   (On this machine, prefer running Python via the user's terminal if the sandbox Python
   fails — hand them the exact command.)
6. **Route to intake:**
   - greenfield → tell the user to run `/sdlc:intake-greenfield`
   - brownfield → tell the user to run `/sdlc:prd` after you dispatch the **codebase-analyzer**
     sub-agent to produce `harness/00-CODEBASE-MAP.md` (do that dispatch now).
7. Print the pipeline order (including `design` if `ui`, and `iac` if `deploy`) and remind them
   each stage ends at `/sdlc:gate`.

Keep output short. Never begin PRD work here — this skill only sets up state and routes.
