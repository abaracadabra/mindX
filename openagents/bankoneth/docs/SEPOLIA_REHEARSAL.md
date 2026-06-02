# bankoneth — Sepolia Rehearsal Runbook

Operator checklist for end-to-end rehearsal of the bankoneth Ethereum
stack on Sepolia **before** the mainnet deploy decision. This runbook
complements [`DEPLOYMENT.md`](DEPLOYMENT.md) (the mainnet recipe) and
[`ADDR_REFERENCE.md`](ADDR_REFERENCE.md) (the canonical address
registry). Run every step in order; do not skip the smoke claim.

Tested-against: `forge` ≥ 1.0, `cast` ≥ 1.0, Foundry profile `default`.
Reference test coverage: `forge coverage --ir-minimum --report summary`
should show ≥95% line on the 4 ENS contracts before invoking this
runbook.

> Outcome: a fully-verified bankoneth deployment on Sepolia with a
> throwaway `.bankon.eth` subname end-to-end claimable via the CLI,
> ready for the mainnet go/no-go conversation.

---

## 0 — Local pre-flight

```bash
cd /home/hacker/mindX/openagents/bankoneth
forge build                              # clean compile
forge test                               # 121/121 expected
forge coverage --ir-minimum --report summary \
  | grep -E 'contracts/(BankonSubnameRegistrar|BankonEthRegistrar|BankonSubnameResolver|BankonDomainHosting)\.sol'
# Each row should show ≥95% line coverage. If not — stop and add tests
# before touching Sepolia.
```

Verify the address-drift guard works on the bankoneth side without
needing RPC:

```bash
MAINNET_RPC=https://eth.llamarpc.com forge test \
  --match-path 'test/fork/*' --match-contract AddressDriftTest -vv
# Expect 4/4 passing.
```

---

## 1 — Environment + addresses

