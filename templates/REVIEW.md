# 06 — Review & Scorecard

> Stage artifact. Produced by `/sdlc:review` (runs `scripts/eval_harness.py` + reviewer agent).

## Verdict
<!-- PASS / FAIL. Pass = weighted score >= 80 AND no hard gate tripped. -->

## Weighted Scorecard

| Criterion | Weight | Score | Weighted | Source |
|---|---|---|---|---|
| Tests pass rate | 25 | | | test command |
| Requirements coverage | 20 | | | reviewer agent |
| Code quality / complexity | 15 | | | static tool |
| Security scan | 15 | | | security tool (hard gate: high sev) |
| Traceability | 10 | | | validator + reviewer |
| Readability / conventions | 10 | | | reviewer agent |
| No secrets / PII | 5 | | | scan (hard gate) |
| **Total** | **100** | | | |

## Hard Gates
<!-- List each hard gate and PASS/FAIL: security-high-severity, secrets/PII. -->

## Findings
<!-- Reviewer notes: coverage gaps, hallucinated/invented APIs, policy issues, readability. -->

## Regression vs Previous Run
<!-- Delta against prior results.json, if any. -->

## Recommended Actions
<!-- What to fix before shipping. -->
