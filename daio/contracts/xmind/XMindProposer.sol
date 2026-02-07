// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title XMindProposer
 * @notice Proposal request queue for mindX; KnowledgeHierarchyDAIO.createProposal is onlyGovernance (timelock executor)
 * @dev mindX submits requests here; the timelock executor must call KnowledgeHierarchyDAIO.createProposal(description) with the requested description
 */
contract XMindProposer is Ownable {
    address public immutable knowledgeHierarchy;

    struct ProposalRequest {
        string description;
        uint256 requestedAt;
        bool fulfilled;  // true once governance has created the proposal (tracked off-chain or by index)
    }

    ProposalRequest[] public requests;

    event ProposalRequested(uint256 indexed requestId, string description, uint256 requestedAt);

    constructor(address _knowledgeHierarchy) Ownable(msg.sender) {
        require(_knowledgeHierarchy != address(0), "Invalid KnowledgeHierarchy");
        knowledgeHierarchy = _knowledgeHierarchy;
    }

    /**
     * @notice Submit a proposal request for mindX; governance (timelock executor) must call KnowledgeHierarchyDAIO.createProposal(description) separately
     */
    function requestProposal(string memory description) external onlyOwner returns (uint256 requestId) {
        require(bytes(description).length > 0, "Empty description");
        requestId = requests.length;
        requests.push(ProposalRequest({
            description: description,
            requestedAt: block.timestamp,
            fulfilled: false
        }));
        emit ProposalRequested(requestId, description, block.timestamp);
        return requestId;
    }

    /**
     * @notice Mark a request as fulfilled (e.g. after off-chain governance created the proposal). Optional, for indexing.
     */
    function setFulfilled(uint256 requestId) external onlyOwner {
        require(requestId < requests.length, "Invalid request");
        requests[requestId].fulfilled = true;
    }

    function getRequestCount() external view returns (uint256) {
        return requests.length;
    }

    function getRequest(uint256 requestId) external view returns (string memory description, uint256 requestedAt, bool fulfilled) {
        require(requestId < requests.length, "Invalid request");
        ProposalRequest storage r = requests[requestId];
        return (r.description, r.requestedAt, r.fulfilled);
    }
}
