#!/usr/bin/env python3
"""Mechanical traceability check for SDLC harness artifacts.

Verifies the ID linkage across the document chain WITHOUT any LLM judgment:
  - every PRD functional requirement (FR-#) is referenced by at least one user story
  - every user story (US-#) appears in the TRD story -> implementation map

Returns per-check Booleans + an overall fraction. Deterministic: same artifacts in,
same result out. Used by eval_harness.py (Traceability criterion) and usable from /sdlc:gate.

Usage:
    python trace_check.py --target <dir> [--json]
Exit codes: 0 = all links present, 1 = missing links, 2 = nothing to trace.
"""
import argparse
import json
import os
import re


def _read(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _numkey(id_str: str) -> int:
    m = re.search(r"-(\d+)", id_str)
    return int(m.group(1)) if m else 0


def check(target: str) -> dict:
    h = os.path.join(target, "harness")
    prd = _read(os.path.join(h, "01-PRD.md"))
    stories = _read(os.path.join(h, "02-USER-STORIES.md"))
    trd = _read(os.path.join(h, "03-TRD.md"))

    prd_frs = sorted(set(re.findall(r"FR-\d+", prd)), key=_numkey)
    story_frs = set(re.findall(r"FR-\d+", stories))
    story_us = sorted(set(re.findall(r"US-\d+", stories)), key=_numkey)
    trd_us = set(re.findall(r"US-\d+", trd))

    if not prd_frs and not story_us:
        return {"skipped": True, "frac": 0.0, "passed": 0, "total": 0,
                "detail": "no FR/US ids found in artifacts", "checks": []}

    checks = []
    for fr in prd_frs:
        checks.append({"id": fr, "rule": "FR referenced by a user story",
                       "pass": fr in story_frs})
    for us in story_us:
        checks.append({"id": us, "rule": "US present in TRD story->impl map",
                       "pass": us in trd_us})

    total = len(checks)
    passed = sum(1 for c in checks if c["pass"])
    frac = 1.0 if total == 0 else passed / total
    missing = [c["id"] for c in checks if not c["pass"]]
    detail = f"{passed}/{total} links intact (FR->story, US->TRD)"
    if missing:
        detail += f"; missing: {', '.join(missing[:6])}"
    return {"skipped": False, "frac": frac, "passed": passed, "total": total,
            "detail": detail, "checks": checks,
            "counts": {"prd_frs": len(prd_frs), "story_us": len(story_us)}}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    r = check(a.target)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        if r.get("skipped"):
            print("Traceability: no FR/US ids found (run PRD + stories first).")
        else:
            print(f"Traceability: {r['detail']}")
            for c in r["checks"]:
                print(f"  [{'x' if c['pass'] else ' '}] {c['id']} — {c['rule']}")
    if r.get("skipped"):
        return 2
    return 0 if r["passed"] == r["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
