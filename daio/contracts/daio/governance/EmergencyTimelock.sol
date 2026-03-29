// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/TimelockController.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../constitution/DAIO_Constitution.sol";
import "./ExecutiveRoles.sol";

/**
 * @title EmergencyTimelock
 * @notice CEO emergency powers with constitutional safeguards
 * @dev Allows 7-day emergency timelock bypass while enforcing constitutional constraints
 */
contract EmergencyTimelock is TimelockController, ReentrancyGuard {

    // Emergency state
    enum EmergencyStatus {
        NONE,           // 0 - No emergency
        DECLARED,       // 1 - Emergency declared
        ACTIVE,         // 2 - Emergency actions being taken
        RESOLVED        // 3 - Emergency resolved
    }

    // Emergency declaration structure
    struct Emergency {
        uint256 id;
        address declaredBy;
        string reason;
        uint256 declaredAt;
        uint256 expiresAt;
        EmergencyStatus status;
        uint256 actionsCount;
        bool constitutionalOverride;  // Whether constitutional validation was bypassed
    }

    // Emergency action tracking
    struct EmergencyAction {
        uint256 emergencyId;
        bytes32 operationId;
        address target;
        uint256 value;
        bytes data;
        uint256 executedAt;
        bool constitutionallyValid;
    }

    // Constants
    uint256 public constant EMERGENCY_DURATION = 7 days;
    uint256 public constant MAX_EMERGENCY_ACTIONS = 10;
    uint256 public constant COOLDOWN_PERIOD = 30 days; // Between emergencies

    // State variables
    DAIO_Constitution public immutable constitution;
    ExecutiveRoles public immutable executiveRoles;

    uint256 public emergencyCounter;
    uint256 public lastEmergencyAt;

    mapping(uint256 => Emergency) public emergencies;
    mapping(uint256 => EmergencyAction[]) public emergencyActions;
    mapping(bytes32 => uint256) public operationToEmergency; // operationId => emergencyId

    // Events
    event EmergencyDeclared(
        uint256 indexed emergencyId,
        address indexed declaredBy,
        string reason,
        uint256 expiresAt
    );
    event EmergencyActionExecuted(
        uint256 indexed emergencyId,
        bytes32 indexed operationId,
        address indexed target,
        uint256 value,
        bool constitutionallyValid
    );
    event EmergencyResolved(
        uint256 indexed emergencyId,
        address indexed resolvedBy,
        uint256 resolvedAt,
        uint256 totalActions
    );
    event ConstitutionalViolationDetected(
        uint256 indexed emergencyId,
        bytes32 indexed operationId,
        string violation
    );

    modifier onlyCEO() {
        require(
            executiveRoles.hasRole(executiveRoles.CEO_ROLE(), msg.sender),
            "Only CEO can declare emergency"
        );
        _;
    }

    modifier duringEmergency(uint256 emergencyId) {
        require(
            emergencies[emergencyId].status == EmergencyStatus.DECLARED ||
            emergencies[emergencyId].status == EmergencyStatus.ACTIVE,
            "No active emergency"
        );
        require(
            block.timestamp <= emergencies[emergencyId].expiresAt,
            "Emergency expired"
        );
        _;
    }

    constructor(
        uint256 minDelay,
        address[] memory proposers,
        address[] memory executors,
        address admin,
        address _constitution,
        address _executiveRoles
    ) TimelockController(minDelay, proposers, executors, admin) {
        require(_constitution != address(0), "Invalid constitution address");
        require(_executiveRoles != address(0), "Invalid executive roles address");

        constitution = DAIO_Constitution(_constitution);
        executiveRoles = ExecutiveRoles(_executiveRoles);
    }

    /**
     * @notice Declare emergency and activate CEO powers
     * @param reason Detailed reason for emergency
     */
    function declareEmergency(string memory reason) external onlyCEO nonReentrant {
        require(bytes(reason).length > 0, "Emergency reason required");
        require(
            lastEmergencyAt == 0 || block.timestamp >= lastEmergencyAt + COOLDOWN_PERIOD,
            "Emergency cooldown period active"
        );

        emergencyCounter++;
        uint256 emergencyId = emergencyCounter;
        uint256 expiresAt = block.timestamp + EMERGENCY_DURATION;

        emergencies[emergencyId] = Emergency({
            id: emergencyId,
            declaredBy: msg.sender,
            reason: reason,
            declaredAt: block.timestamp,
            expiresAt: expiresAt,
            status: EmergencyStatus.DECLARED,
            actionsCount: 0,
            constitutionalOverride: false
        });

        lastEmergencyAt = block.timestamp;

        emit EmergencyDeclared(emergencyId, msg.sender, reason, expiresAt);
    }

    /**
     * @notice Execute emergency action bypassing normal timelock
     * @param emergencyId Active emergency ID
     * @param target Target contract address
     * @param value Native token value to send
     * @param data Encoded function call data
     */
    function executeEmergencyAction(
        uint256 emergencyId,
        address target,
        uint256 value,
        bytes memory data
    ) public onlyCEO duringEmergency(emergencyId) nonReentrant returns (bytes32) {
        Emergency storage emergency = emergencies[emergencyId];

        require(
            emergency.actionsCount < MAX_EMERGENCY_ACTIONS,
            "Max emergency actions exceeded"
        );

        // Update emergency status to ACTIVE
        if (emergency.status == EmergencyStatus.DECLARED) {
            emergency.status = EmergencyStatus.ACTIVE;
        }

        // Generate operation ID
        bytes32 operationId = keccak256(abi.encode(emergencyId, target, value, data, block.timestamp));

        // Validate against constitution if possible
        bool constitutionallyValid = false;
        string memory violationReason = "";

        try constitution.validateAction(target, data, value) returns (bool valid) {
            constitutionallyValid = valid;
            if (!valid) {
                violationReason = "Constitutional validation failed";
            }
        } catch (bytes memory reason) {
            violationReason = string(reason);
            // Emergency can proceed but flag constitutional violation
            emit ConstitutionalViolationDetected(emergencyId, operationId, violationReason);
        }

        // Execute action regardless (emergency bypass)
        (bool success, bytes memory returnData) = target.call{value: value}(data);
        require(success, "Emergency action execution failed");

        // Record action
        EmergencyAction memory action = EmergencyAction({
            emergencyId: emergencyId,
            operationId: operationId,
            target: target,
            value: value,
            data: data,
            executedAt: block.timestamp,
            constitutionallyValid: constitutionallyValid
        });

        emergencyActions[emergencyId].push(action);
        operationToEmergency[operationId] = emergencyId;
        emergency.actionsCount++;

        // Update constitutional override flag if needed
        if (!constitutionallyValid) {
            emergency.constitutionalOverride = true;
        }

        emit EmergencyActionExecuted(
            emergencyId,
            operationId,
            target,
            value,
            constitutionallyValid
        );

        return operationId;
    }

    /**
     * @notice Resolve emergency and return to normal governance
     * @param emergencyId Emergency to resolve
     */
    function resolveEmergency(uint256 emergencyId) external {
        Emergency storage emergency = emergencies[emergencyId];

        require(
            emergency.status == EmergencyStatus.DECLARED ||
            emergency.status == EmergencyStatus.ACTIVE,
            "Emergency not active"
        );

        // CEO or governance can resolve
        require(
            executiveRoles.hasRole(executiveRoles.CEO_ROLE(), msg.sender) ||
            executiveRoles.hasRole(executiveRoles.GOVERNANCE_ROLE(), msg.sender),
            "Not authorized to resolve emergency"
        );

        emergency.status = EmergencyStatus.RESOLVED;

        emit EmergencyResolved(
            emergencyId,
            msg.sender,
            block.timestamp,
            emergency.actionsCount
        );
    }

    /**
     * @notice Get emergency details
     * @param emergencyId Emergency ID to query
     * @return emergency Emergency struct
     */
    function getEmergency(uint256 emergencyId) external view returns (Emergency memory emergency) {
        return emergencies[emergencyId];
    }

    /**
     * @notice Get all actions for an emergency
     * @param emergencyId Emergency ID to query
     * @return actions Array of emergency actions
     */
    function getEmergencyActions(uint256 emergencyId) external view returns (EmergencyAction[] memory actions) {
        return emergencyActions[emergencyId];
    }

    /**
     * @notice Check if emergency is currently active
     * @param emergencyId Emergency ID to check
     * @return active Whether emergency is active
     */
    function isEmergencyActive(uint256 emergencyId) external view returns (bool active) {
        Emergency memory emergency = emergencies[emergencyId];
        return (emergency.status == EmergencyStatus.DECLARED || emergency.status == EmergencyStatus.ACTIVE) &&
               block.timestamp <= emergency.expiresAt;
    }

    /**
     * @notice Get current active emergency (if any)
     * @return emergencyId Active emergency ID (0 if none)
     * @return emergency Emergency details
     */
    function getCurrentEmergency() external view returns (uint256 emergencyId, Emergency memory emergency) {
        for (uint256 i = emergencyCounter; i > 0; i--) {
            Emergency memory em = emergencies[i];
            if ((em.status == EmergencyStatus.DECLARED || em.status == EmergencyStatus.ACTIVE) &&
                block.timestamp <= em.expiresAt) {
                return (i, em);
            }
        }
        return (0, emergency); // No active emergency
    }

    /**
     * @notice Check CEO emergency override capability
     * @return canDeclare Whether CEO can currently declare emergency
     * @return cooldownEnd When cooldown period ends (if applicable)
     */
    function checkCEOEmergencyStatus() external view returns (bool canDeclare, uint256 cooldownEnd) {
        if (lastEmergencyAt == 0) {
            return (true, 0);
        }

        cooldownEnd = lastEmergencyAt + COOLDOWN_PERIOD;
        canDeclare = block.timestamp >= cooldownEnd;
    }

    /**
     * @notice Get emergency action by operation ID
     * @param operationId Operation ID to lookup
     * @return emergencyId Associated emergency ID
     * @return action Emergency action details
     */
    function getActionByOperationId(bytes32 operationId) external view returns (
        uint256 emergencyId,
        EmergencyAction memory action
    ) {
        emergencyId = operationToEmergency[operationId];
        require(emergencyId != 0, "Operation not found");

        EmergencyAction[] memory actions = emergencyActions[emergencyId];
        for (uint i = 0; i < actions.length; i++) {
            if (actions[i].operationId == operationId) {
                return (emergencyId, actions[i]);
            }
        }
        revert("Action not found in emergency");
    }

    /**
     * @notice Batch execute multiple emergency actions
     * @param emergencyId Active emergency ID
     * @param targets Array of target addresses
     * @param values Array of values to send
     * @param datas Array of call data
     * @return operationIds Array of operation IDs
     */
    function batchEmergencyExecute(
        uint256 emergencyId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory datas
    ) external onlyCEO duringEmergency(emergencyId) nonReentrant returns (bytes32[] memory operationIds) {
        require(
            targets.length == values.length && values.length == datas.length,
            "Array length mismatch"
        );
        require(targets.length <= 5, "Too many actions in batch");

        Emergency storage emergency = emergencies[emergencyId];
        require(
            emergency.actionsCount + targets.length <= MAX_EMERGENCY_ACTIONS,
            "Batch would exceed max actions"
        );

        operationIds = new bytes32[](targets.length);

        for (uint i = 0; i < targets.length; i++) {
            operationIds[i] = executeEmergencyAction(
                emergencyId,
                targets[i],
                values[i],
                datas[i]
            );
        }

        return operationIds;
    }

    /**
     * @notice Override to prevent normal timelock operations during emergency
     */
    function execute(
        address target,
        uint256 value,
        bytes calldata data,
        bytes32 predecessor,
        bytes32 salt
    ) public payable override nonReentrant {
        // Check if emergency is active
        (uint256 emergencyId, ) = this.getCurrentEmergency();
        if (emergencyId != 0) {
            revert("Normal operations suspended during emergency");
        }

        // Validate against constitution
        require(
            constitution.validateAction(target, data, value),
            "Constitutional validation failed"
        );

        super.execute(target, value, data, predecessor, salt);
    }

    /**
     * @notice Override to prevent scheduling during emergency
     */
    function schedule(
        address target,
        uint256 value,
        bytes calldata data,
        bytes32 predecessor,
        bytes32 salt,
        uint256 delay
    ) public override {
        // Check if emergency is active
        (uint256 emergencyId, ) = this.getCurrentEmergency();
        if (emergencyId != 0) {
            revert("Cannot schedule operations during emergency");
        }

        super.schedule(target, value, data, predecessor, salt, delay);
    }

    /**
     * @notice Get comprehensive emergency statistics
     * @return totalEmergencies Total emergencies declared
     * @return activeEmergencyId Current active emergency ID (0 if none)
     * @return lastEmergencyTimestamp When last emergency was declared
     * @return canDeclareNew Whether new emergency can be declared
     */
    function getEmergencyStatistics() external view returns (
        uint256 totalEmergencies,
        uint256 activeEmergencyId,
        uint256 lastEmergencyTimestamp,
        bool canDeclareNew
    ) {
        totalEmergencies = emergencyCounter;
        (activeEmergencyId, ) = this.getCurrentEmergency();
        lastEmergencyTimestamp = lastEmergencyAt;
        (canDeclareNew, ) = this.checkCEOEmergencyStatus();
    }
}