#!/usr/bin/env python3
"""Scaffold the working `harness/` directory + STATE.md inside a target project.

Usage:
    python init_harness.py --target <dir> --mode greenfield|brownfield [--stack python|js]

Idempotent: never clobbers an existing STATE.md unless --force is given.
STATE.md carries a machine-readable YAML block that the skills, hooks, and the
eval harness all read/write. Keep the keys stable.
"""
import argparse
import os
import sys
from datetime import datetime, timezone

BASE_STAGES = [
    ("intake", "00-INTAKE.md / 00-CODEBASE-MAP.md"),
    ("prd", "01-PRD.md"),
    ("stories", "02-USER-STORIES.md"),
    ("trd", "03-TRD.md"),
    ("implement", "(source code)"),
    ("test", "05-TEST-REPORT.md"),
    ("review", "06-REVIEW.md"),
]
DESIGN_STAGE = ("design", "04-UX-SPEC.md")   # inserted after `stories` when the project has a UI
IAC_STAGE = ("iac", "07-DEPLOY.md")          # appended after `review` when there is a deploy target


def build_stages(ui: bool, deploy: bool):
    """The effective pipeline for this project. Conditional stages (design, iac) are only added
    when relevant, so a backend-only run keeps the short 7-stage pipeline."""
    stages = list(BASE_STAGES)
    if ui:
        idx = [s[0] for s in stages].index("stories") + 1
        stages.insert(idx, DESIGN_STAGE)
    if deploy:
        stages.append(IAC_STAGE)
    return stages


def state_template(mode: str, stack: str, target: str, ui: bool, deploy: bool) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    intake_artifact = "00-INTAKE.md" if mode == "greenfield" else "00-CODEBASE-MAP.md"
    stages = build_stages(ui, deploy)
    rows = "\n".join(
        f"| {name} | {art if name != 'intake' else intake_artifact} | pending |"
        for name, art in stages
    )
    gate_lines = "\n".join(f"  {name}: pending" for name, _ in stages)
    return f"""# SDLC Harness — State

<!-- MACHINE-READABLE BLOCK: skills/hooks/eval read these keys. Do not remove. -->
```yaml
mode: {mode}            # greenfield | brownfield
stack: {stack}          # eval toolchain selector: python | js | go | java | rust | ruby | (custom via eval.config.json)
ui: {str(ui).lower()}              # true => project has a UI: adds the design stage + ux scoring
deploy: {str(deploy).lower()}          # true => project has a deploy target: adds the iac stage + deployment gate
target: {target}
current_stage: intake
created: {now}
gates:
{gate_lines}
```

## Pipeline

| Stage | Artifact | Gate status |
|---|---|---|
{rows}

## Log
- {now} — harness initialized (mode={mode}, stack={stack}, ui={str(ui).lower()}, deploy={str(deploy).lower()})
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True)
    p.add_argument("--mode", required=True, choices=["greenfield", "brownfield"])
    p.add_argument("--stack", default="python",
                   help="eval toolchain selector (any string; python/js/go/java/rust/ruby built in, others via eval.config.json)")
    p.add_argument("--ui", action="store_true", help="project has a UI (adds the design stage + ux scoring)")
    p.add_argument("--deploy", action="store_true",
                   help="project has a deploy target (adds the iac stage + deployment gate)")
    p.add_argument("--force", action="store_true")
    a = p.parse_args()

    hdir = os.path.join(a.target, "harness")
    os.makedirs(hdir, exist_ok=True)
    state_path = os.path.join(hdir, "STATE.md")
    audit_path = os.path.join(hdir, "AUDIT.log")

    if os.path.exists(state_path) and not a.force:
        print(f"STATE.md already exists at {state_path} (use --force to overwrite). No changes.")
        return 0

    with open(state_path, "w", encoding="utf-8") as f:
        f.write(state_template(a.mode, a.stack, os.path.abspath(a.target), a.ui, a.deploy))
    if not os.path.exists(audit_path):
        open(audit_path, "a", encoding="utf-8").close()

    print(f"Initialized harness at {hdir}")
    print(f"  STATE.md  -> {state_path}")
    print(f"  AUDIT.log -> {audit_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
