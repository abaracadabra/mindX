// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl}   from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable}        from "@openzeppelin/contracts/utils/Pausable.sol";

import {IBankonDomainHosting, IBankonX402Attestor} from "./interfaces/IBankonExtensions.sol";
import {INameWrapper, IPublicResolver, IBankonPaymentRouter} from "./interfaces/IBankon.sol";

/// @title  BankonDomainHosting — Flow C: subdomain-minting-as-a-service.
/// @notice External `.eth` holders enroll their domain (wrapping it into ENS
///         NameWrapper if not already, burning `CANNOT_UNWRAP` for the
///         parent-lock requirement that the docs call out) and bankoneth
///         becomes the issuance contract for that parent. The original owner
///         sets per-parent pricing + fuse policy + a parent-owner payout
///         share in basis points; the rest of the revenue goes through the
///         standard BankonPaymentRouter 5-bucket split.
///
/// @dev    Enrollment requires the parent owner to have already approved this
///         contract as an operator on the NameWrapper:
///         `NameWrapper.setApprovalForAll(thisAddress, true)` before calling
///         `enroll()`. Without that approval, `issue()` cannot mint subnames.
contract BankonDomainHosting is
    IBankonDomainHosting,
    AccessControl,
    ReentrancyGuard,
    Pausable
{
    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");

    /// @dev ENS NameWrapper fuse bits — same as upstream.
    uint32 public constant CANNOT_UNWRAP = 1;
    /// @dev Sane default for parent-lock subnames.
    uint32 public constant PARENT_CANNOT_CONTROL = 1 << 16;
    uint32 public constant CAN_EXTEND_EXPIRY     = 1 << 18;
    uint32 public constant DEFAULT_CHILD_FUSES   =
        PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CAN_EXTEND_EXPIRY;

    INameWrapper          public immutable nameWrapper;
    IPublicResolver       public immutable resolver;
    IBankonPaymentRouter  public immutable paymentRouter;
    IBankonX402Attestor   public immutable x402Attestor;

    /// @dev bankoneth's share in basis points (10000 = 100%). Defaults to 2500 (25%).
    ///      Parent owner gets `(10000 - hostShareBps)` of (price - protocol cut).
    uint16 public hostShareBps = 2500;

    mapping(bytes32 => EnrolledParent) private _parents;

    error ParentNotWrapped();
    error CannotUnwrapNotBurned();
    error NotParentOwner();
    error ParentNotEnrolled();
    error AlreadyEnrolled();
    error LabelTaken();
    error InsufficientPayment(uint256 paid, uint256 required);

    constructor(
        address admin,
        INameWrapper _nameWrapper,
        IPublicResolver _resolver,
        IBankonPaymentRouter _paymentRouter,
        IBankonX402Attestor _x402Attestor
    ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        nameWrapper   = _nameWrapper;
        resolver      = _resolver;
        paymentRouter = _paymentRouter;
        x402Attestor  = _x402Attestor;
    }

    // ── Admin ──────────────────────────────────────────────────────

    function setHostShareBps(uint16 newBps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newBps <= 5000, "host share > 50%");
        hostShareBps = newBps;
    }

    function pause()   external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }

    // ── Enrollment ─────────────────────────────────────────────────

    /// @inheritdoc IBankonDomainHosting
    function enroll(
        bytes32 parentNode,
        uint256 pricePerLabel6,
        uint256 priceEthWei,
        uint32  childFuses,
        uint64  defaultExpiry,
        uint16  ownerShareBps
    ) external override whenNotPaused {
        if (_parents[parentNode].active) revert AlreadyEnrolled();

        // Must be wrapped and CANNOT_UNWRAP must be burned — the parent-lock
        // requirement from the ENS docs. Without it, the parent could rug
        // existing subnames.
        if (!nameWrapper.isWrapped(parentNode)) revert ParentNotWrapped();
        (address owner, uint32 fuses,) = nameWrapper.getData(uint256(parentNode));
        if (owner != msg.sender) revert NotParentOwner();
        if ((fuses & CANNOT_UNWRAP) == 0) revert CannotUnwrapNotBurned();

        require(ownerShareBps <= 10_000 - hostShareBps, "owner share too high");

        _parents[parentNode] = EnrolledParent({
            parentOwner:     msg.sender,
            pricePerLabel6:  pricePerLabel6,
            priceEthWei:     priceEthWei,
            // No more uint16 truncation — DEFAULT_CHILD_FUSES has bits at
            // positions 0, 16 and 18 (CANNOT_UNWRAP | PARENT_CANNOT_CONTROL |
            // CAN_EXTEND_EXPIRY). Casting to uint16 silently lost the latter
            // two and broke the parent-lock + extend-expiry guarantees the
            // doc promises. Storage + arg are now uint32.
            childFuses:      childFuses == 0 ? DEFAULT_CHILD_FUSES : childFuses,
            defaultExpiry:   defaultExpiry,
            ownerShareBps:   ownerShareBps,
            active:          true
        });

        emit ParentEnrolled(parentNode, msg.sender, ownerShareBps);
    }

    /// @inheritdoc IBankonDomainHosting
    function setPrices(bytes32 parentNode, uint256 pricePerLabel6, uint256 priceEthWei)
        external override
    {
        EnrolledParent storage p = _parents[parentNode];
        if (!p.active) revert ParentNotEnrolled();
        if (p.parentOwner != msg.sender) revert NotParentOwner();
        p.pricePerLabel6 = pricePerLabel6;
        p.priceEthWei    = priceEthWei;
    }

    /// @inheritdoc IBankonDomainHosting
    function disenroll(bytes32 parentNode) external override {
        EnrolledParent storage p = _parents[parentNode];
        if (!p.active) revert ParentNotEnrolled();
        if (p.parentOwner != msg.sender) revert NotParentOwner();
        p.active = false;
    }

    // ── Issue ──────────────────────────────────────────────────────

    /// @inheritdoc IBankonDomainHosting
    function issue(
        bytes32 parentNode,
        string calldata label,
        address owner,
        bytes calldata payment
    ) external payable override nonReentrant whenNotPaused returns (bytes32 subnameNode) {
        EnrolledParent memory p = _parents[parentNode];
        if (!p.active) revert ParentNotEnrolled();

        // Verify payment (ETH or x402-avm).
        if (payment.length > 0 && payment[0] == 0x02) {
            IBankonX402Attestor.X402Receipt memory r = abi.decode(payment[1:], (IBankonX402Attestor.X402Receipt));
            require(x402Attestor.verify(r), "x402 verify");
            require(r.usd6 >= p.pricePerLabel6, "x402 underpay");
        } else {
            // ETH rail — must meet the per-parent `priceEthWei` floor that the
            // parent owner set at enrollment (and can update via setPrices()).
            // priceEthWei=0 disables the ETH rail for this parent, forcing
            // x402-avm.
            if (p.priceEthWei == 0) revert InsufficientPayment(msg.value, 0);
            if (msg.value < p.priceEthWei) revert InsufficientPayment(msg.value, p.priceEthWei);
        }

        // Compute label node and check availability via name wrapper getData.
        bytes32 labelhash = keccak256(bytes(label));
        subnameNode = keccak256(abi.encodePacked(parentNode, labelhash));
        (address existingOwner,,) = nameWrapper.getData(uint256(subnameNode));
        if (existingOwner != address(0)) revert LabelTaken();

        nameWrapper.setSubnodeRecord(
            parentNode,
            label,
            owner,
            address(resolver),
            0,
            p.childFuses,         // already uint32 — no truncation
            p.defaultExpiry
        );

        // Split revenue:
        //   - bankoneth keeps `hostShareBps` of the ETH/USDC
        //   - parent owner keeps `ownerShareBps`
        //   - remainder goes to the payment router for the standard 5-bucket
        if (msg.value > 0) {
            uint256 ownerCut = (msg.value * p.ownerShareBps) / 10_000;
            uint256 routerCut = msg.value - ownerCut;
            if (ownerCut > 0) {
                (bool ok,) = payable(p.parentOwner).call{value: ownerCut}("");
                require(ok, "parent payout failed");
            }
            if (routerCut > 0) {
                // Forward ETH to the router (its receive() accepts it), then
                // ask the router to fan it out across the configured buckets.
                (bool ok,) = payable(address(paymentRouter)).call{value: routerCut}("");
                require(ok, "router fund failed");
                paymentRouter.distribute(address(0), routerCut);
            }
        }

        emit SubnameIssued(parentNode, label, owner);
    }

    // ── Views ──────────────────────────────────────────────────────

    /// @inheritdoc IBankonDomainHosting
    function parentOf(bytes32 parentNode) external view override returns (EnrolledParent memory) {
        return _parents[parentNode];
    }
}
