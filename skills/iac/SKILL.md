---
name: iac
description: Generate the Infrastructure-as-Code + CI/CD pipeline per the TRD, delegating to the deploy-author sub-agent, and write harness/07-DEPLOY.md. Only for projects with a deploy target (STATE.md deploy:true). Runs after the review gate passes; its gate (gates.iac) is the deployment tollgate.
---

# /sdlc:iac — generate + gate the deployment

## Preconditions
- `deploy: true` in `harness/STATE.md` (this stage only exists for projects with a deploy target).
- `gates.review: approved` in `harness/STATE.md` — you review the code before you package it to ship.

## Steps
1. Read `harness/03-TRD.md` (Deployment & Infrastructure + Non-Functional Design) and
   `harness/01-PRD.md` (NFR-# targets). Confirm the deploy target and IaC/CI-CD tools.
2. Dispatch the **deploy-author** sub-agent. It generates the IaC + CI/CD files into the project
   (idempotent, pinned versions, secrets via vault, pipeline runs the harness gates before deploy,
   least-privilege) and writes `harness/07-DEPLOY.md`. It never provisions or deploys anything.
3. If the deploy-author flags a missing choice (cloud/provider/platform the TRD didn't name),
   **stop and surface it to the user** — never guess infrastructure.
4. If the project can lint its IaC (tflint / checkov / hadolint / actionlint), declare that command
   in `harness/eval.config.json` under the `iac` slot so the `iac` mechanical check scores it. Example:
   ```json
   { "iac": { "cmd": "checkov -d infra --compact", "kind": "exit-code", "hard_gate": false } }
   ```
5. Set `current_stage: iac`, `gates.iac: pending`. Summarize the files created and the promotion path.
6. Tell the user to review `07-DEPLOY.md` + the generated IaC, then run `/sdlc:gate` to approve.

## The deployment gate
Approving `gates.iac` (via `/sdlc:gate`) is what unblocks deployment. `hook_deploy_gate.py` blocks
`terraform apply` / `kubectl apply` / `docker push` / `helm upgrade` / `gh workflow run` / etc. until
**both** `gates.review: approved` AND `gates.iac: approved`. Never approve on an unreviewed or failing
build. The harness generates and gates the pipeline; it does not run the cloud deploy itself.

## Rules
- Files only — no real provisioning, no destructive commands, no new cloud accounts.
- No secrets/credentials in any generated file. Pin what ships. Keep the deploy role least-privilege.
