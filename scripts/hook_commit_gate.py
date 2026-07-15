#!/usr/bin/env python3
"""PreToolUse hook: block `git commit` / `git push` until the review gate has passed.

Reads the hook JSON from stdin. If the Bash command is a git commit or push and the
project's harness/STATE.md does NOT show `gates.review: approved`, block the call
(exit code 2 + stderr reason). Otherwise allow (exit 0). If there is no harness run
in this project, do nothing.
"""
import json
import os
import re
import sys


def review_approved(cwd):
    state = os.path.join(cwd, "harness", "STATE.md")
    if not os.path.isfile(state):
        return None  # no harness run -> not our concern
    with open(state, encoding="utf-8-sig") as f:
        text = f.read()
    m = re.search(r"^\s*review:\s*(\w+)", text, re.M)
    return bool(m and m.group(1).lower() == "approved")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input", {}) or {}).get("command", "")
    if not re.search(r"\bgit\s+(commit|push)\b", cmd):
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    approved = review_approved(cwd)
    if approved is None:
        return 0  # no harness -> allow
    if approved:
        return 0  # gate passed -> allow
    sys.stderr.write(
        "[sdlc] Commit/push blocked: the review gate has not passed. "
        "Run /sdlc:review and approve it via /sdlc:gate (STATE.md gates.review must be "
        "'approved') before shipping. This enforces 'don't ship un-reviewed code.'\n"
    )
    return 2  # exit code 2 => PreToolUse blocks the tool call


if __name__ == "__main__":
    sys.exit(main())
