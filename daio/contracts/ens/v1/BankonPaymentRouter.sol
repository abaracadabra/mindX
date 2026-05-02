// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {IBankonPaymentRouter} from "./interfaces/IBankon.sol";

/// @title  BankonPaymentRouter
/// @notice Records x402 payment receipts (off-chain settlement on the source
///         chain — Base USDC, Algorand PYTHAI, L1 ETH/USDC) and distributes
///         L1-deposited revenue across five buckets per the doc spec:
///           40% treasury
///           25% buyback-and-make
///           15% public goods
///           10% ops
///           10% squat reserve
///
///         Agnostic: any registrar can call `recordReceipt()` after a paid
///         registration. Any operator can call `distribute()` (TREASURER_ROLE)
///         to sweep accumulated revenue into the configured destinations.
contract BankonPaymentRouter is AccessControl, ReentrancyGuard, IBankonPaymentRouter {
    using SafeERC20 for IERC20;

    bytes32 public constant TREASURER_ROLE        = keccak256("TREASURER_ROLE");
    bytes32 public constant REGISTRAR_ROLE        = keccak256("REGISTRAR_ROLE");

    /// Recipients (set via setRecipients). Zero address disables that bucket.
    address public treasury;
    address public buybackVault;
    address public publicGoods;
    address public ops;
    address public squatReserve;

    /// Splits in basis points (sum must equal 10000). Defaults match the spec.
    uint16 public bpsTreasury     = 4000;
    uint16 public bpsBuyback      = 2500;
    uint16 public bpsPublicGoods  = 1500;
    uint16 public bpsOps          = 1000;
    uint16 public bpsSquat        = 1000;

    /// Receipts seen via recordReceipt — anti-replay companion to the
    /// registrar's `usedReceipts` mapping (same hash, different layer).
    mapping(bytes32 => bool) public seenReceipt;

    /// Buyback trigger threshold (USDC base units). When `buybackPending`
    /// crosses, emit `BuybackTriggerCrossed` so KeeperHub upkeeps fire.
    uint256 public buybackThresholdUSD6 = 100_000000;       // $100 default
    uint256 public buybackPending;

    event RecipientsUpdated(
        address treasury, address buybackVault, address publicGoods,
        address ops, address squatReserve
    );
    event SplitsUpdated(uint16 t, uint16 b, uint16 p, uint16 o, uint16 s);
    event ReceiptRecorded(bytes32 indexed receiptHash, uint256 usd6, address asset);
    event Distributed(address indexed asset, uint256 total,
                      uint256 toTreasury, uint256 toBuyback,
                      uint256 toPublicGoods, uint256 toOps, uint256 toSquat);
    event BuybackTriggerCrossed(uint256 amountUSD6);
    event BuybackThresholdUpdated(uint256 oldT, uint256 newT);

    error ReceiptAlreadyRecorded(bytes32 h);
    error BadSplits();
    error NoRecipients();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(TREASURER_ROLE, admin);
        _grantRole(REGISTRAR_ROLE, admin);
    }

    /* ───── Read ────────────────────────────────────────────────── */

    function splitConfigured() external view override returns (bool) {
        return treasury != address(0) || buybackVault != address(0) ||
               publicGoods != address(0) || ops != address(0) ||
               squatReserve != address(0);
    }

    /* ───── Recording (called by registrar) ─────────────────────── */

    /// @notice Record that a paid registration occurred for accounting purposes.
    ///         Settlement actually happened on the source chain via x402; this
    ///         is the L1 audit trail.
    function recordReceipt(bytes32 receiptHash, uint256 usd6, address asset)
        external override onlyRole(REGISTRAR_ROLE)
    {
        if (seenReceipt[receiptHash]) revert ReceiptAlreadyRecorded(receiptHash);
        seenReceipt[receiptHash] = true;
        // Track expected buyback portion (25%) toward the trigger threshold.
        uint256 toBuyback = (usd6 * bpsBuyback) / 10000;
        buybackPending += toBuyback;
        emit ReceiptRecorded(receiptHash, usd6, asset);
        if (buybackPending >= buybackThresholdUSD6) {
            emit BuybackTriggerCrossed(buybackPending);
            buybackPending = 0;
        }
    }

    /* ───── Distribution (called by treasurer) ──────────────────── */

    /// @notice Split `amount` of `asset` across the five buckets per the BPS.
    ///         Address(0) bucket is skipped and its share rolls to treasury.
    function distribute(address asset, uint256 amount)
        external override nonReentrant onlyRole(TREASURER_ROLE)
    {
        if (treasury == address(0) && buybackVault == address(0) &&
            publicGoods == address(0) && ops == address(0) && squatReserve == address(0)) {
            revert NoRecipients();
        }

        uint256 toTreasury = (amount * bpsTreasury)    / 10000;
        uint256 toBuyback  = (amount * bpsBuyback)     / 10000;
        uint256 toPublic   = (amount * bpsPublicGoods) / 10000;
        uint256 toOps      = (amount * bpsOps)         / 10000;
        uint256 toSquat    = (amount * bpsSquat)       / 10000;

        // Roll any disabled-bucket shares into treasury.
        uint256 rolled;
        if (buybackVault == address(0)) { rolled += toBuyback; toBuyback = 0; }
        if (publicGoods  == address(0)) { rolled += toPublic;  toPublic  = 0; }
        if (ops          == address(0)) { rolled += toOps;     toOps     = 0; }
        if (squatReserve == address(0)) { rolled += toSquat;   toSquat   = 0; }
        toTreasury += rolled;

        if (asset == address(0)) {
            // Native token (ETH).
            if (toTreasury > 0)  _send(treasury,     toTreasury);
            if (toBuyback  > 0)  _send(buybackVault, toBuyback);
            if (toPublic   > 0)  _send(publicGoods,  toPublic);
            if (toOps      > 0)  _send(ops,          toOps);
            if (toSquat    > 0)  _send(squatReserve, toSquat);
        } else {
            IERC20 t = IERC20(asset);
            if (toTreasury > 0) t.safeTransfer(treasury,     toTreasury);
            if (toBuyback  > 0) t.safeTransfer(buybackVault, toBuyback);
            if (toPublic   > 0) t.safeTransfer(publicGoods,  toPublic);
            if (toOps      > 0) t.safeTransfer(ops,          toOps);
            if (toSquat    > 0) t.safeTransfer(squatReserve, toSquat);
        }

        emit Distributed(asset, amount, toTreasury, toBuyback, toPublic, toOps, toSquat);
    }

    function _send(address to, uint256 wei_) internal {
        if (to == address(0) || wei_ == 0) return;
        (bool ok, ) = to.call{value: wei_}("");
        require(ok, "ETH send failed");
    }

    /* ───── Admin ────────────────────────────────────────────────── */

    function setRecipients(
        address _treasury, address _buyback, address _publicGoods,
        address _ops, address _squat
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        treasury     = _treasury;
        buybackVault = _buyback;
        publicGoods  = _publicGoods;
        ops          = _ops;
        squatReserve = _squat;
        emit RecipientsUpdated(_treasury, _buyback, _publicGoods, _ops, _squat);
    }

    function setSplits(uint16 t, uint16 b, uint16 p, uint16 o, uint16 s)
        external onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (uint256(t) + b + p + o + s != 10000) revert BadSplits();
        bpsTreasury    = t;
        bpsBuyback     = b;
        bpsPublicGoods = p;
        bpsOps         = o;
        bpsSquat       = s;
        emit SplitsUpdated(t, b, p, o, s);
    }

    function setBuybackThreshold(uint256 newThreshold) external onlyRole(DEFAULT_ADMIN_ROLE) {
        emit BuybackThresholdUpdated(buybackThresholdUSD6, newThreshold);
        buybackThresholdUSD6 = newThreshold;
    }

    receive() external payable {}
}
