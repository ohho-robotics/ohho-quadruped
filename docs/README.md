# docs/ — ADRs and runbooks

**Status: in progress.**

This directory will hold Architecture Decision Records (ADRs) and runbooks.

## ADRs

| ID | Title | Status |
|---|---|---|
| 0001 | Unitree Go2: target, sport-mode first, MuJoCo-first sim, safety rules | Accepted ([0001-unitree-go2.md](adr/0001-unitree-go2.md)) |
| 0002 | Go2 velocity-policy training stack (scaffold) | Accepted scaffold ([0002-velocity-policy-training-stack.md](adr/0002-velocity-policy-training-stack.md)) |

ADR 0001 was merged to main in PR #3:
https://github.com/ohho-robotics/ohho-quadruped/pull/3

## Sibling follow-ups (OHH-133)

See [docs/sibling-followups.md](sibling-followups.md) for required honesty updates in:
- `ohho-os`: `docs/unitree.md` (planned: sim-tested only, not hardware-tested; domain 0 arming gates; sport-mode allowlist)
- `site`: `docs/ohho-os/robots.md` (sim-tested only, not hardware-tested; Vision until Go2 EDU available)

## Runbooks

**Needs Varun: physically present, Go2 EDU access (OHH-135).**

| Runbook | What it is |
|---|---|
| [Go2 bring-up](runbooks/go2-bringup.md) | Six-step read-only procedure. Written in advance. Not executed. No motion. |
| [Evidence template](runbooks/go2-bringup-evidence-template.md) | Blank sheet for that procedure. Measured cells stay empty in git. |
| [Go2 sport-mode motion (OHH-137)](runbooks/go2-sport-motion.md) | Staged procedure for a later human session. Nothing in it has been executed. |
| [Evidence template (OHH-137)](runbooks/go2-sport-motion-evidence-template.md) | Empty table. Dates, videos, logs, stop times, and results are unfilled. |

`python scripts/check_bringup_runbook.py` checks those two files offline
(no DDS import, no socket). The bring-up pair is the first two rows above.

**Needs Varun: physically present with the remote; Go2 EDU access (OHH-135).**

An agent session must not arm hardware and must not run those motion steps.
`python scripts/rehearse_sport_motion.py` rehearses the sport-motion steps offline on a fake transport.

Scaffold only (not a finished train): [train-velocity-policy.md](train-velocity-policy.md).

Runbooks for sim setup, hardware arming, and safety procedures will be added
as each milestone is completed (M1 onward, November 2026).

## Notes

- ADR 0001 records the key decisions: Go2 EDU target, sport-mode first,
  MuJoCo sim, safety rules, scheduling, and code boundaries.
- Nothing in docs/ constitutes a capability claim. Everything is planning
  or decision-recording.
