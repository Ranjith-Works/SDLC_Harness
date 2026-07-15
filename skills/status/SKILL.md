---
name: status
description: Show the current SDLC run status from harness/STATE.md — mode, stack, current stage, per-stage gate approvals, and the next recommended command. Use anytime to see where the pipeline stands.
---

# /sdlc:status — where the run stands

## Steps
1. Read `harness/STATE.md` (and list which artifacts in `harness/` exist).
2. Print a compact summary:
   - **Mode / Stack / Target**
   - **Pipeline table:** stage | artifact | gate status (pending/approved) | exists?
   - **Current stage** and the **next command** to run.
3. If a `harness/results.json` exists, show the latest verdict + total and the last regression
   delta.
4. Keep it to a short readout — no changes to any file.
