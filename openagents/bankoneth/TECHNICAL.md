# TECHNICAL — bankoneth client-side prototype stack

> **⚠ PROTOTYPE — message to the next agent (Claude).** This document describes a
> **working prototype**: `pay2play/` (Solidity rails, 15/15 `forge test`),
> `walletcreator/` (Python reference vault + wallet minting, verified), and
> `deployer/` (client-side DEPLOY/LAUNCH/RETURN dApp). It is **not audited** and not
> production. Keep the modular folder separation (see
> [`docs/DELIVERY_AND_MODULARITY.md`](docs/DELIVERY_AND_MODULARITY.md)). Built by
> Claude, for Claude.

© BANKON — all rights preserved. Frontend and vault are always open source.

---

## 1. Summary

The stack turns **payment** into **identity-bound privilege**, and lets a participant
**create wallets** and **deploy contracts** entirely from their own device.

```
  pay → entitlement → admission        |   wallet → vault          |   deploy
  ───────────────────────────────      |   ──────────────────      |   ──────
  pay2play (BANKONPaymentRouter)        |   walletcreator           |   deployer
    → BankonEntitlement (persistence)   |     (bankon_vault +       |     (index.html +
    → Pay2PlayGate (signature admit)    |      wallet_creator)      |      index.xml +
    → Pay2PlayArcSettlement (USDC/ARC)  |                           |      deployer.js)
```

Three guarantees run through all of it:
- **Identity is a signature** — ownership of the private key is the credential.
- **Fair & nominal fee** — the fee lives in the contracts, hard-capped.
- **Client-side & open source** — anything that touches a private key (the vault, the
  frontend) is auditable and runs on the participant's device; BANKON never holds keys.

---

## 2. pay2play — the rails (Solidity, Foundry, OZ v5, solc 0.8.24 / Cancun / via_ir)

Self-contained sub-module; reuses `../lib`. Four concerns, one contract each, plus the
gate and the ARC settlement.

### 2.1 BankonServiceRegistry
The **BANKON-as-a-Service catalogue**. `Service { beneficiary, asset, price, period,
tier, active, name }` keyed by `serviceId` (e.g. `keccak256("identity.register")`).
`SERVICE_ADMIN_ROLE` writes; everyone reads. Adding a service is adding a row.

### 2.2 BankonEntitlement
The **identity ledger** (persistence.state): `user → service → expiry` (uint64,
`type(uint64).max` = permanent) and a monotonic `tier`. Only `GRANTER_ROLE` (the router
and the ARC settlement) may `grant`. `hasAccess` is the read every gated surface checks.

### 2.3 BANKONPaymentRouter
The **spine**. `play / playFor / playWithSig`:
- reads the service, charges `price` (native via `msg.value`, or ERC-20 via
  `safeTransferFrom`),
- takes `feeBps` (default **250 = 2.5%**, hard cap `MAX_FEE_BPS = 1000`) to
  `feeRecipient`, forwards the net to `beneficiary` (the router never custodies funds),
- grants the entitlement for `period` (or permanent).
- `playWithSig` verifies an EIP-712 `Play(serviceId,user,nonce)` signature so a sponsor
  can pay while the entitlement binds to the **signer** — proof of private-key ownership
  = identity. `SignatureChecker` ⇒ EOA (ECDSA) **and** ERC-1271 smart accounts.
`ReentrancyGuard` on the charge path.

### 2.4 Pay2PlayArcSettlement — ARC USDC x402 rail
For the most off-chain path: the customer pays **USDC on Circle's ARC chain** through an
x402 facilitator; the facilitator returns an EIP-712 `ArcReceipt { serviceId, payer,
asset, amount, srcChainId, nonce, deadline }`. `settle(...)` verifies and grants the
entitlement **without moving tokens** (settled on ARC). Defences, in order: facilitator
**allowlist**, **deadline**, ARC **chainId + USDC asset** match, **monotonic
per-facilitator nonce** (replay 1), **spent-once receipt digest** (replay 2), **amount ≥
price**, then the facilitator signature (EOA/1271). `ReentrancyGuard` because the
signature check may call into an ERC-1271 facilitator. Same shape as the Algorand
x402-avm rail (`contracts/BankonX402Attestor.sol`).

