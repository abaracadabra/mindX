# bankoneth — internal audit (2026-05-23)

Self-audit pass over all 10 core contracts plus identity / iNFT / x402
primitives. Findings are categorised by severity, with the fix landed
in the same commit. Run `forge test` to verify — 54/54 passing post-fix.

| Severity | Used for |
|---|---|
| **HIGH**   | Loss of funds, total bypass of access control, broken security invariant |
| **MEDIUM** | Partial bypass, livelock, design flaw with mainnet impact |
| **LOW**    | Behaviour that's "wrong but recoverable", surprising semantics |
| **INFO**   | Code-quality / clarity, no security impact |

## Findings

### HIGH-1 — `BankonDomainHosting`: fuses truncated to `uint16`, parent-lock + extend-expiry guarantees silently lost

**File:** `contracts/BankonDomainHosting.sol` (line 108 pre-fix), `contracts/interfaces/IBankonExtensions.sol` (struct definition)

`DEFAULT_CHILD_FUSES = CANNOT_UNWRAP | PARENT_CANNOT_CONTROL | CAN_EXTEND_EXPIRY`
= `0x50001` (bits 0, 16, 18). The interface's `EnrolledParent` struct
declared `childFuses` as `uint16`, and `enroll()` cast
`uint16(DEFAULT_CHILD_FUSES)` to fit — producing `0x0001`. **Only
`CANNOT_UNWRAP` survived; `PARENT_CANNOT_CONTROL` and `CAN_EXTEND_EXPIRY`
were silently dropped.** This breaks the bankoneth security model: without
`PARENT_CANNOT_CONTROL`, the parent owner could rewrite subname records
on-the-fly; without `CAN_EXTEND_EXPIRY`, subname holders could not renew.

Then on line 161 (issue()), the storage was widened back via
`uint32(p.childFuses)` — but `p.childFuses` was already `uint16`, so the
high bits were gone for good.

**Fix:** widened `EnrolledParent.childFuses` and the `enroll()` arg to
`uint32` end-to-end. Storage now holds the full bitmask; `setSubnodeRecord`
receives it directly. Default fuses now reach NameWrapper correctly.

**Impact:** every subname previously issued via Flow C would have been
issuable without parent-lock — a silent griefable rug. Caught pre-mainnet.

---

### HIGH-3 — `BankonEthRegistrar.sweep()` calls `paymentRouter.distribute` without funding the router (Phase 0.2)

**File:** `contracts/BankonEthRegistrar.sol` (line 241 pre-fix)

`sweep()` invoked `paymentRouter.distribute(address(0), bal)` directly,
but `BankonPaymentRouter.distribute` is **not** `payable` — it fans out
from its own balance, which is zero unless funded first. Every sweep
would silently revert at the first `_send(treasury, …)` low-level call
inside the router (the call uses `payable(...).call{value: …}("")`
which reverts on insufficient balance).

This is the same bug class as HIGH-2 (`BankonDomainHosting.issue()`
ETH router-cut path). It was caught here by the new
`test_Sweep_routesBalanceToRouter` test added in Phase 0.2.

**Fix:** mirror the HIGH-2 pattern — top up the router with a raw
`payable(address(paymentRouter)).call{value: bal}("")` before invoking
`distribute()`. The new code:

```solidity
(bool ok,) = payable(address(paymentRouter)).call{value: bal}("");
require(ok, "router fund failed");
paymentRouter.distribute(address(0), bal);
```

**Impact:** every Flow B sweep would revert, leaving the BANKON markup
trapped in the registrar contract indefinitely. The treasurer would
have had to redeploy with a fixed `sweep()` post-mainnet to recover
funds. Caught pre-mainnet by the new Phase 0.2 test.

**Status:** CLOSED — Phase 0.2 (v2 plan).

---

### HIGH-2 — `BankonDomainHosting.issue()` ETH rail accepts any `msg.value > 0`

**File:** `contracts/BankonDomainHosting.sol` (line 146 pre-fix)

The ETH path checked `if (msg.value == 0) revert InsufficientPayment(...)`
but did not compare against the parent's price. Any caller could mint a
subname under any enrolled parent for **1 wei**, draining the parent's
revenue without owner consent.

