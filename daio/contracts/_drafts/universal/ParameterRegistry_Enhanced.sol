// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./UniversalDAIO.sol";
import "../daio/governance/ExecutiveGovernance.sol";
import "../daio/constitution/DAIO_Constitution_Enhanced.sol";
import "../deployment/ProductionDeploymentFramework.sol";

/**
 * @title ParameterRegistry_Enhanced
 * @notice Enhanced universal parameter configuration with CEO + Seven Soldiers integration
 * @dev Production-ready parameter management with executive approval and constitutional validation
 *
 * Features:
 * - CEO + Seven Soldiers approval for critical parameters
 * - Constitutional constraint validation
 * - Production monitoring and alerting
 * - Corporate governance parameter templates
 * - AI agent parameter management
 * - Performance metrics and optimization
 * - Emergency response procedures
 * - Multi-chain parameter coordination
 * - Automated compliance reporting
 *
 * Parameter Categories:
 * - GOVERNANCE: Voting thresholds, executive powers, consensus rules
 * - ECONOMIC: Treasury rates, fee structures, allocation limits
 * - SECURITY: Emergency controls, access permissions, circuit breakers
 * - OPERATIONAL: System timeouts, automation settings, performance tuning
 * - EXECUTIVE: CEO + Seven Soldiers specific parameters
 * - CONSTITUTIONAL: Core constitutional constraint parameters
 * - CORPORATE: Fortune 500 corporate governance parameters
 * - AI_INTEGRATION: AI agent voting weights and capabilities
 *
 * @author DAIO Development Team
 */