Source from [`ADDR_REFERENCE.md`](ADDR_REFERENCE.md) and from
[`docs.ens.domains/learn/deployments`](https://docs.ens.domains/learn/deployments).
The ENS docs page lists Sepolia and mainnet side by side; mistake one
for the other and the deploy bricks.

```bash
# ── Identity ────────────────────────────────────────────────────────
export DEPLOYER_PK=0x...                            # rehearsal-only EOA
export TREASURY_ADDR=0x...                          # Sepolia Safe

# ── RPC + verification ──────────────────────────────────────────────
export SEPOLIA_RPC=https://ethereum-sepolia-rpc.publicnode.com
export ETHERSCAN_API_KEY=...                        # https://etherscan.io/myapikey

# ── Sepolia ENS canonical (≠ mainnet) ───────────────────────────────
export NAME_WRAPPER_ADDR=0x0635513f179D50A207757E05759CbD106d7dFcE8
export ETH_REGISTRAR_CONTROLLER=0xfb3cE5D01e0f33f41DbB39035dB9745962F1f968

# ── bankoneth-side fixtures ─────────────────────────────────────────
export BANKON_ETH_NODE=$(cast namehash bankon.eth)
export WEBHOOK_URL=https://staging.agenticplace.pythai.net/api/listings
export ALLOW_TESTNET=true                           # bypass mainnet-addr guard
```

Pre-flight:

```bash
# 1. DEPLOYER has Sepolia ETH (need ≥ 0.3 ETH for the 12-contract deploy)
cast balance --rpc-url $SEPOLIA_RPC $(cast wallet address --private-key $DEPLOYER_PK)

# 2. bankon.eth exists on Sepolia and is wrapped to TREASURY_ADDR
cast call --rpc-url $SEPOLIA_RPC $NAME_WRAPPER_ADDR \
  "ownerOf(uint256)(address)" $(cast --to-uint256 $BANKON_ETH_NODE)
# Expect: TREASURY_ADDR

# 3. CANNOT_UNWRAP burned on bankon.eth (parent-lock requirement)
cast call --rpc-url $SEPOLIA_RPC $NAME_WRAPPER_ADDR \
  "getData(uint256)(address,uint32,uint64)" $(cast --to-uint256 $BANKON_ETH_NODE)
# Expect: (TREASURY_ADDR, fuses-includes-bit-0 = 1, expiry > now)
```

If `CANNOT_UNWRAP` is not burned, do that first via
[`app.ens.domains`](https://app.ens.domains) (Permissions tab) before
proceeding.

---

## 2 — Deploy the 12 Ethereum contracts

```bash
forge script script/DeployEthereum.s.sol \
  --rpc-url $SEPOLIA_RPC \
  --broadcast \
  --verify \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  -vvv
```

Expected: 12 contract creations, ~$2-3 worth of Sepolia ETH consumed,
verification attempted in-band. `--verify` may fail on transient
Etherscan flakes; Step 6 below has the retry recipe.

Capture the deployed addresses:

```bash
jq '.transactions[] | select(.transactionType == "CREATE") | {name: .contractName, address: .contractAddress}' \
  broadcast/DeployEthereum.s.sol/11155111/run-latest.json
```

Pin them into `~/bankoneth-sepolia.env`:

```bash
cat > ~/bankoneth-sepolia.env <<'EOF'
SUBNAME_REGISTRAR_ADDR=0x...
ETH_REGISTRAR_ADDR=0x...
DOMAIN_HOSTING_ADDR=0x...
RESOLVER_ADDR=0x...
INFT_ADAPTER_ADDR=0x...
X402_ATTESTOR_ADDR=0x...
AGENTICPLACE_HOOK_ADDR=0x...
PRICE_ORACLE_ADDR=0x...
PAYMENT_ROUTER_ADDR=0x...
REPUTATION_GATE_ADDR=0x...
AGENT_REGISTRY_ADDR=0x...
ZEROG_INFT_ADDR=0x0000000000000000000000000000000000000000   # inert on rehearsal
EOF
```

---

## 3 — Smoke claim a `.bankon.eth` subname (Flow A)

```bash
source ~/bankoneth-sepolia.env

LABEL="testclaim-$(date +%s)"
echo "Claiming $LABEL.bankon.eth"

cd packages/cli
pnpm install --frozen-lockfile
pnpm bankoneth claim "$LABEL" \
  --network sepolia \
  --rpc $SEPOLIA_RPC \
  --addresses ~/bankoneth-sepolia.env \
  --rail eth \
  --duration 30   # 30 days; cheap rehearsal
```

Then verify via `cast`:

```bash
NODE=$(cast namehash "$LABEL.bankon.eth")
cast call --rpc-url $SEPOLIA_RPC $RESOLVER_ADDR \
  "addr(bytes32)(address)" $NODE
# Expect: the EOA derived from DEPLOYER_PK (or whatever owner the CLI used)

cast call --rpc-url $SEPOLIA_RPC $NAME_WRAPPER_ADDR \
  "getData(uint256)(address,uint32,uint64)" $(cast --to-uint256 $NODE)
# Expect: (owner, fuses including DEFAULT_FUSES bits, expiry ~= now + 30 days)
```

Fuses check: bits at positions 0 (`CANNOT_UNWRAP=1`), 2
(`CANNOT_TRANSFER=4`), 16 (`PARENT_CANNOT_CONTROL=0x10000`), and 18
(`CAN_EXTEND_EXPIRY=0x40000`) — that's `0x50005`.

---

## 4 — Sanity-check Flow B (`.eth` 2LD purchase)

```bash
LABEL="bankoneth-rehearse-$(date +%s)"

# Quote first — this is read-only, costs nothing.
cast call --rpc-url $SEPOLIA_RPC $ETH_REGISTRAR_ADDR \
  "quote(string,uint256)(uint256,uint256)" "$LABEL" 1
# Expect: (weiOwed, usd6Owed) — non-zero
```

Only proceed if the rehearsal wallet has enough Sepolia ETH for the
full ENS rent. The Sepolia ENS controller charges real ETH and refunds
overpayment. A 5-char name at 1 year is typically ~0.0019 ETH base on
Sepolia. Document the actual cost; mainnet will be ~30× higher.

If skipping the live purchase: at minimum verify the commit-only
half — `commit(p)` then `cast call` on `committedAt(commitment)` and
assert non-zero.

---

## 5 — Verify deployed contracts on Sepolia Etherscan

If `--verify` succeeded inline (Step 2), skip to Step 6. If it failed
(common — Etherscan rate-limits), the deploy script prints the per-
contract `forge verify-contract` commands:

```bash
forge script script/Verify.s.sol \
  --rpc-url $SEPOLIA_RPC \
  -vv \
  --sig "run()"
```

Copy the printed commands and run them in parallel:

```bash
forge verify-contract --chain sepolia $SUBNAME_REGISTRAR_ADDR \
  contracts/BankonSubnameRegistrar.sol:BankonSubnameRegistrar \
  --etherscan-api-key $ETHERSCAN_API_KEY
# Repeat per contract.
```

---

## 6 — Etherscan link checklist

For each of the 12 contracts, open the Sepolia Etherscan page and tick:

- [ ] Source code tab shows "Contract Source Code Verified (Exact Match)"
- [ ] Read Contract tab loads every view function (try `quote`,
      `parentOf`, `priceUSD`, `verify`, `webhookURL`, etc.)
- [ ] Write Contract tab lists every external mutator
- [ ] Constructor args decoded correctly (TREASURY_ADDR, NAME_WRAPPER_ADDR,
      controller, etc.)
- [ ] No `INVALID OPCODE` / `0xfe` in the bytecode (sentinel for a
      partial deploy)

---

## 7 — Off-chain wiring (rehearsal-only)

These steps are no-ops if you're skipping the off-chain rehearsal, but
the mainnet runbook (Phase 2 of `DEPLOYMENT.md`) requires them, so
practising here de-risks the mainnet day.

```bash
# 1. Configure the x402 facilitator EOA on the attestor:
cast send --rpc-url $SEPOLIA_RPC --private-key $DEPLOYER_PK \
  $X402_ATTESTOR_ADDR \
  "setFacilitator(address,bool)" $X402_FACILITATOR_ADDR true

# 2. Grant CONSUMER_ROLE to each registrar (subname / eth / hosting):
ATTESTOR_CONSUMER_ROLE=$(cast keccak "CONSUMER_ROLE")
for r in $SUBNAME_REGISTRAR_ADDR $ETH_REGISTRAR_ADDR $DOMAIN_HOSTING_ADDR; do
  cast send --rpc-url $SEPOLIA_RPC --private-key $DEPLOYER_PK \
    $X402_ATTESTOR_ADDR \
    "grantRole(bytes32,address)" $ATTESTOR_CONSUMER_ROLE $r
done

# 3. Set payment router recipients to the Sepolia Safe (treasury) +
#    address(0) for the other 4 buckets (rolls all into treasury):
cast send --rpc-url $SEPOLIA_RPC --private-key $DEPLOYER_PK \
  $PAYMENT_ROUTER_ADDR \
  "setRecipients(address,address,address,address,address)" \
  $TREASURY_ADDR 0x0 0x0 0x0 0x0

# 4. Mark the registrar bonded into the resolver:
RESOLVER_REGISTRAR_ROLE=$(cast keccak "REGISTRAR_ROLE")
for r in $SUBNAME_REGISTRAR_ADDR $DOMAIN_HOSTING_ADDR; do
  cast send --rpc-url $SEPOLIA_RPC --private-key $DEPLOYER_PK \
    $RESOLVER_ADDR \
    "grantRegistrar(address)" $r
done
```

---

## 8 — Sign-off

When this runbook completes cleanly:

- [ ] All 12 contracts deployed + Etherscan-verified on Sepolia
- [ ] Smoke claim produced a real `*.bankon.eth` subname with the
      correct DEFAULT_FUSES bitmask
- [ ] Resolver returns the expected `addr(node)` for the smoke claim
- [ ] (Optional) Flow B commit-only test recorded a commitment
- [ ] x402 + resolver roles wired (Step 7 above)
- [ ] AUDIT.md HIGH-3 (Phase 0.2) fix verified by a sample
      `sweep()` against a router with a configured recipient

Then proceed to the mainnet `DEPLOYMENT.md` Phase 2. Otherwise, file
the failure mode in the operator log + re-run from the failing step.

---

## Known pitfalls

- **Sepolia controller address drift.** Early ENS docs cited
  `0xfb3cE5…f968` for ETHRegistrarController on Sepolia. That is still
  current as of 2026-05; verify against the official deployments page
  before each rehearsal.
- **ALLOW_TESTNET=true is rehearsal-only.** Mainnet deploys MUST run
  without it so `_verifyChainAddresses` enforces the mainnet
  `0xD4416b…` / `0x59E1…` pair.
- **NameWrapper revert without CANNOT_UNWRAP burned.** Flow A enroll +
  Flow C enroll both abort here. Burn the fuse via the ENS app before
  the runbook starts.
- **Forge verify rate-limits.** Etherscan caps at ~5 req/sec; the
  bundled retries in `forge verify-contract` usually paper over this
  but a fresh API key with a higher rate limit avoids surprises.
- **HIGH-3 regression sentinel.** If `sweep()` reverts with "router
  fund failed", the Phase 0.2 fix didn't ship. Re-deploy from a clean
  commit on top of `4eef82faa…` or later.
