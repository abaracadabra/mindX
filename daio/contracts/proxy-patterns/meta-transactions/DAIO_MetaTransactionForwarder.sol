// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Permit.sol";

/**
 * @title DAIO_MetaTransactionForwarder
 * @notice Meta-transaction forwarder with ERC2612 permit integration and DAIO governance
 * @dev Enables gasless transactions with permit-based token approvals and constitutional compliance
 */
contract DAIO_MetaTransactionForwarder is EIP712, AccessControl, ReentrancyGuard {
    using ECDSA for bytes32;

    bytes32 public constant FORWARDER_ADMIN_ROLE = keccak256("FORWARDER_ADMIN_ROLE");
    bytes32 public constant RELAYER_ROLE = keccak256("RELAYER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Forward request structure
    struct ForwardRequest {
        address from;              // Transaction sender
        address to;                // Transaction target
        uint256 value;             // ETH value to send
        uint256 gas;               // Gas limit for execution
        uint256 nonce;             // Sender's nonce
        bytes data;                // Transaction calldata
        uint256 validUntil;        // Validity deadline
    }

    // Permit transaction structure (combines meta-tx with permit)
    struct PermitRequest {
        ForwardRequest forwardRequest; // Meta-transaction request
        address token;                 // Token for permit
        uint256 amount;               // Permit amount
        uint256 deadline;             // Permit deadline
        uint8 v;                      // Permit signature v
        bytes32 r;                    // Permit signature r
        bytes32 s;                    // Permit signature s
    }

    // Batch request for multiple transactions
    struct BatchRequest {
        ForwardRequest[] requests;     // Array of forward requests
        bytes[] signatures;           // Array of corresponding signatures
    }

    // Gas sponsorship configuration
    struct GasSponsorConfig {
        address sponsor;              // Address sponsoring gas
        uint256 maxGasPerTx;         // Maximum gas per transaction
        uint256 maxTxPerDay;         // Maximum transactions per day
        uint256 dailyGasLimit;       // Daily gas limit
        bool isActive;               // Whether sponsorship is active
        mapping(address => uint256) userDailyUsage; // user -> daily gas used
        mapping(uint256 => uint256) dailyUsage;     // day -> total gas used
    }

    // DAIO Constitutional Integration
    struct ConstitutionalLimits {
        uint256 maxTransactionValue;  // Maximum ETH value per transaction
        uint256 maxGasLimit;          // Maximum gas limit per transaction
        uint256 maxDailyVolume;       // Maximum daily transaction volume
        uint256 forwardingFee;        // Fee for forwarding (BPS)
        address treasuryContract;     // DAIO treasury contract
        address executiveGovernance;  // CEO + Seven Soldiers contract
        bool constitutionalCompliance; // Whether constitutional compliance is enforced
    }

    // EIP712 type hashes
    bytes32 private constant FORWARD_REQUEST_TYPEHASH = keccak256(
        "ForwardRequest(address from,address to,uint256 value,uint256 gas,uint256 nonce,bytes data,uint256 validUntil)"
    );

    bytes32 private constant PERMIT_REQUEST_TYPEHASH = keccak256(
        "PermitRequest(ForwardRequest forwardRequest,address token,uint256 amount,uint256 deadline,uint8 v,bytes32 r,bytes32 s)"
    );

    // State variables
    mapping(address => uint256) public nonces;              // User nonces
    mapping(address => GasSponsorConfig) internal gasSponsors; // Gas sponsorship configs
    mapping(address => bool) public trustedTargets;        // Trusted target contracts
    mapping(address => uint256) public userDailyVolume;    // User daily transaction volume
    mapping(uint256 => uint256) public dailyTotalVolume;   // Daily total volume

    ConstitutionalLimits public constitutionalLimits;

    // Relayer management
    address[] public authorizedRelayers;
    mapping(address => bool) public isRelayer;
    mapping(address => uint256) public relayerReputation;  // Relayer reputation score

    // Statistics tracking
    uint256 public totalTransactionsForwarded;
    uint256 public totalGasSponsored;
    uint256 public totalFeesCollected;

    // Events
    event TransactionForwarded(
        address indexed from,
        address indexed to,
        address indexed relayer,
        uint256 value,
        uint256 gas,
        bool success,
        bytes returndata
    );
    event PermitTransactionForwarded(
        address indexed from,
        address indexed to,
        address indexed token,
        uint256 permitAmount,
        bool success
    );
    event BatchTransactionForwarded(
        address indexed relayer,
        uint256 batchSize,
        uint256 successCount,
        uint256 totalGasUsed
    );
    event GasSponsorshipConfigured(
        address indexed sponsor,
        uint256 maxGasPerTx,
        uint256 dailyGasLimit,
        bool isActive
    );
    event RelayerAuthorized(
        address indexed relayer,
        address indexed authorizer
    );
    event RelayerDeauthorized(
        address indexed relayer,
        string reason,
        address indexed deauthorizer
    );
    event ConstitutionalComplianceCheck(
        bool compliant,
        string reason,
        address user,
        uint256 value
    );
    event EmergencyPause(
        string reason,
        address indexed pauser
    );

    /**
     * @notice Initialize DAIO Meta Transaction Forwarder
     * @param _treasuryContract DAIO treasury contract
     * @param _executiveGovernance CEO + Seven Soldiers governance
     * @param admin Admin address for role management
     */
    constructor(
        address _treasuryContract,
        address _executiveGovernance,
        address admin
    ) EIP712("DAIO_MetaTransactionForwarder", "1.0.0") {
        require(admin != address(0), "Invalid admin address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(FORWARDER_ADMIN_ROLE, admin);
        _grantRole(RELAYER_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);

        // Initialize constitutional limits
        constitutionalLimits = ConstitutionalLimits({
            maxTransactionValue: 10 ether,       // 10 ETH max per transaction
            maxGasLimit: 1000000,               // 1M gas limit per transaction
            maxDailyVolume: 100 ether,          // 100 ETH daily volume limit
            forwardingFee: 100,                 // 1% forwarding fee
            treasuryContract: _treasuryContract,
            executiveGovernance: _executiveGovernance,
            constitutionalCompliance: true
        });
    }

    /**
     * @notice Forward meta-transaction
     * @param req Forward request
     * @param signature Request signature
     * @return success Whether transaction succeeded
     * @return returndata Transaction return data
     */
    function forward(
        ForwardRequest calldata req,
        bytes calldata signature
    ) external payable nonReentrant onlyRole(RELAYER_ROLE) returns (bool success, bytes memory returndata) {
        // Verify signature and request
        _verifyForwardRequest(req, signature);

        // Check constitutional compliance
        _checkConstitutionalCompliance(req.from, req.value);

        // Update nonce
        nonces[req.from]++;

        // Execute transaction
        (success, returndata) = _executeForwardRequest(req);

        // Handle fees and gas sponsorship
        _handleForwardingFees(req, success);

        // Update statistics
        totalTransactionsForwarded++;
        if (success) {
            relayerReputation[msg.sender]++;
        }

        emit TransactionForwarded(
            req.from,
            req.to,
            msg.sender,
            req.value,
            req.gas,
            success,
            returndata
        );

        return (success, returndata);
    }

    /**
     * @notice Forward transaction with permit
     * @param permitReq Permit request containing both forward request and permit data
     * @param forwardSignature Signature for forward request
     * @return success Whether transaction succeeded
     * @return returndata Transaction return data
     */
    function forwardWithPermit(
        PermitRequest calldata permitReq,
        bytes calldata forwardSignature
    ) external payable nonReentrant onlyRole(RELAYER_ROLE) returns (bool success, bytes memory returndata) {
        // Verify forward request signature
        _verifyForwardRequest(permitReq.forwardRequest, forwardSignature);

        // Check constitutional compliance
        _checkConstitutionalCompliance(permitReq.forwardRequest.from, permitReq.forwardRequest.value);

        // Execute permit
        IERC20Permit(permitReq.token).permit(
            permitReq.forwardRequest.from,
            address(this),
            permitReq.amount,
            permitReq.deadline,
            permitReq.v,
            permitReq.r,
            permitReq.s
        );

        // Update nonce
        nonces[permitReq.forwardRequest.from]++;

        // Execute transaction
        (success, returndata) = _executeForwardRequest(permitReq.forwardRequest);

        // Handle fees and gas sponsorship
        _handleForwardingFees(permitReq.forwardRequest, success);

        // Update statistics
        totalTransactionsForwarded++;
        if (success) {
            relayerReputation[msg.sender]++;
        }

        emit PermitTransactionForwarded(
            permitReq.forwardRequest.from,
            permitReq.forwardRequest.to,
            permitReq.token,
            permitReq.amount,
            success
        );

        return (success, returndata);
    }

    /**
     * @notice Forward batch of transactions
     * @param batchReq Batch request with multiple transactions
     * @return results Array of execution results
     * @return successes Array of success flags
     */
    function forwardBatch(
        BatchRequest calldata batchReq
    ) external payable nonReentrant onlyRole(RELAYER_ROLE) returns (bytes[] memory results, bool[] memory successes) {
        require(batchReq.requests.length == batchReq.signatures.length, "Array length mismatch");
        require(batchReq.requests.length <= 10, "Batch too large");

        uint256 batchSize = batchReq.requests.length;
        results = new bytes[](batchSize);
        successes = new bool[](batchSize);
        uint256 successCount = 0;
        uint256 totalGasUsed = 0;

        for (uint256 i = 0; i < batchSize; i++) {
            // Verify each request
            try this._verifyForwardRequestExternal(batchReq.requests[i], batchReq.signatures[i]) {
                // Check constitutional compliance
                _checkConstitutionalCompliance(batchReq.requests[i].from, batchReq.requests[i].value);

                // Update nonce
                nonces[batchReq.requests[i].from]++;

                // Execute transaction
                uint256 gasStart = gasleft();
                (successes[i], results[i]) = _executeForwardRequest(batchReq.requests[i]);
                uint256 gasUsed = gasStart - gasleft();

                totalGasUsed += gasUsed;

                if (successes[i]) {
                    successCount++;
                }

                // Handle fees for each transaction
                _handleForwardingFees(batchReq.requests[i], successes[i]);

            } catch {
                successes[i] = false;
                results[i] = "Verification failed";
            }
        }

        // Update statistics
        totalTransactionsForwarded += batchSize;
        if (successCount > batchSize / 2) { // More than half successful
            relayerReputation[msg.sender] += successCount;
        }

        emit BatchTransactionForwarded(msg.sender, batchSize, successCount, totalGasUsed);

        return (results, successes);
    }

    /**
     * @notice Configure gas sponsorship
     * @param sponsor Sponsor address
     * @param maxGasPerTx Maximum gas per transaction
     * @param maxTxPerDay Maximum transactions per day
     * @param dailyGasLimit Daily gas limit
     * @param isActive Whether sponsorship is active
     */
    function configureGasSponsorship(
        address sponsor,
        uint256 maxGasPerTx,
        uint256 maxTxPerDay,
        uint256 dailyGasLimit,
        bool isActive
    ) external onlyRole(FORWARDER_ADMIN_ROLE) {
        require(sponsor != address(0), "Invalid sponsor address");

        GasSponsorConfig storage config = gasSponsors[sponsor];
        config.sponsor = sponsor;
        config.maxGasPerTx = maxGasPerTx;
        config.maxTxPerDay = maxTxPerDay;
        config.dailyGasLimit = dailyGasLimit;
        config.isActive = isActive;

        emit GasSponsorshipConfigured(sponsor, maxGasPerTx, dailyGasLimit, isActive);
    }

    /**
     * @notice Authorize relayer
     * @param relayer Relayer address to authorize
     */
    function authorizeRelayer(address relayer) external onlyRole(FORWARDER_ADMIN_ROLE) {
        require(relayer != address(0), "Invalid relayer address");
        require(!isRelayer[relayer], "Relayer already authorized");

        _grantRole(RELAYER_ROLE, relayer);
        isRelayer[relayer] = true;
        authorizedRelayers.push(relayer);
        relayerReputation[relayer] = 100; // Starting reputation

        emit RelayerAuthorized(relayer, msg.sender);
    }

    /**
     * @notice Deauthorize relayer
     * @param relayer Relayer address to deauthorize
     * @param reason Deauthorization reason
     */
    function deauthorizeRelayer(address relayer, string memory reason) external onlyRole(FORWARDER_ADMIN_ROLE) {
        require(isRelayer[relayer], "Relayer not authorized");

        _revokeRole(RELAYER_ROLE, relayer);
        isRelayer[relayer] = false;
        relayerReputation[relayer] = 0;

        // Remove from authorized relayers array
        for (uint256 i = 0; i < authorizedRelayers.length; i++) {
            if (authorizedRelayers[i] == relayer) {
                authorizedRelayers[i] = authorizedRelayers[authorizedRelayers.length - 1];
                authorizedRelayers.pop();
                break;
            }
        }

        emit RelayerDeauthorized(relayer, reason, msg.sender);
    }

    /**
     * @notice Add trusted target contract
     * @param target Target contract address
     */
    function addTrustedTarget(address target) external onlyRole(FORWARDER_ADMIN_ROLE) {
        trustedTargets[target] = true;
    }

    /**
     * @notice Remove trusted target contract
     * @param target Target contract address
     */
    function removeTrustedTarget(address target) external onlyRole(FORWARDER_ADMIN_ROLE) {
        trustedTargets[target] = false;
    }

    /**
     * @notice Emergency pause all forwarding
     * @param reason Pause reason
     */
    function emergencyPause(string memory reason) external onlyRole(EMERGENCY_ROLE) {
        // Implementation would pause all forwarding operations
        emit EmergencyPause(reason, msg.sender);
    }

    // Internal Functions

    function _verifyForwardRequest(ForwardRequest calldata req, bytes calldata signature) internal view {
        require(req.validUntil > block.timestamp, "Request expired");
        require(req.nonce == nonces[req.from], "Invalid nonce");
        require(req.gas <= constitutionalLimits.maxGasLimit, "Gas limit too high");

        bytes32 digest = _hashTypedDataV4(_getStructHash(req));
        address signer = digest.recover(signature);
        require(signer == req.from, "Invalid signature");
    }

    function _verifyForwardRequestExternal(ForwardRequest calldata req, bytes calldata signature) external view {
        _verifyForwardRequest(req, signature);
    }

    function _getStructHash(ForwardRequest calldata req) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            FORWARD_REQUEST_TYPEHASH,
            req.from,
            req.to,
            req.value,
            req.gas,
            req.nonce,
            keccak256(req.data),
            req.validUntil
        ));
    }

    function _executeForwardRequest(ForwardRequest calldata req) internal returns (bool success, bytes memory returndata) {
        // Check if target is trusted (optional additional security)
        if (trustedTargets[req.to]) {
            // Additional security checks for trusted targets
        }

        // Execute with specified gas limit
        (success, returndata) = req.to.call{value: req.value, gas: req.gas}(req.data);

        return (success, returndata);
    }

    function _handleForwardingFees(ForwardRequest calldata req, bool success) internal {
        // Calculate and collect forwarding fees
        if (constitutionalLimits.forwardingFee > 0 && req.value > 0) {
            uint256 fee = (req.value * constitutionalLimits.forwardingFee) / 10000;

            if (fee > 0 && constitutionalLimits.treasuryContract != address(0)) {
                payable(constitutionalLimits.treasuryContract).transfer(fee);
                totalFeesCollected += fee;
            }
        }

        // Handle gas sponsorship accounting
        _updateGasSponsorshipUsage(req.from, req.gas);
    }

    function _updateGasSponsorshipUsage(address user, uint256 gasUsed) internal {
        // Check if user has gas sponsorship
        for (uint256 i = 0; i < authorizedRelayers.length; i++) {
            address relayer = authorizedRelayers[i];
            GasSponsorConfig storage config = gasSponsors[relayer];

            if (config.isActive) {
                uint256 currentDay = block.timestamp / 86400;

                // Update user daily usage
                config.userDailyUsage[user] += gasUsed;

                // Update sponsor daily usage
                config.dailyUsage[currentDay] += gasUsed;

                totalGasSponsored += gasUsed;
                break; // Use first available sponsor
            }
        }
    }

    function _checkConstitutionalCompliance(address user, uint256 value) internal {
        if (!constitutionalLimits.constitutionalCompliance) return;

        bool compliant = true;
        string memory reason = "Transaction within constitutional limits";

        // Check transaction value limit
        if (value > constitutionalLimits.maxTransactionValue) {
            compliant = false;
            reason = "Transaction value exceeds constitutional limit";
        }

        // Check daily volume limit
        uint256 currentDay = block.timestamp / 86400;
        if (userDailyVolume[user] + value > constitutionalLimits.maxDailyVolume) {
            compliant = false;
            reason = "Daily volume limit exceeded";
        }

        if (dailyTotalVolume[currentDay] + value > constitutionalLimits.maxDailyVolume * 100) {
            compliant = false;
            reason = "Global daily volume limit exceeded";
        }

        emit ConstitutionalComplianceCheck(compliant, reason, user, value);
        require(compliant, reason);

        // Update volume tracking if compliant
        userDailyVolume[user] += value;
        dailyTotalVolume[currentDay] += value;
    }

    /**
     * @notice Get user's nonce
     * @param user User address
     * @return nonce Current nonce
     */
    function getNonce(address user) external view returns (uint256 nonce) {
        return nonces[user];
    }

    /**
     * @notice Verify signature for a forward request
     * @param req Forward request
     * @param signature Request signature
     * @return valid Whether signature is valid
     */
    function verify(ForwardRequest calldata req, bytes calldata signature) external view returns (bool valid) {
        try this._verifyForwardRequestExternal(req, signature) {
            return true;
        } catch {
            return false;
        }
    }

    /**
     * @notice Get gas sponsor configuration
     * @param sponsor Sponsor address
     * @return maxGasPerTx Maximum gas per transaction
     * @return maxTxPerDay Maximum transactions per day
     * @return dailyGasLimit Daily gas limit
     * @return isActive Whether sponsorship is active
     */
    function getGasSponsorConfig(address sponsor)
        external
        view
        returns (
            uint256 maxGasPerTx,
            uint256 maxTxPerDay,
            uint256 dailyGasLimit,
            bool isActive
        )
    {
        GasSponsorConfig storage config = gasSponsors[sponsor];
        return (
            config.maxGasPerTx,
            config.maxTxPerDay,
            config.dailyGasLimit,
            config.isActive
        );
    }

    /**
     * @notice Get authorized relayers
     * @return relayers Array of authorized relayer addresses
     */
    function getAuthorizedRelayers() external view returns (address[] memory relayers) {
        return authorizedRelayers;
    }

    /**
     * @notice Get constitutional limits
     * @return limits Constitutional limits configuration
     */
    function getConstitutionalLimits() external view returns (ConstitutionalLimits memory limits) {
        return constitutionalLimits;
    }

    /**
     * @notice Get forwarder statistics
     * @return totalTx Total transactions forwarded
     * @return totalGas Total gas sponsored
     * @return totalFees Total fees collected
     */
    function getForwarderStats()
        external
        view
        returns (uint256 totalTx, uint256 totalGas, uint256 totalFees)
    {
        return (totalTransactionsForwarded, totalGasSponsored, totalFeesCollected);
    }
}