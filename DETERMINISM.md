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
| PRD, User Stories, UX-spec, TRD | **LLM** | inherently generative |
| Implement code / author tests / generate IaC | **LLM** | inherently generative |
| Run tests → pass rate | **Mechanical** | project's own test runner |
| **Test coverage %** | **Mechanical** | coverage tool (pytest-cov / lcov / cobertura / configurable) |
| Requirements coverage (Functional review) | **LLM → Boolean checklist** | per-FR implemented?, per-AC tested? |
| Traceability | **Mechanical** | `trace_check.py` — FR→US→TRD, NFR→TRD ID linkage |
| Code complexity | **Mechanical** | radon / eslint / configurable |
| Security scan | **Mechanical** | bandit / npm audit / configurable (hard gate) |
| Readability (Technical review) | **LLM → Boolean checklist** | single-purpose?, no hallucinated APIs?, etc. |
| Non-functional review (NFR) | **LLM → Boolean checklist** | per-NFR provisioned?, timeouts/retries?, graceful degradation? |
| UI/UX review (ui only) | **Mechanical (visual/a11y tool) + LLM → Boolean checklist** | states/a11y/responsive vs the UX spec |
| IaC / CI-CD readiness (deploy only) | **Mechanical (IaC lint) + LLM → Boolean checklist** | idempotent?, pinned?, secrets vaulted?, rollback?, gates-before-deploy? |
| Secrets / PII | **Mechanical** | language-agnostic pattern scan (hard gate) |
| Gates / commit-block / deploy-block / audit (hooks) | **Mechanical** | deterministic enforcement |

## The scorecard: normalized over applicable criteria

Nine criteria are **always** scored; two are **conditional** — `ux` (only if the project has a
UI) and `iac` (only if it has a deploy target). The total is **normalized over the applicable
weights**, so a non-applicable criterion is dropped from both numerator and denominator (never a
penalty):

```
total = round( Σ(frac × weight for applicable criteria) ÷ Σ(weight for applicable criteria) × 100, 1 )
```

Applicability itself is **deterministic**: an explicit `ui:` / `deploy:` flag (STATE.md or
`eval.config.json`) wins; otherwise it is auto-detected from the source tree (front-end files /
IaC files). Same inputs → same applicable set → same denominator → same score.

| Criterion | Raw wt | Applies | Source | Deterministic? |
|---|---:|---|---|---|
| Tests pass rate | 20 | always | test runner | ✅ mechanical |
| Test coverage | 10 | always | coverage tool | ✅ mechanical |
| Functional review (requirements) | 20 | always | reviewer **Boolean checklist** → yes/total | ✅ reproducible |
| Traceability | 10 | always | `trace_check.py` | ✅ mechanical |
| Code quality / complexity | 10 | always | static tool | ✅ mechanical |
| Security scan | 15 | always | scanner (**hard gate**) | ✅ mechanical |
| Technical review (readability) | 10 | always | reviewer **Boolean checklist** → yes/total | ✅ reproducible |
| No secrets / PII | 5 | always | scan (**hard gate**) | ✅ mechanical |
| Non-functional review (avail/perf/reliability) | 10 | always | reviewer **Boolean checklist** → yes/total | ✅ reproducible |
| UI/UX review + visual/a11y | 15 | **ui only** | ux tool + reviewer checklist (averaged) | ✅ mechanical + reproducible |
| IaC + CI/CD readiness | 15 | **deploy only** | iac tool + reviewer checklist (averaged) | ✅ mechanical + reproducible |

**The bulk of every score is mechanical; the review dimensions are deterministic counts of
yes/no answers**, each with cited evidence. The conditional `ux`/`iac` criteria average a
mechanical tool half (exit-code / a11y percentage) with the reviewer's Boolean half.

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

## Non-functional & UI/UX: still deterministic
- **NFR review** is generated mechanically from the PRD: one Boolean per `NFR-#` ("has a concrete
  architectural provision?") plus a fixed reliability rubric (timeouts/retries, graceful
  degradation, health check, idempotency). `trace_check.py` separately verifies each `NFR-#` is
  addressed in the TRD — a mechanical linkage check.
- **UI/UX** combines a mechanical visual/a11y tool (Playwright/axe/Lighthouse via the `ux` slot,
  scored by exit code or an a11y percentage) with a Boolean checklist scored against the UX spec,
  citing captured screenshots as evidence — so "the UI is right" reduces to auditable checks, not
  a vibe.

## Why this is reproducible
- Mechanical criteria are pure functions of the code + artifacts.
- Applicability (which criteria count) is a deterministic function of declared flags + the source
  tree — so the denominator is stable across runs.
- The reviewer's contribution is a set of atomic Booleans + evidence; re-running it yields the
  same aggregate far more reliably than a holistic "0.9". Any disagreement is pinpointed to a
  single check you can audit.
- Results are versioned in `harness/results.json`, so any run can be compared to the last for
  regression.
