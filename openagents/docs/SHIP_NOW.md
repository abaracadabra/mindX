---
name: 24-Hour Ship Roadmap — ETHGlobal Open Agents (Deadline Moved)
description: Hard pivot — deadline moved up to 2026-05-03. Single-day execution window. Video is now a blocker, not a polish item.
type: roadmap
---

# 24-Hour Ship Roadmap — ETHGlobal Open Agents

> **Today:** 2026-05-02 (evening) · **Deadline:** 2026-05-03 · **Window:** ~24h
> **Goal:** all 8 submission forms filed before deadline. Buffer compressed.
>
> **Pivot from earlier roadmap:** video was deferred. **It can no longer be deferred** — every form requires a demo video URL, and you cannot submit without one. Order of operations changes accordingly.
>
> Supersedes `SHIP_48H.md` (kept as historical reference).

---

## What changed

| | Old (48h) | New (24h) |
|---|---|---|
| Deadline | 2026-05-06 | **2026-05-03** |
| Push window | 48h | ~24h |
| Video position | Last (after submissions) | **Second** (after polish, before submissions) |
| Buffer | 12h+12h | ~3h |
| Cabinet prod activation | Optional bonus | **Skip** unless trivially fast — submission > polish |

---

## Status snapshot (entering the window)

| Item | State |
|---|---|
| 30 tests green (20 Cabinet pytest, 10 Conclave forge) | ✅ |
| Doc reorg + per-track READMEs + INDEX + LIVE_EVIDENCE | ✅ |
| `SUBMISSIONS.md` paste-ready blocks for all 8 forms | ✅ |
| KeeperHub deployed live to prod | ✅ |
| `openagents.html` + `inft7857` UI live on prod | ✅ |
| Cabinet code committed (auto-backup `fc22fce65`) + guide (`6701e4225`) | ✅ |
| Local repo state | 53 commits ahead of `cryptoagi/main` |
| Push remote chosen | ⚠️ NOT YET — blocks form submissions (links to GitHub) |
| Demo video | ⚠️ NOT YET — blocks ALL form submissions |
| FEEDBACK contact handles | ⚠️ Two `TBD` lines — fill before submission |

---

## Hour-by-hour (24h plan)

### Tonight, Hours 0–4 (May 2 evening, ~3h active work)

**Block A — Critical fixes (10 min):**

1. Pick the canonical public repo URL. Three candidates already in your remote list:
   - `cryptoagi/main` (current upstream — 53 commits behind, repo at `https://github.com/cryptoAGI/daio.git`)
   - `agenticplace` aka `origin` (`https://github.com/agenticplace/mindX.git`)
   - `abaracadabra` (`git@github.com:abaracadabra/mindX.git`)

   Or, if `Professor-Codephreak/mindX` is the canonical (matches the README): add it as a remote and push there. **Pick one**, then:
   ```bash
   git push <remote> main
   ```

2. Polish FEEDBACK contact handles:
   ```bash
   sed -i 's/Telegram: TBD, X: TBD/Telegram: <handle>, X: <handle>/' \
       openagents/docs/keeperhub/FEEDBACK.md \
       openagents/docs/uniswap/FEEDBACK.md
   git add openagents/docs/keeperhub/FEEDBACK.md openagents/docs/uniswap/FEEDBACK.md
   git commit -m "feedback: fill in contact handles for ETHGlobal submission"
   git push
   ```

**Block B — Video (40 min recording + cuts):**

Record a single 60-second walkthrough — this video is the demo URL for ALL 8 forms. Loom is fastest; YouTube unlisted is fine too.

Tight script (verbatim, time-coded):
```
0:00 — 0:08  PITCH
  "I'm shipping eight agnostic, composable peer modules for AI agents on
   Ethereum. mindX is the consumer that wires them together. ETHGlobal
   Open Agents — five sponsor tracks, eight prize slots, 138+20 tests
   passing."

0:08 — 0:23  COMPOSITION DEMO
  Open https://mindx.pythai.net/openagents — point at the 8-module
  diagram. "Each module ships standalone with its own README, tests,
  and Solidity contracts."

0:23 — 0:38  iNFT-7857 LIVE
  Click through to /inft7857 — show the 9-tab console. Mention "56 of 56
  Foundry tests, sealed-key transfer gating, oracle-signed re-encryption."

0:38 — 0:50  AXL + KEEPERHUB
  Run `curl -s https://mindx.pythai.net/p2p/keeperhub/info | jq .accepts`
  on screen — show dual-rail Base + Tempo envelope. Briefly mention the
  Conclave 8-node mesh and the Cabinet bonus (BANKON Vault signing oracle).

