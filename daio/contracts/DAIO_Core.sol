// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./daio/governance/ExecutiveGovernance.sol";
import "./daio/governance/ExecutiveRoles.sol";
import "./daio/governance/WeightedVotingEngine.sol";
import "./daio/governance/EmergencyTimelock.sol";
import "./daio/governance/KnowledgeHierarchyDAIO.sol";
import "./daio/constitution/DAIO_Constitution_Enhanced.sol";
import "./daio/treasury/Treasury.sol";
import "./daio/settings/GovernanceSettings.sol";
import "./daio/governance/AgentFactory.sol";
import "./daio/identity/IDNFT.sol";

/**
 * @title DAIO_Core
 * @notice Core DAIO deployment orchestrator and registry
 * @dev Minimal viable DAIO deployment with CEO + Seven Soldiers governance
 * @dev Extensions can be added modularly without affecting core functionality
 */
contract DAIO_Core {

    // Version and metadata
    string public constant VERSION = "1.0.0";
    string public constant NAME = "Decentralized Autonomous Intelligence Organization";

    // Core component registry
    struct CoreComponents {
        address constitution;           // Enhanced configurable constitution
        address executiveRoles;        // CEO + Seven Soldiers management
        address votingEngine;          // Weighted consensus engine
        address emergencyTimelock;     // CEO emergency powers
        address executiveGovernance;   // Main governance orchestrator
        address knowledgeHierarchy;    // AI agent voting
        address treasury;              // Multi-project treasury
        address settings;              // Governance parameters
        address agentFactory;          // Agent identity creation
        address idNFT;                 // Identity NFT system
    }

    // Deployment status
    struct DeploymentInfo {
        bool initialized;
        address deployer;
        uint256 deployedAt;
        bytes32 configHash;           // Hash of deployment configuration
        string deploymentName;        // Human-readable deployment name
    }

    // Extension registry
    struct Extension {
        string name;
        string description;
        address contractAddress;
        bool active;
        uint256 addedAt;
        string category;              // "marketplace", "nft", "defi", "analytics"
    }

    // Core state
    CoreComponents public core;
    DeploymentInfo public deployment;
    Extension[] public extensions;
    mapping(string => address) public extensionsByName;
    mapping(string => Extension[]) public extensionsByCategory;

    // Access control
    address public admin;
    address public executiveGovernance; // Can add/remove extensions
    mapping(address => bool) public authorizedDeployers;

    // Events
    event DAIODeployed(
        address indexed deployer,
        string deploymentName,
        bytes32 configHash,
        uint256 timestamp
    );

    event ExtensionAdded(
        string indexed name,
        address indexed contractAddress,
        string category
    );

    event ExtensionRemoved(string indexed name);

    event ComponentUpgraded(
        string componentName,
        address oldAddress,
        address newAddress
    );

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    modifier onlyExecutiveGovernance() {
        require(msg.sender == executiveGovernance, "Only executive governance");
        _;
    }

    modifier onlyInitialized() {
        require(deployment.initialized, "DAIO not initialized");
        _;
    }

    constructor() {
        admin = msg.sender;
        authorizedDeployers[msg.sender] = true;
    }

    /**
     * @notice Deploy minimal viable DAIO core system
     * @param deploymentName Human-readable name for this DAIO instance
     * @param chairman Chairman address for constitution
     * @param ceoAddress CEO address for executive roles
     * @param config Deployment configuration parameters
     * @return success Whether deployment succeeded
     */
    function deployDAIOCore(
        string memory deploymentName,
        address chairman,
        address ceoAddress,
        bytes32 config
    ) external returns (bool success) {
        require(!deployment.initialized, "Already initialized");
        require(authorizedDeployers[msg.sender], "Not authorized deployer");
        require(chairman != address(0) && ceoAddress != address(0), "Invalid addresses");

        // Deploy core components in dependency order
        success = _deployCoreDependencies(chairman, ceoAddress);

        if (success) {
            deployment = DeploymentInfo({
                initialized: true,
                deployer: msg.sender,
                deployedAt: block.timestamp,
                configHash: config,
                deploymentName: deploymentName
            });

            executiveGovernance = core.executiveGovernance;

            emit DAIODeployed(msg.sender, deploymentName, config, block.timestamp);
        }
    }

    /**
     * @notice Add extension to DAIO ecosystem
     * @param name Extension name
     * @param description Extension description
     * @param contractAddress Extension contract address
     * @param category Extension category
     */
    function addExtension(
        string memory name,
        string memory description,
        address contractAddress,
        string memory category
    ) external onlyExecutiveGovernance onlyInitialized {
        require(contractAddress != address(0), "Invalid contract address");
        require(extensionsByName[name] == address(0), "Extension already exists");

        Extension memory newExtension = Extension({
            name: name,
            description: description,
            contractAddress: contractAddress,
            active: true,
            addedAt: block.timestamp,
            category: category
        });

        extensions.push(newExtension);
        extensionsByName[name] = contractAddress;
        extensionsByCategory[category].push(newExtension);

        emit ExtensionAdded(name, contractAddress, category);
    }

    /**
     * @notice Remove extension from DAIO ecosystem
     * @param name Extension name to remove
     */
    function removeExtension(string memory name) external onlyExecutiveGovernance {
        address extensionAddress = extensionsByName[name];
        require(extensionAddress != address(0), "Extension doesn't exist");

        // Mark as inactive (preserve for historical record)
        for (uint i = 0; i < extensions.length; i++) {
            if (keccak256(abi.encodePacked(extensions[i].name)) == keccak256(abi.encodePacked(name))) {
                extensions[i].active = false;
                break;
            }
        }

        delete extensionsByName[name];
        emit ExtensionRemoved(name);
    }

    /**
     * @notice Get all active extensions in a category
     * @param category Category to query
     * @return activeExtensions Array of active extensions
     */
    function getExtensionsByCategory(string memory category) external view returns (Extension[] memory activeExtensions) {
        Extension[] memory categoryExtensions = extensionsByCategory[category];
        uint activeCount = 0;

        // Count active extensions
        for (uint i = 0; i < categoryExtensions.length; i++) {
            if (categoryExtensions[i].active) activeCount++;
        }

        activeExtensions = new Extension[](activeCount);
        uint index = 0;

        // Populate active extensions
        for (uint i = 0; i < categoryExtensions.length; i++) {
            if (categoryExtensions[i].active) {
                activeExtensions[index] = categoryExtensions[i];
                index++;
            }
        }
    }

    /**
     * @notice Get comprehensive DAIO system status
     * @return coreComponents Core system components
     * @return deploymentInfo Deployment information
     * @return totalExtensions Total number of extensions
     * @return activeExtensions Number of active extensions
     */
    function getDAIOStatus() external view returns (
        CoreComponents memory coreComponents,
        DeploymentInfo memory deploymentInfo,
        uint256 totalExtensions,
        uint256 activeExtensions
    ) {
        coreComponents = core;
        deploymentInfo = deployment;
        totalExtensions = extensions.length;

        for (uint i = 0; i < extensions.length; i++) {
            if (extensions[i].active) activeExtensions++;
        }
    }

    /**
     * @notice Check if DAIO has specific extension
     * @param name Extension name
     * @return exists Whether extension exists and is active
     */
    function hasExtension(string memory name) external view returns (bool exists) {
        address extensionAddress = extensionsByName[name];
        if (extensionAddress == address(0)) return false;

        // Check if extension is still active
        for (uint i = 0; i < extensions.length; i++) {
            if (keccak256(abi.encodePacked(extensions[i].name)) == keccak256(abi.encodePacked(name))) {
                return extensions[i].active;
            }
        }
        return false;
    }

    /**
     * @notice Get minimal DAIO deployment requirements
     * @return requirements Array of requirement descriptions
     */
    function getDeploymentRequirements() external pure returns (string[] memory requirements) {
        requirements = new string[](5);
        requirements[0] = "Chairman address for constitutional authority";
        requirements[1] = "CEO address for executive leadership";
        requirements[2] = "Deployment name for identification";
        requirements[3] = "Authorized deployer permissions";
        requirements[4] = "Foundry environment with OpenZeppelin contracts";
    }

    /**
     * @notice Authorize additional deployers
     * @param deployer Address to authorize
     */
    function authorizeDeployer(address deployer) external onlyAdmin {
        authorizedDeployers[deployer] = true;
    }

    /**
     * @notice Revoke deployer authorization
     * @param deployer Address to revoke
     */
    function revokeDeployer(address deployer) external onlyAdmin {
        authorizedDeployers[deployer] = false;
    }

    // Internal deployment logic
    function _deployCoreDependencies(address chairman, address ceoAddress) internal returns (bool) {
        try this._unsafeDeployCore(chairman, ceoAddress) {
            return true;
        } catch {
            return false;
        }
    }

    function _unsafeDeployCore(address chairman, address ceoAddress) external {
        require(msg.sender == address(this), "Internal call only");

        // 1. Deploy Constitution (foundation)
        DAIO_Constitution_Enhanced constitution = new DAIO_Constitution_Enhanced(chairman);
        core.constitution = address(constitution);

        // 2. Deploy Governance Settings
        GovernanceSettings settings = new GovernanceSettings();
        core.settings = address(settings);

        // 3. Deploy Executive Roles
        ExecutiveRoles executiveRoles = new ExecutiveRoles(address(this));
        core.executiveRoles = address(executiveRoles);

        // 4. Deploy Voting Engine
        WeightedVotingEngine votingEngine = new WeightedVotingEngine(address(executiveRoles));
        core.votingEngine = address(votingEngine);

        // 5. Deploy Emergency Timelock
        address[] memory proposers = new address[](1);
        address[] memory executors = new address[](1);
        proposers[0] = address(this);
        executors[0] = address(this);

        EmergencyTimelock emergencyTimelock = new EmergencyTimelock(
            1 days,
            proposers,
            executors,
            address(this),
            address(constitution),
            address(executiveRoles)
        );
        core.emergencyTimelock = address(emergencyTimelock);

        // 6. Deploy Knowledge Hierarchy
        KnowledgeHierarchyDAIO knowledgeHierarchy = new KnowledgeHierarchyDAIO(
            TimelockController(payable(address(emergencyTimelock))),
            address(constitution)
        );
        core.knowledgeHierarchy = address(knowledgeHierarchy);

        // 7. Deploy Treasury
        address[] memory initialSigners = new address[](1);
        initialSigners[0] = address(this);
        Treasury treasury = new Treasury(address(constitution), initialSigners);
        core.treasury = address(treasury);

        // 8. Deploy Agent Factory
        AgentFactory agentFactory = new AgentFactory(
            address(executiveRoles),
            address(treasury)
        );
        core.agentFactory = address(agentFactory);

        // 9. Deploy IDNFT
        IDNFT idNFT = new IDNFT();
        core.idNFT = address(idNFT);

        // 10. Deploy Executive Governance (orchestrator)
        ExecutiveGovernance execGov = new ExecutiveGovernance(
            address(executiveRoles),
            address(votingEngine),
            payable(address(emergencyTimelock)),
            address(knowledgeHierarchy),
            address(constitution),
            address(settings)
        );
        core.executiveGovernance = address(execGov);

        // Configure relationships
        constitution.setExecutiveGovernance(address(execGov));
        constitution.setTreasury(address(treasury));

        // Appoint CEO
        executiveRoles.appointExecutive(
            ceoAddress,
            ExecutiveRoles.ExecutiveRole.CEO,
            0, // Indefinite term
            "Chief Executive Officer - Genesis Appointment"
        );
    }
}