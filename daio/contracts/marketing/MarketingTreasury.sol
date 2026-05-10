// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl}  from "@openzeppelin/contracts/access/AccessControl.sol";
import {IERC20}         from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20}      from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable}       from "@openzeppelin/contracts/utils/Pausable.sol";

/// @notice Subset of OpenZeppelin's IERC20Burnable — only what we need.
interface IERC20Burnable {
    function burn(uint256 amount) external;
}

/// @notice Minimal Uniswap V3 SwapRouter interface — exactly the ABI we call.
///         We import the interface inline rather than depending on the
///         uniswap-v3-periphery package because the existing repo does not
///         vendor it; this contract is portable and audit-friendly with the
///         interface declared next to its caller.
interface IUniswapV3SwapRouter {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24  fee;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata params)
        external
        payable
        returns (uint256 amountOut);
}

/// @title  MarketingTreasury
/// @author marketinga.bankon.eth
///
/// @notice Marketing-attributed-revenue buyback / burn router.
///
///         Distinct from the main `Treasury.sol` because:
///           1. **Different burn rule.** Hard-coded 99% revenue → buyback →
///              BANKON SATOSHI burn. Encoded in code, not config — auditable.
///           2. **Accounting separation.** Marketing-attributed revenue must
///              be tagged distinctly so quarterly RetroPGF + BANKON SATOSHI
///              burn dashboards can read a single source.
///           3. **Narrative transparency.** Burns are public narrative beats;
///              decoupled events keep marketing burns from polluting (or
///              being polluted by) other treasury flows.
///
///         Deploy target: Ethereum L1 (constitutional finality for the
///         buyback/burn rule).
///
/// @dev    Operator flow:
///          1. external services pay marketing-attributed revenue in `revenueAsset`
///             into this contract via `pay(campaignId, amount)`.
///          2. operator (or a permissionless cron contract) calls
///             `executeBuybackAndBurn(...)` to swap 99% to BANKON SATOSHI and burn.
///          3. 1% retained for the Foundation grants treasury (configurable).
///
///         Pausable via `PAUSE_ROLE` — granted to a Censura-equivalent guardian
///         (today: `BoardroomExtension` admin; tomorrow: BONAFIDE Censura).
contract MarketingTreasury is AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    bytes32 public constant ADMIN_ROLE          = keccak256("ADMIN_ROLE");
    bytes32 public constant BUYBACK_OPERATOR_ROLE = keccak256("BUYBACK_OPERATOR_ROLE");
    bytes32 public constant PAUSE_ROLE          = keccak256("PAUSE_ROLE");

    /// @notice Hard-coded 99% buyback rule. 100 basis points = 1%.
    uint16 public constant BUYBACK_BPS = 9_900;     // 99.00%
    uint16 public constant FOUNDATION_BPS = 100;    // 1.00%
    uint16 public constant BPS_DIVISOR = 10_000;

    IERC20  public immutable revenueAsset;       // USDC default
    IERC20  public immutable bankonSatoshi;      // burned target
    IUniswapV3SwapRouter public immutable swapRouter;
    uint24  public immutable poolFee;            // e.g. 3000 (0.3%) or 500 (0.05%)
    address public foundation;                   // 1% recipient

    /// @notice Per-campaign cumulative inflow.
    mapping(bytes32 => uint256) public revenueByCampaign;

    /// @notice Cumulative buyback / burn / foundation totals.
    uint256 public totalRevenue;
    uint256 public totalBoughtBack;
    uint256 public totalBurned;
    uint256 public totalToFoundation;

    event MarketingRevenueReceived(
        bytes32 indexed campaignId,
        address indexed payer,
        address indexed asset,
        uint256 amount,
        uint256 cumulativeForCampaign
    );

    event MarketingBuybackExecuted(
        bytes32 indexed campaignId,
        uint256 revenueIn,
        uint256 bankonOut,
        uint256 foundationKept
    );

    event MarketingBurnAnnounced(
        bytes32 indexed campaignId,
        uint256 burned,
        uint256 cumulativeBurned
    );

    event FoundationUpdated(address indexed previous, address indexed current);

    error ZeroAmount();
    error ZeroAddress();
    error NoRevenueForCampaign(bytes32 campaignId);

    constructor(
        address admin,
        IERC20 revenueAsset_,
        IERC20 bankonSatoshi_,
        IUniswapV3SwapRouter swapRouter_,
        uint24 poolFee_,
        address foundation_
    ) {
        if (admin == address(0)) revert ZeroAddress();
        if (address(revenueAsset_) == address(0)) revert ZeroAddress();
        if (address(bankonSatoshi_) == address(0)) revert ZeroAddress();
        if (address(swapRouter_) == address(0)) revert ZeroAddress();
        if (foundation_ == address(0)) revert ZeroAddress();

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(BUYBACK_OPERATOR_ROLE, admin);
        _grantRole(PAUSE_ROLE, admin);

        revenueAsset = revenueAsset_;
        bankonSatoshi = bankonSatoshi_;
        swapRouter = swapRouter_;
        poolFee = poolFee_;
        foundation = foundation_;
    }

    // ─────────────────────────────────────────────────────────────────
    // Admin
    // ─────────────────────────────────────────────────────────────────

    function setFoundation(address foundation_) external onlyRole(ADMIN_ROLE) {
        if (foundation_ == address(0)) revert ZeroAddress();
        emit FoundationUpdated(foundation, foundation_);
        foundation = foundation_;
    }

    function pause() external onlyRole(PAUSE_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSE_ROLE) {
        _unpause();
    }

    // ─────────────────────────────────────────────────────────────────
    // Revenue intake
    // ─────────────────────────────────────────────────────────────────

    /// @notice Pay marketing-attributed revenue, tagged by campaignId.
    /// @dev    Caller must approve `revenueAsset` first.
    function pay(bytes32 campaignId, uint256 amount) external whenNotPaused nonReentrant {
        if (amount == 0) revert ZeroAmount();
        revenueAsset.safeTransferFrom(msg.sender, address(this), amount);
        unchecked { revenueByCampaign[campaignId] += amount; totalRevenue += amount; }
        emit MarketingRevenueReceived(
            campaignId, msg.sender, address(revenueAsset), amount, revenueByCampaign[campaignId]
        );
    }

    // ─────────────────────────────────────────────────────────────────
    // Buyback + burn
    // ─────────────────────────────────────────────────────────────────

    /// @notice Execute the 99/1 split for one campaign. The 99% portion is
    ///         swapped via Uniswap V3 to BANKON SATOSHI and burned. The 1%
    ///         portion is transferred to `foundation`.
    function executeBuybackAndBurn(
        bytes32 campaignId,
        uint256 amountIn,
        uint256 minBankonOut
    ) external onlyRole(BUYBACK_OPERATOR_ROLE) whenNotPaused nonReentrant returns (uint256 bankonOut) {
        if (amountIn == 0) revert ZeroAmount();
        if (revenueByCampaign[campaignId] < amountIn) revert NoRevenueForCampaign(campaignId);

        uint256 foundationCut = (amountIn * FOUNDATION_BPS) / BPS_DIVISOR;
        uint256 buybackCut    = amountIn - foundationCut;

        unchecked {
            revenueByCampaign[campaignId] -= amountIn;
            totalToFoundation += foundationCut;
        }

        if (foundationCut > 0) {
            revenueAsset.safeTransfer(foundation, foundationCut);
        }

        revenueAsset.forceApprove(address(swapRouter), buybackCut);
        bankonOut = swapRouter.exactInputSingle(
            IUniswapV3SwapRouter.ExactInputSingleParams({
                tokenIn:           address(revenueAsset),
                tokenOut:          address(bankonSatoshi),
                fee:               poolFee,
                recipient:         address(this),
                amountIn:          buybackCut,
                amountOutMinimum:  minBankonOut,
                sqrtPriceLimitX96: 0
            })
        );

        unchecked { totalBoughtBack += bankonOut; }
        emit MarketingBuybackExecuted(campaignId, amountIn, bankonOut, foundationCut);

        if (bankonOut > 0) {
            IERC20Burnable(address(bankonSatoshi)).burn(bankonOut);
            unchecked { totalBurned += bankonOut; }
            emit MarketingBurnAnnounced(campaignId, bankonOut, totalBurned);
        }

        return bankonOut;
    }
}
