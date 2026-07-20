#!/usr/bin/env python3
"""Weighted SDLC eval harness — the scorecard behind `/sdlc:review`.

Scores a target project out of 100 across weighted criteria, applies HARD GATES
(any tripped => FAIL regardless of score), writes versioned results to
`harness/results.json`, and compares against the previous run for regression.

The score is NORMALIZED over the criteria that apply to the project: nine
always-on dimensions plus two conditional ones — `ux` (only if the project has a
UI) and `iac` (only if it has a deploy target). A criterion that doesn't apply is
dropped from both numerator and denominator, so a backend library is never
penalized for missing a UI or a pipeline. Applicability is deterministic: an
explicit `ui:` / `deploy:` flag (STATE.md or eval.config.json) wins, else
auto-detection from the source tree.

Deterministic criteria (tests, coverage, complexity, security, secrets,
traceability) are computed by this script. LLM-judged criteria (functional,
readability, nfr, and the review halves of ux/iac) are read from
`harness/reviewer.json` as Boolean yes/total checklists. This split keeps the
score reproducible.

Toolchain is pluggable per stack (read from harness/STATE.md `stack:` key, or
--stack): built-ins for python / js / go / java / rust / ruby; ANY other stack
(and the ux/iac tool slots) plugs in via harness/eval.config.json.

Usage:
    python eval_harness.py --target <dir> [--src <code-dir>] [--stack <name>]
                           [--test-cmd "..."] [--ui auto|on|off]
                           [--deploy auto|on|off] [--json]

Exit codes: 0 = PASS, 1 = FAIL, 2 = usage/setup error.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone

import trace_check  # local module (same scripts/ dir) — mechanical traceability

# criterion key -> (label, weight, applies). Mechanical criteria are deterministic; LLM-judged
# criteria (functional, readability, nfr, and the LLM half of ux/iac) come from reviewer.json as
# Boolean checklists aggregated to yes/total.
#
# `applies` gates whether the criterion enters the scorecard for THIS project:
#   "always" — every project.
#   "ui"     — only if the project has a UI (detected or declared via `ui:` flag).
#   "deploy" — only if the project has a deploy target (detected or declared via `deploy:` flag).
# The final score is NORMALIZED over the applicable weights (see `evaluate`), so a backend library
# with no UI/deploy is scored only on the dimensions that apply to it — never penalized for
# missing a UI or a pipeline it was never meant to have.
WEIGHTS = [
    ("tests", "Tests pass rate", 20, "always"),
    ("testcov", "Test coverage", 10, "always"),
    ("functional", "Functional review (requirements)", 20, "always"),
    ("traceability", "Traceability (mechanical)", 10, "always"),
    ("quality", "Code quality / complexity", 10, "always"),
    ("security", "Security scan", 15, "always"),
    ("readability", "Technical review (readability)", 10, "always"),
    ("secrets", "No secrets / PII", 5, "always"),
    ("nfr", "Non-functional review (avail/perf/reliability)", 10, "always"),
    ("ux", "UI/UX review + visual/a11y", 15, "ui"),
    ("iac", "IaC + CI/CD readiness", 15, "deploy"),
]
PASS_THRESHOLD = 80

# Built-in, normalized toolchains. A project can override/extend these with a
# harness/eval.config.json (same shape) so ANY stack plugs in without editing this file.
# Recognized coverage `kind`s: coverage-py, coverage-generic (percent_regex on stdout, or an
# lcov/cobertura/coverage-json report). Recognized complexity/security `kind`s: radon, eslint,
# bandit, npm-audit, and the generic "exit-code" (score from the tool's return code). The `ux`
# and `iac` slots are conditional criteria (see WEIGHTS) and default to exit-code scoring; they
# are usually declared per project in eval.config.json since their tools are project-specific.
# Any unknown kind falls back to exit-code.
BUILTIN_TOOLCHAINS = {
    "python": {
        "test": {"cmd": "pytest -q", "pass_regex": r"(\d+)\s+passed", "fail_regex": r"(\d+)\s+failed"},
        "coverage": {"kind": "coverage-py",
                     "cmd": "pytest --cov={src} --cov-report=json:harness/coverage.json -q",
                     "report": "harness/coverage.json"},
        "complexity": {"kind": "radon"},
        "security": {"kind": "bandit", "hard_gate": True},
    },
    "js": {
        "test": {"cmd": "npm test --silent", "pass_regex": r"(\d+)\s+passed", "fail_regex": r"(\d+)\s+failed"},
        "complexity": {"kind": "eslint"},
        "security": {"kind": "npm-audit", "hard_gate": True},
    },
    "go": {
        "test": {"cmd": "go test ./...", "pass_regex": r"^ok\b", "fail_regex": r"^FAIL\b"},
        "coverage": {"kind": "coverage-generic", "cmd": "go test ./... -cover",
                     "percent_regex": r"coverage:\s*([\d.]+)%"},
        "complexity": {"kind": "exit-code", "cmd": "gocyclo -over 15 ."},
        "security": {"kind": "exit-code", "cmd": "gosec ./...", "hard_gate": True},
    },
    "java": {
        "test": {"cmd": "mvn -q test", "pass_regex": r"Tests run: (\d+)", "fail_regex": r"Failures: (\d+)"},
        "complexity": {"kind": "exit-code", "cmd": "mvn -q checkstyle:check"},
        "security": {"kind": "exit-code", "cmd": "mvn -q com.github.spotbugs:spotbugs-maven-plugin:check",
                     "hard_gate": True},
    },
    "rust": {
        "test": {"cmd": "cargo test", "pass_regex": r"(\d+)\s+passed", "fail_regex": r"(\d+)\s+failed"},
        "complexity": {"kind": "exit-code", "cmd": "cargo clippy -- -D warnings"},
        "security": {"kind": "exit-code", "cmd": "cargo audit", "hard_gate": True},
    },
    "ruby": {
        "test": {"cmd": "bundle exec rspec"},  # rc fallback: rspec exits non-zero on any failure
        "complexity": {"kind": "exit-code", "cmd": "rubocop"},
        "security": {"kind": "exit-code", "cmd": "brakeman -q -z", "hard_gate": True},
    },
}
_TOOL_KEYS = ("test", "coverage", "complexity", "security", "ux", "iac")

SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
    (r"(?i)(api[_-]?key|secret|token|passwd|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]", "hardcoded credential"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "Slack token"),
    (r"gh[pousr]_[0-9A-Za-z]{30,}", "GitHub token"),
]
# files/dirs we never scan for secrets or complexity
SKIP_DIRS = {"harness", "node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build",
             ".pytest_cache", "target", "vendor", ".gradle", ".terraform", ".next", "coverage"}
# binary / non-source extensions the secrets scan skips (everything else is treated as text, so
# secret scanning is language-agnostic — Go/Rust/Java/Ruby/etc. source is covered, not just .py/.js)
BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf", ".zip", ".gz",
               ".tar", ".tgz", ".jar", ".war", ".class", ".exe", ".dll", ".so", ".dylib", ".bin",
               ".o", ".a", ".pyc", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".mov",
               ".wav", ".lock", ".map", ".min.js", ".min.css"}


def run(cmd, cwd):
    """Run a shell command, capture output. Returns (rc, stdout+stderr).

    On Windows, split with posix=False so backslashes in paths (e.g. an absolute {src} passed to
    a coverage command) are preserved rather than treated as shell escapes."""
    try:
        args = cmd if isinstance(cmd, list) else shlex.split(cmd, posix=(os.name != "nt"))
        proc = subprocess.run(
            args,
            cwd=cwd, capture_output=True, text=True, timeout=600,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return 127, "command not found"
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def tool_exists(name):
    from shutil import which
    return which(name) is not None


def _render(cmd, src):
    """Substitute the {src} placeholder in a configured command."""
    return cmd.replace("{src}", src) if isinstance(cmd, str) else cmd


def iter_source_files(src, exts):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if any(fn.endswith(e) for e in exts):
                yield os.path.join(root, fn)


def iter_text_files(src, max_bytes=1_000_000):
    """Yield every likely-text source file under src (skipping SKIP_DIRS, binary extensions, and
    oversized files). Language-agnostic — used by the secrets scan so it covers any stack."""
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            low = fn.lower()
            if any(low.endswith(e) for e in BINARY_EXTS):
                continue
            path = os.path.join(root, fn)
            try:
                if os.path.getsize(path) > max_bytes:
                    continue
            except OSError:
                continue
            yield path


# ---------------- state ----------------

def read_state(target):
    path = os.path.join(target, "harness", "STATE.md")
    state = {}
    if not os.path.isfile(path):
        return state
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    m = re.search(r"```yaml\n(.*?)```", text, re.S)
    block = m.group(1) if m else text
    for line in block.splitlines():
        mm = re.match(r"^\s{0,2}(mode|stack|target|current_stage|ui|deploy|deploy_target):\s*(\S+)", line)
        if mm:
            state[mm.group(1)] = mm.group(2)
    return state


def _as_bool(v):
    """Interpret a declared flag (STATE.md / eval.config.json) as a tri-state bool. None = unset."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "yes", "1", "on")


