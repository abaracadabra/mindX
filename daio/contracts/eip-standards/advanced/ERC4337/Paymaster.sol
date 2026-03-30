// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title Paymaster
 * @dev ERC4337 Paymaster implementation with DAIO integration
 *
 * Features:
 * - Gasless transactions for corporate accounts
 * - Token-based gas payments (pay gas with ERC20 tokens)
 * - Sponsored transactions with limits and policies
 * - DAIO governance integration for policy management
 * - Emergency controls and circuit breakers
 * - Subscription-based sponsorship models
 *
 * @author DAIO Development Team
 */

interface IEntryPoint {
    struct UserOperation {
        address sender;
        uint256 nonce;
        bytes initCode;
        bytes callData;
        uint256 callGasLimit;
        uint256 verificationGasLimit;
        uint256 preVerificationGas;
        uint256 maxFeePerGas;
        uint256 maxPriorityFeePerGas;
        bytes paymasterAndData;
        bytes signature;
    }

    function balanceOf(address account) external view returns (uint256);
    function depositTo(address account) external payable;
    function withdrawTo(address payable withdrawAddress, uint256 withdrawAmount) external;
}

interface IPaymaster {
    enum PostOpMode {
        opSucceeded,
        opReverted,
        postOpReverted
    }

    function validatePaymasterUserOp(
        IEntryPoint.UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost
    ) external returns (bytes memory context, uint256 validationData);

    function postOp(
        PostOpMode mode,
        bytes calldata context,
        uint256 actualGasCost
    ) external;
}

interface IDAIO_Constitution_Enhanced {
    function validatePaymasterSponsorship(
        address paymaster,
        address account,
        uint256 maxCost,
        bytes calldata paymasterData
    ) external view returns (bool valid, string memory reason);
}

interface IExecutiveGovernance {
    function hasExecutiveApproval(address account) external view returns (bool);
    function hasPaymasterManagerRole(address account) external view returns (bool);
}

interface ITreasury {
    function collectPaymasterFee(
        address paymaster,
        uint256 amount
    ) external;

    function reimbursePaymaster(
        address paymaster,
        uint256 amount
    ) external;
}

