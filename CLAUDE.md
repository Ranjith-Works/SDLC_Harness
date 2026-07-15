# SDLC Harness — Operating Guardrails

These rules apply to every skill and sub-agent in the `sdlc` plugin, and should be copied
into the target project's own `CLAUDE.md` at intake so they persist across the run.

## Grounding
- **Build only from the artifacts.** Every stage consumes the prior artifact(s). Never invent
  requirements, users, APIs, endpoints, libraries, or fields that are not in the PRD / stories
  / TRD / codebase map. If something is missing, flag the gap — do not paper over it.
- **Traceability is mandatory.** PRD `FR-#` → `US-#` → TRD component → code → test. IDs must be
  carried through so any line of code traces back to a requirement.

## Safety
- **No secrets, no PII, dummy data only.** Never hardcode credentials, tokens, or real personal
  data. Test fixtures use synthetic data.
- **No new third-party dependencies without asking.** If the design needs one, stop and get
  explicit user approval before adding it.
- **Never mutate unrelated code.** Especially brownfield: change only what the assigned story
  requires; imitate the existing conventions recorded in the codebase map.

## Process
- **Human tollgates.** Stages advance only through `/sdlc:gate` with explicit user approval.
  `start` and `gate` are user-invoked only (`disable-model-invocation: true`).
- **Don't ship un-reviewed code.** The commit hook blocks `git commit`/`git push` until the
  review gate has passed (STATE.md `gates.review: approved`).
- **Don't fake a green build.** Never weaken or delete a test to make it pass, and never inflate
  review scores. A failing test means fix the code (or record the defect).

## Review honesty
- The weighted eval is reproducible: deterministic checks (tests, complexity, security,
  secrets) are computed by `eval_harness.py`; subjective ones (coverage, traceability,
  readability) come from the reviewer agent in `reviewer.json`. Report the real number.
- Hard gates (security high-severity, secrets/PII) force FAIL regardless of the weighted total.
