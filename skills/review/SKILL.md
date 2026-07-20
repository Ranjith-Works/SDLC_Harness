---
name: review
description: Run the weighted eval harness (scripts/eval_harness.py) plus the reviewer sub-agent to score the project out of 100 with hard gates, write harness/06-REVIEW.md + results.json, and compare against the previous run for regression. Use after the test gate passes.
---

# /sdlc:review — weighted eval scorecard

## Preconditions
- `gates.test: approved` in `harness/STATE.md`.

## Determinism model (what this stage optimizes)
The score is split so most of it is mechanical and the rest is reproducible, and it is
**normalized over the criteria that apply** to the project (see below):
- **Mechanical (deterministic):** tests pass-rate, **test coverage %**, **traceability**
  (computed by `scripts/trace_check.py` — FR→US→TRD→NFR ID linkage), complexity, security,
  secrets, plus the mechanical halves of ux (visual/a11y tool) and iac (IaC lint).
- **LLM-judged, as Boolean checklists:** the reviewer answers atomic yes/no questions with
  evidence; the scorer aggregates each criterion as (yes ÷ total). No holistic floats.
- **Normalization / applicability:** nine always-on criteria, plus `ux` (only if `ui: true`) and
  `iac` (only if `deploy: true`). A non-applicable criterion is dropped from both numerator and
  denominator — a backend library is never penalized for having no UI or pipeline.

## Steps
1. **If `ui: true`, capture UX evidence first**: drive the running UI (Playwright MCP / browser
   tool) and save a screenshot per screen+state into `harness/screenshots/`. The reviewer cites
   these in its `ux` checklist.
2. Dispatch the **reviewer** sub-agent. It reads STATE.md `ui:`/`deploy:` flags and produces
   Boolean checklists in `harness/reviewer.json`: **Functional** (per-FR implemented?, per-AC
   tested?), **Technical** (single-purpose functions?, no hallucinated APIs?, errors handled?,
   conventions matched?, no security smell?, no secrets/PII?), **NFR** (each NFR-# provisioned?,
   timeouts/retries?, graceful degradation?), and — when applicable — **UX** (states/a11y/
   responsive vs the spec, citing screenshots) and **IaC** (idempotent?, pinned?, secrets vaulted?,
   rollback?, gates-before-deploy?). Each item is `answer: true/false` + `evidence`. It does NOT
   score traceability (mechanical) or emit floats.
3. Run the deterministic scorer (hand the user the exact command if sandbox Python fails):
   `python <plugin>/scripts/eval_harness.py --target "<target>" --src "<code-dir>" --json`
   It reads `reviewer.json`, STATE.md (`stack:`, `ui:`, `deploy:`), and (if present)
   `harness/eval.config.json` to select the toolchain + applicability, runs the checks + secrets
   scan, writes versioned `harness/results.json`, and prints the scorecard + regression. Use
   `--ui on|off` / `--deploy on|off` only to override the detected/declared applicability.
   If the scorer reports **skipped** criteria (no tool configured for this stack), the review
   must call them out explicitly — a skipped tool-criterion scores 0, so either add the tool to
   `eval.config.json` or note in `06-REVIEW.md` why it is not applicable. Never present a
   skipped criterion as if it passed.
4. Fill `templates/REVIEW.md` into `harness/06-REVIEW.md`: the verdict (PASS if total ≥ 80 AND
   no hard gate tripped), the weighted (normalized) table, hard-gate status, reviewer findings,
   and the regression delta.
5. Set `current_stage: review`. Set `gates.review: approved` **only if verdict is PASS** and
   the user accepts it via `/sdlc:gate`. On FAIL, list the recommended fixes and which stage to
   return to. (For `deploy: true` projects, `/sdlc:iac` runs next, then its gate is the deploy gate.)

## Hard gates (force FAIL regardless of score)
- Security scan high-severity finding.
- Secrets / PII detected.
- Any `iac` mechanical check marked `hard_gate` (e.g. a failing infra security scan).

The review gate passing is what unblocks the commit hook; the iac gate is what unblocks deployment.
Do not mark either approved on a FAIL.
