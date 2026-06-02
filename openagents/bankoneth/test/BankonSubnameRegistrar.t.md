# BankonSubnameRegistrar.t

> Comprehensive Foundry suite for the BANKON v1 ENS subname registrar — re-homed from the DAIO repository. Covers paid registration via EIP-712 voucher, free reputation-gated path, replay protection, label validation, expiry capping, ERC-8004 bundled mint, fuse profile, renewal, pause, role admin, event emission, the new `registerAgentSubname` mindX-agent path, and a fuzz harness over arbitrary receipts and expiry windows.

**SPDX:** Apache-2.0 (source file is MIT — note the deliberate license divergence) | **Pragma:** ^0.8.24 | **Source:** [`BankonSubnameRegistrar.t.sol`](./BankonSubnameRegistrar.t.sol) | **Suite:** `BankonSubnameRegistrar_Test`

> **NOTE:** the .sol file itself carries `SPDX-License-Identifier: MIT` — divergent from the Apache-2.0 elsewhere in `test/`. Likely a vestige of the DAIO repo origin. Audit ledger should flag for consistency.

## Role in bankoneth

Exercises [`contracts/BankonSubnameRegistrar.sol`](../contracts/BankonSubnameRegistrar.sol) — the Flow A central registrar: mints `*.bankon.eth` subnames with ENS NameWrapper, writes the canonical resolver record set (`addr`, multi-chain addrs, text records, contenthash), records a payment receipt on the router, optionally bundles an ERC-8004 agent mint, all gated by an EIP-712 voucher signed by the BANKON gateway (paid path) OR by a reputation-gate score (free path) OR by a role-gated mindX-agent path (address-as-label hex mint).

This is the **most exhaustive** test file in bankoneth — 34 tests covering construction, both registration paths, replay/expiry/label/fuse/cap edge cases, renewal, resolver records, ERC-8004 bundle toggle, pause, admin setters, role grants, USD quoting, fuzz, and the new agent-subname path.

Flow coverage: **Flow A** (canonical bankon.eth subname mint).

## Fixture (`setUp()`)

1. `gateway = vm.addr(gatewayPk)` where `gatewayPk = 0xD0`.
2. `vm.warp(1_700_000_000)` — anchors `block.timestamp` for deterministic deadline math.
3. Deploys `MockNameWrapper`, `MockResolver`, `MockIdentityRegistry`, `BankonPriceOracle(admin)`, `BankonReputationGate(admin)`, `BankonPaymentRouter(admin)`.
4. Computes synthetic `parentNode = namehash("bankon.eth")` (test-local — `keccak256(keccak256("" || keccak256("eth")) || keccak256("bankon"))`).
5. `wrapper.adminSetParent(parentNode, admin, 0, now + 10y)` — wraps the parent owned by admin with far-future expiry so child expiry isn't capped accidentally.
6. Deploys `BankonSubnameRegistrar(wrapper, resolver, parentNode, router, oracle, gate, idreg, admin)`.
7. Caches `DOMAIN_SEPARATOR = _domainSeparator(address(reg))` for voucher signing.
8. Role grants:
   - `reg.grantRole(GATEWAY_SIGNER_ROLE, gateway)` from admin.
   - `gate.grantRole(GOV_ROLE, address(this))` from admin — lets the test directly set reputation scores.
   - `router.grantRole(REGISTRAR_ROLE, address(reg))` from admin — lets the registrar record receipts on the router.

EOAs / constants: `admin=0xA11CE`, `alice=0xA1`, `bob=0xB1`, `carol=0xC1`, `gatewayPk=0xD0`.

