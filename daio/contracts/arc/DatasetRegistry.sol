// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DatasetRegistry
 * @notice Registry for datasets on ARC chain, mapping dataset IDs to IPFS CIDs
 * @dev Part of THOT-DAIO architecture for dataset marketplace
 */
contract DatasetRegistry {
    struct Dataset {
        bytes32 datasetId;
        string rootCID;           // IPFS manifest CID
        address creator;
        uint256 createdAt;
        uint256 version;
        bool isActive;
    }
    
    mapping(bytes32 => Dataset) public datasets;
    mapping(bytes32 => string[]) public versions;  // Version history
    mapping(address => bytes32[]) public creatorDatasets;  // Datasets by creator
    
    address public owner;
    uint256 public totalDatasets;
    
    event DatasetRegistered(bytes32 indexed datasetId, string rootCID, address creator, uint256 version);
    event DatasetVersioned(bytes32 indexed datasetId, string newRootCID, uint256 version);
    event DatasetDeactivated(bytes32 indexed datasetId);
    event DatasetActivated(bytes32 indexed datasetId);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @notice Register a new dataset
     * @param datasetId Unique identifier for the dataset
     * @param rootCID IPFS CID of the dataset manifest
     * @return success Whether registration was successful
     */
    function registerDataset(
        bytes32 datasetId,
        string memory rootCID
    ) external returns (bool) {
        require(datasets[datasetId].datasetId == bytes32(0), "Dataset already exists");
        require(bytes(rootCID).length > 0, "Invalid CID");
        
        datasets[datasetId] = Dataset({
            datasetId: datasetId,
            rootCID: rootCID,
            creator: msg.sender,
            createdAt: block.timestamp,
            version: 1,
            isActive: true
        });
        
        versions[datasetId].push(rootCID);
        creatorDatasets[msg.sender].push(datasetId);
        totalDatasets++;
        
        emit DatasetRegistered(datasetId, rootCID, msg.sender, 1);
        return true;
    }
    
    /**
     * @notice Create a new version of an existing dataset
     * @param datasetId Dataset identifier
     * @param newRootCID New IPFS CID for the updated dataset
     * @return newVersion The new version number
     */
    function versionDataset(
        bytes32 datasetId,
        string memory newRootCID
    ) external returns (uint256) {
        Dataset storage dataset = datasets[datasetId];
        require(dataset.creator == msg.sender, "Only creator can version");
        require(dataset.isActive, "Dataset not active");
        require(bytes(newRootCID).length > 0, "Invalid CID");
        
        dataset.version++;
        dataset.rootCID = newRootCID;
        versions[datasetId].push(newRootCID);
        
        emit DatasetVersioned(datasetId, newRootCID, dataset.version);
        return dataset.version;
    }
    
    /**
     * @notice Get dataset information
     * @param datasetId Dataset identifier
     * @return dataset Dataset struct
     */
    function getDataset(bytes32 datasetId) external view returns (Dataset memory) {
        return datasets[datasetId];
    }
    
    /**
     * @notice Get the latest version CID for a dataset
     * @param datasetId Dataset identifier
     * @return latestCID Latest version CID
     */
    function getLatestVersion(bytes32 datasetId) external view returns (string memory) {
        return datasets[datasetId].rootCID;
    }
    
    /**
     * @notice Get all versions of a dataset
     * @param datasetId Dataset identifier
     * @return versionCIDs Array of all version CIDs
     */
    function getAllVersions(bytes32 datasetId) external view returns (string[] memory) {
        return versions[datasetId];
    }
    
    /**
     * @notice Get datasets created by an address
     * @param creator Creator address
     * @return datasetIds Array of dataset IDs
     */
    function getCreatorDatasets(address creator) external view returns (bytes32[] memory) {
        return creatorDatasets[creator];
    }
    
    /**
     * @notice Deactivate a dataset (only creator or owner)
     * @param datasetId Dataset identifier
     */
    function deactivateDataset(bytes32 datasetId) external {
        Dataset storage dataset = datasets[datasetId];
        require(
            dataset.creator == msg.sender || msg.sender == owner,
            "Not authorized"
        );
        dataset.isActive = false;
        emit DatasetDeactivated(datasetId);
    }
    
    /**
     * @notice Reactivate a dataset (only creator or owner)
     * @param datasetId Dataset identifier
     */
    function activateDataset(bytes32 datasetId) external {
        Dataset storage dataset = datasets[datasetId];
        require(
            dataset.creator == msg.sender || msg.sender == owner,
            "Not authorized"
        );
        dataset.isActive = true;
        emit DatasetActivated(datasetId);
    }
}
