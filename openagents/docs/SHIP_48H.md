---
name: 48-Hour Ship Roadmap — ETHGlobal Open Agents
description: Critical path from now (May 1) to submission deadline (May 6). 48h push covers everything except final polish.
type: roadmap
---

# 48-Hour Ship Roadmap — ETHGlobal Open Agents

> **Today:** 2026-05-01 · **Deadline:** 2026-05-06 · **Push window:** next 48h (Fri–Sat)
> **Goal:** all 8 submission forms filed by end of hour 36, leaving 12h+12h buffer for sponsor questions.

---

## Status snapshot

- ✅ Doc reorg complete — `docs/INDEX.md`, per-track `docs/{0g,ens,keeperhub,uniswap,axl}/README.md`, `LIVE_EVIDENCE.md`
- ✅ Test suites green — 119 forge (iNFT 56, BANKON 29, THOT 14, AgentRegistry 20) + 9 conclave Python
- ✅ Local backend up at port 8000 — all UI routes 200
- ✅ Live console up — https://mindx.pythai.net/openagents
- ⚠️ Prod gap — `/p2p/keeperhub/info` returns 404 (stale deploy)
- ⚠️ Conclave forge tests — `lib/forge-std` missing (user must `forge install`)
- ⚠️ Reorg uncommitted — `git status` shows ~25 file moves staged

---

## Phase 1 — Critical fixes (hours 0–8)

### 1. Deploy KeeperHub bridge to prod
```bash
scp openagents/keeperhub/bridge_routes.py mindx@168.231.126.58:/home/mindx/mindX/openagents/keeperhub/
ssh root@168.231.126.58 "chown mindx:mindx /home/mindx/mindX/openagents/keeperhub/bridge_routes.py && systemctl restart mindx.service"
curl -s https://mindx.pythai.net/p2p/keeperhub/info | jq .  # expect 200, not 404
```
**Why:** KeeperHub Best Use track requires live evidence. Prod is running stale code.

### 2. Install `forge-std` for Conclave contracts
```bash
cd openagents/conclave/contracts
forge install foundry-rs/forge-std --no-git --no-commit
forge test  # expect 10 tests green
```
**Why:** AXL track judges may run the contract tests. Without forge-std they all fail.

### 3. Commit doc reorg
```bash
cd /home/hacker/mindX
git add openagents/README.md openagents/docs/ openagents/.gitignore
git rm openagents/conclave.tar.gz 2>/dev/null
git commit -m "openagents: reorg docs into per-track folders + INDEX.md + LIVE_EVIDENCE.md"
git push
```
**Why:** Submission forms link to GitHub; reorg must be on `main`.

### 4. Verify FEEDBACK content is real
- `openagents/docs/keeperhub/FEEDBACK.md` — already 85 lines, dated Apr 27. **Read it; polish only if a specific friction point is missing.**
- `openagents/docs/uniswap/FEEDBACK.md` — already populated. Same: **read + polish, don't rewrite.**

---

## Phase 2 — Submission content (hours 8–16)

### 5. Record demo video (1-minute walkthrough)
ETHGlobal forms typically require a Loom or YouTube link. Cover in 60s:
- 0–10s: pitch ("8 agnostic modules, mindX is the demo consumer")
- 10–25s: `/openagents.html` composition demo
- 25–40s: `/inft7857` 9-tab console — mint flow
- 40–55s: live curl `/p2p/keeperhub/info` + Conclave 8-node mesh visualization
- 55–60s: GitHub URL

### 6. Update `LIVE_EVIDENCE.md` with prod-verified outputs
After Phase 1 step 1 lands, re-run the smoke loop and paste real `curl -s` output blocks under each track section.

### 7. Smoke-test full live console
```bash
for path in /openagents /inft7857 /feedback.html /THOT.html /docs; do
  curl -sI https://mindx.pythai.net$path | head -1
done
```

---

## Phase 3 — File the 8 forms (hours 16–32)

Each form: paste from the corresponding `docs/{track}/README.md` + GitHub URL + demo video URL.

- [ ] **0G — Best Autonomous Agents / iNFT** → `docs/0g/INFT_7857.md`
- [ ] **0G — Best Framework, Tooling & Core Extensions** → `docs/0g/README.md` (sidecar + zerog_handler)
- [ ] **Gensyn — AXL** → `conclave/SUBMISSION.md`
- [ ] **ENS — Best Integration for AI Agents** → `docs/ens/README.md`
- [ ] **ENS — Most Creative Use of ENS** → `docs/ens/README.md` (creative angle: soulbound bundled-with-ERC-8004 agent identity)
- [ ] **KeeperHub — Best Use of KeeperHub** → `docs/keeperhub/README.md`
- [ ] **KeeperHub — Builder Feedback Bounty** → `docs/keeperhub/FEEDBACK.md`
- [ ] **Uniswap — Best API Integration** → `docs/uniswap/README.md`

---

## Phase 4 — Polish & buffer (hours 32–48)

- Monitor sponsor Discord/Telegram for judge questions
- Re-run all 8 verification commands from `LIVE_EVIDENCE.md` once more
- Draft a single-tweet announcement for X/Farcaster pinned to submission
- If a sponsor asks for something specific (more tests, a contract redeploy, a video re-cut), this is where the buffer lives

---

## Out of scope for the 48h push

- New features. The submission ships what's in the tree today.
- Refactoring `agents.storage.zerog_provider` factory protocol.
- Authoring fresh content for FEEDBACK.md (existing Apr 27 content is the artifact).
- New chains, new tokens, new tests beyond what's already green.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Prod restart fails after deploy | Local backend already verified; can demo locally if VPS hiccups |
| `forge install` blocked by sandbox | User runs interactively; ~30 sec |
| Sponsor wants a deep technical Q&A | `docs/INDEX.md` + `LIVE_EVIDENCE.md` are the prepared answer surfaces |
| Demo video record fails | Each `docs/{track}/README.md` is self-sufficient as a written submission |
