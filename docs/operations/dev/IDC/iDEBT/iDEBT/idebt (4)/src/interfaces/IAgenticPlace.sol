// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IAgenticPlace
/// @notice On-chain surface for the AgenticPlace agent marketplace
///         (off-chain at agenticplace.pythai.net) implementing ERC-8004-style
///         agent identity & reputation for iDEBT underwriters/advisors.
interface IAgenticPlace {
    struct Agent {
        bytes32 agentId;      // unique identity root
        address owner;        // wallet controlling the agent
        uint128 reputation;   // BONAFIDE reputation score
        uint64  registeredAt;
        uint64  lastActivity;
        string  endpoint;     // e.g. https://agent.pythai.net/a/<id>
    }

    event AgentRegistered(bytes32 indexed agentId, address indexed owner, string endpoint);
    event AgentAttested(bytes32 indexed agentId, uint128 delta, address attester);
    event AgentSlashed(bytes32 indexed agentId, uint128 amount, string reason);

    error AgentExists();
    error UnknownAgent();
    error NotAuthorized();

    function register(bytes32 agentId, string calldata endpoint) external;
    function attest(bytes32 agentId, uint128 delta) external;
    function slash(bytes32 agentId, uint128 amount, string calldata reason) external;
    function agentOf(bytes32 agentId) external view returns (Agent memory);
    function reputationOf(bytes32 agentId) external view returns (uint128);
}
