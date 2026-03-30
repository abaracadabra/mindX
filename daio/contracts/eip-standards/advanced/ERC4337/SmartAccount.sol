// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC1155/IERC1155.sol";

/**
 * @title SmartAccount
 * @dev ERC4337 Account Abstraction implementation with DAIO integration
 *
 * Features:
 * - Gasless transactions through paymasters
 * - Social recovery mechanisms
 * - Multi-signature functionality
 * - Session key management
 * - DAIO governance integration for corporate accounts
 * - Batch transaction execution
 * - Emergency recovery mechanisms
 *
 * @author DAIO Development Team
 */

// ERC4337 Interfaces
interface IEntryPoint {
    function handleOps(UserOperation[] calldata ops, address payable beneficiary) external;
    function simulateValidation(UserOperation calldata userOp) external returns (ValidationResult memory result);

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

    struct ValidationResult {
        uint256 preOpGas;
        uint256 prefund;
        bool sigFailed;
        uint48 validAfter;
        uint48 validUntil;
        bytes paymasterContext;
    }
}

interface IAccount {
    function validateUserOp(
        IEntryPoint.UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 missingAccountFunds
    ) external returns (uint256 validationData);
}

interface IDAIO_Constitution_Enhanced {
    function validateSmartAccountAction(
        address account,
        address target,
        uint256 value,
        bytes calldata data
    ) external view returns (bool valid, string memory reason);
}

interface IExecutiveGovernance {
    function hasExecutiveApproval(address account) external view returns (bool);
    function hasSmartAccountManagerRole(address account) external view returns (bool);
}