**Fix:** added a per-parent `priceEthWei` floor configurable at
`enroll()` and updatable via a new `setPrices()` method. The ETH rail
requires `msg.value >= priceEthWei`; setting `priceEthWei = 0` disables
the rail entirely (forcing x402-avm). Parent owners track ETH/USD
movement off-chain and update via `setPrices()`.

**Impact:** unbounded under-payment under mainnet conditions. Fixed.

---

### MEDIUM-1 — `BankonInftAdapter`: tokenId 0 fools duplicate check; WIRER can silently rebind a label

**File:** `contracts/BankonInftAdapter.sol` (lines 113, 131-133 pre-fix)

Two related issues:

1. `requestMint` used `_tokenIdOf[labelhash] != 0` as the
   "already-bound" sentinel — but tokenId 0 is a legal value on some 0G
   chains, so a label whose iNFT was minted as tokenId 0 would slip
   through duplicate detection.
2. `registerZeroGTokenId` overwrote `_tokenIdOf[labelhash]` and
   `_tbaOf[labelhash]` unconditionally. A compromised or rogue
   `WIRER_ROLE` could redirect any existing TBA binding to a new
   address.

**Fix:** added a `_bound[labelhash]` boolean as the canonical "set once"
sentinel. `requestMint` checks `_bound`; `registerZeroGTokenId` now
reverts with `LabelAlreadyBound` on second binding. Rebinding requires
contract-level intervention (deploy a new adapter, re-grant roles).

**Impact:** WIRER trust model now properly scoped — they can bind labels
to (tokenId, TBA) but not rebind. Aligns with the "WIRER is operator,
not admin" intent.

---

### MEDIUM-2 — `BankonX402Attestor`: monotonic nonce enforcement causes false rejects under parallel consumption

**File:** `contracts/BankonX402Attestor.sol` (lines 80-83 pre-fix)

The contract enforced `r.nonce > lastNonce[signer]` and reverted with
`NonceTooOld` otherwise. But the same facilitator key signs receipts
that get consumed by Flow A registrar, Flow B registrar, and Flow C
hosting **in parallel** — three transactions in the same block can
arrive in any order. Whichever was mined last won the nonce race; the
other two reverted.

The check was justified as "defense in depth against replay" but
`_spent[receiptHash]` already prevents replay independently. Monotonic
nonce ordering added no security and broke legitimate use.

**Fix:** dropped the `revert NonceTooOld(...)` branch. `lastNonce` is
still tracked (`= max(lastNonce, r.nonce)`) for off-chain monitoring of
facilitator activity, but no longer enforced. The `NonceTooOld` error
selector was removed.

**Test impact:** `test_MonotonicNonce` was inverted to
`test_OutOfOrderNonceAccepted` — asserts the opposite behaviour now.

---

### LOW-1 — `BankonSubnameResolver.multicall` is callable by anyone

**File:** `contracts/BankonSubnameResolver.sol` (lines 126-133)

`multicall` is `external` with no access control. The inner state-mutating
functions (`setAddr`, `setText`, `setINFTBinding`) are gated by
`REGISTRAR_ROLE`. delegatecall preserves `msg.sender`, so unauthorized
callers can't actually write — the inner check reverts and unwinds.

**Status:** Verified safe. No fix required. Pattern matches ENS's
canonical `PublicResolver.multicall` shape; documented in the .md.

---

### LOW-2 — `BankonEthRegistrar.reveal` uses `this.quote(...)` (external self-call)

**File:** `contracts/BankonEthRegistrar.sol` (line 181 pre-fix; now line 191)

External self-call wastes ~700 gas per `reveal()` invocation and breaks
view inlining. Could be `_quote(...)` internal helper.

**Fix:** added `_quote(string memory label, uint256 durationYears)`
internal view at `BankonEthRegistrar.sol:122`. Both the public
`quote()` external view and `reveal()` now call the internal helper.
Saves ~700 gas per reveal; no behavioural change.

**Status:** CLOSED — Phase 0.1 (v2 plan).

---

### LOW-3 — `BankonReputationGate.bonafideScore` trusts external oracle

**File:** `contracts/BankonReputationGate.sol` (line 78)

`bonafide.score(agent)` is an external call into a contract whose
behaviour we don't control. A malicious oracle could revert, gas-grief,
or return arbitrary numbers. Only `GOV_ROLE` can set the oracle, so this
is a documented trust assumption.

**Status:** Acknowledged. Treasury must vet oracle contracts before
calling `setOracles`. Documented in `BankonReputationGate.md`.

