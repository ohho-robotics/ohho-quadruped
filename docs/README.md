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

| Runbook | What it is |
|---|---|
| [Go2 sport-mode motion (OHH-137)](runbooks/go2-sport-motion.md) | Staged procedure for a later human session. Nothing in it has been executed. |
| [Evidence template (OHH-137)](runbooks/go2-sport-motion-evidence-template.md) | Empty table. Dates, videos, logs, stop times, and results are unfilled. |

**Needs Varun: physically present with the remote; Go2 EDU access (OHH-135).**

An agent session must not arm hardware and must not run those motion steps.
Further sim-setup and arming runbooks are still planned for later milestones
(M1 onward, November 2026).

## Notes

- ADR 0001 records the key decisions: Go2 EDU target, sport-mode first,
  MuJoCo sim, safety rules, scheduling, and code boundaries.
- Nothing in docs/ constitutes a capability claim. Everything is planning
  or decision-recording.
