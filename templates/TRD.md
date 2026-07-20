# 03 — Technical Requirements Document

> Stage artifact. Filled by `/sdlc:trd` from PRD + User Stories.
> Validate with `/sdlc:gate` before advancing.

## Architecture Overview
<!-- High-level design; how the pieces fit. A diagram (ascii/mermaid) is welcome. -->

## Tech Stack
<!-- Languages, frameworks, datastores, key libraries. For brownfield, match existing stack. -->

## Data Model
<!-- Entities, fields, relationships, schema. -->

## API / Interface Design
<!-- Endpoints or interfaces: method, path, request, response, status codes. -->

## Components & Responsibilities
<!-- Modules/files to add or change and what each owns. -->

## Story -> Implementation Map
<!-- Table: US-# | Components/files | Notes. Every story must map to at least one component. -->

## Testing Strategy
<!-- Unit/integration approach, test command, coverage expectations per acceptance criterion. -->

## Security & Guardrails
<!-- Auth, input validation, secrets handling, dependency policy. -->

## Non-Functional Design
<!--
For EACH NFR-# in the PRD, state the concrete architectural provision that meets it, and how it
is (or could be) verified. Table: NFR-# | Target | Design provision | Verification.
Reference every NFR-# by id so trace_check can confirm it is addressed here. Cover availability,
performance, reliability, scalability (security may live in Security & Guardrails above — link it).
-->

## Deployment & Infrastructure
<!--
Only required when the project has a deploy target (the `deploy` flag / iac stage). Name the
deploy target and IaC/CI-CD approach at a high level; the concrete files are generated in
/sdlc:iac -> harness/07-DEPLOY.md. Cover: environments, IaC tool, CI/CD platform, promotion path.
-->

## Rollout / Migration
<!-- For brownfield: how this integrates without breaking existing behavior. -->
