// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SubscriptionManager
 * @notice Manage recurring subscription payments for agentic services
 * @dev Supports flexible billing cycles and automated renewals
 */
contract SubscriptionManager {
    
    struct Subscription {
        bytes32 subscriptionId;
        address subscriber;
        address provider;
        uint256 amount;             // USDC per billing cycle
        uint256 billingCycle;       // Duration in seconds (e.g., 30 days)
        uint256 startDate;
        uint256 nextBillingDate;
        uint256 endDate;            // 0 for indefinite
        uint256 totalPaid;
        uint256 missedPayments;
        bool isActive;
        bool autoRenew;
    }
    
    struct PaymentHistory {
        bytes32 paymentId;
        bytes32 subscriptionId;
        uint256 amount;
        uint256 timestamp;
        bool successful;
    }
    
    mapping(bytes32 => Subscription) public subscriptions;
    mapping(address => bytes32[]) public subscriberSubscriptions;
    mapping(address => bytes32[]) public providerSubscriptions;
    mapping(bytes32 => PaymentHistory[]) public paymentHistory;
    
    address public owner;
    address public feeCollector;
    uint256 public platformFeeRate;
    uint256 public totalSubscriptions;
    uint256 public activeSubscriptions;
    
    event SubscriptionCreated(
        bytes32 indexed subscriptionId,
        address indexed subscriber,
        address indexed provider,
        uint256 amount,
        uint256 billingCycle
    );
    event SubscriptionActivated(bytes32 indexed subscriptionId);
    event SubscriptionCancelled(bytes32 indexed subscriptionId);
    event SubscriptionRenewed(bytes32 indexed subscriptionId, uint256 nextBillingDate);
    event PaymentProcessed(bytes32 indexed subscriptionId, uint256 amount, bool successful);
    event PaymentFailed(bytes32 indexed subscriptionId, uint256 missedPayments);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    modifier onlySubscriber(bytes32 subscriptionId) {
        require(subscriptions[subscriptionId].subscriber == msg.sender, "Only subscriber");
        _;
    }
    
    constructor(address _feeCollector, uint256 _platformFeeRate) {
        owner = msg.sender;
        feeCollector = _feeCollector;
        platformFeeRate = _platformFeeRate;
    }
    
    /**
     * @notice Create a new subscription
     * @param provider Service provider address
     * @param amount USDC amount per billing cycle
     * @param billingCycle Billing cycle duration in seconds
     * @param autoRenew Whether to auto-renew
     * @return subscriptionId The created subscription ID
     */
    function createSubscription(
        address provider,
        uint256 amount,
        uint256 billingCycle,
        bool autoRenew
    ) external returns (bytes32) {
        require(provider != address(0), "Invalid provider");
        require(amount > 0, "Invalid amount");
        require(billingCycle > 0, "Invalid billing cycle");
        
        bytes32 subscriptionId = keccak256(
            abi.encodePacked(
                msg.sender,
                provider,
                amount,
                block.timestamp,
                totalSubscriptions
            )
        );
        
        subscriptions[subscriptionId] = Subscription({
            subscriptionId: subscriptionId,
            subscriber: msg.sender,
            provider: provider,
            amount: amount,
            billingCycle: billingCycle,
            startDate: block.timestamp,
            nextBillingDate: block.timestamp + billingCycle,
            endDate: 0,
            totalPaid: 0,
            missedPayments: 0,
            isActive: false,
            autoRenew: autoRenew
        });
        
        subscriberSubscriptions[msg.sender].push(subscriptionId);
        providerSubscriptions[provider].push(subscriptionId);
        totalSubscriptions++;
        
        emit SubscriptionCreated(subscriptionId, msg.sender, provider, amount, billingCycle);
        return subscriptionId;
    }
    
    /**
     * @notice Activate subscription with initial payment
     * @param subscriptionId Subscription identifier
     */
    function activateSubscription(bytes32 subscriptionId) external payable onlySubscriber(subscriptionId) {
        Subscription storage sub = subscriptions[subscriptionId];
        require(!sub.isActive, "Already active");
        require(msg.value >= sub.amount, "Insufficient payment");
        
        sub.isActive = true;
        activeSubscriptions++;
        
        // Process initial payment
        _processPayment(subscriptionId, msg.value);
        
        emit SubscriptionActivated(subscriptionId);
    }
    
    /**
     * @notice Process subscription payment
     * @param subscriptionId Subscription identifier
     */
    function processPayment(bytes32 subscriptionId) external payable {
        Subscription storage sub = subscriptions[subscriptionId];
        require(sub.isActive, "Subscription not active");
        require(msg.sender == sub.subscriber, "Only subscriber");
        require(block.timestamp >= sub.nextBillingDate, "Not due yet");
        require(msg.value >= sub.amount, "Insufficient payment");
        
        _processPayment(subscriptionId, msg.value);
        
        // Update next billing date
        sub.nextBillingDate += sub.billingCycle;
        
        emit SubscriptionRenewed(subscriptionId, sub.nextBillingDate);
    }
    
    function _processPayment(bytes32 subscriptionId, uint256 amount) internal {
        Subscription storage sub = subscriptions[subscriptionId];
        
        // Calculate fee
        uint256 fee = (amount * platformFeeRate) / 10000;
        uint256 providerAmount = amount - fee;
        
        // Transfer to provider
        payable(sub.provider).transfer(providerAmount);
        
        // Transfer fee
        if (fee > 0) {
            payable(feeCollector).transfer(fee);
        }
        
        // Record payment
        sub.totalPaid += amount;
        
        bytes32 paymentId = keccak256(
            abi.encodePacked(
                subscriptionId,
                amount,
                block.timestamp
            )
        );
        
        paymentHistory[subscriptionId].push(PaymentHistory({
            paymentId: paymentId,
            subscriptionId: subscriptionId,
            amount: amount,
            timestamp: block.timestamp,
            successful: true
        }));
        
        emit PaymentProcessed(subscriptionId, amount, true);
    }
    
    /**
     * @notice Cancel subscription
     * @param subscriptionId Subscription identifier
     */
    function cancelSubscription(bytes32 subscriptionId) external onlySubscriber(subscriptionId) {
        Subscription storage sub = subscriptions[subscriptionId];
        require(sub.isActive, "Not active");
        
        sub.isActive = false;
        sub.endDate = block.timestamp;
        activeSubscriptions--;
        
        emit SubscriptionCancelled(subscriptionId);
    }
    
    /**
     * @notice Check for overdue subscriptions and mark missed payments
     * @param subscriptionId Subscription identifier
     */
    function checkOverdue(bytes32 subscriptionId) external {
        Subscription storage sub = subscriptions[subscriptionId];
        require(sub.isActive, "Not active");
        
        if (block.timestamp > sub.nextBillingDate + sub.billingCycle) {
            sub.missedPayments++;
            
            // Auto-cancel after 3 missed payments
            if (sub.missedPayments >= 3) {
                sub.isActive = false;
                sub.endDate = block.timestamp;
                activeSubscriptions--;
                emit SubscriptionCancelled(subscriptionId);
            }
            
            emit PaymentFailed(subscriptionId, sub.missedPayments);
        }
    }
    
    /**
     * @notice Update auto-renew setting
     * @param subscriptionId Subscription identifier
     * @param autoRenew New auto-renew setting
     */
    function updateAutoRenew(bytes32 subscriptionId, bool autoRenew) external onlySubscriber(subscriptionId) {
        subscriptions[subscriptionId].autoRenew = autoRenew;
    }
    
    // ============ View Functions ============
    
    function getSubscription(bytes32 subscriptionId) external view returns (Subscription memory) {
        return subscriptions[subscriptionId];
    }
    
    function getSubscriberSubscriptions(address subscriber) external view returns (bytes32[] memory) {
        return subscriberSubscriptions[subscriber];
    }
    
    function getProviderSubscriptions(address provider) external view returns (bytes32[] memory) {
        return providerSubscriptions[provider];
    }
    
    function getPaymentHistory(bytes32 subscriptionId) external view returns (PaymentHistory[] memory) {
        return paymentHistory[subscriptionId];
    }
    
    function isSubscriptionActive(bytes32 subscriptionId) external view returns (bool) {
        return subscriptions[subscriptionId].isActive;
    }
    
    function getNextBillingDate(bytes32 subscriptionId) external view returns (uint256) {
        return subscriptions[subscriptionId].nextBillingDate;
    }
}
