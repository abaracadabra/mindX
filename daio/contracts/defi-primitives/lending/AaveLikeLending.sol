// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title AaveLikeLending
 * @notice Aave-style lending protocol with DAIO integration
 * @dev Separate aToken (interest-bearing) and debt token implementation
 */
contract AaveLikeLending is AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    bytes32 public constant POOL_ADMIN_ROLE = keccak256("POOL_ADMIN_ROLE");
    bytes32 public constant RISK_MANAGER_ROLE = keccak256("RISK_MANAGER_ROLE");
    bytes32 public constant LIQUIDATOR_ROLE = keccak256("LIQUIDATOR_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Reserve configuration
    struct ReserveData {
        IERC20 underlyingAsset;         // Underlying asset
        AToken aToken;                  // Interest-bearing token
        DebtToken stableDebtToken;      // Stable rate debt token
        DebtToken variableDebtToken;    // Variable rate debt token
        uint256 liquidityIndex;         // Cumulative liquidity index
        uint256 variableBorrowIndex;    // Cumulative variable borrow index
        uint256 currentLiquidityRate;   // Current liquidity rate
        uint256 currentVariableBorrowRate; // Current variable borrow rate
        uint256 currentStableBorrowRate; // Current stable borrow rate
        uint256 lastUpdateTimestamp;    // Last update timestamp
        uint256 ltv;                    // Loan to value ratio (BPS)
        uint256 liquidationThreshold;   // Liquidation threshold (BPS)
        uint256 liquidationBonus;       // Liquidation bonus (BPS)
        uint256 reserveFactor;          // Reserve factor (BPS)
        uint256 supplyCap;              // Supply cap
        uint256 borrowCap;              // Borrow cap
        bool isActive;                  // Whether reserve is active
        bool isFrozen;                  // Whether reserve is frozen
        bool borrowingEnabled;          // Whether borrowing is enabled
        bool stableBorrowRateEnabled;   // Whether stable borrowing is enabled
    }

    // User account data
    struct UserAccountData {
        uint256 totalCollateralETH;
        uint256 totalDebtETH;
        uint256 availableBorrowsETH;
        uint256 currentLiquidationThreshold;
        uint256 ltv;
        uint256 healthFactor;
    }

    // Interest rate strategy
    struct InterestRateStrategy {
        uint256 baseVariableBorrowRate;
        uint256 variableRateSlope1;
        uint256 variableRateSlope2;
        uint256 stableRateSlope1;
        uint256 stableRateSlope2;
        uint256 optimalUtilizationRate;
        uint256 maxExcessUtilizationRate;
        uint256 baseStableBorrowRate;
    }

    // DAIO Constitutional Integration
    struct ConstitutionalLimits {
        uint256 titheRate;              // 15% tithe to DAIO treasury (BPS)
        uint256 maxSingleDeposit;       // 15% max single deposit of total liquidity (BPS)
        uint256 maxTotalExposure;       // Maximum total lending exposure
        uint256 liquidationProtocolFee; // Protocol fee on liquidations (BPS)
        address treasuryContract;       // DAIO treasury contract
        address executiveGovernance;    // CEO + Seven Soldiers contract
        address priceOracle;            // Price oracle for asset valuation
        bool constitutionalCompliance;  // Whether constitutional compliance is enforced
    }

    // Flash loan data
    struct FlashLoanLocalVars {
        uint256[] amounts;
        address[] assets;
        uint256[] premiums;
        uint256[] modes;
        address onBehalfOf;
        bytes params;
    }

    // State variables
    mapping(address => ReserveData) public reserves;
    mapping(address => mapping(address => bool)) public userUseReserveAsCollateral;
    mapping(address => bool) public reservesList;
    address[] public reservesArray;

    InterestRateStrategy public defaultInterestRateStrategy;
    ConstitutionalLimits public constitutionalLimits;

    uint256 public constant HEALTH_FACTOR_LIQUIDATION_THRESHOLD = 1e18;
    uint256 public constant LIQUIDATION_CLOSE_FACTOR_HF_THRESHOLD = 0.95e18;
    uint256 public constant MAX_RESERVES_COUNT = 128;

    // Fee tracking
    uint256 public totalFeesCollected;
    uint256 public totalTithePaid;
    uint256 public totalLiquidationFees;
    uint256 public totalFlashLoanFees;

    // Flash loan configuration
    uint256 public flashLoanPremiumTotal = 9; // 0.09%
    uint256 public flashLoanPremiumToProtocol = 3000; // 30% of total premium

    // Events
    event Supply(
        address indexed reserve,
        address user,
        address indexed onBehalfOf,
        uint256 amount,
        uint16 indexed referral
    );
    event Withdraw(
        address indexed reserve,
        address indexed user,
        address indexed to,
        uint256 amount
    );
    event Borrow(
        address indexed reserve,
        address user,
        address indexed onBehalfOf,
        uint256 amount,
        uint256 borrowRateMode,
        uint256 borrowRate,
        uint16 indexed referral
    );
    event Repay(
        address indexed reserve,
        address indexed user,
        address indexed repayer,
        uint256 amount
    );
    event LiquidationCall(
        address indexed collateralAsset,
        address indexed debtAsset,
        address indexed user,
        uint256 debtToCover,
        uint256 liquidatedCollateralAmount,
        address liquidator,
        bool receiveAToken
    );
    event FlashLoan(
        address indexed target,
        address indexed initiator,
        address indexed asset,
        uint256 amount,
        uint256 premium,
        uint16 referralCode
    );
    event ReserveActivated(address indexed asset);
    event ReserveDeactivated(address indexed asset);
    event ConstitutionalComplianceChecked(bool compliant, string reason, uint256 amount);

    /**
     * @notice Initialize Aave-like lending pool
     * @param _treasuryContract DAIO treasury contract
     * @param _executiveGovernance CEO + Seven Soldiers governance
     * @param _priceOracle Price oracle contract
     * @param admin Admin address for role management
     */
    constructor(
        address _treasuryContract,
        address _executiveGovernance,
        address _priceOracle,
        address admin
    ) {
        require(admin != address(0), "Invalid admin address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(POOL_ADMIN_ROLE, admin);
        _grantRole(RISK_MANAGER_ROLE, admin);
        _grantRole(LIQUIDATOR_ROLE, admin);
        _grantRole(TREASURY_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);

        // Initialize default interest rate strategy (similar to Aave)
        defaultInterestRateStrategy = InterestRateStrategy({
            baseVariableBorrowRate: 0,
            variableRateSlope1: 400,        // 4%
            variableRateSlope2: 6000,       // 60%
            stableRateSlope1: 500,          // 5%
            stableRateSlope2: 6000,         // 60%
            optimalUtilizationRate: 8000,   // 80%
            maxExcessUtilizationRate: 2000, // 20%
            baseStableBorrowRate: 200       // 2%
        });

        // Initialize DAIO constitutional integration
        constitutionalLimits = ConstitutionalLimits({
            titheRate: 1500,                    // 15% tithe rate (constitutional requirement)
            maxSingleDeposit: 1500,             // 15% max single deposit (constitutional limit)
            maxTotalExposure: 1000000000e18,    // 1B maximum exposure
            liquidationProtocolFee: 300,        // 3% protocol fee on liquidations
            treasuryContract: _treasuryContract,
            executiveGovernance: _executiveGovernance,
            priceOracle: _priceOracle,
            constitutionalCompliance: true
        });
    }

    /**
     * @notice Supply assets to the protocol
     * @param asset Address of the underlying asset
     * @param amount Amount to be supplied
     * @param onBehalfOf Address receiving the aTokens
     * @param referralCode Referral code for integrators
     */
    function supply(
        address asset,
        uint256 amount,
        address onBehalfOf,
        uint16 referralCode
    ) external nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be greater than 0");
        require(onBehalfOf != address(0), "Invalid onBehalfOf address");

        ReserveData storage reserve = reserves[asset];
        require(reserve.isActive, "Reserve not active");
        require(!reserve.isFrozen, "Reserve is frozen");

        _updateReserveData(asset);

        // Check constitutional compliance
        _checkConstitutionalCompliance(amount, true, "supply");

        // Check supply cap
        uint256 currentTotalSupply = reserve.aToken.totalSupply();
        require(currentTotalSupply + amount <= reserve.supplyCap, "Supply cap exceeded");

        // Transfer asset from user
        IERC20(asset).safeTransferFrom(msg.sender, address(reserve.aToken), amount);

        // Calculate aTokens to mint (with liquidity index)
        uint256 amountScaled = (amount * 1e27) / reserve.liquidityIndex;

        // Mint aTokens to user
        reserve.aToken.mint(onBehalfOf, amountScaled);

        emit Supply(asset, msg.sender, onBehalfOf, amount, referralCode);
    }

    /**
     * @notice Withdraw assets from the protocol
     * @param asset Address of the underlying asset
     * @param amount Amount to withdraw (use type(uint256).max for full balance)
     * @param to Address receiving the assets
     * @return actualAmount Actual amount withdrawn
     */
    function withdraw(
        address asset,
        uint256 amount,
        address to
    ) external nonReentrant returns (uint256 actualAmount) {
        require(to != address(0), "Invalid to address");

        ReserveData storage reserve = reserves[asset];
        require(reserve.isActive, "Reserve not active");

        _updateReserveData(asset);

        uint256 userBalance = reserve.aToken.balanceOf(msg.sender);
        require(userBalance > 0, "No aTokens to withdraw");

        // Handle max withdrawal
        if (amount == type(uint256).max) {
            actualAmount = userBalance;
        } else {
            actualAmount = amount;
        }

        require(actualAmount <= userBalance, "Not enough aTokens");

        // Check if withdrawal would leave user undercollateralized
        _validateHealthFactorAfterWithdraw(asset, msg.sender, actualAmount);

        // Calculate underlying amount with liquidity index
        uint256 amountToWithdraw = (actualAmount * reserve.liquidityIndex) / 1e27;

        // Check constitutional compliance for large withdrawals
        _checkConstitutionalCompliance(amountToWithdraw, false, "withdraw");

        // Burn aTokens
        reserve.aToken.burn(msg.sender, actualAmount);

        // Transfer underlying asset to user
        IERC20(asset).safeTransfer(to, amountToWithdraw);

        emit Withdraw(asset, msg.sender, to, amountToWithdraw);
        return amountToWithdraw;
    }

    /**
     * @notice Borrow assets from the protocol
     * @param asset Address of the underlying asset
     * @param amount Amount to borrow
     * @param interestRateMode Interest rate mode (1 = stable, 2 = variable)
     * @param referralCode Referral code for integrators
     * @param onBehalfOf Address receiving the borrowed assets
     */
    function borrow(
        address asset,
        uint256 amount,
        uint256 interestRateMode,
        uint16 referralCode,
        address onBehalfOf
    ) external nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be greater than 0");
        require(onBehalfOf != address(0), "Invalid onBehalfOf address");
        require(interestRateMode == 1 || interestRateMode == 2, "Invalid interest rate mode");

        ReserveData storage reserve = reserves[asset];
        require(reserve.isActive, "Reserve not active");
        require(reserve.borrowingEnabled, "Borrowing not enabled");

        if (interestRateMode == 1) {
            require(reserve.stableBorrowRateEnabled, "Stable borrowing not enabled");
        }

        _updateReserveData(asset);

        // Check constitutional compliance
        require(
            amount <= (IERC20(asset).balanceOf(address(reserve.aToken)) * constitutionalLimits.maxSingleDeposit) / 10000,
            "Single borrow exceeds constitutional limit"
        );
        _checkConstitutionalCompliance(amount, true, "borrow");

        // Check borrow cap
        uint256 totalStableDebt = reserve.stableDebtToken.totalSupply();
        uint256 totalVariableDebt = reserve.variableDebtToken.totalSupply();
        require(totalStableDebt + totalVariableDebt + amount <= reserve.borrowCap, "Borrow cap exceeded");

        // Validate borrowing power
        UserAccountData memory accountData = _getUserAccountData(onBehalfOf);
        require(accountData.availableBorrowsETH > 0, "No borrowing power");

        // Convert amount to ETH for comparison
        uint256 amountETH = _getAssetPrice(asset) * amount / 1e18;
        require(amountETH <= accountData.availableBorrowsETH, "Insufficient borrowing power");

        // Mint debt tokens
        if (interestRateMode == 1) {
            // Stable rate borrow
            reserve.stableDebtToken.mint(onBehalfOf, amount, reserve.currentStableBorrowRate);
        } else {
            // Variable rate borrow
            reserve.variableDebtToken.mint(onBehalfOf, amount);
        }

        // Transfer borrowed asset to user
        reserve.aToken.transferUnderlyingTo(onBehalfOf, amount);

        emit Borrow(
            asset,
            onBehalfOf,
            onBehalfOf,
            amount,
            interestRateMode,
            interestRateMode == 1 ? reserve.currentStableBorrowRate : reserve.currentVariableBorrowRate,
            referralCode
        );
    }

    /**
     * @notice Repay borrowed assets
     * @param asset Address of the underlying asset
     * @param amount Amount to repay (use type(uint256).max for full repayment)
     * @param rateMode Interest rate mode (1 = stable, 2 = variable)
     * @param onBehalfOf Address of the borrower
     * @return actualAmount Actual amount repaid
     */
    function repay(
        address asset,
        uint256 amount,
        uint256 rateMode,
        address onBehalfOf
    ) external nonReentrant returns (uint256 actualAmount) {
        require(amount > 0, "Amount must be greater than 0");
        require(rateMode == 1 || rateMode == 2, "Invalid rate mode");

        ReserveData storage reserve = reserves[asset];
        require(reserve.isActive, "Reserve not active");

        _updateReserveData(asset);

        uint256 debtBalance;
        if (rateMode == 1) {
            debtBalance = reserve.stableDebtToken.balanceOf(onBehalfOf);
        } else {
            debtBalance = reserve.variableDebtToken.balanceOf(onBehalfOf);
        }

        require(debtBalance > 0, "No debt to repay");

        // Handle full repayment
        if (amount == type(uint256).max) {
            actualAmount = debtBalance;
        } else {
            actualAmount = amount > debtBalance ? debtBalance : amount;
        }

        // Transfer repayment from user to aToken
        IERC20(asset).safeTransferFrom(msg.sender, address(reserve.aToken), actualAmount);

        // Burn debt tokens
        if (rateMode == 1) {
            reserve.stableDebtToken.burn(onBehalfOf, actualAmount);
        } else {
            reserve.variableDebtToken.burn(onBehalfOf, actualAmount);
        }

        emit Repay(asset, onBehalfOf, msg.sender, actualAmount);
        return actualAmount;
    }

    /**
     * @notice Liquidate undercollateralized position
     * @param collateralAsset Address of collateral asset
     * @param debtAsset Address of debt asset
     * @param user Address of borrower to liquidate
     * @param debtToCover Amount of debt to cover
     * @param receiveAToken True to receive aTokens, false to receive underlying
     */
    function liquidationCall(
        address collateralAsset,
        address debtAsset,
        address user,
        uint256 debtToCover,
        bool receiveAToken
    ) external nonReentrant {
        require(user != msg.sender, "Cannot liquidate self");
        require(debtToCover > 0, "Debt to cover must be greater than 0");

        ReserveData storage debtReserve = reserves[debtAsset];
        ReserveData storage collateralReserve = reserves[collateralAsset];

        require(debtReserve.isActive && collateralReserve.isActive, "Reserves not active");

        _updateReserveData(debtAsset);
        _updateReserveData(collateralAsset);

        // Validate user can be liquidated
        UserAccountData memory accountData = _getUserAccountData(user);
        require(
            accountData.healthFactor < HEALTH_FACTOR_LIQUIDATION_THRESHOLD,
            "Health factor not below liquidation threshold"
        );

        // Calculate liquidation amounts
        uint256 userDebtBalance = debtReserve.stableDebtToken.balanceOf(user) +
                                debtReserve.variableDebtToken.balanceOf(user);

        uint256 maxLiquidatableDebt = userDebtBalance;
        if (accountData.healthFactor > LIQUIDATION_CLOSE_FACTOR_HF_THRESHOLD) {
            maxLiquidatableDebt = userDebtBalance / 2; // 50% liquidation limit
        }

        if (debtToCover > maxLiquidatableDebt) {
            debtToCover = maxLiquidatableDebt;
        }

        // Calculate collateral to seize
        uint256 liquidationBonus = collateralReserve.liquidationBonus;
        uint256 debtAssetPrice = _getAssetPrice(debtAsset);
        uint256 collateralAssetPrice = _getAssetPrice(collateralAsset);

        uint256 collateralAmount = (debtToCover * debtAssetPrice * (10000 + liquidationBonus)) /
                                  (collateralAssetPrice * 10000);

        // Limit collateral seizure to available collateral
        uint256 userCollateralBalance = collateralReserve.aToken.balanceOf(user);
        if (collateralAmount > userCollateralBalance) {
            collateralAmount = userCollateralBalance;
        }

        // Perform liquidation
        IERC20(debtAsset).safeTransferFrom(msg.sender, address(debtReserve.aToken), debtToCover);

        // Burn debt tokens proportionally
        uint256 stableDebt = debtReserve.stableDebtToken.balanceOf(user);
        uint256 variableDebt = debtReserve.variableDebtToken.balanceOf(user);
        uint256 totalDebt = stableDebt + variableDebt;

        if (stableDebt > 0) {
            uint256 stableDebtToBurn = (debtToCover * stableDebt) / totalDebt;
            debtReserve.stableDebtToken.burn(user, stableDebtToBurn);
        }

        if (variableDebt > 0) {
            uint256 variableDebtToBurn = (debtToCover * variableDebt) / totalDebt;
            debtReserve.variableDebtToken.burn(user, variableDebtToBurn);
        }

        // Transfer collateral
        if (receiveAToken) {
            collateralReserve.aToken.transferFrom(user, msg.sender, collateralAmount);
        } else {
            collateralReserve.aToken.burn(user, collateralAmount);
            uint256 collateralAmountToSend = (collateralAmount * collateralReserve.liquidityIndex) / 1e27;
            IERC20(collateralAsset).safeTransfer(msg.sender, collateralAmountToSend);
        }

        // Collect and distribute liquidation fees
        uint256 protocolFee = (collateralAmount * constitutionalLimits.liquidationProtocolFee) / 10000;
        if (protocolFee > 0) {
            collateralReserve.aToken.burn(user, protocolFee);
            totalLiquidationFees += protocolFee;
            _distributeFees(collateralAsset, protocolFee);
        }

        emit LiquidationCall(
            collateralAsset,
            debtAsset,
            user,
            debtToCover,
            collateralAmount,
            msg.sender,
            receiveAToken
        );
    }

    /**
     * @notice Flash loan function
     * @param receiverAddress Address of flash loan receiver contract
     * @param assets Assets to flash loan
     * @param amounts Amounts to flash loan
     * @param modes Interest rate modes (0 = no open debt, 1 = stable, 2 = variable)
     * @param onBehalfOf Address for whom debt tokens will be minted
     * @param params Additional parameters
     * @param referralCode Referral code
     */
    function flashLoan(
        address receiverAddress,
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata modes,
        address onBehalfOf,
        bytes calldata params,
        uint16 referralCode
    ) external nonReentrant {
        require(receiverAddress != address(0), "Invalid receiver address");
        require(assets.length == amounts.length, "Arrays length mismatch");
        require(assets.length == modes.length, "Arrays length mismatch");

        FlashLoanLocalVars memory vars;
        vars.assets = assets;
        vars.amounts = amounts;
        vars.modes = modes;
        vars.onBehalfOf = onBehalfOf;
        vars.params = params;

        // Calculate premiums
        vars.premiums = new uint256[](assets.length);
        for (uint256 i = 0; i < assets.length; i++) {
            vars.premiums[i] = (amounts[i] * flashLoanPremiumTotal) / 10000;
        }

        // Transfer assets to receiver
        for (uint256 i = 0; i < assets.length; i++) {
            ReserveData storage reserve = reserves[assets[i]];
            require(reserve.isActive, "Reserve not active");

            uint256 availableLiquidity = IERC20(assets[i]).balanceOf(address(reserve.aToken));
            require(amounts[i] <= availableLiquidity, "Insufficient liquidity");

            reserve.aToken.transferUnderlyingTo(receiverAddress, amounts[i]);
        }

        // Execute flash loan callback
        require(
            IFlashLoanReceiver(receiverAddress).executeOperation(
                assets,
                amounts,
                vars.premiums,
                msg.sender,
                params
            ),
            "Flash loan execution failed"
        );

        // Collect repayments and fees
        for (uint256 i = 0; i < assets.length; i++) {
            uint256 amountPlusPremium = amounts[i] + vars.premiums[i];

            if (modes[i] == 0) {
                // No debt, collect full amount plus premium
                IERC20(assets[i]).safeTransferFrom(receiverAddress, address(reserves[assets[i]].aToken), amountPlusPremium);
            } else {
                // Open debt position, collect premium only
                IERC20(assets[i]).safeTransferFrom(receiverAddress, address(reserves[assets[i]].aToken), vars.premiums[i]);

                // Mint debt tokens
                if (modes[i] == 1) {
                    reserves[assets[i]].stableDebtToken.mint(onBehalfOf, amounts[i], reserves[assets[i]].currentStableBorrowRate);
                } else {
                    reserves[assets[i]].variableDebtToken.mint(onBehalfOf, amounts[i]);
                }
            }

            // Distribute flash loan fees
            _distributeFees(assets[i], vars.premiums[i]);
            totalFlashLoanFees += vars.premiums[i];

            emit FlashLoan(
                receiverAddress,
                msg.sender,
                assets[i],
                amounts[i],
                vars.premiums[i],
                referralCode
            );
        }
    }

    /**
     * @notice Initialize a new reserve
     * @param asset Address of the underlying asset
     * @param aTokenAddress Address of the corresponding aToken
     * @param stableDebtTokenAddress Address of stable debt token
     * @param variableDebtTokenAddress Address of variable debt token
     */
    function initReserve(
        address asset,
        address aTokenAddress,
        address stableDebtTokenAddress,
        address variableDebtTokenAddress
    ) external onlyRole(POOL_ADMIN_ROLE) {
        require(!reservesList[asset], "Reserve already initialized");
        require(reservesArray.length < MAX_RESERVES_COUNT, "Too many reserves");

        reserves[asset] = ReserveData({
            underlyingAsset: IERC20(asset),
            aToken: AToken(aTokenAddress),
            stableDebtToken: DebtToken(stableDebtTokenAddress),
            variableDebtToken: DebtToken(variableDebtTokenAddress),
            liquidityIndex: 1e27,
            variableBorrowIndex: 1e27,
            currentLiquidityRate: 0,
            currentVariableBorrowRate: 0,
            currentStableBorrowRate: 0,
            lastUpdateTimestamp: block.timestamp,
            ltv: 8000,                      // 80% LTV
            liquidationThreshold: 8500,      // 85% liquidation threshold
            liquidationBonus: 500,          // 5% liquidation bonus
            reserveFactor: 1500,            // 15% reserve factor (constitutional requirement)
            supplyCap: 0,                   // No supply cap initially
            borrowCap: 0,                   // No borrow cap initially
            isActive: true,
            isFrozen: false,
            borrowingEnabled: true,
            stableBorrowRateEnabled: true
        });

        reservesList[asset] = true;
        reservesArray.push(asset);

        emit ReserveActivated(asset);
    }

    /**
     * @notice Set use reserve as collateral
     * @param asset Address of the reserve
     * @param useAsCollateral True to use as collateral
     */
    function setUserUseReserveAsCollateral(address asset, bool useAsCollateral) external {
        userUseReserveAsCollateral[msg.sender][asset] = useAsCollateral;
    }

    /**
     * @notice Get user account data
     * @param user Address of user
     * @return totalCollateralETH Total collateral in ETH
     * @return totalDebtETH Total debt in ETH
     * @return availableBorrowsETH Available borrowing power in ETH
     * @return currentLiquidationThreshold Current liquidation threshold
     * @return ltv Loan to value ratio
     * @return healthFactor Health factor
     */
    function getUserAccountData(address user)
        external
        view
        returns (
            uint256 totalCollateralETH,
            uint256 totalDebtETH,
            uint256 availableBorrowsETH,
            uint256 currentLiquidationThreshold,
            uint256 ltv,
            uint256 healthFactor
        )
    {
        UserAccountData memory accountData = _getUserAccountData(user);
        return (
            accountData.totalCollateralETH,
            accountData.totalDebtETH,
            accountData.availableBorrowsETH,
            accountData.currentLiquidationThreshold,
            accountData.ltv,
            accountData.healthFactor
        );
    }

    // Internal Functions

    function _updateReserveData(address asset) internal {
        ReserveData storage reserve = reserves[asset];

        uint256 timeDelta = block.timestamp - reserve.lastUpdateTimestamp;
        if (timeDelta == 0) return;

        uint256 totalDebt = reserve.stableDebtToken.totalSupply() + reserve.variableDebtToken.totalSupply();
        uint256 availableLiquidity = IERC20(asset).balanceOf(address(reserve.aToken));

        // Update interest rates and indexes
        (uint256 newLiquidityRate, uint256 newVariableBorrowRate, uint256 newStableBorrowRate) =
            _calculateInterestRates(availableLiquidity, totalDebt, reserve.reserveFactor);

        reserve.currentLiquidityRate = newLiquidityRate;
        reserve.currentVariableBorrowRate = newVariableBorrowRate;
        reserve.currentStableBorrowRate = newStableBorrowRate;

        // Update liquidity index
        if (newLiquidityRate > 0) {
            uint256 cumulatedLiquidityInterest = ((newLiquidityRate * timeDelta) / 365 days) + 1e27;
            reserve.liquidityIndex = (reserve.liquidityIndex * cumulatedLiquidityInterest) / 1e27;
        }

        // Update variable borrow index
        if (newVariableBorrowRate > 0) {
            uint256 cumulatedVariableBorrowInterest = ((newVariableBorrowRate * timeDelta) / 365 days) + 1e27;
            reserve.variableBorrowIndex = (reserve.variableBorrowIndex * cumulatedVariableBorrowInterest) / 1e27;
        }

        reserve.lastUpdateTimestamp = block.timestamp;
    }

    function _calculateInterestRates(
        uint256 availableLiquidity,
        uint256 totalDebt,
        uint256 reserveFactor
    ) internal view returns (uint256 liquidityRate, uint256 variableBorrowRate, uint256 stableBorrowRate) {
        uint256 totalLiquidity = availableLiquidity + totalDebt;

        if (totalLiquidity == 0) {
            return (0, defaultInterestRateStrategy.baseVariableBorrowRate, defaultInterestRateStrategy.baseStableBorrowRate);
        }

        uint256 utilizationRate = (totalDebt * 1e27) / totalLiquidity;

        // Calculate variable borrow rate
        if (utilizationRate <= defaultInterestRateStrategy.optimalUtilizationRate) {
            variableBorrowRate = defaultInterestRateStrategy.baseVariableBorrowRate +
                (utilizationRate * defaultInterestRateStrategy.variableRateSlope1) / defaultInterestRateStrategy.optimalUtilizationRate;
        } else {
            uint256 excessUtilizationRate = utilizationRate - defaultInterestRateStrategy.optimalUtilizationRate;
            variableBorrowRate = defaultInterestRateStrategy.baseVariableBorrowRate +
                defaultInterestRateStrategy.variableRateSlope1 +
                (excessUtilizationRate * defaultInterestRateStrategy.variableRateSlope2) / defaultInterestRateStrategy.maxExcessUtilizationRate;
        }

        // Calculate stable borrow rate
        stableBorrowRate = defaultInterestRateStrategy.baseStableBorrowRate + defaultInterestRateStrategy.stableRateSlope1;

        // Calculate liquidity rate
        liquidityRate = ((variableBorrowRate * utilizationRate) / 1e27) * (10000 - reserveFactor) / 10000;
    }

    function _getUserAccountData(address user) internal view returns (UserAccountData memory) {
        UserAccountData memory accountData;

        for (uint256 i = 0; i < reservesArray.length; i++) {
            address currentReserveAddress = reservesArray[i];
            ReserveData memory currentReserve = reserves[currentReserveAddress];

            if (!currentReserve.isActive) continue;

            uint256 assetPrice = _getAssetPrice(currentReserveAddress);

            // Calculate collateral
            uint256 aTokenBalance = currentReserve.aToken.balanceOf(user);
            if (aTokenBalance > 0 && userUseReserveAsCollateral[user][currentReserveAddress]) {
                uint256 underlyingBalance = (aTokenBalance * currentReserve.liquidityIndex) / 1e27;
                uint256 collateralETH = (underlyingBalance * assetPrice) / 1e18;

                accountData.totalCollateralETH += collateralETH;

                // Weighted averages for LTV and liquidation threshold
                accountData.ltv += collateralETH * currentReserve.ltv;
                accountData.currentLiquidationThreshold += collateralETH * currentReserve.liquidationThreshold;
            }

            // Calculate debt
            uint256 stableDebt = currentReserve.stableDebtToken.balanceOf(user);
            uint256 variableDebt = currentReserve.variableDebtToken.balanceOf(user);
            uint256 totalDebt = stableDebt + variableDebt;

            if (totalDebt > 0) {
                uint256 debtETH = (totalDebt * assetPrice) / 1e18;
                accountData.totalDebtETH += debtETH;
            }
        }

        // Finalize calculations
        if (accountData.totalCollateralETH > 0) {
            accountData.ltv = accountData.ltv / accountData.totalCollateralETH;
            accountData.currentLiquidationThreshold = accountData.currentLiquidationThreshold / accountData.totalCollateralETH;
        }

        accountData.availableBorrowsETH = (accountData.totalCollateralETH * accountData.ltv) / 10000;
        if (accountData.availableBorrowsETH > accountData.totalDebtETH) {
            accountData.availableBorrowsETH -= accountData.totalDebtETH;
        } else {
            accountData.availableBorrowsETH = 0;
        }

        // Calculate health factor
        if (accountData.totalDebtETH > 0) {
            accountData.healthFactor = (accountData.totalCollateralETH * accountData.currentLiquidationThreshold) /
                                      (accountData.totalDebtETH * 10000);
        } else {
            accountData.healthFactor = type(uint256).max;
        }

        return accountData;
    }

    function _getAssetPrice(address asset) internal view returns (uint256) {
        // This would integrate with the price oracle
        // For now, return 1e18 as a placeholder (1 ETH = 1 asset)
        return 1e18;
    }

    function _validateHealthFactorAfterWithdraw(address asset, address user, uint256 amount) internal view {
        // Simplified health factor check - in production would calculate actual post-withdrawal health factor
        UserAccountData memory accountData = _getUserAccountData(user);
        require(accountData.healthFactor >= HEALTH_FACTOR_LIQUIDATION_THRESHOLD, "Health factor too low");
    }

    function _distributeFees(address asset, uint256 feeAmount) internal {
        if (constitutionalLimits.treasuryContract != address(0) && constitutionalLimits.titheRate > 0) {
            uint256 titheAmount = (feeAmount * constitutionalLimits.titheRate) / 10000;
            if (titheAmount > 0) {
                // Convert to underlying amount and transfer to treasury
                uint256 underlyingAmount = (titheAmount * reserves[asset].liquidityIndex) / 1e27;
                if (underlyingAmount <= IERC20(asset).balanceOf(address(reserves[asset].aToken))) {
                    reserves[asset].aToken.transferUnderlyingTo(constitutionalLimits.treasuryContract, underlyingAmount);
                    totalTithePaid += underlyingAmount;
                    totalFeesCollected += feeAmount;
                }
            }
        }
    }

    function _checkConstitutionalCompliance(uint256 amount, bool isDepositOrBorrow, string memory operation) internal {
        if (!constitutionalLimits.constitutionalCompliance) return;

        string memory reason = "Operation within constitutional limits";
        bool compliant = true;

        if (isDepositOrBorrow) {
            // Check maximum exposure limits
            if (amount > constitutionalLimits.maxTotalExposure) {
                reason = "Amount exceeds maximum constitutional exposure";
                compliant = false;
            }
        }

        emit ConstitutionalComplianceChecked(compliant, reason, amount);
        require(compliant, reason);
    }

    /**
     * @notice Emergency pause all operations
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause all operations
     */
    function unpause() external onlyRole(EMERGENCY_ROLE) {
        _unpause();
    }
}

// Supporting contracts interfaces

interface AToken {
    function mint(address user, uint256 amount) external;
    function burn(address user, uint256 amount) external;
    function balanceOf(address user) external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transferUnderlyingTo(address user, uint256 amount) external;
}

interface DebtToken {
    function mint(address user, uint256 amount, uint256 rate) external;
    function mint(address user, uint256 amount) external;
    function burn(address user, uint256 amount) external;
    function balanceOf(address user) external view returns (uint256);
    function totalSupply() external view returns (uint256);
}

interface IFlashLoanReceiver {
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}