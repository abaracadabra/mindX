// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title ITHOTDeployment
 * @notice Interface for THOT deployment engine
 */
interface ITHOTDeployment {

    enum DeploymentType {
        Inference,      // Read-only inference
        FineTuning,     // Fine-tuning session
        Evaluation,     // Benchmarking
        Integration     // Integration testing
    }

    struct DeploymentSession {
        bytes32 sessionId;
        uint256 thotTokenId;
        address deployer;
        address thotContract;
        uint256 startTime;
        uint256 endTime;
        uint256 tokensProcessed;
        uint256 avgLatency;
        uint256 peakMemoryMB;
        bool isActive;
        DeploymentType deploymentType;
    }

    struct DeploymentMetrics {
        uint256 tokensProcessed;
        uint256 avgLatency;
        uint256 peakMemoryMB;
        uint256 errorCount;
        uint256 successRate;      // Scaled by 10000
    }

    // Events
    event TensorDeployed(
        bytes32 indexed sessionId,
        uint256 indexed thotTokenId,
        address indexed deployer,
        DeploymentType deploymentType
    );

    event TensorUndeployed(
        bytes32 indexed sessionId,
        uint256 tokensProcessed,
        uint256 avgLatency
    );

    event DeploymentPaused(bytes32 indexed sessionId);
    event DeploymentResumed(bytes32 indexed sessionId);

    // Core Functions
    function deployTensor(
        address thotContract,
        uint256 thotTokenId,
        DeploymentType deploymentType
    ) external returns (bytes32 sessionId);

    function undeployTensor(
        bytes32 sessionId,
        DeploymentMetrics memory metrics
    ) external;

    function pauseDeployment(bytes32 sessionId) external;
    function resumeDeployment(bytes32 sessionId) external;

    // Access Control
    function canDeploy(address user, address thotContract, uint256 thotTokenId)
        external view returns (bool, string memory reason);

    // Getters
    function getDeploymentSession(bytes32 sessionId) external view returns (DeploymentSession memory);
    function getActiveDeploymentsForUser(address user) external view returns (bytes32[] memory);
    function getDeploymentHistory(address thotContract, uint256 thotTokenId)
        external view returns (DeploymentSession[] memory);
}
