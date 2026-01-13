// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ProviderRegistry
 * @notice Registry for dataset providers (alive agents) on ARC chain
 * @dev Part of THOT-DAIO architecture for dataset marketplace
 */
contract ProviderRegistry {
    struct Provider {
        address providerAddress;
        string peerId;              // IPFS peer ID
        string endpoint;            // Service endpoint
        uint256 stake;              // Collateral/stake
        uint256 reputation;         // Reputation score (0-10000)
        uint256 successRate;        // Challenge success rate (basis points)
        uint256 medianLatency;      // Median retrieval latency (ms)
        uint256 totalChallenges;    // Total challenges received
        uint256 successfulChallenges; // Successful challenge responses
        bool isActive;
        uint256 registeredAt;
    }
    
    mapping(address => Provider) public providers;
    mapping(address => bytes32[]) public providerDatasets;  // CIDs this provider serves
    mapping(bytes32 => address[]) public datasetProviders;  // Providers serving a dataset
    
    address public owner;
    address public challengeManager;  // ChallengeManager contract address
    uint256 public totalProviders;
    
    event ProviderRegistered(address indexed provider, string peerId, string endpoint, uint256 stake);
    event ProviderStakeUpdated(address indexed provider, uint256 newStake);
    event ProviderReputationUpdated(address indexed provider, uint256 newReputation);
    event ProviderEndpointUpdated(address indexed provider, string newEndpoint);
    event ProviderDeactivated(address indexed provider);
    event DatasetAdded(address indexed provider, bytes32 rootCID);
    event DatasetRemoved(address indexed provider, bytes32 rootCID);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    modifier onlyChallengeManager() {
        require(msg.sender == challengeManager, "Only ChallengeManager");
        _;
    }
    
    modifier onlyProvider() {
        require(providers[msg.sender].isActive, "Not a registered provider");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @notice Set ChallengeManager contract address
     * @param _challengeManager ChallengeManager contract address
     */
    function setChallengeManager(address _challengeManager) external onlyOwner {
        challengeManager = _challengeManager;
    }
    
    /**
     * @notice Register as a dataset provider
     * @param peerId IPFS peer ID
     * @param endpoint Service endpoint URL
     * @return success Whether registration was successful
     */
    function registerProvider(
        string memory peerId,
        string memory endpoint,
        uint256 initialStake
    ) external payable returns (bool) {
        require(!providers[msg.sender].isActive, "Already registered");
        require(msg.value >= initialStake, "Insufficient stake");
        require(bytes(peerId).length > 0, "Invalid peer ID");
        require(bytes(endpoint).length > 0, "Invalid endpoint");
        
        providers[msg.sender] = Provider({
            providerAddress: msg.sender,
            peerId: peerId,
            endpoint: endpoint,
            stake: initialStake,
            reputation: 5000,  // Start at 50% reputation
            successRate: 0,
            medianLatency: 0,
            totalChallenges: 0,
            successfulChallenges: 0,
            isActive: true,
            registeredAt: block.timestamp
        });
        
        totalProviders++;
        emit ProviderRegistered(msg.sender, peerId, endpoint, initialStake);
        return true;
    }
    
    /**
     * @notice Update provider endpoint
     * @param endpoint New endpoint URL
     */
    function updateProviderEndpoint(string memory endpoint) external onlyProvider {
        require(bytes(endpoint).length > 0, "Invalid endpoint");
        providers[msg.sender].endpoint = endpoint;
        emit ProviderEndpointUpdated(msg.sender, endpoint);
    }
    
    /**
     * @notice Add a dataset that this provider serves
     * @param rootCID Dataset root CID
     */
    function addDataset(bytes32 rootCID) external onlyProvider {
        bytes32[] storage datasets = providerDatasets[msg.sender];
        
        // Check if already added
        for (uint256 i = 0; i < datasets.length; i++) {
            require(datasets[i] != rootCID, "Dataset already added");
        }
        
        datasets.push(rootCID);
        datasetProviders[rootCID].push(msg.sender);
        emit DatasetAdded(msg.sender, rootCID);
    }
    
    /**
     * @notice Remove a dataset from provider's list
     * @param rootCID Dataset root CID
     */
    function removeDataset(bytes32 rootCID) external onlyProvider {
        bytes32[] storage datasets = providerDatasets[msg.sender];
        bool found = false;
        
        for (uint256 i = 0; i < datasets.length; i++) {
            if (datasets[i] == rootCID) {
                datasets[i] = datasets[datasets.length - 1];
                datasets.pop();
                found = true;
                break;
            }
        }
        
        require(found, "Dataset not found");
        
        // Remove from datasetProviders mapping
        address[] storage providers_list = datasetProviders[rootCID];
        for (uint256 i = 0; i < providers_list.length; i++) {
            if (providers_list[i] == msg.sender) {
                providers_list[i] = providers_list[providers_list.length - 1];
                providers_list.pop();
                break;
            }
        }
        
        emit DatasetRemoved(msg.sender, rootCID);
    }
    
    /**
     * @notice Update provider reputation (called by ChallengeManager)
     * @param provider Provider address
     * @param successRate Challenge success rate (basis points)
     * @param medianLatency Median retrieval latency (ms)
     */
    function updateReputation(
        address provider,
        uint256 successRate,
        uint256 medianLatency
    ) external onlyChallengeManager {
        Provider storage p = providers[provider];
        require(p.isActive, "Provider not active");
        
        p.successRate = successRate;
        p.medianLatency = medianLatency;
        
        // Calculate reputation based on success rate and latency
        // Higher success rate = higher reputation
        // Lower latency = higher reputation
        uint256 baseReputation = successRate;  // 0-10000 basis points
        uint256 latencyBonus = medianLatency < 1000 ? (1000 - medianLatency) / 10 : 0;  // Bonus for low latency
        p.reputation = baseReputation + latencyBonus;
        if (p.reputation > 10000) p.reputation = 10000;  // Cap at 10000
        
        emit ProviderReputationUpdated(provider, p.reputation);
    }
    
    /**
     * @notice Record a challenge result
     * @param provider Provider address
     * @param success Whether challenge was successful
     */
    function recordChallenge(address provider, bool success) external onlyChallengeManager {
        Provider storage p = providers[provider];
        p.totalChallenges++;
        if (success) {
            p.successfulChallenges++;
        }
        
        // Update success rate
        if (p.totalChallenges > 0) {
            p.successRate = (p.successfulChallenges * 10000) / p.totalChallenges;
        }
    }
    
    /**
     * @notice Update provider stake
     * @param newStake New stake amount
     */
    function updateStake(uint256 newStake) external payable onlyProvider {
        Provider storage p = providers[msg.sender];
        if (newStake > p.stake) {
            require(msg.value >= (newStake - p.stake), "Insufficient payment");
        }
        p.stake = newStake;
        emit ProviderStakeUpdated(msg.sender, newStake);
    }
    
    /**
     * @notice Deactivate a provider
     */
    function deactivateProvider() external onlyProvider {
        providers[msg.sender].isActive = false;
        emit ProviderDeactivated(msg.sender);
    }
    
    /**
     * @notice Get providers serving a dataset
     * @param rootCID Dataset root CID
     * @return providerAddresses Array of provider addresses
     */
    function getDatasetProviders(bytes32 rootCID) external view returns (address[] memory) {
        return datasetProviders[rootCID];
    }
    
    /**
     * @notice Get datasets served by a provider
     * @param provider Provider address
     * @return datasetCIDs Array of dataset CIDs
     */
    function getProviderDatasets(address provider) external view returns (bytes32[] memory) {
        return providerDatasets[provider];
    }
}
