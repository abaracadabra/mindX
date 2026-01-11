// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface IDAIO_Constitution {
    function checkDiversificationLimit() external view returns (bool);
    function calculateTithe(uint256 profit) external pure returns (uint256);
    function validateTithe(uint256 profit, uint256 titheProvided) external pure returns (bool);
    function recordTithe(uint256 amount, address from) external;
    function updateTreasuryState(uint256 totalValue, uint256 diversifiedValue) external;
}

/**
 * @title Treasury
 * @dev Economic operations and profit distribution for DAIO.
 *
 * Features:
 * - Multi-signature wallet (3-of-5)
 * - 15% tithe to treasury (constitutional)
 * - 85% distribution to contributing agents
 * - Cross-chain asset support
 * - Constitutional constraint enforcement
 */
contract Treasury is AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // Roles
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");
    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");
    bytes32 public constant SIGNER_ROLE = keccak256("SIGNER_ROLE");

    // Constants
    uint256 public constant TITHE_PERCENTAGE = 1500;      // 15% in basis points
    uint256 public constant DISTRIBUTION_PERCENTAGE = 8500; // 85% in basis points
    uint256 public constant BASIS_POINTS = 10000;
    uint256 public constant REQUIRED_SIGNATURES = 3;
    uint256 public constant MAX_SIGNERS = 5;

    // Multi-sig transaction status
    enum TransactionStatus {
        Pending,
        Executed,
        Cancelled
    }

    // Transaction structure for multi-sig
    struct Transaction {
        uint256 id;
        address to;
        uint256 value;
        bytes data;
        address token;              // address(0) for ETH
        string reason;
        uint256 confirmations;
        TransactionStatus status;
        uint40 createdAt;
        uint40 executedAt;
    }

    // Allocation request structure
    struct AllocationRequest {
        uint256 id;
        address requester;
        uint256 amount;
        address token;
        string purpose;
        bool approved;
        bool executed;
        uint40 requestedAt;
    }

    // Reward distribution record
    struct RewardDistribution {
        uint256 id;
        address agent;
        uint256 amount;
        address token;
        string reason;
        uint40 distributedAt;
    }

    // State
    IDAIO_Constitution public constitution;

    uint256 public transactionCount;
    uint256 public allocationRequestCount;
    uint256 public distributionCount;

    uint256 public totalDeposited;
    uint256 public totalDistributed;
    uint256 public titheCollected;

    mapping(uint256 => Transaction) public transactions;
    mapping(uint256 => mapping(address => bool)) public confirmations;
    mapping(uint256 => AllocationRequest) public allocationRequests;
    mapping(uint256 => RewardDistribution) public distributions;

    // Token balances tracking
    mapping(address => uint256) public tokenBalances;
    address[] public supportedTokens;
    mapping(address => bool) public isTokenSupported;

    // Diversification tracking
    uint256 public diversifiedValue;
    mapping(address => uint256) public diversifiedTokenBalances;

    // Events
    event Deposit(
        address indexed from,
        address indexed token,
        uint256 amount,
        uint256 titheAmount
    );

    event TransactionSubmitted(
        uint256 indexed txId,
        address indexed to,
        uint256 value,
        address token
    );

    event TransactionConfirmed(
        uint256 indexed txId,
        address indexed signer
    );

    event TransactionExecuted(
        uint256 indexed txId,
        address indexed executor
    );

    event TransactionCancelled(
        uint256 indexed txId
    );

    event RewardDistributed(
        uint256 indexed distributionId,
        address indexed agent,
        uint256 amount,
        address token
    );

    event AllocationRequested(
        uint256 indexed requestId,
        address indexed requester,
        uint256 amount,
        string purpose
    );

    event AllocationApproved(
        uint256 indexed requestId
    );

    event TitheCollected(
        uint256 amount,
        address indexed from
    );

    event TokenAdded(address indexed token);
    event TokenRemoved(address indexed token);

    // Errors
    error InsufficientBalance();
    error TransactionAlreadyExecuted();
    error TransactionAlreadyConfirmed();
    error NotEnoughConfirmations();
    error InvalidAmount();
    error ConstitutionalViolation();
    error TokenNotSupported();

    constructor(address _constitution) {
        constitution = IDAIO_Constitution(_constitution);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(GOVERNANCE_ROLE, msg.sender);
        _grantRole(TREASURER_ROLE, msg.sender);
        _grantRole(SIGNER_ROLE, msg.sender);
    }

    // ============ Deposit Functions ============

    /**
     * @dev Deposits ETH into the treasury
     */
    function deposit() external payable nonReentrant whenNotPaused {
        require(msg.value > 0, "Zero value");

        uint256 tithe = (msg.value * TITHE_PERCENTAGE) / BASIS_POINTS;
        titheCollected += tithe;
        totalDeposited += msg.value;

        constitution.recordTithe(tithe, msg.sender);
        _updateTreasuryState();

        emit Deposit(msg.sender, address(0), msg.value, tithe);
    }

    /**
     * @dev Deposits ERC20 tokens into the treasury
     * @param token Token address
     * @param amount Amount to deposit
     */
    function depositToken(
        address token,
        uint256 amount
    ) external nonReentrant whenNotPaused {
        require(amount > 0, "Zero amount");

        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        uint256 tithe = (amount * TITHE_PERCENTAGE) / BASIS_POINTS;
        titheCollected += tithe;
        tokenBalances[token] += amount;
        totalDeposited += amount;

        if (!isTokenSupported[token]) {
            supportedTokens.push(token);
            isTokenSupported[token] = true;
            emit TokenAdded(token);
        }

        constitution.recordTithe(tithe, msg.sender);
        _updateTreasuryState();

        emit Deposit(msg.sender, token, amount, tithe);
    }

    // ============ Multi-Sig Transactions ============

    /**
     * @dev Submits a new transaction for multi-sig approval
     * @param to Recipient address
     * @param value Amount (ETH or token)
     * @param token Token address (address(0) for ETH)
     * @param data Additional calldata
     * @param reason Reason for transaction
     * @return txId Transaction ID
     */
    function submitTransaction(
        address to,
        uint256 value,
        address token,
        bytes memory data,
        string memory reason
    ) external onlyRole(SIGNER_ROLE) returns (uint256 txId) {
        transactionCount++;
        txId = transactionCount;

        transactions[txId] = Transaction({
            id: txId,
            to: to,
            value: value,
            data: data,
            token: token,
            reason: reason,
            confirmations: 0,
            status: TransactionStatus.Pending,
            createdAt: uint40(block.timestamp),
            executedAt: 0
        });

        emit TransactionSubmitted(txId, to, value, token);

        // Auto-confirm by submitter
        confirmTransaction(txId);

        return txId;
    }

    /**
     * @dev Confirms a pending transaction
     * @param txId Transaction ID
     */
    function confirmTransaction(uint256 txId) public onlyRole(SIGNER_ROLE) {
        Transaction storage txn = transactions[txId];

        require(txn.status == TransactionStatus.Pending, "Not pending");
        require(!confirmations[txId][msg.sender], "Already confirmed");

        confirmations[txId][msg.sender] = true;
        txn.confirmations++;

        emit TransactionConfirmed(txId, msg.sender);

        // Auto-execute if threshold reached
        if (txn.confirmations >= REQUIRED_SIGNATURES) {
            executeTransaction(txId);
        }
    }

    /**
     * @dev Executes a confirmed transaction
     * @param txId Transaction ID
     */
    function executeTransaction(uint256 txId) public onlyRole(SIGNER_ROLE) nonReentrant {
        Transaction storage txn = transactions[txId];

        require(txn.status == TransactionStatus.Pending, "Not pending");
        require(txn.confirmations >= REQUIRED_SIGNATURES, "Not enough confirmations");

        // Check constitutional constraints
        if (!constitution.checkDiversificationLimit()) {
            revert ConstitutionalViolation();
        }

        txn.status = TransactionStatus.Executed;
        txn.executedAt = uint40(block.timestamp);

        if (txn.token == address(0)) {
            // ETH transfer
            require(address(this).balance >= txn.value, "Insufficient ETH");
            (bool success, ) = txn.to.call{value: txn.value}(txn.data);
            require(success, "ETH transfer failed");
        } else {
            // Token transfer
            require(tokenBalances[txn.token] >= txn.value, "Insufficient tokens");
            tokenBalances[txn.token] -= txn.value;
            IERC20(txn.token).safeTransfer(txn.to, txn.value);
        }

        totalDistributed += txn.value;
        _updateTreasuryState();

        emit TransactionExecuted(txId, msg.sender);
    }

    /**
     * @dev Cancels a pending transaction
     * @param txId Transaction ID
     */
    function cancelTransaction(uint256 txId) external onlyRole(GOVERNANCE_ROLE) {
        Transaction storage txn = transactions[txId];
        require(txn.status == TransactionStatus.Pending, "Not pending");

        txn.status = TransactionStatus.Cancelled;
        emit TransactionCancelled(txId);
    }

    // ============ Reward Distribution ============

    /**
     * @dev Distributes rewards to an agent
     * @param to Agent address
     * @param amount Reward amount
     * @param token Token address (address(0) for ETH)
     * @param reason Reason for reward
     */
    function distributeReward(
        address to,
        uint256 amount,
        address token,
        string memory reason
    ) external onlyRole(GOVERNANCE_ROLE) nonReentrant {
        require(to != address(0), "Invalid recipient");
        require(amount > 0, "Zero amount");

        // Check constitutional constraints
        if (!constitution.checkDiversificationLimit()) {
            revert ConstitutionalViolation();
        }

        distributionCount++;
        uint256 distId = distributionCount;

        if (token == address(0)) {
            require(address(this).balance >= amount, "Insufficient ETH");
            (bool success, ) = to.call{value: amount}("");
            require(success, "ETH transfer failed");
        } else {
            require(tokenBalances[token] >= amount, "Insufficient tokens");
            tokenBalances[token] -= amount;
            IERC20(token).safeTransfer(to, amount);
        }

        distributions[distId] = RewardDistribution({
            id: distId,
            agent: to,
            amount: amount,
            token: token,
            reason: reason,
            distributedAt: uint40(block.timestamp)
        });

        totalDistributed += amount;
        _updateTreasuryState();

        emit RewardDistributed(distId, to, amount, token);
    }

    // ============ Allocation Requests ============

    /**
     * @dev Requests an allocation from treasury
     * @param amount Amount requested
     * @param token Token address (address(0) for ETH)
     * @param purpose Purpose of allocation
     * @return requestId Request ID
     */
    function requestAllocation(
        uint256 amount,
        address token,
        string memory purpose
    ) external returns (uint256 requestId) {
        allocationRequestCount++;
        requestId = allocationRequestCount;

        allocationRequests[requestId] = AllocationRequest({
            id: requestId,
            requester: msg.sender,
            amount: amount,
            token: token,
            purpose: purpose,
            approved: false,
            executed: false,
            requestedAt: uint40(block.timestamp)
        });

        emit AllocationRequested(requestId, msg.sender, amount, purpose);
        return requestId;
    }

    /**
     * @dev Approves an allocation request
     * @param requestId Request ID
     */
    function approveAllocation(uint256 requestId) external onlyRole(GOVERNANCE_ROLE) {
        AllocationRequest storage request = allocationRequests[requestId];
        require(!request.approved, "Already approved");
        require(!request.executed, "Already executed");

        // Check constitutional constraints
        if (!constitution.checkDiversificationLimit()) {
            revert ConstitutionalViolation();
        }

        request.approved = true;
        emit AllocationApproved(requestId);
    }

    /**
     * @dev Executes an approved allocation
     * @param requestId Request ID
     */
    function executeAllocation(uint256 requestId) external nonReentrant {
        AllocationRequest storage request = allocationRequests[requestId];
        require(request.approved, "Not approved");
        require(!request.executed, "Already executed");

        request.executed = true;

        if (request.token == address(0)) {
            require(address(this).balance >= request.amount, "Insufficient ETH");
            (bool success, ) = request.requester.call{value: request.amount}("");
            require(success, "ETH transfer failed");
        } else {
            require(tokenBalances[request.token] >= request.amount, "Insufficient tokens");
            tokenBalances[request.token] -= request.amount;
            IERC20(request.token).safeTransfer(request.requester, request.amount);
        }

        totalDistributed += request.amount;
        _updateTreasuryState();
    }

    // ============ Diversification Management ============

    /**
     * @dev Marks tokens as diversified assets
     * @param token Token address
     * @param amount Amount to mark as diversified
     */
    function markAsDiversified(
        address token,
        uint256 amount
    ) external onlyRole(TREASURER_ROLE) {
        require(isTokenSupported[token] || token == address(0), "Token not supported");

        if (token == address(0)) {
            require(address(this).balance >= amount, "Insufficient ETH");
        } else {
            require(tokenBalances[token] >= amount, "Insufficient tokens");
        }

        diversifiedTokenBalances[token] += amount;
        diversifiedValue += amount;

        _updateTreasuryState();
    }

    // ============ View Functions ============

    /**
     * @dev Gets treasury balance
     * @return ethBalance ETH balance
     * @return totalTokenValue Estimated token value
     */
    function getBalance() external view returns (uint256 ethBalance, uint256 totalTokenValue) {
        ethBalance = address(this).balance;
        totalTokenValue = 0;
        for (uint256 i = 0; i < supportedTokens.length; i++) {
            totalTokenValue += tokenBalances[supportedTokens[i]];
        }
    }

    /**
     * @dev Gets transaction details
     * @param txId Transaction ID
     * @return transaction The transaction data
     */
    function getTransaction(uint256 txId) external view returns (Transaction memory transaction) {
        return transactions[txId];
    }

    /**
     * @dev Gets allocation request details
     * @param requestId Request ID
     * @return request The request data
     */
    function getAllocationRequest(uint256 requestId) external view returns (AllocationRequest memory request) {
        return allocationRequests[requestId];
    }

    /**
     * @dev Gets treasury statistics
     * @return deposited Total deposited
     * @return distributed Total distributed
     * @return tithe Total tithe collected
     * @return diversified Diversified value
     */
    function getStats() external view returns (
        uint256 deposited,
        uint256 distributed,
        uint256 tithe,
        uint256 diversified
    ) {
        return (totalDeposited, totalDistributed, titheCollected, diversifiedValue);
    }

    /**
     * @dev Checks diversification compliance
     * @return compliant Whether diversification mandate is met
     */
    function checkConstitutionalConstraints() external view returns (bool compliant) {
        return constitution.checkDiversificationLimit();
    }

    // ============ Internal Functions ============

    function _updateTreasuryState() internal {
        uint256 totalValue = address(this).balance;
        for (uint256 i = 0; i < supportedTokens.length; i++) {
            totalValue += tokenBalances[supportedTokens[i]];
        }

        constitution.updateTreasuryState(totalValue, diversifiedValue);
    }

    // ============ Admin Functions ============

    /**
     * @dev Updates the constitution contract address
     * @param newConstitution New constitution address
     */
    function setConstitution(address newConstitution) external onlyRole(GOVERNANCE_ROLE) {
        constitution = IDAIO_Constitution(newConstitution);
    }

    /**
     * @dev Pauses treasury operations
     */
    function pause() external onlyRole(GOVERNANCE_ROLE) {
        _pause();
    }

    /**
     * @dev Unpauses treasury operations
     */
    function unpause() external onlyRole(GOVERNANCE_ROLE) {
        _unpause();
    }

    /**
     * @dev Receive ETH
     */
    receive() external payable {
        uint256 tithe = (msg.value * TITHE_PERCENTAGE) / BASIS_POINTS;
        titheCollected += tithe;
        totalDeposited += msg.value;
        emit Deposit(msg.sender, address(0), msg.value, tithe);
    }
}
