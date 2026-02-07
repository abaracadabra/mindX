// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DAIOBridge
 * @notice Facade to DAIO governance for mindX: single entrypoint for proposal and vote flows
 * @dev Forwards calls to DAIOGovernance; msg.sender is preserved so voting power applies to the caller
 */
interface IDAIOGovernance {
    enum ProposalType {
        Generic,
        Treasury,
        AgentRegistry,
        ProjectExtension,
        CrossProject
    }
    enum ProposalStatus {
        Pending,
        Active,
        Succeeded,
        Defeated,
        Executed,
        Cancelled
    }
    function getProposal(uint256 proposalId) external view returns (
        address proposer,
        string memory title,
        ProposalStatus status,
        uint256 forVotes,
        uint256 againstVotes
    );
    function proposalCount() external view returns (uint256);
    function createProposal(
        string memory title,
        string memory description,
        ProposalType proposalType,
        string memory projectId,
        address target,
        bytes memory executionData
    ) external returns (uint256);
    function createTreasuryAllocationProposal(
        string memory title,
        string memory description,
        string memory projectId,
        address recipient,
        uint256 amount,
        address token
    ) external returns (uint256);
    function vote(uint256 proposalId, bool support) external;
    function checkProposalStatus(uint256 proposalId) external;
    function executeProposal(uint256 proposalId) external;
}

/**
 * @title DAIOBridge
 * @notice Bridge contract exposing DAIO governance to mindX; deploy once per DAIOGovernance
 */
contract DAIOBridge {
    IDAIOGovernance public immutable daioGovernance;

    event BridgeCall(string fn, uint256 proposalIdOrCount);

    constructor(address _daioGovernance) {
        require(_daioGovernance != address(0), "Invalid DAIO governance");
        daioGovernance = IDAIOGovernance(_daioGovernance);
    }

    function getProposal(uint256 proposalId) external view returns (
        address proposer,
        string memory title,
        IDAIOGovernance.ProposalStatus status,
        uint256 forVotes,
        uint256 againstVotes
    ) {
        return daioGovernance.getProposal(proposalId);
    }

    function proposalCount() external view returns (uint256) {
        return daioGovernance.proposalCount();
    }

    function createProposal(
        string memory title,
        string memory description,
        IDAIOGovernance.ProposalType proposalType,
        string memory projectId,
        address target,
        bytes memory executionData
    ) external returns (uint256) {
        uint256 id = daioGovernance.createProposal(
            title,
            description,
            proposalType,
            projectId,
            target,
            executionData
        );
        emit BridgeCall("createProposal", id);
        return id;
    }

    function createTreasuryAllocationProposal(
        string memory title,
        string memory description,
        string memory projectId,
        address recipient,
        uint256 amount,
        address token
    ) external returns (uint256) {
        uint256 id = daioGovernance.createTreasuryAllocationProposal(
            title,
            description,
            projectId,
            recipient,
            amount,
            token
        );
        emit BridgeCall("createTreasuryAllocationProposal", id);
        return id;
    }

    function vote(uint256 proposalId, bool support) external {
        daioGovernance.vote(proposalId, support);
        emit BridgeCall("vote", proposalId);
    }

    function checkProposalStatus(uint256 proposalId) external {
        daioGovernance.checkProposalStatus(proposalId);
    }

    function executeProposal(uint256 proposalId) external {
        daioGovernance.executeProposal(proposalId);
        emit BridgeCall("executeProposal", proposalId);
    }
}
