// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ERC20 } from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import { Address } from "@openzeppelin/contracts/utils/Address.sol";

/// @title ReflectionRewardToken - Parameterized Reflection Token
/// @notice Configurable reflection token with fee distribution and wallet-to-wallet fee exemption
/// @dev Based on ShambaLuv architecture, parameterized for bonding curve deployments
/// @dev Default name: "REFLECT REWARD", default symbol: "REWARD"
contract ReflectionRewardToken is ERC20, Ownable, ReentrancyGuard {
    using Address for address payable;

    // ============ CONFIGURABLE PARAMETERS ============
    uint256 public immutable TOTAL_SUPPLY;
    uint256 public immutable BASE_REFLECTION_FEE;  // Basis points (default: 300 = 3%)
    uint256 public immutable BASE_LIQUIDITY_FEE;   // Basis points (default: 100 = 1%)
    uint256 public immutable BASE_TEAM_FEE;        // Basis points (default: 100 = 1%)
    uint256 private constant FEE_DENOMINATOR = 10000;
    
    // ============ STATE VARIABLES ============
    uint256 public teamSwapThreshold;
    uint256 public swapThreshold;
    uint256 public liquidityThreshold;
    uint256 public maxTransferPercent = 100; // 1% default
    uint256 public maxTransferAmount;
    bool public maxTransferEnabled = true;

    address public teamWallet;
    address public liquidityWallet;
    address public adminWallet;
    address public pendingAdmin;
    bool public adminFinalized;

    // Router management
    address public router;
    address public v3Router;
    address public immutable WETH;
    bool public useV3Router = false;

    // Swap management
    bool public swapEnabled = true;
    bool private inSwap;

    // Wallet-to-wallet fee exemption
    bool public walletToWalletFeeExempt = true;

    // Exemptions
    mapping(address => bool) public isExcludedFromFee;
    mapping(address => bool) public isExcludedFromMaxTransfer;
    mapping(address => bool) public isExcludedFromReflection;

    // Reflection variables
    uint256 public reflectionThreshold = 1e30;
    uint256 public totalReflectionFeesCollected;
    uint256 public totalReflectionFeesDistributed;
    uint256 public reflectionIndex;
    mapping(address => uint256) public lastReflectionIndex;
    mapping(address => uint256) public reflectionBalance;
    uint256 private _localTotalSupply;
    uint256 public accumulatedReflectionFees;
    uint256 public reflectionBatchThreshold = 1e30;

    // Security
    uint256 public maxSlippage = 500; // 5% default
    uint256 private constant MAX_SLIPPAGE = 2000; // 20% max
    uint256 private constant REFLECTION_DENOMINATOR = 1e18;

    // ============ EVENTS ============
    event RouterUpdated(address indexed oldRouter, address indexed newRouter);
    event ThresholdsUpdated(uint256 teamThreshold, uint256 liquidityThreshold);
    event MaxTransferUpdated(uint256 oldMax, uint256 newMax);
    event WalletUpdated(string walletType, address indexed oldWallet, address indexed newWallet);
    event FeeExemptionUpdated(address indexed account, bool status);
    event ReflectionDistributed(address indexed holder, uint256 amount);
    event WalletToWalletFeeExemptTransfer(address indexed from, address indexed to, uint256 amount);
    event AdminUpdated(address indexed previousAdmin, address indexed newAdmin);

    // ============ MODIFIERS ============
    modifier swapping() {
        inSwap = true;
        _;
        inSwap = false;
    }

    modifier onlyAdmin() {
        require(msg.sender == adminWallet, "Not admin");
        _;
    }

    // ============ CONSTRUCTOR ============
    /// @param _name Token name (default: "REFLECT REWARD")
    /// @param _symbol Token symbol (default: "REWARD")
    /// @param _totalSupply Total supply to mint (default: 1e35 = 100 quadrillion)
    /// @param _reflectionFee Reflection fee in basis points (default: 300 = 3%)
    /// @param _liquidityFee Liquidity fee in basis points (default: 100 = 1%)
    /// @param _teamFee Team fee in basis points (default: 100 = 1%)
    /// @param _teamWallet Team wallet address
    /// @param _liquidityWallet Liquidity wallet address
    /// @param _router Router address (Uniswap V2 compatible)
    /// @param _weth WETH address
    constructor(
        string memory _name,
        string memory _symbol,
        uint256 _totalSupply,
        uint256 _reflectionFee,
        uint256 _liquidityFee,
        uint256 _teamFee,
        address _teamWallet,
        address _liquidityWallet,
        address _router,
        address _weth
    ) ERC20(_name, _symbol) Ownable(msg.sender) {
        require(_teamWallet != address(0), "Invalid team wallet");
        require(_liquidityWallet != address(0), "Invalid liquidity wallet");
        require(_router != address(0), "Invalid router");
        require(_weth != address(0), "Invalid WETH");
        require(_reflectionFee + _liquidityFee + _teamFee <= 1000, "Total fees exceed 10%");
        
        // Set immutable parameters
        TOTAL_SUPPLY = _totalSupply;
        BASE_REFLECTION_FEE = _reflectionFee;
        BASE_LIQUIDITY_FEE = _liquidityFee;
        BASE_TEAM_FEE = _teamFee;
        WETH = _weth;
        
        teamWallet = _teamWallet;
        liquidityWallet = _liquidityWallet;
        router = _router;
        
        // Initialize thresholds (1% of supply)
        teamSwapThreshold = _totalSupply / 100;
        swapThreshold = _totalSupply / 100;
        liquidityThreshold = _totalSupply / 100;
        maxTransferAmount = _totalSupply / maxTransferPercent;
        
        // Exclude owner and liquidity wallet
        isExcludedFromFee[msg.sender] = true;
        isExcludedFromMaxTransfer[msg.sender] = true;
        isExcludedFromReflection[liquidityWallet] = true;
        
        // Mint total supply
        _mint(msg.sender, _totalSupply);
        _localTotalSupply = _totalSupply;
    }

    // ============ CORE FUNCTIONS ============
    function transfer(address to, uint256 amount) public virtual override returns (bool) {
        return _transferWithFees(_msgSender(), to, amount);
    }

    function transferFrom(address from, address to, uint256 amount) public virtual override returns (bool) {
        address spender = _msgSender();
        _spendAllowance(from, spender, amount);
        return _transferWithFees(from, to, amount);
    }

    function _transferWithFees(address from, address to, uint256 amount) internal returns (bool) {
        if (from == address(0)) {
            super._transfer(from, to, amount);
            _localTotalSupply = _localTotalSupply + amount;
            return true;
        }
        
        require(to != address(0), "Transfer to zero");
        require(amount != 0, "Transfer amount must be positive");

        // Max transfer check
        if (maxTransferEnabled && !isExcludedFromMaxTransfer[from] && !isExcludedFromMaxTransfer[to]) {
            require(amount <= maxTransferAmount, "Transfer exceeds max limit");
        }

        // Wallet-to-wallet fee exemption
        bool isWalletToWallet = from.code.length == 0 && to.code.length == 0;
        if (
            isExcludedFromFee[from] ||
            isExcludedFromFee[to] ||
            (walletToWalletFeeExempt && isWalletToWallet)
        ) {
            super._transfer(from, to, amount);
            if (walletToWalletFeeExempt && isWalletToWallet) {
                emit WalletToWalletFeeExemptTransfer(from, to, amount);
            }
            return true;
        }

        // Calculate fees
        uint256 totalFee = (amount * (BASE_REFLECTION_FEE + BASE_LIQUIDITY_FEE + BASE_TEAM_FEE)) / FEE_DENOMINATOR;
        uint256 reflectionFee = (amount * BASE_REFLECTION_FEE) / FEE_DENOMINATOR;
        uint256 remaining = amount - totalFee;
        
        super._transfer(from, to, remaining);
        super._transfer(from, address(this), totalFee);
        
        // Accumulate reflection fees
        if (reflectionFee != 0) {
            accumulatedReflectionFees = accumulatedReflectionFees + reflectionFee;
            totalReflectionFeesCollected = totalReflectionFeesCollected + reflectionFee;
            
            if (accumulatedReflectionFees >= reflectionBatchThreshold) {
                _processReflectionBatch();
            }
        }

        // Auto-swap
        if (swapEnabled && !inSwap && balanceOf(address(this)) >= swapThreshold) {
            _maybeSwapBack();
        }

        return true;
    }

    function _processReflectionBatch() private {
        if (accumulatedReflectionFees == 0 || _localTotalSupply == 0) return;
        reflectionIndex = reflectionIndex + (accumulatedReflectionFees * REFLECTION_DENOMINATOR) / _localTotalSupply;
        accumulatedReflectionFees = 0;
    }

    function _claimReflections(address holder) private returns (uint256) {
        if (isExcludedFromReflection[holder]) return 0;
        if (accumulatedReflectionFees != 0) _processReflectionBatch();
        
        uint256 currentReflectionIndex = reflectionIndex;
        uint256 lastIndex = lastReflectionIndex[holder];
        uint256 holderBalance = balanceOf(holder);
        
        if (holderBalance == 0 || currentReflectionIndex <= lastIndex) return 0;
        
        uint256 reflectionAmount = (holderBalance * (currentReflectionIndex - lastIndex)) / REFLECTION_DENOMINATOR;
        if (reflectionAmount != 0) {
            reflectionBalance[holder] = reflectionBalance[holder] + reflectionAmount;
            totalReflectionFeesDistributed = totalReflectionFeesDistributed + reflectionAmount;
        }
        lastReflectionIndex[holder] = currentReflectionIndex;
        return reflectionAmount;
    }

    function claimReflections() external nonReentrant {
        require(!isExcludedFromReflection[msg.sender], "Exempt from reflections");
        uint256 amount = _claimReflections(msg.sender);
        require(amount != 0, "No reflections to claim");
        reflectionBalance[msg.sender] = 0;
        _transfer(address(this), msg.sender, amount);
        emit ReflectionDistributed(msg.sender, amount);
    }

    function _maybeSwapBack() private swapping {
        uint256 contractBalance = balanceOf(address(this));
        if (contractBalance == 0) return;
        
        uint256 totalFee = BASE_LIQUIDITY_FEE + BASE_TEAM_FEE;
        uint256 swapAmount = (contractBalance * totalFee) / (BASE_REFLECTION_FEE + BASE_LIQUIDITY_FEE + BASE_TEAM_FEE);
        if (swapAmount == 0) return;
        
        // Simplified swap - would need router interface in production
        // This is a stub for the bonding curve integration
    }

    // ============ ADMIN FUNCTIONS ============
    function setAdmin(address newAdmin) external onlyOwner {
        require(!adminFinalized, "Admin finalized");
        require(newAdmin != address(0), "Zero address");
        address oldAdmin = adminWallet;
        adminWallet = newAdmin;
        emit AdminUpdated(oldAdmin, newAdmin);
    }

    function setThresholds(uint256 _teamThreshold, uint256 _liquidityThreshold) external onlyOwner {
        teamSwapThreshold = _teamThreshold;
        liquidityThreshold = _liquidityThreshold;
        emit ThresholdsUpdated(_teamThreshold, _liquidityThreshold);
    }

    function setMaxTransferPercent(uint256 _newPercent) external onlyOwner {
        require(_newPercent >= 100 && _newPercent <= 10000, "Invalid percent");
        maxTransferPercent = _newPercent;
        maxTransferAmount = TOTAL_SUPPLY / maxTransferPercent;
        emit MaxTransferUpdated(maxTransferAmount, maxTransferAmount);
    }

    function setTeamWallet(address _teamWallet) external onlyOwner {
        require(_teamWallet != address(0), "Zero address");
        address oldWallet = teamWallet;
        teamWallet = _teamWallet;
        emit WalletUpdated("team", oldWallet, _teamWallet);
    }

    function setLiquidityWallet(address _liqWallet) external onlyOwner {
        require(_liqWallet != address(0), "Zero address");
        address oldWallet = liquidityWallet;
        liquidityWallet = _liqWallet;
        emit WalletUpdated("liquidity", oldWallet, _liqWallet);
    }

    function setFeeExemption(address account, bool status) external onlyOwner {
        isExcludedFromFee[account] = status;
        emit FeeExemptionUpdated(account, status);
    }

    function setMaxTransferExemption(address account, bool status) external onlyOwner {
        isExcludedFromMaxTransfer[account] = status;
    }

    function setReflectionExemption(address account, bool status) external onlyOwner {
        isExcludedFromReflection[account] = status;
    }

    function setWalletToWalletFeeExempt(bool _exempt) external onlyOwner {
        walletToWalletFeeExempt = _exempt;
    }

    function getFeePercentage() external view returns (uint256) {
        return BASE_REFLECTION_FEE + BASE_LIQUIDITY_FEE + BASE_TEAM_FEE;
    }

    function getReflectionBalance(address holder) external view returns (uint256) {
        if (isExcludedFromReflection[holder]) return 0;
        uint256 currentReflectionIndex = reflectionIndex;
        uint256 lastIndex = lastReflectionIndex[holder];
        uint256 holderBalance = balanceOf(holder);
        if (holderBalance == 0 || currentReflectionIndex <= lastIndex) {
            return reflectionBalance[holder];
        }
        uint256 reflectionAmount = (holderBalance * (currentReflectionIndex - lastIndex)) / REFLECTION_DENOMINATOR;
        return reflectionBalance[holder] + reflectionAmount;
    }
}
