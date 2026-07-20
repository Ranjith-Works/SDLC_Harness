# sdlc — an SDLC harness for Claude Code

A Claude Code **plugin** that drives any project through the full software development
lifecycle as a governed, traceable pipeline:

```
intake → PRD → User Stories → [UX design] → TRD → Implement → Test → Review (weighted eval) → [IaC/CI-CD]
```

The bracketed stages are **conditional**: `UX design` runs only for projects with a UI, and
`IaC/CI-CD` only for projects with a deploy target — so a backend library keeps the short
7-stage pipeline. Each stage produces a **file artifact** under `<project>/harness/`, and each
stage advances only through a human-approved **tollgate** (`/sdlc:gate`) — including a
**deployment gate** that blocks `terraform apply` / `kubectl apply` / `docker push` / … until the
infrastructure is reviewed and approved. It works for **greenfield** (new build — interviews you
for the stack) and **brownfield** (extends an existing codebase after a read-only analysis)
projects, and is domain- and stack-agnostic (built-ins for python/js/go/java/rust/ruby; any other
stack plugs in via `eval.config.json`).

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
`/sdlc:prd`, `/sdlc:stories`, `/sdlc:design` (UI projects), `/sdlc:trd`, `/sdlc:implement`,
`/sdlc:test`, `/sdlc:review`, `/sdlc:iac` (deploy projects), `/sdlc:gate`, `/sdlc:status`.

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
  | Python | Python 3 | `pip install pytest pytest-cov radon bandit` |
  | JS / TS | Python 3 + Node/npm | `npm i -D eslint` (npm audit is built in) |
  | Go / Java / Rust / Ruby | Python 3 | built-in defaults (`go test`/`gosec`, `mvn`, `cargo`/`clippy`, `rspec`/`brakeman`) — override in `eval.config.json` |
  | Any other | Python 3 | your stack's own test / coverage / lint / security CLIs, named in `harness/eval.config.json` |
  | UI (visual/a11y) | Python 3 + the tool | e.g. `npx playwright`, `axe`, `@lhci/cli` — named in the `ux` slot |
  | Deploy (IaC lint) | Python 3 + the tool | e.g. `tflint`, `checkov`, `hadolint`, `actionlint` — named in the `iac` slot |

- **`python` vs `python3`:** on macOS/Linux the command is often `python3`. Alias it, or edit
  the command prefix in `hooks/hooks.json` and the skill instructions.

## Usage

