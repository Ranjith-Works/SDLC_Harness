# 07 — Deployment & Infrastructure

> Stage artifact. Filled by `/sdlc:iac` from the TRD's Deployment & Infrastructure section.
> Validate with `/sdlc:gate` before deploying. The generated IaC/CI-CD files live in the project
> (e.g. `infra/`, `Dockerfile`, `.github/workflows/`); this document is the human-readable map.

## Environments
<!-- The environments and their promotion path, e.g. dev -> staging -> prod. What differs per env. -->

## Infrastructure (IaC)
<!--
The IaC tool (Terraform / Docker / Kubernetes / Helm / CloudFormation / Pulumi / ...) and the
resources it provisions. List the generated files and what each owns. State how versions/images
are pinned and where secrets come from (vault/secret store — never literals).
-->

## CI/CD Pipeline
<!--
The CI/CD platform and pipeline stages. The pipeline MUST run the harness gates (tests + review)
before any deploy step. Describe: build -> test -> review gate -> deploy, and what each stage does.
-->

## Deployment Gates
<!--
The gates guarding a deploy. At minimum: STATE.md gates.review AND gates.iac must be 'approved'
(enforced by hook_deploy_gate.py, which blocks terraform apply / kubectl apply / docker push /
helm upgrade / etc. until then). List any additional env-promotion approvals.
-->

## Rollback
<!-- How to roll back a bad deploy (previous image/version, terraform state, blue-green, etc.). -->

## Observability
<!-- Health/readiness checks, key metrics, logs, alerts. How you'd detect the NFR targets slipping. -->

## NFR Coverage
<!-- For each NFR-# from the PRD that infra is responsible for (availability, scaling, RTO/RPO),
     state how this deployment meets it. Reference NFR-# ids so traceability holds. -->