### Helpers
- `_domainSeparator(addr)` — EIP-712 domain hash with name=`"BankonSubnameRegistrar"`, version=`"1"`, chainId, verifyingContract.
- `_signRegistration(label, owner, expiry, paymentReceiptHash, deadline, signerPk)` — RSV-packed EIP-712 sig of `Registration` typehash.
- `_signRenewal(label, newExpiry, paymentReceiptHash, deadline, signerPk)` — RSV-packed EIP-712 sig of `Renewal` typehash.
- `_meta()` — canonical `AgentMetadata` literal: agentURI, mindxEndpoint, x402Endpoint, algoIDNftDID, contenthash=`0xe3010170`, baseAddress=`0xBA5E`, algoAddr=`0x01020304`.
- `_node(label)` — `keccak256(parentNode || keccak256(label))`.

## Test inventory

All 34 tests, in source order:

| # | Test | What it asserts | Notable cheatcodes |
|---|---|---|---|
| 1 | `test_Constructor_setsRolesAndImmutables` | Reads back every immutable + role: `nameWrapper`, `defaultResolver`, `paymentRouter`, `priceOracle`, `reputationGate`, `parentNode`. Asserts admin holds `DEFAULT_ADMIN_ROLE` + `BANKON_OPS_ROLE` + `BONAFIDE_GOV_ROLE`, gateway holds `GATEWAY_SIGNER_ROLE`. Asserts `DEFAULT_FUSES == 0x10000 | 0x1 | 0x4 | 0x40000` (PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CANNOT_TRANSFER | CAN_EXTEND_EXPIRY). Asserts `erc8004BundleEnabled() == true`. | view-only |
| 2 | `test_Constructor_revertsOnZeroAddresses` | Constructor reverts with `ZeroAddress` selector for each of the first four address args set to `address(0)`. (Does not exhaustively test all 7 — covers wrapper, resolver, paymentRouter, priceOracle.) | `vm.expectRevert(selector)` × 4 |
| 3 | `test_PaidRegister_happyPath_emitsAndStores` | Voucher-signed register stores correctly: returned `node == _node("alice")`, `agentId > 0`, `reg.labelOf(node) == "alice"`, `reg.ownerOfLabel(node) == alice`, `reg.usedReceipts(receipt) == true`, `wrapper.getData(node) == (alice, DEFAULT_FUSES, expiry)`, `resolver.addrOf(node) == alice`, `idreg.ownerOf(agentId) == alice`, `idreg.uriOf(agentId) == _meta().agentURI`. | EIP-712 `vm.sign` |
| 4 | `test_PaidRegister_revertsOnReplayedReceipt` | First register burns the receipt; a second register with a different label but same `receipt` reverts with `ReceiptAlreadyUsed`. | `vm.expectRevert(selector)` |
| 5 | `test_PaidRegister_revertsOnWrongSigner` | Voucher signed by random PK (`0xDEAD`) — not the registered gateway — reverts with `InvalidGatewaySignature`. | `vm.sign(0xDEAD, …)` |
| 6 | `test_PaidRegister_revertsOnExpiredDeadline` | `deadline = block.timestamp - 1` → reverts with `VoucherExpired`. | warp-relative deadline |
| 7 | `test_PaidRegister_revertsOnEmptyLabel` | `label = ""` → reverts with `LabelEmpty`. | — |
| 8 | `test_PaidRegister_revertsOnLabelTooShort` | `label = "ab"` (2 chars) → reverts with `LabelTooShort`. (Paid minimum is 3 chars.) | — |
| 9 | `test_PaidRegister_revertsOnZeroOwner` | `owner = address(0)` → reverts with `ZeroAddress`. | — |
| 10 | `test_PaidRegister_capsExpiryToParent` | Sets parent expiry to `now + 1 day`; requests `now + 365 days`. Asserts actual stored expiry == parent's `now + 1 day`. Implements the "no child can outlive parent" ENS invariant. | `wrapper.adminSetParent(...)` re-set |
| 11 | `test_PaidRegister_revertsWhenAgentBanned` | `gate.setBanned(alice, true)` then register for alice → reverts with `NotEligible`. | direct gate state-write |
| 12 | `test_FreeRegister_allowsReputableAgent` | `gate.setAdminScore(alice, 200)` (≥ freeThreshold 100), 9-char label `"longalice"` → free register succeeds; node matches; `wrapper.getData(node).fuses == DEFAULT_FUSES`. | direct gate state-write |
| 13 | `test_FreeRegister_revertsForUnreputableAgent` | alice score=0, free register reverts with `NotEligible`. | — |
| 14 | `test_FreeRegister_revertsOnShortLabel` | Reputable alice, label `"abc123"` (6 chars — free tier requires 7+) → reverts with `LabelTooShort`. | — |
| 15 | `test_Renew_extendsExpiry` | After initial register, renew via `_signRenewal` voucher to `now + 2y`. Asserts `wrapper.getData(node).expiry == newExp` and `reg.usedReceipts(renewReceipt) == true`. | renewal EIP-712 sign |
| 16 | `test_Renew_revertsOnReplayedReceipt` | First renew burns receipt; second renew (different newExpiry, same receipt) reverts with `ReceiptAlreadyUsed`. | replay-protection check |
| 17 | `test_PaidRegister_writesAllResolverRecords` | After register, asserts the resolver received the full record bundle: `setAddr(node, alice)`, text records (`url`→mindxEndpoint, `x402.endpoint`, `algoid.did`, `agent.card`), contenthash, multi-chain Base addr (coinType `0x80002105`), multi-chain Algorand addr (coinType `0x8000011B`). Asserts `resolver.multicallCount() == 1` — all records written in a single `multicall`. | multi-record read-back |
| 18 | `test_PaidRegister_skipsErc8004WhenDisabled` | Admin calls `reg.setErc8004Bundle(false)`; register returns `agentId == 0`; `idreg.nextId() == 1` (no mint happened). | `vm.prank(admin)` |
| 19 | `test_Pause_blocksRegister` | Admin pauses; register reverts with `Pausable.EnforcedPause.selector`. | `vm.expectRevert(Pausable selector)` |
| 20 | `test_Pause_unpauseRestoresRegister` | Admin pauses then unpauses; register succeeds again. | `vm.startPrank(admin)` |
| 21 | `test_Pause_revertsForNonOps` | alice (no `BANKON_OPS_ROLE`) calls `pause()` → reverts with `AccessControlUnauthorizedAccount(alice, opsRole)`. | `vm.expectRevert(abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, …))` |
| 22 | `test_SetPriceOracle_byGov` | Admin deploys a new `BankonPriceOracle`, calls `setPriceOracle(newAddr)`; `reg.priceOracle() == newAddr`. | — |
| 23 | `test_SetPriceOracle_revertsOnZero` | `setPriceOracle(address(0))` → reverts with `ZeroAddress`. | — |
| 24 | `test_SetReputationGate_byGov` | Admin deploys new gate, swaps via `setReputationGate(newAddr)`. | — |
| 25 | `test_SetIdentityRegistry8004_byGov` | Admin calls `setIdentityRegistry8004(0xBEEF)`; `reg.identityRegistry8004() == 0xBEEF`. Allows hot-swap of the ERC-8004 backend. | — |
| 26 | `test_SetErc8004Bundle_emits` | Admin disables ERC-8004 bundle; `reg.erc8004BundleEnabled() == false`. Test name implies it emits, but only the storage read is asserted — no `expectEmit`. | — |
| 27 | `test_GrantGatewaySignerRole_letsNewSignerVouch` | Admin grants `GATEWAY_SIGNER_ROLE` to a new EOA `0xCAFE`. A voucher signed by the new EOA registers successfully. Validates the gateway signer set is mutable. | `vm.sign(newSignerPk, …)` |
| 28 | `test_QuoteUSD_usesOracle` | `quoteUSD("alice" /* 5 char */, now+365d)` returns `5_000_000` (= $5/yr base 6 decimals, default 5-char-label rate per oracle). | view-only |
| 29 | `testFuzz_PaidRegister_arbitraryReceiptAndExpiry(bytes32 receipt, uint16 daysOut)` | Fuzz: `vm.assume(receipt != 0)`, `vm.assume(1 ≤ daysOut ≤ 365*5)`. Builds voucher with `expiry = now + daysOut days`, registers. Asserts `reg.ownerOfLabel(_node("fuzzz")) == alice` and `reg.usedReceipts(receipt) == true`. | `vm.assume`, fuzz parameters |
| 30 | `test_AgentSubname_revertsWithoutRole` | alice (no `MINDX_AGENT_MINTER_ROLE`) calls `registerAgentSubname(alice, expiry, _meta())` → reverts (bare `vm.expectRevert()`). | — |
| 31 | `test_AgentSubname_mintsWithRole_freeAddressAsLabel` | mindxMinter (`0xCA51EFE`) granted role mints for alice. Asserts returned `label.length == 40` (40 lowercase hex chars, no `0x`), `node == _node(label)`, `agentId > 0`, `reg.ownerOfLabel(node) == alice`. ERC-8004 bundle still triggers. | `_grantMindxMinter()` helper |
| 32 | `test_AgentSubname_labelIsLowercaseHexNoPrefix` | Mints for `agent=0xDEaDBeEFcAfe1234567890aBCDEF1234567890AB`. Asserts label literally equals `"deadbeefcafe1234567890abcdef1234567890ab"` (40 chars, all-lowercase, no `0x`). | label encoding spec |
| 33 | `test_AgentSubname_revertsOnZeroAddress` | mindxMinter calls `registerAgentSubname(address(0), …)` → reverts with `ZeroAddress`. | — |
| 34 | `test_AgentSubname_paidAndFreePathsStillWork` | After enabling the agent path, the prior paid path (alice/receipt-1) and free path (bob/score=200, `"longbob123"`) and agent path (carol) all coexist without interference. Smoke test for the three-mint-path orthogonality invariant. | composite check |

