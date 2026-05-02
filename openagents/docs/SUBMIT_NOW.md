---
name: Submission-Day Playbook
description: Step-by-step walkthrough to file all 8 ETHGlobal forms + record demo video. Designed to take under 60 minutes once you sit down with `SUBMISSIONS.md` and a browser open.
---

# Submission-Day Playbook

> 9 user-action items remain. The repo is hackathon-clean and CI-green; these are click-through tasks that require **your** ETHGlobal login and **your** screen/voice.
> Estimated time: 60 minutes if you follow the order below.

---

## Pre-flight (5 min — do once before opening any forms)

### 1. Repo access for judges

Go to `https://github.com/AgenticPlace/openagents/settings/access` and either:
- Flip repo to public (one click in repo Settings → Danger Zone → Change visibility), **or**
- Add ETHGlobal as collaborators if their judging system needs auth

The submission forms link to GitHub. Without judge access, the submissions can't be evaluated.

### 2. Polish the two FEEDBACK contact handles

```bash
cd /home/hacker/mindX
sed -i 's/Telegram: TBD, X: TBD/Telegram: <your-handle>, X: <your-handle>/' \
    openagents/docs/keeperhub/FEEDBACK.md \
    openagents/docs/uniswap/FEEDBACK.md
git add openagents/docs/keeperhub/FEEDBACK.md openagents/docs/uniswap/FEEDBACK.md
git commit -m "feedback: fill in contact handles for submission"
git push agenticplace_openagents main
```

### 3. Open these tabs

- `https://ethglobal.com/events/openagents/prizes` — prize index
- `openagents/docs/SUBMISSIONS.md` (in your editor or browser) — paste source
- `openagents/docs/LIVE_EVIDENCE.md` — fallback if a sponsor asks "is this real"

---

## Order of operations

File the **strongest-evidence** forms first. If your time runs out partway, the most defensible submissions are already in.

| Priority | Form | Why first | Paste anchor |
|---|---|---|---|
| **1** | 0G iNFT-7857 | 57 forge tests + 95.65% coverage + Slither bug fixed + live UI | `SUBMISSIONS.md` § Form 1 |
| **2** | Gensyn AXL Conclave | 35 Solidity + 9 Python tests + 8-node demo | `SUBMISSIONS.md` § Form 3 |
| **3** | ENS BANKON Best Integration | 29 fuzz tests + 94.85% coverage | `SUBMISSIONS.md` § Form 4 |
| **4** | Uniswap V4 Trader | Live V4 Quoter + persona constraints + FEEDBACK.md | `SUBMISSIONS.md` § Form 8 |
| **5** | KeeperHub Best Use | Dual-rail bridge live on prod | `SUBMISSIONS.md` § Form 6 |
| **6** | KeeperHub Builder Bounty | FEEDBACK.md (one-doc submission) | `SUBMISSIONS.md` § Form 7 |
| **7** | 0G Framework / Tooling | sidecar + zerog_handler | `SUBMISSIONS.md` § Form 2 |
| **8** | ENS Most Creative | Same project as Form 3, creative angle | `SUBMISSIONS.md` § Form 5 |
| **9** | **Demo video** | All forms accept video URL paste-in late | record after forms 1-4 are filed |

---

## Per-form recipe (repeat 8x)

For each form on `https://ethglobal.com/events/openagents/showcase`:

1. **"Project name"** field → copy the `**Project name:**` line from `SUBMISSIONS.md` for that form
2. **"Tagline / short description"** (≤ 140 chars typical) → copy `**Short description / tagline:**`
3. **"Long description"** → copy `**Long description:**` block (multiple paragraphs)
4. **"How it's built"** / "What technologies" → copy `**How it's built:**` block
5. **"Tech stack"** field → copy `**Tech stack:**` line
6. **"Tracks applied for"** → confirm the track matches the form (form already determines this)
7. **"GitHub link"** → `https://github.com/AgenticPlace/openagents`
8. **"Demo video link"** → fill in once you have the YouTube/Loom URL (forms typically allow editing post-submit)
9. **"Live demo link"** → use the per-track URL from the table at the top of `SUBMISSIONS.md`:
   - Form 1 → `https://mindx.pythai.net/inft7857`
   - Form 2 → `https://mindx.pythai.net/zerog`
   - Form 3 → `https://mindx.pythai.net/conclave`
   - Form 4 → `https://mindx.pythai.net/bankon-ens`
   - Form 5 → `https://mindx.pythai.net/bankon-ens` (same)
   - Form 6 → `https://mindx.pythai.net/keeperhub`
   - Form 7 → `https://mindx.pythai.net/keeperhub` (or link `openagents/docs/keeperhub/FEEDBACK.md` directly)
   - Form 8 → `https://mindx.pythai.net/uniswap`
