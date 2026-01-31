// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../interfaces/ITHOTTensorNFT.sol";

/**
 * @title THOTTensorNFT
 * @notice Enhanced ERC721 for Transferable Hyper-Optimized Tensors
 * @dev Comprehensive neural network tensor NFT with lifecycle tracking
 *      Extends basic THOT.sol with optimization metadata, performance metrics, and version control
 */
contract THOTTensorNFT is ERC721, Ownable, ReentrancyGuard, ITHOTTensorNFT {

    // State variables
    uint256 private _tokenIdCounter;

    // Storage mappings
    mapping(uint256 => TensorIdentity) private _identity;
    mapping(uint256 => OptimizationMetadata) private _optimization;
    mapping(uint256 => TensorFiles) private _files;
    mapping(uint256 => PerformanceMetrics) private _performance;
    mapping(uint256 => TrainingProvenance) private _provenance;
    mapping(uint256 => bytes32[]) private _versionHistory;
    mapping(uint256 => bool) private _isPublic;
    mapping(uint256 => bool) private _isEncrypted;
    mapping(uint256 => bytes32) private _licenseHash;
    mapping(uint256 => uint256) private _lastUpdatedAt;
    mapping(uint256 => uint256) private _lastDeployedAt;

    // CID tracking to prevent duplicates
    mapping(bytes32 => bool) private _cidExists;
    mapping(bytes32 => uint256) private _cidToTokenId;

    // Rating tracking
    mapping(uint256 => mapping(address => bool)) private _hasRated;
    mapping(uint256 => uint256) private _totalRatings;
    mapping(uint256 => uint256) private _ratingSum;

    constructor() ERC721("THOT Tensor NFT", "THOT") Ownable(msg.sender) {
        _tokenIdCounter = 1;
    }

    /**
     * @notice Mint new comprehensive THOT tensor NFT
     * @param recipient Address to receive the tensor NFT
     * @param identity Tensor identity metadata
     * @param optimization Optimization metadata
     * @param files IPFS CIDs for tensor files
     * @param provenance Training provenance data
     * @param isPublic Whether tensor is publicly accessible
     * @return tokenId The ID of the newly minted tensor
     */
    function mintTHOTTensor(
        address recipient,
        TensorIdentity memory identity,
        OptimizationMetadata memory optimization,
        TensorFiles memory files,
        TrainingProvenance memory provenance,
        bool isPublic
    ) external onlyOwner nonReentrant returns (uint256) {
        require(recipient != address(0), "Invalid recipient");
        require(!_cidExists[files.packageCID], "Package CID already exists");
        require(bytes(identity.modelName).length > 0, "Model name required");
        require(bytes(identity.architecture).length > 0, "Architecture required");

        uint256 tokenId = _tokenIdCounter++;

        // Set identity
        identity.creator = msg.sender;
        identity.createdAt = block.timestamp;
        _identity[tokenId] = identity;

        // Set optimization metadata
        _optimization[tokenId] = optimization;

        // Set tensor files
        _files[tokenId] = files;

        // Set provenance
        _provenance[tokenId] = provenance;

        // Initialize performance metrics
        _performance[tokenId] = PerformanceMetrics({
            inferenceLatencyP50: 0,
            inferenceLatencyP95: 0,
            throughputTokensPerSec: 0,
            memoryFootprintMB: identity.optimizedSizeMB,
            taskSuccessRate: 5000, // 50% starting point
            deploymentCount: 0,
            totalTokensProcessed: 0
        });

        // Initialize version history
        _versionHistory[tokenId].push(files.packageCID);

        // Set access control
        _isPublic[tokenId] = isPublic;
        _isEncrypted[tokenId] = !isPublic;

        // Set timestamps
        _lastUpdatedAt[tokenId] = block.timestamp;

        // Track CID
        _cidExists[files.packageCID] = true;
        _cidToTokenId[files.packageCID] = tokenId;

        // Mint token
        _safeMint(recipient, tokenId);

        emit THOTTensorMinted(
            tokenId,
            identity.modelName,
            files.packageCID,
            msg.sender
        );

        return tokenId;
    }

    /**
     * @notice Optimize existing tensor with new compression/quantization
     * @param tokenId Token ID to optimize
     * @param newPackageCID New package CID after optimization
     * @param newFiles New tensor files
     * @param newOptimization New optimization metadata
     */
    function optimizeTensor(
        uint256 tokenId,
        bytes32 newPackageCID,
        TensorFiles memory newFiles,
        OptimizationMetadata memory newOptimization
    ) external nonReentrant {
        require(_ownerOf(tokenId) == msg.sender, "Not token owner");
        require(!_cidExists[newPackageCID], "Package CID already exists");

        bytes32 oldPackageCID = _files[tokenId].packageCID;

        // Update files
        _files[tokenId] = newFiles;

        // Update optimization metadata
        _optimization[tokenId] = newOptimization;

        // Update identity size
        _identity[tokenId].optimizedSizeMB = newFiles.packageCID != bytes32(0)
            ? _identity[tokenId].optimizedSizeMB // Keep existing if not changing
            : newOptimization.compressionRatio > 0
                ? (_identity[tokenId].originalSizeMB * 100) / newOptimization.compressionRatio
                : _identity[tokenId].optimizedSizeMB;

        // Add to version history
        _versionHistory[tokenId].push(newPackageCID);

        // Update CID tracking
        delete _cidExists[oldPackageCID];
        _cidExists[newPackageCID] = true;
        _cidToTokenId[newPackageCID] = tokenId;

        // Update timestamp
        _lastUpdatedAt[tokenId] = block.timestamp;

        emit THOTOptimized(
            tokenId,
            oldPackageCID,
            newPackageCID,
            newOptimization.compressionRatio
        );
    }

    /**
     * @notice Record deployment session for tensor
     * @param tokenId Token ID
     * @param tokensProcessed Number of tokens processed
     * @param latency Deployment latency in ms
     * @param memoryUsed Memory used in MB
     */
    function recordDeployment(
        uint256 tokenId,
        uint256 tokensProcessed,
        uint256 latency,
        uint256 memoryUsed
    ) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");

        PerformanceMetrics storage perf = _performance[tokenId];

        // Increment deployment count
        perf.deploymentCount++;

        // Update total tokens processed
        perf.totalTokensProcessed += tokensProcessed;

        // Update metrics using exponential moving average (EMA with alpha = 0.3)
        if (perf.inferenceLatencyP50 == 0) {
            // First deployment - use actual values
            perf.inferenceLatencyP50 = latency;
            perf.memoryFootprintMB = memoryUsed;
        } else {
            // Subsequent deployments - EMA
            perf.inferenceLatencyP50 = (perf.inferenceLatencyP50 * 70 + latency * 30) / 100;
            perf.memoryFootprintMB = (perf.memoryFootprintMB * 70 + memoryUsed * 30) / 100;
        }

        // Update timestamp
        _lastDeployedAt[tokenId] = block.timestamp;

        emit THOTDeploymentRecorded(
            tokenId,
            perf.deploymentCount,
            perf.totalTokensProcessed
        );
    }

    /**
     * @notice Update performance metrics for tensor
     * @param tokenId Token ID
     * @param metrics New performance metrics
     */
    function updatePerformanceMetrics(
        uint256 tokenId,
        PerformanceMetrics memory metrics
    ) external {
        require(_ownerOf(tokenId) == msg.sender || owner() == msg.sender, "Not authorized");
        require(_ownerOf(tokenId) != address(0), "Token does not exist");

        _performance[tokenId] = metrics;

        emit THOTPerformanceUpdated(
            tokenId,
            metrics.inferenceLatencyP50,
            metrics.throughputTokensPerSec,
            metrics.taskSuccessRate
        );
    }

    /**
     * @notice Create new version of tensor
     * @param tokenId Token ID
     * @param newFiles New tensor files for version
     * @param versionNotes Notes about this version
     * @return versionIndex Index of the new version
     */
    function createVersion(
        uint256 tokenId,
        TensorFiles memory newFiles,
        string memory versionNotes
    ) external returns (uint256) {
        require(_ownerOf(tokenId) == msg.sender, "Not token owner");
        require(!_cidExists[newFiles.packageCID], "Package CID already exists");

        // Add to version history
        _versionHistory[tokenId].push(newFiles.packageCID);
        uint256 versionIndex = _versionHistory[tokenId].length - 1;

        // Track CID
        _cidExists[newFiles.packageCID] = true;

        // Update files to latest version
        _files[tokenId] = newFiles;

        // Update timestamp
        _lastUpdatedAt[tokenId] = block.timestamp;

        emit THOTVersionCreated(
            tokenId,
            versionIndex,
            newFiles.packageCID
        );

        return versionIndex;
    }

    /**
     * @notice Rate tensor quality
     * @param tokenId Token ID to rate
     * @param rating Rating (1-100)
     */
    function rateTensor(uint256 tokenId, uint256 rating) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(rating >= 1 && rating <= 100, "Rating must be 1-100");
        require(!_hasRated[tokenId][msg.sender], "Already rated");

        _hasRated[tokenId][msg.sender] = true;
        _totalRatings[tokenId]++;
        _ratingSum[tokenId] += rating;

        uint256 averageRating = _ratingSum[tokenId] / _totalRatings[tokenId];

        emit THTensorRated(tokenId, msg.sender, rating);
    }

    // ==================== Getter Functions ====================

    function getTensorIdentity(uint256 tokenId)
        external
        view
        returns (TensorIdentity memory)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _identity[tokenId];
    }

    function getOptimizationMetadata(uint256 tokenId)
        external
        view
        returns (OptimizationMetadata memory)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _optimization[tokenId];
    }

    function getTensorFiles(uint256 tokenId)
        external
        view
        returns (TensorFiles memory)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _files[tokenId];
    }

    function getPerformanceMetrics(uint256 tokenId)
        external
        view
        returns (PerformanceMetrics memory)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _performance[tokenId];
    }

    function getTrainingProvenance(uint256 tokenId)
        external
        view
        returns (TrainingProvenance memory)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _provenance[tokenId];
    }

    function getVersionHistory(uint256 tokenId)
        external
        view
        returns (bytes32[] memory)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _versionHistory[tokenId];
    }

    function getVersion(uint256 tokenId, uint256 versionIndex)
        external
        view
        returns (bytes32)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(versionIndex < _versionHistory[tokenId].length, "Invalid version index");
        return _versionHistory[tokenId][versionIndex];
    }

    /**
     * @notice Get tensor rating
     * @param tokenId Token ID
     * @return averageRating Average rating (scaled by 100)
     * @return ratingCount Number of ratings
     */
    function getTensorRating(uint256 tokenId)
        external
        view
        returns (uint256 averageRating, uint256 ratingCount)
    {
        ratingCount = _totalRatings[tokenId];
        if (ratingCount == 0) {
            return (0, 0);
        }
        averageRating = (_ratingSum[tokenId] * 100) / ratingCount; // Scale by 100
        return (averageRating, ratingCount);
    }

    /**
     * @notice Check if tensor is public
     * @param tokenId Token ID
     * @return isPublic Whether tensor is public
     */
    function isPublicTensor(uint256 tokenId) external view returns (bool) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _isPublic[tokenId];
    }

    /**
     * @notice Get comprehensive tensor metadata
     * @param tokenId Token ID
     * @return identity Tensor identity
     * @return optimization Optimization metadata
     * @return files Tensor files
     * @return performance Performance metrics
     * @return provenance Training provenance
     */
    function getCompleteTensorData(uint256 tokenId)
        external
        view
        returns (
            TensorIdentity memory identity,
            OptimizationMetadata memory optimization,
            TensorFiles memory files,
            PerformanceMetrics memory performance,
            TrainingProvenance memory provenance
        )
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return (
            _identity[tokenId],
            _optimization[tokenId],
            _files[tokenId],
            _performance[tokenId],
            _provenance[tokenId]
        );
    }

    /**
     * @notice Get token ID by package CID
     * @param packageCID Package CID to look up
     * @return tokenId Token ID associated with CID
     */
    function getTokenIdByCID(bytes32 packageCID) external view returns (uint256) {
        require(_cidExists[packageCID], "CID does not exist");
        return _cidToTokenId[packageCID];
    }

    /**
     * @notice Check if CID exists
     * @param packageCID Package CID to check
     * @return exists Whether CID exists
     */
    function cidExists(bytes32 packageCID) external view returns (bool) {
        return _cidExists[packageCID];
    }

    /**
     * @notice Get total supply of tensors
     * @return totalSupply Total number of tensors minted
     */
    function totalSupply() external view returns (uint256) {
        return _tokenIdCounter - 1;
    }
}
