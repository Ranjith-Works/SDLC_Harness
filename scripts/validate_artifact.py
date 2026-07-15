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


def validate(path: str, kind: str | None) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    kind = kind or detect_kind(path)
    result = {"path": path, "kind": kind, "valid": True, "missing": [], "warnings": []}

    if kind is None or kind not in REQUIRED:
        result["warnings"].append("unknown artifact kind; skipped section checks")
        return result

    present = headers(text)
    for req in REQUIRED[kind]:
        if norm(req) not in present:
            result["missing"].append(req)

    if result["missing"]:
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