### 2.5 Pay2PlayGate — the gate to a service
Turns an entitlement into **admission** to an API call or a DeltaVerse-style privileged
room. A `Room { service, proofOracle?, nft? (ERC-721/1155 + minBalance), active, name }`.
`admit / admitWithSig` checks: the entitlement (`hasAccess`), an optional **proof.oracle**
(`IProofOracle.proven` — "world" connection: personhood, presence, NFT proof, zk), and a
modular-NFT balance gate. On success it emits `Admitted` — the signal an **off-chain
signature event-listener layer** watches to open the session. `admitWithSig` binds to the
EIP-712 `Connect(roomId,user,nonce)` signer. No tokens move in the gate.

---

## 3. walletcreator — client-side vault + wallet minting (Python reference)

The Python here is the **auditable reference implementation**; production runs the same
logic on the client (Tauri/web).

### 3.1 bankon_vault.py — the always-open-source vault
Crypto: `passphrase | participant-signature ──HKDF-SHA512(salt, "…master-key")──▶ master
key (RAM only)`; per entry `HKDF-SHA512(salt, "…entry:<id>") ──▶ entry key`;
`AES-256-GCM(nonce=12B, aad=<id>)`. A reserved `__check__` entry detects a wrong key
without leaking. On-disk: `{version, salt, check, entries{id:{nonce,ct,meta}}}`, `0600`.
- `from_participant_signature(path, sig)` binds the vault to the **participant's private
  key**: they sign `BINDING_MESSAGE`; that signature is the only KDF input ⇒ only they
  decrypt it, never BANKON or a host.
- `encrypt_folder / decrypt_folder` seal a whole directory (tar+gzip) into the vault.
- `network_connected() / airgap_advisory()` drive the **airgap-first** gate: if online on
  first use, the client must ask "network is connected, do you want to proceed?".

### 3.2 wallet_creator.py — allchain minting
`create_allchain_wallet()` mints one EVM keypair (valid on every EVM chain on
allchain.html) + an Algorand ed25519 keypair, vaults both, and returns a
`{chain: address}` map. `sign_message` = EIP-191 personal_sign (proof of identity for
`playWithSig`). Anvil dev keys for local testing. Vault ids: `wallet:<kind>:<address>`.

---

## 4. deployer — client-side DEPLOY / LAUNCH / RETURN dApp

Framework-free; only the wallet's EIP-1193 provider in the trust path.
- **index.html** — protective layer (nothing deploys until a wallet connects); identity =
  public key (optional bankon.eth).
- **index.xml** — the **solution**: `<contract>` entries point at Foundry artifacts
  (exact compiled bytecode/ABI), declare constructor arg sources (`from="wallet"`, a
  literal, `from="deployed:<id>"` for dependent deploys), a `value` kind, and the pay2play
  `privilege` conferred.
- **deployer.js** — **DEPLOY** arms (resolve args, fetch bytecode, ABI-encode static
  types, build tx — no cost); **LAUNCH** fires from value (`signature` to prove identity,
  or `token` native value) then `eth_sendTransaction`; **RETURN** polls
  `eth_getTransactionReceipt` and shows hash/status/deployed address. Deployed addresses
  feed `from="deployed:<id>"` so a session can deploy registry → entitlement → ARC
  settlement in order.

---

## 5. End-to-end control flow

1. **Create** (client): `airgap_advisory()` → create vault bound to participant key →
   `create_allchain_wallet()` → keys sealed client-side.
2. **Pay** (chain): `BANKONPaymentRouter.play*` (or `Pay2PlayArcSettlement.settle` for
   USDC/ARC) → fee split → `BankonEntitlement.grant`.
3. **Admit** (chain+off-chain): `Pay2PlayGate.admitWithSig` checks entitlement + proof +
   NFT → emits `Admitted` → off-chain listener opens the API/room.
4. **Deploy** (client): DEPLOY arms → LAUNCH (signature/token) → RETURN shows the tx.

