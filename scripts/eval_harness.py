#!/usr/bin/env python3
"""Weighted SDLC eval harness — the scorecard behind `/sdlc:review`.

Scores a target project out of 100 across 7 weighted criteria, applies HARD
GATES (any tripped => FAIL regardless of score), writes versioned results to
`harness/results.json`, and compares against the previous run for regression.

Deterministic criteria (tests, complexity, security, secrets) are computed by
this script. LLM-judged criteria (requirements coverage, traceability,
readability) are read from `harness/reviewer.json`, which the reviewer sub-agent
writes before this runs. This split keeps the score reproducible.

Toolchain is pluggable per stack (read from harness/STATE.md `stack:` key, or
--stack): python -> pytest / radon / bandit ; js -> npm test / eslint / npm audit.

Usage:
    python eval_harness.py --target <dir> [--src <code-dir>] [--stack python|js]
                           [--test-cmd "..."] [--json]

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

# criterion key -> (label, weight). Mechanical criteria (tests, testcov, traceability,
# quality, security, secrets = 70 pts) are deterministic. LLM-judged criteria (functional,
# readability = 30 pts) come from reviewer.json as Boolean checklists aggregated to yes/total.
WEIGHTS = [
    ("tests", "Tests pass rate", 20),
    ("testcov", "Test coverage", 10),
    ("functional", "Functional review (requirements)", 20),
    ("traceability", "Traceability (mechanical)", 10),
    ("quality", "Code quality / complexity", 10),
    ("security", "Security scan", 15),
    ("readability", "Technical review (readability)", 10),
    ("secrets", "No secrets / PII", 5),
]
PASS_THRESHOLD = 80

# Built-in, normalized toolchains. A project can override/extend these with a
# harness/eval.config.json (same shape) so ANY stack plugs in without editing this file.
# Recognized complexity/security `kind`s: radon, eslint, bandit, npm-audit, and the generic
# "exit-code" (score from the tool's return code). Any unknown kind falls back to exit-code.
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
}
_TOOL_KEYS = ("test", "coverage", "complexity", "security")

SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
    (r"(?i)(api[_-]?key|secret|token|passwd|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]", "hardcoded credential"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "Slack token"),
    (r"gh[pousr]_[0-9A-Za-z]{30,}", "GitHub token"),
]
# files/dirs we never scan for secrets or complexity
SKIP_DIRS = {"harness", "node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build", ".pytest_cache"}


def run(cmd, cwd):
    """Run a shell command, capture output. Returns (rc, stdout+stderr)."""
    try:
        proc = subprocess.run(
            cmd if isinstance(cmd, list) else shlex.split(cmd),
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
        mm = re.match(r"^\s{0,2}(mode|stack|target|current_stage):\s*(\S+)", line)
        if mm:
            state[mm.group(1)] = mm.group(2)
    return state


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
    exts = (".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".env", ".yaml", ".yml", ".cfg", ".ini", ".txt", ".md")
    hits = []
    for path in iter_source_files(src, exts):
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


def evaluate(target, src, tc):
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

    rows, total, hard_failed = [], 0.0, []
    for key, label, weight in WEIGHTS:
        r = results[key]
        pts = round(r["frac"] * weight, 1)
        total += pts
        if r.get("hard_gate_failed"):
            hard_failed.append(label)
        rows.append({"key": key, "label": label, "weight": weight,
                     "frac": round(r["frac"], 3), "points": pts,
                     "detail": r["detail"], "skipped": r.get("skipped", False)})

    total = round(total, 1)
    verdict = "PASS" if (total >= PASS_THRESHOLD and not hard_failed) else "FAIL"
    # any criterion that was skipped (no tool/config/reviewer input) -> reported loudly
    skipped = [r["label"] for r in rows if r["skipped"]]
    return {"verdict": verdict, "total": total, "threshold": PASS_THRESHOLD,
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
    p.add_argument("--json", action="store_true", help="print machine JSON only")
    a = p.parse_args()

    if not os.path.isdir(a.target):
        print(f"target not a directory: {a.target}", file=sys.stderr)
        return 2

    state = read_state(a.target)
    stack = a.stack or state.get("stack", "python")
    src = a.src or a.target
    stack, tc = resolve_toolchain(a.target, stack, a.config, a.test_cmd)

    result = evaluate(a.target, src, tc)
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
        print(f"\n  SDLC EVAL — {result['verdict']}  ({result['total']}/100, threshold {PASS_THRESHOLD})\n")
        print(f"  {'Criterion':<28}{'Wt':>4}{'Score':>8}{'Pts':>7}   Detail")
        print("  " + "-" * 74)
        for r in result["criteria"]:
            flag = " [skipped]" if r["skipped"] else ""
            print(f"  {r['label']:<28}{r['weight']:>4}{r['frac']*100:>7.0f}%{r['points']:>7}   {r['detail']}{flag}")
        print("  " + "-" * 74)
        print(f"  {'TOTAL':<28}{'100':>4}{'':>8}{result['total']:>7}")
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
