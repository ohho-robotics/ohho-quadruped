# docs/ — ADRs and runbooks

**Status: in progress.**

This directory will hold Architecture Decision Records (ADRs) and runbooks.

## ADRs

| ID | Title | Status |
|---|---|---|
| 0001 | Unitree Go2: target, sport-mode first, MuJoCo-first sim, safety rules | Proposed (PR #3) |

ADR 0001 is open in PR #3 and has not yet been merged:
https://github.com/ohho-robotics/ohho-quadruped/pull/3

Do **not** create or edit anything under `docs/adr/` on this branch — that
directory is owned by PR #3 to avoid add/add conflicts.

## Runbooks

**Needs Varun: physically present, Go2 EDU access (OHH-135).**

| Runbook | What it is |
|---|---|
| [Go2 bring-up](runbooks/go2-bringup.md) | Six-step read-only procedure. Written in advance. Not executed. No motion. |
| [Evidence template](runbooks/go2-bringup-evidence-template.md) | Blank sheet for that procedure. Measured cells stay empty in git. |

`python scripts/check_bringup_runbook.py` checks those two files offline
(no DDS import, no socket). Further runbooks (sim setup, later motion)
are still planned for M1 onward, November 2026.

## Notes

- ADR 0001 records the key decisions: Go2 EDU target, sport-mode first,
  MuJoCo sim, safety rules, scheduling, and code boundaries.
- Nothing in docs/ constitutes a capability claim. Everything is planning
  or decision-recording.
