# Deployment Status — Gödel subsystem & AuthorAgent

**As of 2026-06-04. Read this before assuming any of the Gödel-machine /
milestone / DOC_INDEX behaviour is live.**

## TL;DR

All of the following is **implemented and verified on the feature branch
`claude/inspiring-carson-22XTs`** — and is **NOT yet deployed to the live VPS**
(`mindx.pythai.net`, `168.231.126.58`). The live service runs the previous
release. In particular, **the live AuthorAgent has not been updated**, so on the
public site it does *not* yet:

- recognize or chronicle milestones from the public git history
  (`github.awareness`),
- maintain `docs/MILESTONES.md` or `docs/DOC_INDEX.md` automatically,
- publish the calibrated ("building toward a Gödel machine") claim,
- serve `/insight/godel/machine` or show the GMI / milestones panels on
  `feedback.html`, the landing page, or `agentic.html`.

These will begin working only after the branch is deployed and `mindx.service`
is restarted on the VPS.

## Branch vs. live — component matrix

| Capability | Branch `claude/inspiring-carson-22XTs` | Live VPS (`mindx.pythai.net`) |
|---|---|---|
| Schmidhüber Engine (`mindx/godel/schmidhuber_engine.py`) | ✅ present (dormant scaffold) | ❌ absent |
| mindXtrain bridge (`mindx/godel/mindxtrain/`) | ✅ present (dormant; `MINDX_ENABLE_MINDXTRAIN=0`) | ❌ absent |
| Gödel eval Phases 0–3 (`mindx/godel/eval/`, `kernel/`, `utility.py`) | ✅ present, 5/8 predicates PROVEN | ❌ absent |
| `/insight/godel/machine` endpoint | ✅ in `main_service.py` | ❌ 404 until deploy |
| `/insight/milestones/recent` endpoint | ✅ in `main_service.py` | ❌ 404 until deploy |
| feedback.html GMI + milestones panels | ✅ added | ❌ not rendered until deploy |
| landing-page GMI headline + calibrated hero | ✅ added | ❌ old hero ("A Darwin-Godel Machine") still live |
| agentic.html eval-gate GMI line | ✅ added | ❌ not present until deploy |
| AuthorAgent `github.awareness` + milestones + DOC_INDEX | ✅ present | ❌ **old AuthorAgent — none of this runs** |
| AuthorAgent calibrated claim (`author_agent.py`) | ✅ calibrated | ❌ old "I am a Godel machine" text still ships in new editions |
| `PublicationOrchestrator.watch_github()` | ✅ wired at startup | ❌ not running until deploy |
| Book of mindX lunar writing | ✅ (unchanged) | ✅ already live (pre-existing) |

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

1. **Review & merge** `claude/inspiring-carson-22XTs` (open a PR; do not
   self-merge without review — this touches the public claim and a critical
   agent).
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
6. **Keep mindXtrain dormant** unless explicitly arming it
   (`MINDX_ENABLE_MINDXTRAIN` stays unset until the external project is
   validated — see the bridge's isolation contract).

## What stays NOT_YET after deploy

Deploying does not flip the Gödel-machine verdict. On the VPS the GMI will read
`NOT_YET_A_GODEL_MACHINE` with blockers (G1/G2 untested until runtime data
accrues; `proof_coverage` climbs only as `self_improve_agent` gates real
changes past 50%). That is by design — the verdict is earned at runtime, not by
deployment. See [`GODEL_EVAL_BLUEPRINT.md`](GODEL_EVAL_BLUEPRINT.md).