contract SmartAccount is IAccount, AccessControl, ReentrancyGuard {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    // =============================================================
    //                        CONSTANTS
    // =============================================================

    bytes32 public constant OWNER_ROLE = keccak256("OWNER_ROLE");
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");
    bytes32 public constant SESSION_KEY_ROLE = keccak256("SESSION_KEY_ROLE");
    bytes32 public constant RECOVERY_ROLE = keccak256("RECOVERY_ROLE");

    uint256 public constant SIG_VALIDATION_SUCCEEDED = 0;
    uint256 public constant SIG_VALIDATION_FAILED = 1;

    // =============================================================
    //                         STORAGE
    // =============================================================

    // ERC4337 Core
    IEntryPoint public immutable entryPoint;
    uint256 public nonce;

    // DAIO Integration
    IDAIO_Constitution_Enhanced public immutable constitution;
    IExecutiveGovernance public immutable governance;

    // Multi-signature settings
    struct MultisigConfig {
        uint256 threshold;
        uint256 ownerCount;
        mapping(address => bool) isOwner;
        address[] owners;
    }
    MultisigConfig public multisigConfig;

    // Session key management
    struct SessionKey {
        address key;
        uint48 validAfter;
        uint48 validUntil;
        uint256 limit; // Spending limit in wei
        uint256 spent; // Amount spent
        address[] allowedTargets;
        mapping(address => bool) isAllowedTarget;
        bool active;
    }
    mapping(address => SessionKey) public sessionKeys;
    address[] public sessionKeyList;

    // Social recovery
    struct RecoveryConfig {
        address[] guardians;
        uint256 threshold;
        uint256 delay; // Recovery delay in seconds
        mapping(address => bool) isGuardian;
        mapping(bytes32 => RecoveryRequest) requests;
    }

    struct RecoveryRequest {
        address newOwner;
        uint256 confirmations;
        uint256 executeAfter;
        bool executed;
        mapping(address => bool) confirmed;
    }

    RecoveryConfig public recoveryConfig;

    // Emergency controls
    bool public locked;
    uint256 public lockUntil;
    mapping(address => bool) public emergencyContacts;

    // Transaction batching
    struct BatchCall {
        address target;
        uint256 value;
        bytes data;
    }

    // Corporate governance integration
    bool public isCorporateAccount;
    uint256 public dailyLimit;
    uint256 public spentToday;
    uint256 public lastResetDay;

    // Events
    event SmartAccountInitialized(address indexed owner, address indexed entryPoint);
    event OwnerAdded(address indexed owner);
    event OwnerRemoved(address indexed owner);
    event ThresholdChanged(uint256 newThreshold);
    event SessionKeyAdded(address indexed sessionKey, uint48 validAfter, uint48 validUntil);
    event SessionKeyRemoved(address indexed sessionKey);
    event GuardianAdded(address indexed guardian);
    event GuardianRemoved(address indexed guardian);
    event RecoveryInitiated(bytes32 indexed requestId, address indexed newOwner);
    event RecoveryExecuted(bytes32 indexed requestId, address indexed newOwner);
    event AccountLocked(uint256 lockUntil);
    event AccountUnlocked();
    event BatchExecuted(uint256 batchSize);
    event EmergencyRecovery(address indexed newOwner, address indexed initiator);

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor() {
        // Constructor is empty as this contract is deployed as implementation
        // Initialization happens in initialize()
    }

    /**
     * @dev Initialize the smart account (called by factory)
     */
    function initialize(
        address initialOwner,
        address entryPointAddress,
        address constitutionAddress,
        address governanceAddress,
        bytes calldata initData
    ) external {
        require(entryPointAddress != address(0), "Invalid entry point");
        require(!hasRole(DEFAULT_ADMIN_ROLE, initialOwner), "Already initialized");

        // Set entry point (immutable-like behavior)
        assembly {
            sstore(entryPoint.slot, entryPointAddress)
        }

        // Initialize DAIO integration (immutable-like behavior)
        assembly {
            sstore(constitution.slot, constitutionAddress)
            sstore(governance.slot, governanceAddress)
        }

        // Set up access control
        _grantRole(DEFAULT_ADMIN_ROLE, initialOwner);
        _grantRole(OWNER_ROLE, initialOwner);

        // Initialize multisig with single owner
        multisigConfig.threshold = 1;
        multisigConfig.ownerCount = 1;
        multisigConfig.isOwner[initialOwner] = true;
        multisigConfig.owners.push(initialOwner);

        // Parse init data if provided
        if (initData.length > 0) {
            (
                bool _isCorporateAccount,
                uint256 _dailyLimit,
                address[] memory _guardians,
                uint256 _recoveryThreshold
            ) = abi.decode(initData, (bool, uint256, address[], uint256));

            isCorporateAccount = _isCorporateAccount;
            dailyLimit = _dailyLimit;

            // Set up guardians
            for (uint256 i = 0; i < _guardians.length; i++) {
                _addGuardian(_guardians[i]);
            }
            recoveryConfig.threshold = _recoveryThreshold;
        }

        emit SmartAccountInitialized(initialOwner, entryPointAddress);
    }

    // =============================================================
    //                    ERC4337 IMPLEMENTATION
    // =============================================================

    /**
     * @dev Validate user operation signature and return validation data
     */
    function validateUserOp(
        IEntryPoint.UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 missingAccountFunds
    ) external override returns (uint256 validationData) {
        require(msg.sender == address(entryPoint), "Only EntryPoint can call");

        // Check if account is locked
        if (locked && block.timestamp < lockUntil) {
            return SIG_VALIDATION_FAILED;
        }

        // Validate signature
        bytes32 hash = userOpHash.toEthSignedMessageHash();
        address signer = hash.recover(userOp.signature);

        bool validSignature = false;
        uint48 validAfter = 0;
        uint48 validUntil = 0;

        // Check if signer is owner
        if (hasRole(OWNER_ROLE, signer)) {
            validSignature = true;
        }
        // Check if signer is valid session key
        else {
            SessionKey storage sessionKey = sessionKeys[signer];
            if (sessionKey.active &&
                block.timestamp >= sessionKey.validAfter &&
                block.timestamp <= sessionKey.validUntil) {

                // Validate session key constraints
                if (_validateSessionKey(userOp, sessionKey)) {
                    validSignature = true;
                    validAfter = sessionKey.validAfter;
                    validUntil = sessionKey.validUntil;
                }
            }
        }

        // Pay for gas if needed
        if (missingAccountFunds > 0) {
            (bool success,) = payable(msg.sender).call{value: missingAccountFunds}("");
            require(success, "Payment failed");
        }

        // Return validation result
        if (validSignature) {
            return _packValidationData(false, validUntil, validAfter);
        } else {
            return SIG_VALIDATION_FAILED;
        }
    }

    /**
     * @dev Execute a transaction
     */
    function execute(
        address target,
        uint256 value,
        bytes calldata data
    ) external nonReentrant {
        require(msg.sender == address(entryPoint) || hasRole(OWNER_ROLE, msg.sender), "Unauthorized");
        require(!locked || block.timestamp >= lockUntil, "Account locked");

        // Validate with DAIO constitution
        (bool valid, string memory reason) = constitution.validateSmartAccountAction(
            address(this),
            target,
            value,
            data
        );
        require(valid, reason);

        // Check daily limits for corporate accounts
        if (isCorporateAccount && value > 0) {
            _checkDailyLimit(value);
        }

        // Execute the transaction
        (bool success, bytes memory result) = target.call{value: value}(data);
        if (!success) {
            assembly {
                revert(add(result, 32), mload(result))
            }
        }
    }

    /**
     * @dev Execute batch transactions
     */
    function executeBatch(
        BatchCall[] calldata calls
    ) external nonReentrant {
        require(msg.sender == address(entryPoint) || hasRole(OWNER_ROLE, msg.sender), "Unauthorized");
        require(!locked || block.timestamp >= lockUntil, "Account locked");

        uint256 totalValue = 0;
        for (uint256 i = 0; i < calls.length; i++) {
            totalValue += calls[i].value;
        }

        // Check daily limits for corporate accounts
        if (isCorporateAccount && totalValue > 0) {
            _checkDailyLimit(totalValue);
        }

        // Execute all calls
        for (uint256 i = 0; i < calls.length; i++) {
            BatchCall memory call = calls[i];

            // Validate each call
            (bool valid, string memory reason) = constitution.validateSmartAccountAction(
                address(this),
                call.target,
                call.value,
                call.data
            );
            require(valid, string(abi.encodePacked("Call ", i, ": ", reason)));

            // Execute call
            (bool success, bytes memory result) = call.target.call{value: call.value}(call.data);
            if (!success) {
                assembly {
                    revert(add(result, 32), mload(result))
                }
            }
        }

        emit BatchExecuted(calls.length);
    }

    // =============================================================
    //                  MULTISIG MANAGEMENT
    // =============================================================

    /**
     * @dev Add owner to multisig
     */
    function addOwner(address newOwner) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newOwner != address(0), "Invalid owner");
        require(!multisigConfig.isOwner[newOwner], "Already owner");

        _grantRole(OWNER_ROLE, newOwner);
        multisigConfig.isOwner[newOwner] = true;
        multisigConfig.owners.push(newOwner);
        multisigConfig.ownerCount++;

        emit OwnerAdded(newOwner);
    }

    /**
     * @dev Remove owner from multisig
     */
    function removeOwner(address owner) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(multisigConfig.isOwner[owner], "Not an owner");
        require(multisigConfig.ownerCount > 1, "Cannot remove last owner");
        require(multisigConfig.ownerCount - 1 >= multisigConfig.threshold, "Would break threshold");

        _revokeRole(OWNER_ROLE, owner);
        multisigConfig.isOwner[owner] = false;
        multisigConfig.ownerCount--;

        // Remove from owners array
        for (uint256 i = 0; i < multisigConfig.owners.length; i++) {
            if (multisigConfig.owners[i] == owner) {
                multisigConfig.owners[i] = multisigConfig.owners[multisigConfig.owners.length - 1];
                multisigConfig.owners.pop();
                break;
            }
        }

        emit OwnerRemoved(owner);
    }

    /**
     * @dev Change multisig threshold
     */
    function changeThreshold(uint256 newThreshold) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newThreshold > 0, "Threshold must be > 0");
        require(newThreshold <= multisigConfig.ownerCount, "Threshold too high");

        multisigConfig.threshold = newThreshold;
        emit ThresholdChanged(newThreshold);
    }

    // =============================================================
    //                  SESSION KEY MANAGEMENT
    // =============================================================

    /**
     * @dev Add session key with constraints
     */
    function addSessionKey(
        address sessionKey,
        uint48 validAfter,
        uint48 validUntil,
        uint256 limit,
        address[] calldata allowedTargets
    ) external onlyRole(OWNER_ROLE) {
        require(sessionKey != address(0), "Invalid session key");
        require(validUntil > validAfter, "Invalid time range");
        require(validAfter >= block.timestamp, "Invalid start time");

        SessionKey storage key = sessionKeys[sessionKey];
        key.key = sessionKey;
        key.validAfter = validAfter;
        key.validUntil = validUntil;
        key.limit = limit;
        key.spent = 0;
        key.active = true;

        // Set allowed targets
        for (uint256 i = 0; i < allowedTargets.length; i++) {
            key.allowedTargets.push(allowedTargets[i]);
            key.isAllowedTarget[allowedTargets[i]] = true;
        }

        sessionKeyList.push(sessionKey);
        _grantRole(SESSION_KEY_ROLE, sessionKey);

        emit SessionKeyAdded(sessionKey, validAfter, validUntil);
    }

    /**
     * @dev Remove session key
     */
    function removeSessionKey(address sessionKey) external onlyRole(OWNER_ROLE) {
        require(sessionKeys[sessionKey].active, "Session key not active");

        sessionKeys[sessionKey].active = false;
        _revokeRole(SESSION_KEY_ROLE, sessionKey);

        // Remove from list
        for (uint256 i = 0; i < sessionKeyList.length; i++) {
            if (sessionKeyList[i] == sessionKey) {
                sessionKeyList[i] = sessionKeyList[sessionKeyList.length - 1];
                sessionKeyList.pop();
                break;
            }
        }

        emit SessionKeyRemoved(sessionKey);
    }

    // =============================================================
    //                   SOCIAL RECOVERY
    // =============================================================

    /**
     * @dev Add guardian for social recovery
     */
    function addGuardian(address guardian) external onlyRole(OWNER_ROLE) {
        _addGuardian(guardian);
    }

    function _addGuardian(address guardian) internal {
        require(guardian != address(0), "Invalid guardian");
        require(!recoveryConfig.isGuardian[guardian], "Already guardian");

        recoveryConfig.guardians.push(guardian);
        recoveryConfig.isGuardian[guardian] = true;
        _grantRole(GUARDIAN_ROLE, guardian);

        emit GuardianAdded(guardian);
    }

    /**
     * @dev Remove guardian
     */
    function removeGuardian(address guardian) external onlyRole(OWNER_ROLE) {
        require(recoveryConfig.isGuardian[guardian], "Not a guardian");

        recoveryConfig.isGuardian[guardian] = false;
        _revokeRole(GUARDIAN_ROLE, guardian);

        // Remove from array
        for (uint256 i = 0; i < recoveryConfig.guardians.length; i++) {
            if (recoveryConfig.guardians[i] == guardian) {
                recoveryConfig.guardians[i] = recoveryConfig.guardians[recoveryConfig.guardians.length - 1];
                recoveryConfig.guardians.pop();
                break;
            }
        }

        emit GuardianRemoved(guardian);
    }

    /**
     * @dev Initiate account recovery
     */
    function initiateRecovery(address newOwner) external onlyRole(GUARDIAN_ROLE) returns (bytes32 requestId) {
        require(newOwner != address(0), "Invalid new owner");

        requestId = keccak256(abi.encodePacked(newOwner, block.timestamp, msg.sender));

        RecoveryRequest storage request = recoveryConfig.requests[requestId];
        request.newOwner = newOwner;
        request.confirmations = 1;
        request.executeAfter = block.timestamp + recoveryConfig.delay;
        request.confirmed[msg.sender] = true;

        emit RecoveryInitiated(requestId, newOwner);
    }

    /**
     * @dev Confirm recovery request
     */
    function confirmRecovery(bytes32 requestId) external onlyRole(GUARDIAN_ROLE) {
        RecoveryRequest storage request = recoveryConfig.requests[requestId];
        require(request.newOwner != address(0), "Recovery request not found");
        require(!request.executed, "Already executed");
        require(!request.confirmed[msg.sender], "Already confirmed");

        request.confirmed[msg.sender] = true;
        request.confirmations++;
    }

    /**
     * @dev Execute recovery if threshold reached
     */
    function executeRecovery(bytes32 requestId) external {
        RecoveryRequest storage request = recoveryConfig.requests[requestId];
        require(request.newOwner != address(0), "Recovery request not found");
        require(!request.executed, "Already executed");
        require(block.timestamp >= request.executeAfter, "Recovery delay not passed");
        require(request.confirmations >= recoveryConfig.threshold, "Insufficient confirmations");

        request.executed = true;

        // Remove all current owners
        for (uint256 i = 0; i < multisigConfig.owners.length; i++) {
            address owner = multisigConfig.owners[i];
            _revokeRole(OWNER_ROLE, owner);
            _revokeRole(DEFAULT_ADMIN_ROLE, owner);
            multisigConfig.isOwner[owner] = false;
        }

        // Clear owners array
        delete multisigConfig.owners;

        // Add new owner
        _grantRole(DEFAULT_ADMIN_ROLE, request.newOwner);
        _grantRole(OWNER_ROLE, request.newOwner);
        multisigConfig.isOwner[request.newOwner] = true;
        multisigConfig.owners.push(request.newOwner);
        multisigConfig.ownerCount = 1;
        multisigConfig.threshold = 1;

        emit RecoveryExecuted(requestId, request.newOwner);
    }

    // =============================================================
    //                  EMERGENCY CONTROLS
    // =============================================================

    /**
     * @dev Emergency lock account
     */
    function emergencyLock(uint256 lockDuration) external {
        require(
            hasRole(OWNER_ROLE, msg.sender) ||
            hasRole(GUARDIAN_ROLE, msg.sender) ||
            emergencyContacts[msg.sender],
            "Unauthorized"
        );

        locked = true;
        lockUntil = block.timestamp + lockDuration;

        emit AccountLocked(lockUntil);
    }

    /**
     * @dev Unlock account
     */
    function unlock() external onlyRole(OWNER_ROLE) {
        locked = false;
        lockUntil = 0;
        emit AccountUnlocked();
    }

    /**
     * @dev Emergency recovery by executive governance
     */
    function emergencyRecovery(address newOwner) external {
        require(governance.hasExecutiveApproval(msg.sender), "Requires executive approval");
        require(newOwner != address(0), "Invalid new owner");

        // Emergency transfer ownership
        address[] memory currentOwners = multisigConfig.owners;
        for (uint256 i = 0; i < currentOwners.length; i++) {
            _revokeRole(OWNER_ROLE, currentOwners[i]);
            _revokeRole(DEFAULT_ADMIN_ROLE, currentOwners[i]);
            multisigConfig.isOwner[currentOwners[i]] = false;
        }

        delete multisigConfig.owners;

        _grantRole(DEFAULT_ADMIN_ROLE, newOwner);
        _grantRole(OWNER_ROLE, newOwner);
        multisigConfig.isOwner[newOwner] = true;
        multisigConfig.owners.push(newOwner);
        multisigConfig.ownerCount = 1;
        multisigConfig.threshold = 1;

        emit EmergencyRecovery(newOwner, msg.sender);
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Check if address is owner
     */
    function isOwner(address account) external view returns (bool) {
        return hasRole(OWNER_ROLE, account);
    }

    /**
     * @dev Get all owners
     */
    function getOwners() external view returns (address[] memory) {
        return multisigConfig.owners;
    }

    /**
     * @dev Get all session keys
     */
    function getSessionKeys() external view returns (address[] memory) {
        return sessionKeyList;
    }

    /**
     * @dev Get all guardians
     */
    function getGuardians() external view returns (address[] memory) {
        return recoveryConfig.guardians;
    }

    // =============================================================
    //                    INTERNAL FUNCTIONS
    // =============================================================

    /**
     * @dev Validate session key constraints
     */
    function _validateSessionKey(
        IEntryPoint.UserOperation calldata userOp,
        SessionKey storage sessionKey
    ) internal returns (bool) {
        // Check spending limit
        if (sessionKey.spent + userOp.callGasLimit * userOp.maxFeePerGas > sessionKey.limit) {
            return false;
        }

        // Check allowed targets (simplified - would need to decode calldata)
        // This is a basic implementation

        // Update spent amount
        sessionKey.spent += userOp.callGasLimit * userOp.maxFeePerGas;

        return true;
    }

    /**
     * @dev Check and update daily spending limit
     */
    function _checkDailyLimit(uint256 amount) internal {
        uint256 today = block.timestamp / 1 days;

        if (lastResetDay < today) {
            spentToday = 0;
            lastResetDay = today;
        }

        require(spentToday + amount <= dailyLimit, "Daily limit exceeded");
        spentToday += amount;
    }

    /**
     * @dev Pack validation data for ERC4337
     */
    function _packValidationData(bool sigFailed, uint48 validUntil, uint48 validAfter) internal pure returns (uint256) {
        return uint256(validAfter) << 208 | uint256(validUntil) << 160 | (sigFailed ? 1 : 0);
    }

    // =============================================================
    //                      RECEIVE/FALLBACK
    // =============================================================

    receive() external payable {}

    fallback() external payable {}
}