contract Paymaster is IPaymaster, AccessControl, ReentrancyGuard {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    // =============================================================
    //                        CONSTANTS
    // =============================================================

    bytes32 public constant PAYMASTER_MANAGER_ROLE = keccak256("PAYMASTER_MANAGER_ROLE");
    bytes32 public constant SPONSOR_ROLE = keccak256("SPONSOR_ROLE");
    bytes32 public constant POLICY_MANAGER_ROLE = keccak256("POLICY_MANAGER_ROLE");

    uint256 public constant SPONSORSHIP_TYPE_UNLIMITED = 0;
    uint256 public constant SPONSORSHIP_TYPE_LIMITED = 1;
    uint256 public constant SPONSORSHIP_TYPE_TOKEN_PAYMENT = 2;
    uint256 public constant SPONSORSHIP_TYPE_SUBSCRIPTION = 3;

    // =============================================================
    //                         STORAGE
    // =============================================================

    // Core ERC4337
    IEntryPoint public immutable entryPoint;

    // DAIO Integration
    IDAIO_Constitution_Enhanced public immutable constitution;
    IExecutiveGovernance public immutable governance;
    ITreasury public immutable treasury;

    // Sponsorship policies
    struct SponsorshipPolicy {
        uint256 sponsorshipType;
        uint256 dailyLimit;
        uint256 perTransactionLimit;
        uint256 monthlyLimit;
        bool requiresApproval;
        address[] allowedTargets;
        mapping(address => bool) isAllowedTarget;
        bytes4[] allowedSelectors;
        mapping(bytes4 => bool) isAllowedSelector;
        bool active;
    }

    mapping(address => SponsorshipPolicy) public sponsorshipPolicies;
    address[] public sponsoredAccounts;

    // Token payment configuration
    struct TokenConfig {
        IERC20 token;
        uint256 pricePerGas; // Token price per gas unit
        uint256 priceUpdateTime;
        address priceOracle;
        bool active;
    }

    mapping(address => TokenConfig) public supportedTokens;
    address[] public tokenList;

    // Subscription model
    struct Subscription {
        uint256 tier;
        uint256 validUntil;
        uint256 gasAllowance;
        uint256 gasUsed;
        uint256 price;
        bool active;
    }

    mapping(address => Subscription) public subscriptions;

    struct SubscriptionTier {
        string name;
        uint256 gasAllowance;
        uint256 duration; // Duration in seconds
        uint256 price;
        bool active;
    }

    mapping(uint256 => SubscriptionTier) public subscriptionTiers;
    uint256 public subscriptionTierCount;

    // Usage tracking
    struct UsageStats {
        uint256 dailySpent;
        uint256 monthlySpent;
        uint256 lastResetDay;
        uint256 lastResetMonth;
        uint256 totalSponsored;
        uint256 transactionCount;
    }

    mapping(address => UsageStats) public usageStats;

    // Emergency controls
    bool public paused;
    uint256 public globalDailyLimit;
    uint256 public globalDailySpent;
    uint256 public lastGlobalResetDay;

    // Verifying signer for approvals
    address public verifyingSigner;

    // Events
    event PaymasterInitialized(address indexed entryPoint, address indexed verifyingSigner);
    event SponsorshipPolicySet(address indexed account, uint256 sponsorshipType);
    event TokenSupportAdded(address indexed token, uint256 pricePerGas);
    event TokenSupportRemoved(address indexed token);
    event SubscriptionTierCreated(uint256 indexed tier, string name, uint256 gasAllowance, uint256 price);
    event SubscriptionPurchased(address indexed account, uint256 indexed tier, uint256 validUntil);
    event UserOperationSponsored(address indexed account, uint256 actualGasCost, uint256 sponsorshipType);
    event EmergencyPause(bool paused);
    event GlobalLimitUpdated(uint256 newLimit);
    event VerifyingSignerUpdated(address indexed newSigner);

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor(
        address entryPointAddress,
        address constitutionAddress,
        address governanceAddress,
        address treasuryAddress,
        address admin,
        address _verifyingSigner
    ) {
        require(entryPointAddress != address(0), "Invalid entry point");

        entryPoint = IEntryPoint(entryPointAddress);
        constitution = IDAIO_Constitution_Enhanced(constitutionAddress);
        governance = IExecutiveGovernance(governanceAddress);
        treasury = ITreasury(treasuryAddress);
        verifyingSigner = _verifyingSigner;

        // Set up access control
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PAYMASTER_MANAGER_ROLE, admin);
        _grantRole(POLICY_MANAGER_ROLE, admin);

        // Set reasonable global daily limit (100 ETH worth of gas)
        globalDailyLimit = 100 ether;

        emit PaymasterInitialized(entryPointAddress, _verifyingSigner);
    }

    // =============================================================
    //                  ERC4337 IMPLEMENTATION
    // =============================================================

    /**
     * @dev Validate paymaster user operation
     */
    function validatePaymasterUserOp(
        IEntryPoint.UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost
    ) external override returns (bytes memory context, uint256 validationData) {
        require(msg.sender == address(entryPoint), "Only EntryPoint can call");
        require(!paused, "Paymaster paused");

        // Validate with DAIO constitution
        (bool valid, string memory reason) = constitution.validatePaymasterSponsorship(
            address(this),
            userOp.sender,
            maxCost,
            userOp.paymasterAndData
        );
        require(valid, reason);

        // Check global limits
        require(_checkGlobalLimits(maxCost), "Global daily limit exceeded");

        // Parse paymaster data
        (uint256 sponsorshipType, bytes memory sponsorshipData) = _parsePaymasterData(userOp.paymasterAndData);

        // Validate sponsorship based on type
        if (sponsorshipType == SPONSORSHIP_TYPE_UNLIMITED) {
            return _validateUnlimitedSponsorship(userOp, userOpHash, maxCost);
        } else if (sponsorshipType == SPONSORSHIP_TYPE_LIMITED) {
            return _validateLimitedSponsorship(userOp, userOpHash, maxCost, sponsorshipData);
        } else if (sponsorshipType == SPONSORSHIP_TYPE_TOKEN_PAYMENT) {
            return _validateTokenPayment(userOp, userOpHash, maxCost, sponsorshipData);
        } else if (sponsorshipType == SPONSORSHIP_TYPE_SUBSCRIPTION) {
            return _validateSubscriptionSponsorship(userOp, userOpHash, maxCost, sponsorshipData);
        } else {
            revert("Invalid sponsorship type");
        }
    }

    /**
     * @dev Post-operation processing
     */
    function postOp(
        PostOpMode mode,
        bytes calldata context,
        uint256 actualGasCost
    ) external override {
        require(msg.sender == address(entryPoint), "Only EntryPoint can call");

        (address account, uint256 sponsorshipType, bytes memory additionalData) =
            abi.decode(context, (address, uint256, bytes));

        // Update usage statistics
        _updateUsageStats(account, actualGasCost);

        // Handle post-op based on sponsorship type
        if (sponsorshipType == SPONSORSHIP_TYPE_TOKEN_PAYMENT) {
            _handleTokenPaymentPostOp(account, actualGasCost, additionalData, mode);
        } else if (sponsorshipType == SPONSORSHIP_TYPE_SUBSCRIPTION) {
            _handleSubscriptionPostOp(account, actualGasCost, mode);
        }

        // Collect fees to treasury (5% of gas cost)
        uint256 treasuryFee = actualGasCost * 500 / 10000; // 5%
        if (treasuryFee > 0) {
            treasury.collectPaymasterFee(address(this), treasuryFee);
        }

        emit UserOperationSponsored(account, actualGasCost, sponsorshipType);
    }

    // =============================================================
    //                   SPONSORSHIP POLICIES
    // =============================================================

    /**
     * @dev Set sponsorship policy for an account
     */
    function setSponsorshipPolicy(
        address account,
        uint256 sponsorshipType,
        uint256 dailyLimit,
        uint256 perTransactionLimit,
        uint256 monthlyLimit,
        bool requiresApproval,
        address[] calldata allowedTargets,
        bytes4[] calldata allowedSelectors
    ) external onlyRole(POLICY_MANAGER_ROLE) {
        SponsorshipPolicy storage policy = sponsorshipPolicies[account];
        policy.sponsorshipType = sponsorshipType;
        policy.dailyLimit = dailyLimit;
        policy.perTransactionLimit = perTransactionLimit;
        policy.monthlyLimit = monthlyLimit;
        policy.requiresApproval = requiresApproval;
        policy.active = true;

        // Set allowed targets
        for (uint256 i = 0; i < allowedTargets.length; i++) {
            policy.allowedTargets.push(allowedTargets[i]);
            policy.isAllowedTarget[allowedTargets[i]] = true;
        }

        // Set allowed selectors
        for (uint256 i = 0; i < allowedSelectors.length; i++) {
            policy.allowedSelectors.push(allowedSelectors[i]);
            policy.isAllowedSelector[allowedSelectors[i]] = true;
        }

        // Add to sponsored accounts list
        bool exists = false;
        for (uint256 i = 0; i < sponsoredAccounts.length; i++) {
            if (sponsoredAccounts[i] == account) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            sponsoredAccounts.push(account);
        }

        emit SponsorshipPolicySet(account, sponsorshipType);
    }

    /**
     * @dev Remove sponsorship for an account
     */
    function removeSponsorshipPolicy(address account) external onlyRole(POLICY_MANAGER_ROLE) {
        sponsorshipPolicies[account].active = false;

        // Remove from sponsored accounts list
        for (uint256 i = 0; i < sponsoredAccounts.length; i++) {
            if (sponsoredAccounts[i] == account) {
                sponsoredAccounts[i] = sponsoredAccounts[sponsoredAccounts.length - 1];
                sponsoredAccounts.pop();
                break;
            }
        }
    }

    // =============================================================
    //                   TOKEN PAYMENT SUPPORT
    // =============================================================

    /**
     * @dev Add support for token-based gas payment
     */
    function addTokenSupport(
        address token,
        uint256 pricePerGas,
        address priceOracle
    ) external onlyRole(PAYMASTER_MANAGER_ROLE) {
        require(token != address(0), "Invalid token");

        TokenConfig storage config = supportedTokens[token];
        config.token = IERC20(token);
        config.pricePerGas = pricePerGas;
        config.priceUpdateTime = block.timestamp;
        config.priceOracle = priceOracle;
        config.active = true;

        // Add to token list if not already present
        bool exists = false;
        for (uint256 i = 0; i < tokenList.length; i++) {
            if (tokenList[i] == token) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            tokenList.push(token);
        }

        emit TokenSupportAdded(token, pricePerGas);
    }

    /**
     * @dev Remove token support
     */
    function removeTokenSupport(address token) external onlyRole(PAYMASTER_MANAGER_ROLE) {
        supportedTokens[token].active = false;

        // Remove from token list
        for (uint256 i = 0; i < tokenList.length; i++) {
            if (tokenList[i] == token) {
                tokenList[i] = tokenList[tokenList.length - 1];
                tokenList.pop();
                break;
            }
        }

        emit TokenSupportRemoved(token);
    }

    // =============================================================
    //                  SUBSCRIPTION MANAGEMENT
    // =============================================================

    /**
     * @dev Create subscription tier
     */
    function createSubscriptionTier(
        string calldata name,
        uint256 gasAllowance,
        uint256 duration,
        uint256 price
    ) external onlyRole(PAYMASTER_MANAGER_ROLE) {
        uint256 tierId = subscriptionTierCount++;

        subscriptionTiers[tierId] = SubscriptionTier({
            name: name,
            gasAllowance: gasAllowance,
            duration: duration,
            price: price,
            active: true
        });

        emit SubscriptionTierCreated(tierId, name, gasAllowance, price);
    }

    /**
     * @dev Purchase subscription
     */
    function purchaseSubscription(uint256 tierId) external payable nonReentrant {
        SubscriptionTier storage tier = subscriptionTiers[tierId];
        require(tier.active, "Subscription tier not active");
        require(msg.value >= tier.price, "Insufficient payment");

        Subscription storage subscription = subscriptions[msg.sender];
        subscription.tier = tierId;
        subscription.validUntil = block.timestamp + tier.duration;
        subscription.gasAllowance = tier.gasAllowance;
        subscription.gasUsed = 0;
        subscription.price = tier.price;
        subscription.active = true;

        // Refund excess payment
        if (msg.value > tier.price) {
            payable(msg.sender).transfer(msg.value - tier.price);
        }

        emit SubscriptionPurchased(msg.sender, tierId, subscription.validUntil);
    }

    // =============================================================
    //                   INTERNAL VALIDATION
    // =============================================================

    /**
     * @dev Validate unlimited sponsorship
     */
    function _validateUnlimitedSponsorship(
        IEntryPoint.UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost
    ) internal view returns (bytes memory context, uint256 validationData) {
        SponsorshipPolicy storage policy = sponsorshipPolicies[userOp.sender];
        require(policy.active && policy.sponsorshipType == SPONSORSHIP_TYPE_UNLIMITED, "Policy not found");

        if (policy.requiresApproval) {
            // Verify signature from verifying signer
            bytes memory signature = userOp.paymasterAndData[20:]; // Skip address prefix
            bytes32 hash = keccak256(abi.encodePacked(userOpHash, maxCost)).toEthSignedMessageHash();
            address recovered = hash.recover(signature);
            require(recovered == verifyingSigner, "Invalid approval signature");
        }

        context = abi.encode(userOp.sender, SPONSORSHIP_TYPE_UNLIMITED, "");
        validationData = 0; // Success
    }

    /**
     * @dev Validate limited sponsorship
     */
    function _validateLimitedSponsorship(
        IEntryPoint.UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost,
        bytes memory sponsorshipData
    ) internal returns (bytes memory context, uint256 validationData) {
        SponsorshipPolicy storage policy = sponsorshipPolicies[userOp.sender];
        require(policy.active && policy.sponsorshipType == SPONSORSHIP_TYPE_LIMITED, "Policy not found");

        // Check limits
        UsageStats storage usage = usageStats[userOp.sender];
        require(_checkDailyLimit(userOp.sender, maxCost), "Daily limit exceeded");
        require(_checkMonthlyLimit(userOp.sender, maxCost), "Monthly limit exceeded");
        require(maxCost <= policy.perTransactionLimit, "Per-transaction limit exceeded");

        context = abi.encode(userOp.sender, SPONSORSHIP_TYPE_LIMITED, sponsorshipData);
        validationData = 0; // Success
    }

    /**
     * @dev Validate token payment
     */
    function _validateTokenPayment(
        IEntryPoint.UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost,
        bytes memory sponsorshipData
    ) internal view returns (bytes memory context, uint256 validationData) {
        address tokenAddress = abi.decode(sponsorshipData, (address));
        TokenConfig storage tokenConfig = supportedTokens[tokenAddress];
        require(tokenConfig.active, "Token not supported");

        uint256 tokenAmount = maxCost * tokenConfig.pricePerGas;
        require(tokenConfig.token.balanceOf(userOp.sender) >= tokenAmount, "Insufficient token balance");
        require(tokenConfig.token.allowance(userOp.sender, address(this)) >= tokenAmount, "Insufficient allowance");

        context = abi.encode(userOp.sender, SPONSORSHIP_TYPE_TOKEN_PAYMENT, sponsorshipData);
        validationData = 0; // Success
    }

    /**
     * @dev Validate subscription sponsorship
     */
    function _validateSubscriptionSponsorship(
        IEntryPoint.UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost,
        bytes memory sponsorshipData
    ) internal view returns (bytes memory context, uint256 validationData) {
        Subscription storage subscription = subscriptions[userOp.sender];
        require(subscription.active, "No active subscription");
        require(block.timestamp <= subscription.validUntil, "Subscription expired");
        require(subscription.gasUsed + maxCost <= subscription.gasAllowance, "Gas allowance exceeded");

        context = abi.encode(userOp.sender, SPONSORSHIP_TYPE_SUBSCRIPTION, sponsorshipData);
        validationData = 0; // Success
    }

    // =============================================================
    //                    POST-OP HANDLERS
    // =============================================================

    /**
     * @dev Handle token payment post-op
     */
    function _handleTokenPaymentPostOp(
        address account,
        uint256 actualGasCost,
        bytes memory additionalData,
        PostOpMode mode
    ) internal {
        if (mode == PostOpMode.postOpReverted) return;

        address tokenAddress = abi.decode(additionalData, (address));
        TokenConfig storage tokenConfig = supportedTokens[tokenAddress];

        uint256 tokenAmount = actualGasCost * tokenConfig.pricePerGas;
        tokenConfig.token.transferFrom(account, address(this), tokenAmount);
    }

    /**
     * @dev Handle subscription post-op
     */
    function _handleSubscriptionPostOp(
        address account,
        uint256 actualGasCost,
        PostOpMode mode
    ) internal {
        if (mode == PostOpMode.postOpReverted) return;

        Subscription storage subscription = subscriptions[account];
        subscription.gasUsed += actualGasCost;
    }

    // =============================================================
    //                      HELPER FUNCTIONS
    // =============================================================

    /**
     * @dev Parse paymaster data
     */
    function _parsePaymasterData(bytes calldata paymasterAndData) internal pure returns (
        uint256 sponsorshipType,
        bytes memory sponsorshipData
    ) {
        require(paymasterAndData.length >= 24, "Invalid paymaster data"); // 20 bytes address + 4 bytes type

        sponsorshipType = uint32(bytes4(paymasterAndData[20:24]));
        if (paymasterAndData.length > 24) {
            sponsorshipData = paymasterAndData[24:];
        }
    }

    /**
     * @dev Check global daily limits
     */
    function _checkGlobalLimits(uint256 amount) internal returns (bool) {
        uint256 today = block.timestamp / 1 days;

        if (lastGlobalResetDay < today) {
            globalDailySpent = 0;
            lastGlobalResetDay = today;
        }

        if (globalDailySpent + amount > globalDailyLimit) {
            return false;
        }

        globalDailySpent += amount;
        return true;
    }

    /**
     * @dev Check daily limit for account
     */
    function _checkDailyLimit(address account, uint256 amount) internal returns (bool) {
        SponsorshipPolicy storage policy = sponsorshipPolicies[account];
        UsageStats storage usage = usageStats[account];

        uint256 today = block.timestamp / 1 days;
        if (usage.lastResetDay < today) {
            usage.dailySpent = 0;
            usage.lastResetDay = today;
        }

        return usage.dailySpent + amount <= policy.dailyLimit;
    }

    /**
     * @dev Check monthly limit for account
     */
    function _checkMonthlyLimit(address account, uint256 amount) internal returns (bool) {
        SponsorshipPolicy storage policy = sponsorshipPolicies[account];
        UsageStats storage usage = usageStats[account];

        uint256 thisMonth = block.timestamp / 30 days;
        if (usage.lastResetMonth < thisMonth) {
            usage.monthlySpent = 0;
            usage.lastResetMonth = thisMonth;
        }

        return usage.monthlySpent + amount <= policy.monthlyLimit;
    }

    /**
     * @dev Update usage statistics
     */
    function _updateUsageStats(address account, uint256 actualGasCost) internal {
        UsageStats storage usage = usageStats[account];

        uint256 today = block.timestamp / 1 days;
        if (usage.lastResetDay < today) {
            usage.dailySpent = 0;
            usage.lastResetDay = today;
        }

        uint256 thisMonth = block.timestamp / 30 days;
        if (usage.lastResetMonth < thisMonth) {
            usage.monthlySpent = 0;
            usage.lastResetMonth = thisMonth;
        }

        usage.dailySpent += actualGasCost;
        usage.monthlySpent += actualGasCost;
        usage.totalSponsored += actualGasCost;
        usage.transactionCount++;
    }

    // =============================================================
    //                      ADMIN FUNCTIONS
    // =============================================================

    /**
     * @dev Emergency pause
     */
    function pause() external {
        require(governance.hasExecutiveApproval(msg.sender), "Requires executive approval");
        paused = true;
        emit EmergencyPause(true);
    }

    /**
     * @dev Unpause
     */
    function unpause() external onlyRole(PAYMASTER_MANAGER_ROLE) {
        paused = false;
        emit EmergencyPause(false);
    }

    /**
     * @dev Update global daily limit
     */
    function updateGlobalDailyLimit(uint256 newLimit) external onlyRole(PAYMASTER_MANAGER_ROLE) {
        globalDailyLimit = newLimit;
        emit GlobalLimitUpdated(newLimit);
    }

    /**
     * @dev Update verifying signer
     */
    function updateVerifyingSigner(address newSigner) external onlyRole(PAYMASTER_MANAGER_ROLE) {
        verifyingSigner = newSigner;
        emit VerifyingSignerUpdated(newSigner);
    }

    /**
     * @dev Deposit to EntryPoint
     */
    function deposit() external payable onlyRole(PAYMASTER_MANAGER_ROLE) {
        entryPoint.depositTo{value: msg.value}(address(this));
    }

    /**
     * @dev Withdraw from EntryPoint
     */
    function withdrawStake(address payable withdrawAddress, uint256 amount) external onlyRole(PAYMASTER_MANAGER_ROLE) {
        entryPoint.withdrawTo(withdrawAddress, amount);
    }

    /**
     * @dev Get EntryPoint deposit
     */
    function getDeposit() external view returns (uint256) {
        return entryPoint.balanceOf(address(this));
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Get sponsored accounts
     */
    function getSponsoredAccounts() external view returns (address[] memory) {
        return sponsoredAccounts;
    }

    /**
     * @dev Get supported tokens
     */
    function getSupportedTokens() external view returns (address[] memory) {
        return tokenList;
    }

    /**
     * @dev Get usage stats for account
     */
    function getUsageStats(address account) external view returns (
        uint256 dailySpent,
        uint256 monthlySpent,
        uint256 totalSponsored,
        uint256 transactionCount
    ) {
        UsageStats storage usage = usageStats[account];
        return (usage.dailySpent, usage.monthlySpent, usage.totalSponsored, usage.transactionCount);
    }

    // =============================================================
    //                    RECEIVE/FALLBACK
    // =============================================================

    receive() external payable {
        // Allow direct deposits for funding the paymaster
    }
}