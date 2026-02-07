// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Address.sol";

// ----------------------------------------------------------------------------
// Uniswap V2 Router (for swap + getAmountsOut for slippage)
// ----------------------------------------------------------------------------
interface IUniswapV2Router02 {
    function swapExactTokensForETHSupportingFeeOnTransferTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external;

    function getAmountsOut(uint256 amountIn, address[] calldata path) external view returns (uint256[] memory amounts);
}

interface IUniswapV3SwapRouter {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

/**
 * @title DAIOReflectionToken
 * @notice Reflection token with fee-on-transfer, wallet-to-wallet exemption, and DAIO-suited admin hierarchy.
 * @dev Modified from ShambaLuv-style deployment. Suitable for DAIO: Owner can transfer to timelock; Admin for ops.
 *
 * FEE STRUCTURE (configurable at deploy):
 *   - Reflection fee (to holders)
 *   - Liquidity fee
 *   - Team / treasury fee
 *
 * FIXES vs original:
 *   - Router approval in constructor so first auto-swap does not revert.
 *   - Slippage: amountOutMin derived from router.getAmountsOut (expected ETH out) then slippage applied; not token amount.
 *   - SwapBackTriggered event for observability.
 *   - Single pragma ^0.8.20; OpenZeppelin imports.
 *
 * ADMIN HIERARCHY (DAIO):
 *   - Owner: deployer; can set admin, set wallets, renounce. Can transfer ownership to DAIO timelock.
 *   - Admin: operational (router, timelock, thresholds). Set to DAIO multisig or timelock executor.
 */
contract DAIOReflectionToken is ERC20, Ownable, ReentrancyGuard {

    uint256 private constant FEE_DENOMINATOR = 10000;
    uint256 private constant MAX_SLIPPAGE_BPS = 2000;   // 20%
    uint256 private constant REFLECTION_DENOMINATOR = 1e18;

    uint256 public immutable TOTAL_FEE_PERCENTAGE;  // e.g. 500 = 5%
    uint256 public immutable BASE_REFLECTION_FEE;
    uint256 public immutable BASE_LIQUIDITY_FEE;
    uint256 public immutable BASE_TEAM_FEE;

    address public teamWallet;
    address public liquidityWallet;
    address public adminWallet;
    bool public adminFinalized;

    IUniswapV2Router02 public router;
    IUniswapV3SwapRouter public v3Router;
    address public immutable WETH;
    bool public useV3Router;

    uint256 public teamSwapThreshold;
    uint256 public swapThreshold;
    uint256 public liquidityThreshold;
    uint256 public maxTransferPercent = 100;  // 1%
    uint256 public maxTransferAmount;
    bool public maxTransferEnabled = true;
    bool public swapEnabled = true;
    bool private inSwap;

    bool public walletToWalletFeeExempt = true;
    mapping(address => bool) public isExcludedFromFee;
    mapping(address => bool) public isExcludedFromMaxTransfer;
    mapping(address => bool) public isExcludedFromReflection;

    uint256 public reflectionIndex;
    mapping(address => uint256) public lastReflectionIndex;
    mapping(address => uint256) public reflectionBalance;
    uint256 public totalReflectionFeesCollected;
    uint256 public totalReflectionFeesDistributed;
    uint256 public accumulatedReflectionFees;
    uint256 public reflectionBatchThreshold = 1e30;
    uint256 private _localTotalSupply;

    uint256 public maxSlippage = 500;  // 5% in bps

    mapping(bytes32 => uint256) public timelockProposals;
    enum OperationState { Unset, Waiting, Ready, Done }
    mapping(bytes32 => OperationState) public operationStates;
    bool public timelockEnabled = false;

    event SwapBackTriggered(uint256 amountIn, uint256 amountOutMin, uint256 received, string routerType);
    event SlippageProtectionUsed(uint256 amountIn, uint256 amountOutMin, uint256 actualOut, string routerType);
    event RouterUpdated(address indexed oldRouter, address indexed newRouter);
    event AdminUpdated(address indexed previousAdmin, address indexed newAdmin);
    event WalletToWalletFeeExemptToggled(bool enabled);
    event ReflectionDistributed(address indexed holder, uint256 amount);

    modifier swapping() {
        inSwap = true;
        _;
        inSwap = false;
    }

    modifier onlyAdmin() {
        require(msg.sender == adminWallet, "Not admin");
        _;
    }

    constructor(
        string memory name_,
        string memory symbol_,
        uint256 totalSupply_,
        address _teamWallet,
        address _liquidityWallet,
        address _router,
        address _weth,
        uint256 reflectionBps_,
        uint256 liquidityBps_,
        uint256 teamBps_
    ) ERC20(name_, symbol_) Ownable(msg.sender) {
        require(_teamWallet != address(0) && _liquidityWallet != address(0) && _router != address(0) && _weth != address(0), "Zero address");
        require(reflectionBps_ + liquidityBps_ + teamBps_ <= 2500, "Fee too high"); // max 25%
        teamWallet = _teamWallet;
        liquidityWallet = _liquidityWallet;
        adminWallet = msg.sender; // deployer is initial admin
        router = IUniswapV2Router02(_router);
        WETH = _weth;
        BASE_REFLECTION_FEE = reflectionBps_;
        BASE_LIQUIDITY_FEE = liquidityBps_;
        BASE_TEAM_FEE = teamBps_;
        TOTAL_FEE_PERCENTAGE = reflectionBps_ + liquidityBps_ + teamBps_;

        teamSwapThreshold = 1e30;
        swapThreshold = 1e30;
        liquidityThreshold = 1e30;
        maxTransferAmount = totalSupply_ / maxTransferPercent;

        isExcludedFromFee[msg.sender] = true;
        isExcludedFromMaxTransfer[msg.sender] = true;
        isExcludedFromReflection[_liquidityWallet] = true;

        _mint(msg.sender, totalSupply_);
        _localTotalSupply = totalSupply_;

        // CRITICAL: Approve router so first auto-swap does not revert
        _approve(address(this), _router, type(uint256).max);
    }

    receive() external payable {}

    function localTotalSupply() public view returns (uint256) {
        return _localTotalSupply;
    }

    function transfer(address to, uint256 amount) public virtual override returns (bool) {
        return _transferWithFees(_msgSender(), to, amount);
    }

    function transferFrom(address from, address to, uint256 amount) public virtual override returns (bool) {
        _spendAllowance(from, _msgSender(), amount);
        return _transferWithFees(from, to, amount);
    }

    function _transferWithFees(address from, address to, uint256 amount) internal returns (bool) {
        if (from == address(0)) {
            super._transfer(from, to, amount);
            _localTotalSupply += amount;
            return true;
        }
        require(to != address(0) && amount != 0, "Invalid transfer");

        if (maxTransferEnabled && !isExcludedFromMaxTransfer[from] && !isExcludedFromMaxTransfer[to]) {
            require(amount <= maxTransferAmount, "Exceeds max transfer");
        }

        bool isWalletToWallet = from.code.length == 0 && to.code.length == 0;
        if (
            isExcludedFromFee[from] ||
            isExcludedFromFee[to] ||
            (walletToWalletFeeExempt && isWalletToWallet)
        ) {
            super._transfer(from, to, amount);
            return true;
        }

        uint256 totalFee = (amount * TOTAL_FEE_PERCENTAGE) / FEE_DENOMINATOR;
        uint256 reflectionFee = (amount * BASE_REFLECTION_FEE) / FEE_DENOMINATOR;
        uint256 remaining = amount - totalFee;

        super._transfer(from, to, remaining);
        super._transfer(from, address(this), totalFee);

        if (reflectionFee != 0) {
            accumulatedReflectionFees += reflectionFee;
            totalReflectionFeesCollected += reflectionFee;
            if (accumulatedReflectionFees >= reflectionBatchThreshold) {
                _processReflectionBatch();
            }
        }

        if (swapEnabled && !inSwap && balanceOf(address(this)) >= swapThreshold) {
            _maybeSwapBack();
        }
        return true;
    }

    function _processReflectionBatch() private {
        if (accumulatedReflectionFees == 0 || _localTotalSupply == 0) return;
        reflectionIndex += (accumulatedReflectionFees * REFLECTION_DENOMINATOR) / _localTotalSupply;
        accumulatedReflectionFees = 0;
    }

    function _maybeSwapBack() private swapping {
        uint256 contractBalance = balanceOf(address(this));
        if (contractBalance == 0) return;
        bool shouldSwapTeam = contractBalance >= teamSwapThreshold;
        bool shouldSwapLiquidity = contractBalance >= liquidityThreshold;
        if (!shouldSwapTeam && !shouldSwapLiquidity) return;

        uint256 totalFee = BASE_LIQUIDITY_FEE + BASE_TEAM_FEE;
        uint256 swapAmount = (contractBalance * totalFee) / TOTAL_FEE_PERCENTAGE;
        if (swapAmount == 0) return;

        if (useV3Router && address(v3Router) != address(0)) {
            _swapBackV3(swapAmount);
        } else {
            _swapBackV2(swapAmount);
        }
    }

    /**
     * @dev Slippage: amountOutMin from router.getAmountsOut (expected ETH out), then apply maxSlippage.
     *    Original bug: used token amount as if it were ETH out, causing reverts or wrong checks.
     */
    function _swapBackV2(uint256 amount) private {
        address[] memory path = new address[](2);
        path[0] = address(this);
        path[1] = WETH;

        uint256 amountOutMin;
        try router.getAmountsOut(amount, path) returns (uint256[] memory amounts) {
            if (amounts[1] == 0) {
                amountOutMin = 0;
            } else {
                amountOutMin = amounts[1] * (10000 - maxSlippage) / 10000;
            }
        } catch {
            amountOutMin = 0; // accept any if quote fails (e.g. no pair yet)
        }

        uint256 beforeBalance = address(this).balance;
        router.swapExactTokensForETHSupportingFeeOnTransferTokens(
            amount,
            amountOutMin,
            path,
            address(this),
            block.timestamp
        );
        uint256 received = address(this).balance - beforeBalance;
        emit SwapBackTriggered(amount, amountOutMin, received, "V2");
        emit SlippageProtectionUsed(amount, amountOutMin, received, "V2");

        uint256 ethBalance = address(this).balance;
        uint256 totalFee = BASE_LIQUIDITY_FEE + BASE_TEAM_FEE;
        uint256 teamShare = (ethBalance * BASE_TEAM_FEE) / totalFee;
        uint256 liquidityShare = ethBalance - teamShare;
        if (teamShare != 0) Address.sendValue(payable(teamWallet), teamShare);
        if (liquidityShare != 0) Address.sendValue(payable(liquidityWallet), liquidityShare);
    }

    function _swapBackV3(uint256 amount) private {
        uint256 amountOutMin = 0; // V3 quote would require Quoter contract; use 0 or add Quoter later
        IUniswapV3SwapRouter.ExactInputSingleParams memory params = IUniswapV3SwapRouter.ExactInputSingleParams({
            tokenIn: address(this),
            tokenOut: WETH,
            fee: 3000,
            recipient: address(this),
            deadline: block.timestamp,
            amountIn: amount,
            amountOutMinimum: amountOutMin,
            sqrtPriceLimitX96: 0
        });
        uint256 amountOut = v3Router.exactInputSingle(params);
        emit SwapBackTriggered(amount, amountOutMin, amountOut, "V3");
        emit SlippageProtectionUsed(amount, amountOutMin, amountOut, "V3");

        uint256 totalFee = BASE_LIQUIDITY_FEE + BASE_TEAM_FEE;
        uint256 teamShare = (amountOut * BASE_TEAM_FEE) / totalFee;
        uint256 liquidityShare = amountOut - teamShare;
        if (teamShare != 0) Address.sendValue(payable(teamWallet), teamShare);
        if (liquidityShare != 0) Address.sendValue(payable(liquidityWallet), liquidityShare);
    }

    function _claimReflections(address holder) private returns (uint256) {
        if (isExcludedFromReflection[holder]) return 0;
        if (accumulatedReflectionFees != 0) _processReflectionBatch();
        uint256 currentReflectionIndex = reflectionIndex;
        uint256 lastIndex = lastReflectionIndex[holder];
        uint256 holderBalance = balanceOf(holder);
        if (holderBalance == 0 || currentReflectionIndex <= lastIndex) return 0;
        uint256 delta = currentReflectionIndex - lastIndex;
        uint256 reflectionAmount = (holderBalance * delta) / REFLECTION_DENOMINATOR;
        if (reflectionAmount != 0) {
            reflectionBalance[holder] += reflectionAmount;
            totalReflectionFeesDistributed += reflectionAmount;
        }
        lastReflectionIndex[holder] = currentReflectionIndex;
        return reflectionAmount;
    }

    function claimReflections() external nonReentrant {
        require(!isExcludedFromReflection[msg.sender], "Exempt");
        uint256 amount = _claimReflections(msg.sender);
        require(amount != 0, "Nothing to claim");
        reflectionBalance[msg.sender] = 0;
        _transfer(address(this), msg.sender, amount);
        emit ReflectionDistributed(msg.sender, amount);
    }

    function getReflectionBalance(address holder) external view returns (uint256) {
        if (isExcludedFromReflection[holder]) return reflectionBalance[holder];
        uint256 currentReflectionIndex = reflectionIndex;
        uint256 lastIndex = lastReflectionIndex[holder];
        uint256 holderBalance = balanceOf(holder);
        if (holderBalance == 0 || currentReflectionIndex <= lastIndex) return reflectionBalance[holder];
        uint256 delta = currentReflectionIndex - lastIndex;
        uint256 reflectionAmount = (holderBalance * delta) / REFLECTION_DENOMINATOR;
        return reflectionBalance[holder] + reflectionAmount;
    }

    // ---------- DAIO admin hierarchy ----------
    /// @notice Set admin (e.g. DAIO timelock or multisig). Only owner. One-time finalization optional.
    function setAdmin(address newAdmin) external onlyOwner {
        require(!adminFinalized, "Admin finalized");
        require(newAdmin != address(0), "Zero address");
        address old = adminWallet;
        adminWallet = newAdmin;
        emit AdminUpdated(old, newAdmin);
    }

    function setAdminFinalized() external onlyOwner {
        adminFinalized = true;
    }

    function setTeamWallet(address _w) external onlyOwner {
        require(_w != address(0), "Zero address");
        teamWallet = _w;
    }

    function setLiquidityWallet(address _w) external onlyOwner {
        require(_w != address(0), "Zero address");
        liquidityWallet = _w;
    }

    function setWalletToWalletFeeExempt(bool _exempt) external onlyOwner {
        walletToWalletFeeExempt = _exempt;
        emit WalletToWalletFeeExemptToggled(_exempt);
    }

    function setFeeExemption(address account, bool status) external onlyOwner {
        isExcludedFromFee[account] = status;
    }

    function setMaxTransferExemption(address account, bool status) external onlyOwner {
        isExcludedFromMaxTransfer[account] = status;
    }

    function setReflectionExemption(address account, bool status) external onlyOwner {
        isExcludedFromReflection[account] = status;
    }

    function setThresholds(uint256 _team, uint256 _liq) external onlyOwner {
        teamSwapThreshold = _team;
        liquidityThreshold = _liq;
    }

    function setMaxSlippage(uint256 _bps) external onlyOwner {
        require(_bps <= MAX_SLIPPAGE_BPS && _bps != 0, "Invalid slippage");
        maxSlippage = _bps;
    }

    /// @notice Admin can update router (e.g. after deploy). Ensure router is approved in constructor or here.
    function updateRouter(address _newRouter) external onlyAdmin {
        require(_newRouter != address(0) && _newRouter != address(router), "Invalid router");
        address old = address(router);
        _approve(address(this), old, 0);
        router = IUniswapV2Router02(_newRouter);
        _approve(address(this), _newRouter, type(uint256).max);
        emit RouterUpdated(old, _newRouter);
    }

    function setV3Router(address _v3Router) external onlyAdmin {
        v3Router = IUniswapV3SwapRouter(_v3Router);
    }

    function setSwapEnabled(bool _enabled) external onlyOwner {
        swapEnabled = _enabled;
    }

    function forceReflectionUpdate() external {
        _processReflectionBatch();
    }
}
