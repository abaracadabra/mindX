// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./UniversalDAIO.sol";

/**
 * @title ParameterRegistry
 * @notice Universal parameter configuration system with hierarchical inheritance
 * @dev Manages all configurable parameters for Universal DAIO with type safety and validation
 */
contract ParameterRegistry is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant PARAMETER_ADMIN_ROLE = keccak256("PARAMETER_ADMIN_ROLE");
    bytes32 public constant PARAMETER_VALIDATOR_ROLE = keccak256("PARAMETER_VALIDATOR_ROLE");
    bytes32 public constant CROSS_CHAIN_SYNC_ROLE = keccak256("CROSS_CHAIN_SYNC_ROLE");
    bytes32 public constant EMERGENCY_OVERRIDE_ROLE = keccak256("EMERGENCY_OVERRIDE_ROLE");

    UniversalDAIO public immutable universalDAIO;

    // Parameter types for categorization and validation
    enum ParameterType {
        GOVERNANCE,         // Voting thresholds, periods, weights
        ECONOMIC,           // Fees, stakes, rewards, treasury rules
        OPERATIONAL,        // Timeouts, limits, automation settings
        SECURITY,           // Emergency controls, pause mechanisms
        EVOLUTION,          // Stage transition criteria
        MULTICHAIN,         // Cross-chain coordination parameters
        AI_INTEGRATION,     // AI voting weights, capabilities
        CUSTOM              // User-defined parameters
    }

    // Parameter data types for type safety
    enum ParameterDataType {
        UINT256,            // Integer values
        UINT256_ARRAY,      // Array of integers
        ADDRESS,            // Ethereum address
        ADDRESS_ARRAY,      // Array of addresses
        BYTES32,            // Hash/identifier
        BYTES32_ARRAY,      // Array of hashes
        BOOL,               // Boolean value
        STRING,             // String value
        BYTES               // Raw bytes data
    }

    // Parameter configuration with validation rules
    struct Parameter {
        string key;                     // Parameter identifier
        ParameterType paramType;        // Parameter category
        ParameterDataType dataType;     // Data type for validation
        bytes value;                    // Encoded parameter value
        uint256 minValue;               // Minimum allowed value (for numeric types)
        uint256 maxValue;               // Maximum allowed value (for numeric types)
        bool requiresEvolution;         // Changes trigger governance evolution
        bool crossChainSync;            // Sync across all chains
        bool emergencyModifiable;       // Can be modified in emergency
        uint256 modificationDelay;      // Delay before parameter change takes effect
        uint256 lastModified;           // Timestamp of last modification
        address lastModifiedBy;         // Address that last modified parameter
        uint256[] dependentChains;      // Chains that must sync this parameter
        bytes32[] dependencies;         // Other parameters this depends on
        bytes validationRules;          // Custom validation logic
    }

    // Parameter hierarchy for inheritance
    struct ParameterHierarchy {
        uint256 configId;               // Configuration ID
        mapping(string => Parameter) parameters; // Config-specific parameters
        mapping(string => bool) overrides;       // Parameters that override defaults
        mapping(string => uint256) inheritanceLevel; // Inheritance priority
        uint256 totalParameters;        // Total parameter count
        bytes32 hierarchyHash;          // Hash of current hierarchy
    }

    // Parameter templates for quick deployment
    struct ParameterTemplate {
        string templateName;            // Template identifier
        ParameterType targetType;       // Primary parameter type
        UniversalDAIO.GovernanceStage targetStage; // Target governance stage
        mapping(string => Parameter) defaultParams; // Default parameters
        uint256 parameterCount;         // Number of parameters in template
        bool active;                    // Template is active
        uint256 deploymentCount;        // Number of times deployed
    }

    // Cross-chain parameter synchronization
    struct CrossChainSync {
        uint256 configId;               // Source configuration ID
        string parameterKey;            // Parameter being synced
        uint256[] targetChains;         // Target chains for sync
        mapping(uint256 => bool) chainSynced; // Chain sync status
        mapping(uint256 => bytes32) chainHashes; // Parameter hash per chain
        uint256 syncInitiated;          // Sync initiation timestamp
        uint256 syncCompleted;          // Sync completion timestamp
        bool syncInProgress;            // Sync operation in progress
        address syncInitiator;          // Address that initiated sync
    }

    // Parameter modification request for delayed changes
    struct ModificationRequest {
        uint256 configId;               // Configuration ID
        string parameterKey;            // Parameter to modify
        bytes newValue;                 // New parameter value
        uint256 requestTime;            // Request timestamp
        uint256 effectiveTime;          // When change becomes effective
        address requester;              // Address that requested change
        bool approved;                  // Admin approval status
        bool executed;                  // Change has been executed
        string justification;           // Justification for change
        uint256 requiredApprovals;      // Number of approvals needed
        mapping(address => bool) approvals; // Admin approvals
    }

    // Storage
    mapping(uint256 => ParameterHierarchy) public parameterHierarchies;
    mapping(string => ParameterTemplate) public parameterTemplates;
    mapping(bytes32 => CrossChainSync) public crossChainSyncs;
    mapping(bytes32 => ModificationRequest) public modificationRequests;
    mapping(string => Parameter) public globalDefaults; // Global default parameters
    mapping(ParameterType => string[]) public parametersByType;
    mapping(uint256 => mapping(string => uint256)) public parameterHistory; // Version history

    // Global settings
    uint256 public defaultModificationDelay = 1 days;
    uint256 public emergencyModificationWindow = 6 hours;
    uint256 public maxParametersPerConfig = 1000;
    uint256 public syncTimeoutPeriod = 1 hours;
    bool public globalParameterLock = false;

    // Statistics
    uint256 public totalParameterConfigurations;
    uint256 public totalCrossChainSyncs;
    uint256 public totalModificationRequests;
    mapping(ParameterType => uint256) public parameterTypeUsage;

    // Template names for common configurations
    string[] public templateNames;

    // Events
    event ParameterConfigured(
        uint256 indexed configId,
        string indexed parameterKey,
        ParameterType paramType,
        bytes value,
        address indexed configuredBy
    );

    event ParameterModificationRequested(
        bytes32 indexed requestId,
        uint256 indexed configId,
        string indexed parameterKey,
        bytes newValue,
        uint256 effectiveTime,
        address requester
    );

    event ParameterModified(
        uint256 indexed configId,
        string indexed parameterKey,
        bytes oldValue,
        bytes newValue,
        address modifiedBy
    );

    event ParameterTemplateCreated(
        string indexed templateName,
        ParameterType targetType,
        UniversalDAIO.GovernanceStage targetStage,
        uint256 parameterCount
    );

    event CrossChainSyncInitiated(
        bytes32 indexed syncId,
        uint256 indexed configId,
        string indexed parameterKey,
        uint256[] targetChains,
        address initiator
    );

    event CrossChainSyncCompleted(
        bytes32 indexed syncId,
        uint256 successfulChains,
        uint256 failedChains,
        uint256 duration
    );

    event ParameterValidationFailed(
        uint256 indexed configId,
        string indexed parameterKey,
        string reason
    );

    event EmergencyParameterOverride(
        uint256 indexed configId,
        string indexed parameterKey,
        bytes oldValue,
        bytes newValue,
        address overrideBy,
        string reason
    );

    event ParameterHierarchyUpdated(
        uint256 indexed configId,
        bytes32 oldHash,
        bytes32 newHash,
        uint256 parametersChanged
    );

    modifier onlyParameterAdmin() {
        require(hasRole(PARAMETER_ADMIN_ROLE, msg.sender), "Not parameter admin");
        _;
    }

    modifier validConfig(uint256 configId) {
        require(configId > 0, "Invalid config ID");
        _;
    }

    modifier parameterExists(uint256 configId, string memory key) {
        require(_parameterExists(configId, key), "Parameter does not exist");
        _;
    }

    modifier notGloballyLocked() {
        require(!globalParameterLock, "Parameter system globally locked");
        _;
    }

    constructor(address _universalDAIO) {
        require(_universalDAIO != address(0), "Invalid UniversalDAIO address");
        universalDAIO = UniversalDAIO(_universalDAIO);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PARAMETER_ADMIN_ROLE, msg.sender);
        _grantRole(PARAMETER_VALIDATOR_ROLE, msg.sender);
        _grantRole(CROSS_CHAIN_SYNC_ROLE, msg.sender);
        _grantRole(EMERGENCY_OVERRIDE_ROLE, msg.sender);

        _initializeGlobalDefaults();
        _createDefaultTemplates();
    }

    /**
     * @notice Configure parameter for a DAIO configuration
     * @param configId Universal DAIO configuration ID
     * @param key Parameter key
     * @param paramType Parameter type
     * @param dataType Parameter data type
     * @param value Encoded parameter value
     * @param minValue Minimum allowed value
     * @param maxValue Maximum allowed value
     * @param requiresEvolution Whether changes require evolution
     * @param crossChainSync Whether to sync across chains
     */
    function configureParameter(
        uint256 configId,
        string memory key,
        ParameterType paramType,
        ParameterDataType dataType,
        bytes memory value,
        uint256 minValue,
        uint256 maxValue,
        bool requiresEvolution,
        bool crossChainSync
    ) external validConfig(configId) onlyParameterAdmin notGloballyLocked {
        require(bytes(key).length > 0, "Parameter key required");
        require(value.length > 0, "Parameter value required");

        // Validate parameter limits
        ParameterHierarchy storage hierarchy = parameterHierarchies[configId];
        require(hierarchy.totalParameters < maxParametersPerConfig, "Max parameters exceeded");

        // Validate parameter value
        require(_validateParameterValue(dataType, value, minValue, maxValue), "Invalid parameter value");

        // Create parameter
        Parameter storage param = hierarchy.parameters[key];
        param.key = key;
        param.paramType = paramType;
        param.dataType = dataType;
        param.value = value;
        param.minValue = minValue;
        param.maxValue = maxValue;
        param.requiresEvolution = requiresEvolution;
        param.crossChainSync = crossChainSync;
        param.emergencyModifiable = _isEmergencyModifiable(paramType, key);
        param.modificationDelay = _getModificationDelay(paramType);
        param.lastModified = block.timestamp;
        param.lastModifiedBy = msg.sender;

        // Update hierarchy
        if (!_parameterExists(configId, key)) {
            hierarchy.totalParameters++;
            parametersByType[paramType].push(key);
        }

        hierarchy.overrides[key] = true;
        hierarchy.hierarchyHash = keccak256(abi.encode(configId, hierarchy.totalParameters, block.timestamp));

        // Update statistics
        parameterTypeUsage[paramType]++;

        emit ParameterConfigured(configId, key, paramType, value, msg.sender);

        // Initiate cross-chain sync if required
        if (crossChainSync) {
            _initiateCrossChainSync(configId, key);
        }
    }

    /**
     * @notice Apply parameter template to configuration
     * @param configId Configuration ID
     * @param templateName Template to apply
     * @param overrideExisting Whether to override existing parameters
     */
    function applyParameterTemplate(
        uint256 configId,
        string memory templateName,
        bool overrideExisting
    ) external validConfig(configId) onlyParameterAdmin notGloballyLocked {
        ParameterTemplate storage template = parameterTemplates[templateName];
        require(template.active, "Template not active");

        // Apply all parameters from template
        // Note: Due to limitations with mappings in structs, this would need
        // to be implemented with explicit parameter lists or external storage

        template.deploymentCount++;

        emit ParameterTemplateCreated(templateName, template.targetType, template.targetStage, template.parameterCount);
    }

    /**
     * @notice Request parameter modification with delay
     * @param configId Configuration ID
     * @param key Parameter key
     * @param newValue New parameter value
     * @param justification Justification for change
     * @return requestId Modification request ID
     */
    function requestParameterModification(
        uint256 configId,
        string memory key,
        bytes memory newValue,
        string memory justification
    ) external validConfig(configId) parameterExists(configId, key) returns (bytes32 requestId) {
        require(!paused(), "Parameter system paused");
        require(bytes(justification).length > 0, "Justification required");

        Parameter storage param = parameterHierarchies[configId].parameters[key];

        // Check modification authority
        require(_hasModificationAuthority(configId, key, msg.sender), "Not authorized to modify");

        // Validate new value
        require(_validateParameterValue(param.dataType, newValue, param.minValue, param.maxValue), "Invalid value");

        // Generate request ID
        requestId = keccak256(abi.encode(configId, key, newValue, block.timestamp, msg.sender));

        // Create modification request
        ModificationRequest storage request = modificationRequests[requestId];
        request.configId = configId;
        request.parameterKey = key;
        request.newValue = newValue;
        request.requestTime = block.timestamp;
        request.effectiveTime = block.timestamp + param.modificationDelay;
        request.requester = msg.sender;
        request.approved = false;
        request.executed = false;
        request.justification = justification;
        request.requiredApprovals = _getRequiredApprovals(configId, key);

        totalModificationRequests++;

        emit ParameterModificationRequested(requestId, configId, key, newValue, request.effectiveTime, msg.sender);

        return requestId;
    }

    /**
     * @notice Approve parameter modification request
     * @param requestId Modification request ID
     */
    function approveParameterModification(bytes32 requestId) external {
        ModificationRequest storage request = modificationRequests[requestId];
        require(request.requestTime > 0, "Request does not exist");
        require(!request.executed, "Request already executed");

        // Check approval authority
        require(_hasApprovalAuthority(request.configId, request.parameterKey, msg.sender), "Not authorized to approve");
        require(!request.approvals[msg.sender], "Already approved");

        request.approvals[msg.sender] = true;

        // Check if enough approvals
        uint256 currentApprovals = _countApprovals(requestId);
        if (currentApprovals >= request.requiredApprovals) {
            request.approved = true;
        }

        // Auto-execute if approved and past effective time
        if (request.approved && block.timestamp >= request.effectiveTime) {
            _executeParameterModification(requestId);
        }
    }

    /**
     * @notice Execute approved parameter modification
     * @param requestId Modification request ID
     */
    function executeParameterModification(bytes32 requestId) external {
        ModificationRequest storage request = modificationRequests[requestId];
        require(request.approved, "Request not approved");
        require(block.timestamp >= request.effectiveTime, "Not yet effective");
        require(!request.executed, "Already executed");

        _executeParameterModification(requestId);
    }

    /**
     * @notice Emergency parameter override
     * @param configId Configuration ID
     * @param key Parameter key
     * @param newValue New parameter value
     * @param reason Emergency reason
     */
    function emergencyParameterOverride(
        uint256 configId,
        string memory key,
        bytes memory newValue,
        string memory reason
    ) external validConfig(configId) parameterExists(configId, key) {
        require(hasRole(EMERGENCY_OVERRIDE_ROLE, msg.sender), "Not authorized for emergency override");
        require(bytes(reason).length > 0, "Emergency reason required");

        Parameter storage param = parameterHierarchies[configId].parameters[key];
        require(param.emergencyModifiable, "Parameter not emergency modifiable");

        // Validate new value
        require(_validateParameterValue(param.dataType, newValue, param.minValue, param.maxValue), "Invalid value");

        bytes memory oldValue = param.value;
        param.value = newValue;
        param.lastModified = block.timestamp;
        param.lastModifiedBy = msg.sender;

        // Update parameter history
        parameterHistory[configId][key] = block.timestamp;

        emit EmergencyParameterOverride(configId, key, oldValue, newValue, msg.sender, reason);
        emit ParameterModified(configId, key, oldValue, newValue, msg.sender);

        // Initiate cross-chain sync if required
        if (param.crossChainSync) {
            _initiateCrossChainSync(configId, key);
        }
    }

    /**
     * @notice Get parameter value
     * @param configId Configuration ID
     * @param key Parameter key
     * @return Parameter value with inheritance resolution
     */
    function getParameter(uint256 configId, string memory key) external view validConfig(configId) returns (Parameter memory) {
        return _resolveParameter(configId, key);
    }

    /**
     * @notice Get parameter as uint256
     * @param configId Configuration ID
     * @param key Parameter key
     * @return value Parameter value as uint256
     */
    function getParameterUint256(uint256 configId, string memory key) external view validConfig(configId) returns (uint256 value) {
        Parameter memory param = _resolveParameter(configId, key);
        require(param.dataType == ParameterDataType.UINT256, "Not uint256 parameter");
        return abi.decode(param.value, (uint256));
    }

    /**
     * @notice Get parameter as address
     * @param configId Configuration ID
     * @param key Parameter key
     * @return value Parameter value as address
     */
    function getParameterAddress(uint256 configId, string memory key) external view validConfig(configId) returns (address value) {
        Parameter memory param = _resolveParameter(configId, key);
        require(param.dataType == ParameterDataType.ADDRESS, "Not address parameter");
        return abi.decode(param.value, (address));
    }

    /**
     * @notice Get parameter as bool
     * @param configId Configuration ID
     * @param key Parameter key
     * @return value Parameter value as bool
     */
    function getParameterBool(uint256 configId, string memory key) external view validConfig(configId) returns (bool value) {
        Parameter memory param = _resolveParameter(configId, key);
        require(param.dataType == ParameterDataType.BOOL, "Not bool parameter");
        return abi.decode(param.value, (bool));
    }

    /**
     * @notice Get all parameters for configuration by type
     * @param configId Configuration ID
     * @param paramType Parameter type filter
     * @return keys Array of parameter keys
     */
    function getParametersByType(uint256 configId, ParameterType paramType) external view validConfig(configId) returns (string[] memory keys) {
        return parametersByType[paramType];
    }

    /**
     * @notice Get parameter configuration hierarchy
     * @param configId Configuration ID
     * @return totalParams Total parameters in hierarchy
     * @return hierarchyHash Current hierarchy hash
     */
    function getParameterHierarchy(uint256 configId) external view validConfig(configId) returns (
        uint256 totalParams,
        bytes32 hierarchyHash
    ) {
        ParameterHierarchy storage hierarchy = parameterHierarchies[configId];
        return (hierarchy.totalParameters, hierarchy.hierarchyHash);
    }

    /**
     * @notice Get cross-chain sync status
     * @param syncId Cross-chain sync ID
     * @return sync Cross-chain sync details
     */
    function getCrossChainSyncStatus(bytes32 syncId) external view returns (CrossChainSync memory sync) {
        return crossChainSyncs[syncId];
    }

    /**
     * @notice Get modification request details
     * @param requestId Modification request ID
     * @return request Modification request details
     */
    function getModificationRequest(bytes32 requestId) external view returns (
        uint256 configId,
        string memory parameterKey,
        bytes memory newValue,
        uint256 effectiveTime,
        address requester,
        bool approved,
        bool executed,
        string memory justification
    ) {
        ModificationRequest storage request = modificationRequests[requestId];
        return (
            request.configId,
            request.parameterKey,
            request.newValue,
            request.effectiveTime,
            request.requester,
            request.approved,
            request.executed,
            request.justification
        );
    }

    /**
     * @notice Create parameter template
     * @param templateName Template name
     * @param targetType Target parameter type
     * @param targetStage Target governance stage
     */
    function createParameterTemplate(
        string memory templateName,
        ParameterType targetType,
        UniversalDAIO.GovernanceStage targetStage
    ) external onlyParameterAdmin {
        require(bytes(templateName).length > 0, "Template name required");
        require(!parameterTemplates[templateName].active, "Template already exists");

        ParameterTemplate storage template = parameterTemplates[templateName];
        template.templateName = templateName;
        template.targetType = targetType;
        template.targetStage = targetStage;
        template.active = true;
        template.deploymentCount = 0;

        templateNames.push(templateName);
    }

    /**
     * @notice Update global parameter settings
     */
    function updateGlobalSettings(
        uint256 _defaultModificationDelay,
        uint256 _emergencyModificationWindow,
        uint256 _maxParametersPerConfig,
        uint256 _syncTimeoutPeriod
    ) external onlyParameterAdmin {
        defaultModificationDelay = _defaultModificationDelay;
        emergencyModificationWindow = _emergencyModificationWindow;
        maxParametersPerConfig = _maxParametersPerConfig;
        syncTimeoutPeriod = _syncTimeoutPeriod;
    }

    /**
     * @notice Enable/disable global parameter lock
     * @param locked Whether parameters are globally locked
     */
    function setGlobalParameterLock(bool locked) external onlyParameterAdmin {
        globalParameterLock = locked;
    }

    /**
     * @notice Pause parameter system
     */
    function pauseParameterSystem() external onlyParameterAdmin {
        _pause();
    }

    /**
     * @notice Unpause parameter system
     */
    function unpauseParameterSystem() external onlyParameterAdmin {
        _unpause();
    }

    // Internal Functions

    /**
     * @notice Resolve parameter with inheritance
     */
    function _resolveParameter(uint256 configId, string memory key) internal view returns (Parameter memory) {
        ParameterHierarchy storage hierarchy = parameterHierarchies[configId];

        // Check if parameter exists in config-specific hierarchy
        if (hierarchy.overrides[key]) {
            return hierarchy.parameters[key];
        }

        // Fall back to global default
        if (bytes(globalDefaults[key].key).length > 0) {
            return globalDefaults[key];
        }

        revert("Parameter not found");
    }

    /**
     * @notice Check if parameter exists
     */
    function _parameterExists(uint256 configId, string memory key) internal view returns (bool) {
        ParameterHierarchy storage hierarchy = parameterHierarchies[configId];
        return hierarchy.overrides[key] || bytes(globalDefaults[key].key).length > 0;
    }

    /**
     * @notice Validate parameter value based on data type and constraints
     */
    function _validateParameterValue(
        ParameterDataType dataType,
        bytes memory value,
        uint256 minValue,
        uint256 maxValue
    ) internal pure returns (bool) {
        if (dataType == ParameterDataType.UINT256) {
            uint256 uintValue = abi.decode(value, (uint256));
            return uintValue >= minValue && uintValue <= maxValue;
        } else if (dataType == ParameterDataType.ADDRESS) {
            address addrValue = abi.decode(value, (address));
            return addrValue != address(0);
        } else if (dataType == ParameterDataType.BOOL) {
            // Bool values are always valid
            abi.decode(value, (bool));
            return true;
        }

        return true; // Other types assume valid for now
    }

    /**
     * @notice Check if address has modification authority
     */
    function _hasModificationAuthority(uint256 configId, string memory key, address account) internal view returns (bool) {
        UniversalDAIO.UniversalConfig memory config = universalDAIO.getConfiguration(configId);

        if (account == config.admin) return true;
        if (hasRole(PARAMETER_ADMIN_ROLE, account)) return true;

        // Check secondary admins
        for (uint i = 0; i < config.secondaryAdmins.length; i++) {
            if (config.secondaryAdmins[i] == account) return true;
        }

        return false;
    }

    /**
     * @notice Check if address has approval authority
     */
    function _hasApprovalAuthority(uint256 configId, string memory key, address account) internal view returns (bool) {
        return _hasModificationAuthority(configId, key, account);
    }

    /**
     * @notice Get modification delay based on parameter type
     */
    function _getModificationDelay(ParameterType paramType) internal view returns (uint256) {
        if (paramType == ParameterType.SECURITY || paramType == ParameterType.EVOLUTION) {
            return defaultModificationDelay * 2; // Double delay for critical parameters
        }
        return defaultModificationDelay;
    }

    /**
     * @notice Check if parameter is emergency modifiable
     */
    function _isEmergencyModifiable(ParameterType paramType, string memory key) internal pure returns (bool) {
        // Security and operational parameters can be emergency modified
        return paramType == ParameterType.SECURITY || paramType == ParameterType.OPERATIONAL;
    }

    /**
     * @notice Get required approvals for parameter modification
     */
    function _getRequiredApprovals(uint256 configId, string memory key) internal view returns (uint256) {
        Parameter memory param = parameterHierarchies[configId].parameters[key];

        if (param.paramType == ParameterType.EVOLUTION || param.paramType == ParameterType.SECURITY) {
            return 2; // Critical parameters require 2 approvals
        }

        return 1; // Standard parameters require 1 approval
    }

    /**
     * @notice Count current approvals for modification request
     */
    function _countApprovals(bytes32 requestId) internal view returns (uint256) {
        // This would iterate through approvals mapping
        // Simplified implementation for now
        return 1;
    }

    /**
     * @notice Execute parameter modification
     */
    function _executeParameterModification(bytes32 requestId) internal {
        ModificationRequest storage request = modificationRequests[requestId];

        Parameter storage param = parameterHierarchies[request.configId].parameters[request.parameterKey];
        bytes memory oldValue = param.value;

        param.value = request.newValue;
        param.lastModified = block.timestamp;
        param.lastModifiedBy = request.requester;

        request.executed = true;

        // Update parameter history
        parameterHistory[request.configId][request.parameterKey] = block.timestamp;

        emit ParameterModified(request.configId, request.parameterKey, oldValue, request.newValue, request.requester);

        // Initiate cross-chain sync if required
        if (param.crossChainSync) {
            _initiateCrossChainSync(request.configId, request.parameterKey);
        }
    }

    /**
     * @notice Initiate cross-chain parameter synchronization
     */
    function _initiateCrossChainSync(uint256 configId, string memory key) internal {
        bytes32 syncId = keccak256(abi.encode(configId, key, block.timestamp));

        CrossChainSync storage sync = crossChainSyncs[syncId];
        sync.configId = configId;
        sync.parameterKey = key;
        sync.syncInitiated = block.timestamp;
        sync.syncInProgress = true;
        sync.syncInitiator = msg.sender;

        // Get target chains (simplified)
        uint256[] memory targetChains = new uint256[](1);
        targetChains[0] = 1; // Ethereum as example

        sync.targetChains = targetChains;

        totalCrossChainSyncs++;

        emit CrossChainSyncInitiated(syncId, configId, key, targetChains, msg.sender);
    }

    /**
     * @notice Initialize global default parameters
     */
    function _initializeGlobalDefaults() internal {
        // Governance defaults
        globalDefaults["voting_threshold"] = Parameter({
            key: "voting_threshold",
            paramType: ParameterType.GOVERNANCE,
            dataType: ParameterDataType.UINT256,
            value: abi.encode(uint256(51)),
            minValue: 1,
            maxValue: 100,
            requiresEvolution: false,
            crossChainSync: true,
            emergencyModifiable: false,
            modificationDelay: defaultModificationDelay,
            lastModified: block.timestamp,
            lastModifiedBy: msg.sender,
            dependentChains: new uint256[](0),
            dependencies: new bytes32[](0),
            validationRules: ""
        });

        // Economic defaults
        globalDefaults["treasury_tithe"] = Parameter({
            key: "treasury_tithe",
            paramType: ParameterType.ECONOMIC,
            dataType: ParameterDataType.UINT256,
            value: abi.encode(uint256(15)),
            minValue: 0,
            maxValue: 50,
            requiresEvolution: true,
            crossChainSync: true,
            emergencyModifiable: false,
            modificationDelay: defaultModificationDelay * 2,
            lastModified: block.timestamp,
            lastModifiedBy: msg.sender,
            dependentChains: new uint256[](0),
            dependencies: new bytes32[](0),
            validationRules: ""
        });
    }

    /**
     * @notice Create default parameter templates
     */
    function _createDefaultTemplates() internal {
        // DictatorDAO template
        templateNames.push("DictatorDAO");
        parameterTemplates["DictatorDAO"].templateName = "DictatorDAO";
        parameterTemplates["DictatorDAO"].targetType = ParameterType.GOVERNANCE;
        parameterTemplates["DictatorDAO"].targetStage = UniversalDAIO.GovernanceStage.DICTATOR;
        parameterTemplates["DictatorDAO"].active = true;

        // MarriageDAO template
        templateNames.push("MarriageDAO");
        parameterTemplates["MarriageDAO"].templateName = "MarriageDAO";
        parameterTemplates["MarriageDAO"].targetType = ParameterType.GOVERNANCE;
        parameterTemplates["MarriageDAO"].targetStage = UniversalDAIO.GovernanceStage.MARRIAGE;
        parameterTemplates["MarriageDAO"].active = true;

        // TriumvirateDAO template
        templateNames.push("TriumvirateDAO");
        parameterTemplates["TriumvirateDAO"].templateName = "TriumvirateDAO";
        parameterTemplates["TriumvirateDAO"].targetType = ParameterType.GOVERNANCE;
        parameterTemplates["TriumvirateDAO"].targetStage = UniversalDAIO.GovernanceStage.TRIUMVIRATE;
        parameterTemplates["TriumvirateDAO"].active = true;
    }
}