# SDLC Harness — Operating Guardrails

These rules apply to every skill and sub-agent in the `sdlc` plugin, and should be copied
into the target project's own `CLAUDE.md` at intake so they persist across the run.

## Grounding
- **Build only from the artifacts.** Every stage consumes the prior artifact(s). Never invent
  requirements, users, APIs, endpoints, libraries, or fields that are not in the PRD / stories
  / TRD / codebase map. If something is missing, flag the gap — do not paper over it.
- **Traceability is mandatory.** PRD `FR-#` → `US-#` → TRD component → code → test, and PRD
  `NFR-#` → TRD non-functional design. IDs must be carried through so any line of code (and every
  non-functional target) traces back to a requirement.

## Safety
- **No secrets, no PII, dummy data only.** Never hardcode credentials, tokens, or real personal
  data. Test fixtures use synthetic data.
- **No new third-party dependencies without asking.** If the design needs one, stop and get
  explicit user approval before adding it.
- **Never mutate unrelated code.** Especially brownfield: change only what the assigned story
  requires; imitate the existing conventions recorded in the codebase map.

## Process
- **Human tollgates.** Stages advance only through `/sdlc:gate` with explicit user approval.
  `start` and `gate` are user-invoked only (`disable-model-invocation: true`). Conditional stages
  (`design` for UI projects, `iac` for deploy projects) have gates too.
- **Don't ship un-reviewed code.** The commit hook blocks `git commit`/`git push` until the
  review gate has passed (STATE.md `gates.review: approved`).
- **Don't deploy un-reviewed infrastructure.** The deploy hook blocks `terraform apply` /
  `kubectl apply` / `docker push` / `helm upgrade` / … until BOTH `gates.review` and `gates.iac`
  are approved. The harness generates and gates the pipeline; it never runs a cloud deploy itself.
- **Don't fake a green build.** Never weaken or delete a test to make it pass, and never inflate
  review scores. A failing test means fix the code (or record the defect).

## Review honesty
- The weighted eval is reproducible and **normalized over the criteria that apply** (ux only for
  UI projects, iac only for deploy projects). Deterministic checks (tests, coverage, complexity,
  security, secrets, traceability) are computed by `eval_harness.py`; subjective ones (functional,
  technical, nfr, and the review halves of ux/iac) come from the reviewer agent in `reviewer.json`
  as Boolean checklists. Report the real number; never present a skipped criterion as passing.
- Hard gates (security high-severity, secrets/PII, and any `iac` hard-gate check) force FAIL
  regardless of the weighted total.