contract ParameterRegistry_Enhanced is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant PARAMETER_ADMIN_ROLE = keccak256("PARAMETER_ADMIN_ROLE");
    bytes32 public constant PARAMETER_VALIDATOR_ROLE = keccak256("PARAMETER_VALIDATOR_ROLE");
    bytes32 public constant EXECUTIVE_APPROVAL_ROLE = keccak256("EXECUTIVE_APPROVAL_ROLE");
    bytes32 public constant CONSTITUTIONAL_REVIEWER_ROLE = keccak256("CONSTITUTIONAL_REVIEWER_ROLE");
    bytes32 public constant EMERGENCY_OVERRIDE_ROLE = keccak256("EMERGENCY_OVERRIDE_ROLE");
    bytes32 public constant PRODUCTION_MONITOR_ROLE = keccak256("PRODUCTION_MONITOR_ROLE");
    bytes32 public constant AI_PARAMETER_MANAGER_ROLE = keccak256("AI_PARAMETER_MANAGER_ROLE");

    // =============================================================
    //                         INTERFACES
    // =============================================================

    UniversalDAIO public immutable universalDAIO;
    ExecutiveGovernance public immutable executiveGovernance;
    DAIO_Constitution_Enhanced public immutable constitution;
    ProductionDeploymentFramework public immutable deploymentFramework;

    // =============================================================
    //                         ENHANCED TYPES
    // =============================================================

    enum ParameterType {
        GOVERNANCE,         // Standard governance parameters
        ECONOMIC,           // Treasury and financial parameters
        OPERATIONAL,        // System operation parameters
        SECURITY,           // Security and emergency controls
        EVOLUTION,          // Governance evolution parameters
        MULTICHAIN,         // Cross-chain coordination
        AI_INTEGRATION,     // AI agent management
        EXECUTIVE,          // CEO + Seven Soldiers specific
        CONSTITUTIONAL,     // Core constitutional constraints
        CORPORATE,          // Corporate governance specific
        PERFORMANCE,        // System performance tuning
        COMPLIANCE         // Regulatory compliance parameters
    }

    enum ParameterDataType {
        UINT256,
        UINT256_ARRAY,
        ADDRESS,
        ADDRESS_ARRAY,
        BYTES32,
        BYTES32_ARRAY,
        BOOL,
        STRING,
        BYTES,
        EXECUTIVE_ROLE,     // Special type for executive role assignments
        CONSTITUTIONAL_LIMIT // Special type for constitutional constraints
    }

    enum ParameterCriticality {
        LOW,                // Standard parameters
        MEDIUM,             // Important but not critical
        HIGH,               // Critical system parameters
        CONSTITUTIONAL,     // Constitutional constraint parameters
        EXECUTIVE,          // Requires executive approval
        EMERGENCY_ONLY     // Only modifiable in emergencies
    }

    enum ApprovalStatus {
        PENDING,
        EXECUTIVE_REVIEW,
        CONSTITUTIONAL_REVIEW,
        APPROVED,
        REJECTED,
        EXECUTED,
        EXPIRED
    }

    // =============================================================
    //                      ENHANCED STRUCTS
    // =============================================================

    struct EnhancedParameter {
        string key;
        ParameterType paramType;
        ParameterDataType dataType;
        ParameterCriticality criticality;
        bytes value;
        uint256 minValue;
        uint256 maxValue;
        bool requiresExecutiveApproval;
        bool requiresConstitutionalValidation;
        bool crossChainSync;
        bool emergencyModifiable;
        uint256 modificationDelay;
        uint256 lastModified;
        address lastModifiedBy;
        uint256[] dependentChains;
        bytes32[] dependencies;
        bytes validationRules;
        string description;
        uint256 performanceImpact;  // 0-100 scale
        bool productionCritical;    // Affects production system
        uint256 complianceLevel;    // Regulatory compliance requirement
    }

    struct ExecutiveApproval {
        bytes32 requestId;
        uint256 configId;
        string parameterKey;
        bytes proposedValue;
        mapping(address => bool) executiveVotes;
        mapping(address => string) voteReasons;
        uint256 approvalsRequired;
        uint256 approvalsReceived;
        uint256 rejectionsReceived;
        uint256 votingDeadline;
        bool ceoApproval;
        bool cisoApproval;    // Security parameters require CISO
        bool croApproval;     // Risk parameters require CRO
        bool cfoApproval;     // Economic parameters require CFO
        ApprovalStatus status;
        address initiator;
        string justification;
    }

    struct ConstitutionalValidation {
        bytes32 requestId;
        bool validationRequired;
        bool validationCompleted;
        bool validationPassed;
        string[] violationReasons;
        uint256 validationStarted;
        uint256 validationCompleted;
        address validator;
        bytes32 complianceHash;
        uint256 constitutionalImpactScore;
    }

    struct ParameterTemplate {
        string templateName;
        string description;
        ParameterType primaryType;
        UniversalDAIO.GovernanceStage targetStage;
        string[] corporateIndustries;   // Applicable industries
        uint256 complianceLevel;        // Required compliance level
        mapping(string => EnhancedParameter) parameters;
        string[] parameterKeys;
        bool active;
        uint256 deploymentCount;
        uint256 productionRating;       // 1-10 production readiness
        address templateCreator;
        uint256 createdAt;
    }

    struct PerformanceMetrics {
        uint256 totalParameters;
        uint256 executiveApprovals;
        uint256 constitutionalValidations;
        uint256 emergencyOverrides;
        uint256 crossChainSyncs;
        uint256 averageApprovalTime;
        uint256 parameterViolations;
        mapping(ParameterType => uint256) typeUsage;
        mapping(ParameterCriticality => uint256) criticalityDistribution;
        uint256 lastMetricsUpdate;
    }

    struct ProductionAlert {
        uint256 alertId;
        string parameterKey;
        string alertType;           // VIOLATION, PERFORMANCE, SECURITY, COMPLIANCE
        string description;
        uint256 severity;           // 1-10 scale
        bool resolved;
        uint256 timestamp;
        address alertedBy;
        string resolution;
    }

    // =============================================================
    //                         STORAGE
    // =============================================================

    // Enhanced parameter storage
    mapping(uint256 => mapping(string => EnhancedParameter)) public enhancedParameters;
    mapping(bytes32 => ExecutiveApproval) public executiveApprovals;
    mapping(bytes32 => ConstitutionalValidation) public constitutionalValidations;
    mapping(string => ParameterTemplate) public parameterTemplates;
    mapping(string => EnhancedParameter) public globalDefaults;

    // Production monitoring
    PerformanceMetrics public performanceMetrics;
    mapping(uint256 => ProductionAlert) public productionAlerts;
    uint256 public alertCounter;

    // Executive role mappings for parameter approval
    mapping(string => bool) public requiresCISOApproval;  // Security parameters
    mapping(string => bool) public requiresCROApproval;   // Risk parameters
    mapping(string => bool) public requiresCFOApproval;   // Economic parameters

    // Corporate governance templates
    string[] public corporateTemplates;
    mapping(string => string[]) public industryTemplates;  // Industry => template names

    // Performance optimization
    mapping(string => uint256) public parameterAccessCount;
    mapping(string => uint256) public lastParameterAccess;
    mapping(uint256 => bytes32) public configParameterHashes;

    // Global settings
    uint256 public defaultExecutiveVotingPeriod = 3 days;
    uint256 public constitutionalReviewPeriod = 2 days;
    uint256 public emergencyModificationWindow = 6 hours;
    uint256 public maxParametersPerConfig = 2000;
    uint256 public productionAlertThreshold = 7;  // Severity 7+ triggers immediate alert

    // =============================================================
    //                         EVENTS
    // =============================================================

    event EnhancedParameterConfigured(
        uint256 indexed configId,
        string indexed parameterKey,
        ParameterType paramType,
        ParameterCriticality criticality,
        bytes value,
        address indexed configuredBy
    );

    event ExecutiveApprovalRequested(
        bytes32 indexed requestId,
        uint256 indexed configId,
        string indexed parameterKey,
        uint256 approvalsRequired,
        uint256 votingDeadline,
        address initiator
    );

    event ExecutiveVoteCast(
        bytes32 indexed requestId,
        address indexed executive,
        bool approval,
        string reason
    );

    event ConstitutionalValidationInitiated(
        bytes32 indexed requestId,
        string indexed parameterKey,
        uint256 constitutionalImpactScore
    );

    event ConstitutionalValidationCompleted(
        bytes32 indexed requestId,
        bool validationPassed,
        string[] violations
    );

    event CorporateTemplateDeployed(
        string indexed templateName,
        uint256 indexed configId,
        string industry,
        uint256 parameterCount
    );

    event PerformanceMetricsUpdated(
        uint256 totalParameters,
        uint256 averageApprovalTime,
        uint256 violationCount
    );

    event ProductionAlertTriggered(
        uint256 indexed alertId,
        string indexed parameterKey,
        string alertType,
        uint256 severity
    );

    event AIParameterManagementEnabled(
        uint256 indexed configId,
        address aiAgent,
        string[] managedParameters
    );

    event EmergencyParameterLockdown(
        uint256 indexed configId,
        string reason,
        address initiatedBy
    );

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor(
        address _universalDAIO,
        address _executiveGovernance,
        address _constitution,
        address _deploymentFramework
    ) {
        require(_universalDAIO != address(0), "Invalid UniversalDAIO");
        require(_executiveGovernance != address(0), "Invalid ExecutiveGovernance");
        require(_constitution != address(0), "Invalid Constitution");
        require(_deploymentFramework != address(0), "Invalid DeploymentFramework");

        universalDAIO = UniversalDAIO(_universalDAIO);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);
        constitution = DAIO_Constitution_Enhanced(_constitution);
        deploymentFramework = ProductionDeploymentFramework(_deploymentFramework);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PARAMETER_ADMIN_ROLE, msg.sender);
        _grantRole(PARAMETER_VALIDATOR_ROLE, msg.sender);
        _grantRole(EXECUTIVE_APPROVAL_ROLE, msg.sender);
        _grantRole(CONSTITUTIONAL_REVIEWER_ROLE, msg.sender);
        _grantRole(EMERGENCY_OVERRIDE_ROLE, msg.sender);
        _grantRole(PRODUCTION_MONITOR_ROLE, msg.sender);
        _grantRole(AI_PARAMETER_MANAGER_ROLE, msg.sender);

        _initializeEnhancedDefaults();
        _initializeCorporateTemplates();
        _initializeExecutiveParameterMappings();
    }

    // =============================================================
    //                   ENHANCED CONFIGURATION
    // =============================================================

    /**
     * @notice Configure enhanced parameter with executive and constitutional validation
     */
    function configureEnhancedParameter(
        uint256 configId,
        string memory key,
        ParameterType paramType,
        ParameterDataType dataType,
        ParameterCriticality criticality,
        bytes memory value,
        uint256 minValue,
        uint256 maxValue,
        string memory description,
        bool productionCritical
    ) external validConfig(configId) onlyRole(PARAMETER_ADMIN_ROLE) {
        require(bytes(key).length > 0, "Parameter key required");
        require(value.length > 0, "Parameter value required");
        require(bytes(description).length > 0, "Description required");

        // Validate parameter value
        require(_validateEnhancedParameterValue(dataType, value, minValue, maxValue), "Invalid parameter value");

        EnhancedParameter storage param = enhancedParameters[configId][key];
        param.key = key;
        param.paramType = paramType;
        param.dataType = dataType;
        param.criticality = criticality;
        param.value = value;
        param.minValue = minValue;
        param.maxValue = maxValue;
        param.description = description;
        param.productionCritical = productionCritical;
        param.lastModified = block.timestamp;
        param.lastModifiedBy = msg.sender;

        // Set approval requirements based on criticality and type
        param.requiresExecutiveApproval = _requiresExecutiveApproval(paramType, criticality);
        param.requiresConstitutionalValidation = _requiresConstitutionalValidation(paramType, criticality);
        param.emergencyModifiable = _isEmergencyModifiable(paramType, criticality);
        param.modificationDelay = _getModificationDelay(paramType, criticality);
        param.performanceImpact = _calculatePerformanceImpact(paramType, productionCritical);
        param.complianceLevel = _getComplianceLevel(paramType, criticality);

        // Update metrics
        performanceMetrics.totalParameters++;
        performanceMetrics.typeUsage[paramType]++;
        performanceMetrics.criticalityDistribution[criticality]++;

        emit EnhancedParameterConfigured(configId, key, paramType, criticality, value, msg.sender);

        // Check for production alerts
        _checkProductionAlerts(configId, key, param);
    }

    /**
     * @notice Request parameter modification with executive approval workflow
     */
    function requestParameterModificationWithApproval(
        uint256 configId,
        string memory key,
        bytes memory newValue,
        string memory justification
    ) external validConfig(configId) returns (bytes32 requestId) {
        EnhancedParameter storage param = enhancedParameters[configId][key];
        require(bytes(param.key).length > 0, "Parameter does not exist");
        require(bytes(justification).length > 0, "Justification required");

        // Validate new value
        require(_validateEnhancedParameterValue(param.dataType, newValue, param.minValue, param.maxValue), "Invalid value");

        requestId = keccak256(abi.encode(configId, key, newValue, block.timestamp, msg.sender));

        // Create executive approval if required
        if (param.requiresExecutiveApproval) {
            _initiateExecutiveApproval(requestId, configId, key, newValue, justification);
        }

        // Create constitutional validation if required
        if (param.requiresConstitutionalValidation) {
            _initiateConstitutionalValidation(requestId, key, newValue);
        }

        return requestId;
    }

    /**
     * @notice Cast executive vote on parameter modification
     */
    function castExecutiveVote(
        bytes32 requestId,
        bool approval,
        string memory reason
    ) external {
        require(
            executiveGovernance.hasExecutiveApproval(msg.sender) ||
            executiveGovernance.isCEO(msg.sender),
            "Not an executive"
        );

        ExecutiveApproval storage execApproval = executiveApprovals[requestId];
        require(block.timestamp <= execApproval.votingDeadline, "Voting period ended");
        require(!execApproval.executiveVotes[msg.sender], "Already voted");

        execApproval.executiveVotes[msg.sender] = true;
        execApproval.voteReasons[msg.sender] = reason;

        if (approval) {
            execApproval.approvalsReceived++;

            // Track specific executive approvals
            if (executiveGovernance.isCEO(msg.sender)) {
                execApproval.ceoApproval = true;
            } else if (executiveGovernance.isCISO(msg.sender)) {
                execApproval.cisoApproval = true;
            } else if (executiveGovernance.isCRO(msg.sender)) {
                execApproval.croApproval = true;
            } else if (executiveGovernance.isCFO(msg.sender)) {
                execApproval.cfoApproval = true;
            }
        } else {
            execApproval.rejectionsReceived++;
        }

        emit ExecutiveVoteCast(requestId, msg.sender, approval, reason);

        // Update approval status
        _updateApprovalStatus(requestId);
    }

    /**
     * @notice Apply corporate governance template
     */
    function applyCorporateTemplate(
        uint256 configId,
        string memory templateName,
        string memory industry,
        bool overrideExisting
    ) external validConfig(configId) onlyRole(PARAMETER_ADMIN_ROLE) {
        ParameterTemplate storage template = parameterTemplates[templateName];
        require(template.active, "Template not active");

        // Validate industry compatibility
        bool industryMatch = false;
        for (uint256 i = 0; i < template.corporateIndustries.length; i++) {
            if (keccak256(bytes(template.corporateIndustries[i])) == keccak256(bytes(industry))) {
                industryMatch = true;
                break;
            }
        }
        require(industryMatch || template.corporateIndustries.length == 0, "Industry not compatible");

        // Apply template parameters
        uint256 appliedCount = 0;
        for (uint256 i = 0; i < template.parameterKeys.length; i++) {
            string memory key = template.parameterKeys[i];

            if (overrideExisting || bytes(enhancedParameters[configId][key].key).length == 0) {
                // Copy parameter from template
                EnhancedParameter storage templateParam = template.parameters[key];
                enhancedParameters[configId][key] = templateParam;
                enhancedParameters[configId][key].lastModified = block.timestamp;
                enhancedParameters[configId][key].lastModifiedBy = msg.sender;
                appliedCount++;
            }
        }

        template.deploymentCount++;
        emit CorporateTemplateDeployed(templateName, configId, industry, appliedCount);
    }

    /**
     * @notice Enable AI parameter management for configuration
     */
    function enableAIParameterManagement(
        uint256 configId,
        address aiAgent,
        string[] memory managedParameterKeys,
        uint256 aiAuthority  // 1-100 scale
    ) external validConfig(configId) onlyRole(AI_PARAMETER_MANAGER_ROLE) {
        require(aiAgent != address(0), "Invalid AI agent");
        require(aiAuthority > 0 && aiAuthority <= 100, "Invalid authority level");
        require(managedParameterKeys.length > 0, "No parameters specified");

        // Validate all parameters exist and are AI-manageable
        for (uint256 i = 0; i < managedParameterKeys.length; i++) {
            string memory key = managedParameterKeys[i];
            EnhancedParameter storage param = enhancedParameters[configId][key];
            require(bytes(param.key).length > 0, "Parameter does not exist");
            require(param.paramType == ParameterType.AI_INTEGRATION || param.paramType == ParameterType.PERFORMANCE, "Parameter not AI-manageable");
        }

        emit AIParameterManagementEnabled(configId, aiAgent, managedParameterKeys);
    }

    /**
     * @notice Emergency parameter lockdown for security
     */
    function emergencyParameterLockdown(
        uint256 configId,
        string memory reason
    ) external {
        require(
            executiveGovernance.isCEO(msg.sender) ||
            hasRole(EMERGENCY_OVERRIDE_ROLE, msg.sender),
            "Not authorized for emergency lockdown"
        );

        // Lock all non-emergency parameters for this configuration
        // Implementation would iterate through parameters and set emergency lock

        emit EmergencyParameterLockdown(configId, reason, msg.sender);
    }

    // =============================================================
    //                    VIEW FUNCTIONS
    // =============================================================

    /**
     * @notice Get enhanced parameter with full details
     */
    function getEnhancedParameter(uint256 configId, string memory key) external view validConfig(configId) returns (EnhancedParameter memory) {
        return _resolveEnhancedParameter(configId, key);
    }

    /**
     * @notice Get executive approval status
     */
    function getExecutiveApprovalStatus(bytes32 requestId) external view returns (
        ApprovalStatus status,
        uint256 approvalsReceived,
        uint256 approvalsRequired,
        uint256 votingDeadline,
        bool ceoApproval
    ) {
        ExecutiveApproval storage approval = executiveApprovals[requestId];
        return (
            approval.status,
            approval.approvalsReceived,
            approval.approvalsRequired,
            approval.votingDeadline,
            approval.ceoApproval
        );
    }

    /**
     * @notice Get performance metrics
     */
    function getPerformanceMetrics() external view returns (
        uint256 totalParameters,
        uint256 executiveApprovals,
        uint256 constitutionalValidations,
        uint256 emergencyOverrides,
        uint256 averageApprovalTime
    ) {
        return (
            performanceMetrics.totalParameters,
            performanceMetrics.executiveApprovals,
            performanceMetrics.constitutionalValidations,
            performanceMetrics.emergencyOverrides,
            performanceMetrics.averageApprovalTime
        );
    }

    /**
     * @notice Get production alerts
     */
    function getProductionAlerts(uint256 severity) external view returns (ProductionAlert[] memory alerts) {
        uint256 count = 0;

        // Count alerts with severity >= threshold
        for (uint256 i = 1; i <= alertCounter; i++) {
            if (productionAlerts[i].severity >= severity && !productionAlerts[i].resolved) {
                count++;
            }
        }

        // Populate alerts array
        alerts = new ProductionAlert[](count);
        uint256 index = 0;
        for (uint256 i = 1; i <= alertCounter; i++) {
            if (productionAlerts[i].severity >= severity && !productionAlerts[i].resolved) {
                alerts[index] = productionAlerts[i];
                index++;
            }
        }

        return alerts;
    }

    /**
     * @notice Get corporate templates for industry
     */
    function getCorporateTemplatesForIndustry(string memory industry) external view returns (string[] memory) {
        return industryTemplates[industry];
    }

    // =============================================================
    //                   INTERNAL FUNCTIONS
    // =============================================================

    /**
     * @notice Resolve enhanced parameter with inheritance
     */
    function _resolveEnhancedParameter(uint256 configId, string memory key) internal view returns (EnhancedParameter memory) {
        if (bytes(enhancedParameters[configId][key].key).length > 0) {
            return enhancedParameters[configId][key];
        }

        if (bytes(globalDefaults[key].key).length > 0) {
            return globalDefaults[key];
        }

        revert("Parameter not found");
    }

    /**
     * @notice Validate enhanced parameter value
     */
    function _validateEnhancedParameterValue(
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
            abi.decode(value, (bool));
            return true;
        } else if (dataType == ParameterDataType.CONSTITUTIONAL_LIMIT) {
            uint256 limitValue = abi.decode(value, (uint256));
            // Constitutional limits have specific constraints (e.g., tithe 0-30%, diversification 5-50%)
            return limitValue >= 0 && limitValue <= 50;
        }

        return true;
    }

    /**
     * @notice Check if parameter requires executive approval
     */
    function _requiresExecutiveApproval(ParameterType paramType, ParameterCriticality criticality) internal pure returns (bool) {
        return criticality == ParameterCriticality.HIGH ||
               criticality == ParameterCriticality.CONSTITUTIONAL ||
               criticality == ParameterCriticality.EXECUTIVE ||
               paramType == ParameterType.EXECUTIVE ||
               paramType == ParameterType.CONSTITUTIONAL;
    }

    /**
     * @notice Check if parameter requires constitutional validation
     */
    function _requiresConstitutionalValidation(ParameterType paramType, ParameterCriticality criticality) internal pure returns (bool) {
        return paramType == ParameterType.CONSTITUTIONAL ||
               paramType == ParameterType.ECONOMIC ||
               criticality == ParameterCriticality.CONSTITUTIONAL;
    }

    /**
     * @notice Check if parameter is emergency modifiable
     */
    function _isEmergencyModifiable(ParameterType paramType, ParameterCriticality criticality) internal pure returns (bool) {
        return paramType == ParameterType.SECURITY ||
               paramType == ParameterType.OPERATIONAL ||
               criticality == ParameterCriticality.LOW ||
               criticality == ParameterCriticality.MEDIUM;
    }

    /**
     * @notice Get modification delay based on type and criticality
     */
    function _getModificationDelay(ParameterType paramType, ParameterCriticality criticality) internal view returns (uint256) {
        if (criticality == ParameterCriticality.CONSTITUTIONAL) {
            return 7 days;  // Constitutional changes need extended delay
        } else if (criticality == ParameterCriticality.HIGH || criticality == ParameterCriticality.EXECUTIVE) {
            return 3 days;  // High criticality needs standard executive delay
        } else if (paramType == ParameterType.SECURITY) {
            return 1 days;  // Security changes need quick approval
        }
        return 6 hours; // Low criticality parameters
    }

    /**
     * @notice Calculate performance impact score
     */
    function _calculatePerformanceImpact(ParameterType paramType, bool productionCritical) internal pure returns (uint256) {
        uint256 baseImpact = 30; // Base 30% impact

        if (productionCritical) {
            baseImpact += 40; // +40% for production critical
        }

        if (paramType == ParameterType.SECURITY || paramType == ParameterType.CONSTITUTIONAL) {
            baseImpact += 30; // +30% for critical types
        }

        return baseImpact > 100 ? 100 : baseImpact;
    }

    /**
     * @notice Get compliance level requirement
     */
    function _getComplianceLevel(ParameterType paramType, ParameterCriticality criticality) internal pure returns (uint256) {
        if (paramType == ParameterType.CORPORATE) return 9; // High compliance for corporate
        if (paramType == ParameterType.CONSTITUTIONAL) return 10; // Maximum for constitutional
        if (criticality == ParameterCriticality.HIGH) return 7;
        if (criticality == ParameterCriticality.EXECUTIVE) return 8;
        return 5; // Standard compliance level
    }

    /**
     * @notice Initiate executive approval process
     */
    function _initiateExecutiveApproval(
        bytes32 requestId,
        uint256 configId,
        string memory key,
        bytes memory newValue,
        string memory justification
    ) internal {
        ExecutiveApproval storage approval = executiveApprovals[requestId];
        approval.requestId = requestId;
        approval.configId = configId;
        approval.parameterKey = key;
        approval.proposedValue = newValue;
        approval.votingDeadline = block.timestamp + defaultExecutiveVotingPeriod;
        approval.status = ApprovalStatus.EXECUTIVE_REVIEW;
        approval.initiator = msg.sender;
        approval.justification = justification;

        // Determine required approvals based on parameter type
        EnhancedParameter storage param = enhancedParameters[configId][key];
        uint256 requiredApprovals = 2; // Default 2 of 8 executives

        if (param.paramType == ParameterType.CONSTITUTIONAL) {
            requiredApprovals = 6; // 3/4 majority for constitutional
        } else if (param.paramType == ParameterType.SECURITY) {
            requiredApprovals = 3; // Security needs more approvals
        } else if (param.criticality == ParameterCriticality.CONSTITUTIONAL) {
            requiredApprovals = 6; // Constitutional criticality
        }

        approval.approvalsRequired = requiredApprovals;

        emit ExecutiveApprovalRequested(requestId, configId, key, requiredApprovals, approval.votingDeadline, msg.sender);
    }

    /**
     * @notice Initiate constitutional validation
     */
    function _initiateConstitutionalValidation(
        bytes32 requestId,
        string memory key,
        bytes memory newValue
    ) internal {
        ConstitutionalValidation storage validation = constitutionalValidations[requestId];
        validation.requestId = requestId;
        validation.validationRequired = true;
        validation.validationStarted = block.timestamp;
        validation.validator = address(constitution);
        validation.constitutionalImpactScore = 75; // Default high impact score

        emit ConstitutionalValidationInitiated(requestId, key, validation.constitutionalImpactScore);
    }

    /**
     * @notice Update approval status based on votes
     */
    function _updateApprovalStatus(bytes32 requestId) internal {
        ExecutiveApproval storage approval = executiveApprovals[requestId];

        if (approval.approvalsReceived >= approval.approvalsRequired) {
            approval.status = ApprovalStatus.APPROVED;
        } else if (approval.rejectionsReceived > (8 - approval.approvalsRequired)) {
            approval.status = ApprovalStatus.REJECTED;
        } else if (block.timestamp > approval.votingDeadline) {
            approval.status = ApprovalStatus.EXPIRED;
        }
    }

    /**
     * @notice Check for production alerts
     */
    function _checkProductionAlerts(uint256 configId, string memory key, EnhancedParameter memory param) internal {
        if (param.productionCritical && param.performanceImpact >= 70) {
            alertCounter++;
            ProductionAlert storage alert = productionAlerts[alertCounter];
            alert.alertId = alertCounter;
            alert.parameterKey = key;
            alert.alertType = "PERFORMANCE";
            alert.description = "High performance impact parameter modified";
            alert.severity = 8;
            alert.resolved = false;
            alert.timestamp = block.timestamp;
            alert.alertedBy = msg.sender;

            emit ProductionAlertTriggered(alertCounter, key, "PERFORMANCE", 8);
        }
    }

    /**
     * @notice Initialize enhanced defaults
     */
    function _initializeEnhancedDefaults() internal {
        // CEO Emergency Power Timeout
        globalDefaults["ceo_emergency_timeout"] = EnhancedParameter({
            key: "ceo_emergency_timeout",
            paramType: ParameterType.EXECUTIVE,
            dataType: ParameterDataType.UINT256,
            criticality: ParameterCriticality.EXECUTIVE,
            value: abi.encode(uint256(7 days)),
            minValue: 1 days,
            maxValue: 30 days,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true,
            crossChainSync: true,
            emergencyModifiable: false,
            modificationDelay: 3 days,
            lastModified: block.timestamp,
            lastModifiedBy: msg.sender,
            dependentChains: new uint256[](0),
            dependencies: new bytes32[](0),
            validationRules: "",
            description: "Maximum duration of CEO emergency powers",
            performanceImpact: 90,
            productionCritical: true,
            complianceLevel: 10
        });

        // Treasury Tithe Rate
        globalDefaults["treasury_tithe_rate"] = EnhancedParameter({
            key: "treasury_tithe_rate",
            paramType: ParameterType.CONSTITUTIONAL,
            dataType: ParameterDataType.CONSTITUTIONAL_LIMIT,
            criticality: ParameterCriticality.CONSTITUTIONAL,
            value: abi.encode(uint256(15)),
            minValue: 1,
            maxValue: 30,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true,
            crossChainSync: true,
            emergencyModifiable: false,
            modificationDelay: 7 days,
            lastModified: block.timestamp,
            lastModifiedBy: msg.sender,
            dependentChains: new uint256[](0),
            dependencies: new bytes32[](0),
            validationRules: "",
            description: "Constitutional treasury tithe rate percentage",
            performanceImpact: 95,
            productionCritical: true,
            complianceLevel: 10
        });
    }

    /**
     * @notice Initialize corporate templates
     */
    function _initializeCorporateTemplates() internal {
        corporateTemplates.push("TechCorpDAO");
        corporateTemplates.push("FinancialServicesDAO");
        corporateTemplates.push("ManufacturingDAO");

        industryTemplates["Technology"].push("TechCorpDAO");
        industryTemplates["Financial Services"].push("FinancialServicesDAO");
        industryTemplates["Manufacturing"].push("ManufacturingDAO");
    }

    /**
     * @notice Initialize executive parameter mappings
     */
    function _initializeExecutiveParameterMappings() internal {
        // Parameters requiring CISO approval
        requiresCISOApproval["security_timeout"] = true;
        requiresCISOApproval["emergency_controls"] = true;
        requiresCISOApproval["access_controls"] = true;

        // Parameters requiring CRO approval
        requiresCROApproval["risk_thresholds"] = true;
        requiresCROApproval["circuit_breaker_limits"] = true;
        requiresCROApproval["volatility_controls"] = true;

        // Parameters requiring CFO approval
        requiresCFOApproval["treasury_tithe_rate"] = true;
        requiresCFOApproval["allocation_limits"] = true;
        requiresCFOApproval["fee_structures"] = true;
    }

    // =============================================================
    //                       MODIFIERS
    // =============================================================

    modifier validConfig(uint256 configId) {
        require(configId > 0, "Invalid config ID");
        _;
    }

    modifier onlyExecutive() {
        require(
            executiveGovernance.hasExecutiveApproval(msg.sender) ||
            executiveGovernance.isCEO(msg.sender),
            "Not an executive"
        );
        _;
    }
}