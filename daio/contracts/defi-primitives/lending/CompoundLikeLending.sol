// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title CompoundLikeLending
 * @notice Compound-style lending protocol with DAIO integration
 * @dev Interest-bearing token lending with constitutional compliance
 */
contract CompoundLikeLending is ERC20, AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    bytes32 public constant PROTOCOL_ADMIN_ROLE = keccak256("PROTOCOL_ADMIN_ROLE");
    bytes32 public constant RISK_MANAGER_ROLE = keccak256("RISK_MANAGER_ROLE");
    bytes32 public constant LIQUIDATOR_ROLE = keccak256("LIQUIDATOR_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");

    // Market configuration
    struct Market {
        IERC20 underlyingToken;         // Underlying asset (e.g., USDC, WETH)
        uint256 exchangeRate;           // Current exchange rate (underlying per cToken)
        uint256 totalBorrows;           // Total amount borrowed
        uint256 totalReserves;          // Protocol reserves
        uint256 borrowIndex;            // Accumulator of the total earned interest rate
        uint256 lastUpdateTime;         // Last time interest was accrued
        uint256 reserveFactor;          // Percentage of interest to reserve (BPS)
        uint256 collateralFactor;       // Percentage of collateral value usable as collateral (BPS)
        uint256 liquidationIncentive;   // Liquidation incentive percentage (BPS)
        uint256 borrowCap;              // Maximum borrowable amount
        uint256 supplyCap;              // Maximum suppliable amount
        bool isListed;                  // Whether market is listed
        bool mintPaused;                // Whether supply is paused
        bool borrowPaused;              // Whether borrowing is paused
    }

    // Borrower account information
    struct BorrowSnapshot {
        uint256 principal;              // Principal borrowed amount
        uint256 interestIndex;          // Last index at which interest was calculated
        uint256 timestamp;              // Last interaction timestamp
    }

    // Interest rate model
    struct InterestRateModel {
        uint256 baseRate;               // Base interest rate (BPS)
        uint256 multiplier;             // Rate increase per utilization (BPS)
        uint256 jumpMultiplier;         // Jump rate multiplier after kink (BPS)
        uint256 kink;                   // Utilization rate at which jump multiplier kicks in (BPS)
    }

    // DAIO Constitutional Integration
    struct ConstitutionalLimits {
        uint256 titheRate;              // 15% tithe to DAIO treasury (BPS)
        uint256 maxSingleBorrow;        // 15% max single borrow of reserves (BPS)
        uint256 maxTotalExposure;       // Maximum total lending exposure
        address treasuryContract;       // DAIO treasury contract
        address executiveGovernance;    // CEO + Seven Soldiers contract
        bool constitutionalCompliance;  // Whether constitutional compliance is enforced
    }

    // State variables
    Market public market;
    InterestRateModel public interestModel;
    ConstitutionalLimits public constitutionalLimits;

    mapping(address => BorrowSnapshot) public accountBorrows;
    mapping(address => uint256) public accountTokens;  // cToken balance tracking

    uint256 public constant INITIAL_EXCHANGE_RATE = 0.02e18; // 0.02 underlying per cToken
    uint256 public constant EXCHANGE_RATE_SCALE = 1e18;
    uint256 public constant INTEREST_RATE_SCALE = 1e18;
    uint256 public constant BLOCKS_PER_YEAR = 2102400; // Assuming 15 second blocks

    // Fee collection tracking
    uint256 public totalFeesCollected;
    uint256 public totalTithePaid;
    uint256 public totalLiquidationFees;

    // Events
    event Supply(address indexed user, uint256 underlyingAmount, uint256 cTokenAmount);
    event Redeem(address indexed user, uint256 cTokenAmount, uint256 underlyingAmount);
    event Borrow(address indexed borrower, uint256 borrowAmount);
    event RepayBorrow(address indexed borrower, uint256 repayAmount);
    event LiquidateBorrow(
        address indexed liquidator,
        address indexed borrower,
        uint256 repayAmount,
        address cTokenCollateral,
        uint256 seizeTokens
    );
    event InterestAccrued(
        uint256 interestAccumulated,
        uint256 borrowIndex,
        uint256 totalBorrows
    );
    event ReservesReduced(address admin, uint256 amount);
    event NewReserveFactor(uint256 oldReserveFactor, uint256 newReserveFactor);
    event ConstitutionalComplianceChecked(bool compliant, string reason);

    /**
     * @notice Initialize Compound-like lending market
     * @param _underlyingToken Underlying token to lend/borrow
     * @param _name cToken name
     * @param _symbol cToken symbol
     * @param _treasuryContract DAIO treasury contract
     * @param _executiveGovernance CEO + Seven Soldiers governance
     * @param admin Admin address for role management
     */
    constructor(
        IERC20 _underlyingToken,
        string memory _name,
        string memory _symbol,
        address _treasuryContract,
        address _executiveGovernance,
        address admin
    ) ERC20(_name, _symbol) {
        require(address(_underlyingToken) != address(0), "Invalid underlying token");
        require(admin != address(0), "Invalid admin address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PROTOCOL_ADMIN_ROLE, admin);
        _grantRole(RISK_MANAGER_ROLE, admin);
        _grantRole(LIQUIDATOR_ROLE, admin);
        _grantRole(TREASURY_ROLE, admin);

        // Initialize market
        market = Market({
            underlyingToken: _underlyingToken,
            exchangeRate: INITIAL_EXCHANGE_RATE,
            totalBorrows: 0,
            totalReserves: 0,
            borrowIndex: EXCHANGE_RATE_SCALE,
            lastUpdateTime: block.timestamp,
            reserveFactor: 1500,        // 15% reserve factor
            collateralFactor: 7500,     // 75% collateral factor
            liquidationIncentive: 500,  // 5% liquidation incentive
            borrowCap: 10000000e18,     // 10M token borrow cap
            supplyCap: 50000000e18,     // 50M token supply cap
            isListed: true,
            mintPaused: false,
            borrowPaused: false
        });

        // Initialize interest rate model (similar to Compound)
        interestModel = InterestRateModel({
            baseRate: 200,              // 2% base rate
            multiplier: 2000,           // 20% multiplier
            jumpMultiplier: 10000,      // 100% jump multiplier
            kink: 8000                  // 80% utilization kink
        });

        // Initialize DAIO constitutional integration
        constitutionalLimits = ConstitutionalLimits({
            titheRate: 1500,                    // 15% tithe rate (constitutional requirement)
            maxSingleBorrow: 1500,              // 15% max single borrow (constitutional limit)
            maxTotalExposure: 100000000e18,     // 100M maximum exposure
            treasuryContract: _treasuryContract,
            executiveGovernance: _executiveGovernance,
            constitutionalCompliance: true
        });
    }

    /**
     * @notice Supply underlying tokens to the market
     * @param mintAmount Amount of underlying tokens to supply
     * @return actualMintAmount Actual amount supplied
     */
    function supply(uint256 mintAmount) external nonReentrant whenNotPaused returns (uint256 actualMintAmount) {
        require(!market.mintPaused, "Market supply is paused");
        require(mintAmount > 0, "Cannot supply zero amount");

        // Accrue interest before any state changes
        accrueInterest();

        // Check supply cap
        uint256 totalSupplyUnderlying = (totalSupply() * market.exchangeRate) / EXCHANGE_RATE_SCALE;
        require(totalSupplyUnderlying + mintAmount <= market.supplyCap, "Supply cap exceeded");

        // Check constitutional compliance for large supplies
        _checkConstitutionalCompliance(mintAmount, true, "supply");

        // Calculate cTokens to mint
        uint256 cTokensToMint = (mintAmount * EXCHANGE_RATE_SCALE) / market.exchangeRate;
        require(cTokensToMint > 0, "Zero cTokens would be minted");

        // Transfer underlying tokens from user
        market.underlyingToken.safeTransferFrom(msg.sender, address(this), mintAmount);

        // Mint cTokens to user
        _mint(msg.sender, cTokensToMint);

        emit Supply(msg.sender, mintAmount, cTokensToMint);
        return mintAmount;
    }

    /**
     * @notice Redeem cTokens for underlying tokens
     * @param redeemTokens Amount of cTokens to redeem
     * @return redeemAmount Amount of underlying tokens redeemed
     */
    function redeem(uint256 redeemTokens) external nonReentrant returns (uint256 redeemAmount) {
        require(redeemTokens > 0, "Cannot redeem zero tokens");
        require(balanceOf(msg.sender) >= redeemTokens, "Insufficient cToken balance");

        // Accrue interest before any state changes
        accrueInterest();

        // Calculate underlying amount to redeem
        redeemAmount = (redeemTokens * market.exchangeRate) / EXCHANGE_RATE_SCALE;

        // Check if enough cash available
        uint256 cashAvailable = getCashAvailable();
        require(redeemAmount <= cashAvailable, "Insufficient cash");

        // Check constitutional compliance for large redemptions
        _checkConstitutionalCompliance(redeemAmount, false, "redeem");

        // Burn cTokens
        _burn(msg.sender, redeemTokens);

        // Transfer underlying to user
        market.underlyingToken.safeTransfer(msg.sender, redeemAmount);

        emit Redeem(msg.sender, redeemTokens, redeemAmount);
        return redeemAmount;
    }

    /**
     * @notice Redeem underlying tokens for cTokens
     * @param redeemAmount Amount of underlying tokens to redeem
     * @return redeemTokens Amount of cTokens burned
     */
    function redeemUnderlying(uint256 redeemAmount) external nonReentrant returns (uint256 redeemTokens) {
        require(redeemAmount > 0, "Cannot redeem zero amount");

        // Accrue interest before any state changes
        accrueInterest();

        // Calculate cTokens needed
        redeemTokens = (redeemAmount * EXCHANGE_RATE_SCALE) / market.exchangeRate;
        require(balanceOf(msg.sender) >= redeemTokens, "Insufficient cToken balance");

        // Check if enough cash available
        uint256 cashAvailable = getCashAvailable();
        require(redeemAmount <= cashAvailable, "Insufficient cash");

        // Check constitutional compliance for large redemptions
        _checkConstitutionalCompliance(redeemAmount, false, "redeemUnderlying");

        // Burn cTokens
        _burn(msg.sender, redeemTokens);

        // Transfer underlying to user
        market.underlyingToken.safeTransfer(msg.sender, redeemAmount);

        emit Redeem(msg.sender, redeemTokens, redeemAmount);
        return redeemTokens;
    }

    /**
     * @notice Borrow underlying tokens
     * @param borrowAmount Amount to borrow
     * @return actualBorrowAmount Actual amount borrowed
     */
    function borrow(uint256 borrowAmount) external nonReentrant whenNotPaused returns (uint256 actualBorrowAmount) {
        require(!market.borrowPaused, "Market borrowing is paused");
        require(borrowAmount > 0, "Cannot borrow zero amount");

        // Accrue interest before any state changes
        accrueInterest();

        // Check borrow cap
        require(market.totalBorrows + borrowAmount <= market.borrowCap, "Borrow cap exceeded");

        // Check constitutional compliance
        require(
            borrowAmount <= (getCashAvailable() * constitutionalLimits.maxSingleBorrow) / 10000,
            "Single borrow exceeds constitutional limit"
        );
        _checkConstitutionalCompliance(borrowAmount, true, "borrow");

        // Check cash available
        uint256 cashAvailable = getCashAvailable();
        require(borrowAmount <= cashAvailable, "Insufficient cash");

        // Check if borrower has sufficient collateral
        // This would integrate with a comptroller in a full implementation
        // For now, we'll require the borrower to have cTokens as collateral
        require(balanceOf(msg.sender) > 0, "No collateral");

        uint256 collateralValue = (balanceOf(msg.sender) * market.exchangeRate * market.collateralFactor) / (EXCHANGE_RATE_SCALE * 10000);
        require(borrowAmount <= collateralValue, "Insufficient collateral");

        // Update borrower's borrow snapshot
        BorrowSnapshot storage borrowSnapshot = accountBorrows[msg.sender];
        uint256 currentBorrowBalance = getBorrowBalance(msg.sender);

        borrowSnapshot.principal = currentBorrowBalance + borrowAmount;
        borrowSnapshot.interestIndex = market.borrowIndex;
        borrowSnapshot.timestamp = block.timestamp;

        // Update market state
        market.totalBorrows += borrowAmount;

        // Transfer tokens to borrower
        market.underlyingToken.safeTransfer(msg.sender, borrowAmount);

        emit Borrow(msg.sender, borrowAmount);
        return borrowAmount;
    }

    /**
     * @notice Repay borrowed amount
     * @param repayAmount Amount to repay (use type(uint256).max for full repayment)
     * @return actualRepayAmount Actual amount repaid
     */
    function repayBorrow(uint256 repayAmount) external nonReentrant returns (uint256 actualRepayAmount) {
        require(repayAmount > 0, "Cannot repay zero amount");

        // Accrue interest before any state changes
        accrueInterest();

        uint256 currentBorrowBalance = getBorrowBalance(msg.sender);
        require(currentBorrowBalance > 0, "No outstanding borrow");

        // Handle full repayment
        if (repayAmount == type(uint256).max) {
            actualRepayAmount = currentBorrowBalance;
        } else {
            actualRepayAmount = repayAmount;
        }

        // Cannot repay more than owed
        if (actualRepayAmount > currentBorrowBalance) {
            actualRepayAmount = currentBorrowBalance;
        }

        // Update borrower's borrow snapshot
        BorrowSnapshot storage borrowSnapshot = accountBorrows[msg.sender];
        borrowSnapshot.principal = currentBorrowBalance - actualRepayAmount;
        borrowSnapshot.interestIndex = market.borrowIndex;
        borrowSnapshot.timestamp = block.timestamp;

        // Update market state
        market.totalBorrows -= actualRepayAmount;

        // Transfer repayment from borrower
        market.underlyingToken.safeTransferFrom(msg.sender, address(this), actualRepayAmount);

        emit RepayBorrow(msg.sender, actualRepayAmount);
        return actualRepayAmount;
    }

    /**
     * @notice Liquidate an undercollateralized borrow
     * @param borrower Address of borrower to liquidate
     * @param repayAmount Amount to repay
     * @return seizedAmount Amount of collateral seized
     */
    function liquidateBorrow(
        address borrower,
        uint256 repayAmount
    ) external nonReentrant onlyRole(LIQUIDATOR_ROLE) returns (uint256 seizedAmount) {
        require(borrower != msg.sender, "Cannot liquidate self");
        require(repayAmount > 0, "Cannot liquidate zero amount");

        // Accrue interest before any state changes
        accrueInterest();

        uint256 currentBorrowBalance = getBorrowBalance(borrower);
        require(currentBorrowBalance > 0, "No outstanding borrow to liquidate");

        // Check if borrower is undercollateralized
        uint256 collateralValue = (balanceOf(borrower) * market.exchangeRate * market.collateralFactor) / (EXCHANGE_RATE_SCALE * 10000);
        require(currentBorrowBalance > collateralValue, "Borrower not undercollateralized");

        // Calculate maximum liquidation amount (50% of outstanding borrow)
        uint256 maxLiquidation = currentBorrowBalance / 2;
        if (repayAmount > maxLiquidation) {
            repayAmount = maxLiquidation;
        }

        // Calculate collateral to seize (with liquidation incentive)
        uint256 collateralPrice = market.exchangeRate; // Simplified price calculation
        seizedAmount = (repayAmount * (10000 + market.liquidationIncentive) * EXCHANGE_RATE_SCALE) / (10000 * collateralPrice);

        // Cannot seize more collateral than borrower has
        if (seizedAmount > balanceOf(borrower)) {
            seizedAmount = balanceOf(borrower);
            // Recalculate repay amount based on available collateral
            repayAmount = (seizedAmount * collateralPrice * 10000) / ((10000 + market.liquidationIncentive) * EXCHANGE_RATE_SCALE);
        }

        // Update borrower's borrow snapshot
        BorrowSnapshot storage borrowSnapshot = accountBorrows[borrower];
        borrowSnapshot.principal = currentBorrowBalance - repayAmount;
        borrowSnapshot.interestIndex = market.borrowIndex;
        borrowSnapshot.timestamp = block.timestamp;

        // Update market state
        market.totalBorrows -= repayAmount;

        // Transfer repayment from liquidator
        market.underlyingToken.safeTransferFrom(msg.sender, address(this), repayAmount);

        // Transfer seized collateral to liquidator
        _transfer(borrower, msg.sender, seizedAmount);

        // Calculate and distribute liquidation fees
        uint256 liquidationFee = (seizedAmount * 100) / 10000; // 1% liquidation fee
        if (liquidationFee > 0) {
            _transfer(msg.sender, address(this), liquidationFee);
            totalLiquidationFees += liquidationFee;
            _distributeFees(liquidationFee);
        }

        emit LiquidateBorrow(msg.sender, borrower, repayAmount, address(this), seizedAmount);
        return seizedAmount;
    }

    /**
     * @notice Accrue interest on borrows
     */
    function accrueInterest() public {
        uint256 currentTime = block.timestamp;
        uint256 timeDelta = currentTime - market.lastUpdateTime;

        if (timeDelta == 0) {
            return;
        }

        uint256 cashPrior = getCashAvailable();
        uint256 borrowsPrior = market.totalBorrows;
        uint256 reservesPrior = market.totalReserves;

        // Calculate interest rate
        uint256 borrowRate = getBorrowRate(cashPrior, borrowsPrior, reservesPrior);

        // Calculate interest accumulation
        uint256 interestAccumulated = (borrowsPrior * borrowRate * timeDelta) / (INTEREST_RATE_SCALE * 365 days);

        // Update total borrows
        uint256 totalBorrowsNew = borrowsPrior + interestAccumulated;

        // Calculate reserves (based on reserve factor)
        uint256 totalReservesNew = reservesPrior + (interestAccumulated * market.reserveFactor) / 10000;

        // Update borrow index
        uint256 borrowIndexNew = market.borrowIndex;
        if (borrowsPrior > 0) {
            borrowIndexNew += (market.borrowIndex * interestAccumulated) / borrowsPrior;
        }

        // Update exchange rate
        uint256 totalSupply_ = totalSupply();
        if (totalSupply_ > 0) {
            uint256 totalCash = cashPrior + interestAccumulated;
            market.exchangeRate = ((totalCash + totalBorrowsNew - totalReservesNew) * EXCHANGE_RATE_SCALE) / totalSupply_;
        }

        // Update market state
        market.totalBorrows = totalBorrowsNew;
        market.totalReserves = totalReservesNew;
        market.borrowIndex = borrowIndexNew;
        market.lastUpdateTime = currentTime;

        // Distribute fees to DAIO treasury
        if (interestAccumulated > 0) {
            _distributeFees(interestAccumulated);
        }

        emit InterestAccrued(interestAccumulated, borrowIndexNew, totalBorrowsNew);
    }

    /**
     * @notice Get current borrow rate
     * @param cash Available cash
     * @param borrows Total borrows
     * @param reserves Total reserves
     * @return borrowRate Current borrow rate per second
     */
    function getBorrowRate(uint256 cash, uint256 borrows, uint256 reserves) public view returns (uint256 borrowRate) {
        uint256 totalSupply_ = cash + borrows - reserves;
        if (totalSupply_ == 0) return interestModel.baseRate;

        uint256 utilizationRate = (borrows * 10000) / totalSupply_;

        if (utilizationRate <= interestModel.kink) {
            return interestModel.baseRate + (utilizationRate * interestModel.multiplier) / 10000;
        } else {
            uint256 normalRate = interestModel.baseRate + (interestModel.kink * interestModel.multiplier) / 10000;
            uint256 excessUtil = utilizationRate - interestModel.kink;
            return normalRate + (excessUtil * interestModel.jumpMultiplier) / 10000;
        }
    }

    /**
     * @notice Get current supply rate
     * @param cash Available cash
     * @param borrows Total borrows
     * @param reserves Total reserves
     * @param reserveFactor Reserve factor
     * @return supplyRate Current supply rate per second
     */
    function getSupplyRate(uint256 cash, uint256 borrows, uint256 reserves, uint256 reserveFactor) public view returns (uint256 supplyRate) {
        uint256 totalSupply_ = cash + borrows - reserves;
        if (totalSupply_ == 0) return 0;

        uint256 borrowRate = getBorrowRate(cash, borrows, reserves);
        uint256 rateToPool = borrowRate * (10000 - reserveFactor) / 10000;
        return (rateToPool * borrows) / totalSupply_;
    }

    /**
     * @notice Get borrower's current borrow balance
     * @param borrower Address of borrower
     * @return borrowBalance Current borrow balance with accrued interest
     */
    function getBorrowBalance(address borrower) public view returns (uint256 borrowBalance) {
        BorrowSnapshot storage borrowSnapshot = accountBorrows[borrower];
        if (borrowSnapshot.principal == 0) {
            return 0;
        }

        return (borrowSnapshot.principal * market.borrowIndex) / borrowSnapshot.interestIndex;
    }

    /**
     * @notice Get available cash
     * @return cashBalance Available cash balance
     */
    function getCashAvailable() public view returns (uint256 cashBalance) {
        return market.underlyingToken.balanceOf(address(this));
    }

    /**
     * @notice Get market utilization rate
     * @return utilizationRate Current utilization rate (BPS)
     */
    function getUtilizationRate() public view returns (uint256 utilizationRate) {
        uint256 cash = getCashAvailable();
        uint256 borrows = market.totalBorrows;
        uint256 reserves = market.totalReserves;
        uint256 totalSupply_ = cash + borrows - reserves;

        if (totalSupply_ == 0) return 0;
        return (borrows * 10000) / totalSupply_;
    }

    /**
     * @notice Update interest rate model
     * @param baseRate New base rate
     * @param multiplier New multiplier
     * @param jumpMultiplier New jump multiplier
     * @param kink New kink point
     */
    function updateInterestRateModel(
        uint256 baseRate,
        uint256 multiplier,
        uint256 jumpMultiplier,
        uint256 kink
    ) external onlyRole(PROTOCOL_ADMIN_ROLE) {
        require(kink <= 10000, "Invalid kink");

        interestModel.baseRate = baseRate;
        interestModel.multiplier = multiplier;
        interestModel.jumpMultiplier = jumpMultiplier;
        interestModel.kink = kink;
    }

    /**
     * @notice Update market configuration
     * @param reserveFactor New reserve factor (BPS)
     * @param collateralFactor New collateral factor (BPS)
     * @param liquidationIncentive New liquidation incentive (BPS)
     */
    function updateMarketConfig(
        uint256 reserveFactor,
        uint256 collateralFactor,
        uint256 liquidationIncentive
    ) external onlyRole(RISK_MANAGER_ROLE) {
        require(reserveFactor <= 5000, "Reserve factor too high"); // Max 50%
        require(collateralFactor <= 9000, "Collateral factor too high"); // Max 90%
        require(liquidationIncentive <= 2000, "Liquidation incentive too high"); // Max 20%

        market.reserveFactor = reserveFactor;
        market.collateralFactor = collateralFactor;
        market.liquidationIncentive = liquidationIncentive;
    }

    /**
     * @notice Reduce reserves (send to treasury)
     * @param reduceAmount Amount to reduce
     */
    function reduceReserves(uint256 reduceAmount) external onlyRole(TREASURY_ROLE) {
        require(reduceAmount <= market.totalReserves, "Cannot reduce more than total reserves");

        market.totalReserves -= reduceAmount;

        // Send to DAIO treasury
        if (constitutionalLimits.treasuryContract != address(0)) {
            market.underlyingToken.safeTransfer(constitutionalLimits.treasuryContract, reduceAmount);
        }

        emit ReservesReduced(msg.sender, reduceAmount);
    }

    /**
     * @notice Pause/unpause market operations
     * @param mintPaused Whether to pause minting
     * @param borrowPaused Whether to pause borrowing
     */
    function setMarketPaused(bool mintPaused, bool borrowPaused) external onlyRole(PROTOCOL_ADMIN_ROLE) {
        market.mintPaused = mintPaused;
        market.borrowPaused = borrowPaused;
    }

    /**
     * @notice Emergency pause all operations
     */
    function emergencyPause() external onlyRole(PROTOCOL_ADMIN_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause all operations
     */
    function unpause() external onlyRole(PROTOCOL_ADMIN_ROLE) {
        _unpause();
    }

    // Internal Functions

    function _distributeFees(uint256 feeAmount) internal {
        if (constitutionalLimits.treasuryContract != address(0) && constitutionalLimits.titheRate > 0) {
            uint256 titheAmount = (feeAmount * constitutionalLimits.titheRate) / 10000;
            if (titheAmount > 0 && titheAmount <= getCashAvailable()) {
                market.underlyingToken.safeTransfer(constitutionalLimits.treasuryContract, titheAmount);
                totalTithePaid += titheAmount;
                totalFeesCollected += feeAmount;
            }
        }
    }

    function _checkConstitutionalCompliance(uint256 amount, bool isSupplyOrBorrow, string memory operation) internal {
        if (!constitutionalLimits.constitutionalCompliance) return;

        string memory reason = "Operation within constitutional limits";
        bool compliant = true;

        if (isSupplyOrBorrow) {
            // Check maximum exposure limits
            if (amount > constitutionalLimits.maxTotalExposure) {
                reason = "Amount exceeds maximum constitutional exposure";
                compliant = false;
            }
        }

        emit ConstitutionalComplianceChecked(compliant, reason);
        require(compliant, reason);
    }

    /**
     * @notice Get market information
     * @return marketInfo Current market state
     */
    function getMarketInfo() external view returns (Market memory marketInfo) {
        return market;
    }

    /**
     * @notice Get interest rate model
     * @return model Current interest rate model
     */
    function getInterestRateModel() external view returns (InterestRateModel memory model) {
        return interestModel;
    }

    /**
     * @notice Get constitutional limits
     * @return limits Current constitutional limits
     */
    function getConstitutionalLimits() external view returns (ConstitutionalLimits memory limits) {
        return constitutionalLimits;
    }
}