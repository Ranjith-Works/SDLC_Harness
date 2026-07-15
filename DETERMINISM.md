# Determinism in the SDLC Harness

The end goal is **deterministic, reproducible output** — the same project should score the same
way every time, and every point should be explainable. This doc states exactly which steps are
**mechanical** (non-LLM, always identical) and which are **LLM-supported**, and how the
LLM-supported parts are made granular so each reduces to a **Boolean** answer.

## Two levers we use
1. **Mechanical-first** — do as much as possible with deterministic scripts, and move things
   *out* of the LLM column whenever they're really pattern-matching (e.g. traceability).
2. **LLM → Boolean** — for the judgment that genuinely needs a model, the reviewer answers a
   fixed list of **yes/no questions with evidence**, and the score is computed mechanically as
   `yes ÷ total`. The model never emits a vague float; it only answers atomic, auditable checks.

## Which steps are LLM vs mechanical

| Pipeline step | Type | Notes |
|---|---|---|
| Intake interview / codebase analysis | **LLM** | inherently generative |
| PRD, User Stories, TRD | **LLM** | inherently generative |
| Implement code / author tests | **LLM** | inherently generative |
| Run tests → pass rate | **Mechanical** | project's own test runner |
| **Test coverage %** | **Mechanical** | coverage tool (pytest-cov / configurable) |
| Requirements coverage (Functional review) | **LLM → Boolean checklist** | per-FR implemented?, per-AC tested? |
| Traceability | **Mechanical** | `trace_check.py` — FR→US→TRD ID linkage |
| Code complexity | **Mechanical** | radon / configurable |
| Security scan | **Mechanical** | bandit / npm audit / configurable (hard gate) |
| Readability (Technical review) | **LLM → Boolean checklist** | single-purpose?, no hallucinated APIs?, etc. |
| Secrets / PII | **Mechanical** | pattern scan (hard gate) |
| Gates / commit-block / audit (hooks) | **Mechanical** | deterministic enforcement |

## The scorecard (100 pts): ~70 mechanical / ~30 Boolean-derived

| Criterion | Weight | Source | Deterministic? |
|---|---:|---|---|
| Tests pass rate | 20 | test runner | ✅ mechanical |
| Test coverage | 10 | coverage tool | ✅ mechanical |
| Functional review (requirements) | 20 | reviewer **Boolean checklist** → yes/total | ✅ reproducible |
| Traceability | 10 | `trace_check.py` | ✅ mechanical |
| Code quality / complexity | 10 | static tool | ✅ mechanical |
| Security scan | 15 | scanner (**hard gate**) | ✅ mechanical |
| Technical review (readability) | 10 | reviewer **Boolean checklist** → yes/total | ✅ reproducible |
| No secrets / PII | 5 | scan (**hard gate**) | ✅ mechanical |

**70 points are pure mechanical. The remaining 30 are computed from Boolean checklists**, so even
the "LLM" part is a deterministic count of yes/no answers, each with cited evidence.

## Review = Functional + Technical (catch defects before system testing)
The review stage explicitly does both angles, so real defects are caught here and only trivial
ones leak downstream:
- **Functional review** (does it meet the spec): for each requirement `FR-#` → "implemented?",
  for each acceptance criterion `AC-#.#` → "has a real test?", plus "every FR implemented AND
  tested?". All Boolean, all evidenced.
- **Technical review** (is the code sound): single-purpose functions? no hallucinated/invented
  APIs? errors & edge cases handled? conventions matched? no security smell? no secrets/PII?

## "How much can automated tests cover before review?"
The **Test coverage** criterion reports the exact line-coverage % from the project's coverage
tool (pytest-cov for Python; configurable per stack). Because the test-author writes a test for
every acceptance criterion, coverage is *requirement-driven*. What automated tests can't
verify — design quality, missing requirements, hallucinated APIs, security posture — is exactly
what the Functional + Technical review is for.

## Why this is reproducible
- Mechanical criteria are pure functions of the code + artifacts.
- The reviewer's contribution is a set of atomic Booleans + evidence; re-running it yields the
  same aggregate far more reliably than a holistic "0.9". Any disagreement is pinpointed to a
  single check you can audit.
- Results are versioned in `harness/results.json`, so any run can be compared to the last for
  regression.
