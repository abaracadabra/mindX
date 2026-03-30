// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import "@openzeppelin/contracts/proxy/transparent/ProxyAdmin.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title DAIO_TransparentProxy
 * @notice Transparent proxy with DAIO governance integration and constitutional compliance
 * @dev Enhanced TransparentUpgradeableProxy with CEO + Seven Soldiers approval for upgrades
 */
contract DAIO_TransparentProxy is TransparentUpgradeableProxy {
    /**
     * @notice Initialize DAIO Transparent Proxy
     * @param logic Initial implementation contract
     * @param admin Proxy admin (should be DAIO_ProxyAdmin)
     * @param data Initialization data for implementation
     */
    constructor(
        address logic,
        address admin,
        bytes memory data
    ) TransparentUpgradeableProxy(logic, admin, data) {
        // Additional DAIO-specific initialization handled by admin contract
    }
}

/**
 * @title DAIO_ProxyAdmin
 * @notice Proxy admin with DAIO governance integration for upgrade management
 * @dev Manages upgrades through CEO + Seven Soldiers approval process
 */
contract DAIO_ProxyAdmin is ProxyAdmin, AccessControl, ReentrancyGuard {
    bytes32 public constant CEO_ROLE = keccak256("CEO_ROLE");
    bytes32 public constant CISO_ROLE = keccak256("CISO_ROLE"); // Chief Information Security Officer
    bytes32 public constant CTO_ROLE = keccak256("CTO_ROLE");   // Chief Technology Officer
    bytes32 public constant UPGRADE_MANAGER_ROLE = keccak256("UPGRADE_MANAGER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Upgrade proposal structure
    struct UpgradeProposal {
        address proxy;                  // Proxy to upgrade
        address newImplementation;      // New implementation address
        bytes upgradeData;              // Upgrade calldata
        string description;             // Upgrade description
        string version;                 // New version identifier
        uint256 proposalTime;          // Proposal timestamp
        uint256 executionDeadline;     // Execution deadline
        uint256 approvalCount;         // Current approval count
        bool executed;                 // Whether upgrade was executed
        bool cancelled;                // Whether proposal was cancelled
        mapping(address => bool) approvals; // Executive approvals
        UpgradeType upgradeType;       // Type of upgrade
        uint256 riskLevel;             // Risk level (1-10)
    }

    enum UpgradeType {
        MINOR_UPDATE,                  // Bug fixes, minor improvements
        MAJOR_UPDATE,                  // New features, breaking changes
        SECURITY_UPDATE,               // Security patches
        EMERGENCY_PATCH,               // Emergency security fixes
        CONSTITUTIONAL_UPDATE          // Constitutional compliance updates
    }

    // DAIO Constitutional Integration
    struct ConstitutionalLimits {
        uint256 upgradeDelayPeriod;    // Minimum delay before upgrade execution
        uint256 emergencyUpgradeWindow; // Emergency upgrade window
        uint256 maxUpgradesPerMonth;   // Maximum upgrades per month
        uint256 consensusThreshold;    // Required approvals (out of 7 executives)
        address treasuryContract;      // DAIO treasury contract
        address constitutionContract;  // Constitution contract
        bool constitutionalCompliance; // Whether constitutional compliance is enforced
    }

    // State variables
    mapping(uint256 => UpgradeProposal) public upgradeProposals;
    mapping(address => uint256[]) public proxyUpgradeHistory; // proxy -> proposal IDs
    mapping(uint256 => uint256) public monthlyUpgradeCount;   // month -> count

    uint256 public proposalCounter;
    ConstitutionalLimits public constitutionalLimits;

    // Executive addresses (CEO + Seven Soldiers)
    address public ceoAddress;
    address public cisoAddress;
    address public ctoAddress;
    address public croAddress;  // Chief Risk Officer
    address public cfoAddress;  // Chief Financial Officer
    address public cpoAddress;  // Chief Product Officer
    address public cooAddress;  // Chief Operating Officer
    address public cloAddress;  // Chief Legal Officer

    // Security and risk management
    mapping(address => bool) public trustedImplementations; // Pre-approved implementations
    mapping(address => uint256) public implementationRiskScores; // Implementation risk scores
    uint256 public maxRiskLevel = 7; // Maximum risk level for auto-approval

    // Events
    event UpgradeProposed(
        uint256 indexed proposalId,
        address indexed proxy,
        address indexed newImplementation,
        UpgradeType upgradeType,
        address proposer
    );
    event UpgradeApproved(
        uint256 indexed proposalId,
        address indexed executive,
        bytes32 role,
        uint256 approvalCount
    );
    event UpgradeExecuted(
        uint256 indexed proposalId,
        address indexed proxy,
        address indexed newImplementation,
        address executor
    );
    event UpgradeCancelled(
        uint256 indexed proposalId,
        string reason,
        address canceller
    );
    event EmergencyUpgrade(
        address indexed proxy,
        address indexed newImplementation,
        string reason,
        address emergency_executor
    );
    event ImplementationTrusted(
        address indexed implementation,
        uint256 riskScore,
        address approver
    );
    event ConstitutionalComplianceCheck(
        bool compliant,
        string reason,
        uint256 proposalId
    );

    /**
     * @notice Initialize DAIO Proxy Admin
     * @param _ceoAddress CEO address
     * @param _executiveAddresses Array of seven soldiers addresses [CISO, CTO, CRO, CFO, CPO, COO, CLO]
     * @param _treasuryContract DAIO treasury contract
     * @param _constitutionContract DAIO constitution contract
     * @param admin Admin address for role management
     */
    constructor(
        address _ceoAddress,
        address[7] memory _executiveAddresses,
        address _treasuryContract,
        address _constitutionContract,
        address admin
    ) ProxyAdmin(admin) {
        require(_ceoAddress != address(0), "Invalid CEO address");
        require(admin != address(0), "Invalid admin address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CEO_ROLE, _ceoAddress);
        _grantRole(CISO_ROLE, _executiveAddresses[0]);
        _grantRole(CTO_ROLE, _executiveAddresses[1]);
        _grantRole(UPGRADE_MANAGER_ROLE, admin);
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
            upgradeDelayPeriod: 2 days,        // 2-day delay for upgrades
            emergencyUpgradeWindow: 24 hours,  // 24-hour emergency window
            maxUpgradesPerMonth: 5,            // Maximum 5 upgrades per month
            consensusThreshold: 5,             // 5 out of 8 executives (CEO + 7 soldiers)
            treasuryContract: _treasuryContract,
            constitutionContract: _constitutionContract,
            constitutionalCompliance: true
        });
    }

    /**
     * @notice Propose upgrade for a proxy
     * @param proxy Proxy contract to upgrade
     * @param newImplementation New implementation address
     * @param upgradeData Upgrade calldata
     * @param description Upgrade description
     * @param version New version identifier
     * @param upgradeType Type of upgrade
     * @param riskLevel Risk level (1-10)
     * @param executionDeadline Execution deadline
     * @return proposalId Created proposal ID
     */
    function proposeUpgrade(
        address proxy,
        address newImplementation,
        bytes memory upgradeData,
        string memory description,
        string memory version,
        UpgradeType upgradeType,
        uint256 riskLevel,
        uint256 executionDeadline
    ) external onlyRole(UPGRADE_MANAGER_ROLE) returns (uint256 proposalId) {
        require(proxy != address(0), "Invalid proxy address");
        require(newImplementation != address(0), "Invalid implementation address");
        require(riskLevel <= 10, "Invalid risk level");
        require(executionDeadline > block.timestamp + constitutionalLimits.upgradeDelayPeriod, "Invalid deadline");

        // Check constitutional compliance
        _checkConstitutionalCompliance(upgradeType, riskLevel);

        proposalId = proposalCounter++;

        UpgradeProposal storage proposal = upgradeProposals[proposalId];
        proposal.proxy = proxy;
        proposal.newImplementation = newImplementation;
        proposal.upgradeData = upgradeData;
        proposal.description = description;
        proposal.version = version;
        proposal.proposalTime = block.timestamp;
        proposal.executionDeadline = executionDeadline;
        proposal.upgradeType = upgradeType;
        proposal.riskLevel = riskLevel;

        // Add to proxy history
        proxyUpgradeHistory[proxy].push(proposalId);

        emit UpgradeProposed(
            proposalId,
            proxy,
            newImplementation,
            upgradeType,
            msg.sender
        );

        return proposalId;
    }

    /**
     * @notice Approve upgrade proposal (CEO + Seven Soldiers)
     * @param proposalId Proposal ID to approve
     */
    function approveUpgrade(uint256 proposalId) external {
        require(proposalId < proposalCounter, "Invalid proposal ID");
        require(_isExecutive(msg.sender), "Not an executive");

        UpgradeProposal storage proposal = upgradeProposals[proposalId];
        require(!proposal.executed, "Proposal already executed");
        require(!proposal.cancelled, "Proposal cancelled");
        require(block.timestamp <= proposal.executionDeadline, "Proposal expired");
        require(!proposal.approvals[msg.sender], "Already approved");

        proposal.approvals[msg.sender] = true;
        proposal.approvalCount++;

        bytes32 role = _getExecutiveRole(msg.sender);

        emit UpgradeApproved(proposalId, msg.sender, role, proposal.approvalCount);
    }

    /**
     * @notice Execute approved upgrade
     * @param proposalId Proposal ID to execute
     */
    function executeUpgrade(uint256 proposalId) external onlyRole(UPGRADE_MANAGER_ROLE) nonReentrant {
        require(proposalId < proposalCounter, "Invalid proposal ID");

        UpgradeProposal storage proposal = upgradeProposals[proposalId];
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

        if (proposal.upgradeData.length > 0) {
            upgradeAndCall(
                ITransparentUpgradeableProxy(proposal.proxy),
                proposal.newImplementation,
                proposal.upgradeData
            );
        } else {
            upgrade(
                ITransparentUpgradeableProxy(proposal.proxy),
                proposal.newImplementation
            );
        }

        // Update monthly upgrade count
        uint256 currentMonth = block.timestamp / 30 days;
        monthlyUpgradeCount[currentMonth]++;

        emit UpgradeExecuted(
            proposalId,
            proposal.proxy,
            proposal.newImplementation,
            msg.sender
        );
    }

    /**
     * @notice Emergency upgrade execution (CEO or CISO only)
     * @param proxy Proxy to upgrade
     * @param newImplementation New implementation
     * @param reason Emergency reason
     */
    function emergencyUpgrade(
        address proxy,
        address newImplementation,
        string memory reason
    ) external onlyRole(EMERGENCY_ROLE) nonReentrant {
        require(proxy != address(0), "Invalid proxy address");
        require(newImplementation != address(0), "Invalid implementation address");
        require(
            trustedImplementations[newImplementation] ||
            implementationRiskScores[newImplementation] <= 3, // Only low-risk for emergency
            "Implementation not approved for emergency use"
        );

        // Execute immediate upgrade
        upgrade(ITransparentUpgradeableProxy(proxy), newImplementation);

        emit EmergencyUpgrade(proxy, newImplementation, reason, msg.sender);
    }

    /**
     * @notice Cancel upgrade proposal
     * @param proposalId Proposal ID to cancel
     * @param reason Cancellation reason
     */
    function cancelUpgrade(
        uint256 proposalId,
        string memory reason
    ) external {
        require(proposalId < proposalCounter, "Invalid proposal ID");
        require(
            _isExecutive(msg.sender) || hasRole(UPGRADE_MANAGER_ROLE, msg.sender),
            "Not authorized to cancel"
        );

        UpgradeProposal storage proposal = upgradeProposals[proposalId];
        require(!proposal.executed, "Proposal already executed");
        require(!proposal.cancelled, "Proposal already cancelled");

        proposal.cancelled = true;

        emit UpgradeCancelled(proposalId, reason, msg.sender);
    }

    /**
     * @notice Add trusted implementation
     * @param implementation Implementation address
     * @param riskScore Risk score (1-10)
     */
    function addTrustedImplementation(
        address implementation,
        uint256 riskScore
    ) external onlyRole(CTO_ROLE) {
        require(implementation != address(0), "Invalid implementation address");
        require(riskScore <= 10, "Invalid risk score");

        trustedImplementations[implementation] = true;
        implementationRiskScores[implementation] = riskScore;

        emit ImplementationTrusted(implementation, riskScore, msg.sender);
    }

    /**
     * @notice Remove trusted implementation
     * @param implementation Implementation address
     */
    function removeTrustedImplementation(address implementation) external onlyRole(CTO_ROLE) {
        trustedImplementations[implementation] = false;
        implementationRiskScores[implementation] = 0;
    }

    /**
     * @notice Update constitutional limits
     * @param upgradeDelayPeriod New upgrade delay period
     * @param consensusThreshold New consensus threshold
     * @param maxUpgradesPerMonth New max upgrades per month
     */
    function updateConstitutionalLimits(
        uint256 upgradeDelayPeriod,
        uint256 consensusThreshold,
        uint256 maxUpgradesPerMonth
    ) external onlyRole(CEO_ROLE) {
        require(consensusThreshold <= 8, "Consensus threshold too high"); // Max 8 (CEO + 7 soldiers)
        require(consensusThreshold >= 4, "Consensus threshold too low"); // Min 4 for security

        constitutionalLimits.upgradeDelayPeriod = upgradeDelayPeriod;
        constitutionalLimits.consensusThreshold = consensusThreshold;
        constitutionalLimits.maxUpgradesPerMonth = maxUpgradesPerMonth;
    }

    // Internal Functions

    function _checkConstitutionalCompliance(UpgradeType upgradeType, uint256 riskLevel) internal {
        if (!constitutionalLimits.constitutionalCompliance) return;

        bool compliant = true;
        string memory reason = "Upgrade within constitutional limits";

        // Check monthly upgrade limit
        uint256 currentMonth = block.timestamp / 30 days;
        if (monthlyUpgradeCount[currentMonth] >= constitutionalLimits.maxUpgradesPerMonth) {
            compliant = false;
            reason = "Monthly upgrade limit exceeded";
        }

        // Check risk level for different upgrade types
        if (upgradeType == UpgradeType.MAJOR_UPDATE && riskLevel > 5) {
            compliant = false;
            reason = "Major update risk level too high";
        }

        if (upgradeType == UpgradeType.CONSTITUTIONAL_UPDATE && riskLevel > 3) {
            compliant = false;
            reason = "Constitutional update must be low risk";
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
     * @notice Get upgrade proposal
     * @param proposalId Proposal ID
     * @return proxy Proxy address
     * @return newImplementation New implementation address
     * @return description Upgrade description
     * @return version New version
     * @return proposalTime Proposal timestamp
     * @return executionDeadline Execution deadline
     * @return approvalCount Current approval count
     * @return executed Whether executed
     * @return cancelled Whether cancelled
     * @return upgradeType Type of upgrade
     * @return riskLevel Risk level
     */
    function getUpgradeProposal(uint256 proposalId)
        external
        view
        returns (
            address proxy,
            address newImplementation,
            string memory description,
            string memory version,
            uint256 proposalTime,
            uint256 executionDeadline,
            uint256 approvalCount,
            bool executed,
            bool cancelled,
            UpgradeType upgradeType,
            uint256 riskLevel
        )
    {
        require(proposalId < proposalCounter, "Invalid proposal ID");

        UpgradeProposal storage proposal = upgradeProposals[proposalId];

        return (
            proposal.proxy,
            proposal.newImplementation,
            proposal.description,
            proposal.version,
            proposal.proposalTime,
            proposal.executionDeadline,
            proposal.approvalCount,
            proposal.executed,
            proposal.cancelled,
            proposal.upgradeType,
            proposal.riskLevel
        );
    }

    /**
     * @notice Check if executive has approved a proposal
     * @param proposalId Proposal ID
     * @param executive Executive address
     * @return approved Whether executive has approved
     */
    function hasApproved(uint256 proposalId, address executive) external view returns (bool approved) {
        require(proposalId < proposalCounter, "Invalid proposal ID");
        return upgradeProposals[proposalId].approvals[executive];
    }

    /**
     * @notice Get proxy upgrade history
     * @param proxy Proxy address
     * @return proposalIds Array of proposal IDs
     */
    function getProxyUpgradeHistory(address proxy) external view returns (uint256[] memory proposalIds) {
        return proxyUpgradeHistory[proxy];
    }

    /**
     * @notice Get constitutional limits
     * @return limits Constitutional limits configuration
     */
    function getConstitutionalLimits() external view returns (ConstitutionalLimits memory limits) {
        return constitutionalLimits;
    }
}