def detect_ui(src):
    """Deterministic UI detection: any front-end source file, or a JS manifest with a UI framework."""
    ui_exts = (".jsx", ".tsx", ".vue", ".svelte", ".html", ".htm", ".css", ".scss")
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.lower().endswith(ui_exts):
                return True
            if fn == "package.json":
                try:
                    with open(os.path.join(root, fn), encoding="utf-8-sig") as f:
                        deps = json.load(f)
                    blob = json.dumps({**deps.get("dependencies", {}), **deps.get("devDependencies", {})})
                    if re.search(r"react|vue|svelte|angular|next|solid-js|preact", blob):
                        return True
                except Exception:
                    pass
    return False


def detect_iac(target):
    """Deterministic IaC/deploy detection: IaC files, CI workflows, or container/orchestration manifests."""
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(root, target).replace(os.sep, "/")
        if rel.startswith(".github/workflows") or "/helm" in ("/" + rel) or rel.endswith("helm"):
            if files:
                return True
        for fn in files:
            low = fn.lower()
            if low == "dockerfile" or low.endswith(".tf") or low.endswith(".tfvars"):
                return True
            if low.startswith("docker-compose") and low.endswith((".yml", ".yaml")):
                return True
            if rel.startswith(".github/workflows") and low.endswith((".yml", ".yaml")):
                return True
    return False


