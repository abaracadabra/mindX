// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl}     from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard}   from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {EIP712}            from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignatureChecker}  from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";

import {
    IPay2PlayArcSettlement,
    IBankonServiceRegistry,
    IBankonEntitlement
} from "./interfaces/IPay2Play.sol";

/// @title  Pay2PlayArcSettlement — ARC-chain USDC x402 settlement layer.
/// @author cypherpunk2048
/// @notice The most off-chain pay-to-play rail: the customer pays **USDC on the
///         ARC chain** (Circle's stablecoin L1) through an x402 facilitator. The
///         facilitator returns an EIP-712-signed receipt attesting the
///         settlement; this contract verifies it and grants the pay2play
///         entitlement — without moving any tokens here (settlement already
///         happened on ARC). Same shape as the Algorand x402-avm rail
///         (`contracts/BankonX402Attestor.sol`), aimed at pay2play instead of
///         registration.
///
///         Trust is bounded by the facilitator's signing key, so:
///           - facilitators are an admin-managed allowlist of EOAs / 1271 safes,
///           - the per-facilitator nonce is strictly monotonic (replay layer 1),
///           - each receipt digest is spent-once (replay layer 2),
///           - the receipt must be for the configured ARC chainId + USDC asset,
///           - the attested amount must cover the service price.
///
///         Wire-up: grant this contract `GRANTER_ROLE` on {BankonEntitlement}
///         post-deploy, and register the facilitator key(s). The admin guarding
///         `setFacilitator` should be a multisig in production.
contract Pay2PlayArcSettlement is AccessControl, ReentrancyGuard, EIP712, IPay2PlayArcSettlement {
    bytes32 public constant FACILITATOR_ADMIN_ROLE = keccak256("FACILITATOR_ADMIN_ROLE");

    IBankonServiceRegistry public immutable registry;
    IBankonEntitlement     public immutable entitlement;

    /// ARC settlement config (settable so the rail can re-point if Circle ARC
    /// finalises ids/addresses).
    uint64  public arcChainId;   // the ARC chain id the receipt must reference
    address public arcUsdc;      // USDC token address on ARC the receipt must reference

    mapping(address => bool)   public isFacilitator; // allowlisted attestor keys
    mapping(address => uint64) public lastNonce;      // monotonic per facilitator
    mapping(bytes32 => bool)   public settled;        // receipt-digest spent-set

    bytes32 private constant RECEIPT_TYPEHASH = keccak256(
        "ArcReceipt(bytes32 serviceId,address payer,address asset,uint256 amount,uint64 srcChainId,uint64 nonce,uint64 deadline)"
    );

    error UnknownFacilitator(address f);
    error ReceiptExpired(uint64 deadline);
    error WrongChain(uint64 got, uint64 want);
    error WrongAsset(address got, address want);
    error NonceNotMonotonic(uint64 got, uint64 last);
    error ServiceInactive(bytes32 id);
    error Underpaid(uint256 amount, uint256 price);
    error AlreadySettled(bytes32 digest);
    error InvalidSignature();
    error ZeroAddress();

    constructor(
        address admin,
        IBankonServiceRegistry registry_,
        IBankonEntitlement entitlement_,
        uint64 arcChainId_,
        address arcUsdc_
    ) EIP712("Pay2PlayArcSettlement", "1") {
        if (
            admin == address(0) ||
            address(registry_) == address(0) ||
            address(entitlement_) == address(0) ||
            arcUsdc_ == address(0)
        ) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(FACILITATOR_ADMIN_ROLE, admin);
        registry    = registry_;
        entitlement = entitlement_;
        arcChainId  = arcChainId_;
        arcUsdc     = arcUsdc_;
    }

    /* ───── Settlement ───────────────────────────────────────────── */

    /// @notice Verify a facilitator-signed ARC USDC receipt and grant the
    ///         pay2play entitlement to `r.payer`. Idempotent and replay-safe.
    /// @param r           The ARC settlement receipt (USDC paid on ARC).
    /// @param facilitator The allowlisted key that signed `r`.
    /// @param sig         EIP-712 signature over `r` by `facilitator`
    ///                    (EOA ECDSA or ERC-1271 safe).
    function settle(ArcReceipt calldata r, address facilitator, bytes calldata sig)
        external
        nonReentrant
        returns (bytes32 digest, uint64 until)
    {
        if (!isFacilitator[facilitator]) revert UnknownFacilitator(facilitator);
        if (block.timestamp > r.deadline) revert ReceiptExpired(r.deadline);
        if (r.srcChainId != arcChainId) revert WrongChain(r.srcChainId, arcChainId);
        if (r.asset != arcUsdc) revert WrongAsset(r.asset, arcUsdc);
        if (r.nonce <= lastNonce[facilitator]) revert NonceNotMonotonic(r.nonce, lastNonce[facilitator]);

        IBankonServiceRegistry.Service memory s = registry.getService(r.serviceId);
        if (!s.active) revert ServiceInactive(r.serviceId);
        if (r.amount < s.price) revert Underpaid(r.amount, s.price);

        digest = _hashTypedDataV4(
            keccak256(abi.encode(
                RECEIPT_TYPEHASH,
                r.serviceId, r.payer, r.asset, r.amount, r.srcChainId, r.nonce, r.deadline
            ))
        );
        if (settled[digest]) revert AlreadySettled(digest);
        if (!SignatureChecker.isValidSignatureNow(facilitator, digest, sig)) revert InvalidSignature();

        settled[digest] = true;
        lastNonce[facilitator] = r.nonce;

        until = s.period == 0 ? type(uint64).max : uint64(block.timestamp) + s.period;
        entitlement.grant(r.payer, r.serviceId, s.tier, until);

        emit ArcSettled(digest, r.serviceId, r.payer, r.asset, r.amount, r.srcChainId, until, facilitator);
    }

    /// @notice The EIP-712 domain separator, for off-chain receipt signing.
    function domainSeparator() external view returns (bytes32) {
        return _domainSeparatorV4();
    }

    /* ───── Admin ────────────────────────────────────────────────── */

    function setFacilitator(address facilitator, bool allowed)
        external
        onlyRole(FACILITATOR_ADMIN_ROLE)
    {
        if (facilitator == address(0)) revert ZeroAddress();
        isFacilitator[facilitator] = allowed;
        emit FacilitatorSet(facilitator, allowed);
    }

    /// @notice Re-point the ARC source chain id / USDC asset the rail accepts.
    function setArcConfig(uint64 arcChainId_, address arcUsdc_)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (arcUsdc_ == address(0)) revert ZeroAddress();
        arcChainId = arcChainId_;
        arcUsdc    = arcUsdc_;
        emit ArcConfigUpdated(arcChainId_, arcUsdc_);
    }
}
