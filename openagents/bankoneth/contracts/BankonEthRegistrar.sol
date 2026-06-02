// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl}   from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable}        from "@openzeppelin/contracts/utils/Pausable.sol";

import {IBankonEthRegistrar, IBankonX402Attestor} from "./interfaces/IBankonExtensions.sol";
import {IBankonPriceOracle, IBankonPaymentRouter} from "./interfaces/IBankon.sol";
import {IReverseRegistrar}                        from "./interfaces/IReverseRegistrar.sol";

/// @notice Subset of the canonical ENS ETHRegistrarController we call.
///         Reference: ensdomains/ens-contracts → ETHRegistrarController.sol
///         (mainnet: 0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547).
interface IETHRegistrarController {
    function rentPrice(string calldata name, uint256 duration)
        external view returns (uint256 base, uint256 premium);

    function makeCommitment(
        string calldata name,
        address owner,
        uint256 duration,
        bytes32 secret,
        address resolver,
        bytes[] calldata data,
        bool reverseRecord,
        uint16 ownerControlledFuses
    ) external pure returns (bytes32);

    function commit(bytes32 commitment) external;

    function register(
        string calldata name,
        address owner,
        uint256 duration,
        bytes32 secret,
        address resolver,
        bytes[] calldata data,
        bool reverseRecord,
        uint16 ownerControlledFuses
    ) external payable;

    function minCommitmentAge() external view returns (uint256);
    function maxCommitmentAge() external view returns (uint256);
    function valid(string calldata name) external view returns (bool);
    function available(string calldata name) external view returns (bool);
}

