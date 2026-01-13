// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DAIOGovernance.sol";

/**
 * @title BoardroomExtension
 * @notice Extension of DAIO governance with boardroom.sol integration
 * @dev Provides treasury management and proposal execution
 */
contract BoardroomExtension {
    DAIOGovernance public daioGovernance;
    
    struct TreasuryInfo {
        address token;      // Token address (address(0) for native)
        uint256 balance;    // Current balance
        uint256 allocated;  // Allocated but not spent
    }
    
    mapping(string => TreasuryInfo) public projectTreasuries;  // Project ID => TreasuryInfo
    mapping(uint256 => TreasuryAllocation) public allocations;  // Proposal ID => Allocation
    
    struct TreasuryAllocation {
        string projectId;
        address recipient;
        uint256 amount;
        address token;
        bool executed;
    }
    
    address public owner;
    
    event TreasuryAllocated(
        uint256 indexed proposalId,
        string projectId,
        address recipient,
        uint256 amount
    );
    event TreasuryExecuted(
        uint256 indexed proposalId,
        address recipient,
        uint256 amount
    );
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    modifier onlyDAIO() {
        require(msg.sender == address(daioGovernance), "Only DAIO");
        _;
    }
    
    constructor(address _daioGovernance) {
        owner = msg.sender;
        daioGovernance = DAIOGovernance(_daioGovernance);
    }
    
    /**
     * @notice Allocate treasury funds (called after proposal succeeds)
     * @param proposalId Proposal identifier
     * @param projectId Project identifier
     * @param recipient Recipient address
     * @param amount Amount to allocate
     * @param token Token address (address(0) for native)
     */
    function allocateTreasury(
        uint256 proposalId,
        string memory projectId,
        address recipient,
        uint256 amount,
        address token
    ) external onlyDAIO {
        TreasuryInfo storage treasury = projectTreasuries[projectId];
        
        if (token == address(0)) {
            require(address(this).balance >= amount, "Insufficient native balance");
        } else {
            // ERC20 token handling would go here
            require(treasury.balance >= amount, "Insufficient token balance");
        }
        
        allocations[proposalId] = TreasuryAllocation({
            projectId: projectId,
            recipient: recipient,
            amount: amount,
            token: token,
            executed: false
        });
        
        treasury.allocated += amount;
        
        emit TreasuryAllocated(proposalId, projectId, recipient, amount);
    }
    
    /**
     * @notice Execute treasury allocation
     * @param proposalId Proposal identifier
     */
    function executeAllocation(uint256 proposalId) external {
        TreasuryAllocation storage allocation = allocations[proposalId];
        require(!allocation.executed, "Already executed");
        (, , DAIOGovernance.ProposalStatus status, , ) = daioGovernance.getProposal(proposalId);
        require(
            status == DAIOGovernance.ProposalStatus.Executed,
            "Proposal not executed"
        );
        
        allocation.executed = true;
        
        TreasuryInfo storage treasury = projectTreasuries[allocation.projectId];
        treasury.allocated -= allocation.amount;
        treasury.balance -= allocation.amount;
        
        if (allocation.token == address(0)) {
            payable(allocation.recipient).transfer(allocation.amount);
        } else {
            // ERC20 transfer would go here
        }
        
        emit TreasuryExecuted(proposalId, allocation.recipient, allocation.amount);
    }
    
    /**
     * @notice Deposit funds to project treasury
     * @param projectId Project identifier
     * @param token Token address (address(0) for native)
     */
    function depositTreasury(string memory projectId, address token) external payable {
        TreasuryInfo storage treasury = projectTreasuries[projectId];
        
        if (token == address(0)) {
            treasury.balance += msg.value;
        } else {
            // ERC20 deposit would go here
            treasury.balance += msg.value;  // Placeholder
        }
    }
    
    /**
     * @notice Get treasury balance for a project
     * @param projectId Project identifier
     * @return balance Current balance
     * @return allocated Allocated amount
     */
    function getTreasury(string memory projectId) external view returns (uint256 balance, uint256 allocated) {
        TreasuryInfo storage treasury = projectTreasuries[projectId];
        return (treasury.balance, treasury.allocated);
    }
}
