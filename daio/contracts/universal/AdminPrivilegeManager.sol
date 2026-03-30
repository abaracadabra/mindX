// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "./UniversalDAIO.sol";

/**
 * @title AdminPrivilegeManager
 * @notice Granular admin privilege system with multi-signature and evolution support
 * @dev Manages privilege assignment, evolution, and multi-signature requirements for Universal DAIO
 */
contract AdminPrivilegeManager is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant PRIVILEGE_ADMIN_ROLE = keccak256("PRIVILEGE_ADMIN_ROLE");
    bytes32 public constant PRIVILEGE_GRANTER_ROLE = keccak256("PRIVILEGE_GRANTER_ROLE");
    bytes32 public constant EMERGENCY_PRIVILEGE_ROLE = keccak256("EMERGENCY_PRIVILEGE_ROLE");
    bytes32 public constant MULTI_SIG_MANAGER_ROLE = keccak256("MULTI_SIG_MANAGER_ROLE");

    using ECDSA for bytes32;

    UniversalDAIO public immutable universalDAIO;

    // Administrative privilege types with granular control
    enum AdminPrivilege {
        PARAMETER_MODIFY,           // Modify configuration parameters
        GOVERNANCE_EVOLVE,          // Force governance evolution
        EMERGENCY_ACTION,           // Emergency stops and overrides
        MULTISIG_MODIFY,           // Modify multi-sig requirements
        CROSS_CHAIN_DEPLOY,        // Deploy to new chains
        ASSET_MANAGER,             // Manage voting assets
        PROPOSAL_MODERATE,         // Moderate proposals
        TREASURY_EMERGENCY,        // Emergency treasury access
        USER_MANAGEMENT,           // Manage user roles and permissions
        SYSTEM_UPGRADE,            // Upgrade system contracts
        AUDIT_ACCESS,              // Access audit functions
        DATA_EXPORT,               // Export system data
        INTEGRATION_MANAGE,        // Manage external integrations
        AI_CONTROL,                // Control AI integration settings
        BRIDGE_CONTROL,            // Control cross-chain bridge operations
        CUSTOM_PRIVILEGE           // Custom privilege definition
    }

    // Privilege configuration with governance stage requirements
    struct PrivilegeConfig {
        AdminPrivilege privilege;
        UniversalDAIO.GovernanceStage requiredStage; // Minimum stage to use privilege
        uint256 requiredSignatures;   // Multi-sig requirement
        uint256 cooldownPeriod;       // Cooldown between uses
        uint256 usageLimit;           // Maximum uses per time period
        uint256 timePeriod;           // Time period for usage limit
        bool requiresEvolution;       // Privilege triggers governance evolution
        bool emergencyOverride;       // Can be used in emergency
        bool crossChainEnabled;       // Can be used across chains
        uint256 lastUsed;             // Last usage timestamp
        uint256 usageCount;           // Current usage count
        address[] authorizedUsers;    // Users with this privilege
        mapping(address => bool) userHasPrivilege; // Quick lookup
        mapping(address => uint256) userLastUsed;  // Per-user usage tracking
        mapping(address => uint256) userUsageCount; // Per-user usage count
    }

    // Multi-signature configuration per privilege and configuration
    struct MultiSigConfig {
        uint256 configId;             // Configuration ID
        AdminPrivilege privilege;     // Privilege requiring multi-sig
        address[] signers;            // Authorized signers
        uint256 requiredSignatures;  // Required signature count
        mapping(AdminPrivilege => uint256) privilegeThresholds; // Different thresholds per privilege
        mapping(address => bool) signerStatus; // Signer authorization status
        mapping(bytes32 => MultiSigTransaction) transactions; // Pending transactions
        bool crossChainRequired;      // Require signatures from multiple chains
        uint256 emergencyBypassTime; // Time after which emergency bypass possible
        uint256 signatureTimeout;    // Signature collection timeout
        bool active;                  // Multi-sig configuration active
    }

    // Multi-signature transaction
    struct MultiSigTransaction {
        bytes32 transactionId;        // Unique transaction ID
        uint256 configId;             // Configuration ID
        AdminPrivilege privilege;     // Privilege being exercised
        address initiator;            // Transaction initiator
        bytes data;                   // Transaction data
        uint256 deadline;             // Transaction deadline
        uint256 signatureCount;       // Current signature count
        bool executed;                // Transaction executed
        bool cancelled;               // Transaction cancelled
        mapping(address => bool) signatures; // Signer signatures
        mapping(address => uint256) signatureTime; // Signature timestamps
        string justification;         // Justification for action
        bytes result;                 // Transaction execution result
    }

    // Privilege delegation system
    struct PrivilegeDelegation {
        address delegator;            // Address delegating privilege
        address delegate;             // Address receiving privilege
        AdminPrivilege privilege;     // Privilege being delegated
        uint256 configId;             // Configuration ID
        uint256 expirationTime;      // Delegation expiration
        uint256 usageLimit;           // Limited usage count
        uint256 usageCount;           // Current usage
        bool revocable;               // Can be revoked early
        bool active;                  // Delegation is active
        string conditions;            // Delegation conditions
    }

    // Emergency privilege escalation
    struct EmergencyEscalation {
        uint256 configId;             // Configuration ID
        address requester;            // Emergency requester
        AdminPrivilege[] privileges;  // Privileges requested
        string justification;         // Emergency justification
        uint256 requestTime;          // Request timestamp
        uint256 approvalDeadline;     // Approval deadline
        uint256 escalationDuration;   // How long escalation lasts
        bool approved;                // Emergency approved
        bool executed;                // Emergency executed
        bool expired;                 // Emergency expired
        mapping(address => bool) approvers; // Emergency approvers
        uint256 approvalCount;        // Current approval count
        uint256 requiredApprovals;    // Required approvals
    }

    // Storage
    mapping(uint256 => mapping(AdminPrivilege => PrivilegeConfig)) public privilegeConfigs;
    mapping(uint256 => mapping(AdminPrivilege => MultiSigConfig)) public multiSigConfigs;
    mapping(bytes32 => PrivilegeDelegation) public privilegeDelegations;
    mapping(bytes32 => EmergencyEscalation) public emergencyEscalations;
    mapping(uint256 => mapping(address => AdminPrivilege[])) public userPrivileges;
    mapping(uint256 => mapping(address => bool)) public emergencyApprovers;

    // Global settings
    uint256 public defaultCooldownPeriod = 1 hours;
    uint256 public emergencyEscalationWindow = 6 hours;
    uint256 public maxPrivilegesPerUser = 10;
    uint256 public defaultSignatureTimeout = 24 hours;
    uint256 public emergencyApprovalTimeout = 2 hours;

    // Statistics
    uint256 public totalPrivilegeConfigurations;
    uint256 public totalMultiSigTransactions;
    uint256 public totalPrivilegeDelegations;
    uint256 public totalEmergencyEscalations;
    mapping(AdminPrivilege => uint256) public privilegeUsageStats;

    // Events
    event PrivilegeConfigured(
        uint256 indexed configId,
        AdminPrivilege indexed privilege,
        UniversalDAIO.GovernanceStage requiredStage,
        uint256 requiredSignatures,
        address indexed configuredBy
    );

    event PrivilegeGranted(
        uint256 indexed configId,
        address indexed user,
        AdminPrivilege indexed privilege,
        address grantedBy
    );

    event PrivilegeRevoked(
        uint256 indexed configId,
        address indexed user,
        AdminPrivilege indexed privilege,
        address revokedBy
    );

    event PrivilegeUsed(
        uint256 indexed configId,
        address indexed user,
        AdminPrivilege indexed privilege,
        bytes data,
        bytes result
    );

    event MultiSigTransactionCreated(
        bytes32 indexed transactionId,
        uint256 indexed configId,
        AdminPrivilege indexed privilege,
        address initiator,
        uint256 deadline
    );

    event MultiSigTransactionSigned(
        bytes32 indexed transactionId,
        address indexed signer,
        uint256 signatureCount,
        uint256 requiredSignatures
    );

    event MultiSigTransactionExecuted(
        bytes32 indexed transactionId,
        address indexed executor,
        bytes result
    );

    event PrivilegeDelegated(
        bytes32 indexed delegationId,
        address indexed delegator,
        address indexed delegate,
        AdminPrivilege privilege,
        uint256 expirationTime
    );

    event EmergencyEscalationRequested(
        bytes32 indexed escalationId,
        uint256 indexed configId,
        address indexed requester,
        AdminPrivilege[] privileges,
        uint256 approvalDeadline
    );

    event EmergencyEscalationApproved(
        bytes32 indexed escalationId,
        address indexed approver,
        uint256 approvalCount,
        uint256 requiredApprovals
    );

    event EmergencyPrivilegeActivated(
        bytes32 indexed escalationId,
        address indexed user,
        AdminPrivilege[] privileges,
        uint256 duration
    );

    modifier onlyPrivilegeAdmin() {
        require(hasRole(PRIVILEGE_ADMIN_ROLE, msg.sender), "Not privilege admin");
        _;
    }

    modifier validConfig(uint256 configId) {
        require(configId > 0, "Invalid config ID");
        _;
    }

    modifier hasPrivilege(uint256 configId, AdminPrivilege privilege) {
        require(_hasPrivilege(configId, msg.sender, privilege), "Insufficient privilege");
        _;
    }

    modifier multiSigRequired(uint256 configId, AdminPrivilege privilege) {
        if (_requiresMultiSig(configId, privilege)) {
            require(_isMultiSigApproved(configId, privilege, msg.sender), "Multi-sig approval required");
        }
        _;
    }

    constructor(address _universalDAIO) {
        require(_universalDAIO != address(0), "Invalid UniversalDAIO address");
        universalDAIO = UniversalDAIO(_universalDAIO);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PRIVILEGE_ADMIN_ROLE, msg.sender);
        _grantRole(PRIVILEGE_GRANTER_ROLE, msg.sender);
        _grantRole(EMERGENCY_PRIVILEGE_ROLE, msg.sender);
        _grantRole(MULTI_SIG_MANAGER_ROLE, msg.sender);

        _initializeDefaultPrivilegeConfigs();
    }

    /**
     * @notice Configure administrative privilege
     * @param configId Configuration ID
     * @param privilege Privilege type
     * @param requiredStage Minimum governance stage required
     * @param requiredSignatures Multi-signature requirement
     * @param cooldownPeriod Cooldown between uses
     * @param usageLimit Maximum uses per time period
     * @param timePeriod Time period for usage limit
     * @param requiresEvolution Whether usage triggers evolution
     */
    function configurePrivilege(
        uint256 configId,
        AdminPrivilege privilege,
        UniversalDAIO.GovernanceStage requiredStage,
        uint256 requiredSignatures,
        uint256 cooldownPeriod,
        uint256 usageLimit,
        uint256 timePeriod,
        bool requiresEvolution
    ) external validConfig(configId) onlyPrivilegeAdmin {
        PrivilegeConfig storage config = privilegeConfigs[configId][privilege];

        config.privilege = privilege;
        config.requiredStage = requiredStage;
        config.requiredSignatures = requiredSignatures;
        config.cooldownPeriod = cooldownPeriod;
        config.usageLimit = usageLimit;
        config.timePeriod = timePeriod;
        config.requiresEvolution = requiresEvolution;
        config.emergencyOverride = _isEmergencyPrivilege(privilege);
        config.crossChainEnabled = _isCrossChainPrivilege(privilege);

        totalPrivilegeConfigurations++;

        emit PrivilegeConfigured(configId, privilege, requiredStage, requiredSignatures, msg.sender);
    }

    /**
     * @notice Grant privilege to user
     * @param configId Configuration ID
     * @param user User address
     * @param privilege Privilege to grant
     */
    function grantPrivilege(
        uint256 configId,
        address user,
        AdminPrivilege privilege
    ) external validConfig(configId) {
        require(user != address(0), "Invalid user address");
        require(
            hasRole(PRIVILEGE_GRANTER_ROLE, msg.sender) ||
            _hasPrivilege(configId, msg.sender, AdminPrivilege.USER_MANAGEMENT),
            "Not authorized to grant privileges"
        );

        PrivilegeConfig storage config = privilegeConfigs[configId][privilege];
        require(userPrivileges[configId][user].length < maxPrivilegesPerUser, "Max privileges exceeded");

        // Check if user already has privilege
        require(!config.userHasPrivilege[user], "User already has privilege");

        // Add privilege to user
        config.userHasPrivilege[user] = true;
        config.authorizedUsers.push(user);
        userPrivileges[configId][user].push(privilege);

        emit PrivilegeGranted(configId, user, privilege, msg.sender);
    }

    /**
     * @notice Revoke privilege from user
     * @param configId Configuration ID
     * @param user User address
     * @param privilege Privilege to revoke
     */
    function revokePrivilege(
        uint256 configId,
        address user,
        AdminPrivilege privilege
    ) external validConfig(configId) {
        require(
            hasRole(PRIVILEGE_GRANTER_ROLE, msg.sender) ||
            _hasPrivilege(configId, msg.sender, AdminPrivilege.USER_MANAGEMENT),
            "Not authorized to revoke privileges"
        );

        PrivilegeConfig storage config = privilegeConfigs[configId][privilege];
        require(config.userHasPrivilege[user], "User does not have privilege");

        // Remove privilege from user
        config.userHasPrivilege[user] = false;

        // Remove from authorized users array
        _removeFromAuthorizedUsers(configId, privilege, user);

        // Remove from user privileges array
        _removeFromUserPrivileges(configId, user, privilege);

        emit PrivilegeRevoked(configId, user, privilege, msg.sender);
    }

    /**
     * @notice Use administrative privilege
     * @param configId Configuration ID
     * @param privilege Privilege to use
     * @param data Action data
     * @return result Action result
     */
    function usePrivilege(
        uint256 configId,
        AdminPrivilege privilege,
        bytes memory data
    ) external validConfig(configId) hasPrivilege(configId, privilege) multiSigRequired(configId, privilege) returns (bytes memory result) {
        require(!paused(), "Privilege system paused");

        PrivilegeConfig storage config = privilegeConfigs[configId][privilege];

        // Check governance stage requirement
        UniversalDAIO.UniversalConfig memory daoConfig = universalDAIO.getConfiguration(configId);
        require(uint256(daoConfig.currentStage) >= uint256(config.requiredStage), "Insufficient governance stage");

        // Check cooldown period
        require(
            block.timestamp >= config.userLastUsed[msg.sender] + config.cooldownPeriod,
            "Privilege in cooldown"
        );

        // Check usage limits
        if (config.usageLimit > 0) {
            require(config.userUsageCount[msg.sender] < config.usageLimit, "Usage limit exceeded");
        }

        // Execute privilege action
        result = _executePrivilegeAction(configId, privilege, data);

        // Update usage tracking
        config.lastUsed = block.timestamp;
        config.userLastUsed[msg.sender] = block.timestamp;
        config.usageCount++;
        config.userUsageCount[msg.sender]++;
        privilegeUsageStats[privilege]++;

        // Reset usage count if time period elapsed
        if (block.timestamp >= config.lastUsed + config.timePeriod) {
            config.usageCount = 1;
            config.userUsageCount[msg.sender] = 1;
        }

        emit PrivilegeUsed(configId, msg.sender, privilege, data, result);

        // Trigger evolution if required
        if (config.requiresEvolution) {
            universalDAIO.evolveGovernance(configId, false);
        }

        return result;
    }

    /**
     * @notice Create multi-signature transaction
     * @param configId Configuration ID
     * @param privilege Privilege requiring multi-sig
     * @param data Transaction data
     * @param justification Justification for action
     * @return transactionId Transaction ID
     */
    function createMultiSigTransaction(
        uint256 configId,
        AdminPrivilege privilege,
        bytes memory data,
        string memory justification
    ) external validConfig(configId) hasPrivilege(configId, privilege) returns (bytes32 transactionId) {
        require(_requiresMultiSig(configId, privilege), "Multi-sig not required");
        require(bytes(justification).length > 0, "Justification required");

        transactionId = keccak256(abi.encode(configId, privilege, data, block.timestamp, msg.sender));

        MultiSigConfig storage multiSig = multiSigConfigs[configId][privilege];
        MultiSigTransaction storage transaction = multiSig.transactions[transactionId];

        transaction.transactionId = transactionId;
        transaction.configId = configId;
        transaction.privilege = privilege;
        transaction.initiator = msg.sender;
        transaction.data = data;
        transaction.deadline = block.timestamp + defaultSignatureTimeout;
        transaction.justification = justification;

        totalMultiSigTransactions++;

        emit MultiSigTransactionCreated(transactionId, configId, privilege, msg.sender, transaction.deadline);

        return transactionId;
    }

    /**
     * @notice Sign multi-signature transaction
     * @param transactionId Transaction ID
     */
    function signMultiSigTransaction(bytes32 transactionId) external {
        MultiSigTransaction storage transaction = _getMultiSigTransaction(transactionId);
        require(block.timestamp <= transaction.deadline, "Transaction deadline expired");
        require(!transaction.executed && !transaction.cancelled, "Transaction not pending");

        MultiSigConfig storage multiSig = multiSigConfigs[transaction.configId][transaction.privilege];
        require(multiSig.signerStatus[msg.sender], "Not authorized signer");
        require(!transaction.signatures[msg.sender], "Already signed");

        transaction.signatures[msg.sender] = true;
        transaction.signatureTime[msg.sender] = block.timestamp;
        transaction.signatureCount++;

        emit MultiSigTransactionSigned(
            transactionId,
            msg.sender,
            transaction.signatureCount,
            multiSig.requiredSignatures
        );

        // Auto-execute if enough signatures
        if (transaction.signatureCount >= multiSig.requiredSignatures) {
            _executeMultiSigTransaction(transactionId);
        }
    }

    /**
     * @notice Execute multi-signature transaction
     * @param transactionId Transaction ID
     */
    function executeMultiSigTransaction(bytes32 transactionId) external {
        MultiSigTransaction storage transaction = _getMultiSigTransaction(transactionId);
        require(!transaction.executed, "Transaction already executed");

        MultiSigConfig storage multiSig = multiSigConfigs[transaction.configId][transaction.privilege];
        require(transaction.signatureCount >= multiSig.requiredSignatures, "Insufficient signatures");

        _executeMultiSigTransaction(transactionId);
    }

    /**
     * @notice Delegate privilege to another address
     * @param configId Configuration ID
     * @param delegate Address to delegate to
     * @param privilege Privilege to delegate
     * @param duration Delegation duration
     * @param usageLimit Usage limit for delegation
     * @param conditions Delegation conditions
     * @return delegationId Delegation ID
     */
    function delegatePrivilege(
        uint256 configId,
        address delegate,
        AdminPrivilege privilege,
        uint256 duration,
        uint256 usageLimit,
        string memory conditions
    ) external validConfig(configId) hasPrivilege(configId, privilege) returns (bytes32 delegationId) {
        require(delegate != address(0) && delegate != msg.sender, "Invalid delegate");
        require(duration > 0 && duration <= 30 days, "Invalid duration");

        delegationId = keccak256(abi.encode(msg.sender, delegate, privilege, block.timestamp));

        PrivilegeDelegation storage delegation = privilegeDelegations[delegationId];
        delegation.delegator = msg.sender;
        delegation.delegate = delegate;
        delegation.privilege = privilege;
        delegation.configId = configId;
        delegation.expirationTime = block.timestamp + duration;
        delegation.usageLimit = usageLimit;
        delegation.usageCount = 0;
        delegation.revocable = true;
        delegation.active = true;
        delegation.conditions = conditions;

        totalPrivilegeDelegations++;

        emit PrivilegeDelegated(delegationId, msg.sender, delegate, privilege, delegation.expirationTime);

        return delegationId;
    }

    /**
     * @notice Request emergency privilege escalation
     * @param configId Configuration ID
     * @param privileges Privileges requested
     * @param justification Emergency justification
     * @param duration Escalation duration
     * @return escalationId Escalation request ID
     */
    function requestEmergencyEscalation(
        uint256 configId,
        AdminPrivilege[] memory privileges,
        string memory justification,
        uint256 duration
    ) external validConfig(configId) returns (bytes32 escalationId) {
        require(privileges.length > 0, "No privileges requested");
        require(bytes(justification).length > 0, "Justification required");
        require(duration > 0 && duration <= emergencyEscalationWindow, "Invalid duration");

        escalationId = keccak256(abi.encode(configId, msg.sender, privileges, block.timestamp));

        EmergencyEscalation storage escalation = emergencyEscalations[escalationId];
        escalation.configId = configId;
        escalation.requester = msg.sender;
        escalation.privileges = privileges;
        escalation.justification = justification;
        escalation.requestTime = block.timestamp;
        escalation.approvalDeadline = block.timestamp + emergencyApprovalTimeout;
        escalation.escalationDuration = duration;
        escalation.requiredApprovals = _getRequiredEmergencyApprovals(configId);

        totalEmergencyEscalations++;

        emit EmergencyEscalationRequested(
            escalationId,
            configId,
            msg.sender,
            privileges,
            escalation.approvalDeadline
        );

        return escalationId;
    }

    /**
     * @notice Approve emergency escalation
     * @param escalationId Escalation ID
     */
    function approveEmergencyEscalation(bytes32 escalationId) external {
        EmergencyEscalation storage escalation = emergencyEscalations[escalationId];
        require(escalation.requestTime > 0, "Escalation does not exist");
        require(block.timestamp <= escalation.approvalDeadline, "Approval deadline expired");
        require(!escalation.executed && !escalation.expired, "Escalation not pending");

        require(
            hasRole(EMERGENCY_PRIVILEGE_ROLE, msg.sender) ||
            emergencyApprovers[escalation.configId][msg.sender],
            "Not authorized to approve emergency"
        );

        require(!escalation.approvers[msg.sender], "Already approved");

        escalation.approvers[msg.sender] = true;
        escalation.approvalCount++;

        emit EmergencyEscalationApproved(
            escalationId,
            msg.sender,
            escalation.approvalCount,
            escalation.requiredApprovals
        );

        // Auto-activate if enough approvals
        if (escalation.approvalCount >= escalation.requiredApprovals) {
            _activateEmergencyPrivileges(escalationId);
        }
    }

    /**
     * @notice Configure multi-signature requirements
     * @param configId Configuration ID
     * @param privilege Privilege requiring multi-sig
     * @param signers Authorized signers
     * @param requiredSignatures Required signature count
     */
    function configureMultiSig(
        uint256 configId,
        AdminPrivilege privilege,
        address[] memory signers,
        uint256 requiredSignatures
    ) external validConfig(configId) {
        require(
            hasRole(MULTI_SIG_MANAGER_ROLE, msg.sender) ||
            _hasPrivilege(configId, msg.sender, AdminPrivilege.MULTISIG_MODIFY),
            "Not authorized to configure multi-sig"
        );

        require(signers.length >= requiredSignatures && requiredSignatures > 0, "Invalid signature requirements");

        MultiSigConfig storage multiSig = multiSigConfigs[configId][privilege];
        multiSig.configId = configId;
        multiSig.privilege = privilege;
        multiSig.signers = signers;
        multiSig.requiredSignatures = requiredSignatures;
        multiSig.active = true;

        // Update signer status
        for (uint i = 0; i < signers.length; i++) {
            multiSig.signerStatus[signers[i]] = true;
        }
    }

    /**
     * @notice Get user privileges for configuration
     * @param configId Configuration ID
     * @param user User address
     * @return privileges Array of user privileges
     */
    function getUserPrivileges(uint256 configId, address user) external view validConfig(configId) returns (AdminPrivilege[] memory) {
        return userPrivileges[configId][user];
    }

    /**
     * @notice Check if user has specific privilege
     * @param configId Configuration ID
     * @param user User address
     * @param privilege Privilege to check
     * @return hasPriv Whether user has privilege
     */
    function hasUserPrivilege(uint256 configId, address user, AdminPrivilege privilege) external view validConfig(configId) returns (bool) {
        return _hasPrivilege(configId, user, privilege);
    }

    /**
     * @notice Get privilege configuration
     * @param configId Configuration ID
     * @param privilege Privilege type
     * @return config Privilege configuration
     */
    function getPrivilegeConfig(uint256 configId, AdminPrivilege privilege) external view validConfig(configId) returns (
        UniversalDAIO.GovernanceStage requiredStage,
        uint256 requiredSignatures,
        uint256 cooldownPeriod,
        uint256 usageLimit,
        uint256 timePeriod,
        bool requiresEvolution,
        bool emergencyOverride,
        bool crossChainEnabled
    ) {
        PrivilegeConfig storage config = privilegeConfigs[configId][privilege];
        return (
            config.requiredStage,
            config.requiredSignatures,
            config.cooldownPeriod,
            config.usageLimit,
            config.timePeriod,
            config.requiresEvolution,
            config.emergencyOverride,
            config.crossChainEnabled
        );
    }

    /**
     * @notice Get multi-signature configuration
     * @param configId Configuration ID
     * @param privilege Privilege type
     * @return signers Authorized signers
     * @return requiredSignatures Required signature count
     * @return active Whether configuration is active
     */
    function getMultiSigConfig(uint256 configId, AdminPrivilege privilege) external view validConfig(configId) returns (
        address[] memory signers,
        uint256 requiredSignatures,
        bool active
    ) {
        MultiSigConfig storage multiSig = multiSigConfigs[configId][privilege];
        return (multiSig.signers, multiSig.requiredSignatures, multiSig.active);
    }

    /**
     * @notice Update global privilege settings
     */
    function updateGlobalSettings(
        uint256 _defaultCooldownPeriod,
        uint256 _emergencyEscalationWindow,
        uint256 _maxPrivilegesPerUser,
        uint256 _defaultSignatureTimeout,
        uint256 _emergencyApprovalTimeout
    ) external onlyPrivilegeAdmin {
        defaultCooldownPeriod = _defaultCooldownPeriod;
        emergencyEscalationWindow = _emergencyEscalationWindow;
        maxPrivilegesPerUser = _maxPrivilegesPerUser;
        defaultSignatureTimeout = _defaultSignatureTimeout;
        emergencyApprovalTimeout = _emergencyApprovalTimeout;
    }

    /**
     * @notice Pause privilege system
     */
    function pausePrivilegeSystem() external onlyPrivilegeAdmin {
        _pause();
    }

    /**
     * @notice Unpause privilege system
     */
    function unpausePrivilegeSystem() external onlyPrivilegeAdmin {
        _unpause();
    }

    // Internal Functions

    /**
     * @notice Check if user has privilege
     */
    function _hasPrivilege(uint256 configId, address user, AdminPrivilege privilege) internal view returns (bool) {
        PrivilegeConfig storage config = privilegeConfigs[configId][privilege];

        // Check direct privilege
        if (config.userHasPrivilege[user]) return true;

        // Check delegation
        return _hasDelegatedPrivilege(configId, user, privilege);
    }

    /**
     * @notice Check if user has delegated privilege
     */
    function _hasDelegatedPrivilege(uint256 configId, address user, AdminPrivilege privilege) internal view returns (bool) {
        // This would iterate through active delegations - simplified for now
        return false;
    }

    /**
     * @notice Check if privilege requires multi-signature
     */
    function _requiresMultiSig(uint256 configId, AdminPrivilege privilege) internal view returns (bool) {
        return multiSigConfigs[configId][privilege].active;
    }

    /**
     * @notice Check if multi-signature is approved
     */
    function _isMultiSigApproved(uint256 configId, AdminPrivilege privilege, address user) internal view returns (bool) {
        // This would check if there's an approved multi-sig transaction - simplified for now
        return false;
    }

    /**
     * @notice Execute privilege action
     */
    function _executePrivilegeAction(uint256 configId, AdminPrivilege privilege, bytes memory data) internal returns (bytes memory) {
        // Execute specific privilege action based on type
        if (privilege == AdminPrivilege.PARAMETER_MODIFY) {
            return _executeParameterModification(configId, data);
        } else if (privilege == AdminPrivilege.GOVERNANCE_EVOLVE) {
            return _executeGovernanceEvolution(configId, data);
        }

        return "Action executed";
    }

    /**
     * @notice Execute parameter modification
     */
    function _executeParameterModification(uint256 configId, bytes memory data) internal returns (bytes memory) {
        // Implementation would integrate with ParameterRegistry
        return "Parameter modified";
    }

    /**
     * @notice Execute governance evolution
     */
    function _executeGovernanceEvolution(uint256 configId, bytes memory data) internal returns (bytes memory) {
        // Implementation would trigger governance evolution
        return "Governance evolved";
    }

    /**
     * @notice Get multi-signature transaction
     */
    function _getMultiSigTransaction(bytes32 transactionId) internal view returns (MultiSigTransaction storage) {
        // Find transaction across all configurations - simplified access pattern
        // In practice, would need to track transaction locations
        revert("Transaction access pattern needs refinement");
    }

    /**
     * @notice Execute multi-signature transaction
     */
    function _executeMultiSigTransaction(bytes32 transactionId) internal {
        MultiSigTransaction storage transaction = _getMultiSigTransaction(transactionId);

        // Execute the transaction
        bytes memory result = _executePrivilegeAction(transaction.configId, transaction.privilege, transaction.data);

        transaction.executed = true;
        transaction.result = result;

        emit MultiSigTransactionExecuted(transactionId, msg.sender, result);
    }

    /**
     * @notice Activate emergency privileges
     */
    function _activateEmergencyPrivileges(bytes32 escalationId) internal {
        EmergencyEscalation storage escalation = emergencyEscalations[escalationId];
        escalation.approved = true;
        escalation.executed = true;

        // Grant temporary privileges
        for (uint i = 0; i < escalation.privileges.length; i++) {
            AdminPrivilege privilege = escalation.privileges[i];
            PrivilegeConfig storage config = privilegeConfigs[escalation.configId][privilege];

            // Temporarily grant privilege
            config.userHasPrivilege[escalation.requester] = true;
        }

        emit EmergencyPrivilegeActivated(escalationId, escalation.requester, escalation.privileges, escalation.escalationDuration);
    }

    /**
     * @notice Get required emergency approvals
     */
    function _getRequiredEmergencyApprovals(uint256 configId) internal view returns (uint256) {
        // Base requirement of 2 approvals, could be configurable
        return 2;
    }

    /**
     * @notice Check if privilege is emergency-capable
     */
    function _isEmergencyPrivilege(AdminPrivilege privilege) internal pure returns (bool) {
        return privilege == AdminPrivilege.EMERGENCY_ACTION ||
               privilege == AdminPrivilege.TREASURY_EMERGENCY ||
               privilege == AdminPrivilege.SYSTEM_UPGRADE;
    }

    /**
     * @notice Check if privilege is cross-chain capable
     */
    function _isCrossChainPrivilege(AdminPrivilege privilege) internal pure returns (bool) {
        return privilege == AdminPrivilege.CROSS_CHAIN_DEPLOY ||
               privilege == AdminPrivilege.BRIDGE_CONTROL ||
               privilege == AdminPrivilege.PARAMETER_MODIFY;
    }

    /**
     * @notice Remove user from authorized users array
     */
    function _removeFromAuthorizedUsers(uint256 configId, AdminPrivilege privilege, address user) internal {
        PrivilegeConfig storage config = privilegeConfigs[configId][privilege];
        for (uint i = 0; i < config.authorizedUsers.length; i++) {
            if (config.authorizedUsers[i] == user) {
                config.authorizedUsers[i] = config.authorizedUsers[config.authorizedUsers.length - 1];
                config.authorizedUsers.pop();
                break;
            }
        }
    }

    /**
     * @notice Remove privilege from user privileges array
     */
    function _removeFromUserPrivileges(uint256 configId, address user, AdminPrivilege privilege) internal {
        AdminPrivilege[] storage privileges = userPrivileges[configId][user];
        for (uint i = 0; i < privileges.length; i++) {
            if (privileges[i] == privilege) {
                privileges[i] = privileges[privileges.length - 1];
                privileges.pop();
                break;
            }
        }
    }

    /**
     * @notice Initialize default privilege configurations
     */
    function _initializeDefaultPrivilegeConfigs() internal {
        // This would set up default configurations for each governance stage
        // Simplified for initial implementation
    }
}