## Coverage

**Covered methods on `BankonSubnameRegistrar`:**
- `constructor(...)` — happy + 4× zero-address revert.
- `register(label, owner, expiry, receiptHash, deadline, sig, meta)` — happy, 7 revert paths, expiry cap, ban check, ERC-8004 bundle skip.
- `registerFree(label, owner, expiry, meta)` — happy + 2 revert paths.
- `registerAgentSubname(agent, expiry, meta)` — happy + 2 revert paths + label format spec.
- `renew(label, newExpiry, receiptHash, deadline, sig)` — happy + replay revert.
- `pause()` / `unpause()` — happy + non-ops revert.
- `setPriceOracle / setReputationGate / setIdentityRegistry8004 / setErc8004Bundle` — admin setters.
- `grantRole(GATEWAY_SIGNER_ROLE, ...)` — new-signer flow.
- `quoteUSD(label, expiry)` — view, single case.
- Public views: `parentNode`, `defaultResolver`, `nameWrapper`, `paymentRouter`, `priceOracle`, `reputationGate`, `identityRegistry8004`, `DEFAULT_FUSES`, `erc8004BundleEnabled`, `labelOf`, `ownerOfLabel`, `usedReceipts`, `MINDX_AGENT_MINTER_ROLE`.
- Custom errors: `ZeroAddress`, `ReceiptAlreadyUsed`, `InvalidGatewaySignature`, `VoucherExpired`, `LabelEmpty`, `LabelTooShort`, `NotEligible`.
- EIP-712 domain: `BankonSubnameRegistrar` v1.
- Type hashes: `Registration(string label,address owner,uint64 expiry,bytes32 paymentReceiptHash,uint256 deadline)`, `Renewal(string label,uint64 newExpiry,bytes32 paymentReceiptHash,uint256 deadline)`.
- Coin types: `COIN_TYPE_BASE = 0x80002105`, `COIN_TYPE_ALGO = 0x8000011B`.

