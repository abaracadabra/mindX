# BANKON Vault — operator runbook for the airgapped custody handoff

## What this is

mindX's BANKON Vault holds every API key and agent private key the running service depends on. By default it lives in **machine custody** — a 64-byte file `.master.key` on the same box as the service. This runbook walks through transferring custody to a **human overseer** (you) using a wallet whose private key never touches the connected machine.

The cryptography is implemented in `mindx_backend_service/bankon_vault/{vault,overseer}.py` and is overseer-agnostic: the same flow described here will move custody from human → DAIO when a Governor contract is live (Stage 2). The end of this doc explains that path.

## Threat model

You're protecting the vault from these attackers:

- **VPS root compromise.** Today, root on the VPS reads `.master.key` and decrypts everything. After handoff, root can read `entries.json` ciphertext and `.salt` and `.overseer_proof.json` — but cannot rotate without your wallet's private key.
- **Service code path leak.** The vault is unlocked in-process for ~50 ms at startup. A bug that dumps `_vault_key` would still lose the vault. Handoff doesn't fix this; it stops the long-tail risk where `.master.key` lives on disk indefinitely.
- **Host filesystem snapshot.** Once `.master.key` is deleted, snapshots of the disk are no longer sufficient to compromise the vault. They are sufficient if a snapshot exists from before the handoff — wipe old backups.
- **Connected machine compromise during ceremony.** Mitigated by signing on the airgap. The connected machine sees only the public address and the signature — not the private key.

You're **not** protected from:

- Phishing attacks that get you to sign a malicious challenge. Read the challenge text before signing — it includes the vault fingerprint and the address it commits to.
- Loss of your wallet's seed phrase. Recovery section below.
- Loss of the proof file (`.overseer_proof.json`). Recovery section below — RFC 6979 deterministic ECDSA means re-signing the same challenge produces the same signature.

## Pre-flight (connected machine)

```bash
cd /home/hacker/mindX
.mindx_env/bin/python manage_credentials.py list  # sanity check vault is reachable
.mindx_env/bin/python manage_custody.py preflight
```

