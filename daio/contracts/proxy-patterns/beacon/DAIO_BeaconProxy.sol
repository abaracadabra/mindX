// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/proxy/beacon/BeaconProxy.sol";
import "@openzeppelin/contracts/proxy/beacon/UpgradeableBeacon.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title DAIO_BeaconProxy
 * @notice Beacon proxy with DAIO governance integration
 * @dev Enhanced BeaconProxy for mass contract upgrades with constitutional compliance
 */
contract DAIO_BeaconProxy is BeaconProxy {
    /**
     * @notice Initialize DAIO Beacon Proxy
     * @param beacon Address of the beacon contract
     * @param data Initialization data for implementation
     */
    constructor(address beacon, bytes memory data) BeaconProxy(beacon, data) {
        // Additional DAIO-specific initialization can be added here
    }
}

/**
 * @title DAIO_UpgradeableBeacon
 * @notice Upgradeable beacon with DAIO governance and constitutional compliance
 * @dev Manages implementation upgrades for multiple beacon proxies through executive approval
 */
contract DAIO_UpgradeableBeacon is UpgradeableBeacon, AccessControl, ReentrancyGuard {
    bytes32 public constant CEO_ROLE = keccak256("CEO_ROLE");
    bytes32 public constant CTO_ROLE = keccak256("CTO_ROLE");
    bytes32 public constant CISO_ROLE = keccak256("CISO_ROLE");
    bytes32 public constant BEACON_MANAGER_ROLE = keccak256("BEACON_MANAGER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Beacon upgrade proposal structure
    struct BeaconUpgradeProposal {
        address newImplementation;      // New implementation address
        string description;             // Upgrade description
        string version;                 // New version identifier
        uint256 proposalTime;          // Proposal timestamp
        uint256 executionDeadline;     // Execution deadline
        uint256 approvalCount;         // Current approval count
        uint256 affectedProxies;       // Number of proxies that would be affected
        bool executed;                 // Whether upgrade was executed
        bool cancelled;                // Whether proposal was cancelled
        mapping(address => bool) approvals; // Executive approvals
        UpgradeType upgradeType;       // Type of upgrade
        uint256 riskLevel;             // Risk level (1-10)
        uint256 estimatedGasCost;      // Estimated gas cost for upgrade
    }

    enum UpgradeType {
        PATCH,                         // Small fixes, minimal risk
        MINOR,                         // Feature additions, low risk
        MAJOR,                         // Significant changes, medium risk
        BREAKING,                      // Breaking changes, high risk
        EMERGENCY                      // Emergency fixes, variable risk
    }

    // Deployment tracking
    struct DeploymentInfo {
        address deployer;              // Who deployed this proxy
        uint256 deploymentTime;        // When it was deployed
        string purpose;                // Purpose description
        uint256 lastUpgrade;           // Last upgrade timestamp
        bool isActive;                 // Whether proxy is still active
    }

    // DAIO Constitutional Integration
    struct ConstitutionalLimits {
        uint256 upgradeDelayPeriod;    // Minimum delay before upgrade execution
        uint256 maxSimultaneousUpgrades; // Max proxies upgradeable at once
        uint256 consensusThreshold;    // Required approvals for upgrades
        uint256 emergencyWindow;       // Emergency upgrade time window
        address treasuryContract;      // DAIO treasury contract
        address constitutionContract;  // Constitution contract
        bool constitutionalCompliance; // Whether constitutional compliance is enforced
        uint256 upgradeGasLimit;       // Maximum gas for single upgrade
    }

    // State variables
    mapping(uint256 => BeaconUpgradeProposal) public upgradeProposals;
    mapping(address => DeploymentInfo) public deployments; // proxy -> deployment info
    mapping(address => bool) public trustedImplementations; // Pre-approved implementations
    mapping(string => address) public versionToImplementation; // version -> implementation

    uint256 public proposalCounter;
    uint256 public totalProxies;
    ConstitutionalLimits public constitutionalLimits;

    // Executive addresses (CEO + Seven Soldiers)
    address public ceoAddress;
    address public cisoAddress;
    address public ctoAddress;
    address public croAddress;
    address public cfoAddress;
    address public cpoAddress;
    address public cooAddress;
    address public cloAddress;

    // Upgrade history and analytics
    string public currentVersion;
    address[] public deployedProxies;
    uint256[] public upgradeHistory; // Proposal IDs of executed upgrades

    // Events
    event BeaconUpgradeProposed(
        uint256 indexed proposalId,
        address indexed newImplementation,
        UpgradeType upgradeType,
        uint256 affectedProxies,
        address proposer
    );
    event BeaconUpgradeApproved(
        uint256 indexed proposalId,
        address indexed executive,
        bytes32 role,
        uint256 approvalCount
    );
    event BeaconUpgradeExecuted(
        uint256 indexed proposalId,
        address indexed newImplementation,
        uint256 affectedProxies,
        string newVersion
    );
    event BeaconUpgradeCancelled(
        uint256 indexed proposalId,
        string reason,
        address canceller
    );
    event ProxyDeployed(
        address indexed proxy,
        address indexed deployer,
        string purpose,
        uint256 totalProxies
    );
    event EmergencyBeaconUpgrade(
        address indexed oldImplementation,
        address indexed newImplementation,
        string reason,
        address executor
    );
    event VersionRegistered(
        string version,
        address indexed implementation,
        address registrar
    );
    event ConstitutionalComplianceCheck(
        bool compliant,
        string reason,
        uint256 proposalId
    );

    /**
     * @notice Initialize DAIO Upgradeable Beacon
     * @param initialImplementation Initial implementation address
     * @param initialVersion Initial version string
     * @param _ceoAddress CEO address
     * @param _executiveAddresses Array of seven soldiers addresses [CISO, CTO, CRO, CFO, CPO, COO, CLO]
     * @param _treasuryContract DAIO treasury contract
     * @param _constitutionContract DAIO constitution contract
     * @param admin Admin address for role management
     */
    constructor(
        address initialImplementation,
        string memory initialVersion,
        address _ceoAddress,
        address[7] memory _executiveAddresses,
        address _treasuryContract,
        address _constitutionContract,
        address admin
    ) UpgradeableBeacon(initialImplementation, admin) {
        require(_ceoAddress != address(0), "Invalid CEO address");
        require(admin != address(0), "Invalid admin address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CEO_ROLE, _ceoAddress);
        _grantRole(CTO_ROLE, _executiveAddresses[1]);
        _grantRole(CISO_ROLE, _executiveAddresses[0]);
        _grantRole(BEACON_MANAGER_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, _ceoAddress);
        _grantRole(EMERGENCY_ROLE, _executiveAddresses[0]); // CISO also has emergency role

        // Store executive addresses
        ceoAddress = _ceoAddress;
        cisoAddress = _executiveAddresses[0];
        ctoAddress = _executiveAddresses[1];
        croAddress = _executiveAddresses[2];
        cfoAddress = _executiveAddresses[3];
        cpoAddress = _executiveAddresses[4];
        cooAddress = _executiveAddresses[5];
        cloAddress = _executiveAddresses[6];

        // Initialize constitutional limits
        constitutionalLimits = ConstitutionalLimits({
            upgradeDelayPeriod: 1 days,        // 1-day delay for beacon upgrades
            maxSimultaneousUpgrades: 100,      // Max 100 proxies upgraded at once
            consensusThreshold: 4,             // 4 out of 8 executives required
            emergencyWindow: 12 hours,         // 12-hour emergency window
            treasuryContract: _treasuryContract,
            constitutionContract: _constitutionContract,
            constitutionalCompliance: true,
            upgradeGasLimit: 5000000           // 5M gas limit for upgrades
        });

        // Register initial version
        currentVersion = initialVersion;
        versionToImplementation[initialVersion] = initialImplementation;
        trustedImplementations[initialImplementation] = true;

        emit VersionRegistered(initialVersion, initialImplementation, msg.sender);
    }

    /**
     * @notice Deploy new beacon proxy
     * @param data Initialization data for proxy
     * @param purpose Purpose description for the proxy
     * @return proxy Address of deployed proxy
     */
    function deployProxy(
        bytes memory data,
        string memory purpose
    ) external returns (address proxy) {
        // Deploy new beacon proxy
        proxy = address(new DAIO_BeaconProxy(address(this), data));

        // Track deployment
        deployments[proxy] = DeploymentInfo({
            deployer: msg.sender,
            deploymentTime: block.timestamp,
            purpose: purpose,
            lastUpgrade: block.timestamp,
            isActive: true
        });

        deployedProxies.push(proxy);
        totalProxies++;

        emit ProxyDeployed(proxy, msg.sender, purpose, totalProxies);
        return proxy;
    }

    /**
     * @notice Propose beacon upgrade
     * @param newImplementation New implementation address
     * @param description Upgrade description
     * @param version New version identifier
     * @param upgradeType Type of upgrade
     * @param riskLevel Risk level (1-10)
     * @param executionDeadline Execution deadline
     * @param estimatedGasCost Estimated gas cost
     * @return proposalId Created proposal ID
     */
    function proposeBeaconUpgrade(
        address newImplementation,
        string memory description,
        string memory version,
        UpgradeType upgradeType,
        uint256 riskLevel,
        uint256 executionDeadline,
        uint256 estimatedGasCost
    ) external onlyRole(BEACON_MANAGER_ROLE) returns (uint256 proposalId) {
        require(newImplementation != address(0), "Invalid implementation address");
        require(newImplementation != implementation(), "Same implementation");
        require(riskLevel <= 10, "Invalid risk level");
        require(
            executionDeadline > block.timestamp + constitutionalLimits.upgradeDelayPeriod,
            "Invalid deadline"
        );
        require(estimatedGasCost <= constitutionalLimits.upgradeGasLimit, "Gas cost too high");

        // Check constitutional compliance
        _checkConstitutionalCompliance(upgradeType, riskLevel, totalProxies);

        proposalId = proposalCounter++;

        BeaconUpgradeProposal storage proposal = upgradeProposals[proposalId];
        proposal.newImplementation = newImplementation;
        proposal.description = description;
        proposal.version = version;
        proposal.proposalTime = block.timestamp;
        proposal.executionDeadline = executionDeadline;
        proposal.upgradeType = upgradeType;
        proposal.riskLevel = riskLevel;
        proposal.estimatedGasCost = estimatedGasCost;
        proposal.affectedProxies = totalProxies;

        emit BeaconUpgradeProposed(
            proposalId,
            newImplementation,
            upgradeType,
            totalProxies,
            msg.sender
        );

        return proposalId;
    }

    /**
     * @notice Approve beacon upgrade proposal (CEO + Seven Soldiers)
     * @param proposalId Proposal ID to approve
     */
    function approveBeaconUpgrade(uint256 proposalId) external {
        require(proposalId < proposalCounter, "Invalid proposal ID");
        require(_isExecutive(msg.sender), "Not an executive");

        BeaconUpgradeProposal storage proposal = upgradeProposals[proposalId];
        require(!proposal.executed, "Proposal already executed");
        require(!proposal.cancelled, "Proposal cancelled");
        require(block.timestamp <= proposal.executionDeadline, "Proposal expired");
        require(!proposal.approvals[msg.sender], "Already approved");

        proposal.approvals[msg.sender] = true;
        proposal.approvalCount++;

        bytes32 role = _getExecutiveRole(msg.sender);

        emit BeaconUpgradeApproved(proposalId, msg.sender, role, proposal.approvalCount);
    }

    /**
     * @notice Execute approved beacon upgrade
     * @param proposalId Proposal ID to execute
     */
    function executeBeaconUpgrade(uint256 proposalId) external onlyRole(BEACON_MANAGER_ROLE) nonReentrant {
        require(proposalId < proposalCounter, "Invalid proposal ID");

        BeaconUpgradeProposal storage proposal = upgradeProposals[proposalId];
        require(!proposal.executed, "Proposal already executed");
        require(!proposal.cancelled, "Proposal cancelled");
        require(block.timestamp <= proposal.executionDeadline, "Proposal expired");
        require(
            block.timestamp >= proposal.proposalTime + constitutionalLimits.upgradeDelayPeriod,
            "Upgrade delay period not met"
        );

        // Check required approvals
        require(
            proposal.approvalCount >= constitutionalLimits.consensusThreshold,
            "Insufficient approvals"
        );

        // Execute upgrade
        proposal.executed = true;

        // Update beacon implementation
        _upgradeTo(proposal.newImplementation);

        // Update version tracking
        currentVersion = proposal.version;
        versionToImplementation[proposal.version] = proposal.newImplementation;
        trustedImplementations[proposal.newImplementation] = true;

        // Update upgrade history
        upgradeHistory.push(proposalId);

        // Update last upgrade time for all proxies
        for (uint256 i = 0; i < deployedProxies.length; i++) {
            if (deployments[deployedProxies[i]].isActive) {
                deployments[deployedProxies[i]].lastUpgrade = block.timestamp;
            }
        }

        emit BeaconUpgradeExecuted(
            proposalId,
            proposal.newImplementation,
            proposal.affectedProxies,
            proposal.version
        );
        emit VersionRegistered(proposal.version, proposal.newImplementation, msg.sender);
    }

    /**
     * @notice Emergency beacon upgrade (CEO or CISO only)
     * @param newImplementation New implementation address
     * @param reason Emergency reason
     * @param version Emergency version identifier
     */
    function emergencyBeaconUpgrade(
        address newImplementation,
        string memory reason,
        string memory version
    ) external onlyRole(EMERGENCY_ROLE) nonReentrant {
        require(newImplementation != address(0), "Invalid implementation address");
        require(newImplementation != implementation(), "Same implementation");
        require(
            trustedImplementations[newImplementation],
            "Implementation not trusted for emergency use"
        );

        address oldImplementation = implementation();

        // Execute immediate upgrade
        _upgradeTo(newImplementation);

        // Update version tracking
        currentVersion = version;
        versionToImplementation[version] = newImplementation;

        // Update last upgrade time for all active proxies
        for (uint256 i = 0; i < deployedProxies.length; i++) {
            if (deployments[deployedProxies[i]].isActive) {
                deployments[deployedProxies[i]].lastUpgrade = block.timestamp;
            }
        }

        emit EmergencyBeaconUpgrade(oldImplementation, newImplementation, reason, msg.sender);
        emit VersionRegistered(version, newImplementation, msg.sender);
    }

    /**
     * @notice Cancel beacon upgrade proposal
     * @param proposalId Proposal ID to cancel
     * @param reason Cancellation reason
     */
    function cancelBeaconUpgrade(
        uint256 proposalId,
        string memory reason
    ) external {
        require(proposalId < proposalCounter, "Invalid proposal ID");
        require(
            _isExecutive(msg.sender) || hasRole(BEACON_MANAGER_ROLE, msg.sender),
            "Not authorized to cancel"
        );

        BeaconUpgradeProposal storage proposal = upgradeProposals[proposalId];
        require(!proposal.executed, "Proposal already executed");
        require(!proposal.cancelled, "Proposal already cancelled");

        proposal.cancelled = true;

        emit BeaconUpgradeCancelled(proposalId, reason, msg.sender);
    }

    /**
     * @notice Deactivate proxy (mark as inactive)
     * @param proxy Proxy address to deactivate
     * @param reason Deactivation reason
     */
    function deactivateProxy(address proxy, string memory reason) external {
        require(deployments[proxy].deployer == msg.sender || _isExecutive(msg.sender), "Not authorized");
        require(deployments[proxy].isActive, "Proxy already inactive");

        deployments[proxy].isActive = false;

        // Could emit an event here for deactivation tracking
    }

    /**
     * @notice Get active proxy count
     * @return count Number of active proxies
     */
    function getActiveProxyCount() external view returns (uint256 count) {
        for (uint256 i = 0; i < deployedProxies.length; i++) {
            if (deployments[deployedProxies[i]].isActive) {
                count++;
            }
        }
        return count;
    }

    /**
     * @notice Get proxies by deployer
     * @param deployer Deployer address
     * @return proxies Array of proxy addresses deployed by deployer
     */
    function getProxiesByDeployer(address deployer) external view returns (address[] memory proxies) {
        uint256 count = 0;

        // First pass: count proxies by deployer
        for (uint256 i = 0; i < deployedProxies.length; i++) {
            if (deployments[deployedProxies[i]].deployer == deployer) {
                count++;
            }
        }

        // Second pass: collect proxies
        proxies = new address[](count);
        uint256 index = 0;
        for (uint256 i = 0; i < deployedProxies.length; i++) {
            if (deployments[deployedProxies[i]].deployer == deployer) {
                proxies[index] = deployedProxies[i];
                index++;
            }
        }

        return proxies;
    }

    // Internal Functions

    function _checkConstitutionalCompliance(
        UpgradeType upgradeType,
        uint256 riskLevel,
        uint256 affectedProxies
    ) internal {
        if (!constitutionalLimits.constitutionalCompliance) return;

        bool compliant = true;
        string memory reason = "Beacon upgrade within constitutional limits";

        // Check affected proxies limit
        if (affectedProxies > constitutionalLimits.maxSimultaneousUpgrades) {
            compliant = false;
            reason = "Too many proxies affected by upgrade";
        }

        // Check risk level for different upgrade types
        if (upgradeType == UpgradeType.BREAKING && riskLevel > 6) {
            compliant = false;
            reason = "Breaking change risk level too high";
        }

        if (upgradeType == UpgradeType.MAJOR && riskLevel > 7) {
            compliant = false;
            reason = "Major update risk level too high";
        }

        emit ConstitutionalComplianceCheck(compliant, reason, proposalCounter);
        require(compliant, reason);
    }

    function _isExecutive(address account) internal view returns (bool) {
        return account == ceoAddress ||
               account == cisoAddress ||
               account == ctoAddress ||
               account == croAddress ||
               account == cfoAddress ||
               account == cpoAddress ||
               account == cooAddress ||
               account == cloAddress;
    }

    function _getExecutiveRole(address account) internal view returns (bytes32) {
        if (account == ceoAddress) return CEO_ROLE;
        if (account == cisoAddress) return CISO_ROLE;
        if (account == ctoAddress) return CTO_ROLE;
        if (account == croAddress) return keccak256("CRO_ROLE");
        if (account == cfoAddress) return keccak256("CFO_ROLE");
        if (account == cpoAddress) return keccak256("CPO_ROLE");
        if (account == cooAddress) return keccak256("COO_ROLE");
        if (account == cloAddress) return keccak256("CLO_ROLE");
        return bytes32(0);
    }

    /**
     * @notice Get beacon upgrade proposal
     * @param proposalId Proposal ID
     * @return newImplementation New implementation address
     * @return description Upgrade description
     * @return version New version
     * @return proposalTime Proposal timestamp
     * @return executionDeadline Execution deadline
     * @return approvalCount Current approval count
     * @return affectedProxies Number of affected proxies
     * @return executed Whether executed
     * @return cancelled Whether cancelled
     * @return upgradeType Type of upgrade
     * @return riskLevel Risk level
     */
    function getBeaconUpgradeProposal(uint256 proposalId)
        external
        view
        returns (
            address newImplementation,
            string memory description,
            string memory version,
            uint256 proposalTime,
            uint256 executionDeadline,
            uint256 approvalCount,
            uint256 affectedProxies,
            bool executed,
            bool cancelled,
            UpgradeType upgradeType,
            uint256 riskLevel
        )
    {
        require(proposalId < proposalCounter, "Invalid proposal ID");

        BeaconUpgradeProposal storage proposal = upgradeProposals[proposalId];

        return (
            proposal.newImplementation,
            proposal.description,
            proposal.version,
            proposal.proposalTime,
            proposal.executionDeadline,
            proposal.approvalCount,
            proposal.affectedProxies,
            proposal.executed,
            proposal.cancelled,
            proposal.upgradeType,
            proposal.riskLevel
        );
    }

    /**
     * @notice Check if executive has approved a beacon upgrade proposal
     * @param proposalId Proposal ID
     * @param executive Executive address
     * @return approved Whether executive has approved
     */
    function hasBeaconApproved(uint256 proposalId, address executive) external view returns (bool approved) {
        require(proposalId < proposalCounter, "Invalid proposal ID");
        return upgradeProposals[proposalId].approvals[executive];
    }

    /**
     * @notice Get deployment info for proxy
     * @param proxy Proxy address
     * @return info Deployment information
     */
    function getDeploymentInfo(address proxy) external view returns (DeploymentInfo memory info) {
        return deployments[proxy];
    }

    /**
     * @notice Get all deployed proxies
     * @return proxies Array of all deployed proxy addresses
     */
    function getAllDeployedProxies() external view returns (address[] memory proxies) {
        return deployedProxies;
    }

    /**
     * @notice Get current version info
     * @return version Current version string
     * @return implementationAddr Current implementation address
     */
    function getCurrentVersionInfo() external view returns (string memory version, address implementationAddr) {
        return (currentVersion, implementation());
    }

    /**
     * @notice Get upgrade history
     * @return history Array of executed upgrade proposal IDs
     */
    function getUpgradeHistory() external view returns (uint256[] memory history) {
        return upgradeHistory;
    }

    /**
     * @notice Get constitutional limits
     * @return limits Constitutional limits configuration
     */
    function getConstitutionalLimits() external view returns (ConstitutionalLimits memory limits) {
        return constitutionalLimits;
    }
}