**Not covered:**
- Long-label fuzz (only `"fuzzz"` is reused as label in the fuzz harness).
- Label charset validation (e.g., uppercase, unicode, `.` separator) — guard exists in contract but isn't fuzzed.
- Mainnet ENS interaction — `MockNameWrapper` is a permissive stub; real `NameWrapper` fuse semantics, approval flow, and CCIP-Read aren't exercised.
- Resolver `multicall` partial-failure handling — the mock just delegatecalls each entry and `require(ok)`.
- Revenue split math in `BankonPaymentRouter.distribute()` — only role-gating is exercised here (single recipient).
- Concurrent receipts (different parents, same hash).

## Notable patterns

- **EIP-712 signing as test infra**: `_signRegistration` and `_signRenewal` are the canonical helpers. They mirror the on-chain encoding exactly — any drift in the contract's typehash string breaks both helpers.
- **`address(this)` granted `GOV_ROLE` on the gate** — lets tests directly poke reputation scores without prank/role-cycling for each test.
- **Cached `DOMAIN_SEPARATOR`** — computed once in setUp because `block.chainid` is constant per test process.
- **`vm.warp(1_700_000_000)`** — anchors timestamps so deadline math is stable even if the host clock drifts.
- **Three-path orthogonality test (`test_AgentSubname_paidAndFreePathsStillWork`)** — a single composite assertion that all three mint paths coexist correctly, used as a guard against future refactors collapsing into one another.
- **Address-as-label hex encoding** — tests 31+32 lock the format: 40 lowercase hex chars, no `0x` prefix. Critical for off-chain agent-discovery indexers (e.g. AgenticPlace) that index by canonical label.

