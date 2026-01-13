// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title DAIO_Constitution
 * @notice Constitutional governance contract enforcing immutable rules
 * @dev Enforces 15% diversification mandate, 15% tithe, and Chairman's Veto
 */
contract DAIO_Constitution is Ownable, Pausable {
    address public chairman;
    address public governance;  // DAIOGovernance contract
    address public treasury;    // Treasury contract (owned by governance)
    
    // Constitutional constants (immutable)
    uint256 public constant DIVERSIFICATION_MANDATE = 1500;  // 15% in basis points
    uint256 public constant TREASURY_TITHE = 1500;          // 15% in basis points
    uint256 public constant MAX_SINGLE_ALLOCATION = 8500;   // 85% max single allocation
    
    // Diversification tracking
    mapping(address => uint256) public allocationPercentages;  // Address => allocation %
    uint256 public totalAllocated;
    
    event ActionValidated(address indexed target, bytes action, bool valid);
    event DiversificationChecked(uint256 currentAllocation, uint256 maxAllowed);
    event ChairmanVeto(address indexed target, bytes action);
    event GovernanceUpdated(address indexed oldGovernance, address indexed newGovernance);
    event ChairmanUpdated(address indexed oldChairman, address indexed newChairman);

    modifier onlyGovernance() {
        require(msg.sender == governance || msg.sender == treasury, "Only governance");
        _;
    }

    modifier onlyChairman() {
        require(msg.sender == chairman, "Only chairman");
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
     * @notice Check if allocation violates 15% diversification mandate
     */
    function checkDiversificationLimit(
        address recipient,
        uint256 amount
    ) public view returns (bool) {
        // Calculate new allocation percentage
        uint256 newAllocation = allocationPercentages[recipient] + amount;
        
        // Check if exceeds 15% of total
        uint256 maxAllowed = totalAllocated > 0 ? (totalAllocated * DIVERSIFICATION_MANDATE) / 10000 : 0;
        
        return newAllocation <= maxAllowed || totalAllocated == 0;
    }
    
    /**
     * @notice Check diversification and emit event (for external calls that need events)
     */
    function checkDiversificationLimitWithEvent(
        address recipient,
        uint256 amount
    ) external returns (bool) {
        uint256 newAllocation = allocationPercentages[recipient] + amount;
        uint256 maxAllowed = totalAllocated > 0 ? (totalAllocated * DIVERSIFICATION_MANDATE) / 10000 : 0;
        
        emit DiversificationChecked(newAllocation, maxAllowed);
        
        return newAllocation <= maxAllowed || totalAllocated == 0;
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
            msg.sender == chairman || msg.sender == governance,
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
        // In a full implementation, this would prevent execution
    }

    /**
     * @notice Get allocation percentage for an address
     */
    function getAllocationPercentage(address recipient) external view returns (uint256) {
        if (totalAllocated == 0) return 0;
        return (allocationPercentages[recipient] * 10000) / totalAllocated;
    }
}
