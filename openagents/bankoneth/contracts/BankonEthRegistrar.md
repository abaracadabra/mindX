# BankonEthRegistrar

> Flow B — wraps the canonical ENS ETHRegistrarController commit-reveal flow so customers buy `newdomain.eth` end-to-end through bankoneth with tri-rail payment.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonEthRegistrar.sol`](./BankonEthRegistrar.sol)

## Role in bankoneth

`BankonEthRegistrar` is the **Flow B** entry point: a customer wants to buy a top-level `.eth` 2LD (e.g. `newdomain.eth`) without touching the ENS contracts directly. The registrar wraps the canonical ENS `ETHRegistrarController` commit-reveal pattern (60-second min wait, max-age expiry) and adds:

- **Tri-rail payment**: rail byte `0x00` = ETH (msg.value), `0x01` = USDC permit (handled upstream by `BankonPaymentRouter`), `0x02` = x402-avm receipt (Algorand USDC settlement, verified by `BankonX402Attestor`).
- **Markup**: `markupBps` (default 1500 = 15%) on top of the ENS base+premium price, accumulated on this contract and swept to `BankonPaymentRouter.distribute(address(0), bal)` by a `TREASURER_ROLE` operator via `sweep()`.
- **Deterministic salt**: the UI drives the 60-second wait without round-trip state because the commit-reveal `secret` is server-managed (`keccak256(label || owner || nonce)` per the doc).

The customer goes commit → wait → reveal, all via this contract. Bankoneth holds the markup until sweep, ENS receives the base+premium directly from `controller.register{value: weiOwed}`. The original Flow B is for *new* `.eth` purchases; `BankonSubnameRegistrar` handles agent subnames under `bankon.eth` (Flow A), and `BankonDomainHosting` handles enrolled external `.eth` parents (Flow C).

## Inheritance

- `IBankonEthRegistrar` — interface in [`interfaces/IBankonExtensions.sol`](./interfaces/IBankonExtensions.sol) (`CommitParams` struct, `Committed`/`Registered` events, `commit/reveal/quote` functions).
- `AccessControl` — `DEFAULT_ADMIN_ROLE` (pause + markup), `TREASURER_ROLE` (sweep).
- `ReentrancyGuard` — `reveal` and `sweep` are `nonReentrant`.
- `Pausable` — `commit` and `reveal` honor `whenNotPaused`.

Also defines `IETHRegistrarController` inline (subset of the canonical ENS controller — mainnet `0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547`).

## Constructor

| arg              | type                       | purpose                                                                |
|------------------|----------------------------|------------------------------------------------------------------------|
| `admin`          | `address`                  | Granted `DEFAULT_ADMIN_ROLE`.                                          |
| `_controller`    | `IETHRegistrarController`  | Canonical ENS controller (`0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547` on mainnet). |
| `_priceOracle`   | `IBankonPriceOracle`       | USD quote source.                                                      |
| `_paymentRouter` | `IBankonPaymentRouter`     | Markup recipient (sweep destination).                                  |
| `_x402Attestor`  | `IBankonX402Attestor`      | Verifies x402-avm receipts (rail `0x02`).                              |

Roles granted at construction: `DEFAULT_ADMIN_ROLE` → `admin`. **`TREASURER_ROLE` is not granted at construction** — must be explicitly granted before `sweep` can be called.

## Storage layout

| name              | type                              | purpose                                                            | mutable? |
|-------------------|-----------------------------------|--------------------------------------------------------------------|----------|
| `TREASURER_ROLE`  | `bytes32 constant`                | `keccak256("TREASURER_ROLE")`.                                     | no       |
| `controller`      | `IETHRegistrarController` immutable | ENS controller binding.                                          | no       |
| `priceOracle`     | `IBankonPriceOracle` immutable    | USD oracle binding.                                                | no       |
| `paymentRouter`   | `IBankonPaymentRouter` immutable  | Markup router binding.                                             | no       |
| `x402Attestor`    | `IBankonX402Attestor` immutable   | x402 verifier binding.                                             | no       |
| `committedAt`     | `mapping(bytes32 => uint256)` public | Commitment-hash → unix timestamp of commit.                     | yes (commit/reveal) |
| `markupBps`       | `uint16` public                   | Markup over ENS base price (default `1500` = 15%).                 | yes (admin)|

## Roles

| Role                 | keccak256                              | Who holds                | What they can do                                                     |
|----------------------|----------------------------------------|---------------------------|----------------------------------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin default                   | `admin` (constructor)     | `setMarkupBps`, `pause`, `unpause`.                                  |
| `TREASURER_ROLE`     | `keccak256("TREASURER_ROLE")`          | (not granted by constructor — must be explicitly granted) | `sweep` markup balance to `paymentRouter`. |

## Events

### `Committed(bytes32 indexed commitment, address indexed payer, address indexed owner)` (from interface)

Emitted on `commit(...)`. `payer = msg.sender`, `owner` is the final registrant per `CommitParams.owner`.

### `Registered(string label, address indexed owner, uint256 cost, address asset)` (from interface)

Emitted on `reveal(...)` after `controller.register` succeeds. `cost = weiOwed` (ENS base+premium+markup in wei), `asset = address(0)` (always ETH at the registrar level, even when off-chain rail was USDC).

## Errors

### `LabelInvalid()`

Reverted when `controller.valid(label) == false`. Caller picked an unregisterable name.

### `LabelUnavailable()`

Reverted on `commit` when `controller.available(label) == false`.

### `CommitmentNotFound()`

Reverted on `reveal` when no `committedAt[commitment]` entry exists. Either the caller never committed, or the commitment was already revealed (deleted).

### `CommitmentTooYoung()`

Reverted on `reveal` when `block.timestamp < ts + controller.minCommitmentAge()`. Caller revealed before the 60-second window.

### `CommitmentTooOld()`

Reverted on `reveal` when `block.timestamp > ts + controller.maxCommitmentAge()`. Caller waited too long; must `commit` again.

### `InsufficientPayment(uint256 paid, uint256 required)`

Reverted on `reveal` when `msg.value < weiOwed` on the ETH rail.

## External / public API

### `setMarkupBps(uint16 newBps) external`

Updates `markupBps`. Reverts `"markup > 50%"` if `newBps > 5000`. Access: `DEFAULT_ADMIN_ROLE`.

### `pause() external` / `unpause() external`

Halt/resume `commit` and `reveal`. Access: `DEFAULT_ADMIN_ROLE`.

### `quote(string calldata label, uint256 durationYears) external view returns (uint256 wei_, uint256 usd6)`

Returns dual-denominated price: `wei_` = `(base + premium) * (1 + markupBps/10000)` from the controller's `rentPrice`, `usd6` = `priceOracle.priceUSD(label, durationYears)`. Reverts `LabelInvalid` if the label is invalid.

### `commit(CommitParams calldata p) external returns (bytes32 commitment)`

Step 1 of the canonical ENS commit-reveal:
- Validates label is valid and available.
- Computes commitment via `controller.makeCommitment(...)`.
- Calls `controller.commit(commitment)`.
- Records `committedAt[commitment] = block.timestamp`.
- Emits `Committed`.

Access: anyone. Modifier: `whenNotPaused`.

### `reveal(CommitParams calldata p, bytes calldata payment) external payable`

Step 2 (after the controller's min-commitment-age):
1. Recomputes the commitment with the same params (must match the committed hash).
2. Reverts `CommitmentNotFound` / `CommitmentTooYoung` / `CommitmentTooOld`.
3. Calls `quote(p.label, p.durationYears)` to derive `weiOwed`, `usd6Owed`.
4. **Payment rail dispatch** (based on `payment[0]`):
   - `0x02` (x402-avm): `abi.decode(payment[1:])` into `X402Receipt`; `x402Attestor.verify(r)`; require `r.usd6 >= usd6Owed` and `msg.value >= weiOwed` (a relayer is expected to supply the ETH).
   - Default (no payment bytes, or `0x00`): require `msg.value >= weiOwed`.
5. Deletes `committedAt[commitment]`.
6. Calls `controller.register{value: weiOwed}(...)` — the ENS controller consumes `weiOwed` for the base+premium plus the markup. **NB**: the markup is sent to the controller as part of `weiOwed`, then the controller will refund any overpayment to *this* contract (per ENS controller semantics). The accumulated balance is what `sweep` later distributes.
7. Refunds any `msg.value - weiOwed` overpayment to `msg.sender` via a raw `call`.
8. Emits `Registered(p.label, p.owner, weiOwed, address(0))`.

Access: anyone (typically a relayer or the customer). Modifiers: `nonReentrant`, `whenNotPaused`.

### `sweep() external`

Forwards the entire contract ETH balance to the payment router via `paymentRouter.distribute(address(0), bal)`. Access: `TREASURER_ROLE`. `nonReentrant`. Does nothing if balance is zero.

### `receive() external payable`

Accepts plain ETH (used by the ENS controller refunding overpayment and by relayer top-ups).

## Internal helpers

—

## Invariants

- `committedAt[commitment] == 0` iff the commitment is unrevealed AND not committed (or has been revealed).
- A successful `reveal` always deletes the entry, preventing replay of the same commit-reveal pair.
- The contract holds only ETH (no ERC-20 logic at this layer).
- `markupBps <= 5000` enforced on every `setMarkupBps`.
- Contract is `Pausable` — `commit` and `reveal` are gated; `sweep` is NOT gated by pause (admin can still rescue funds during a pause).
- Contract has `receive()`; no `fallback()`.

## Security considerations

- **Reentrancy**: `reveal` is `nonReentrant`. `controller.register{value:}(...)` is an external call to a trusted canonical contract; reentrancy through it is not a concern in normal operation, but the guard remains for defense in depth. `sweep` is also `nonReentrant`.
- **Front-running of commit**: the commit-reveal pattern prevents name-snipe front-running (per ENS design). The `secret` should be high-entropy server-side per the doc.
- **x402 rail trust**: x402-avm depends on the attestor's facilitator key. See [`BankonX402Attestor.md`](./BankonX402Attestor.md).
- **Relayer-funded ETH on x402 rail**: when rail = `0x02`, the relayer must supply `msg.value >= weiOwed`. The attestor verifies USD-side; the relayer is trusted to front the ETH for the controller. Mismatch handling: explicit `"relayer underfunded"` require.
- **Markup accounting**: the markup is part of `weiOwed` sent to the controller. The ENS controller refunds excess to `msg.sender` (which is this contract, not the original caller) — that's how the markup ends up here. Any refund the controller makes goes via `receive()`. The actual marked-up portion remaining in this contract = `weiOwed - (base + premium)`.
- **Refund path**: any over-`weiOwed` `msg.value` is refunded directly to `msg.sender` (the relayer or caller). Refund failure reverts the whole reveal — this is intentional (better to fail than silently drop ETH).
- **Pause behavior**: pausing halts `commit` and `reveal`, allowing live commit-reveal windows to expire harmlessly. `sweep` is intentionally not paused.
- **No price check on x402 underpay**: the require `r.usd6 >= usd6Owed` ensures the off-chain USD settlement matches the on-chain quote. Don't change `markupBps` between the user's quote and reveal or the USD might desync.
- **`secret` storage**: not stored on-chain; only the commitment hash is. Forgetting the secret = lost commitment (must re-commit and pay another minCommitmentAge wait).

## Integration patterns

- Frontend (`@bankoneth/core`, `@bankoneth/ui`) flow:
  1. Call `quote(label, years)` for display.
  2. Build `CommitParams` with deterministic `secret = keccak256(label || owner || nonce)`.
  3. Call `commit(p)` — wait ≥ `controller.minCommitmentAge()` (60s on mainnet).
  4. Build `payment` payload (rail byte + optional x402 receipt encoding).
  5. Call `reveal(p, payment)` with the right `msg.value`.
- Deployed via [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) line 99: `new BankonEthRegistrar(treasury, controller, oracle, router, attestor)`. Granted `LISTER_ROLE` on `BankonAgenticPlaceHook` and `CONSUMER_ROLE` on `BankonX402Attestor` post-deploy (lines 120 + 123).
- Sweep cadence: operator runs `sweep()` periodically (e.g. daily) — the router then 5-way splits the markup.

## Known gotchas

- `committedAt` survives across `reveal` failures other than success — but successful reveal deletes it. A reverted reveal can be retried with the same `CommitParams`.
- The contract uses `this.quote(...)` (external call to self) inside `reveal` (line 181). That works under Solidity 0.8.x but costs an extra CALL — a future optimization is to inline `quote`.
- The markup is in **basis points of the ENS base+premium price**, not of the USD oracle price. The two can diverge if the ENS premium decay schedule differs from the oracle's flat-tier model.
- `sweep` does NOT need to be called before pausing — the funds are safely held in the contract.
- No revocation path for `committedAt`; if the controller's commitment goes stale (`maxCommitmentAge`), this contract still keeps the storage slot until a fresh `commit` overwrites it (commitment hashes are unique per param set so this is largely cosmetic — but worth knowing for storage-cost accounting).
- The `Registered` event always reports `asset = address(0)` (ETH), even when settlement was via x402-avm USDC. Use the x402 attestor's `ReceiptConsumed` event to reconstruct the original asset.

## See also

- [`interfaces/IBankonExtensions.md`](./interfaces/IBankonExtensions.md) — `IBankonEthRegistrar` interface + `CommitParams`.
- [`BankonPriceOracle.md`](./BankonPriceOracle.md) — supplies USD quote.
- [`BankonX402Attestor.md`](./BankonX402Attestor.md) — verifies rail `0x02` receipts.
- [`BankonPaymentRouter.md`](./BankonPaymentRouter.md) — receives markup on `sweep`.
- [`BankonAgenticPlaceHook.md`](./BankonAgenticPlaceHook.md) — may receive a `list(...)` call post-mint (optional).
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — Flow A counterpart (`*.bankon.eth` agent subnames).
- [`BankonDomainHosting.md`](./BankonDomainHosting.md) — Flow C counterpart (enrolled external parents).
