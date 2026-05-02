# X402_DEPLOY — once-and-only-once mainnet ceremony

> *Companion to [X402.md](X402.md). The path to mainnet is testnet first (due diligence), then a single, locked deploy on each chain. This doc is the operator runbook — every step has a check, every check has a reason, the mainnet step is gated.*

## Posture

mindX has pioneered the cross-chain x402 receipt pair. Per the operator decision (2026-05-02): **TestNet for due diligence, MainNet once and once only.** The contracts are not upgradeable by design — `X402Receipt.sol` and `x402_receipt.algo.ts` are immutable post-deploy. Role-based admin (EVM `DEFAULT_ADMIN_ROLE`, AVM `admin` GlobalState) is the only mutable surface, and it should be transferred to a multisig immediately after deploy.

## Contract pair under deploy

| Chain | Source | Address policy |
|---|---|---|
| EVM | [`daio/contracts/x402/X402Receipt.sol`](../daio/contracts/x402/X402Receipt.sol) | CREATE2 via EIP-2470 SingletonFactory `0x8A791620dd6260079BF849Dc5567aDC3F2FdC318` for cross-chain identical address (recommended) **or** plain CREATE if the chain lacks the singleton |
| AVM | [`daio/contracts/algorand/x402_receipt.algo.ts`](../daio/contracts/algorand/x402_receipt.algo.ts) | App ID assigned by Algorand on creation; record post-deploy |

Deploy drivers:
- EVM: [`daio/contracts/x402/script/Deploy.s.sol`](../daio/contracts/x402/script/Deploy.s.sol) — Foundry script with `predict()`, `deployTestnet()`, `deployMainnet()`
- AVM: [`daio/contracts/algorand/x402_receipt_deploy.ts`](../daio/contracts/algorand/x402_receipt_deploy.ts) — AlgoKit-utils + algosdk driver with `predict | deploy-testnet | deploy-mainnet` sub-commands

## Pre-flight checklist (run once, BEFORE any TestNet deploy)

