// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title ITHOTTensorNFT
 * @notice Interface for comprehensive THOT Tensor NFT
 * @dev Extends basic THOT with neural network tensor metadata and lifecycle tracking
 */
interface ITHOTTensorNFT {

    // Structs
    struct TensorIdentity {
        string modelName;           // e.g., "AtaraxiaCoach-v3.2"
        string architecture;        // e.g., "transformer", "cnn", "diffusion"
        uint256 parameterCount;     // Total parameters (scaled by 1e9 for billions)
        uint256 optimizedSizeMB;    // Compressed size
        uint256 originalSizeMB;     // Original unoptimized size
        address creator;
        uint256 createdAt;
    }

    struct OptimizationMetadata {
        string quantizationMethod;  // "INT8", "INT4", "FP16", "BFLOAT16", etc.
        uint256 compressionRatio;   // Scaled by 100 (409 = 4.09x)
        uint256 accuracyRetained;   // Scaled by 10000 (9870 = 98.7%)
        uint256 sparsityLevel;      // Pruning level (scaled by 10000)
        uint256 prunedParameters;   // Count of pruned parameters
    }

    struct TensorFiles {
        bytes32 packageCID;         // Root IPFS CID for entire package
        bytes32 weightsCID;         // Neural network weights
        bytes32 embeddingsCID;      // Embedding layers
        bytes32 attentionCID;       // Attention weights (for transformers)
        bytes32 feedforwardCID;     // Feedforward layers
        bytes32 configCID;          // Deployment configuration
    }

    struct PerformanceMetrics {
        uint256 inferenceLatencyP50;    // Median latency in ms
        uint256 inferenceLatencyP95;    // p95 latency in ms
        uint256 throughputTokensPerSec; // Throughput
        uint256 memoryFootprintMB;      // Memory usage
        uint256 taskSuccessRate;        // Scaled by 10000
        uint256 deploymentCount;        // Number of times deployed
        uint256 totalTokensProcessed;   // Lifetime token count
    }

    struct TrainingProvenance {
        bytes32 baseModelCID;       // Base model fine-tuned from
        bytes32 trainingDatasetCID; // Training data CID
        uint256 trainingEpochs;
        uint256 gpuHours;           // Total compute used
        string framework;           // "pytorch", "tensorflow", "jax", etc.
    }

    // Events
    event THOTTensorMinted(
        uint256 indexed tokenId,
        string modelName,
        bytes32 packageCID,
        address indexed creator
    );

    event THOTOptimized(
        uint256 indexed tokenId,
        bytes32 oldPackageCID,
        bytes32 newPackageCID,
        uint256 compressionRatio
    );

    event THOTVersionCreated(
        uint256 indexed tokenId,
        uint256 versionIndex,
        bytes32 packageCID
    );

    event THOTDeploymentRecorded(
        uint256 indexed tokenId,
        uint256 deploymentCount,
        uint256 totalTokensProcessed
    );

    event THOTPerformanceUpdated(
        uint256 indexed tokenId,
        uint256 inferenceLatency,
        uint256 throughput,
        uint256 taskSuccessRate
    );

    event THTensorRated(
        uint256 indexed tokenId,
        address indexed rater,
        uint256 rating
    );

    // Core Functions
    function mintTHOTTensor(
        address recipient,
        TensorIdentity memory identity,
        OptimizationMetadata memory optimization,
        TensorFiles memory files,
        TrainingProvenance memory provenance,
        bool isPublic
    ) external returns (uint256 tokenId);

    function optimizeTensor(
        uint256 tokenId,
        bytes32 newPackageCID,
        TensorFiles memory newFiles,
        OptimizationMetadata memory newOptimization
    ) external;

    function recordDeployment(
        uint256 tokenId,
        uint256 tokensProcessed,
        uint256 latency,
        uint256 memoryUsed
    ) external;

    function updatePerformanceMetrics(
        uint256 tokenId,
        PerformanceMetrics memory metrics
    ) external;

    function createVersion(
        uint256 tokenId,
        TensorFiles memory newFiles,
        string memory versionNotes
    ) external returns (uint256 versionIndex);

    // Getters
    function getTensorIdentity(uint256 tokenId) external view returns (TensorIdentity memory);
    function getOptimizationMetadata(uint256 tokenId) external view returns (OptimizationMetadata memory);
    function getTensorFiles(uint256 tokenId) external view returns (TensorFiles memory);
    function getPerformanceMetrics(uint256 tokenId) external view returns (PerformanceMetrics memory);
    function getTrainingProvenance(uint256 tokenId) external view returns (TrainingProvenance memory);
    function getVersionHistory(uint256 tokenId) external view returns (bytes32[] memory);
    function getVersion(uint256 tokenId, uint256 versionIndex) external view returns (bytes32);
}
