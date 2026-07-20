# 06 — Review & Scorecard

> Stage artifact. Produced by `/sdlc:review` (runs `scripts/eval_harness.py` + reviewer agent).

## Verdict
<!-- PASS / FAIL. Pass = normalized score >= 80 AND no hard gate tripped. -->

## Weighted Scorecard
<!--
The score is NORMALIZED over the criteria that APPLY to this project. Nine always-on criteria,
plus `ux` (only if ui:true) and `iac` (only if deploy:true). Non-applicable criteria are dropped
from both numerator and denominator (not penalized). Copy the actual rows/numbers from
`harness/results.json`. The Pts column is normalized so it sums to the Total.
-->

| Criterion | Raw Wt | Applies | Score % | Pts | Source |
|---|---|---|---|---|---|
| Tests pass rate | 20 | always | | | test command |
| Test coverage | 10 | always | | | coverage tool |
| Functional review (requirements) | 20 | always | | | reviewer agent |
| Traceability | 10 | always | | | trace_check.py |
| Code quality / complexity | 10 | always | | | static tool |
| Security scan | 15 | always | | | security tool (hard gate: high sev) |
| Technical review (readability) | 10 | always | | | reviewer agent |
| No secrets / PII | 5 | always | | | scan (hard gate) |
| Non-functional review (avail/perf/reliability) | 10 | always | | | reviewer agent |
| UI/UX review + visual/a11y | 15 | ui only | | | ux tool + reviewer agent |
| IaC + CI/CD readiness | 15 | deploy only | | | iac tool + reviewer agent |
| **Total (normalized)** | | | | **/100** | |

## Hard Gates
<!-- List each hard gate and PASS/FAIL: security-high-severity, secrets/PII, and any iac hard gate. -->

## Findings
<!-- Reviewer notes: coverage gaps, hallucinated/invented APIs, policy issues, readability. -->

## Regression vs Previous Run
<!-- Delta against prior results.json, if any. -->

## Recommended Actions
<!-- What to fix before shipping. -->
