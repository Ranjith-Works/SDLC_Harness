#!/usr/bin/env python3
"""Structural validator for SDLC harness artifacts.

Checks that a stage artifact contains its required section headers and is not
still a template stub (no un-filled `<!-- ... -->` placeholders under a heading
with no real content). Used by `/sdlc:gate` and by the PostToolUse hook.

Usage:
    python validate_artifact.py <path-to-artifact.md>
    python validate_artifact.py --kind prd <path>     # force artifact kind

Exit codes:
    0 = valid ; 1 = missing sections / stub ; 2 = usage / file error
Prints a JSON summary to stdout so callers can parse it.
"""
import argparse
import json
import os
import re
import sys

# Required top-level section headers per artifact kind (matched case-insensitively,
# ignoring markdown heading level and trailing punctuation).
REQUIRED = {
    "prd": [
        "Overview", "Problem Statement", "Goals", "Non-Goals",
        "Functional Requirements", "Non-Functional Requirements", "Success Metrics",
    ],
    "stories": ["Story Index", "Stories"],
    "trd": [
        "Architecture Overview", "Tech Stack", "Data Model",
        "API / Interface Design", "Story -> Implementation Map", "Testing Strategy",
        "Security & Guardrails",
    ],
    "review": ["Verdict", "Weighted Scorecard", "Hard Gates", "Findings"],
}

# Map filename fragments -> artifact kind.
KIND_BY_NAME = [
    ("01-prd", "prd"), ("prd", "prd"),
    ("02-user-stories", "stories"), ("user-stories", "stories"), ("stories", "stories"),
    ("03-trd", "trd"), ("trd", "trd"),
    ("06-review", "review"), ("review", "review"),
]


def detect_kind(path: str) -> str | None:
    base = os.path.basename(path).lower()
    for frag, kind in KIND_BY_NAME:
        if frag in base:
            return kind
    return None


def headers(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if m:
            out.append(m.group(1).strip().rstrip(":").lower())
    return out


def norm(s: str) -> str:
    return s.strip().rstrip(":").lower()


def content_under_headings(text: str) -> bool:
    """True if at least one section has real (non-comment, non-blank) content."""
    lines = text.splitlines()
    in_section = False
    for line in lines:
        if re.match(r"^#{1,6}\s+", line):
            in_section = True
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<!--") or stripped.startswith(">"):
            continue
        # a markdown comment can span lines; skip lines that are inside one crudely
        return True
    return False


def content_rules(kind: str, text: str) -> list[dict]:
    """Deterministic per-kind content checks, each a Boolean {rule, pass}. Mechanical: these
    verify the artifact carries the traceable structure the pipeline depends on."""
    def has(pattern):
        return bool(re.search(pattern, text, re.I))

    if kind == "prd":
        return [
            {"rule": "declares numbered functional requirements (FR-#)", "pass": has(r"FR-\d+")},
        ]
    if kind == "stories":
        return [
            {"rule": "declares user stories (US-#)", "pass": has(r"US-\d+")},
            {"rule": "stories trace to requirements (Traces to: FR-#)", "pass": has(r"traces to")},
            {"rule": "has Given/When/Then acceptance criteria", "pass": has(r"given") and has(r"when") and has(r"then")},
        ]
    if kind == "trd":
        return [
            {"rule": "has a Story -> Implementation map", "pass": has(r"story\s*->|story\s*to\s*impl|implementation map")},
            {"rule": "references user stories (US-#)", "pass": has(r"US-\d+")},
            {"rule": "specifies a test command/strategy", "pass": has(r"test")},
        ]
    if kind == "review":
        return [
            {"rule": "states a PASS/FAIL verdict", "pass": has(r"\bPASS\b|\bFAIL\b")},
        ]
    return []


def validate(path: str, kind: str | None) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    kind = kind or detect_kind(path)
    result = {"path": path, "kind": kind, "valid": True, "missing": [],
              "rules": [], "rule_failures": [], "warnings": []}

    if kind is None or kind not in REQUIRED:
        result["warnings"].append("unknown artifact kind; skipped section checks")
        return result

    present = headers(text)
    for req in REQUIRED[kind]:
        if norm(req) not in present:
            result["missing"].append(req)

    result["rules"] = content_rules(kind, text)
    result["rule_failures"] = [r["rule"] for r in result["rules"] if not r["pass"]]

    if result["missing"] or result["rule_failures"]:
        result["valid"] = False
    if not content_under_headings(text):
        result["valid"] = False
        result["warnings"].append("artifact appears to be an empty template (no filled content)")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--kind", choices=sorted(REQUIRED.keys()))
    a = p.parse_args()

    if not os.path.isfile(a.path):
        print(json.dumps({"error": f"not a file: {a.path}"}))
        return 2

    res = validate(a.path, a.kind)
    print(json.dumps(res, indent=2))
    return 0 if res["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
