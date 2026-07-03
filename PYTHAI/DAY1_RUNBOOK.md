# PYTHAI Day-1 Runbook — the OVERLORD's command sequence

Everything an agent can prepare is DONE and rehearsed. What remains requires
your keys, your signature, or the Hostinger panel. House rule holds: an agent
never signs mainnet — you sign. Companion: `NAV.md` (the coherence map) and
`../..//DeltaVerse/deploy/web2/pythai/README.md` (web tenant detail).

## State handed to you (verified)

| item | state |
|---|---|
| Holdings gate | `gather-holdings --check` GREEN — `~/PYTHAI/holdings.json` generated (123 held) |
| BONA FIDE proof gate | localnet 21/0 refreshed → `DeltaVerse/deploy/localnet-deploy-bonafide.json` (deploy.html unlock) |
| Algorand A1–A4 driver | NEW `DeltaVerse/contracts/scripts/deploy-mainnet.ts` — rehearsed end-to-end on localnet (8/8 read-back, idempotent) |
| x402 E4+E5 script | NEW `DeltaVerse/scripts/deploy-x402-base.mjs` — rehearsed on anvil (all checks green, idempotent) |
| Base preflight | GREEN: Nick factory present, targets undeployed, gas 0.006 gwei, bankon.eth holds 0.039 ETH on Base |
| Web bundle | vhosts + landing + parsec dist RSYNCED to the VPS (`/root/pythai-web2/`, `/tmp/pythai-index.html`, `/tmp/parsec-dist/`) |
| Registry flip | template at `mindX/mindx_backend_service/static/agenticplace_deployments.day1.json` |

Deterministic addresses (same on EVERY chain — CREATE2/Nick):
```
Scientific            0x428222a63809C98FcA59fd0ca36619F551Ff67c0   (SCIEN·TIFIC first light)
iNFT_7857             0x8F880281aaa6D163552eBb11825e43f133188fD9
BankonPriceOracle     0xeb555cfF1603ad609446C82cF5807d65353Ca7C5
BankonReputationGate  0x0AE564598DcC4e6adAD049604A7d451586351510
BankonPaymentRouter   0xe5Abbcf71C6594CcdC92FBd15fd119983da22B5a
X402Receipt           0xCDf6CdE9be92433d2B23598D9eA5EC0B7be940a1
```

## 1 — Algorand BONA FIDE gate (A1–A4, honored first)

Fund an Algorand mainnet account with ≥ 12 ALGO, then:

**BONA FIDE is the keystone — completing it (21 checks) unlocks the whole EVM
suite E1–E10.** This is not four standalone apps; the tokens/identity/iNFT/x402/
DAIO stages below gate on this proof. Full map: DeploymentGuide.md §0.

Addresses (NFD-resolved 2026-07-02 — now genuinely separate keys):
treasury = **fortuna** (fortuna.algo) `CPVKAV6MACS65P3CLNZ43DR6YUC7O74FMIW7PGA373TVBORCX4IDARVOFQ` ·
admin = **mindx.algo** `L24WEG3KK6QDSQGQGXCJIYR46HHDFK5IJ7HOZF3YDDTHTREGYPDWY74KG4`
(the L24W deployer holds 11.53 ALGO — **top up to ~14**; the gate is 12).

```bash
cd ~/DeltaVerse/contracts
export ALGORAND_DEPLOYER_MNEMONIC='<25 words — shell only>'
export BONAFIDE_TREASURY='CPVKAV6MACS65P3CLNZ43DR6YUC7O74FMIW7PGA373TVBORCX4IDARVOFQ'  # fortuna.algo
export BONAFIDE_ADMIN='L24WEG3KK6QDSQGQGXCJIYR46HHDFK5IJ7HOZF3YDDTHTREGYPDWY74KG4'     # mindx.algo
ALGORAND_NETWORK=mainnet pnpm deploy:predict          # read-only sanity
ALGORAND_DEPLOY_MAINNET=true pnpm deploy:mainnet      # A1→A2→A3(wire)→A4
```
Manifest → `live/contracts/mainnet-deploy-bonafide.json` + `live/agenticplace/algorand-deploy.json`.
Then the proof unlocks the EVM suite (steps 2–7 below). Driver is idempotent.
Full review + suite map + fee map + audit: `~/DeltaVerse/contracts/DeploymentGuide.md`.
NOTE: contracts pin raw addresses — re-resolve NFDs at deploy time; admin is
permanent (no setAdmin), treasury (fortuna) is admin-changeable via setTreasury.

## 2 — SCIENTIFIC first light: Base canary

```bash
cd ~/DeltaVerse
PRIVATE_KEY=0x<funded Base key> ./deployer.sh base
```
Verify on basescan: code at `0x428222…67c0` (SCIEN·TIFIC) + `0x8F88…8fD9` (iNFT), `overlord()` = bankon.eth.

## 3 — Crosschain continuance: the primary trio

```bash
./deployer.sh          # serves the gate on :8141 — sign in as bankon.eth (SIWE)
```
In `pages/deploy.html`: DEPLOY → LAUNCH `settlement-tokens` on **Moonbeam 1284, Blast 81457, 0G**.
Continuance is proven the moment chain #2 lands at the SAME address. Then anchor
ENS `scientific.bankon.eth` on the ENS-home chain.

## 4 — x402 settlement stack (E4+E5) on Base

```bash
PRIVATE_KEY=0x<same key> node scripts/deploy-x402-base.mjs
```
Script self-verifies: admin role = bankon.eth on all four + `X402Receipt.router()` wired.
Record → `live/agenticplace/base-x402-deploy.json`.
(Do NOT use the deploy.html pay2play bundle for these — it points at different bytecode.)

## 5 — Registry flip (activates /inft mint handoff)

After explorer confirmation: fill the two `FILL_FROM_…` tx hashes in
`mindX/mindx_backend_service/static/agenticplace_deployments.day1.json` from
`live/agenticplace/base-deploy.json`, then replace `agenticplace_deployments.json`
with it and rsync to the VPS mindX static dir (+ restart mindx.service).

## 6 — Web estate: apex + every subdomain resolves

Hostinger DNS panel FIRST — A records → `168.231.126.58`:
`@` (apex — confirm it is not parked on the site builder), `www`, `gpt`, `parsec`, `bankon`, `agenticplace`.

Then on the VPS as root:
```bash
cd /root/pythai-web2 && ./deploy-pythai.sh bootstrap        # tenant, vhosts, certbot
install -m 644 /tmp/pythai-index.html /home/pythai/www/index.html
rsync -a /tmp/parsec-dist/ /home/pythai/www/parsec/
./deploy-pythai.sh update && ./deploy-pythai.sh status
```
gpt/bankon GitHub redirect targets are placeholders (github.com/AgenticPlace) —
repoint in the vhost + `subdomains.json` when confirmed.

## 7 — Day-1 announcement on rage.pythai.net

Draft: `DAY1_ANNOUNCEMENT_rage.md` (this folder) — fill the Algorand appIds + tx
hashes, then publish from the VPS (local vault has no WP creds):
```bash
ssh root@168.231.126.58
PYTHONPATH=/home/mindx/mindX sudo -u mindx /home/mindx/mindX/.mindx_env/bin/python \
  -c "…publish_to_rage…"        # per the established AuthorAgent publish flow
```
Confirm via wordpress.tool `/post/{id}` — NOT public curl (BPS firewall 403s it).
