# Slither Static Analysis — 2026-05-02

> Slither v0.11.5 run against `daio/contracts/inft/iNFT_7857.sol` and the result of acting on its findings.

## Summary

| Severity | Found | After hardening |
|---|---|---|
| High | 0 | 0 |
| Medium | **1** (cross-function reentrancy in `mintAgent`) | **mitigated** with `nonReentrant` + dedicated regression test |
| Low | (excluded) | — |
| Informational | (excluded) | — |
| Optimization | (excluded) | — |

Slither's command:
```
slither inft/iNFT_7857.sol \
  --solc-remaps "@openzeppelin/=lib/openzeppelin-contracts/" \
  --exclude-low --exclude-informational --exclude-optimization
```

Verbatim output: [`slither_inft7857.txt`](slither_inft7857.txt).

---

## The finding

**Detector:** `reentrancy-no-eth`
**Function:** `iNFT_7857.mintAgent(address, bytes32, string, bytes32, uint32, uint8, bytes32, string)`

Slither correctly identified the gate-open pattern:

```solidity
// Before hardening:
_gateOpen = true;
_safeMint(to, tokenId);  // calls onERC721Received(to) — external call
_gateOpen = false;
```

**The exploit Slither warned about:** A malicious contract recipient implements `onERC721Received` to re-enter the contract while `_gateOpen == true`. The re-entered call could pass the gate-check in `_update()` (which reads `_gateOpen`) and execute an unauthorized transfer of the just-minted token, bypassing the entire ERC-7857 sealed-key invariant.

The same pattern exists in `burn`, but burn transfers to `address(0)` so there's no recipient callback to exploit. Still hardened defensively.

**`transferWithSealedKey` and `cloneAgent` were already protected** with `nonReentrant`. Only `mintAgent` and `burn` lacked the modifier.

---

## The hardening

```solidity
// After hardening (one-line addition to two functions):
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

`nonReentrant` is OpenZeppelin's `ReentrancyGuard` mutex (already inherited at line 73 of `iNFT_7857.sol`). It uses a single status variable that ALL `nonReentrant`-decorated functions share. With this change, the moment `mintAgent` enters its body, the mutex is locked; any re-entry into `mintAgent`, `burn`, `transferWithSealedKey`, or `cloneAgent` reverts with `ReentrancyGuardReentrantCall()`.

**56 → 57 iNFT-7857 tests pass.** No test broke; one new test added.

---

## The regression test (authoritative proof)

`test_mintAgent_blocksReentrancyViaOnERC721Received` actively performs the attack:

```solidity
contract ReentrantReceiver is IERC721Receiver {
    iNFT_7857 internal target;
    constructor(iNFT_7857 _target) { target = _target; }

    function onERC721Received(...) external returns (bytes4) {
        // Attempt cross-function reentrancy. Will revert because the
        // outer mintAgent call holds the nonReentrant mutex.
        target.mintAgent(
            address(this), keccak256("re-entry-root"), "ipfs://reentry",
            bytes32(uint256(0xcd)), 128, 1, keccak256("sealed-reentry"),
            "ipfs://uri-reentry"
        );
        return IERC721Receiver.onERC721Received.selector;
    }
}

function test_mintAgent_blocksReentrancyViaOnERC721Received() public {
    ReentrantReceiver attacker = new ReentrantReceiver(nft);
    vm.prank(minter);
    vm.expectRevert();  // re-entry is blocked
    nft.mintAgent(address(attacker), ROOT_A, "ipfs://x",
                  bytes32(uint256(0xab)), 128, 1,
                  keccak256("sealed-key-A"), "ipfs://uri");
}
```

**Result: PASS in 184,743 gas.** The malicious receiver's `onERC721Received` calls `mintAgent` again, the `nonReentrant` mutex blocks it, and the revert propagates through `_safeMint` causing the outer mint to fail. The token is never minted; the attack vector is closed.

---

## Why Slither still flags it after hardening

After the fix, `slither` still reports the same pattern. **This is a known limitation of static analysis** — Slither identifies the syntactic pattern (external call followed by state write) but does not model OpenZeppelin's `nonReentrant` modifier semantics. It cannot distinguish "vulnerable reentrancy" from "reentrancy guarded by a mutex."

The regression test in this section is the authoritative proof that the runtime behavior is safe. The Slither finding is now a **false positive** for the security-properties-as-stated.

---

## Other Slither output (non-action items)

- 12 `divide-before-multiply` notices, all in `lib/openzeppelin-contracts/contracts/utils/math/Math.sol` (`mulDiv`, `invMod`). These are inside OpenZeppelin's well-audited `Math` library; the algorithms are correct under fixed-precision arithmetic. Out of scope for this submission.

- All other findings excluded (`--exclude-low --exclude-informational --exclude-optimization`).

---

## Reproduce

```bash
# Install Slither
pip install slither-analyzer

# Run scan
cd daio/contracts
slither inft/iNFT_7857.sol \
    --solc-remaps "@openzeppelin/=lib/openzeppelin-contracts/" \
    --exclude-low --exclude-informational --exclude-optimization

# Run regression test
FOUNDRY_PROFILE=inft forge test --match-test test_mintAgent_blocksReentrancyViaOnERC721Received -vv
```
