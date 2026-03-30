// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../../daio/settings/GovernanceSettings.sol";
import "../../executive-governance/ExecutiveGovernance.sol";
import "../../daio/constitution/DAIO_Constitution.sol";

/**
 * @title ExecutiveSettingsManager
 * @dev Executive control over governance settings with role-based access
 *
 * Key Features:
 * - Role-based settings control (different executives control different categories)
 * - Constitutional validation for all setting changes
 * - Emergency settings for crisis management
 * - Complete audit trail of settings changes
 * - Integration with CEO + Seven Soldiers governance
 */
contract ExecutiveSettingsManager is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant SETTINGS_MANAGER_ROLE = keccak256("SETTINGS_MANAGER_ROLE");
    bytes32 public constant EMERGENCY_SETTINGS_ROLE = keccak256("EMERGENCY_SETTINGS_ROLE");
    bytes32 public constant AUDIT_ROLE = keccak256("AUDIT_ROLE");

    // Core contracts
    GovernanceSettings public immutable governanceSettings;
    ExecutiveGovernance public immutable executiveGovernance;
    DAIO_Constitution public immutable constitution;

    // Settings categories with role-based access
    enum SettingsCategory {
        GOVERNANCE,        // Voting periods, quorums, thresholds
        TREASURY,          // Treasury allocation limits, fees
        SECURITY,          // Security parameters, emergency controls
        OPERATIONS,        // Operational parameters, timeouts
        CONSTITUTIONAL,    // Constitutional parameters (requires unanimity)
        EMERGENCY          // Emergency-only settings
    }

    // Executive role mappings to settings categories
    enum ExecutiveRole {
        CEO,              // Can modify any category
        CISO,             // Security settings
        CTO,              // Operations and governance technical settings
        CFO,              // Treasury and financial settings
        CRO,              // Risk and compliance settings
        CPO,              // Operational and people settings
        COO,              // Operations and governance process settings
        CLO               // Legal and constitutional settings
    }

    struct SettingChange {
        uint256 id;
        address executor;
        ExecutiveRole executiveRole;
        SettingsCategory category;
        string settingName;
        bytes32 oldValue;
        bytes32 newValue;
        uint256 timestamp;
        bool approved;
        bool executed;
        string justification;
        uint256 approvalCount;
        mapping(address => bool) approvals;
    }

    struct EmergencySettingChange {
        uint256 id;
        address ceo;
        string settingName;
        bytes32 oldValue;
        bytes32 newValue;
        uint256 timestamp;
        uint256 duration;
        string justification;
        bool active;
        bool constitutionallyValidated;
    }

    mapping(uint256 => SettingChange) public settingChanges;
    mapping(uint256 => EmergencySettingChange) public emergencyChanges;
    mapping(ExecutiveRole => mapping(SettingsCategory => bool)) public rolePermissions;
    mapping(SettingsCategory => uint256) public requiredApprovals;
    mapping(SettingsCategory => bool) public requiresConstitutionalValidation;
    mapping(string => SettingsCategory) public settingCategories;
    mapping(string => bytes32) public currentSettings;

    uint256 public nextChangeId = 1;
    uint256 public nextEmergencyId = 1;
    uint256 public emergencySettingDuration = 7 days;

    event SettingChangeProposed(
        uint256 indexed changeId,
        address indexed proposer,
        ExecutiveRole role,
        SettingsCategory category,
        string settingName
    );

    event SettingChangeApproved(
        uint256 indexed changeId,
        address indexed approver,
        uint256 approvalCount,
        uint256 required
    );

    event SettingChangeExecuted(
        uint256 indexed changeId,
        string settingName,
        bytes32 oldValue,
        bytes32 newValue,
        uint256 timestamp
    );

    event EmergencySettingActivated(
        uint256 indexed emergencyId,
        address indexed ceo,
        string settingName,
        bytes32 newValue,
        uint256 duration
    );

    event RolePermissionUpdated(
        ExecutiveRole role,
        SettingsCategory category,
        bool granted,
        address updater
    );

    constructor(
        address _governanceSettings,
        address _executiveGovernance,
        address _constitution,
        address _admin
    ) {
        require(_governanceSettings != address(0), "Invalid governance settings");
        require(_executiveGovernance != address(0), "Invalid executive governance");
        require(_constitution != address(0), "Invalid constitution");
        require(_admin != address(0), "Invalid admin");

        governanceSettings = GovernanceSettings(_governanceSettings);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);
        constitution = DAIO_Constitution(_constitution);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(SETTINGS_MANAGER_ROLE, _admin);
        _grantRole(EMERGENCY_SETTINGS_ROLE, _admin);
        _grantRole(AUDIT_ROLE, _admin);

        _initializeRolePermissions();
        _initializeSettingCategories();
        _initializeApprovalRequirements();
    }

    /**
     * @dev Initialize role-based permissions for settings categories
     */
    function _initializeRolePermissions() internal {
        // CEO can modify any category
        for (uint256 i = 0; i <= uint256(SettingsCategory.EMERGENCY); i++) {
            rolePermissions[ExecutiveRole.CEO][SettingsCategory(i)] = true;
        }

        // CISO - Security settings
        rolePermissions[ExecutiveRole.CISO][SettingsCategory.SECURITY] = true;
        rolePermissions[ExecutiveRole.CISO][SettingsCategory.EMERGENCY] = true;

        // CTO - Technical and operational settings
        rolePermissions[ExecutiveRole.CTO][SettingsCategory.GOVERNANCE] = true;
        rolePermissions[ExecutiveRole.CTO][SettingsCategory.OPERATIONS] = true;

        // CFO - Treasury and financial settings
        rolePermissions[ExecutiveRole.CFO][SettingsCategory.TREASURY] = true;
        rolePermissions[ExecutiveRole.CFO][SettingsCategory.GOVERNANCE] = true; // Voting thresholds

        // CRO - Risk and compliance
        rolePermissions[ExecutiveRole.CRO][SettingsCategory.SECURITY] = true;
        rolePermissions[ExecutiveRole.CRO][SettingsCategory.TREASURY] = true;

        // CPO - People and operational
        rolePermissions[ExecutiveRole.CPO][SettingsCategory.OPERATIONS] = true;
        rolePermissions[ExecutiveRole.CPO][SettingsCategory.GOVERNANCE] = true; // Participation settings

        // COO - Operations and processes
        rolePermissions[ExecutiveRole.COO][SettingsCategory.OPERATIONS] = true;
        rolePermissions[ExecutiveRole.COO][SettingsCategory.GOVERNANCE] = true;

        // CLO - Legal and constitutional
        rolePermissions[ExecutiveRole.CLO][SettingsCategory.CONSTITUTIONAL] = true;
        rolePermissions[ExecutiveRole.CLO][SettingsCategory.SECURITY] = true; // Compliance
    }

    /**
     * @dev Initialize settings categorization
     */
    function _initializeSettingCategories() internal {
        // Governance settings
        settingCategories["votingPeriod"] = SettingsCategory.GOVERNANCE;
        settingCategories["quorumThreshold"] = SettingsCategory.GOVERNANCE;
        settingCategories["approvalThreshold"] = SettingsCategory.GOVERNANCE;
        settingCategories["proposalThreshold"] = SettingsCategory.GOVERNANCE;

        // Treasury settings
        settingCategories["maxAllocation"] = SettingsCategory.TREASURY;
        settingCategories["treasuryFee"] = SettingsCategory.TREASURY;
        settingCategories["diversificationLimit"] = SettingsCategory.TREASURY;
        settingCategories["titheRate"] = SettingsCategory.CONSTITUTIONAL; // Constitutional

        // Security settings
        settingCategories["timelockDelay"] = SettingsCategory.SECURITY;
        settingCategories["emergencyDelay"] = SettingsCategory.SECURITY;
        settingCategories["pauseDuration"] = SettingsCategory.SECURITY;

        // Operational settings
        settingCategories["executionTimeout"] = SettingsCategory.OPERATIONS;
        settingCategories["agentActivationDelay"] = SettingsCategory.OPERATIONS;
        settingCategories["knowledgeUpdatePeriod"] = SettingsCategory.OPERATIONS;

        // Constitutional settings
        settingCategories["constitutionalThreshold"] = SettingsCategory.CONSTITUTIONAL;
        settingCategories["chairmanVetoPower"] = SettingsCategory.CONSTITUTIONAL;
    }

    /**
     * @dev Initialize approval requirements for each category
     */
    function _initializeApprovalRequirements() internal {
        requiredApprovals[SettingsCategory.GOVERNANCE] = 3; // 3 executives
        requiredApprovals[SettingsCategory.TREASURY] = 5;   // 5 executives
        requiredApprovals[SettingsCategory.SECURITY] = 4;   // 4 executives
        requiredApprovals[SettingsCategory.OPERATIONS] = 3; // 3 executives
        requiredApprovals[SettingsCategory.CONSTITUTIONAL] = 8; // All executives
        requiredApprovals[SettingsCategory.EMERGENCY] = 1;  // CEO only

        // Constitutional validation requirements
        requiresConstitutionalValidation[SettingsCategory.TREASURY] = true;
        requiresConstitutionalValidation[SettingsCategory.CONSTITUTIONAL] = true;
    }

    /**
     * @dev Propose setting change
     */
    function proposeSettingChange(
        string calldata settingName,
        bytes32 newValue,
        string calldata justification
    ) external nonReentrant whenNotPaused returns (uint256) {
        // Verify executive role
        ExecutiveRole role = _getExecutiveRole(msg.sender);
        require(role != ExecutiveRole.CEO || executiveGovernance.isCEO(msg.sender), "Invalid executive role");

        // Get setting category
        SettingsCategory category = settingCategories[settingName];
        require(_hasPermission(role, category), "No permission for this setting category");

        // Get current value
        bytes32 oldValue = _getCurrentSettingValue(settingName);

        // Constitutional validation if required
        if (requiresConstitutionalValidation[category]) {
            require(_validateConstitutionalChange(settingName, newValue), "Constitutional violation");
        }

        uint256 changeId = nextChangeId++;

        SettingChange storage change = settingChanges[changeId];
        change.id = changeId;
        change.executor = msg.sender;
        change.executiveRole = role;
        change.category = category;
        change.settingName = settingName;
        change.oldValue = oldValue;
        change.newValue = newValue;
        change.timestamp = block.timestamp;
        change.justification = justification;

        emit SettingChangeProposed(changeId, msg.sender, role, category, settingName);

        // Auto-approve if only one approval required or if CEO
        if (requiredApprovals[category] <= 1 || role == ExecutiveRole.CEO) {
            _approveSettingChange(changeId, msg.sender);
        }

        return changeId;
    }

    /**
     * @dev Approve setting change
     */
    function approveSettingChange(
        uint256 changeId
    ) external nonReentrant whenNotPaused {
        SettingChange storage change = settingChanges[changeId];
        require(!change.executed, "Already executed");
        require(!change.approvals[msg.sender], "Already approved");

        // Verify executive role
        ExecutiveRole role = _getExecutiveRole(msg.sender);
        require(_hasPermission(role, change.category), "No permission for this category");

        _approveSettingChange(changeId, msg.sender);
    }

    /**
     * @dev Internal approval logic
     */
    function _approveSettingChange(uint256 changeId, address approver) internal {
        SettingChange storage change = settingChanges[changeId];

        change.approvals[approver] = true;
        change.approvalCount++;

        emit SettingChangeApproved(
            changeId,
            approver,
            change.approvalCount,
            requiredApprovals[change.category]
        );

        // Check if sufficient approvals received
        if (change.approvalCount >= requiredApprovals[change.category]) {
            _executeSettingChange(changeId);
        }
    }

    /**
     * @dev Execute approved setting change
     */
    function _executeSettingChange(uint256 changeId) internal {
        SettingChange storage change = settingChanges[changeId];
        require(!change.executed, "Already executed");

        // Update the setting
        _updateSetting(change.settingName, change.newValue);

        change.executed = true;
        change.approved = true;

        emit SettingChangeExecuted(
            changeId,
            change.settingName,
            change.oldValue,
            change.newValue,
            block.timestamp
        );
    }

    /**
     * @dev Emergency setting change by CEO
     */
    function emergencySettingChange(
        string calldata settingName,
        bytes32 newValue,
        string calldata justification,
        uint256 duration
    ) external onlyRole(EMERGENCY_SETTINGS_ROLE) nonReentrant returns (uint256) {
        require(executiveGovernance.isCEO(msg.sender), "Only CEO can make emergency changes");
        require(duration <= emergencySettingDuration, "Duration exceeds maximum");

        bytes32 oldValue = _getCurrentSettingValue(settingName);

        // Constitutional validation
        bool constitutionallyValid = _validateConstitutionalChange(settingName, newValue);
        require(constitutionallyValid || _isEmergencyOverride(justification), "Constitutional violation");

        uint256 emergencyId = nextEmergencyId++;

        EmergencySettingChange storage emergency = emergencyChanges[emergencyId];
        emergency.id = emergencyId;
        emergency.ceo = msg.sender;
        emergency.settingName = settingName;
        emergency.oldValue = oldValue;
        emergency.newValue = newValue;
        emergency.timestamp = block.timestamp;
        emergency.duration = duration;
        emergency.justification = justification;
        emergency.active = true;
        emergency.constitutionallyValidated = constitutionallyValid;

        // Apply emergency change immediately
        _updateSetting(settingName, newValue);

        emit EmergencySettingActivated(emergencyId, msg.sender, settingName, newValue, duration);

        return emergencyId;
    }

    /**
     * @dev Revert emergency setting change
     */
    function revertEmergencyChange(
        uint256 emergencyId
    ) external nonReentrant {
        EmergencySettingChange storage emergency = emergencyChanges[emergencyId];
        require(emergency.active, "Emergency change not active");
        require(
            block.timestamp >= emergency.timestamp + emergency.duration ||
            emergency.ceo == msg.sender ||
            hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "Cannot revert yet"
        );

        // Revert to old value
        _updateSetting(emergency.settingName, emergency.oldValue);
        emergency.active = false;
    }

    /**
     * @dev Get current setting value
     */
    function _getCurrentSettingValue(string memory settingName) internal view returns (bytes32) {
        // Try to get from current settings cache first
        bytes32 cachedValue = currentSettings[settingName];
        if (cachedValue != bytes32(0)) {
            return cachedValue;
        }

        // Get from GovernanceSettings contract
        return governanceSettings.getSettingValue(settingName);
    }

    /**
     * @dev Update setting value
     */
    function _updateSetting(string memory settingName, bytes32 value) internal {
        // Update cache
        currentSettings[settingName] = value;

        // Update in GovernanceSettings contract
        governanceSettings.updateSetting(settingName, value);
    }

    /**
     * @dev Validate constitutional compliance for setting change
     */
    function _validateConstitutionalChange(
        string memory settingName,
        bytes32 newValue
    ) internal view returns (bool) {
        // Special validation for constitutional parameters
        if (keccak256(bytes(settingName)) == keccak256(bytes("titheRate"))) {
            uint256 rate = uint256(newValue);
            return rate >= 1000 && rate <= 2000; // 10% to 20%
        }

        if (keccak256(bytes(settingName)) == keccak256(bytes("diversificationLimit"))) {
            uint256 limit = uint256(newValue);
            return limit >= 500 && limit <= 2500; // 5% to 25%
        }

        // Default constitutional validation
        return constitution.validateSettingChange(settingName, newValue);
    }

    /**
     * @dev Check if justification qualifies for emergency override
     */
    function _isEmergencyOverride(string memory justification) internal pure returns (bool) {
        bytes32 justificationHash = keccak256(bytes(justification));
        return justificationHash == keccak256(bytes("SECURITY_BREACH")) ||
               justificationHash == keccak256(bytes("SYSTEM_COMPROMISE")) ||
               justificationHash == keccak256(bytes("IMMEDIATE_THREAT"));
    }

    /**
     * @dev Get executive role for address
     */
    function _getExecutiveRole(address executive) internal view returns (ExecutiveRole) {
        if (executiveGovernance.isCEO(executive)) return ExecutiveRole.CEO;

        // Get role from ExecutiveGovernance contract
        string memory roleString = executiveGovernance.getExecutiveRole(executive);
        bytes32 roleHash = keccak256(bytes(roleString));

        if (roleHash == keccak256(bytes("CISO"))) return ExecutiveRole.CISO;
        if (roleHash == keccak256(bytes("CTO"))) return ExecutiveRole.CTO;
        if (roleHash == keccak256(bytes("CFO"))) return ExecutiveRole.CFO;
        if (roleHash == keccak256(bytes("CRO"))) return ExecutiveRole.CRO;
        if (roleHash == keccak256(bytes("CPO"))) return ExecutiveRole.CPO;
        if (roleHash == keccak256(bytes("COO"))) return ExecutiveRole.COO;
        if (roleHash == keccak256(bytes("CLO"))) return ExecutiveRole.CLO;

        revert("Invalid executive role");
    }

    /**
     * @dev Check if role has permission for category
     */
    function _hasPermission(ExecutiveRole role, SettingsCategory category) internal view returns (bool) {
        return rolePermissions[role][category];
    }

    /**
     * @dev Update role permissions
     */
    function updateRolePermission(
        ExecutiveRole role,
        SettingsCategory category,
        bool granted
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        rolePermissions[role][category] = granted;
        emit RolePermissionUpdated(role, category, granted, msg.sender);
    }

    /**
     * @dev Update required approvals for category
     */
    function updateRequiredApprovals(
        SettingsCategory category,
        uint256 requiredCount
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(requiredCount <= 8, "Cannot require more than 8 approvals");
        requiredApprovals[category] = requiredCount;
    }

    /**
     * @dev Get setting change details
     */
    function getSettingChangeDetails(uint256 changeId) external view returns (
        address executor,
        ExecutiveRole role,
        SettingsCategory category,
        string memory settingName,
        bytes32 oldValue,
        bytes32 newValue,
        uint256 approvalCount,
        uint256 requiredCount,
        bool executed
    ) {
        SettingChange storage change = settingChanges[changeId];
        return (
            change.executor,
            change.executiveRole,
            change.category,
            change.settingName,
            change.oldValue,
            change.newValue,
            change.approvalCount,
            requiredApprovals[change.category],
            change.executed
        );
    }

    /**
     * @dev Check if executive has approved setting change
     */
    function hasApprovedSettingChange(
        uint256 changeId,
        address executive
    ) external view returns (bool) {
        return settingChanges[changeId].approvals[executive];
    }

    /**
     * @dev Get active emergency changes
     */
    function getActiveEmergencyChanges() external view returns (uint256[] memory) {
        uint256 count = 0;
        for (uint256 i = 1; i < nextEmergencyId; i++) {
            if (emergencyChanges[i].active &&
                block.timestamp < emergencyChanges[i].timestamp + emergencyChanges[i].duration) {
                count++;
            }
        }

        uint256[] memory activeChanges = new uint256[](count);
        uint256 index = 0;
        for (uint256 i = 1; i < nextEmergencyId; i++) {
            if (emergencyChanges[i].active &&
                block.timestamp < emergencyChanges[i].timestamp + emergencyChanges[i].duration) {
                activeChanges[index] = i;
                index++;
            }
        }

        return activeChanges;
    }

    /**
     * @dev Emergency pause
     */
    function emergencyPause() external onlyRole(EMERGENCY_SETTINGS_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}