```
/sdlc:start                 # detect greenfield vs brownfield + ui/deploy scope, scaffold harness/ + STATE.md
/sdlc:intake-greenfield     # (greenfield) interview: stack + key decisions -> 00-INTAKE.md
                            # (brownfield) start dispatches the codebase-analyzer -> 00-CODEBASE-MAP.md
/sdlc:prd                   # -> harness/01-PRD.md          (then /sdlc:gate)
/sdlc:stories               # -> harness/02-USER-STORIES.md (then /sdlc:gate)
/sdlc:design                # (ui only) -> harness/04-UX-SPEC.md (then /sdlc:gate)
/sdlc:trd                   # -> harness/03-TRD.md          (then /sdlc:gate)
/sdlc:implement             # implementer agent, one story at a time (then /sdlc:gate)
/sdlc:test                  # test-author agent (+ visual/a11y for UI) -> 05-TEST-REPORT.md (then /sdlc:gate)
/sdlc:review                # reviewer agent + eval_harness.py -> 06-REVIEW.md + results.json
/sdlc:iac                   # (deploy only) deploy-author -> IaC/CI-CD + 07-DEPLOY.md (gate = deployment gate)
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
`prd → stories → [design] → trd → implement → test → review → [iac]`, approving each
`/sdlc:gate`. Greenfield? it interviews you for the stack. Brownfield? it analyzes your repo
first (read-only). UI and deploy stages appear only if the project has a UI / a deploy target.

**What you end up with** — a `harness/` folder holding a full **spec → UX design → code → tests
→ infra** trail (traceable by FR/US/NFR IDs), and a deterministic **/100 scorecard**: tests
pass-rate, **coverage %**, requirements coverage, mechanical traceability, security, readability,
**non-functional review**, and (where they apply) **UI/UX visual+a11y** and **IaC/CI-CD
readiness** — plus a `git commit` blocked until the review gate passes and a **deploy blocked
until the deployment gate passes**.

**One honest note:** the harness *structures and scores* the work and enforces the gates — you
still approve each stage and answer the intake. It makes engineering judgment traceable and
reproducible; it doesn't replace it.

## What ships in the box

```
.claude-plugin/plugin.json   manifest (name: sdlc)
CLAUDE.md                    operating guardrails (grounding, safety, process)
skills/                      12 orchestration commands (/sdlc:*), incl. design + iac
agents/                      codebase-analyzer, implementer, test-author, reviewer, deploy-author
hooks/hooks.json             audit log, artifact validation, commit gate, deployment gate
scripts/                     eval_harness.py, trace_check.py, validate_artifact.py, init_harness.py, hook_*.py
templates/                   PRD, USER-STORIES, UX-SPEC, TRD, DEPLOY, REVIEW section templates
```

## Working artifacts (written into the target project)

```
<target>/harness/
├── STATE.md            mode, stack, ui/deploy flags, current stage, per-stage gate approvals
├── 00-INTAKE.md        greenfield stack + decisions   (or)
├── 00-CODEBASE-MAP.md  brownfield analyzer output
├── 01-PRD.md  02-USER-STORIES.md  03-TRD.md  05-TEST-REPORT.md  06-REVIEW.md
├── 04-UX-SPEC.md       (ui projects) screens, states, a11y, responsive, design tokens
├── 07-DEPLOY.md        (deploy projects) environments, IaC, CI/CD, gates, rollback
├── screenshots/        (ui projects) per-screen+state captures — UX review evidence
├── eval.config.json    (optional) per-stack test/coverage/complexity/security + ux/iac commands
├── reviewer.json       LLM-judged Boolean checklists w/ evidence (input to the eval)
├── coverage.json       test-coverage report (written during review)
├── results.json        versioned eval results (regression baseline)
└── AUDIT.log           stage/subagent transitions (from hooks)
```

## The weighted eval (the showpiece)

`/sdlc:review` runs `scripts/eval_harness.py`: a reproducible **/100** scorer with **hard
gates**. Pass = total **≥ 80** AND no hard gate tripped. Re-runs compare against the previous
`results.json` for **regression**.

The score is **normalized over the criteria that apply** to the project. Nine criteria are
always scored; two are **conditional** — `ux` only when the project has a UI, `iac` only when it
has a deploy target. A non-applicable criterion is dropped from *both* numerator and denominator,
so a backend library is never penalized for having no UI or pipeline. (`total = Σ(frac×wt over
applicable) ÷ Σ(wt over applicable) × 100`.)

| Criterion | Raw wt | Applies | Source | Hard gate |
|---|---:|---|---|---|
| Tests pass rate | 20 | always | project's test runner | |
| Test coverage | 10 | always | coverage tool (pytest-cov / lcov / cobertura / configurable) | |
| Functional review (requirements) | 20 | always | reviewer **Boolean checklist** (per-FR/AC → yes÷total) | |
| Traceability | 10 | always | `trace_check.py` — FR→US→TRD, NFR→TRD ID linkage (**mechanical**) | |
| Code quality / complexity | 10 | always | radon (py) / eslint (js) / configurable | |
| Security scan | 15 | always | bandit (py) / npm audit (js) / configurable | **high severity → FAIL** |
| Technical review (readability) | 10 | always | reviewer **Boolean checklist** (yes÷total) | |
| No secrets / PII | 5 | always | pattern scan (language-agnostic) | **any hit → FAIL** |
| Non-functional review (avail/perf/reliability) | 10 | always | reviewer **Boolean checklist** (per-NFR + reliability) | |
| UI/UX review + visual/a11y | 15 | **ui only** | ux tool (Playwright/axe/…) + reviewer checklist | |
| IaC + CI/CD readiness | 15 | **deploy only** | iac tool (tflint/checkov/…) + reviewer checklist | optional (configurable) |

**Most points are pure mechanical; the review dimensions are counts of yes/no checks with
evidence** — so the same code yields the same verdict. See [`DETERMINISM.md`](DETERMINISM.md)
for the full LLM-vs-mechanical map and the normalization rules.

### Works with any stack

- **The pipeline is fully language-agnostic** — the PRD/stories/UX-spec/TRD are Markdown, and
  code + tests are written in whatever language the project uses.
- **The scorecard is too.** The review dimensions (functional, technical, nfr, traceability,
  secrets — all language-neutral) need no stack-specific tools. The tool-based criteria (tests,
  coverage, complexity, security, and the ux/iac mechanical halves) are **pluggable**: `python`,
  `js`, `go`, `java`, `rust`, and `ruby` are built in, and any other stack declares its own tools
  in an optional **`harness/eval.config.json`**:

  ```json
  {
    "stack": "go",
    "test":       { "cmd": "go test ./...", "pass_regex": "^ok\\b", "fail_regex": "^FAIL\\b" },
    "coverage":   { "cmd": "go test ./... -cover", "kind": "coverage-generic", "percent_regex": "coverage:\\s*([\\d.]+)%" },
    "complexity": { "cmd": "gocyclo -over 15 .", "kind": "exit-code" },
    "security":   { "cmd": "gosec ./...",        "kind": "exit-code", "hard_gate": true },
    "ui": true,
    "ux":  { "cmd": "npx playwright test", "kind": "exit-code" },
    "deploy_target": "aws",
    "iac": { "cmd": "checkov -d infra --compact", "kind": "exit-code", "hard_gate": false }
  }
  ```

  Recognized coverage `kind`s: `coverage-py`, `coverage-generic` (scrape a percent via
  `percent_regex`, or parse an lcov/cobertura report). Complexity/security/ux/iac `kind`s:
  `radon`, `eslint`, `bandit`, `npm-audit`, and the generic **`exit-code`** (any tool — score from
  its return code, 0 = pass). Resolution order: `eval.config.json` → built-in `stack` → skip. A
  criterion with **no** tool configured is reported **skipped** (scores 0, flagged loudly) rather
  than silently ignored. Applicability (`ui`/`deploy`) is taken from the STATE.md or config flags,
  else auto-detected — override at the CLI with `--ui on|off` / `--deploy on|off`.

## Governance hooks

- **PreToolUse / Bash — commit gate** — blocks `git commit`/`git push` until the review gate has passed.
- **PreToolUse / Bash — deployment gate** — blocks `terraform apply` / `kubectl apply` /
  `docker push` / `helm upgrade` / `gh workflow run` / … until **both** the review and iac gates
  are approved.
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