/// @title  BankonEthRegistrar — Flow B: `.eth` 2LD purchase as a service.
/// @notice Wraps the canonical ENS ETHRegistrarController commit-reveal flow so
///         customers buy `newdomain.eth` end-to-end through bankoneth. Tri-rail
///         payment routes through BankonPaymentRouter; the customer never
///         touches the ENS contracts directly.
///
/// @dev    The commit-reveal window is server-managed via a deterministic salt
///         (`keccak256(label || owner || nonce)`) so the UI can drive the
///         60-second wait without round-trip state. The contract enforces the
///         min/max commitment ages from the upstream controller.
contract BankonEthRegistrar is
    IBankonEthRegistrar,
    AccessControl,
    ReentrancyGuard,
    Pausable
{
    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");

    IETHRegistrarController public immutable controller;
    IBankonPriceOracle      public immutable priceOracle;
    IBankonPaymentRouter    public immutable paymentRouter;
    IBankonX402Attestor     public immutable x402Attestor;

    /// @dev commitment → unix seconds when committed (0 = not committed).
    mapping(bytes32 => uint256) public committedAt;

    /// @dev BANKON markup over the ENS base price, in basis points. Default 1500 = 15%.
    uint16 public markupBps = 1500;

    error LabelInvalid();
    error LabelUnavailable();
    error CommitmentNotFound();
    error CommitmentTooYoung();
    error CommitmentTooOld();
    error InsufficientPayment(uint256 paid, uint256 required);

    constructor(
        address admin,
        IETHRegistrarController _controller,
        IBankonPriceOracle _priceOracle,
        IBankonPaymentRouter _paymentRouter,
        IBankonX402Attestor _x402Attestor
    ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        controller    = _controller;
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

    /// @notice ENSIP-15 contract-naming hook. Admin-only. Records `name` as
    ///         the ENS primary name for this contract via the canonical
    ///         ReverseRegistrar (mainnet 0xa58E81fe…7Cb). After this lands,
    ///         block explorers + wallets that perform reverse resolution
    ///         display `name` instead of the raw address. See
    ///         docs.ens.domains/web/naming-contracts.
    function setReverseName(IReverseRegistrar rr, string calldata newName)
        external onlyRole(DEFAULT_ADMIN_ROLE) returns (bytes32)
    {
        return rr.setName(newName);
    }

    // ── Quote ──────────────────────────────────────────────────────

    /// @inheritdoc IBankonEthRegistrar
    function quote(string calldata label, uint256 durationYears)
        external
        view
        override
        returns (uint256 wei_, uint256 usd6)
    {
        return _quote(label, durationYears);
    }

    /// @dev Internal quote — avoids the external self-call from reveal().
    ///      Audit LOW-2: saves ~700 gas per reveal() and unblocks view-inlining.
    function _quote(string memory label, uint256 durationYears)
        internal
        view
        returns (uint256 wei_, uint256 usd6)
    {
        if (!controller.valid(label)) revert LabelInvalid();
        uint256 durationSeconds = durationYears * 365 days;
        (uint256 base, uint256 premium) = controller.rentPrice(label, durationSeconds);
        uint256 ensWei = base + premium;
        wei_ = ensWei + (ensWei * markupBps) / 10_000;
        usd6 = priceOracle.priceUSD(label, durationYears);
    }

    // ── Commit ─────────────────────────────────────────────────────

    /// @inheritdoc IBankonEthRegistrar
    function commit(CommitParams calldata p)
        external
        override
        whenNotPaused
        returns (bytes32 commitment)
    {
        if (!controller.valid(p.label))     revert LabelInvalid();
        if (!controller.available(p.label)) revert LabelUnavailable();

        bytes[] memory data = new bytes[](0);
        commitment = controller.makeCommitment(
            p.label,
            p.owner,
            p.durationYears * 365 days,
            p.secret,
            p.resolver,
            data,
            p.reverseRecord,
            p.ownerControlledFuses
        );

        controller.commit(commitment);
        committedAt[commitment] = block.timestamp;
        emit Committed(commitment, msg.sender, p.owner);
    }

    // ── Reveal + register ──────────────────────────────────────────

    /// @inheritdoc IBankonEthRegistrar
    function reveal(CommitParams calldata p, bytes calldata payment)
        external
        payable
        override
        nonReentrant
        whenNotPaused
    {
        bytes[] memory data = new bytes[](0);
        bytes32 commitment = controller.makeCommitment(
            p.label,
            p.owner,
            p.durationYears * 365 days,
            p.secret,
            p.resolver,
            data,
            p.reverseRecord,
            p.ownerControlledFuses
        );

        uint256 ts = committedAt[commitment];
        if (ts == 0) revert CommitmentNotFound();
        if (block.timestamp < ts + controller.minCommitmentAge()) revert CommitmentTooYoung();
        if (block.timestamp > ts + controller.maxCommitmentAge()) revert CommitmentTooOld();

        (uint256 weiOwed, uint256 usd6Owed) = _quote(p.label, p.durationYears);

        // Payment rails:
        //   - rail==0x00 → ETH (msg.value)
        //   - rail==0x01 → USDC permit (handled by BankonPaymentRouter via `payment`)
        //   - rail==0x02 → x402-avm receipt (attestor verifies, route the equivalent ETH)
        if (payment.length > 0 && payment[0] == 0x02) {
            // x402-avm: payment = abi.encode(X402Receipt) — verified, no on-chain transfer of USDC.
            // The off-chain Algorand settlement already happened; we still owe the controller in ETH,
            // so the operator-prefunded ETH treasury pays from msg.value supplied by a relayer.
            IBankonX402Attestor.X402Receipt memory r = abi.decode(payment[1:], (IBankonX402Attestor.X402Receipt));
            require(x402Attestor.verify(r), "x402 verify");
            require(r.usd6 >= usd6Owed, "x402 underpay");
            require(msg.value >= weiOwed, "relayer underfunded");
        } else {
            if (msg.value < weiOwed) revert InsufficientPayment(msg.value, weiOwed);
        }

        delete committedAt[commitment];

        controller.register{value: weiOwed}(
            p.label,
            p.owner,
            p.durationYears * 365 days,
            p.secret,
            p.resolver,
            data,
            p.reverseRecord,
            p.ownerControlledFuses
        );

        // Refund any overpayment.
        uint256 refund = msg.value - weiOwed;
        if (refund > 0) {
            (bool ok,) = payable(msg.sender).call{value: refund}("");
            require(ok, "refund failed");
        }

        // Route bankoneth's markup share to the treasury via the payment router.
        // (controller.register consumed `weiOwed` for the ENS base+premium;
        //  the markup portion stays in this contract until sweeped — see sweep().)

        emit Registered(p.label, p.owner, weiOwed, address(0));
    }

    /// @notice Sweep accumulated ETH balance (the BANKON markup) to the payment
    ///         router for the 5-bucket split.
    /// @dev    Mirrors the fund-then-distribute pattern from
    ///         BankonDomainHosting.issue() (HIGH-2 audit fix): `distribute()`
    ///         is not `payable`, so the router needs its ETH topped up via a
    ///         raw call before `distribute()` can fan it out.
    function sweep() external nonReentrant onlyRole(TREASURER_ROLE) {
        uint256 bal = address(this).balance;
        if (bal == 0) return;
        (bool ok,) = payable(address(paymentRouter)).call{value: bal}("");
        require(ok, "router fund failed");
        paymentRouter.distribute(address(0), bal);
    }

    receive() external payable {}
}