- [ ] `FOUNDRY_PROFILE=x402 forge test` — all 6 tests green
- [ ] `FOUNDRY_PROFILE=x402 forge build` — no errors, no warnings other than the existing `_signAs` mutability hint
- [ ] Slither pass (optional but recommended): `cd daio/contracts && slither x402/X402Receipt.sol --solc-remaps "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/"`
- [ ] PuyaTs build of `x402_receipt.algo.ts` succeeds — produces `*.arc56.json`, `*.approval.teal`, `*.clear.teal` in `daio/contracts/algorand-artifacts/X402Receipt/`
- [ ] Existing live contracts inventoried: aORC Minter app `757891101`, aORC Registry app `757891112` (TestNet), `BankonPaymentRouter` Hardhat-localhost address from [`/home/hacker/live/contracts/deployment-1337.json`](file:///home/hacker/live/contracts/deployment-1337.json) — note the deployed mainnet `BankonPaymentRouter` address when available
- [ ] Multisig address chosen for `X402_ADMIN` (EVM) and the AVM `admin` initialiser. Do **not** use an EOA on mainnet.
- [ ] `algorand_mnemonic` vault key is the deployer; the vault is unlocked
- [ ] `PRIVATE_KEY` (EVM deployer) is the deployer; **same EOA on every EVM chain** if you want CREATE2 cross-chain identical addresses
- [ ] Deployer balances funded:
  - EVM: ≥ 0.05 ETH on each target chain (override via `MIN_DEPLOYER_BALANCE_WEI`)
  - AVM: ≥ 3 ALGO (override via `MIN_DEPLOYER_MICROALGO`) — matches the `nextStep` note in [`/home/hacker/live/contracts/testnet-deploy.json`](file:///home/hacker/live/contracts/testnet-deploy.json)

## Phase T — TestNet (due diligence)

### T.1 — Predict (no broadcast)

EVM (per chain):
```bash
cd daio/contracts
FOUNDRY_PROFILE=x402 forge script x402/script/Deploy.s.sol:Deploy \
    --sig "predict()" \
    --rpc-url $BASE_SEPOLIA_RPC \
    --private-key $PRIVATE_KEY
```

Records:
- `deployer`, `deployer nonce` — both must match what you'll deploy from
- `CREATE predicted` — the address that plain `new X402Receipt(...)` will land at given the current nonce
- `CREATE2 predicted` — the address that EIP-2470 SingletonFactory + `salt` lands at; **identical across chains if you keep deployer + admin + router + salt fixed**
- `chainId` — sanity check

AVM:
```bash
cd daio/contracts/algorand
ALGORAND_NETWORK=testnet ALGORAND_DEPLOYER_MNEMONIC="<25-word>" \
    tsx x402_receipt_deploy.ts predict
```

### T.2 — Deploy on TestNet (per EVM chain + Algorand TestNet)

EVM (Base Sepolia, Polygon Amoy, etc.):
```bash
FOUNDRY_PROFILE=x402 forge script x402/script/Deploy.s.sol:Deploy \
    --sig "deployTestnet()" \
    --rpc-url $BASE_SEPOLIA_RPC \
    --private-key $PRIVATE_KEY \
    --broadcast \
    --verify  # if Etherscan/Basescan API key is set
```

The script uses the env vars:
- `X402_ADMIN` — defaults to `msg.sender`; set to your TestNet multisig address if you want to dry-run that custody on testnet
- `BANKON_PAYMENT_ROUTER` — defaults to `address(0)` (no cascade); set to the deployed router address to enable receipt forwarding

AVM:
```bash
ALGORAND_NETWORK=testnet ALGORAND_DEPLOYER_MNEMONIC="<25-word>" \
    tsx x402_receipt_deploy.ts deploy-testnet
```

Captures the output: AppID, AppAddress, TxID, explorer link.

### T.3 — Verify TestNet deploy

EVM:
- Open Etherscan/Basescan/Polygonscan for the `--verify` ed contract; confirm source matches commit
- Read `getRoleAdmin(DEFAULT_ADMIN_ROLE)` → returns `DEFAULT_ADMIN_ROLE` (sentinel)
- Read `hasRole(DEFAULT_ADMIN_ROLE, $X402_ADMIN)` → true
- Read `router()` → matches `$BANKON_PAYMENT_ROUTER` or `address(0)`

AVM (via vibekit-mcp or `goal app read`):
- `mcp__vibekit-mcp__indexer_lookup_application` → AppID confirms approval-program hash matches the local artifact hash
- `mcp__vibekit-mcp__read_global_state` → `admin` matches deployer (or whatever was passed to `initialize`)
- `mcp__vibekit-mcp__read_global_state` → `totalReceipts` is `0`

### T.4 — End-to-end TestNet smoke test

Compose a sample receipt off-chain, sign with the buyer wallet, submit on each chain, confirm idempotency rejects the duplicate.

EVM:
```bash
# 1. Build the canonical hash
cast call $X402_RECEIPT_ADDR \
    "canonicalReceiptHash(address,address,address,uint256,bytes32,bytes32)(bytes32)" \
    $PAYER $PAYEE $USDC 2000000 $RESOURCE_HASH $NONCE \
    --rpc-url $BASE_SEPOLIA_RPC

# 2. Sign with personal_sign over the returned hash
SIG=$(cast wallet sign $RECEIPT_HASH --private-key $BUYER_PK)

# 3. Submit
cast send $X402_RECEIPT_ADDR \
    "recordX402Receipt(bytes32,address,address,address,uint256,bytes32,bytes32,bytes)" \
    $RECEIPT_HASH $PAYER $PAYEE $USDC 2000000 $RESOURCE_HASH $NONCE $SIG \
    --rpc-url $BASE_SEPOLIA_RPC \
    --private-key $RELAYER_PK

# 4. Confirm event
cast logs --from-block latest --address $X402_RECEIPT_ADDR \
    "X402ReceiptRecorded(bytes32,bytes32,address,address,address,uint256,uint64,uint64)" \
    --rpc-url $BASE_SEPOLIA_RPC

# 5. Re-submit — must revert with ReceiptAlreadyRecorded
cast send $X402_RECEIPT_ADDR \
    "recordX402Receipt(...)" ... # same args
# Expect: revert ReceiptAlreadyRecorded(0x...)
```

AVM (via algosdk in a small driver — use `tools/x402_avm_client.py` once it points at the deployed AppID):
```python
import asyncio
from tools.x402_avm_client import X402AvmClient

async def main():
    c = X402AvmClient(facilitator_url="https://x402.goplausible.xyz")  # or self-hosted
    # First call → expect 200, second identical call → expect upstream 402-still or app-side revert
    r1 = await c.fetch("GET", "https://x402.goplausible.xyz/examples/weather")
    print(r1)

asyncio.run(main())
```

Confirm in the AVM indexer:
- `mcp__vibekit-mcp__indexer_lookup_application_logs` → exactly one log row for the receiptHash
- `mcp__vibekit-mcp__read_box` (using the `xr_<receiptHash>` key) → record present, fields match what was sent

### T.5 — Cross-chain join check

Submit two receipts with the same logical fields (`payer`, `payee`, `asset`-equivalent, `amount`, `resourceHash`, `nonce`) — one on EVM TestNet, one on AVM TestNet. Confirm the unified indexer parses both events to the same `(payer, payee, asset, amount, resourceHash)` tuple. The two `receiptHash` values will differ (different canonical encodings per chain), but the **payload tuple is identical** — that's the cross-chain join key.

### T.6 — TestNet sign-off

Operator sign-off in writing (commit message, ledger note, or boardroom thread):
- All T.x checks green
- TestNet AppID + EVM addresses recorded in `/home/hacker/live/contracts/x402-testnet-deploy.json`
- `docs/X402.md` "Live deployment artifacts" table updated
- 24-hour soak — leave the contracts running, watch for any unsolicited interactions

## Phase M — MainNet (single shot, per chain)

> **From here on, every TX costs real funds and is irreversible.** No autonomous execution — every step is a deliberate operator action.

### M.1 — Lock the parameters

Pick exactly:
- `X402_ADMIN` = mainnet multisig (Safe on EVM; multisig descriptor on AVM)
- `BANKON_PAYMENT_ROUTER` = the existing mainnet `BankonPaymentRouter` address (or `address(0)` if cascade is deferred)
- `salt` (EVM CREATE2) — recommend `keccak256("x402-receipt-mainnet-v1" || admin)` for cross-chain consistency
- Algorand mnemonic for the deployer — funded with ≥ 3 ALGO

Commit these to a `mainnet-deploy.env` file kept ONLY in BANKON Vault; never disk.

### M.2 — Final predict (no broadcast)

EVM (per target mainnet chain):
```bash
FOUNDRY_PROFILE=x402 forge script x402/script/Deploy.s.sol:Deploy \
    --sig "predict()" \
    --rpc-url $BASE_MAINNET_RPC \
    --private-key $PRIVATE_KEY
```

Confirm `chainId` matches Base mainnet (8453), Polygon (137), Ethereum (1), Arbitrum (42161), or Optimism (10). Anything else aborts in `_assertMainnetChainAllowed`.

AVM:
```bash
ALGORAND_NETWORK=mainnet ALGORAND_DEPLOYER_MNEMONIC="<25-word>" \
    tsx x402_receipt_deploy.ts predict
```

### M.3 — Single deploy per chain

EVM:
```bash
X402_DEPLOY_MAINNET=true \
X402_ADMIN=0x<safe_address> \
BANKON_PAYMENT_ROUTER=0x<router_address> \
FOUNDRY_PROFILE=x402 forge script x402/script/Deploy.s.sol:Deploy \
    --sig "deployMainnet()" \
    --rpc-url $BASE_MAINNET_RPC \
    --private-key $PRIVATE_KEY \
    --broadcast \
    --verify
```

If the env gate is missing, the script reverts with `MainnetGateClosed()` before any RPC call. If the chain ID is unexpected, it reverts with `WrongChainForMainnet`. If the deployer is underfunded, `DeployerUnderfunded`.

AVM:
```bash
X402_DEPLOY_MAINNET=true \
ALGORAND_NETWORK=mainnet \
ALGORAND_DEPLOYER_MNEMONIC="<25-word>" \
    tsx x402_receipt_deploy.ts deploy-mainnet
```

### M.4 — Post-deploy wiring

EVM (one TX, signed by the existing `BankonPaymentRouter` admin):
```bash
# Grant REGISTRAR_ROLE on the router to the new X402Receipt so cascades land.
cast send $BANKON_PAYMENT_ROUTER \
    "grantRole(bytes32,address)" \
    $(cast keccak "REGISTRAR_ROLE") \
    $X402_RECEIPT_DEPLOYED_ADDR \
    --rpc-url $BASE_MAINNET_RPC \
    --private-key $ROUTER_ADMIN_PK
```

AVM:
- Fund the new App's `AppAddress` with 1 ALGO (minimum balance for box writes)
- Opt the recipient address into the USDC ASA on MainNet (ASA `31566704`)
- Snapshot `globalState` and the artifact hash to `/home/hacker/live/contracts/x402-mainnet-deploy.json`

### M.5 — Documentation update (within 24 hours)

- [ ] [`docs/X402.md`](X402.md) "Live deployment artifacts" table updated with mainnet addresses
- [ ] [`docs/BOARDROOM.md`](BOARDROOM.md), [`docs/lighthouse.md`](lighthouse.md), [`docs/DAIO.md`](DAIO.md) — replace TestNet references where mainnet now applies
- [ ] [`mindx_backend_service/agenticplace_routes.py`](../mindx_backend_service/agenticplace_routes.py) — set the `algorand_recipient_address` and `algorand_usdc_asa_id` defaults to the mainnet values
- [ ] Tweet / changelog entry: "X402Receipt deployed on Base + Algorand. EVM @ 0x…, AVM AppID …. First proof of x402 from contracts."
- [ ] Boardroom session logged via `daio/governance/boardroom.py`: `x402-mainnet-deploy-2026-MM-DD.json` capturing the deploy hash, the admin multisig, the router cascade status

### M.6 — Lock

After M.5 the contract pair is **locked**. Any future change to the receipt format requires a v2 contract pair with new addresses; this pair stays as the canonical `x402-receipt-v1` evidence forever.

## Recovery / abort paths

- **TX dropped before mainnet inclusion**: re-broadcast with the same nonce. `forge script` rebroadcast handles this; `algosdk` waits for confirmation, which surfaces the failure cleanly.
- **TX confirms but at unexpected address (CREATE-based, nonce changed)**: the deploy is still valid; update docs to match. The X402Receipt address is whatever was emitted — not what was predicted.
- **Wrong `X402_ADMIN`**: the constructor immutably grants `DEFAULT_ADMIN_ROLE` to that address. **There is no recovery.** Do another deploy at a fresh address (still "once" per the canonical address); abandon the wrong one. The wasted gas is the cost of the lesson.
- **AVM AppID conflict**: AppIDs are assigned by Algorand sequentially; conflict is impossible. If the deploy reverts mid-way (out-of-balance, network drop), retry — no on-chain state was committed.

## Auditing the deploy after the fact

For both chains, the deploy artefact is a transaction. Anyone can verify:
- EVM: `cast tx <txhash> --rpc-url $RPC` shows `to: 0x0` (deploy), `from: deployer`, `contractAddress: <addr>`, and the `vm.broadcast` traces match the script
- AVM: `mcp__vibekit-mcp__indexer_lookup_transaction` on the deploy txID shows the `appl-create` entry; the resulting AppID's program hash matches the SHA512/256 of the local `*.approval.teal`

Both are reproducible: anyone with the same source tree commit can recompute the bytecode hash and confirm.

## See also

- [X402.md](X402.md) — canonical x402 doc, Lead, Live deployment artifacts
- [BANKON_VAULT.md](BANKON_VAULT.md) — credential custody for `algorand_mnemonic`, mainnet-deploy.env
- [BANKON_VAULT_HANDOFF.md](BANKON_VAULT_HANDOFF.md) — operator ceremony for mainnet-tier secret access
- [DAIO.md](DAIO.md) — broader on-chain governance context; `BankonPaymentRouter` lives in `daio/contracts/ens/v1/`

---

*Once and once only.*
