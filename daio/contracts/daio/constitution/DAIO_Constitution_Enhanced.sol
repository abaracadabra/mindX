// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title DAIO_Constitution_Enhanced
 * @notice Enhanced constitutional governance with configurable risk parameters
 * @dev 15% defaults for diversification/tithe provide protection against catastrophic single asset failure
 * @dev Parameters can be adjusted through executive governance consensus while maintaining risk controls
 */
contract DAIO_Constitution_Enhanced is Ownable, Pausable {
    address public chairman;
    address public governance;      // DAIOGovernance contract
    address public treasury;        // Treasury contract (owned by governance)
    address public executiveGovernance; // Executive governance for parameter updates

    // Constitutional parameters (configurable with protective defaults)
    uint256 public diversificationMandateBP = 1500;    // 15% in basis points (default)
    uint256 public treasuryTitheBP = 1500;             // 15% in basis points (default)
    uint256 public maxSingleAllocationBP = 8500;       // 85% max single allocation (default)

    // Parameter bounds for safety
    uint256 public constant MIN_DIVERSIFICATION = 500;     // 5% minimum
    uint256 public constant MAX_DIVERSIFICATION = 5000;    // 50% maximum
    uint256 public constant MIN_TITHE = 100;               // 1% minimum
    uint256 public constant MAX_TITHE = 3000;              // 30% maximum
    uint256 public constant MIN_SINGLE_ALLOCATION = 5000;  // 50% minimum
    uint256 public constant MAX_SINGLE_ALLOCATION = 9500;  // 95% maximum
    uint256 public constant BASIS_POINTS = 10000;          // 100% = 10000 basis points

    // Emergency parameter freeze
    bool public parametersLocked;
    uint256 public lockExpiresAt;

    // Diversification tracking
    mapping(address => uint256) public allocationPercentages;  // Address => allocation %
    uint256 public totalAllocated;

    // Parameter change proposals
    struct ParameterChangeProposal {
        uint256 id;
        string parameter;               // "diversification", "tithe", "maxAllocation"
        uint256 newValue;
        uint256 proposedAt;
        uint256 executionTime;          // When change can be executed
        bool executed;
        address proposer;
        string rationale;
    }

    mapping(uint256 => ParameterChangeProposal) public parameterProposals;
    uint256 public proposalCounter;
    uint256 public constant PARAMETER_CHANGE_DELAY = 7 days; // Constitutional change delay

    // Events
    event ActionValidated(address indexed target, bytes action, bool valid);
    event DiversificationChecked(uint256 currentAllocation, uint256 maxAllowed);
    event ChairmanVeto(address indexed target, bytes action);
    event GovernanceUpdated(address indexed oldGovernance, address indexed newGovernance);
    event ChairmanUpdated(address indexed oldChairman, address indexed newChairman);
    event ExecutiveGovernanceUpdated(address indexed oldExecGov, address indexed newExecGov);

    // Parameter change events
    event ParameterChangeProposed(
        uint256 indexed proposalId,
        string parameter,
        uint256 currentValue,
        uint256 newValue,
        address proposer,
        string rationale
    );
    event ParameterChanged(
        string parameter,
        uint256 oldValue,
        uint256 newValue,
        uint256 proposalId
    );
    event ParametersLocked(uint256 lockExpiresAt, string reason);
    event ParametersUnlocked();

    modifier onlyGovernance() {
        require(
            msg.sender == governance ||
            msg.sender == treasury ||
            msg.sender == executiveGovernance,
            "Only governance"
        );
        _;
    }

    modifier onlyExecutiveGovernance() {
        require(msg.sender == executiveGovernance, "Only executive governance");
        _;
    }

    modifier onlyChairman() {
        require(msg.sender == chairman, "Only chairman");
        _;
    }

    modifier whenNotLocked() {
        require(!parametersLocked || block.timestamp >= lockExpiresAt, "Parameters locked");
        _;
    }

    constructor(address _chairman) Ownable(msg.sender) {
        require(_chairman != address(0), "Invalid chairman");
        chairman = _chairman;
    }

    /**
     * @notice Set governance contract address
     */
    function setGovernance(address _governance) external onlyOwner {
        require(_governance != address(0), "Invalid governance");
        address oldGovernance = governance;
        governance = _governance;
        emit GovernanceUpdated(oldGovernance, _governance);
    }

    /**
     * @notice Set executive governance contract address
     */
    function setExecutiveGovernance(address _executiveGovernance) external onlyOwner {
        require(_executiveGovernance != address(0), "Invalid executive governance");
        address oldExecGov = executiveGovernance;
        executiveGovernance = _executiveGovernance;
        emit ExecutiveGovernanceUpdated(oldExecGov, _executiveGovernance);
    }

    /**
     * @notice Set treasury contract address
     */
    function setTreasury(address _treasury) external onlyOwner {
        require(_treasury != address(0), "Invalid treasury");
        treasury = _treasury;
    }

    /**
     * @notice Update chairman (requires governance proposal)
     */
    function updateChairman(address _newChairman) external onlyGovernance {
        require(_newChairman != address(0), "Invalid chairman");
        address oldChairman = chairman;
        chairman = _newChairman;
        emit ChairmanUpdated(oldChairman, _newChairman);
    }

    /**
     * @notice Propose constitutional parameter change
     * @param parameter Parameter to change ("diversification", "tithe", "maxAllocation")
     * @param newValue New value in basis points
     * @param rationale Detailed rationale for the change
     */
    function proposeParameterChange(
        string memory parameter,
        uint256 newValue,
        string memory rationale
    ) external onlyExecutiveGovernance whenNotLocked returns (uint256) {
        require(bytes(parameter).length > 0, "Parameter required");
        require(bytes(rationale).length > 0, "Rationale required");

        // Validate parameter bounds
        _validateParameterBounds(parameter, newValue);

        proposalCounter++;
        uint256 proposalId = proposalCounter;
        uint256 executionTime = block.timestamp + PARAMETER_CHANGE_DELAY;

        // Get current value for comparison
        uint256 currentValue = _getCurrentParameterValue(parameter);

        parameterProposals[proposalId] = ParameterChangeProposal({
            id: proposalId,
            parameter: parameter,
            newValue: newValue,
            proposedAt: block.timestamp,
            executionTime: executionTime,
            executed: false,
            proposer: msg.sender,
            rationale: rationale
        });

        emit ParameterChangeProposed(
            proposalId,
            parameter,
            currentValue,
            newValue,
            msg.sender,
            rationale
        );

        return proposalId;
    }

    /**
     * @notice Execute approved parameter change
     * @param proposalId Proposal to execute
     */
    function executeParameterChange(uint256 proposalId) external onlyExecutiveGovernance whenNotLocked {
        ParameterChangeProposal storage proposal = parameterProposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(!proposal.executed, "Already executed");
        require(block.timestamp >= proposal.executionTime, "Execution delay not met");

        proposal.executed = true;

        uint256 oldValue = _getCurrentParameterValue(proposal.parameter);

        // Update the parameter
        _setParameter(proposal.parameter, proposal.newValue);

        emit ParameterChanged(
            proposal.parameter,
            oldValue,
            proposal.newValue,
            proposalId
        );
    }

    /**
     * @notice Emergency lock parameters to prevent changes
     * @param lockDuration Duration to lock parameters (max 30 days)
     * @param reason Reason for emergency lock
     */
    function emergencyLockParameters(uint256 lockDuration, string memory reason) external onlyChairman {
        require(lockDuration <= 30 days, "Lock duration too long");
        require(bytes(reason).length > 0, "Reason required");

        parametersLocked = true;
        lockExpiresAt = block.timestamp + lockDuration;

        emit ParametersLocked(lockExpiresAt, reason);
    }

    /**
     * @notice Unlock parameters (governance or expiration)
     */
    function unlockParameters() external {
        require(
            msg.sender == governance ||
            msg.sender == executiveGovernance ||
            block.timestamp >= lockExpiresAt,
            "Not authorized or lock not expired"
        );

        parametersLocked = false;
        lockExpiresAt = 0;

        emit ParametersUnlocked();
    }

    /**
     * @notice Validate action against constitutional constraints
     */
    function validateAction(
        address target,
        bytes memory action,
        uint256 amount
    ) external onlyGovernance returns (bool) {
        require(!paused(), "System paused");

        // Check diversification mandate
        bool diversificationValid = checkDiversificationLimit(target, amount);

        // Additional validation logic can be added here
        bool actionValid = diversificationValid;

        emit ActionValidated(target, action, actionValid);
        return actionValid;
    }

    /**
     * @notice Check if allocation violates diversification mandate
     */
    function checkDiversificationLimit(
        address recipient,
        uint256 amount
    ) public view returns (bool) {
        // Calculate new allocation percentage
        uint256 newAllocation = allocationPercentages[recipient] + amount;

        // Check if exceeds current diversification mandate
        uint256 maxAllowed = totalAllocated > 0 ?
            (totalAllocated * diversificationMandateBP) / BASIS_POINTS : 0;

        return newAllocation <= maxAllowed || totalAllocated == 0;
    }

    /**
     * @notice Get current tithe percentage in basis points
     */
    function getCurrentTitheRate() external view returns (uint256) {
        return treasuryTitheBP;
    }

    /**
     * @notice Get current diversification limit in basis points
     */
    function getCurrentDiversificationLimit() external view returns (uint256) {
        return diversificationMandateBP;
    }

    /**
     * @notice Get current max single allocation in basis points
     */
    function getCurrentMaxSingleAllocation() external view returns (uint256) {
        return maxSingleAllocationBP;
    }

    /**
     * @notice Calculate tithe amount for a given deposit
     * @param amount Deposit amount
     * @return tithe Amount to be collected as tithe
     */
    function calculateTithe(uint256 amount) external view returns (uint256 tithe) {
        return (amount * treasuryTitheBP) / BASIS_POINTS;
    }

    /**
     * @notice Record allocation for diversification tracking
     */
    function recordAllocation(
        address recipient,
        uint256 amount
    ) external onlyGovernance {
        allocationPercentages[recipient] += amount;
        totalAllocated += amount;
    }

    /**
     * @notice Remove allocation (for refunds/cancellations)
     */
    function removeAllocation(
        address recipient,
        uint256 amount
    ) external onlyGovernance {
        require(allocationPercentages[recipient] >= amount, "Insufficient allocation");
        allocationPercentages[recipient] -= amount;
        totalAllocated -= amount;
    }

    /**
     * @notice Chairman's Veto - Emergency pause
     */
    function pauseSystem() external onlyChairman {
        _pause();
    }

    /**
     * @notice Unpause system (requires governance or chairman)
     */
    function unpauseSystem() external {
        require(
            msg.sender == chairman || msg.sender == governance || msg.sender == executiveGovernance,
            "Not authorized"
        );
        _unpause();
    }

    /**
     * @notice Chairman's Veto - Block specific action
     */
    function vetoAction(
        address target,
        bytes memory action
    ) external onlyChairman {
        emit ChairmanVeto(target, action);
    }

    /**
     * @notice Get allocation percentage for an address
     */
    function getAllocationPercentage(address recipient) external view returns (uint256) {
        if (totalAllocated == 0) return 0;
        return (allocationPercentages[recipient] * BASIS_POINTS) / totalAllocated;
    }

    /**
     * @notice Get parameter change proposal details
     */
    function getParameterProposal(uint256 proposalId) external view returns (ParameterChangeProposal memory) {
        return parameterProposals[proposalId];
    }

    /**
     * @notice Check if parameters are currently modifiable
     */
    function canModifyParameters() external view returns (bool) {
        return !parametersLocked || block.timestamp >= lockExpiresAt;
    }

    /**
     * @notice Get comprehensive constitutional status
     */
    function getConstitutionalStatus() external view returns (
        uint256 currentDiversificationLimit,
        uint256 currentTitheRate,
        uint256 currentMaxAllocation,
        bool locked,
        uint256 lockExpiry,
        bool systemPaused
    ) {
        currentDiversificationLimit = diversificationMandateBP;
        currentTitheRate = treasuryTitheBP;
        currentMaxAllocation = maxSingleAllocationBP;
        locked = parametersLocked;
        lockExpiry = lockExpiresAt;
        systemPaused = paused();
    }

    // Internal functions

    function _validateParameterBounds(string memory parameter, uint256 newValue) internal pure {
        bytes32 paramHash = keccak256(abi.encodePacked(parameter));

        if (paramHash == keccak256(abi.encodePacked("diversification"))) {
            require(
                newValue >= MIN_DIVERSIFICATION && newValue <= MAX_DIVERSIFICATION,
                "Diversification out of bounds (5%-50%)"
            );
        } else if (paramHash == keccak256(abi.encodePacked("tithe"))) {
            require(
                newValue >= MIN_TITHE && newValue <= MAX_TITHE,
                "Tithe out of bounds (1%-30%)"
            );
        } else if (paramHash == keccak256(abi.encodePacked("maxAllocation"))) {
            require(
                newValue >= MIN_SINGLE_ALLOCATION && newValue <= MAX_SINGLE_ALLOCATION,
                "Max allocation out of bounds (50%-95%)"
            );
        } else {
            revert("Invalid parameter");
        }
    }

    function _getCurrentParameterValue(string memory parameter) internal view returns (uint256) {
        bytes32 paramHash = keccak256(abi.encodePacked(parameter));

        if (paramHash == keccak256(abi.encodePacked("diversification"))) {
            return diversificationMandateBP;
        } else if (paramHash == keccak256(abi.encodePacked("tithe"))) {
            return treasuryTitheBP;
        } else if (paramHash == keccak256(abi.encodePacked("maxAllocation"))) {
            return maxSingleAllocationBP;
        } else {
            revert("Invalid parameter");
        }
    }

    function _setParameter(string memory parameter, uint256 newValue) internal {
        bytes32 paramHash = keccak256(abi.encodePacked(parameter));

        if (paramHash == keccak256(abi.encodePacked("diversification"))) {
            diversificationMandateBP = newValue;
        } else if (paramHash == keccak256(abi.encodePacked("tithe"))) {
            treasuryTitheBP = newValue;
        } else if (paramHash == keccak256(abi.encodePacked("maxAllocation"))) {
            maxSingleAllocationBP = newValue;
        } else {
            revert("Invalid parameter");
        }
    }
}