#!/usr/bin/env python3
"""PreToolUse hook: block deployment commands until the deployment gate has passed.

Reads the hook JSON from stdin. If the Bash command looks like a deploy/provision action
(terraform apply, kubectl apply, docker push, helm upgrade, gh workflow run, cdk/pulumi/
serverless/vercel/fly deploy, ...) and the project's harness/STATE.md does NOT show BOTH
`gates.review: approved` AND `gates.iac: approved`, block the call (exit 2 + stderr reason).
Otherwise allow (exit 0). If there is no harness run in this project, do nothing.

This is the deployment tollgate: the harness generates the IaC/CI-CD (via /sdlc:iac) and
gates it, but never lets un-reviewed, un-gated infrastructure ship.
"""
import json
import os
import re
import sys

# Deploy/provision verbs we guard. Kept deliberately specific so read-only commands
# (terraform plan, kubectl get, docker build) are NOT blocked.
DEPLOY_PATTERNS = [
    r"\bterraform\s+(apply|destroy)\b",
    r"\bkubectl\s+(apply|delete|rollout|create)\b",
    r"\bdocker\s+push\b",
    r"\bhelm\s+(install|upgrade|uninstall)\b",
    r"\bgh\s+workflow\s+run\b",
    r"\b(cdk|pulumi)\s+(deploy|up)\b",
    r"\bserverless\s+deploy\b",
    r"\bsls\s+deploy\b",
    r"\b(vercel|netlify|wrangler|flyctl|fly)\s+deploy\b",
    r"\bansible-playbook\b",
    r"\baws\s+(deploy|cloudformation\s+(deploy|create-stack|update-stack))\b",
]


def _gate(text, name):
    m = re.search(rf"^\s*{name}:\s*(\w+)", text, re.M)
    return bool(m and m.group(1).lower() == "approved")


def deploy_allowed(cwd):
    """None => no harness (not our concern). True/False => gate state."""
    state = os.path.join(cwd, "harness", "STATE.md")
    if not os.path.isfile(state):
        return None
    with open(state, encoding="utf-8-sig") as f:
        text = f.read()
    # only the machine-readable gates block matters; require review AND iac both approved
    return _gate(text, "review") and _gate(text, "iac")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input", {}) or {}).get("command", "")
    if not any(re.search(p, cmd) for p in DEPLOY_PATTERNS):
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    allowed = deploy_allowed(cwd)
    if allowed is None:
        return 0  # no harness -> allow
    if allowed:
        return 0  # both gates passed -> allow
    sys.stderr.write(
        "[sdlc] Deployment blocked: the deployment gate has not passed. "
        "Run /sdlc:iac to generate + review the infrastructure/CI-CD, then approve it via "
        "/sdlc:gate. Both STATE.md gates.review AND gates.iac must be 'approved' before any "
        "deploy/provision command runs. This enforces 'don't ship un-reviewed infrastructure.'\n"
    )
    return 2  # exit code 2 => PreToolUse blocks the tool call


if __name__ == "__main__":
    sys.exit(main())