def resolve_applicability(target, src, state, cfg, ui_override="auto", deploy_override="auto"):
    """Decide which conditional criteria apply. Precedence: CLI override -> declared flag
    (eval.config.json, then STATE.md) -> deterministic auto-detect. Returns {"ui": bool, "deploy": bool}."""
    cfg = cfg or {}

    def resolve(name, override, detector):
        if override in ("on", "off"):
            return override == "on"
        declared = _as_bool(cfg.get(name))
        if declared is None:
            declared = _as_bool(state.get(name))
        if declared is not None:
            return declared
        return detector()

    ui = resolve("ui", ui_override, lambda: detect_ui(src))
    deploy = resolve(
        "deploy", deploy_override,
        lambda: bool(cfg.get("deploy_target") or state.get("deploy_target")) or detect_iac(target),
    )
    return {"ui": ui, "deploy": deploy}


def load_config(target, config_path):
    """Load harness/eval.config.json (or --config path) if present, else None."""
    path = config_path or os.path.join(target, "harness", "eval.config.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def resolve_toolchain(target, stack, config_path, test_cmd):
    """Resolve the eval toolchain. Order: eval.config.json -> built-in[stack] -> empty (skip).

    Returns (resolved_stack, toolchain_dict) where toolchain_dict has normalized
    'test' / 'complexity' / 'security' specs. Missing specs => that criterion is skipped.
    """
    cfg = load_config(target, config_path)
    if cfg:
        stack = cfg.get("stack", stack)
        builtin = BUILTIN_TOOLCHAINS.get(stack, {})
        tc = {k: {**builtin.get(k, {}), **(cfg.get(k) or {})} for k in _TOOL_KEYS}
    else:
        builtin = BUILTIN_TOOLCHAINS.get(stack, {})
        tc = {k: dict(builtin.get(k, {})) for k in _TOOL_KEYS}
    if test_cmd:
        tc["test"]["cmd"] = test_cmd
    return stack, tc


# ---------------- criteria scorers ----------------
# each returns dict: {frac: 0..1, detail: str, hard_gate_failed: bool}

def score_tests(target, spec):
    cmd = spec.get("cmd")
    if not cmd:
        return {"frac": 0.0, "detail": "no test command configured", "skipped": True}
    tool = cmd.split()[0]
    if not tool_exists(tool):
        return {"frac": 0.0, "detail": f"test runner '{tool}' not found", "skipped": True}
    rc, out = run(cmd, target)
    pass_re = spec.get("pass_regex", r"(\d+)\s+passed")
    fail_re = spec.get("fail_regex", r"(\d+)\s+failed")
    passed = failed = 0
    m = re.search(pass_re, out)
    if m and m.groups():
        passed = int(m.group(1))
    m = re.search(fail_re, out)
    if m and m.groups():
        failed = int(m.group(1))
    total = passed + failed
    if total == 0:
        # regex captured no counts (e.g. `go test` prints ok/FAIL) -> fall back to exit code
        frac = 1.0 if rc == 0 else 0.0
        detail = f"no test count parsed; runner rc={rc}"
    else:
        frac = passed / total
        detail = f"{passed}/{total} passed"
    return {"frac": frac, "detail": detail}


def _parse_lcov(text):
    """LCOV: sum LF (lines found) and LH (lines hit) across records -> covered fraction."""
    found = sum(int(m) for m in re.findall(r"^LF:(\d+)", text, re.M))
    hit = sum(int(m) for m in re.findall(r"^LH:(\d+)", text, re.M))
    return (hit / found) if found else None


def _parse_cobertura(text):
    """Cobertura XML: read the top-level line-rate attribute (0..1)."""
    m = re.search(r'line-rate="([\d.]+)"', text)
    return float(m.group(1)) if m else None


def score_coverage(target, src, spec):
    kind = spec.get("kind")
    cmd = spec.get("cmd")
    if kind == "coverage-py":
        if not tool_exists("pytest"):
            return {"frac": 0.0, "detail": "pytest not installed", "skipped": True}
        run(_render(cmd, src), target)  # runs the suite under coverage; writes the json report
        report = os.path.join(target, spec.get("report", "harness/coverage.json"))
        try:
            with open(report, encoding="utf-8-sig") as f:
                data = json.load(f)
            pct = data.get("totals", {}).get("percent_covered")
            if pct is None:
                raise ValueError("no percent_covered")
            return {"frac": max(0.0, min(1.0, pct / 100.0)), "detail": f"{pct:.0f}% lines covered"}
        except Exception:
            return {"frac": 0.0, "detail": "coverage report unparsable (install pytest-cov?)", "skipped": True}
    if kind == "coverage-generic":
        # Stack-agnostic coverage: either scrape a percent from stdout, or parse an lcov/cobertura report.
        if cmd:
            tool = _render(cmd, src).split()[0]
            if not tool_exists(tool):
                return {"frac": 0.0, "detail": f"'{tool}' not found", "skipped": True}
            _, out = run(_render(cmd, src), target)
        else:
            out = ""
        prx = spec.get("percent_regex")
        if prx:
            vals = [float(m) for m in re.findall(prx, out)]
            if vals:
                pct = sum(vals) / len(vals)  # mean across packages/modules
                return {"frac": max(0.0, min(1.0, pct / 100.0)), "detail": f"{pct:.0f}% covered (mean)"}
        report = spec.get("report")
        if report:
            try:
                with open(os.path.join(target, report), encoding="utf-8-sig") as f:
                    text = f.read()
                rk = spec.get("report_kind", "lcov")
                frac = _parse_cobertura(text) if rk == "cobertura" else _parse_lcov(text)
                if frac is not None:
                    return {"frac": max(0.0, min(1.0, frac)), "detail": f"{frac*100:.0f}% covered ({rk})"}
            except Exception:
                pass
        return {"frac": 0.0, "detail": "coverage report unparsable", "skipped": True}
    if cmd:
        return {"frac": 0.0, "detail": "coverage tool kind not recognized", "skipped": True}
    return {"frac": 0.0, "detail": "no coverage tool configured", "skipped": True}


def score_traceability(target):
    r = trace_check.check(target)
    if r.get("skipped"):
        return {"frac": 0.0, "detail": "no PRD/stories to trace", "skipped": True}
    return {"frac": r["frac"], "detail": r["detail"]}


def _score_exit_code(target, cmd, hard_gate=False):
    """Generic fallback: score a tool purely by its exit code (0 = pass)."""
    tool = cmd.split()[0]
    if not tool_exists(tool):
        return {"frac": 0.0, "detail": f"'{tool}' not found", "skipped": True}
    rc, _ = run(cmd, target)
    clean = rc == 0
    return {"frac": 1.0 if clean else 0.0,
            "detail": f"exit-code mode: rc={rc}",
            "hard_gate_failed": bool(hard_gate) and not clean}


def score_tool(target, src, spec):
    """Mechanical scorer for a configured tool slot (used by the ux/iac mechanical halves).
    Supports the `exit-code` kind (default) and `percent` (scrape a 0-100 number via percent_regex).
    Returns skipped when no cmd is configured so the caller can fall back to the LLM half."""
    cmd = spec.get("cmd")
    if not cmd:
        return {"frac": 0.0, "detail": "no tool configured", "skipped": True}
    cmd = _render(cmd, src)
    kind = spec.get("kind", "exit-code")
    if kind == "percent":
        tool = cmd.split()[0]
        if not tool_exists(tool):
            return {"frac": 0.0, "detail": f"'{tool}' not found", "skipped": True}
        _, out = run(cmd, target)
        vals = [float(m) for m in re.findall(spec.get("percent_regex", r"([\d.]+)%"), out)]
        if not vals:
            return {"frac": 0.0, "detail": "no percent parsed", "skipped": True}
        pct = sum(vals) / len(vals)
        return {"frac": max(0.0, min(1.0, pct / 100.0)), "detail": f"{pct:.0f}% (mean)"}
    return _score_exit_code(target, cmd, hard_gate=spec.get("hard_gate", False))


def _combine(parts):
    """Combine a mechanical sub-score and an LLM checklist sub-score into one criterion result.
    Averages the fracs of whichever parts are present (not skipped); propagates any hard gate.
    Skipped only if BOTH parts are absent."""
    live = [p for p in parts if p and not p.get("skipped")]
    if not live:
        return {"frac": 0.0,
                "detail": "; ".join(p.get("detail", "") for p in parts if p) or "no signal",
                "skipped": True}
    frac = sum(p["frac"] for p in live) / len(live)
    return {"frac": frac,
            "detail": " | ".join(p["detail"] for p in live),
            "hard_gate_failed": any(p.get("hard_gate_failed") for p in live)}


def score_quality(target, src, spec):
    kind = spec.get("kind")
    if kind == "radon":
        if not tool_exists("radon"):
            return {"frac": 0.0, "detail": "radon not installed", "skipped": True}
        rc, out = run(spec.get("cmd") or ["radon", "cc", "-s", "-j", src], target)
        try:
            data = json.loads(out)
        except Exception:
            return {"frac": 0.0, "detail": "radon output unparsable", "skipped": True}
        cx = [item["complexity"] for fns in data.values() for item in fns]
        if not cx:
            return {"frac": 1.0, "detail": "no functions to score"}
        avg = sum(cx) / len(cx)
        worst = max(cx)
        # avg cc <=5 excellent -> 1.0 ; >=15 poor -> 0.0
        frac = max(0.0, min(1.0, (15 - avg) / 10))
        return {"frac": frac, "detail": f"avg complexity {avg:.1f}, worst {worst} over {len(cx)} funcs"}
    if kind == "eslint":
        if not tool_exists("eslint") and not tool_exists("npx"):
            return {"frac": 0.0, "detail": "eslint not installed", "skipped": True}
        rc, out = run(spec.get("cmd") or "npx eslint . -f json", target)
        try:
            data = json.loads(out)
            errs = sum(f.get("errorCount", 0) for f in data)
            warns = sum(f.get("warningCount", 0) for f in data)
            frac = max(0.0, 1.0 - (errs * 0.1 + warns * 0.02))
            return {"frac": frac, "detail": f"{errs} errors, {warns} warnings"}
        except Exception:
            return {"frac": 0.5, "detail": "eslint ran, output unparsed", "skipped": True}
    if spec.get("cmd"):
        return _score_exit_code(target, spec["cmd"])
    return {"frac": 0.0, "detail": "no complexity tool configured", "skipped": True}


def score_security(target, src, spec):
    kind = spec.get("kind")
    if kind == "bandit":
        if not tool_exists("bandit"):
            return {"frac": 0.0, "detail": "bandit not installed", "skipped": True}
        rc, out = run(spec.get("cmd") or ["bandit", "-r", src, "-f", "json", "-q"], target)
        try:
            data = json.loads(out)
        except Exception:
            return {"frac": 0.0, "detail": "bandit output unparsable", "skipped": True}
        sev = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for r in data.get("results", []):
            sev[r.get("issue_severity", "LOW").upper()] = sev.get(r.get("issue_severity", "LOW").upper(), 0) + 1
        hard = sev["HIGH"] > 0 and spec.get("hard_gate", True)
        frac = max(0.0, 1.0 - (sev["HIGH"] * 0.5 + sev["MEDIUM"] * 0.15 + sev["LOW"] * 0.05))
        return {"frac": frac, "detail": f"HIGH={sev['HIGH']} MED={sev['MEDIUM']} LOW={sev['LOW']}",
                "hard_gate_failed": hard}
    if kind == "npm-audit":
        if not tool_exists("npm"):
            return {"frac": 0.0, "detail": "npm not installed", "skipped": True}
        rc, out = run(spec.get("cmd") or "npm audit --json", target)
        try:
            data = json.loads(out)
            vulns = data.get("metadata", {}).get("vulnerabilities", {})
            high = vulns.get("high", 0) + vulns.get("critical", 0)
            frac = max(0.0, 1.0 - (high * 0.5 + vulns.get("moderate", 0) * 0.15 + vulns.get("low", 0) * 0.05))
            return {"frac": frac, "detail": f"crit/high={high} mod={vulns.get('moderate',0)}",
                    "hard_gate_failed": high > 0 and spec.get("hard_gate", True)}
        except Exception:
            return {"frac": 1.0, "detail": "no npm audit findings parsed"}
    if spec.get("cmd"):
        return _score_exit_code(target, spec["cmd"], hard_gate=spec.get("hard_gate", True))
    return {"frac": 0.0, "detail": "no security tool configured", "skipped": True}


def score_secrets(target, src):
    hits = []
    for path in iter_text_files(src):
        if "harness" in path.split(os.sep):
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        for pat, label in SECRET_PATTERNS:
            if re.search(pat, content):
                hits.append(f"{label} in {os.path.relpath(path, target)}")
    frac = 1.0 if not hits else 0.0
    return {"frac": frac, "detail": ("clean" if not hits else "; ".join(hits[:5])),
            "hard_gate_failed": bool(hits)}


def read_reviewer(target):
    path = os.path.join(target, "harness", "reviewer.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8-sig") as f:  # utf-8-sig tolerates a BOM (Windows Out-File)
        return json.load(f)


# ---------------- orchestration ----------------

def _rev_checklist(reviewer, key, legacy_key):
    """Score an LLM criterion from a Boolean checklist (yes / total). The reviewer emits only
    booleans + evidence, so the number is a deterministic aggregation, not a holistic guess.
    Falls back to a legacy holistic float if that's what reviewer.json still contains."""
    val = reviewer.get(key)
    if isinstance(val, dict) and isinstance(val.get("checks"), list):
        checks = val["checks"]
        total = len(checks)
        if total == 0:
            return {"frac": 0.0, "detail": "empty checklist", "skipped": True}
        yes = sum(1 for c in checks if c.get("answer") is True)
        return {"frac": yes / total, "detail": f"{yes}/{total} checks pass"}
    for k in (legacy_key, key):
        v = reviewer.get(k)
        if isinstance(v, (int, float)):
            return {"frac": float(v), "detail": f"reviewer float (legacy): {v}"}
    return {"frac": 0.0, "detail": "reviewer.json missing this criterion", "skipped": True}


def evaluate(target, src, tc, ctx):
    reviewer = read_reviewer(target) or {}
    results = {}

    results["tests"] = score_tests(target, tc["test"])
    results["testcov"] = score_coverage(target, src, tc.get("coverage", {}))
    results["quality"] = score_quality(target, src, tc["complexity"])
    results["security"] = score_security(target, src, tc["security"])
    results["secrets"] = score_secrets(target, src)
    results["traceability"] = score_traceability(target)
    results["functional"] = _rev_checklist(reviewer, "functional", "requirements_coverage")
    results["readability"] = _rev_checklist(reviewer, "readability", "readability")
    results["nfr"] = _rev_checklist(reviewer, "nfr", "non_functional")
    # conditional criteria = mechanical tool half + LLM checklist half, averaged over whichever is present
    results["ux"] = _combine([score_tool(target, src, tc.get("ux", {})),
                              _rev_checklist(reviewer, "ux", "ux")])
    results["iac"] = _combine([score_tool(target, src, tc.get("iac", {})),
                               _rev_checklist(reviewer, "iac", "deploy_readiness")])

    # Normalize over the APPLICABLE weights: a criterion whose `applies` context is off is dropped
    # from BOTH numerator and denominator (not a penalty). A criterion that applies but was skipped
    # (no tool/reviewer input) stays in the denominator and scores 0 (reported loudly).
    rows, num, den, hard_failed = [], 0.0, 0.0, []
    for key, label, weight, applies in WEIGHTS:
        if applies == "ui" and not ctx["ui"]:
            continue
        if applies == "deploy" and not ctx["deploy"]:
            continue
        r = results[key]
        num += r["frac"] * weight
        den += weight
        if r.get("hard_gate_failed"):
            hard_failed.append(label)
        rows.append({"key": key, "label": label, "weight": weight, "applies": applies,
                     "frac": round(r["frac"], 3),
                     "detail": r["detail"], "skipped": r.get("skipped", False)})

    total = round(num / den * 100.0, 1) if den else 0.0
    for row in rows:  # normalized points/cap so the column sums to `total`
        row["points"] = round(row["frac"] * row["weight"] / den * 100.0, 1) if den else 0.0
        row["max"] = round(row["weight"] / den * 100.0, 1) if den else 0.0

    verdict = "PASS" if (total >= PASS_THRESHOLD and not hard_failed) else "FAIL"
    skipped = [r["label"] for r in rows if r["skipped"]]
    return {"verdict": verdict, "total": total, "threshold": PASS_THRESHOLD,
            "applicable_weight": round(den, 1), "context": ctx,
            "hard_gates_failed": hard_failed, "skipped_criteria": skipped, "criteria": rows}


def save_results(target, run_record):
    path = os.path.join(target, "harness", "results.json")
    history = {"schema": 1, "runs": []}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                history = json.load(f)
        except Exception:
            pass
    prev = history["runs"][-1] if history["runs"] else None
    history["runs"].append(run_record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    return prev


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True)
    p.add_argument("--src", help="code dir to scan (default: target)")
    p.add_argument("--stack", help="toolchain selector (any string; python/js are built in)")
    p.add_argument("--config", help="path to an eval.config.json (default: <target>/harness/eval.config.json)")
    p.add_argument("--test-cmd")
    p.add_argument("--ui", choices=["auto", "on", "off"], default="auto",
                   help="force the UI/UX criterion on/off (default: auto-detect + declared flags)")
    p.add_argument("--deploy", choices=["auto", "on", "off"], default="auto",
                   help="force the IaC/deploy criterion on/off (default: auto-detect + declared flags)")
    p.add_argument("--json", action="store_true", help="print machine JSON only")
    a = p.parse_args()

    if not os.path.isdir(a.target):
        print(f"target not a directory: {a.target}", file=sys.stderr)
        return 2

    state = read_state(a.target)
    stack = a.stack or state.get("stack", "python")
    src = a.src or a.target
    stack, tc = resolve_toolchain(a.target, stack, a.config, a.test_cmd)
    ctx = resolve_applicability(a.target, src, state, load_config(a.target, a.config), a.ui, a.deploy)

    result = evaluate(a.target, src, tc, ctx)
    record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stack": stack, **result,
    }
    prev = save_results(a.target, record)
    if prev:
        record["regression"] = {"prev_total": prev.get("total"),
                                "delta": round(result["total"] - prev.get("total", 0), 1),
                                "prev_verdict": prev.get("verdict")}

    if a.json:
        print(json.dumps(record, indent=2))
    else:
        c = result["context"]
        print(f"\n  SDLC EVAL — {result['verdict']}  ({result['total']}/100, threshold {PASS_THRESHOLD})")
        print(f"  applicable dimensions: UI/UX {'ON' if c['ui'] else 'off'} · "
              f"IaC/deploy {'ON' if c['deploy'] else 'off'} "
              f"(score normalized over {result['applicable_weight']:.0f} raw weight)\n")
        print(f"  {'Criterion':<46}{'Max':>5}{'Score':>8}{'Pts':>7}   Detail")
        print("  " + "-" * 92)
        for r in result["criteria"]:
            flag = " [skipped]" if r["skipped"] else ""
            print(f"  {r['label']:<46}{r['max']:>5.0f}{r['frac']*100:>7.0f}%{r['points']:>7.0f}   {r['detail']}{flag}")
        print("  " + "-" * 92)
        print(f"  {'TOTAL':<46}{'100':>5}{'':>8}{result['total']:>7}")
        if result["skipped_criteria"]:
            print(f"\n  NOTE: {len(result['skipped_criteria'])} scored criteria SKIPPED "
                  f"(no tool configured/installed): {', '.join(result['skipped_criteria'])}.")
            print("        These count as 0 — declare tools in harness/eval.config.json so they score.")
        if result["hard_gates_failed"]:
            print(f"\n  HARD GATES FAILED: {', '.join(result['hard_gates_failed'])}")
        if "regression" in record:
            reg = record["regression"]
            print(f"\n  Regression vs previous: {reg['prev_total']} -> {result['total']} (delta {reg['delta']:+})")
        print()

    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
