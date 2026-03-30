// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../daio/governance/KnowledgeHierarchyDAIO.sol";
import "../daio/constitution/DAIO_Constitution.sol";
import "../daio/treasury/Treasury.sol";
import "../DAIO_Core.sol";

/**
 * @title UniversalDAIO
 * @notice Meta-orchestrator for all DAIO configurations supporting complete configurability
 * @dev Enables deployment of any governance model from DictatorDAO to global federations
 */
contract UniversalDAIO is AccessControl, ReentrancyGuard {

    bytes32 public constant UNIVERSAL_ADMIN_ROLE = keccak256("UNIVERSAL_ADMIN_ROLE");
    bytes32 public constant DEPLOYMENT_ROLE = keccak256("DEPLOYMENT_ROLE");
    bytes32 public constant EVOLUTION_ROLE = keccak256("EVOLUTION_ROLE");
    bytes32 public constant CROSS_CHAIN_ROLE = keccak256("CROSS_CHAIN_ROLE");

    // Governance evolution stages
    enum GovernanceStage {
        DICTATOR,       // Single admin control
        MARRIAGE,       // Two-person consensus
        TRIUMVIRATE,    // Three-domain governance with AI
        CUSTOM,         // User-defined governance
        FEDERATION,     // Multi-chain coordination
        AUTONOMOUS      // AI-driven governance
    }

    // Chain deployment support
    enum ChainSupport {
        SINGLE,         // Single chain deployment
        MULTICHAIN,     // Multiple specific chains
        ALLCHAIN        // All compatible chains
    }

    // Voting asset types
    enum VotingAssetType {
        ERC20,          // Token-based voting
        ERC721,         // NFT-based voting
        ERC1155,        // Multi-token voting
        NATIVE,         // Native token voting
        HYBRID,         // Multiple asset types
        REPUTATION      // Reputation-based voting
    }

    // Universal configuration structure
    struct UniversalConfig {
        string name;                    // DAIO name
        GovernanceStage currentStage;   // Current governance stage
        GovernanceStage targetStage;    // Target evolution stage
        ChainSupport chainSupport;      // Multi-chain support level
        address admin;                  // Primary admin
        address[] secondaryAdmins;      // Additional admins for multi-sig
        bool evolutionEnabled;          // Can evolve governance
        bool aiIntegrationEnabled;      // AI participation allowed
        uint256 createdAt;             // Creation timestamp
        bytes32 configHash;            // Configuration hash for verification
    }

    // Governance stage specific configuration
    struct StageConfig {
        GovernanceStage stage;
        mapping(string => uint256) parameters;    // Stage-specific parameters
        mapping(string => address) contracts;     // Stage-specific contracts
        mapping(string => bool) features;         // Stage-specific features
        address[] requiredRoles;                  // Required admin roles
        uint256 multiSigThreshold;               // Multi-signature threshold
        bool crossChainEnabled;                  // Cross-chain coordination
    }

    // Evolution trigger configuration
    struct EvolutionTrigger {
        uint256 timeThreshold;          // Time-based trigger (seconds)
        uint256 valueThreshold;         // Treasury value trigger (wei)
        uint256 memberThreshold;        // Member count trigger
        uint256 proposalThreshold;      // Proposal count trigger
        uint256 activityThreshold;      // Activity level trigger
        bool communityVeto;             // Community can block evolution
        bool adminOverride;             // Admin can force evolution
        bool autoExecute;               // Automatic evolution when triggered
    }

    // Multi-chain configuration
    struct MultiChainConfig {
        uint256[] supportedChains;      // Supported chain IDs
        mapping(uint256 => address) chainDeployments; // Chain => DAIO address
        mapping(uint256 => uint256) chainWeights;     // Chain voting weights
        mapping(uint256 => bool) chainActive;         // Chain status
        uint256 primaryChain;           // Primary chain for coordination
        bool crossChainVoting;          // Cross-chain voting enabled
        uint256 crossChainDelay;        // Cross-chain execution delay
    }

    // Voting asset configuration
    struct VotingAssetConfig {
        VotingAssetType assetType;      // Type of voting asset
        address contractAddress;        // Asset contract address
        uint256 votingWeight;          // Weight multiplier
        uint256 minHolding;            // Minimum holding to vote
        uint256 lockDuration;          // Required lock duration
        bool delegationAllowed;        // Delegation enabled
        bool crossChainEnabled;        // Cross-chain asset support
    }

    // Storage
    mapping(uint256 => UniversalConfig) public universalConfigs;
    mapping(uint256 => StageConfig) public stageConfigs;
    mapping(uint256 => EvolutionTrigger) public evolutionTriggers;
    mapping(uint256 => MultiChainConfig) public multiChainConfigs;
    mapping(uint256 => VotingAssetConfig[]) public votingAssets;
    mapping(uint256 => address) public deployedDAIOs;
    mapping(address => uint256) public daoToConfigId;
    mapping(address => bool) public authorizedDeployers;

    uint256 public configCount;
    uint256 public totalDeployments;

    // Default configurations for quick deployment
    mapping(GovernanceStage => StageConfig) public defaultStageConfigs;

    // Events
    event UniversalDAIODeployed(
        uint256 indexed configId,
        address indexed daoAddress,
        GovernanceStage stage,
        address indexed deployer
    );

    event GovernanceEvolved(
        uint256 indexed configId,
        GovernanceStage oldStage,
        GovernanceStage newStage,
        address trigger
    );

    event CrossChainDeployment(
        uint256 indexed configId,
        uint256[] chains,
        address[] deployments
    );

    event ConfigurationUpdated(
        uint256 indexed configId,
        string parameter,
        uint256 oldValue,
        uint256 newValue
    );

    event EvolutionTriggerMet(
        uint256 indexed configId,
        string triggerType,
        uint256 currentValue,
        uint256 threshold
    );

    event MultiSigEnabled(
        uint256 indexed configId,
        address[] signers,
        uint256 threshold
    );

    modifier onlyUniversalAdmin() {
        require(hasRole(UNIVERSAL_ADMIN_ROLE, msg.sender), "Not universal admin");
        _;
    }

    modifier onlyAuthorizedDeployer() {
        require(authorizedDeployers[msg.sender] || hasRole(DEPLOYMENT_ROLE, msg.sender), "Not authorized deployer");
        _;
    }

    modifier validConfig(uint256 configId) {
        require(configId > 0 && configId <= configCount, "Invalid config ID");
        _;
    }

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(UNIVERSAL_ADMIN_ROLE, msg.sender);
        _grantRole(DEPLOYMENT_ROLE, msg.sender);
        _grantRole(EVOLUTION_ROLE, msg.sender);
        _grantRole(CROSS_CHAIN_ROLE, msg.sender);

        authorizedDeployers[msg.sender] = true;

        _initializeDefaultConfigurations();
    }

    /**
     * @notice Deploy Universal DAIO with complete configuration
     * @param config Universal configuration
     * @param evolutionTrigger Evolution trigger configuration
     * @param votingAssetConfigs Voting asset configurations
     * @param targetChains Target chains for deployment
     * @return configId Configuration ID
     * @return daoAddress Primary DAIO address
     */
    function deployUniversalDAIO(
        UniversalConfig memory config,
        EvolutionTrigger memory evolutionTrigger,
        VotingAssetConfig[] memory votingAssetConfigs,
        uint256[] memory targetChains
    ) external onlyAuthorizedDeployer nonReentrant returns (uint256 configId, address daoAddress) {
        require(bytes(config.name).length > 0, "Name required");
        require(config.admin != address(0), "Admin required");

        configCount++;
        configId = configCount;
        totalDeployments++;

        // Store universal configuration
        config.createdAt = block.timestamp;
        config.configHash = keccak256(abi.encode(config, evolutionTrigger, block.timestamp));
        universalConfigs[configId] = config;

        // Store evolution trigger
        evolutionTriggers[configId] = evolutionTrigger;

        // Store voting assets
        for (uint i = 0; i < votingAssetConfigs.length; i++) {
            votingAssets[configId].push(votingAssetConfigs[i]);
        }

        // Configure stage-specific settings
        _configureStage(configId, config.currentStage);

        // Deploy primary DAIO
        daoAddress = _deployStageDAIO(configId, config.currentStage);
        deployedDAIOs[configId] = daoAddress;
        daoToConfigId[daoAddress] = configId;

        // Configure multi-chain if specified
        if (config.chainSupport != ChainSupport.SINGLE && targetChains.length > 0) {
            _configureCrossChain(configId, targetChains, daoAddress);
        }

        emit UniversalDAIODeployed(configId, daoAddress, config.currentStage, msg.sender);
        return (configId, daoAddress);
    }

    /**
     * @notice Deploy DictatorDAO with single admin
     * @param admin Admin address
     * @param name DAIO name
     * @param evolutionTrigger Evolution configuration
     * @return configId Configuration ID
     * @return daoAddress DAIO address
     */
    function deployDictatorDAO(
        address admin,
        string memory name,
        EvolutionTrigger memory evolutionTrigger
    ) external onlyAuthorizedDeployer returns (uint256 configId, address daoAddress) {
        UniversalConfig memory config = UniversalConfig({
            name: name,
            currentStage: GovernanceStage.DICTATOR,
            targetStage: GovernanceStage.MARRIAGE,
            chainSupport: ChainSupport.SINGLE,
            admin: admin,
            secondaryAdmins: new address[](0),
            evolutionEnabled: true,
            aiIntegrationEnabled: false,
            createdAt: block.timestamp,
            configHash: bytes32(0)
        });

        VotingAssetConfig[] memory assets = new VotingAssetConfig[](1);
        assets[0] = VotingAssetConfig({
            assetType: VotingAssetType.NATIVE,
            contractAddress: address(0),
            votingWeight: 100,
            minHolding: 0.01 ether,
            lockDuration: 0,
            delegationAllowed: false,
            crossChainEnabled: false
        });

        uint256[] memory chains = new uint256[](0);

        return deployUniversalDAIO(config, evolutionTrigger, assets, chains);
    }

    /**
     * @notice Deploy MarriageDAO with two-person governance
     * @param partner1 First partner address
     * @param partner2 Second partner address
     * @param name DAIO name
     * @param weights Voting weights [partner1, partner2]
     * @return configId Configuration ID
     * @return daoAddress DAIO address
     */
    function deployMarriageDAO(
        address partner1,
        address partner2,
        string memory name,
        uint256[2] memory weights
    ) external onlyAuthorizedDeployer returns (uint256 configId, address daoAddress) {
        require(partner1 != address(0) && partner2 != address(0), "Invalid partners");
        require(weights[0] + weights[1] == 100, "Weights must sum to 100");

        address[] memory admins = new address[](2);
        admins[0] = partner1;
        admins[1] = partner2;

        UniversalConfig memory config = UniversalConfig({
            name: name,
            currentStage: GovernanceStage.MARRIAGE,
            targetStage: GovernanceStage.TRIUMVIRATE,
            chainSupport: ChainSupport.SINGLE,
            admin: partner1, // Primary admin
            secondaryAdmins: admins,
            evolutionEnabled: true,
            aiIntegrationEnabled: false,
            createdAt: block.timestamp,
            configHash: bytes32(0)
        });

        EvolutionTrigger memory trigger = EvolutionTrigger({
            timeThreshold: 90 days,
            valueThreshold: 500 ether,
            memberThreshold: 100,
            proposalThreshold: 50,
            activityThreshold: 1000,
            communityVeto: true,
            adminOverride: true,
            autoExecute: false
        });

        VotingAssetConfig[] memory assets = new VotingAssetConfig[](1);
        assets[0] = VotingAssetConfig({
            assetType: VotingAssetType.NATIVE,
            contractAddress: address(0),
            votingWeight: 100,
            minHolding: 0.1 ether,
            lockDuration: 7 days,
            delegationAllowed: true,
            crossChainEnabled: false
        });

        uint256[] memory chains = new uint256[](0);

        (configId, daoAddress) = deployUniversalDAIO(config, trigger, assets, chains);

        // Store marriage-specific weights in stage config
        stageConfigs[configId].parameters["partner1_weight"] = weights[0];
        stageConfigs[configId].parameters["partner2_weight"] = weights[1];
    }

    /**
     * @notice Deploy TriumvirateDAO with Dev/Com/Mark governance
     * @param dev Development domain lead
     * @param community Community domain lead
     * @param marketing Marketing domain lead
     * @param name DAIO name
     * @param enableAI Enable AI voting integration
     * @return configId Configuration ID
     * @return daoAddress DAIO address
     */
    function deployTriumvirateDAO(
        address dev,
        address community,
        address marketing,
        string memory name,
        bool enableAI
    ) external onlyAuthorizedDeployer returns (uint256 configId, address daoAddress) {
        require(dev != address(0) && community != address(0) && marketing != address(0), "Invalid addresses");

        address[] memory admins = new address[](3);
        admins[0] = dev;
        admins[1] = community;
        admins[2] = marketing;

        UniversalConfig memory config = UniversalConfig({
            name: name,
            currentStage: GovernanceStage.TRIUMVIRATE,
            targetStage: GovernanceStage.FEDERATION,
            chainSupport: ChainSupport.MULTICHAIN,
            admin: dev, // Primary admin
            secondaryAdmins: admins,
            evolutionEnabled: true,
            aiIntegrationEnabled: enableAI,
            createdAt: block.timestamp,
            configHash: bytes32(0)
        });

        EvolutionTrigger memory trigger = EvolutionTrigger({
            timeThreshold: 180 days,
            valueThreshold: 1000 ether,
            memberThreshold: 500,
            proposalThreshold: 200,
            activityThreshold: 5000,
            communityVeto: true,
            adminOverride: false, // No admin override for triumvirate
            autoExecute: false
        });

        VotingAssetConfig[] memory assets = new VotingAssetConfig[](1);
        assets[0] = VotingAssetConfig({
            assetType: VotingAssetType.HYBRID,
            contractAddress: address(0),
            votingWeight: 100,
            minHolding: 1 ether,
            lockDuration: 30 days,
            delegationAllowed: true,
            crossChainEnabled: true
        });

        uint256[] memory chains = new uint256[](0);

        (configId, daoAddress) = deployUniversalDAIO(config, trigger, assets, chains);

        // Store triumvirate-specific configuration
        stageConfigs[configId].parameters["dev_weight"] = 33;
        stageConfigs[configId].parameters["community_weight"] = 34;
        stageConfigs[configId].parameters["marketing_weight"] = 33;
        stageConfigs[configId].parameters["ai_voting_weight"] = enableAI ? 33 : 0;
        stageConfigs[configId].parameters["consensus_threshold"] = 67;
    }

    /**
     * @notice Evolve governance to next stage
     * @param configId Configuration ID
     * @param forced Force evolution (admin override)
     */
    function evolveGovernance(uint256 configId, bool forced) external validConfig(configId) {
        UniversalConfig storage config = universalConfigs[configId];
        require(config.evolutionEnabled, "Evolution disabled");

        if (!forced) {
            require(_checkEvolutionTriggers(configId), "Evolution triggers not met");
        } else {
            require(hasRole(EVOLUTION_ROLE, msg.sender), "Not authorized to force evolution");
            EvolutionTrigger storage trigger = evolutionTriggers[configId];
            require(trigger.adminOverride, "Admin override disabled");
        }

        GovernanceStage oldStage = config.currentStage;
        GovernanceStage newStage = config.targetStage;

        config.currentStage = newStage;

        // Set next target stage
        if (newStage == GovernanceStage.DICTATOR) {
            config.targetStage = GovernanceStage.MARRIAGE;
        } else if (newStage == GovernanceStage.MARRIAGE) {
            config.targetStage = GovernanceStage.TRIUMVIRATE;
        } else if (newStage == GovernanceStage.TRIUMVIRATE) {
            config.targetStage = GovernanceStage.FEDERATION;
        }

        // Reconfigure for new stage
        _configureStage(configId, newStage);

        emit GovernanceEvolved(configId, oldStage, newStage, msg.sender);
    }

    /**
     * @notice Enable multi-signature for configuration
     * @param configId Configuration ID
     * @param signers Signer addresses
     * @param threshold Required signatures
     */
    function enableMultiSig(
        uint256 configId,
        address[] memory signers,
        uint256 threshold
    ) external validConfig(configId) onlyUniversalAdmin {
        require(signers.length >= threshold && threshold > 0, "Invalid threshold");

        StageConfig storage stageConfig = stageConfigs[configId];
        stageConfig.multiSigThreshold = threshold;

        UniversalConfig storage config = universalConfigs[configId];
        config.secondaryAdmins = signers;

        emit MultiSigEnabled(configId, signers, threshold);
    }

    /**
     * @notice Update configuration parameter
     * @param configId Configuration ID
     * @param parameter Parameter name
     * @param newValue New parameter value
     */
    function updateParameter(
        uint256 configId,
        string memory parameter,
        uint256 newValue
    ) external validConfig(configId) {
        require(_hasParameterAccess(configId, msg.sender), "Not authorized");

        StageConfig storage stageConfig = stageConfigs[configId];
        uint256 oldValue = stageConfig.parameters[parameter];
        stageConfig.parameters[parameter] = newValue;

        emit ConfigurationUpdated(configId, parameter, oldValue, newValue);
    }

    /**
     * @notice Get configuration details
     * @param configId Configuration ID
     * @return Universal configuration
     */
    function getConfiguration(uint256 configId) external view validConfig(configId) returns (UniversalConfig memory) {
        return universalConfigs[configId];
    }

    /**
     * @notice Get stage parameter
     * @param configId Configuration ID
     * @param parameter Parameter name
     * @return Parameter value
     */
    function getParameter(uint256 configId, string memory parameter) external view validConfig(configId) returns (uint256) {
        return stageConfigs[configId].parameters[parameter];
    }

    /**
     * @notice Check if evolution triggers are met
     * @param configId Configuration ID
     * @return Whether triggers are met
     */
    function checkEvolutionTriggers(uint256 configId) external view validConfig(configId) returns (bool) {
        return _checkEvolutionTriggers(configId);
    }

    /**
     * @notice Get voting assets for configuration
     * @param configId Configuration ID
     * @return Array of voting asset configurations
     */
    function getVotingAssets(uint256 configId) external view validConfig(configId) returns (VotingAssetConfig[] memory) {
        return votingAssets[configId];
    }

    /**
     * @notice Configure stage-specific settings
     * @param configId Configuration ID
     * @param stage Governance stage
     */
    function _configureStage(uint256 configId, GovernanceStage stage) internal {
        StageConfig storage stageConfig = stageConfigs[configId];
        stageConfig.stage = stage;

        if (stage == GovernanceStage.DICTATOR) {
            stageConfig.parameters["voting_threshold"] = 100; // 100% (dictator decides)
            stageConfig.parameters["voting_period"] = 1 days;
            stageConfig.parameters["proposal_threshold"] = 0.01 ether;
            stageConfig.parameters["multisig_threshold"] = 1;
            stageConfig.features["emergency_powers"] = true;
            stageConfig.features["ai_integration"] = false;
        } else if (stage == GovernanceStage.MARRIAGE) {
            stageConfig.parameters["voting_threshold"] = 51; // Simple majority between partners
            stageConfig.parameters["voting_period"] = 3 days;
            stageConfig.parameters["proposal_threshold"] = 0.1 ether;
            stageConfig.parameters["multisig_threshold"] = 2;
            stageConfig.features["deadlock_resolution"] = true;
            stageConfig.features["ai_integration"] = false;
        } else if (stage == GovernanceStage.TRIUMVIRATE) {
            stageConfig.parameters["voting_threshold"] = 67; // 2/3 consensus
            stageConfig.parameters["voting_period"] = 7 days;
            stageConfig.parameters["proposal_threshold"] = 1 ether;
            stageConfig.parameters["multisig_threshold"] = 2;
            stageConfig.parameters["ai_voting_weight"] = 33;
            stageConfig.features["ai_integration"] = true;
            stageConfig.features["self_extending"] = true;
            stageConfig.features["economic_incentives"] = true;
        }
    }

    /**
     * @notice Deploy DAIO for specific governance stage
     * @param configId Configuration ID
     * @param stage Governance stage
     * @return daoAddress Deployed DAIO address
     */
    function _deployStageDAIO(uint256 configId, GovernanceStage stage) internal returns (address daoAddress) {
        UniversalConfig memory config = universalConfigs[configId];

        // Deploy appropriate DAIO type based on stage
        if (stage == GovernanceStage.DICTATOR || stage == GovernanceStage.MARRIAGE) {
            // Deploy basic DAIO with single/dual admin
            DAIO_Core daio = new DAIO_Core();
            daio.deployDAIOCore(
                config.name,
                config.admin, // Chairman
                config.admin, // CEO (same as admin for dictator)
                config.configHash
            );
            return address(daio);
        } else {
            // Deploy enhanced DAIO with full capabilities
            DAIO_Core daio = new DAIO_Core();
            daio.deployDAIOCore(
                config.name,
                config.admin,
                config.admin,
                config.configHash
            );
            return address(daio);
        }
    }

    /**
     * @notice Configure cross-chain deployment
     * @param configId Configuration ID
     * @param targetChains Target chain IDs
     * @param primaryDAO Primary DAO address
     */
    function _configureCrossChain(
        uint256 configId,
        uint256[] memory targetChains,
        address primaryDAO
    ) internal {
        MultiChainConfig storage multiChain = multiChainConfigs[configId];
        multiChain.supportedChains = targetChains;
        multiChain.primaryChain = block.chainid;
        multiChain.chainDeployments[block.chainid] = primaryDAO;
        multiChain.chainActive[block.chainid] = true;
        multiChain.crossChainVoting = true;

        // Equal weight for all chains initially
        uint256 weightPerChain = 100 / targetChains.length;
        for (uint i = 0; i < targetChains.length; i++) {
            multiChain.chainWeights[targetChains[i]] = weightPerChain;
        }
    }

    /**
     * @notice Check if evolution triggers are met
     * @param configId Configuration ID
     * @return Whether all required triggers are met
     */
    function _checkEvolutionTriggers(uint256 configId) internal view returns (bool) {
        EvolutionTrigger memory trigger = evolutionTriggers[configId];
        UniversalConfig memory config = universalConfigs[configId];

        // Time trigger
        if (trigger.timeThreshold > 0 && block.timestamp < config.createdAt + trigger.timeThreshold) {
            return false;
        }

        // Value trigger (would need treasury integration)
        if (trigger.valueThreshold > 0) {
            // Simplified check - would integrate with actual treasury
            // return treasuryValue >= trigger.valueThreshold;
        }

        // Member trigger (would need member count integration)
        // Proposal trigger (would need proposal count integration)
        // Activity trigger (would need activity metrics integration)

        return true; // Simplified for now
    }

    /**
     * @notice Check if address has parameter access
     * @param configId Configuration ID
     * @param account Account to check
     * @return Whether account has access
     */
    function _hasParameterAccess(uint256 configId, address account) internal view returns (bool) {
        UniversalConfig memory config = universalConfigs[configId];

        if (account == config.admin) return true;
        if (hasRole(UNIVERSAL_ADMIN_ROLE, account)) return true;

        // Check if account is in secondary admins
        for (uint i = 0; i < config.secondaryAdmins.length; i++) {
            if (config.secondaryAdmins[i] == account) return true;
        }

        return false;
    }

    /**
     * @notice Initialize default configurations for each stage
     */
    function _initializeDefaultConfigurations() internal {
        // Default configurations would be set up here for quick deployment
        // This is simplified for the initial implementation
    }

    /**
     * @notice Authorize deployer
     * @param deployer Address to authorize
     */
    function authorizeDeployer(address deployer) external onlyUniversalAdmin {
        authorizedDeployers[deployer] = true;
    }

    /**
     * @notice Revoke deployer authorization
     * @param deployer Address to revoke
     */
    function revokeDeployer(address deployer) external onlyUniversalAdmin {
        authorizedDeployers[deployer] = false;
    }
}