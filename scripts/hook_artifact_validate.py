#!/usr/bin/env python3
"""PostToolUse hook: after a Write/Edit to harness/*.md, validate its structure.

Reads the hook JSON from stdin, pulls the edited file path from tool_input, and if
it is a harness artifact (01-PRD / 02-USER-STORIES / 03-TRD / 06-REVIEW) runs the
section validator. Emits a NON-blocking warning (exit 0) if a required section is
missing so the author can fix it — a structural nudge, not a gate.
"""
import json
import os
import subprocess
import sys

VALIDATABLE = ("01-prd", "02-user-stories", "03-trd", "06-review",
               "prd.md", "user-stories.md", "trd.md", "review.md")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    ti = payload.get("tool_input", {}) or {}
    path = ti.get("file_path") or ti.get("path") or ""
    base = os.path.basename(path).lower()
    if "harness" not in path.replace("\\", "/").split("/"):
        return 0
    if not any(frag in base for frag in VALIDATABLE):
        return 0

    here = os.path.dirname(os.path.abspath(__file__))
    validator = os.path.join(here, "validate_artifact.py")
    try:
        proc = subprocess.run([sys.executable, validator, path],
                              capture_output=True, text=True, timeout=30)
    except Exception:
        return 0
    if proc.returncode == 1:
        # non-blocking warning surfaced to the user/agent
        try:
            data = json.loads(proc.stdout)
            missing = data.get("missing", [])
            warns = data.get("warnings", [])
            msg = f"[sdlc] Artifact {base} may be incomplete."
            if missing:
                msg += f" Missing sections: {', '.join(missing)}."
            if warns:
                msg += f" {' '.join(warns)}"
            print(msg, file=sys.stderr)
        except Exception:
            print(f"[sdlc] Artifact {base} failed structural validation.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
