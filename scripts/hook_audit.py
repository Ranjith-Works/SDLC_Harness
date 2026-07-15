#!/usr/bin/env python3
"""Audit hook: append a stage-transition / subagent event line to harness/AUDIT.log.

Wired to SubagentStop (and usable for SessionStart). Reads the hook JSON payload
from stdin, resolves the project's harness dir from `cwd`, and appends a timestamped
line. Never blocks — always exits 0.
"""
import json
import os
import sys
from datetime import datetime, timezone


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    cwd = payload.get("cwd") or os.getcwd()
    event = payload.get("hook_event_name", "event")
    hdir = os.path.join(cwd, "harness")
    if not os.path.isdir(hdir):
        return 0  # no active harness run here
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    detail = payload.get("agent_type") or payload.get("tool_name") or ""
    line = f"{ts} | {event} | {detail}".rstrip(" |")
    try:
        with open(os.path.join(hdir, "AUDIT.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
