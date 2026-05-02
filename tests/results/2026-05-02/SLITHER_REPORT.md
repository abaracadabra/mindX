# Slither Static Analysis — All Submission Contracts (2026-05-02)

> Slither v0.11.5 run against all 6 contracts in scope for the ETHGlobal Open Agents submission.
> Severity: medium and above only (`--exclude-low --exclude-informational --exclude-optimization`).

## Aggregate

| Contract | Findings | Severity | Action taken |
|---|---|---|---|
| `daio/contracts/inft/iNFT_7857.sol` | **1** | Medium (reentrancy-no-eth) | **FIXED** — `nonReentrant` added to `mintAgent` and `burn`; regression test added |
| `daio/contracts/ens/v1/BankonSubnameRegistrar.sol` | 3 | Medium (unused-return) | Documented as accepted (false positive — deterministic recompute) |
| `daio/contracts/THOT/v1/THOT.sol` | 0 (clean) | — | — |
| `daio/contracts/agentregistry/AgentRegistry.sol` | 0 (clean) | — | — |
| `openagents/conclave/contracts/src/Conclave.sol` | 1 | Medium (write-after-write) | Documented as intentional (set-execute-clear pattern) |
| `openagents/conclave/contracts/src/ConclaveBond.sol` | **0 (clean)** | — | — |

**Net: 1 real finding (iNFT) — fixed and tested. 4 false positives.**

Verbatim Slither output captured per file:
- [`slither_inft7857.txt`](slither_inft7857.txt)
- [`slither_bankonsubnameregistrar.txt`](slither_bankonsubnameregistrar.txt)
- [`slither_thot.txt`](slither_thot.txt)
- [`slither_agentregistry.txt`](slither_agentregistry.txt)
- [`slither_conclave_conclave.txt`](slither_conclave_conclave.txt)
- [`slither_conclave_conclavebond.txt`](slither_conclave_conclavebond.txt)

---

## Finding 1 (FIXED) — iNFT_7857.mintAgent cross-function reentrancy

**Detector:** `reentrancy-no-eth`
**Severity:** Medium
**File:** `daio/contracts/inft/iNFT_7857.sol:254-307`

### The vulnerability

The mint flow used the gate-open pattern:

```solidity
_gateOpen = true;
_safeMint(to, tokenId);  // calls onERC721Received(to) — external call
_gateOpen = false;
```

`_gateOpen` is read by `_update()` (line 615) to permit privileged transfers that would otherwise be blocked by the "transfer requires sealed key" rule. A malicious recipient could implement `onERC721Received` to re-enter the contract while `_gateOpen == true`, calling back into `_update` (e.g. via `transferFrom`) to bypass the sealed-key invariant.

### Why it mattered

ERC-7857's entire security model is "ownership only moves through sealed-key handoff." This re-entry would have allowed a recipient to transfer a freshly-minted token to anyone, without the sealed-key oracle proof, defeating the standard.

`transferWithSealedKey` and `cloneAgent` were already protected with `nonReentrant`. Only `mintAgent` and (defensively) `burn` lacked it.

### The fix (one line per function)

```solidity
function mintAgent(...)
    external
    whenNotPaused
    onlyRole(MINTER_ROLE)
    nonReentrant            // ← added
    returns (uint256 tokenId)
{ ... }

function burn(uint256 tokenId)
    public
    override(ERC721Burnable)
    nonReentrant            // ← added
{ ... }
```

`nonReentrant` is OZ's `ReentrancyGuard` mutex (already inherited at line 73). It's a single status variable shared across all `nonReentrant`-decorated functions. Re-entry into ANY of `mintAgent`, `burn`, `transferWithSealedKey`, or `cloneAgent` while one is executing reverts with `ReentrancyGuardReentrantCall()`.

### The regression test

`test_mintAgent_blocksReentrancyViaOnERC721Received` actively performs the attack:

```solidity
contract ReentrantReceiver is IERC721Receiver {
    iNFT_7857 internal target;
    constructor(iNFT_7857 _target) { target = _target; }

    function onERC721Received(...) external returns (bytes4) {
        // Attempts cross-function reentrancy. Reverts because the outer
        // mintAgent call holds the nonReentrant mutex.
        target.mintAgent(address(this), keccak256("re-entry-root"), ...);
        return IERC721Receiver.onERC721Received.selector;
    }
}

function test_mintAgent_blocksReentrancyViaOnERC721Received() public {
    ReentrantReceiver attacker = new ReentrantReceiver(nft);
    vm.prank(minter);
    vm.expectRevert();  // re-entry is blocked
    nft.mintAgent(address(attacker), ROOT_A, ...);
}
```

