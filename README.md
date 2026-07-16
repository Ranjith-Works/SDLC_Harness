# sdlc — an SDLC harness for Claude Code

A Claude Code **plugin** that drives any project through the full software development
lifecycle as a governed, traceable pipeline:

```
intake → PRD → User Stories → TRD → Implement → Test → Review (weighted eval)
```

Each stage produces a **file artifact** under `<project>/harness/`, and each stage advances
only through a human-approved **tollgate** (`/sdlc:gate`). It works for **greenfield** (new
build — interviews you for the stack) and **brownfield** (extends an existing codebase after a
read-only analysis) projects, and is domain- and stack-agnostic.

## Why a plugin
A plugin bundles skills + sub-agents + hooks + scripts into one versioned, namespaced unit
that drops into any repo. Everything is exposed as `/sdlc:*` commands.

## Install

**Recommended — via the plugin marketplace** (persistent, auto-updates). In Claude Code, run:

```
/plugin marketplace add Ranjith-Works/SDLC_Harness
/plugin install sdlc@sdlc-harness
```

Then `/plugin list` to confirm, and `/reload-plugins` if the commands don't appear yet. This is
not a VS Code extension — the commands are typed inside Claude Code, which clones the repo for
you (no manual download).

**Quick try / local development — via `--plugin-dir`** (session-only, no auto-update). Clone the
repo, then:

```bash
git clone https://github.com/Ranjith-Works/SDLC_Harness.git
claude --plugin-dir ./SDLC_Harness
```

Either way, these commands become available: `/sdlc:start`, `/sdlc:intake-greenfield`,
`/sdlc:prd`, `/sdlc:stories`, `/sdlc:trd`, `/sdlc:implement`, `/sdlc:test`, `/sdlc:review`,
`/sdlc:gate`, `/sdlc:status`.

**Updating:** `/plugin update sdlc@sdlc-harness` (pulls the latest published version).

### Runtime & prerequisites

- **Harness runtime:** **Python 3** on PATH — the *only* thing the plugin itself needs. It runs
  the orchestration glue (scaffold a state file, validate section headers, compute the weighted
  score, enforce hooks). Think of it like requiring `git` or `make`: a small (~30 MB) runner,
  **not** a project dependency, and it never ships into your repo.
- **Python never inspects your code.** Every real code check shells out to the *project's own*
  tools. What a team installs depends only on *their* stack:

  | Project stack | Harness needs | Eval toolchain to install |
  |---|---|---|
  | Python | Python 3 | `pip install pytest radon bandit` |
  | JS / TS | Python 3 + Node/npm | `npm i -D eslint` (npm audit is built in) |
  | Any other (Go, Rust, Java, …) | Python 3 | your stack's own test / lint / security CLIs, named in `harness/eval.config.json` |

- **`python` vs `python3`:** on macOS/Linux the command is often `python3`. Alias it, or edit
  the command prefix in `hooks/hooks.json` and the skill instructions.

## Usage

```
/sdlc:start                 # detect greenfield vs brownfield, scaffold harness/ + STATE.md
/sdlc:intake-greenfield     # (greenfield) interview: stack + key decisions -> 00-INTAKE.md
                            # (brownfield) start dispatches the codebase-analyzer -> 00-CODEBASE-MAP.md
/sdlc:prd                   # -> harness/01-PRD.md          (then /sdlc:gate)
/sdlc:stories               # -> harness/02-USER-STORIES.md (then /sdlc:gate)
/sdlc:trd                   # -> harness/03-TRD.md          (then /sdlc:gate)
/sdlc:implement             # implementer agent, one story at a time (then /sdlc:gate)
/sdlc:test                  # test-author agent -> harness/05-TEST-REPORT.md (then /sdlc:gate)
/sdlc:review                # reviewer agent + eval_harness.py -> 06-REVIEW.md + results.json
/sdlc:gate                  # validate current artifact + record human approval
/sdlc:status                # show where the run stands
```

Run `/sdlc:gate` after every stage. Nothing advances without your explicit approval.

## Quickstart — from install to meaningful results

**Step 0 — install your stack's tools** (so the scorecard is real):
`pip install pytest pytest-cov radon bandit` (Python) · `npm i -D eslint` (JS) · any other
stack → name its test/lint/security commands in `harness/eval.config.json`.

**Step 1 — install the plugin** (in Claude Code, via terminal):
```
claude plugin marketplace add Ranjith-Works/SDLC_Harness
claude plugin install sdlc@sdlc-harness
```

**Step 2 — run the pipeline on your project:** `/sdlc:start` → walk
`prd → stories → trd → implement → test → review`, approving each `/sdlc:gate`. Greenfield?
it interviews you for the stack. Brownfield? it analyzes your repo first (read-only).

**What you end up with** — a `harness/` folder holding a full **spec → design → code → tests**
trail (traceable by FR/US IDs), and a deterministic **/100 scorecard**: tests pass-rate,
**coverage %**, requirements coverage, mechanical traceability, security, readability — plus a
`git commit` that stays **blocked until the review gate passes**.