Confirm:
- `vault_dir` resolves to `mindx_backend_service/vault_bankon/`
- `.master.key` is present (you're in machine custody — expected pre-handoff)
- `.human_overseer_active` is **absent** (sentinel not yet written)
- `MINDX_VAULT_ALLOW_OVERSEER_ROTATION` is unset (you'll set it in step 4)

Also: deploy the `/admin/vault/{keys,migrate}` auth-gate patches before this ceremony if running against production. Until those land, attackers can enumerate your private-key IDs over HTTP.

## Step 1 — Generate the challenge (connected)

```bash
.mindx_env/bin/python manage_custody.py challenge --address 0xYOUR_OVERSEER
```

Writes `./handoff_challenge.txt` containing six lines binding:
- The vault fingerprint (`sha256(salt || entries.json[:4096])[:16]`).
- The overseer address you're claiming.
- An ISO-8601 timestamp.
- A 32-character random nonce.
- A custody acceptance statement.

**Read it.** Anyone who tricks you into signing a different challenge gets your vault.

Optional — encode for camera transfer:

```bash
qrencode -o handoff_challenge.qr.png -r handoff_challenge.txt
```

(`qrencode` is in most distros; if not, copy the text via USB or paper. Treating challenge text as public is fine — it's not secret.)

## Step 2 — Move challenge to airgap

Use one of:

- **Camera + QR.** Display `handoff_challenge.qr.png` on a phone or laptop, scan from the airgap with `zbarcam` or any QR reader. Most paranoid path.
- **Read-only USB.** Mount one-way; do not write anything from the airgap back to the same stick. Reformat after.
- **Paper.** The challenge fits on one printed page. Type it back in.

The challenge is **not** secret — it's just a bound message. Confidentiality of the transfer doesn't matter; integrity does. (Hash the file on both sides if you're paranoid.)

## Step 3 — Sign on the airgap

The airgapped machine needs:

- Python 3.9+
- `pip install eth-account>=0.13`
- Optional: `pip install mnemonic` for `--mnemonic-file`, `pip install 'qrcode[pil]' pillow` for `--out-qr`
- `scripts/vault/airgap_sign.py` from this repo (single file, no mindX imports)

Pick one signer mode:

```bash
# (A) Hex private key from memorized prompt (no shell history)
python airgap_sign.py \
    --challenge-file handoff_challenge.txt \
    --privkey-prompt \
    --out handoff_sig.json \
    --out-qr handoff_sig.qr.png

# (B) BIP39 mnemonic + standard Ethereum derivation
python airgap_sign.py \
    --challenge-file handoff_challenge.txt \
    --mnemonic-file ~/.airgap/seed.txt \
    --derivation-path "m/44'/60'/0'/0/0" \
    --out handoff_sig.json

# (C) Encrypted keystore JSON (geth/MyCrypto V3) with password prompt
python airgap_sign.py \
    --challenge-file handoff_challenge.txt \
    --keystore ~/.airgap/keystore-utc.json \
    --out handoff_sig.json

# (D) External signer — Ledger/Trezor: produce the sig elsewhere, then
#     verify-and-package with airgap_sign.py:
python airgap_sign.py \
    --challenge-file handoff_challenge.txt \
    --paste-sig 0xabc... --address 0xYOUR_OVERSEER \
    --out handoff_sig.json
```

`airgap_sign.py` post-verifies the signature recovers to the expected EOA before writing anything. It refuses to emit if the signature is wrong shape (must be 65 bytes) or fails recovery.

Output JSON shape (matches what the rotation consumes):

```json
{
  "address": "0xYOUR_OVERSEER",
  "signature": "0x<130 hex chars = 65 bytes>",
  "message": "<the original challenge text, byte-for-byte>"
}
```

## Step 4 — Move signature back to connected machine

Either return the QR PNG (`handoff_sig.qr.png`) or the JSON file. The signature is **not** secret either — it can only be replayed against this exact challenge text on this exact vault, and the vault will have already used it.

## Step 5 — Dry-run the rotation (connected)

```bash
export MINDX_VAULT_ALLOW_OVERSEER_ROTATION=1
SIG=$(jq -r .signature handoff_sig.json)
ADDR=$(jq -r .address handoff_sig.json)

.mindx_env/bin/python manage_custody.py dry-run \
    --address "$ADDR" --signature "$SIG"
```

Expected output:

```json
{
  "status": "dry_run_ok",
  "entries": <N>,
  "new_fingerprint": "human:<last 8 of address>",
  ...
}
```

The dry-run writes:

- `entries.json.candidate` — re-encrypted under the new key (does **not** replace the live `entries.json`).
- `.rotation.ok` — sha256 of the candidate, must be <300 s old at commit.

It also takes a snapshot of the entire vault directory under `/tmp/mindx-vault-snapshot-*`. If anything goes wrong before commit, restore from there.

If `dry_run_ok` doesn't print, **stop**. Read the error. Re-sign the challenge if the signature is malformed. Do not proceed to commit.

## Step 6 — Commit (connected, irreversible-ish)

```bash
.mindx_env/bin/python manage_custody.py commit \
    --address "$ADDR" --signature "$SIG" --i-am-sure
```

What happens, in order (vault.py:516-633):

1. Re-runs the dry-run to refresh `.rotation.ok` and `entries.json.candidate`.
2. POSIX-atomic `os.replace(candidate, entries.json)`.
3. fsync's the file and the directory.
4. Writes `.overseer_proof.json` (so future restarts can re-unlock without re-signing).
5. Writes the sentinel `.human_overseer_active` (blocks any future machine-key regeneration).
6. fsync's the directory.
7. Overwrites `.master.key` with `\x00` × 64, then unlinks it.
8. Swaps in-memory state to the new key.
9. Appends one row to `data/governance/overseer_history.jsonl`.
10. Deletes `.rotation.ok`.

After this:
- `unlock_with_key_file()` raises `RuntimeError` if anything ever tries to fall back to machine custody (vault.py:191-197).
- Service restarts will load the proof file via `load_human_from_proof()` and call `unlock_with_overseer()` automatically (manage_custody.py:71-79).

## Step 7 — Lock down + smoke-test (connected)

```bash
.mindx_env/bin/python manage_custody.py lock-routes --address "$ADDR"
.mindx_env/bin/python manage_custody.py smoke-test
```

`lock-routes` adds your overseer address to `security.admin_addresses` so the existing `require_admin_access` gate now considers you admin.

`smoke-test` confirms: anonymous `/vault/credentials/list` is rejected, sentinel present, master.key absent, audit log non-empty.

Restart the service:

```bash
sudo systemctl restart mindx     # if on the VPS
# or, locally:
./mindX.sh
```

Expected: clean startup, `os.environ` populated with the 21 provider keys (the proof-file re-unlock path runs automatically).

```bash
unset MINDX_VAULT_ALLOW_OVERSEER_ROTATION  # don't leave the rotation flag set
```

## Recovery — lost proof file

If `.overseer_proof.json` is deleted, the service can't auto-unlock. Two paths to recover, neither destructive:

1. **Re-sign.** Because EIP-191 personal_sign uses RFC 6979 deterministic ECDSA, the same wallet signing the same challenge text produces the same 65-byte signature. Re-run Step 3 with the original `handoff_challenge.txt` (find it in your secure storage), repackage the JSON, and pass it to `manage_custody.py dry-run` — the vault unlocks without writing a new proof, then you can drop the JSON back as `.overseer_proof.json` manually.

2. **Snapshot restore.** Every dry-run snapshots the vault under `/tmp/mindx-vault-snapshot-*`. If you have a snapshot from immediately after the original commit, copy the proof file out of there.

If you've also lost the original challenge text, you can regenerate it deterministically only if the vault salt and entries are unchanged — `manage_custody.py challenge --address 0xYOUR` produces a new challenge with a fresh nonce and timestamp, so re-signing that yields a different signature. That's fine — the vault rotates the proof on the next dry-run + commit. As long as you control the same wallet, the vault is recoverable.

## Recovery — lost wallet seed

You can't. The vault key is derived from the EIP-191 signature; the signature is derived from the wallet seed. Lose the seed, lose the vault.

Mitigations before you need them:
- Store the seed phrase in two physically separate locations (paper + metal stamp, etc.).
- Use a hardware wallet on the airgap so the seed never touches a screen.
- After this ceremony, repeat the same ceremony with a **second** wallet to a hot-spare overseer, and run the equivalent of `rotate_overseer(HumanOverseer(spare_addr, ...))`. Two valid overseer addresses in your control = redundancy.

## Stage 2 — DAIO custody

`overseer.py:200-244` already declares `DAIOOverseer(registry, threshold, chain_id)` as a stub. When the Governor contract is live:

1. Replace the IKM source. Where `HumanOverseer.produce_raw_key` reads a 65-byte signature, `DAIOOverseer.produce_raw_key` will read an on-chain attestation digest from the executed proposal and HKDF it under `DAIO_INFO_PREFIX + registry + chain_id`.
2. `verify_evidence` will eth_call the Governor: `proposalState(id) == Executed` AND `hashProposal` matches the digest in evidence AND the weighted vote ≥ threshold.
3. Run the same ceremony — `manage_custody.py` is overseer-agnostic. Replace `--address` with the proposal id; the script will need a thin extension to construct `DAIOOverseer` instead of `HumanOverseer`. Same `vault.rotate_overseer(...)` call. Same `.salt`. Same audit log row, just `to_kind == "daio"`.

The two-stage HKDF in `overseer.py` (per-overseer `_INFO_PREFIX` for IKM, then unified `b"bankon-vault-master-key"` for the vault key) is deliberate — both human and DAIO end up at the same 32-byte vault key from a different root of trust, with no `entries.json` re-encryption beyond what `rotate_overseer` already does.

When the time comes you can run Human → DAIO with the same atomic-swap two-phase commit, and the audit log records the transition. Or revert: DAIO → Human if the Governor needs to be unwound.

## Reference

- `mindx_backend_service/bankon_vault/vault.py` — core vault, `rotate_overseer`.
- `mindx_backend_service/bankon_vault/overseer.py` — `HumanOverseer`, `DAIOOverseer`, `load_human_from_proof`.
- `manage_custody.py` — connected-side CLI: preflight, challenge, dry-run, commit, transfer-agents, update-agent-map, lock-routes, smoke-test.
- `scripts/vault/airgap_sign.py` — airgap-side signer.
- `tests/bankon_vault/test_rotate_overseer.py` — rotation contract test (`make test-vault`).
- `data/governance/overseer_history.jsonl` — append-only audit log.
- `/home/hacker/.claude/plans/glimmering-growing-scroll.md` — original overseer design plan.
- `/home/hacker/.claude/plans/jolly-baking-wilkinson.md` — full vault audit including the security findings remediated alongside this toolkit.
