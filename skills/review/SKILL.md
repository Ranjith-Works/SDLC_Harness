---
name: review
description: Run the weighted eval harness (scripts/eval_harness.py) plus the reviewer sub-agent to score the project out of 100 with hard gates, write harness/06-REVIEW.md + results.json, and compare against the previous run for regression. Use after the test gate passes.
---

# /sdlc:review — weighted eval scorecard

## Preconditions
- `gates.test: approved` in `harness/STATE.md`.

## Determinism model (what this stage optimizes)
The score is split so most of it is mechanical and the rest is reproducible:
- **Mechanical (deterministic, ~70 pts):** tests pass-rate, **test coverage %**, **traceability**
  (computed by `scripts/trace_check.py` — FR→US→TRD ID linkage), complexity, security, secrets.
- **LLM-judged (~30 pts), as Boolean checklists:** the reviewer answers atomic yes/no questions
  with evidence; the scorer aggregates each criterion as (yes ÷ total). No holistic floats.

## Steps
1. Dispatch the **reviewer** sub-agent first. It produces two Boolean checklists in
   `harness/reviewer.json`: a **Functional review** (per-FR implemented?, per-AC tested?) and a
   **Technical review** (single-purpose functions?, no hallucinated APIs?, errors handled?,
   conventions matched?, no security smell?, no secrets/PII?). Each item is `answer: true/false`
   + `evidence`. It does NOT score traceability (now mechanical) or emit floats.
2. Run the deterministic scorer (hand the user the exact command if sandbox Python fails):
   `python <plugin>/scripts/eval_harness.py --target "<target>" --src "<code-dir>" --json`
   It reads `reviewer.json`, STATE.md `stack:`, and (if present) `harness/eval.config.json`
   to select the test/complexity/security toolchain, runs those checks + the secrets scan,
   writes versioned `harness/results.json`, and prints the scorecard + regression.
   If the scorer reports **skipped** criteria (no tool configured for this stack), the review
   must call them out explicitly — a skipped tool-criterion scores 0, so either add the tool to
   `eval.config.json` or note in `06-REVIEW.md` why it is not applicable. Never present a
   skipped criterion as if it passed.
3. Fill `templates/REVIEW.md` into `harness/06-REVIEW.md`: the verdict (PASS if total ≥ 80 AND
   no hard gate tripped), the weighted table, hard-gate status, reviewer findings, and the
   regression delta.
4. Set `current_stage: review`. Set `gates.review: approved` **only if verdict is PASS** and
   the user accepts it via `/sdlc:gate`. On FAIL, list the recommended fixes and which stage to
   return to.

## Hard gates (force FAIL regardless of score)
- Security scan high-severity finding.
- Secrets / PII detected.

The review gate passing is what unblocks the commit hook. Do not mark it approved on a FAIL.