0:50 — 1:00  CLOSE
  "Repo: github.com/<your-canonical-url>. Live demo: mindx.pythai.net/
   openagents. Submission docs: openagents/docs/SUBMISSIONS.md. Thanks."
```

Tools: OBS, QuickTime, Loom, screencast — whichever is fastest. Do NOT spend time on cuts beyond a basic intro/outro fade.

Upload. Get the URL. Save it.

**Block C — File the 4 highest-confidence forms (60 min):**

Open `openagents/docs/SUBMISSIONS.md`. Copy-paste these in order — they're the ones with the strongest evidence and least integration risk:

1. **Form 1 — 0G iNFT-7857** (live UI + 56 tests)
2. **Form 3 — Gensyn AXL Conclave** (10 tests pass, 8-node demo)
3. **Form 4 — ENS Best Integration BANKON v1** (29 fuzz tests)
4. **Form 8 — Uniswap V4 Trader** (FEEDBACK.md required artifact already done)

Each form: paste the block, attach video URL, attach repo URL, submit. Don't iterate — each block is already sized to fit.

### Sleep, Hours 4–10 (~6h)

You've banked the 4 strongest submissions. The remaining 4 are variations that build on the same evidence. Sleep.

### Tomorrow morning, Hours 10–18 (~8h, includes some buffer)

**Block D — File remaining 4 forms (30 min):**

5. **Form 2 — 0G Framework** (sidecar + zerog_handler — same composition, different track angle)
6. **Form 5 — ENS Most Creative** (same registrar, creative pitch about credentials)
7. **Form 6 — KeeperHub Best Use** (live `/p2p/keeperhub/info`)
8. **Form 7 — KeeperHub Builder Bounty** (FEEDBACK.md submission)

**Block E — Active monitoring (until deadline):**

- Watch ETHGlobal Discord for sponsor questions
- Re-run `LIVE_EVIDENCE.md` smoke commands once
- Be ready to redeploy if a sponsor asks for a fix

**Block F — (optional) Cabinet activation if you have spare time:**

Generate offline wallet → set 2 env vars on prod → restart `mindx.service` → /cabinet now serves a clickable bonus demo. ~5 minutes if everything's smooth, but **skip if any submission is still pending** — the bonus doesn't substitute for a missing form.

---

## What I cannot do for you (in any order)

1. **Choose your canonical repo URL** — only you know which org / which org-of-yours is the canonical public mirror.
2. **Sign in to ETHGlobal** — your account, your forms.
3. **Record the video** — your face / voice / screen.
4. **Fill in real Telegram + X handles** — won't fabricate.
5. **Generate the offline shadow-overlord wallet** for the optional Cabinet activation — the wallet must never touch a server I have access to.

Everything else is staged, tested, committed, and documented in the repo.

---

## Risk register (compressed for 24h)

| Risk | Mitigation |
|---|---|
| Sponsor asks for a feature you don't have | The 30 tests + per-track README docs are your defense; respond with link to LIVE_EVIDENCE.md |
| Video upload fails / slow | Loom uploads in seconds; YouTube as fallback |
| Push to wrong remote | The repo URL is the only field that matters in the form — pick what's permanent |
| Form 4+5 (both ENS) gets rejected as duplicate | README claim is they're separate tracks; confirm on the form, fall back to one if needed |
| Cabinet activation fails on prod | Skip it. Submissions > bonus. |
| Sleep too long, miss deadline | Submit Forms 1, 3, 4, 8 tonight. Even a partial 4-of-8 is shippable. |

---

## Files you need open while working

```
openagents/docs/SUBMISSIONS.md       ← paste-ready blocks for all 8 forms
openagents/docs/LIVE_EVIDENCE.md     ← ammo for sponsor questions
openagents/docs/INDEX.md             ← master nav (links if you get lost)
openagents/docs/SHIP_NOW.md          ← this file
```

---

## After deadline

Whatever happens, the repo state is durable. The Cabinet bonus is independently valuable and ready to demonstrate at any time post-hackathon. The 30 tests will keep passing. The docs aren't going anywhere.

Submit, sleep, and see what the judges think.