10. **Hit Submit**

---

## Time budgets

| Block | Target | What you're doing |
|---|---|---|
| Pre-flight (1-3) | 5 min | Repo visibility · contact handles · open tabs |
| Forms 1-4 (strongest evidence) | 30 min | ~7-8 min/form |
| Forms 5-8 (variations) | 20 min | ~5 min/form (mostly variations of forms already filed) |
| Demo video | last 30 min | one Loom recording, paste URL into all 8 forms (most platforms let you edit submissions for ~24h) |
| **Total** | **~85 min** | |

If short on time: file forms 1-4 first; even 4-of-8 submissions are valid entries.

---

## Demo video (60 seconds)

Record this once. Loom's the fastest. Script is 60 seconds:

```
0:00–0:08  PITCH
  "I'm shipping eight agnostic, composable peer modules for AI agents on
   Ethereum. mindX is the consumer that wires them together. ETHGlobal
   Open Agents — five sponsor tracks, eight prize slots, 193 tests
   passing across 7 suites, 87% coverage, Slither audited."

0:08–0:23  COMPOSITION DEMO
  Open https://mindx.pythai.net/openagents — point at the 8-module
  diagram. "Each module ships standalone with its own README, tests,
  and Solidity contracts. Cabinet is the bonus: shadow-overlord vault
  that signs as the agent without leaking the key."

0:23–0:38  iNFT-7857 LIVE
  Click through to /inft7857 — show the 9-tab console. "Fifty-seven
  Foundry tests including a Slither-found cross-function reentrancy
  bug we fixed mid-hackathon with an active-exploit regression test."

0:38–0:50  AXL + KEEPERHUB
  Run `curl -s https://mindx.pythai.net/p2p/keeperhub/info | jq .accepts`
  on screen — show dual-rail Base + Tempo envelope. "And conclave is
  the AXL-native distributed boardroom: 35 Solidity tests, both
  contracts at 100% line coverage."

0:50–1:00  CLOSE
  "Repo: github.com/AgenticPlace/openagents. Live demo:
   mindx.pythai.net/openagents. CI green on all 8 jobs. Thanks."
```

Tools (any one):
- **Loom** (browser, fastest) — `https://loom.com/record`
- **OBS** (free, more polish) — `https://obsproject.com`
- **QuickTime** on macOS — Cmd+Shift+5

Upload, copy URL, paste into the demo-video field on each of the 8 forms.

---

## Reference cheat sheet (single screen)

```
Repo:        https://github.com/AgenticPlace/openagents
Live demo:   https://mindx.pythai.net/openagents
Tag:         v1.0.0-ethglobal
Test count:  193 (CI green)
Coverage:    87% Cabinet · 100% Conclave Solidity · 89-96% daio Solidity
Audit:       Slither v0.11.5 — 2 bugs fixed + permanent CI guard

Per-track consoles (paste into Live Demo URL field):
  /inft7857   /zerog        /conclave   /bankon-ens
  /keeperhub  /uniswap      /agentregistry  /cabinet (bonus)

Per-track docs (source of truth for paste text):
  openagents/docs/0g/README.md
  openagents/docs/ens/README.md
  openagents/docs/keeperhub/README.md
  openagents/docs/uniswap/README.md
  openagents/docs/axl/README.md
```

---

## After submission

Once all 8 forms are in:

1. Watch ETHGlobal Discord / Telegram for sponsor questions
2. If a judge asks "is this live?" → point them at `LIVE_EVIDENCE.md`
3. If they ask "is this tested?" → CI badge on the README
4. If they ask "is this audited?" → `tests/results/2026-05-02/SLITHER_REPORT.md`
5. If they ask "did you find any bugs?" → Yes, two: cross-function reentrancy in `iNFT_7857.mintAgent` (Slither) + in-memory state leak in cabinet rollback (test); both fixed with active-exploit regression tests in CI

The repo holds. The infrastructure is durable. Tomorrow's deadline closes the window — until then, nothing further from the engineering side adds value.
