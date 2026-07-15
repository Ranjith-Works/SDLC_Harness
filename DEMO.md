# SDLC Harness — VP Walkthrough

This ties the `sdlc` plugin to two worked, end-to-end runs. The point: a **reusable harness**
that drives *any* project through PRD → Stories → TRD → Code → Tests → weighted-eval Review,
with file artifacts and human tollgates — proven on both a greenfield build and a brownfield
feature.

## 1. What was built

**A Claude Code plugin** at `Downloads\sdlc-harness` — one versioned, namespaced unit that
drops into any repo via `claude --plugin-dir`:

- **10 skills** (`/sdlc:start … /sdlc:review … /sdlc:gate … /sdlc:status`) — the pipeline.
- **4 sub-agents** — `codebase-analyzer` (brownfield, read-only), `implementer`,
  `test-author`, `reviewer`.
- **3 governance hooks** — commit blocked until review passes; artifact structural validation;
  audit log of stage/subagent transitions.
- **A runnable weighted eval** (`scripts/eval_harness.py`) — 100 points, hard gates, versioned
  `results.json`, regression compare. The showpiece.
- **Guardrails** (`CLAUDE.md`) — build only from artifacts, no invented APIs, no secrets/PII,
  no new deps without asking, human approval at every gate.

Greenfield and brownfield differ **only at intake** (interview vs. read-only analysis), then
converge on the same spine.

> **"Why Python? Does it only work for Python/JS?"** Python is the harness's *runner* only — it
> never inspects your code; every code check shells out to the project's own tools. The pipeline
> is language-agnostic, and so is the scorecard: `python`/`js` toolchains are built in, and any
> other stack (Go, Rust, Java…) plugs its own test/lint/security commands into a one-file
> `harness/eval.config.json`. Criteria with no tool are reported *skipped*, never faked.

## 2. Verified before the demos (standalone)

| Check | Result |
|---|---|
| `validate_artifact.py` on an empty template | correctly flagged incomplete (`valid: false`) |
| `eval_harness.py` on a fixture | scorecard rendered, **PASS 95.5/100**, hard gates evaluated |
| Commit-gate hook (review pending) | **blocked** (exit 2) with reason |
| Commit-gate hook (review approved) | **allowed** (exit 0) |
| Artifact-validation hook (stub PRD) | non-blocking warning listing missing sections |
| Audit hook | appended `SubagentStop` event to `AUDIT.log` |

## 3. Greenfield run — URL Shortener API

`Downloads\url-shortener`. Stack chosen via the intake interview: **Python · FastAPI · SQLite ·
pytest + TestClient**.

- Full artifact chain in `url-shortener\harness\`: `00-INTAKE → 01-PRD (7 FRs) →
  02-USER-STORIES (US-1..5, every FR covered) → 03-TRD (3-layer design + story→impl map) →
  05-TEST-REPORT → 06-REVIEW`.
- Code: `app/storage.py` (parameterized SQLite), `app/service.py` (CSPRNG base62 + uniqueness
  retry), `app/main.py` (FastAPI). Endpoints: `POST /shorten`, `GET /{code}` (307 + click++),
  `GET /api/stats/{code}`, `GET /health`.
- **Tests: 13/13 pass.** Persistence is exercised via a real two-client restart, not mocked.
- **Review: PASS — 98.6/100.** bandit clean (0 high/med/low), no secrets, all FRs traceable.

## 4. Brownfield run — Ticket Intelligence + `GET /metrics`

`Downloads\ticket-intelligence-brownfield-demo` — a **copy** (the original is never touched;
`.env` and secrets excluded from the copy).

- `codebase-analyzer` produced `00-CODEBASE-MAP.md`: detected FastAPI + scikit-learn + RAG/LLM
  stack, the `config.PATHS` convention, lazy-import pattern, and the exact integration point.
- Feature: a read-only **`GET /metrics`** endpoint exposing the trained model's evaluation
  metrics, added **beside** `/health` — imitating existing conventions (pydantic
  `response_model`, `config.PATHS.METRICS`, thin handler). Returns 503 when untrained.
- **Non-breaking:** regression tests assert `/health` and every pre-existing route
  (`/predict`, `/analyze`, `/evaluate`) are unchanged; `GET /metrics` never loads the model/LLM.
- **Tests: 6/6 pass.** **Review: PASS — 98.3/100** (scans scoped to the changed surface `api/`).
- The one new dependency (pytest, dev-only — the repo had no tests) was **disclosed and
  flagged**, per the "no new deps without asking" guardrail.

## 5. How to reproduce (fresh session = the real reusability check)

```text
# install the published plugin in any Claude Code workspace:
/plugin marketplace add Ranjith-Works/SDLC_Harness
/plugin install sdlc@sdlc-harness
# (local-dev fallback: git clone the repo, then `claude --plugin-dir ./SDLC_Harness`)

#  /sdlc:start  ->  intake  ->  /sdlc:prd  ->  gate  ->  stories  ->  gate  -> ...
#  ... -> /sdlc:trd -> gate -> /sdlc:implement -> gate -> /sdlc:test -> gate -> /sdlc:review

# re-run either eval directly:
python sdlc-harness\scripts\eval_harness.py --target url-shortener --src app
python sdlc-harness\scripts\eval_harness.py --target ticket-intelligence-brownfield-demo --src api
```

## 6. Scorecard at a glance

| Run | Tests | Security (hard gate) | Secrets (hard gate) | Weighted total | Verdict |
|---|---|---|---|---|---|
| Fixture (self-test) | 3/3 | clean | clean | 95.5 | PASS |
| Greenfield — URL shortener | 13/13 | 0 high | clean | **98.6** | PASS |
| Brownfield — /metrics | 6/6 | 0 high | clean | **98.3** | PASS |

Every stage produced a reviewable file, every transition required human approval, and the
final gate is enforced in code — un-reviewed work cannot be committed.
