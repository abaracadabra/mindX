// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../DAIOBridge.sol";

/**
 * Mock DAIO governance for testing DAIOBridge
 */
contract MockDAIOGovernance is IDAIOGovernance {
    uint256 private _proposalCount;
    mapping(uint256 => ProposalData) private _proposals;

    struct ProposalData {
        address proposer;
        string title;
        ProposalStatus status;
        uint256 forVotes;
        uint256 againstVotes;
    }

    function getProposal(uint256 proposalId) external view returns (
        address proposer,
        string memory title,
        ProposalStatus status,
        uint256 forVotes,
        uint256 againstVotes
    ) {
        ProposalData storage p = _proposals[proposalId];
        return (p.proposer, p.title, p.status, p.forVotes, p.againstVotes);
    }

    function proposalCount() external view returns (uint256) {
        return _proposalCount;
    }

    function createProposal(
        string memory title,
        string memory description,
        ProposalType proposalType,
        string memory projectId,
        address target,
        bytes memory executionData
    ) external returns (uint256) {
        _proposalCount++;
        _proposals[_proposalCount] = ProposalData({
            proposer: msg.sender,
            title: title,
            status: ProposalStatus.Active,
            forVotes: 0,
            againstVotes: 0
        });
        return _proposalCount;
    }

    function createTreasuryAllocationProposal(
        string memory title,
        string memory description,
        string memory projectId,
        address recipient,
        uint256 amount,
        address token
    ) external returns (uint256) {
        _proposalCount++;
        _proposals[_proposalCount] = ProposalData({
            proposer: msg.sender,
            title: title,
            status: ProposalStatus.Active,
            forVotes: 0,
            againstVotes: 0
        });
        return _proposalCount;
    }

    function vote(uint256 proposalId, bool support) external {
        ProposalData storage p = _proposals[proposalId];
        if (support) p.forVotes += 1;
        else p.againstVotes += 1;
    }

    function checkProposalStatus(uint256 proposalId) external {}

    function executeProposal(uint256 proposalId) external {
        _proposals[proposalId].status = ProposalStatus.Executed;
    }
}
