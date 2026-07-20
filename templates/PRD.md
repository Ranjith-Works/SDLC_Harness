# 01 — Product Requirements Document

> Stage artifact. Filled by `/sdlc:prd`. Validate with `/sdlc:gate` before advancing.

## Overview
<!-- One paragraph: what this product/feature is and who it is for. -->

## Problem Statement
<!-- The concrete problem being solved and why it matters now. -->

## Goals
<!-- Bullet list of measurable goals. -->

## Non-Goals
<!-- Explicitly out of scope, to prevent scope creep. -->

## Users & Personas
<!-- Who uses this and their key needs. -->

## Functional Requirements
<!-- FR-1, FR-2, ... Each a single testable capability. -->

## Non-Functional Requirements
<!--
Number each NFR (NFR-1, NFR-2, ...) so it can be traced into the TRD and reviewed.
Give MEASURABLE targets — the harness's nfr review checks each one has an architectural
provision, and trace_check verifies each NFR-# is addressed in the TRD. Cover, where relevant:
  - Performance:   e.g. NFR-1: p99 API latency < 200ms at 100 rps
  - Availability:  e.g. NFR-2: 99.9% monthly uptime; graceful degradation on dependency loss
  - Reliability:   e.g. NFR-3: RTO 5min / RPO 1min; retries + timeouts on all external calls
  - Scalability:   e.g. NFR-4: horizontal scaling to 1k concurrent users, stateless services
  - Security:      e.g. NFR-5: all input validated; secrets via vault; TLS in transit
Omit a category only if it genuinely does not apply, and say so.
-->

## Success Metrics
<!-- How we know it worked (quantifiable where possible). -->

## Constraints & Assumptions
<!-- Known limits, dependencies, assumptions. -->

## Out of Scope / Risks
<!-- Risks and mitigations. -->
