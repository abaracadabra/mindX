# gitmind — self-contained git monitor + multi-source backup/rollback

gitmind is mindX's own backup and rollback substrate for its source tree. It
watches the git repository, records every rollback (and distinguishes the ones
mindX initiates on itself), snapshots the whole repo as a git bundle, and
**replicates that bundle across variable backup sources** — local filesystem,
IPFS (via Lighthouse), and Arweave. It is self-contained: the standard library
plus `git` plus the existing `agents.storage` providers (loaded lazily). Every
operation is guarded — gitmind never raises into the caller.

> **Standalone project:** gitmind is also a separate MIT, model-agnostic library —
> [github.com/Professor-Codephreak/gitmind](https://github.com/Professor-Codephreak/gitmind).
> It has no LLM dependency (works the same with GLM-4.5/5.2, Llama, Qwen, Claude…).
> This page documents the mindX-integrated build (THOT/iNFT anchoring + OVERLORD gating).

- Module: `mindx/gitmind/gitmind.py` (`GitMind`, `get_gitmind`)
- Ledger: `data/gitmind/ledger.jsonl` (append-only, rebuildable view)
- Bundles: `data/gitmind/backups/*.bundle` (local; newest 3 kept)
- Live: `GET /insight/gitmind` (public diagnostics; `?h=true` for plain text)

## Why

A self-improving system edits its own code. That demands a containment and
expansion story: the ability to **roll back** a bad self-change, to **record**
that it happened (ordinary vs self-initiated), and to **replicate** the repo so
no single disk loss is fatal. gitmind is that story — git is already the unit of
change, so the backup unit is a git bundle and the rollback unit is a commit.

## What it records (the ledger)

Append-only events in `data/gitmind/ledger.jsonl`:

| kind | when | key fields |
|------|------|-----------|
| `snapshot` | each monitor tick, no HEAD move or forward only | `head`, `branch`, `transition` |
| `rollback` | HEAD moved to an ancestor / diverged, not self-flagged | `from`, `to`, `transition`, `reflog_op` |
| `self_rollback` | a rollback mindX initiated on itself | `from`, `to`, `op`, `self_initiated: true` |
| `backup` | an (incremental) THOT was made + linked + replicated | `seq`, `incremental`, `thot_root`, `parent_root`, `thlnk_id`, `asset_kind`, `cid`, `replicas`, `self_host_ok` |
| `backup_skipped` | HEAD unchanged → no-op (the cheap-frequent path) | `head`, `reason`, `thlnk_id` |
| `anchor` | a backup CID registered on-chain (THOT/iNFT) | `cid`, `anchor_kind`, `tx_hash`, `chain` |

**Rollback classification** is git-ancestry based, not guesswork:

- HEAD's new commit is an **ancestor** of the previous HEAD → `rollback` (moved backward).
- previous HEAD is an ancestor of the new one → `advance` (ordinary forward commits).
- neither → `reset` (history diverged: reset/force to a different line).

A rollback is **self-initiated** when mindX calls `GitMind.mark_self_rollback()`
immediately before reverting (or uses `rollback_to()`, which marks it). The next
snapshot reads the flag and records `self_rollback`. This is how the system
tells *"a human/CI rolled us back"* from *"we rolled ourselves back."*

## Self-hosting + THlNK (the THOT lINK) — distributed mindX

gitmind is mindX's **extremely efficient, self-hosted git method**: it does not need
GitHub to have a durable, restorable home.

- **Self-hosted origin.** `ensure_self_host()` + `mirror_push()` keep a local bare
  repository `data/gitmind/self.git` in sync using git's native packfile
  negotiation — **only deltas travel** (O(new-objects), not O(repo)). It is a real,
  cloneable origin mindX owns. `clone_self_host(dest)` restores a working tree from it.
- **Incremental THOTs.** Each `backup()` bundles only what is new since the last
  backup (`git bundle --all --not <basis>`), a tiny **immutable, content-addressed
  THOT**. When HEAD is unchanged it is a pure no-op (`skipped: no new commits`) — the
  cheap-frequent property. The first/`--full` backup is a self-contained **basis** THOT.
- **THlNK = the link of THOTs.** Every THOT carries a canon-congruent `thot_root`
  (binary Merkle over 256 KiB UnixFS-aligned chunks, RFC-6962 prefixes, Keccak-256)
  and a `parent_root` pointing at the prior THOT — a lineage chain (genesis
  `parent_root = 0x00…00`). The ordered chain is the **THlNK** (THINK spelled with an
  ell — a THOT lINK), recorded in `data/gitmind/thlnk.json` and content-addressed by
  `thlnk_id`. Replicated to Lighthouse + Arweave, **the THlNK is distributed mindX**:
  `reconstruct_from_thlnk(dest)` applies the THOT chain in order and rebuilds the repo
  exactly — fetching any missing THOT from the permaweb by CID/txid.
- **iNFT / THOT anchoring.** A backup containing tensor artifacts anchors its CID as a
  **THOT**; a code/dir backup anchors as an **iNFT** (`MINDX_GITMIND_ANCHOR=1`).

This is the git-native instantiation of the canonical architecture in
[`docs/operations/THOT, THLNK, and ERC-7857 INFTs`](operations/THOT,%20THLNK,%20and%20ERC-7857%20INFTs_%20A%20Production%20Architecture%20for%20Agent%20Boardroom%20Governance.md):
THOT = content-addressed Merkle-committed artifact; THLNK = the self-describing
pointer (`thot_root` + `cid` + iNFT/x402); the `parent_root` chain to a checkpoint is
the lineage that, on-chain, `MindXCheckpointRegistry` enforces. gitmind realizes that
model off-chain with git bundles as the THOT bodies.

## Forgejo forge — the web-accessible origin mindX owns (git.pythai.net)

The bare `self.git` is fast but same-disk; the permaweb THlNK is durable but slow to
clone. **Forgejo** (the GPLv3 [Gitea fork](https://forgejo.org/faq/)) is the third leg
of the origin triad: a live, browseable, HTTP(S) forge running on mindX's own VPS at
**https://git.pythai.net** — no GitHub dependency, but a real web UI, issues, and
`git clone`/`push` over HTTPS. It fits the *repo-private-pending-audit* posture: the
mirror repo is created **private** by default.

A forge is a git *remote*, not a blob store, so it is **not** a `_Source` — it pushes
refs (`git push --mirror`) the way `mirror_push` syncs the bare origin. `ForgejoRemote`
is dormant + guarded until configured, and **never logs the token** (the auth URL is
only ever a subprocess argument; any echoed token is scrubbed from errors).

| config key (env wins over vault) | meaning | default |
|---|---|---|
| `MINDX_FORGEJO_URL` / `forgejo_url` | forge base | — (dormant when unset) |
| `MINDX_FORGEJO_TOKEN` / `forgejo_token` | access token, scope `write:repository` | — |
| `MINDX_FORGEJO_USER` / `forgejo_user` | push username | `mindx` |
| `MINDX_FORGEJO_REPO` / `forgejo_repo` | `owner/name` | `mindx/mindX` |

`backup()` pushes to Forgejo at **step 1b** — before the skip-on-no-change check — so
ref moves reach the forge even when there are no new commits to bundle. `ensure_repo()`
best-effort creates the private mirror via the Forgejo API (stdlib only, no SDK) on
first push. Surfaced in `report()["forgejo"]` and `scripts/gitmind.py forgejo[ --status]`.

**Install (VPS, operator-run):** `scripts/install_forgejo.sh` is idempotent — binary +
`git` system user + `/var/lib/forgejo` + `/etc/forgejo`, **reuses Postgres** (own DB),
binds `127.0.0.1:3000`, writes the systemd unit, and creates the admin + a push token.
It makes **no** Apache/DNS/cert changes itself; it prints the next steps. The reverse
proxy is `deploy/apache/git-pythai-net.conf` (+ `certbot --apache -d git.pythai.net`).

## Backup sources (variable, pluggable)

Each incremental THOT (and the THlNK manifest itself) fans out to every configured
source concurrently:

| source | backing | configured by | status when unset |
|--------|---------|---------------|-------------------|
| `local` | `data/gitmind/backups/` (newest 3 kept) | always on | always available |
| `ipfs` | `agents.storage` MultiProvider → Lighthouse | `LIGHTHOUSE_API_KEY` / vault `lighthouse_api_key` | `not_configured` |
| `arweave` | permanent on-chain (`arweave` client) | vault `arweave_wallet_jwk` | `not_configured` |

Each source returns `{name, ok, ref, ...}` — a local path, an IPFS CID (+ gateway
URL), or an Arweave tx id (+ gateway URL). Sources that aren't configured report
`not_configured` and are simply skipped; the backup still succeeds as long as one
replica lands. This is the "variable source" contract: replication scales to
whatever is wired up, and new sources slot in behind the same `_Source` interface.

> Only the **first** (basis) THOT is full history; every later THOT is a small delta,
> so frequent IPFS/Arweave replication is cheap. Local `.bundle` copies are pruned to
> the newest 3 — the permaweb holds the full chain, and `reconstruct_from_thlnk`
> back-fills any locally-pruned THOT from its CID/txid.

## Rollback / restore

```python
from mindx.gitmind import get_gitmind
gm = get_gitmind()
gm.rollback_to("<sha>")              # safe: git revert --no-edit <sha>..HEAD (keeps history)
gm.rollback_to("<sha>", hard=True)   # git reset --hard <sha>  (gated by MINDX_GITMIND_ALLOW_HARD=1)
```

`rollback_to()` backs up first, marks the action self-initiated, then moves HEAD.
The **safe default is `git revert`** (no history rewrite); the destructive
`reset --hard` path is gated behind an explicit env flag so an autonomous loop
can never silently rewrite history.

## Usage

```python
from mindx.gitmind import get_gitmind
gm = get_gitmind()
gm.snapshot()                     # monitor tick: record state, classify transition, log rollbacks
await gm.backup()                 # incremental THOT (skips if unchanged) + self-host + THlNK
await gm.backup(full=True)        # force a fresh basis THOT (new THlNK root)
gm.mirror_push()                  # delta-sync the self-hosted origin only
gm.forgejo.push()                 # mirror to the self-hosted Forgejo forge (dormant until configured)
gm.clone_self_host("/tmp/clone")  # restore a working tree from the self-hosted origin
gm.reconstruct_from_thlnk("/tmp/rebuild")  # rebuild from the link of THOTs
gm.thlnk_summary(); gm.report()   # the /insight/gitmind view (+ self_host + thlnk)
```

```bash
python scripts/gitmind.py status        # state + self-host + THlNK head
python scripts/gitmind.py backup         # incremental THOT (skips if unchanged)
python scripts/gitmind.py thlnk          # the link of THOTs (lineage)
python scripts/gitmind.py forgejo --status  # Forgejo forge config (no push)
bash scripts/install_forgejo.sh          # (VPS, operator) stand up git.pythai.net
python scripts/gitmind.py reconstruct /tmp/rebuild   # rebuild from the THlNK chain
curl -s https://mindx.pythai.net/insight/gitmind?h=true   # state + backups + rollback history
```

## Roadmap (contain → expand → replicate)

- ✅ Incremental THOT bundles (`--all --not basis`) + skip-on-no-change for cheap frequent IPFS/Arweave replication.
- ✅ Self-hosted bare origin (`mirror_push`) + restore (`clone_self_host`, `reconstruct_from_thlnk`, permaweb back-fill).
- ✅ THlNK lineage: per-THOT `thot_root` (Keccak/RFC-6962 Merkle) + `parent_root` chain; iNFT/THOT CID anchoring.
- ✅ Forgejo forge leg: `ForgejoRemote` (`git push --mirror`, token-redacted, API repo auto-create) + `scripts/install_forgejo.sh` + `deploy/apache/git-pythai-net.conf`. *Built locally; not yet installed on the VPS.*
- Wire `snapshot()` into the heartbeat and `backup()` into the dream cycle (Phase 8 alongside the IPFS offload projector).
- On-chain THlNK: register the lineage in `MindXCheckpointRegistry`; mint per-THOT ERC-7857 iNFTs binding `thot_root` + `keccak(thlnk)`.
- Tests: `tests/test_gitmind_efficient.py` (incremental, skip, lineage, self-host clone, full reconstruction).