---

## 6. Security model & trust boundaries

- **Keys never leave the client.** The vault is open source and key-bound; BANKON cannot
  decrypt it.
- **Signatures, not passwords.** EIP-712 / EIP-191; EOA + ERC-1271.
- **x402/ARC trust is the facilitator key** — allowlisted, multisig-recommended, double
  replay-guarded. Same as the audited Algorand attestor's model.
- **The router never custodies** — it forwards net to the beneficiary in the same call.
- **Fee is capped** in-contract (≤ 10%).
- **Admin roles** should be multisigs in production (`DEFAULT_ADMIN_ROLE`,
  `FACILITATOR_ADMIN_ROLE`, `SERVICE_ADMIN_ROLE`, `ROOM_ADMIN_ROLE`, `GRANTER_ROLE`).

---

## 7. Testing

- `pay2play`: `forge test` — **15/15** (router native/ERC-20/sig + fee cap + inactive;
  ARC settle/replay/nonce/chain/asset/underpaid/unknown-facilitator; gate
  entitlement/nft/proof/admitWithSig/entitlement-only).
- `walletcreator`: Python smoke — vault round-trip, wrong-key rejection, participant-key
  binding (only same wallet reopens), folder encrypt/decrypt, allchain mint, signature
  recovery.
- `deployer`: JS parses; `index.xml` well-formed; referenced artifacts carry real
  bytecode (deployable against Anvil).

---

## 8. Limitations (read before extending)

**Maturity**
- Prototype; **no audit, no formal verification, no testnet rehearsal** of pay2play/ARC.
- Admin keys are single EOAs in the deploy script — make them multisigs.

**pay2play contracts**
- `Pay2PlayArcSettlement` trusts the facilitator's *attestation* of an ARC settlement;
  it does **not** itself verify the USDC transfer on ARC (that is the facilitator's job,
  exactly like the Algorand attestor). Compromise of a facilitator key ⇒ free grants
  until the key is removed. Use a multisig facilitator + tight allowlist.
- `arcChainId` is a placeholder (Circle ARC ids not finalised here) — set via
  `setArcConfig` before use.
- The fee path assumes a standard ERC-20; **fee-on-transfer / rebasing tokens** will
  mis-split (net/fee computed on nominal `price`). Whitelist assets.
- `BankonEntitlement.tier` is monotonic (never decreases) and there is **no revocation**
  of an active entitlement — add a revoke path if you need clawback.
- No on-chain coupling between the gate's `Admitted` event and a session — the **off-chain
  listener is trusted** to honour it; a malicious server can ignore admission.

**walletcreator**
- The **Python is a reference**, not the production client. Real key generation must
  happen in the Tauri/web client; running it server-side would defeat the non-custodial
  model.
- `network_connected()` is best-effort (one TCP probe); not a substitute for a truly
  airgapped device.
- Only EVM (shared key) + Algorand (ed25519) are minted; **Cosmos/CosmWasm and other
  non-EVM kinds are not yet derived**.
- Vault file is single-device; no multi-device sync / social recovery / Shamir split yet.

**deployer**
- Constructor ABI encoder is **static types only** (address, uint*, bool, bytes32) — no
  string/bytes/arrays/tuples.
- `token` value means **native** value on the deploy tx; **ERC-20 approve+pay** and the
  full x402/ARC payment-then-deploy path are not wired in yet (pairs with pay2play).
- `bankon.eth` reverse resolution is a **hook** (address is the identity by default);
  kept out of the trust path so the deployer has no keccak/ENS dependency.
- Reads Foundry artifacts at a relative path — **`forge build` in `../pay2play` first**,
  and serve the folder so `../pay2play/out/` is reachable (`out/` is gitignored).
- No gas estimation UI, no tx-cancel/replace, no multi-chain switching helper.

**Not yet built**
- The Tauri shell and the `packages/parsec-view` web client that host this flow with
  on-device key binding.
- ERC-20 / x402 payment wired through the deployer's LAUNCH.
- A unified cross-chain receipt indexer joining EVM + ARC + Algorand by receipt hash.
