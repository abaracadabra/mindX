// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title  IPay2Play — interfaces for the BANKON pay-to-play rails.
/// @notice Three concerns, kept separate per the bankoneth modular doctrine:
///         a service catalogue (BANKON-as-a-Service collections), an identity
///         entitlement ledger, and the payment router that binds them.
///         See `pay2play/README.md`.

/// @notice The BANKON-as-a-Service catalogue. Each entry is one purchasable
///         service (identity.register, hosting, allchain access, …). A service
///         confers a `tier` and a time-boxed (or permanent) entitlement.
interface IBankonServiceRegistry {
    struct Service {
        address beneficiary; // receives the net payment (the BANKON service treasury)
        address asset;       // address(0) = native coin; otherwise an ERC-20 (e.g. USDC)
        uint256 price;       // price in `asset` base units
        uint64  period;      // entitlement duration in seconds; 0 = one-time / permanent
        uint8   tier;        // identity tier conferred on purchase (0..255)
        bool    active;      // gate: only active services are payable
        string  name;        // human label, e.g. "identity.register"
    }

    function getService(bytes32 id) external view returns (Service memory);
    function isActive(bytes32 id) external view returns (bool);

    event ServiceSet(
        bytes32 indexed id,
        address beneficiary,
        address asset,
        uint256 price,
        uint64  period,
        uint8   tier,
        bool    active,
        string  name
    );
}

/// @notice Identity-management ledger: which wallet holds which entitlement,
///         until when, and the highest tier it has been granted. The wallet
///         address IS the identity; access is proven by holding the entitlement.
interface IBankonEntitlement {
    function grant(address user, bytes32 service, uint8 tier, uint64 until) external;
    function hasAccess(address user, bytes32 service) external view returns (bool);
    function expiryOf(address user, bytes32 service) external view returns (uint64);
    function tierOf(address user) external view returns (uint8);

    event EntitlementGranted(address indexed user, bytes32 indexed service, uint8 tier, uint64 until);
}

/// @notice The pay-to-play router: pay for a service, take a fair/nominal fee
///         (set in this contract), forward the net to the service beneficiary,
///         and grant the payer (or a signature-proven identity) the entitlement.
interface IBANKONPaymentRouter {
    function play(bytes32 serviceId) external payable;
    function playFor(bytes32 serviceId, address user) external payable;
    function playWithSig(bytes32 serviceId, address user, bytes calldata sig) external payable;

    event Played(
        bytes32 indexed serviceId,
        address indexed payer,
        address indexed user,
        address asset,
        uint256 paid,
        uint256 fee,
        uint64  until
    );
    event FeeConfigUpdated(uint16 feeBps, address feeRecipient);
}

/// @notice ARC-chain USDC x402 settlement: a facilitator attests that `payer`
///         settled `amount` USDC on the ARC chain for `serviceId`; the layer
///         grants the entitlement without moving tokens (settled on ARC).
interface IPay2PlayArcSettlement {
    struct ArcReceipt {
        bytes32 serviceId;  // the pay2play service paid for
        address payer;      // the identity that paid USDC on ARC → receives the entitlement
        address asset;      // USDC token on ARC (must equal arcUsdc)
        uint256 amount;     // USDC base units (6dp) settled on ARC (must cover service price)
        uint64  srcChainId; // ARC chain id (must equal arcChainId)
        uint64  nonce;      // strictly monotonic per facilitator (replay guard)
        uint64  deadline;   // receipt expiry (unix seconds)
    }

    function settle(ArcReceipt calldata r, address facilitator, bytes calldata sig)
        external
        returns (bytes32 digest, uint64 until);

    event ArcSettled(
        bytes32 indexed digest,
        bytes32 indexed serviceId,
        address indexed payer,
        address asset,
        uint256 amount,
        uint64  srcChainId,
        uint64  until,
        address facilitator
    );
    event FacilitatorSet(address indexed facilitator, bool allowed);
    event ArcConfigUpdated(uint64 arcChainId, address arcUsdc);
}