## Known caveats

- `MockNameWrapper` is permissive — it accepts any subnode mint without ENS validation, doesn't enforce CANNOT_UNWRAP semantics on the parent at mint time, and treats `isWrapped` as `owner != address(0)`. The expiry cap behavior is faithful (`extendExpiry` caps to parent expiry), but fuse-burn semantics are not.
- `MockResolver` records writes but doesn't validate them — e.g., a duplicate `setAddr` overwrites silently. Real Public Resolver has access-control checks.
- `MockIdentityRegistry` mints sequential IDs with no metadata validation.
- The license discrepancy (file is MIT, sibling tests are Apache-2.0) is unintentional baggage from the DAIO repo re-home — see note at top.
- The fuzz harness reuses the literal label `"fuzzz"` and only fuzzes `receipt` + `daysOut` — label charset/length aren't fuzzed.
- `test_SetErc8004Bundle_emits` name promises an event check that isn't actually performed — name is misleading.

## How to run

```bash
# All 34 tests:
forge test --match-path test/BankonSubnameRegistrar.t.sol -vvv

# Just the fuzz harness:
forge test --match-path test/BankonSubnameRegistrar.t.sol --match-test testFuzz_ -vvv

# Just the agent-subname tests:
forge test --match-path test/BankonSubnameRegistrar.t.sol --match-test AgentSubname -vvv
```

## See also

- [`../contracts/BankonSubnameRegistrar.sol`](../contracts/BankonSubnameRegistrar.sol) — system under test.
- [`../contracts/BankonPriceOracle.sol`](../contracts/BankonPriceOracle.sol), [`BankonReputationGate.sol`](../contracts/BankonReputationGate.sol), [`BankonPaymentRouter.sol`](../contracts/BankonPaymentRouter.sol) — dependencies.
- [`mocks/MockNameWrapper.sol`](./mocks/MockNameWrapper.sol), [`mocks/MockResolver.sol`](./mocks/MockResolver.sol), [`mocks/MockIdentityRegistry.sol`](./mocks/MockIdentityRegistry.sol) — fakes.
- [`BankonEndToEnd.t.sol`](./BankonEndToEnd.t.sol) — Mode-A iNFT pipeline.
- `docs/FLOWS.md` (Flow A) — canonical bankon.eth subname mint.
- `docs/ERC8004_BUNDLE.md` — ERC-8004 agent-mint bundle design.
- Origin: re-homed from `DAIO/contracts/test/BankonSubnameRegistrar.t.sol` (preserved git history during re-home).
