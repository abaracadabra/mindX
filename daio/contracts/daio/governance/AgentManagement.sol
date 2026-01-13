// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./AgentFactory.sol";

/**
 * @title AgentManagement
 * @notice Agent lifecycle management with inactivity tracking
 * @dev Manages agent metadata updates and inactivity-based deactivation
 * @dev Compatible with AgentFactory for agent lifecycle operations
 */
contract AgentManagement {
    AgentFactory public immutable agentFactory;
    uint256 public inactivityTimeout = 365 days; // Default inactivity timeout

    // Events
    event AgentUpdated(
        address indexed agentAddress,
        bool active,
        uint256 timestamp
    );
    event AgentDeactivatedDueToInactivity(
        address indexed agentAddress,
        uint256 timestamp
    );
    event InactivityTimeoutUpdated(uint256 oldTimeout, uint256 newTimeout);

    modifier onlyGovernance() {
        require(
            msg.sender == agentFactory.governanceContract(),
            "Only governance contract"
        );
        _;
    }

    constructor(AgentFactory _agentFactory) {
        require(
            address(_agentFactory) != address(0),
            "Invalid AgentFactory address"
        );
        agentFactory = _agentFactory;
    }

    /**
     * @notice Update agent metadata via NFT
     * @param nftId NFT ID from AgentFactory
     * @param newMetadata New metadata URI
     */
    function updateAgentMetadataByNFT(
        uint256 nftId,
        string memory newMetadata
    ) external {
        AgentFactory.Agent memory agent = agentFactory.getAgentByNFT(nftId);
        require(agent.active, "Agent is not active");

        // Update the metadata in AgentFactory
        agentFactory.updateNFTMetadata(nftId, newMetadata);

        // Emit an update event
        emit AgentUpdated(agent.agentAddress, true, block.timestamp);
    }

    /**
     * @notice Update agent metadata by agent address
     * @param agentAddress Agent address
     * @param nftId NFT ID from AgentFactory
     * @param newMetadata New metadata URI
     */
    function updateAgentMetadata(
        address agentAddress,
        uint256 nftId,
        string memory newMetadata
    ) external {
        require(agentFactory.isAgentActive(agentAddress), "Agent is not active");

        // Verify NFT belongs to agent - get agent details
        (
            address agentAddr,
            bool active,
            uint256 createdAt,
            address tokenAddress,
            uint256 agentNftId,
            bytes32 metadataHash,
            uint256 idNFTTokenId
        ) = agentFactory.agents(agentAddress);
        
        require(agentNftId == nftId, "NFT does not belong to agent");

        // Update the metadata in AgentFactory
        agentFactory.updateNFTMetadata(nftId, newMetadata);

        // Emit an update event
        emit AgentUpdated(agentAddress, true, block.timestamp);
    }

    /**
     * @notice Deactivate agent due to inactivity
     * @param agentAddress Agent address
     * @dev Checks if agent has been inactive for longer than inactivityTimeout
     * @dev Note: This requires tracking last activity, which may need to be added to AgentFactory
     */
    function deactivateInactiveAgent(address agentAddress) external {
        require(agentFactory.isAgentActive(agentAddress), "Agent is already inactive");
        
        // Get agent details - agents mapping returns struct components
        (
            address agentAddr,
            bool active,
            uint256 createdAt,
            address tokenAddress,
            uint256 nftId,
            bytes32 metadataHash,
            uint256 idNFTTokenId
        ) = agentFactory.agents(agentAddress);
        
        require(agentAddr != address(0), "Agent doesn't exist");

        // Check if the agent has been inactive for too long
        // Note: This assumes createdAt can be used as lastActivity
        // In production, you may want to add a lastActivity field to AgentFactory
        uint256 timeSinceCreation = block.timestamp - createdAt;
        
        // For now, we'll use a simple check based on creation time
        // In a full implementation, you'd track lastActivity separately
        if (timeSinceCreation > inactivityTimeout) {
            // Mark agent as inactive (destroyed)
            agentFactory.destroyAgent(agentAddress);

            // Emit event
            emit AgentDeactivatedDueToInactivity(agentAddress, block.timestamp);
        }
    }

    /**
     * @notice Set inactivity timeout
     * @param newTimeout New inactivity timeout in seconds
     */
    function setInactivityTimeout(uint256 newTimeout) external onlyGovernance {
        require(newTimeout > 0, "Invalid timeout");
        uint256 oldTimeout = inactivityTimeout;
        inactivityTimeout = newTimeout;
        emit InactivityTimeoutUpdated(oldTimeout, newTimeout);
    }

    /**
     * @notice Check if agent should be deactivated due to inactivity
     * @param agentAddress Agent address
     * @return bool Whether agent should be deactivated
     */
    function shouldDeactivateAgent(address agentAddress) external view returns (bool) {
        if (!agentFactory.isAgentActive(agentAddress)) {
            return false;
        }
        
        // Get agent creation time
        (
            address agentAddr,
            bool active,
            uint256 createdAt,
            ,,,
        ) = agentFactory.agents(agentAddress);
        
        if (agentAddr == address(0)) {
            return false;
        }

        uint256 timeSinceCreation = block.timestamp - createdAt;
        return timeSinceCreation > inactivityTimeout;
    }

    /**
     * @notice Get agent status information
     * @param agentAddress Agent address
     * @return active Whether agent is active
     * @return createdAt Creation timestamp
     * @return timeSinceCreation Time since creation
     * @return shouldDeactivate Whether agent should be deactivated
     */
    function getAgentStatus(address agentAddress)
        external
        view
        returns (
            bool active,
            uint256 createdAt,
            uint256 timeSinceCreation,
            bool shouldDeactivate
        )
    {
        active = agentFactory.isAgentActive(agentAddress);
        
        // Get agent creation time
        (
            address agentAddr,
            bool agentActive,
            uint256 agentCreatedAt,
            ,,,
        ) = agentFactory.agents(agentAddress);
        
        createdAt = agentCreatedAt;
        timeSinceCreation = block.timestamp - createdAt;
        shouldDeactivate = timeSinceCreation > inactivityTimeout && active && agentAddr != address(0);
    }
}