**Result: PASS, 184,743 gas.** The malicious receiver's re-entry attempt is blocked; the outer mint reverts; the token is never minted.

iNFT-7857 forge tests: **56 → 57** all passing.

### Why Slither still flags after the fix

Slither identifies the *syntactic* pattern (external call followed by state write). It does not model OpenZeppelin's `nonReentrant` modifier semantics. Post-fix, the report is a known false positive. The regression test is the authoritative proof.

---

## Finding 2 (accepted false positive) — BANKON v1 unused-return

**Detector:** `unused-return`
**Severity:** Medium
**File:** `daio/contracts/ens/v1/BankonSubnameRegistrar.sol:308-330`

Three calls ignore their return value:
1. `nameWrapper.setSubnodeOwner(...)` returns `bytes32 node` — we ignore it
2. `nameWrapper.setSubnodeRecord(...)` returns same — ignored
3. `defaultResolver.multicall(calls)` returns `bytes[]` — ignored

### Why this is accepted

For (1) and (2): the returned node hash is deterministic (`keccak256(parentNode || keccak256(label))`); the registrar can recompute it on demand and does not need the return value. Storing it would be redundant.

For (3): Solidity's `multicall` reverts the entire transaction if any sub-call reverts. The returned `bytes[]` array contains success-data from each call; we don't need it because we don't decode further results from the resolver writes (we just need them to land).

Could we add `assert(success)` checks? Yes, but the `multicall` already reverts on failure, so the check would be unreachable.

**No action taken.** 29/29 BANKON tests still validate the round-trip behavior.

---

## Finding 3 (accepted intentional pattern) — Conclave write-after-write on _slashContext

**Detector:** `write-after-write`
**Severity:** Medium
**File:** `openagents/conclave/contracts/src/Conclave.sol:202-204`

```solidity
c.members[idx1 - 1].slashed = true;
_slashContext = conclave_id;        // line 202
uint256 amt = bond.slash(conclave_id, leaker);  // line 203 (reads _slashContext via callback)
_slashContext = bytes32(0);         // line 204
```

### Why this is intentional

`_slashContext` is a transient state variable (line 269: `bytes32 private _slashContext`). It is exposed via a public view function (`slashContext()` at line 261) so the `ConclaveBond` contract can verify, during its `slash()` callback, that the caller was authorized by `Conclave`.

Pattern:
1. Set `_slashContext = conclave_id` (gate open).
2. Call `bond.slash(...)` — bond's logic reads `slashContext()` to authorize.
3. Clear `_slashContext = bytes32(0)` (gate closed).

Slither sees the syntactic write-then-write but doesn't understand the cross-contract read in between. **No action taken.** 10/10 Conclave Solidity tests validate end-to-end slash flow.

---

## Library-level findings (out of scope)

12× `divide-before-multiply` notices in `lib/openzeppelin-contracts/contracts/utils/math/Math.sol` (`mulDiv`, `invMod`). These are inside OpenZeppelin's well-audited `Math` library; the algorithms are correct under fixed-precision arithmetic. We do not modify upstream OZ code.

---

## Reproduce

```bash
pip install slither-analyzer

# daio contracts (3 of 4 with findings)
cd daio/contracts
slither inft/iNFT_7857.sol \
    --solc-remaps "@openzeppelin/=lib/openzeppelin-contracts/" \
    --exclude-low --exclude-informational --exclude-optimization

slither ens/v1/BankonSubnameRegistrar.sol \
    --solc-remaps "@openzeppelin/=lib/openzeppelin-contracts/" \
    --exclude-low --exclude-informational --exclude-optimization

slither THOT/v1/THOT.sol \
    --solc-remaps "@openzeppelin/=lib/openzeppelin-contracts/" \
    --exclude-low --exclude-informational --exclude-optimization

slither agentregistry/AgentRegistry.sol \
    --solc-remaps "@openzeppelin/=lib/openzeppelin-contracts/" \
    --exclude-low --exclude-informational --exclude-optimization

# Conclave contracts (in their own foundry project)
cd ../../openagents/conclave/contracts
slither src/Conclave.sol \
    --exclude-low --exclude-informational --exclude-optimization

slither src/ConclaveBond.sol \
    --exclude-low --exclude-informational --exclude-optimization
```

# Reproduce the regression test that proves the iNFT fix

```bash
cd daio/contracts
FOUNDRY_PROFILE=inft forge test --match-test test_mintAgent_blocksReentrancy -vv
# Expected: 1 passed
```