---

### INFO-1 — `AgentRegistry`: shadowed parameter name `isSoulbound`

**File:** `contracts/identity/AgentRegistry.sol` (line 212)

`function setSoulbound(uint256 agentTokenId, bool isSoulbound)` shadows
the public view function `isSoulbound(uint256)` at line 295. Solc emits
a warning; no runtime effect.

**Fix:** renamed the parameter to `soulboundFlag`; both usages updated.
Solc warning gone.

**Status:** CLOSED — Phase 0.1 (v2 plan).

---

### INFO-2 — Two test functions can be `view`

**Files:** `script/Verify.s.sol:17`, `test/BankonAgenticPlaceHook.t.sol:19`

Solc suggests `view` mutability for two functions that read state but
don't mutate. Cosmetic warnings only.

**Fix:** added `view` to `Verify.run()` and
`BankonAgenticPlaceHookTest.test_InitialWebhook()`. Solc warnings gone.

**Status:** CLOSED — Phase 0.1 (v2 plan).

---

## What's NOT a finding

Patterns that look risky but verified safe:

- `BankonInftAdapter._computeTba` (the hand-rolled CREATE2 derivation) —
  verified against ERC-6551 reference impl byte-for-byte.
- `BankonPaymentRouter._send` low-level call — every call site checks
  `(bool ok,)` and reverts on failure.
- `BankonSubnameResolver.multicall` — see LOW-1.
- `BankonSubnameRegistrar.register` voucher flow — EIP-712 signing with
  gateway-signer-role check, idempotent via `usedReceipts[hash]`,
  reentrancy-guarded, pause-aware.
- `BankonEthRegistrar.reveal` refund math — verified balance accounting
  holds even with ENS controller's automatic refund of overpayment.
- ECDSA malleability — OZ v5 `ECDSA.recover` reverts on malleable sigs,
  not returns `address(0)`.

## What's out of scope

This is an internal first-pass audit. Things deliberately not covered:

- **External audit** — pre-mainnet, the operator should commission a
  proper external review (Trail of Bits / Spearbit / Cantina) covering
  the contracts in this report plus the rest of the iNFT_7857 surface
  (sealed key rotation, oracle-attested transfers, ZKP TODO).
- **Cross-chain bridge** between Ethereum InftAdapter and 0G iNFT — the
  current operator-attested WIRER pattern is an interim. A real bridge
  needs its own audit.
- **Treasury Safe operational security** — multisig signer rotation,
  hardware wallet hygiene, post-deploy address handoff. Not a contract
  concern.
- **Gas optimisation** — focus was correctness + security. LOW-2 was
  the only material gas finding; closed in Phase 0.1.
- **Fork tests** against live mainnet ENS — recommended before deploy.
  `vm.createSelectFork(MAINNET_RPC, ...)` boilerplate not in this pass.

## Verification

```bash
cd openagents/bankoneth
forge build          # 89 files compile, default profile
forge test           # 54 tests pass (including the inverted nonce test)
FOUNDRY_PROFILE=zerog forge build --force   # 87 files, iNFT_7857
```

All audit fixes pass the existing suite; no regression in the 34-test
re-homed registrar suite.

## Changelog (single commit)

- `BankonDomainHosting.sol` — `enroll()` signature: `+priceEthWei`,
  `childFuses` widened to `uint32`. New `setPrices()` admin method.
  Issue() ETH path enforces `priceEthWei` floor.
- `IBankonExtensions.sol` — `EnrolledParent.priceEthWei` added,
  `childFuses` widened to `uint32`, `setPrices()` added.
- `BankonInftAdapter.sol` — `_bound[labelhash]` mapping added; both
  `requestMint` and `registerZeroGTokenId` use it as the duplicate
  sentinel.
- `BankonX402Attestor.sol` — removed `NonceTooOld` error and the
  monotonic enforcement branch; `lastNonce` is now `max(...)` only.
- `BankonX402Attestor.t.sol` — `test_MonotonicNonce` inverted to
  `test_OutOfOrderNonceAccepted`.
- `BankonDomainHosting.t.sol` — `enroll()` calls updated to pass
  `priceEthWei = 0.001 ether`.
- `packages/core/src/abis.ts` — `BANKON_DOMAIN_HOSTING_ABI` updated for
  the new struct + new `setPrices()` method.