**One honest note:** the harness *structures and scores* the work and enforces the gates — you
still approve each stage and answer the intake. It makes engineering judgment traceable and
reproducible; it doesn't replace it.

## What ships in the box

```
.claude-plugin/plugin.json   manifest (name: sdlc)
CLAUDE.md                    operating guardrails (grounding, safety, process)
skills/                      10 orchestration commands (/sdlc:*)
agents/                      codebase-analyzer, implementer, test-author, reviewer
hooks/hooks.json             audit log, artifact validation, commit gate
scripts/                     eval_harness.py, validate_artifact.py, init_harness.py, hook_*.py
templates/                   PRD, USER-STORIES, TRD, REVIEW section templates
```

## Working artifacts (written into the target project)

```
<target>/harness/
├── STATE.md            mode, stack, current stage, per-stage gate approvals
├── 00-INTAKE.md        greenfield stack + decisions   (or)
├── 00-CODEBASE-MAP.md  brownfield analyzer output
├── 01-PRD.md  02-USER-STORIES.md  03-TRD.md  05-TEST-REPORT.md  06-REVIEW.md
├── eval.config.json    (optional) per-stack test/complexity/security commands
├── reviewer.json       LLM-judged Boolean checklists w/ evidence (input to the eval)
├── coverage.json       test-coverage report (written during review)
├── results.json        versioned eval results (regression baseline)
└── AUDIT.log           stage/subagent transitions (from hooks)
```

## The weighted eval (the showpiece)

`/sdlc:review` runs `scripts/eval_harness.py`: a reproducible **100-point** scorer with
**hard gates**. Pass = total **≥ 80** AND no hard gate tripped. Re-runs compare against the
previous `results.json` for **regression**.

| Criterion | Weight | Source | Hard gate |
|---|---:|---|---|
| Tests pass rate | 20 | project's test runner | |
| Test coverage | 10 | coverage tool (pytest-cov / configurable) | |
| Functional review (requirements) | 20 | reviewer **Boolean checklist** (per-FR/AC → yes÷total) | |
| Traceability | 10 | `trace_check.py` — FR→US→TRD ID linkage (**mechanical**) | |
| Code quality / complexity | 10 | radon (py) / eslint (js) / configurable | |
| Security scan | 15 | bandit (py) / npm audit (js) / configurable | **high severity → FAIL** |
| Technical review (readability) | 10 | reviewer **Boolean checklist** (yes÷total) | |
| No secrets / PII | 5 | pattern scan | **any hit → FAIL** |

**~70 of 100 points are pure mechanical; the other 30 are counts of yes/no review checks with
evidence** — so the same code yields the same verdict. See [`DETERMINISM.md`](DETERMINISM.md)
for the full LLM-vs-mechanical map.

### Works with any stack

- **The pipeline is fully language-agnostic** — the PRD/stories/TRD are Markdown, and code +
  tests are written in whatever language the project uses.
- **The scorecard is too.** 4 of the 8 criteria (functional review, traceability, technical
  review, secrets/PII = 45 pts) need no stack-specific tools. The 4 tool-based criteria (tests,
  coverage, complexity, security = 55 pts) are **pluggable**: `python` and `js` are built in, and
  any other stack declares its own tools in an optional **`harness/eval.config.json`**:

  ```json
  {
    "stack": "go",
    "test":       { "cmd": "go test ./...", "pass_regex": "ok\\b", "fail_regex": "FAIL" },
    "complexity": { "cmd": "gocyclo -over 10 .", "kind": "exit-code" },
    "security":   { "cmd": "gosec ./...",        "kind": "exit-code", "hard_gate": true }
  }
  ```

  Recognized `kind`s: `radon`, `eslint`, `bandit`, `npm-audit`, and the generic **`exit-code`**
  (any tool — score from its return code, 0 = pass). Resolution order:
  `eval.config.json` → built-in `stack` → skip. A criterion with **no** tool configured is
  reported **skipped** (scores 0, and is flagged loudly) rather than silently ignored — so the
  harness runs on any stack and is honest about what it did and didn't measure.

## Governance hooks

- **PreToolUse / Bash** — blocks `git commit`/`git push` until the review gate has passed.
- **PostToolUse / Write|Edit** — validates `harness/*.md` artifacts have their required
  sections (non-blocking warning).
- **SubagentStop / SessionStart** — append lifecycle events to `harness/AUDIT.log`.

## Guardrails

Build only from the artifacts (no invented APIs); no secrets/PII (dummy data only); no new
dependencies without asking; never mutate unrelated code; human approval at every gate; never
fake a green build. See `CLAUDE.md`.

## Demos

Two worked end-to-end runs live alongside this plugin — see `DEMO.md`:
- **Greenfield:** a URL shortener API built from an idea + a stack interview.
- **Brownfield:** a new feature added to a copy of an existing project.
