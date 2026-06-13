// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl}   from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable}        from "@openzeppelin/contracts/utils/Pausable.sol";

import {IBankonPriceOracle, IBankonPaymentRouter} from "./interfaces/IBankon.sol";
import {IBankonX402Attestor}                       from "./interfaces/IBankonExtensions.sol";
import {IReverseRegistrar}                         from "./interfaces/IReverseRegistrar.sol";

/// @title  BankonOffchainRegistrar
/// @notice Phase 2.2 — issue `*.bankon.eth` subnames via CCIP-Read
///         (EIP-3668) instead of on-chain NameWrapper writes. ~$0.01/mint
///         amortized vs ~$2.50 on-chain. The trade-off: name records live
///         off-chain in the gateway's store (SQLite/IPFS) and clients
///         must hit the gateway during resolution. Same handshake the
///         Universal Resolver follows automatically, so end users see
///         nothing different.
///
///         Flow:
///           1. User calls `claim(parentNode, label, owner, payment)` with
///              ETH / x402-avm receipt as proof of payment.
///           2. Pricing comes from the same `BankonPriceOracle` Flow A uses.
///           3. We verify payment, route via the payment router, and emit
///              `OffchainSubnameClaimed` with the label + owner + an
///              IPFS-mirrored `recordsCid` for the gateway to consume.
///           4. The gateway's indexer watches the event, persists the
///              record in its SQLite store + Lighthouse-mirrored IPFS bundle,
///              and starts serving CCIP-Read queries for
///              `<label>.bankon.eth`.
///
///         No NameWrapper interaction — bankon.eth's resolver points at
///         `BankonOffchainResolver` for the wildcard subname surface; the
///         on-chain `BankonSubnameRegistrar` keeps serving names that
///         predate this contract.
contract BankonOffchainRegistrar is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");

    IBankonPriceOracle    public immutable priceOracle;
    IBankonPaymentRouter  public immutable paymentRouter;
    IBankonX402Attestor   public immutable x402Attestor;

    /// @dev parent under which subnames are issued — e.g. namehash("bankon.eth").
    bytes32 public immutable parentNode;

    /// @dev BANKON markup over the oracle price, in basis points. 1500 = 15%.
    uint16 public markupBps = 1500;

    /// @dev Tracks claimed labels under this parent so duplicate emissions
    ///      are caught early. (Gateway is source of truth, but a stale
    ///      indexer shouldn't accept a re-mint.)
    mapping(bytes32 => bool) public claimed; // keccak256(parent || labelhash)

    /// @notice Emitted on a successful CCIP-Read subname claim. The gateway
    ///         indexer watches this and writes the record to its store.
    /// @param parentNode  parent namehash (e.g. bankon.eth)
    /// @param labelhash   keccak256(bytes(label))
    /// @param label       the raw label string
    /// @param owner       claimant address (will resolve to this on addr(node))
    /// @param recordsCid  optional IPFS CID with extra records (avatar, text, etc.); empty if none
    /// @param paidUsd6    USD price paid (6 decimals), for the off-chain ledger
    event OffchainSubnameClaimed(
        bytes32 indexed parentNode,
        bytes32 indexed labelhash,
        string  label,
        address indexed owner,
        string  recordsCid,
        uint256 paidUsd6
    );

    error LabelEmpty();
    error LabelTooShort();
    error LabelAlreadyClaimed();
    error InsufficientPayment(uint256 paid, uint256 required);

    constructor(
        address admin,
        bytes32 _parentNode,
        IBankonPriceOracle _priceOracle,
        IBankonPaymentRouter _paymentRouter,
        IBankonX402Attestor _x402Attestor
    ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        parentNode    = _parentNode;
        priceOracle   = _priceOracle;
        paymentRouter = _paymentRouter;
        x402Attestor  = _x402Attestor;
    }

    // ── Admin ──────────────────────────────────────────────────────

    function setMarkupBps(uint16 newBps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newBps <= 5000, "markup > 50%");
        markupBps = newBps;
    }

    function pause()   external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }

    /// @notice ENSIP-15 contract-naming hook. Mirror of the helper on the
    ///         on-chain registrars (Phase 2.3). Sets the contract's primary
    ///         to e.g. "offchain.bankon.eth".
    function setReverseName(IReverseRegistrar rr, string calldata newName)
        external onlyRole(DEFAULT_ADMIN_ROLE) returns (bytes32)
    {
        return rr.setName(newName);
    }

    // ── Pricing ────────────────────────────────────────────────────

    /// @notice USD-6 price for a label. Mirrors BankonPriceOracle's tier
    ///         table. Duration is always 1 year for off-chain claims (the
    ///         gateway re-issues records yearly via internal renewals).
    function quote(string calldata label) external view returns (uint256 usd6) {
        return priceOracle.priceUSD(label, 1);
    }

    // ── Claim ──────────────────────────────────────────────────────

    /// @notice Mint an off-chain `<label>.bankon.eth` subname. Emits
    ///         OffchainSubnameClaimed; the gateway indexer persists.
    /// @param label       lowercase ASCII label, ≥3 chars
    /// @param owner       address that will resolve via the resolver's addr(node)
    /// @param recordsCid  optional IPFS CID with extra records (empty string disables)
    /// @param payment     payment-rail discriminator: empty = ETH (msg.value),
    ///                     leading byte 0x02 = x402-avm receipt encoded after
    function claim(
        string calldata label,
        address owner,
        string calldata recordsCid,
        bytes calldata payment
    )
        external
        payable
        nonReentrant
        whenNotPaused
    {
        if (bytes(label).length == 0) revert LabelEmpty();
        if (bytes(label).length < 3)  revert LabelTooShort();

        bytes32 labelhash = keccak256(bytes(label));
        bytes32 key = keccak256(abi.encodePacked(parentNode, labelhash));
        if (claimed[key]) revert LabelAlreadyClaimed();
        claimed[key] = true;

        uint256 usd6Owed = priceOracle.priceUSD(label, 1);

        // Payment rails — match Flow A semantics.
        if (payment.length > 0 && payment[0] == 0x02) {
            IBankonX402Attestor.X402Receipt memory r =
                abi.decode(payment[1:], (IBankonX402Attestor.X402Receipt));
            require(x402Attestor.verify(r), "x402 verify");
            require(r.usd6 >= usd6Owed, "x402 underpay");
        } else {
            // ETH rail. usd6Owed is in USDC base units; we don't convert to
            // ETH here because this contract is intended for the cheap-mint
            // path. Operators configure markupBps + ETH floor off-chain
            // via the gateway; on-chain we require *any* msg.value > 0 so
            // an empty TX is rejected. Tighten when a real ETH price feed
            // is wired in.
            if (msg.value == 0) revert InsufficientPayment(0, 1);
        }

        emit OffchainSubnameClaimed(parentNode, labelhash, label, owner, recordsCid, usd6Owed);
    }

    /// @notice Sweep ETH balance to the payment router. Mirrors the HIGH-3-
    ///         fix pattern from BankonEthRegistrar (fund-then-distribute).
    function sweep() external nonReentrant onlyRole(TREASURER_ROLE) {
        uint256 bal = address(this).balance;
        if (bal == 0) return;
        (bool ok,) = payable(address(paymentRouter)).call{value: bal}("");
        require(ok, "router fund failed");
        paymentRouter.distribute(address(0), bal);
    }

    receive() external payable {}
}
