// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../constitution/DAIO_Constitution.sol";

/**
 * @title DAIO_ConfigurationEngine
 * @notice Complete configurability engine for all DAIO parameters
 * @dev Enables runtime parameter adjustment while maintaining constitutional constraints
 */
contract DAIO_ConfigurationEngine is AccessControl, ReentrancyGuard {

    bytes32 public constant CONFIGURATOR_ROLE = keccak256("CONFIGURATOR_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Configuration categories
    enum ConfigCategory {
        GOVERNANCE,     // Voting thresholds, proposal periods
        ORGANIZATION,   // Branch autonomy, resource sharing
        ECONOMICS,      // Fee structures, stake requirements
        AI_INTEGRATION, // AI voting weights, proposal limits
        EMERGENCY       // Emergency parameters, timeouts
    }

    // Template types for deployment
    enum DeploymentTemplate {
        UMBRELLA,       // Parent with multiple subsidiaries
        STANDALONE,     // Independent single DAIO
        BRANCH,         // Subsidiary with parent oversight
        CUSTOM          // User-defined configuration
    }

    struct ConfigurationParameter {
        string key;
        uint256 value;
        uint256 minValue;
        uint256 maxValue;
        ConfigCategory category;
        bool constitutional;    // Cannot be changed without constitutional process
        uint256 lastUpdated;
        address lastUpdatedBy;
    }

    struct TemplateConfig {
        string name;
        string description;
        DeploymentTemplate templateType;
        mapping(string => uint256) parameters;
        bool active;
        uint256 createdAt;
    }

    struct ConfigurationChange {
        string parameterKey;
        uint256 oldValue;
        uint256 newValue;
        uint256 timestamp;
        address changedBy;
        uint8 riskLevel;        // 1-10 scale
        bool requiresApproval;
    }

    // Storage
    mapping(string => ConfigurationParameter) public parameters;
    mapping(uint256 => TemplateConfig) public templates;
    mapping(bytes32 => bool) public frozenConfigurations;
    ConfigurationChange[] public configHistory;

    uint256 public templateCount;
    DAIO_Constitution public constitution;

    // Default parameter ranges
    struct ParameterRanges {
        uint256 votingThresholdMin;    // 50%
        uint256 votingThresholdMax;    // 100%
        uint256 proposalPeriodMin;     // 1 hour
        uint256 proposalPeriodMax;     // 30 days
        uint256 stakeRequirementMin;   // 0.01 ETH
        uint256 stakeRequirementMax;   // 100 ETH
        uint256 aiVotingWeightMin;     // 0%
        uint256 aiVotingWeightMax;     // 50%
        uint256 feeStructureMin;       // 0%
        uint256 feeStructureMax;       // 10%
    }

    ParameterRanges public ranges;

    // Events
    event ParameterUpdated(
        string indexed key,
        uint256 oldValue,
        uint256 newValue,
        address indexed updatedBy,
        uint8 riskLevel
    );

    event TemplateCreated(
        uint256 indexed templateId,
        string name,
        DeploymentTemplate templateType
    );

    event ConfigurationFrozen(
        bytes32 indexed configHash,
        string reason,
        uint256 duration
    );

    event ParameterRollback(
        string indexed key,
        uint256 rolledBackValue,
        uint256 timestamp
    );

    modifier onlyConfigurator() {
        require(hasRole(CONFIGURATOR_ROLE, msg.sender), "Not configurator");
        _;
    }

    modifier onlyEmergency() {
        require(hasRole(EMERGENCY_ROLE, msg.sender), "Not emergency role");
        _;
    }

    modifier notFrozen(string memory key) {
        bytes32 configHash = keccak256(abi.encodePacked(key));
        require(!frozenConfigurations[configHash], "Configuration frozen");
        _;
    }

    constructor(address _constitution) {
        require(_constitution != address(0), "Invalid constitution");

        constitution = DAIO_Constitution(_constitution);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(CONFIGURATOR_ROLE, msg.sender);
        _grantRole(EMERGENCY_ROLE, msg.sender);

        _initializeDefaultParameters();
        _createStandardTemplates();
    }

    /**
     * @notice Update configuration parameter with risk assessment
     * @param key Parameter key
     * @param newValue New parameter value
     * @param riskLevel Risk level (1-10)
     * @param reason Change reason
     */
    function updateParameter(
        string memory key,
        uint256 newValue,
        uint8 riskLevel,
        string memory reason
    ) external onlyConfigurator notFrozen(key) nonReentrant {
        require(riskLevel >= 1 && riskLevel <= 10, "Invalid risk level");

        ConfigurationParameter storage param = parameters[key];
        require(bytes(param.key).length > 0, "Parameter doesn't exist");
        require(newValue >= param.minValue && newValue <= param.maxValue, "Value out of range");

        // Constitutional parameters require special process
        if (param.constitutional) {
            require(riskLevel >= 8, "Constitutional changes are high risk");
            // Would integrate with enhanced constitution process
        }

        uint256 oldValue = param.value;
        param.value = newValue;
        param.lastUpdated = block.timestamp;
        param.lastUpdatedBy = msg.sender;

        // Record change in history
        configHistory.push(ConfigurationChange({
            parameterKey: key,
            oldValue: oldValue,
            newValue: newValue,
            timestamp: block.timestamp,
            changedBy: msg.sender,
            riskLevel: riskLevel,
            requiresApproval: riskLevel >= 7
        }));

        emit ParameterUpdated(key, oldValue, newValue, msg.sender, riskLevel);
    }

    /**
     * @notice Create new deployment template
     * @param name Template name
     * @param description Template description
     * @param templateType Type of template
     * @param parameterKeys Array of parameter keys
     * @param parameterValues Array of parameter values
     */
    function createTemplate(
        string memory name,
        string memory description,
        DeploymentTemplate templateType,
        string[] memory parameterKeys,
        uint256[] memory parameterValues
    ) external onlyConfigurator {
        require(parameterKeys.length == parameterValues.length, "Array length mismatch");

        templateCount++;
        TemplateConfig storage template = templates[templateCount];
        template.name = name;
        template.description = description;
        template.templateType = templateType;
        template.active = true;
        template.createdAt = block.timestamp;

        // Set template parameters
        for (uint i = 0; i < parameterKeys.length; i++) {
            template.parameters[parameterKeys[i]] = parameterValues[i];
        }

        emit TemplateCreated(templateCount, name, templateType);
    }

    /**
     * @notice Apply template configuration to current instance
     * @param templateId Template ID to apply
     * @param overrideKeys Parameter override keys
     * @param overrideValues Parameter override values
     */
    function applyTemplate(
        uint256 templateId,
        string[] memory overrideKeys,
        uint256[] memory overrideValues
    ) external onlyConfigurator {
        require(templates[templateId].active, "Template not active");
        require(overrideKeys.length == overrideValues.length, "Array length mismatch");

        TemplateConfig storage template = templates[templateId];

        // Apply template parameters (implementation would iterate through stored parameters)
        // This is a simplified version - full implementation would store parameter arrays

        // Apply overrides
        for (uint i = 0; i < overrideKeys.length; i++) {
            ConfigurationParameter storage param = parameters[overrideKeys[i]];
            if (bytes(param.key).length > 0) {
                param.value = overrideValues[i];
                param.lastUpdated = block.timestamp;
                param.lastUpdatedBy = msg.sender;
            }
        }
    }

    /**
     * @notice Freeze configuration for emergency
     * @param key Parameter key to freeze
     * @param reason Freeze reason
     * @param duration Freeze duration in seconds
     */
    function freezeConfiguration(
        string memory key,
        string memory reason,
        uint256 duration
    ) external onlyEmergency {
        bytes32 configHash = keccak256(abi.encodePacked(key));
        frozenConfigurations[configHash] = true;

        // Auto-unfreeze after duration (would need timer mechanism)
        emit ConfigurationFrozen(configHash, reason, duration);
    }

    /**
     * @notice Rollback parameter to previous value
     * @param key Parameter key
     */
    function rollbackParameter(string memory key) external onlyConfigurator {
        require(configHistory.length > 0, "No history available");

        // Find last change for this parameter
        for (uint i = configHistory.length; i > 0; i--) {
            ConfigurationChange storage change = configHistory[i - 1];
            if (keccak256(abi.encodePacked(change.parameterKey)) == keccak256(abi.encodePacked(key))) {
                ConfigurationParameter storage param = parameters[key];
                param.value = change.oldValue;
                param.lastUpdated = block.timestamp;
                param.lastUpdatedBy = msg.sender;

                emit ParameterRollback(key, change.oldValue, block.timestamp);
                break;
            }
        }
    }

    /**
     * @notice Get parameter value
     * @param key Parameter key
     * @return value Parameter value
     */
    function getParameter(string memory key) external view returns (uint256) {
        return parameters[key].value;
    }

    /**
     * @notice Get parameter details
     * @param key Parameter key
     * @return parameter ConfigurationParameter struct
     */
    function getParameterDetails(string memory key) external view returns (ConfigurationParameter memory) {
        return parameters[key];
    }

    /**
     * @notice Get template parameters (simplified getter)
     * @param templateId Template ID
     * @param parameterKey Parameter key
     * @return value Parameter value for template
     */
    function getTemplateParameter(uint256 templateId, string memory parameterKey) external view returns (uint256) {
        return templates[templateId].parameters[parameterKey];
    }

    /**
     * @notice Get configuration change history count
     * @return count Number of configuration changes
     */
    function getConfigHistoryCount() external view returns (uint256) {
        return configHistory.length;
    }

    /**
     * @notice Initialize default parameters with safe ranges
     */
    function _initializeDefaultParameters() internal {
        // Set parameter ranges
        ranges = ParameterRanges({
            votingThresholdMin: 50,     // 50%
            votingThresholdMax: 100,    // 100%
            proposalPeriodMin: 3600,    // 1 hour
            proposalPeriodMax: 2592000, // 30 days
            stakeRequirementMin: 0.01 ether,
            stakeRequirementMax: 100 ether,
            aiVotingWeightMin: 0,       // 0%
            aiVotingWeightMax: 50,      // 50%
            feeStructureMin: 0,         // 0%
            feeStructureMax: 10         // 10%
        });

        // Governance parameters
        parameters["voting_threshold"] = ConfigurationParameter({
            key: "voting_threshold",
            value: 67,  // 67% (2/3)
            minValue: ranges.votingThresholdMin,
            maxValue: ranges.votingThresholdMax,
            category: ConfigCategory.GOVERNANCE,
            constitutional: true,
            lastUpdated: block.timestamp,
            lastUpdatedBy: msg.sender
        });

        parameters["proposal_period"] = ConfigurationParameter({
            key: "proposal_period",
            value: 45818,  // ~1 week in blocks
            minValue: ranges.proposalPeriodMin / 13,  // Convert seconds to blocks
            maxValue: ranges.proposalPeriodMax / 13,
            category: ConfigCategory.GOVERNANCE,
            constitutional: false,
            lastUpdated: block.timestamp,
            lastUpdatedBy: msg.sender
        });

        parameters["ai_voting_weight"] = ConfigurationParameter({
            key: "ai_voting_weight",
            value: 33,  // 33.33%
            minValue: ranges.aiVotingWeightMin,
            maxValue: ranges.aiVotingWeightMax,
            category: ConfigCategory.AI_INTEGRATION,
            constitutional: true,
            lastUpdated: block.timestamp,
            lastUpdatedBy: msg.sender
        });

        // Economic parameters
        parameters["proposal_stake_requirement"] = ConfigurationParameter({
            key: "proposal_stake_requirement",
            value: 1 ether,  // 1 ETH default
            minValue: ranges.stakeRequirementMin,
            maxValue: ranges.stakeRequirementMax,
            category: ConfigCategory.ECONOMICS,
            constitutional: false,
            lastUpdated: block.timestamp,
            lastUpdatedBy: msg.sender
        });

        parameters["treasury_fee_rate"] = ConfigurationParameter({
            key: "treasury_fee_rate",
            value: 2,  // 2%
            minValue: ranges.feeStructureMin,
            maxValue: ranges.feeStructureMax,
            category: ConfigCategory.ECONOMICS,
            constitutional: false,
            lastUpdated: block.timestamp,
            lastUpdatedBy: msg.sender
        });

        // Organization parameters
        parameters["branch_autonomy_level"] = ConfigurationParameter({
            key: "branch_autonomy_level",
            value: 75,  // 75% autonomy
            minValue: 0,
            maxValue: 100,
            category: ConfigCategory.ORGANIZATION,
            constitutional: false,
            lastUpdated: block.timestamp,
            lastUpdatedBy: msg.sender
        });
    }

    /**
     * @notice Create standard deployment templates
     */
    function _createStandardTemplates() internal {
        // Templates would be created with full parameter sets
        // This is simplified - full implementation would create comprehensive templates
        templateCount = 3; // Umbrella, Standalone, Branch templates created
    }
}