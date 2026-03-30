// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../../daio/constitution/DAIO_Constitution.sol";
import "../../executive-governance/ExecutiveGovernance.sol";
import "../treasury/Treasury.sol";

/**
 * @title ConstitutionalComplianceAdapter
 * @dev Ensures all executive decisions comply with DAIO constitutional requirements
 *
 * Key Features:
 * - Real-time constitutional compliance monitoring
 * - Violation detection and prevention
 * - Emergency override procedures with constitutional bounds
 * - Complete audit trail for constitutional compliance
 * - Integration with CEO + Seven Soldiers governance
 */
contract ConstitutionalComplianceAdapter is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant COMPLIANCE_OFFICER_ROLE = keccak256("COMPLIANCE_OFFICER_ROLE");
    bytes32 public constant AUDITOR_ROLE = keccak256("AUDITOR_ROLE");
    bytes32 public constant EMERGENCY_OVERRIDE_ROLE = keccak256("EMERGENCY_OVERRIDE_ROLE");

    // Core constitution and governance contracts
    DAIO_Constitution public immutable constitution;
    ExecutiveGovernance public immutable executiveGovernance;
    Treasury public immutable treasury;

    // Compliance tracking structures
    struct ComplianceCheck {
        uint256 id;
        address requester;
        address target;
        bytes data;
        uint256 value;
        uint256 timestamp;
        bool approved;
        bool executed;
        string violationType;
        string resolution;
        address approver;
    }

    struct ViolationRecord {
        uint256 id;
        address violator;
        string violationType;
        string description;
        uint256 timestamp;
        bool resolved;
        string resolution;
        uint256 penaltyAmount;
    }

    struct ComplianceMetrics {
        uint256 totalChecks;
        uint256 approvedChecks;
        uint256 violations;
        uint256 resolved;
        uint256 lastUpdateTime;
    }

    // Emergency override tracking
    struct EmergencyOverride {
        uint256 id;
        address executor;
        string justification;
        uint256 timestamp;
        uint256 duration;
        bool active;
        bytes originalAction;
        bool constitutionallyValidated;
    }

    mapping(uint256 => ComplianceCheck) public complianceChecks;
    mapping(uint256 => ViolationRecord) public violations;
    mapping(uint256 => EmergencyOverride) public emergencyOverrides;
    mapping(address => ComplianceMetrics) public complianceMetrics;
    mapping(bytes4 => bool) public exemptMethods;
    mapping(address => bool) public trustedContracts;

    uint256 public nextCheckId = 1;
    uint256 public nextViolationId = 1;
    uint256 public nextOverrideId = 1;

    // Constitutional limits (synced with DAIO_Constitution)
    uint256 public constant TITHE_RATE = 1500; // 15%
    uint256 public constant DIVERSIFICATION_LIMIT = 1500; // 15%
    uint256 public constant MAX_EMERGENCY_DURATION = 7 days;
    uint256 public constant MAX_SINGLE_ALLOCATION = 1000 ether; // Example limit

    event ComplianceCheckRequested(
        uint256 indexed checkId,
        address indexed requester,
        address indexed target,
        bytes data
    );

    event ComplianceApproved(
        uint256 indexed checkId,
        address indexed approver,
        uint256 timestamp
    );

    event ViolationDetected(
        uint256 indexed violationId,
        address indexed violator,
        string violationType,
        uint256 timestamp
    );

    event EmergencyOverrideActivated(
        uint256 indexed overrideId,
        address indexed executor,
        string justification,
        uint256 duration
    );

    event ConstitutionalParameterUpdated(
        string parameter,
        uint256 oldValue,
        uint256 newValue,
        address updater
    );

    constructor(
        address _constitution,
        address _executiveGovernance,
        address _treasury,
        address _admin
    ) {
        require(_constitution != address(0), "Invalid constitution");
        require(_executiveGovernance != address(0), "Invalid executive governance");
        require(_treasury != address(0), "Invalid treasury");
        require(_admin != address(0), "Invalid admin");

        constitution = DAIO_Constitution(_constitution);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);
        treasury = Treasury(_treasury);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(COMPLIANCE_OFFICER_ROLE, _admin);
        _grantRole(AUDITOR_ROLE, _admin);
        _grantRole(EMERGENCY_OVERRIDE_ROLE, _admin);

        _initializeExemptMethods();
        _initializeTrustedContracts();
    }

    /**
     * @dev Initialize methods exempt from compliance checking
     */
    function _initializeExemptMethods() internal {
        // View functions
        exemptMethods[bytes4(keccak256("balanceOf(address)"))] = true;
        exemptMethods[bytes4(keccak256("totalSupply()"))] = true;
        exemptMethods[bytes4(keccak256("getProposal(uint256)"))] = true;

        // Standard ERC operations with built-in constraints
        exemptMethods[bytes4(keccak256("transfer(address,uint256)"))] = true;
        exemptMethods[bytes4(keccak256("approve(address,uint256)"))] = true;
    }

    /**
     * @dev Initialize trusted contracts that can bypass some checks
     */
    function _initializeTrustedContracts() internal {
        trustedContracts[address(constitution)] = true;
        trustedContracts[address(executiveGovernance)] = true;
        trustedContracts[address(treasury)] = true;
    }

    /**
     * @dev Validate executive decision against constitutional requirements
     */
    function validateExecutiveDecision(
        address target,
        bytes calldata data,
        uint256 value,
        address executor
    ) external nonReentrant whenNotPaused returns (uint256 checkId, bool approved) {
        require(executiveGovernance.hasExecutiveRole(executor), "Not an executive");

        checkId = nextCheckId++;

        // Create compliance check record
        ComplianceCheck storage check = complianceChecks[checkId];
        check.id = checkId;
        check.requester = msg.sender;
        check.target = target;
        check.data = data;
        check.value = value;
        check.timestamp = block.timestamp;

        emit ComplianceCheckRequested(checkId, msg.sender, target, data);

        // Skip checks for trusted contracts and exempt methods
        if (_shouldSkipCheck(target, data)) {
            check.approved = true;
            check.approver = address(this);
            emit ComplianceApproved(checkId, address(this), block.timestamp);
            return (checkId, true);
        }

        // Perform comprehensive compliance validation
        (bool isCompliant, string memory violationType) = _performComplianceCheck(target, data, value);

        if (isCompliant) {
            check.approved = true;
            check.approver = msg.sender;
            _updateComplianceMetrics(msg.sender, true);
            emit ComplianceApproved(checkId, msg.sender, block.timestamp);
        } else {
            check.violationType = violationType;
            _recordViolation(executor, violationType, string(data));
            _updateComplianceMetrics(msg.sender, false);
        }

        return (checkId, isCompliant);
    }

    /**
     * @dev Perform comprehensive compliance check
     */
    function _performComplianceCheck(
        address target,
        bytes calldata data,
        uint256 value
    ) internal view returns (bool isCompliant, string memory violationType) {
        // Check constitutional constraints via DAIO_Constitution
        (bool constitutionallyValid, string memory constitutionalError) = constitution.validateAction(target, data, value);
        if (!constitutionallyValid) {
            return (false, constitutionalError);
        }

        // Extract method signature
        if (data.length < 4) {
            return (true, "");
        }

        bytes4 methodSig = bytes4(data[:4]);

        // Treasury allocation checks
        if (_isTreasuryAllocation(methodSig)) {
            return _validateTreasuryAllocation(data, value);
        }

        // Asset diversification checks
        if (_isAssetOperation(methodSig)) {
            return _validateAssetDiversification(data, value);
        }

        // Governance parameter checks
        if (_isGovernanceUpdate(methodSig)) {
            return _validateGovernanceUpdate(data);
        }

        // Emergency action checks
        if (_isEmergencyAction(methodSig)) {
            return _validateEmergencyAction(data);
        }

        return (true, "");
    }

    /**
     * @dev Check if method is treasury allocation
     */
    function _isTreasuryAllocation(bytes4 methodSig) internal pure returns (bool) {
        return methodSig == bytes4(keccak256("allocateFunds(address,uint256)")) ||
               methodSig == bytes4(keccak256("withdrawFromTreasury(address,uint256)")) ||
               methodSig == bytes4(keccak256("investFunds(address,uint256)"));
    }

    /**
     * @dev Validate treasury allocation against 15% diversification limit
     */
    function _validateTreasuryAllocation(
        bytes calldata data,
        uint256 value
    ) internal view returns (bool, string memory) {
        // Decode allocation amount from data
        uint256 amount = value;
        if (data.length >= 68) {
            amount = abi.decode(data[36:68], (uint256));
        }

        // Get total treasury value
        uint256 totalTreasuryValue = treasury.getTotalValue();

        // Check 15% diversification limit
        uint256 maxAllocation = (totalTreasuryValue * DIVERSIFICATION_LIMIT) / 10000;
        if (amount > maxAllocation) {
            return (false, "Exceeds 15% diversification limit");
        }

        // Check against absolute maximum
        if (amount > MAX_SINGLE_ALLOCATION) {
            return (false, "Exceeds maximum single allocation");
        }

        return (true, "");
    }

    /**
     * @dev Check if method is asset operation
     */
    function _isAssetOperation(bytes4 methodSig) internal pure returns (bool) {
        return methodSig == bytes4(keccak256("addAsset(address,uint256)")) ||
               methodSig == bytes4(keccak256("removeAsset(address,uint256)")) ||
               methodSig == bytes4(keccak256("rebalancePortfolio(address[],uint256[])"));
    }

    /**
     * @dev Validate asset diversification
     */
    function _validateAssetDiversification(
        bytes calldata data,
        uint256 value
    ) internal view returns (bool, string memory) {
        // Implementation would check asset concentration limits
        // For now, return true with basic validation
        return (value <= MAX_SINGLE_ALLOCATION, "Asset operation within limits");
    }

    /**
     * @dev Check if method is governance update
     */
    function _isGovernanceUpdate(bytes4 methodSig) internal pure returns (bool) {
        return methodSig == bytes4(keccak256("updateVotingThreshold(uint256)")) ||
               methodSig == bytes4(keccak256("updateExecutiveRoles(address[])")) ||
               methodSig == bytes4(keccak256("modifyConstitution(bytes)"));
    }

    /**
     * @dev Validate governance updates
     */
    function _validateGovernanceUpdate(bytes calldata data) internal pure returns (bool, string memory) {
        // Governance updates require special validation
        // Constitutional amendments need unanimous approval
        bytes4 methodSig = bytes4(data[:4]);

        if (methodSig == bytes4(keccak256("modifyConstitution(bytes)"))) {
            return (false, "Constitutional modifications require unanimous consent");
        }

        return (true, "");
    }

    /**
     * @dev Check if method is emergency action
     */
    function _isEmergencyAction(bytes4 methodSig) internal pure returns (bool) {
        return methodSig == bytes4(keccak256("emergencyPause()")) ||
               methodSig == bytes4(keccak256("emergencyWithdraw(address,uint256)")) ||
               methodSig == bytes4(keccak256("activateEmergencyProtocol()"));
    }

    /**
     * @dev Validate emergency actions
     */
    function _validateEmergencyAction(bytes calldata data) internal view returns (bool, string memory) {
        // Emergency actions are time-limited
        bytes4 methodSig = bytes4(data[:4]);

        // Check for active emergency overrides
        for (uint256 i = 1; i < nextOverrideId; i++) {
            EmergencyOverride storage override = emergencyOverrides[i];
            if (override.active && block.timestamp < override.timestamp + override.duration) {
                return (true, "Emergency action authorized by active override");
            }
        }

        return (false, "Emergency action requires active override");
    }

    /**
     * @dev Record constitutional violation
     */
    function _recordViolation(
        address violator,
        string memory violationType,
        string memory description
    ) internal {
        uint256 violationId = nextViolationId++;

        ViolationRecord storage violation = violations[violationId];
        violation.id = violationId;
        violation.violator = violator;
        violation.violationType = violationType;
        violation.description = description;
        violation.timestamp = block.timestamp;
        violation.resolved = false;

        emit ViolationDetected(violationId, violator, violationType, block.timestamp);
    }

    /**
     * @dev Update compliance metrics
     */
    function _updateComplianceMetrics(address entity, bool approved) internal {
        ComplianceMetrics storage metrics = complianceMetrics[entity];
        metrics.totalChecks++;
        if (approved) {
            metrics.approvedChecks++;
        } else {
            metrics.violations++;
        }
        metrics.lastUpdateTime = block.timestamp;
    }

    /**
     * @dev Check if compliance check should be skipped
     */
    function _shouldSkipCheck(address target, bytes calldata data) internal view returns (bool) {
        // Skip for trusted contracts
        if (trustedContracts[target]) {
            return true;
        }

        // Skip for exempt methods
        if (data.length >= 4) {
            bytes4 methodSig = bytes4(data[:4]);
            if (exemptMethods[methodSig]) {
                return true;
            }
        }

        return false;
    }

    /**
     * @dev Activate emergency override (CEO only)
     */
    function activateEmergencyOverride(
        string calldata justification,
        uint256 duration,
        bytes calldata originalAction
    ) external onlyRole(EMERGENCY_OVERRIDE_ROLE) nonReentrant returns (uint256) {
        require(executiveGovernance.isCEO(msg.sender), "Only CEO can activate emergency override");
        require(duration <= MAX_EMERGENCY_DURATION, "Duration exceeds maximum");
        require(bytes(justification).length > 0, "Justification required");

        uint256 overrideId = nextOverrideId++;

        EmergencyOverride storage override = emergencyOverrides[overrideId];
        override.id = overrideId;
        override.executor = msg.sender;
        override.justification = justification;
        override.timestamp = block.timestamp;
        override.duration = duration;
        override.active = true;
        override.originalAction = originalAction;

        // Constitutional validation of the override itself
        (bool valid, ) = constitution.validateEmergencyAction(msg.sender, justification);
        override.constitutionallyValidated = valid;

        emit EmergencyOverrideActivated(overrideId, msg.sender, justification, duration);
        return overrideId;
    }

    /**
     * @dev Deactivate emergency override
     */
    function deactivateEmergencyOverride(
        uint256 overrideId
    ) external onlyRole(EMERGENCY_OVERRIDE_ROLE) {
        EmergencyOverride storage override = emergencyOverrides[overrideId];
        require(override.active, "Override not active");
        require(
            override.executor == msg.sender ||
            hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "Not authorized to deactivate"
        );

        override.active = false;
    }

    /**
     * @dev Resolve violation
     */
    function resolveViolation(
        uint256 violationId,
        string calldata resolution,
        uint256 penaltyAmount
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        ViolationRecord storage violation = violations[violationId];
        require(!violation.resolved, "Already resolved");

        violation.resolved = true;
        violation.resolution = resolution;
        violation.penaltyAmount = penaltyAmount;

        // Update metrics
        complianceMetrics[violation.violator].resolved++;
    }

    /**
     * @dev Get compliance report for address
     */
    function getComplianceReport(address entity) external view returns (
        ComplianceMetrics memory metrics,
        uint256[] memory violationIds,
        uint256 complianceScore
    ) {
        metrics = complianceMetrics[entity];

        // Find all violations for this entity
        uint256 count = 0;
        for (uint256 i = 1; i < nextViolationId; i++) {
            if (violations[i].violator == entity) {
                count++;
            }
        }

        violationIds = new uint256[](count);
        uint256 index = 0;
        for (uint256 i = 1; i < nextViolationId; i++) {
            if (violations[i].violator == entity) {
                violationIds[index] = i;
                index++;
            }
        }

        // Calculate compliance score (0-10000, where 10000 is perfect compliance)
        complianceScore = metrics.totalChecks > 0 ?
            (metrics.approvedChecks * 10000) / metrics.totalChecks : 10000;

        return (metrics, violationIds, complianceScore);
    }

    /**
     * @dev Add trusted contract
     */
    function addTrustedContract(address contractAddr) external onlyRole(DEFAULT_ADMIN_ROLE) {
        trustedContracts[contractAddr] = true;
    }

    /**
     * @dev Remove trusted contract
     */
    function removeTrustedContract(address contractAddr) external onlyRole(DEFAULT_ADMIN_ROLE) {
        trustedContracts[contractAddr] = false;
    }

    /**
     * @dev Add exempt method
     */
    function addExemptMethod(bytes4 methodSig) external onlyRole(DEFAULT_ADMIN_ROLE) {
        exemptMethods[methodSig] = true;
    }

    /**
     * @dev Remove exempt method
     */
    function removeExemptMethod(bytes4 methodSig) external onlyRole(DEFAULT_ADMIN_ROLE) {
        exemptMethods[methodSig] = false;
    }

    /**
     * @dev Get active emergency overrides
     */
    function getActiveEmergencyOverrides() external view returns (uint256[] memory) {
        uint256 count = 0;
        for (uint256 i = 1; i < nextOverrideId; i++) {
            if (emergencyOverrides[i].active &&
                block.timestamp < emergencyOverrides[i].timestamp + emergencyOverrides[i].duration) {
                count++;
            }
        }

        uint256[] memory activeOverrides = new uint256[](count);
        uint256 index = 0;
        for (uint256 i = 1; i < nextOverrideId; i++) {
            if (emergencyOverrides[i].active &&
                block.timestamp < emergencyOverrides[i].timestamp + emergencyOverrides[i].duration) {
                activeOverrides[index] = i;
                index++;
            }
        }

        return activeOverrides;
    }

    /**
     * @dev Emergency pause
     */
    function emergencyPause() external onlyRole(EMERGENCY_OVERRIDE_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}