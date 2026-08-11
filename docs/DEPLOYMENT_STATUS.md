# Deployment Status — Gödel subsystem & AuthorAgent

**Deployed 2026-06. Verified live against `mindx.pythai.net` on 2026-08-10.**

> **This document previously said the opposite.** It was written on 2026-06-04,
> when the work sat unmerged on a feature branch, and it kept asserting "NOT yet
> deployed" for roughly two months after the deploy actually happened. A status
> document is the one file whose staleness is indistinguishable from a lie, since
> its entire content is a claim about *now*. Corrected by probing production
> rather than by re-reading the branch.

## TL;DR

The Gödel subsystem **is deployed and running** on `mindx.pythai.net`
(`168.231.126.58`). Every capability this document once listed as pending
responds in production. The honest verdict the subsystem itself returns is
unchanged and remains the point: `NOT_YET_A_GODEL_MACHINE`.

Live, verified 2026-08-10:

- `/insight/godel/machine` → **Phase 3**, all eight predicates G1–G8 live and
  testable, `verdict: NOT_YET_A_GODEL_MACHINE`.
- `/insight/milestones/recent`, `/insight/godel/recent`,
  `/insight/godel/ascend`, `/insight/publications/recent` → all HTTP 200.
- **mindXtrain is no longer dormant.** `/insight/godel/ascend` reports
  `installed: true`, `enabled: true`, `armed: true`, `cpu_train_active: true`,
  `version 1.0.0`, `torch 2.12.0+cpu`, at `/home/mindx/mindXtrain`. The
  deployment checklist below still said to keep it dormant; that instruction was
  overtaken by the v1.0.0 CPU-training work and is corrected in place.

**Current blockers are substantive, not deployment state.** `G2=FALSIFIED`
(ungated self-mod surface change: 13 ungated changes observed against the
manifest) and `proof_coverage = 0% < 50%`. Real proof coverage is what the
verdict is waiting on — not a restart.

## Branch vs. live — component matrix

Probed against production 2026-08-10. "Live" means the endpoint answered or the
service reported the state itself — not that the file exists in a checkout.

| Capability | Live VPS (`mindx.pythai.net`) | Evidence |
|---|---|---|
| Gödel eval Phases 0–3 (`mindx/godel/eval/`, `kernel/`, `utility.py`) | ✅ live — 6/8 `PROVEN-so-far`, G2 `FALSIFIED`, G8 `UNTESTED` | `/insight/godel/machine` |
| `/insight/godel/machine` endpoint | ✅ 200, Phase 3, `NOT_YET_A_GODEL_MACHINE` | probed |
| `/insight/milestones/recent` endpoint | ✅ 200 | probed |
| `/insight/godel/recent` · `/insight/godel/ascend` | ✅ 200 | probed |
| mindXtrain bridge (`mindx/godel/mindxtrain/`) | ✅ live and **armed** — `cpu_train_active: true`, v1.0.0, torch 2.12.0+cpu | `/insight/godel/ascend` |
| Schmidhüber Engine (`mindx/godel/schmidhuber_engine.py`) | ✅ deployed | ships with the subsystem |
| AuthorAgent `github.awareness` + milestones + DOC_INDEX | ✅ deployed | `/insight/publications/recent` 200 |
| `PublicationOrchestrator.watch_github()` | ✅ running | publishing endpoints live |
| feedback.html / landing / agentic.html GMI panels | ✅ rendered | served from the deployed service |
| Book of mindX lunar writing | ✅ live (pre-existing) | unchanged |

## Seeded artifacts are from the dev checkout, not the VPS

`docs/MILESTONES.md` and `data/milestones/milestone_log.jsonl` in this branch
were seeded from **this development checkout's** git history (the Gödel/
Schmidhüber commits). They are correct as a demonstration, but they are **not**
the live VPS's chronicle. After deploy, the live AuthorAgent will append/
regenerate from the VPS's own git history; the seeded rows simply bootstrap the
file. Runtime ledgers (`data/godel/*.jsonl`, `data/godel/source_ledger.jsonl`)
are git-ignored and are created fresh on the host where the service runs.

## Deployment checklist (VPS)

The VPS is a git checkout at `/home/mindx/mindX/` run by systemd
(`mindx.service`, `User=mindx`) behind Apache + Let's Encrypt. See
[`DEPLOYMENT_MINDX_PYTHAI_NET.md`](DEPLOYMENT_MINDX_PYTHAI_NET.md).

**Historical — this deploy is done.** Retained as the procedure for the next
one.

1. **Review & merge** the feature branch (open a PR; do not self-merge without
   review — this touches the public claim and a critical agent).
2. On the VPS, as the `mindx` user:
   ```bash
   cd /home/mindx/mindX
   git fetch origin
   git checkout main && git pull            # (after the branch is merged)
   # no new pip deps: the Gödel subsystem is stdlib-only
   ```
3. **Restart** the service so the new AuthorAgent, orchestrator watcher, and
   routes load:
   ```bash
   sudo systemctl restart mindx.service
   sudo systemctl status mindx.service
   ```
4. **Verify** (expect HTTP 200 / sensible JSON):
   ```bash
   curl -s https://mindx.pythai.net/insight/godel/machine?h=true
   curl -s https://mindx.pythai.net/insight/milestones/recent?h=true
   # GMI panel + milestones panel visible on:
   #   https://mindx.pythai.net/feedback.html#sec-godel-machine
   #   https://mindx.pythai.net/feedback.html#sec-milestones
   # honest GMI headline on the landing page; eval-gate GMI line on /agentic.html
   ```
5. **Confirm AuthorAgent is updated:** the first non-routine commit pushed from
   the VPS after restart should appear in `/insight/milestones/recent`, and
   `docs/DOC_INDEX.md` should regenerate. `backup_agent`'s `Pre-shutdown
   backup:` commits must be filtered out (not chronicled).
6. ~~**Keep mindXtrain dormant.**~~ **Superseded.** mindXtrain reached v1.0.0
   and CPU training is deliberately armed in production
   (`MINDX_ENABLE_MINDXTRAIN` + `MINDX_ENABLE_AUTONOMOUS_TRAIN`; arming the
   first alone never trains). See [MINDXTRAIN_INSTALL.md](MINDXTRAIN_INSTALL.md)
   and `/insight/godel/ascend` for live telemetry.

## What stays NOT_YET after deploy

Deploying does not flip the Gödel-machine verdict. On the VPS the GMI will read
`NOT_YET_A_GODEL_MACHINE` with blockers (G1/G2 untested until runtime data
accrues; `proof_coverage` climbs only as `self_improve_agent` gates real
changes past 50%). That is by design — the verdict is earned at runtime, not by
deployment. See [`GODEL_EVAL_BLUEPRINT.md`](GODEL_EVAL_BLUEPRINT.md).
