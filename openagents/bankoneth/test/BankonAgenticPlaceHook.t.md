# BankonAgenticPlaceHook.t

> Smoke suite for `BankonAgenticPlaceHook` — exercises webhook configuration, lister role gating, and `AgenticPlaceListing` event emission.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonAgenticPlaceHook.t.sol`](./BankonAgenticPlaceHook.t.sol) | **Suite:** `BankonAgenticPlaceHookTest`

## Role in bankoneth

Exercises [`contracts/BankonAgenticPlaceHook.sol`](../contracts/BankonAgenticPlaceHook.sol) — the on-chain → off-chain bridge between BANKON registrar mints and the `agenticplace.pythai.net` listings indexer. The hook is a thin permissioned event emitter: registrars (whitelisted listers) call `list(...)`; an off-chain indexer subscribes to the event and POSTs to `webhookURL`.

This file is **smoke-only**: it covers the four critical surfaces (initial webhook, admin-rotated webhook, role gate, event shape) without fuzzing or end-to-end flows. The Mode-A iNFT integration with this hook is exercised in [`BankonEndToEnd.t.sol`](./BankonEndToEnd.t.sol).

Flow coverage: **Flow C** (AgenticPlace registry visibility).

## Fixture (`setUp()`)

1. Deploys `BankonAgenticPlaceHook(admin, "https://agenticplace.pythai.net/api/listings")`.
2. `vm.prank(admin)` → `hook.grantLister(lister)` — grants `LISTER_ROLE` to the test's `lister` EOA.

State seeded:
- `webhookURL` = the prod URL.
- `LISTER_ROLE` held by `admin` and `lister`.
- `DEFAULT_ADMIN_ROLE` held by `admin`.

## Test inventory

| Test | What it asserts | Notable cheatcodes |
|---|---|---|
| `test_InitialWebhook` | Constructor-seeded `webhookURL` returns the URL passed to the constructor. | view-only |
| `test_SetWebhookByAdmin` | Admin can rotate the webhook URL via `setWebhookURL(...)`. Read-back confirms storage update. | `vm.prank(admin)` |
| `test_OnlyListerCanList` | A non-lister (`makeAddr("stranger")`) calling `list(...)` reverts. Uses bare `vm.expectRevert()` (no selector check — covers any access-control revert shape). | `vm.prank(stranger)` + `vm.expectRevert()` |
| `test_ListEmitsEvent` | Lister calling `list(...)` emits exactly the `IBankonAgenticPlaceHook.AgenticPlaceListing` event with all six fields matching: parentNode `0xb017`, labelHash `keccak256("alice")`, tba `0xabba`, tokenId `42`, metadataURI `"ipfs://meta"`, author `0xfeed`. | `vm.prank(lister)` + `vm.expectEmit(true,true,true,true,address(hook))` |

## Coverage

**Covered (`BankonAgenticPlaceHook.sol`):**
- `constructor(admin, webhookURL)` — initial-state assertion.
- `setWebhookURL(string)` — admin-gated rotation.
- `list(bytes32,bytes32,address,uint256,string,address)` — happy path + access-control gate.
- `AgenticPlaceListing` event shape.

**Not covered (intentional):**
- `grantLister` / `revokeLister` semantics beyond happy path.
- Long-string URL handling (no fuzz over URL strings).
- Pause / emergency stop (the contract has none — listing is unconditional).
- The actual webhook delivery — that's off-chain; only the event reachability is on-chain-testable.

## Notable patterns

- `vm.expectEmit(true, true, true, true, address(hook))` — all four indexed checks enabled + data check + sender check. The test relies on the event topology matching field-by-field.
- Hash literals (`bytes32(uint256(0xb017))`, `address(uint160(0xabba))`) chosen for distinct, memorable bytes — eases debugging when an event mismatch is reported by Foundry.

## Known caveats

- Uses bare `vm.expectRevert()` in `test_OnlyListerCanList` — won't catch a regression where the contract starts reverting with a *different* (still unauthorized) reason. Strict version would use `IAccessControl.AccessControlUnauthorizedAccount.selector`.
- Doesn't fuzz `webhookURL` — long URLs / multibyte chars not exercised.
- No assertion on `lister` being able to *replace* the URL (only `admin` can, per the test).

## How to run

```bash
forge test --match-path test/BankonAgenticPlaceHook.t.sol -vvv
```

## See also

- [`../contracts/BankonAgenticPlaceHook.sol`](../contracts/BankonAgenticPlaceHook.sol) — the system under test.
- [`../contracts/interfaces/IBankonExtensions.sol`](../contracts/interfaces/IBankonExtensions.sol) — `IBankonAgenticPlaceHook` interface + event signature.
- [`BankonEndToEnd.t.sol`](./BankonEndToEnd.t.sol) — exercises this hook in the Mode-A iNFT pipeline.
- `docs/FLOWS.md` (Flow C) — AgenticPlace registry visibility flow.
