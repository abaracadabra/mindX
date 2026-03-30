// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Pausable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title SecurityToken
 * @dev ERC1400 Security Token Standard implementation with DAIO integration
 *
 * Features:
 * - Partition-based token management (different classes of securities)
 * - Compliance framework with transfer restrictions
 * - Document management for legal compliance
 * - Integration with DAIO governance and constitutional constraints
 * - Corporate governance tools (voting, dividends, compliance)
 * - Regulatory compliance automation
 *
 * Partitions allow different classes of securities:
 * - Common stock, preferred stock, bonds, warrants, etc.
 * - Each partition can have different rights and restrictions
 *
 * @author DAIO Development Team
 */

interface IDAIO_Constitution_Enhanced {
    function validateSecurityTokenAction(
        address token,
        bytes32 partition,
        address from,
        address to,
        uint256 amount,
        bytes calldata data
    ) external view returns (bool valid, string memory reason);

    function validatePartitionCreation(
        address token,
        bytes32 partition,
        uint256 totalSupply
    ) external view returns (bool valid, string memory reason);
}

interface ITreasury {
    function collectSecurityTokenFee(
        address token,
        bytes32 partition,
        uint256 amount
    ) external;

    function paySecurityTokenDividend(
        address token,
        bytes32 partition,
        address holder,
        uint256 amount
    ) external;
}

interface IExecutiveGovernance {
    function hasExecutiveApproval(address account) external view returns (bool);
    function hasComplianceOfficerRole(address account) external view returns (bool);
}

contract SecurityToken is ERC20, ERC20Pausable, AccessControl, ReentrancyGuard {
    // =============================================================
    //                        CONSTANTS
    // =============================================================

    bytes32 public constant COMPLIANCE_OFFICER_ROLE = keccak256("COMPLIANCE_OFFICER_ROLE");
    bytes32 public constant TRANSFER_AGENT_ROLE = keccak256("TRANSFER_AGENT_ROLE");
    bytes32 public constant CONTROLLER_ROLE = keccak256("CONTROLLER_ROLE");
    bytes32 public constant DOCUMENT_MANAGER_ROLE = keccak256("DOCUMENT_MANAGER_ROLE");

    // Standard partition names for different security types
    bytes32 public constant COMMON_STOCK = keccak256("COMMON_STOCK");
    bytes32 public constant PREFERRED_STOCK = keccak256("PREFERRED_STOCK");
    bytes32 public constant BONDS = keccak256("BONDS");
    bytes32 public constant WARRANTS = keccak256("WARRANTS");
    bytes32 public constant RESTRICTED = keccak256("RESTRICTED");

    // Transfer restriction codes (ERC1066)
    bytes1 public constant TRANSFER_SUCCESS = 0x51;
    bytes1 public constant TRANSFER_FAILURE_NO_REASON = 0x50;
    bytes1 public constant TRANSFER_FAILURE_NOT_AUTHORIZED = 0x52;
    bytes1 public constant TRANSFER_FAILURE_COMPLIANCE = 0x53;
    bytes1 public constant TRANSFER_FAILURE_PARTITION_MISMATCH = 0x54;
    bytes1 public constant TRANSFER_FAILURE_INSUFFICIENT_BALANCE = 0x55;
    bytes1 public constant TRANSFER_FAILURE_INVALID_RECEIVER = 0x56;
    bytes1 public constant TRANSFER_FAILURE_LIMIT_EXCEEDED = 0x57;

    // =============================================================
    //                         STORAGE
    // =============================================================

    // DAIO Integration
    IDAIO_Constitution_Enhanced public immutable constitution;
    ITreasury public immutable treasury;
    IExecutiveGovernance public immutable governance;

    // Partition Management
    struct PartitionInfo {
        string name;
        string description;
        uint256 totalSupply;
        bool transferable;
        bool votingRights;
        uint256 dividendRate; // Basis points (10000 = 100%)
        address[] holders;
        mapping(address => uint256) balances;
        mapping(address => bool) isHolder;
        bool exists;
    }

    mapping(bytes32 => PartitionInfo) public partitions;
    bytes32[] public partitionList;

    // Compliance Framework
    struct ComplianceRule {
        bool active;
        uint256 maxHolderCount;
        uint256 maxHoldingPercent; // Basis points
        uint256 minHoldingAmount;
        uint256 maxDailyTransferAmount;
        bytes32[] allowedPartitions;
        address[] exemptAddresses;
        bool requiresKYC;
        uint256 lockupPeriod; // Seconds
    }

    mapping(bytes32 => ComplianceRule) public complianceRules;
    mapping(address => mapping(bytes32 => uint256)) public holderLockupEnd;
    mapping(address => bool) public kycApproved;
    mapping(address => mapping(bytes32 => uint256)) public dailyTransferAmounts;
    mapping(address => mapping(bytes32 => uint256)) public lastTransferDay;

    // Document Management
    struct Document {
        bytes32 name;
        string uri;
        bytes32 docHash;
        uint256 timestamp;
        bool active;
    }

    mapping(bytes32 => Document) public documents;
    bytes32[] public documentList;

    // Corporate Actions
    struct DividendDistribution {
        bytes32 partition;
        uint256 totalAmount;
        uint256 perTokenAmount;
        uint256 declarationTime;
        uint256 recordDate;
        uint256 paymentDate;
        bool executed;
        mapping(address => bool) claimed;
    }

    mapping(uint256 => DividendDistribution) public dividends;
    uint256 public dividendCount;

    // Events
    event PartitionCreated(
        bytes32 indexed partition,
        string name,
        string description,
        uint256 totalSupply
    );

    event TransferByPartition(
        bytes32 indexed fromPartition,
        address indexed from,
        address indexed to,
        uint256 value,
        bytes data,
        bytes operatorData
    );

    event IssuedByPartition(
        bytes32 indexed partition,
        address indexed to,
        uint256 value,
        bytes data
    );

    event RedeemedByPartition(
        bytes32 indexed partition,
        address indexed from,
        uint256 value,
        bytes data
    );

    event ComplianceRuleSet(
        bytes32 indexed partition,
        uint256 maxHolderCount,
        uint256 maxHoldingPercent
    );

    event DocumentSet(
        bytes32 indexed name,
        string uri,
        bytes32 docHash
    );

    event DividendDeclared(
        uint256 indexed dividendId,
        bytes32 indexed partition,
        uint256 totalAmount,
        uint256 recordDate,
        uint256 paymentDate
    );

    event DividendPaid(
        uint256 indexed dividendId,
        address indexed holder,
        uint256 amount
    );

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor(
        string memory name,
        string memory symbol,
        address constitutionAddress,
        address treasuryAddress,
        address governanceAddress,
        address admin
    ) ERC20(name, symbol) {
        constitution = IDAIO_Constitution_Enhanced(constitutionAddress);
        treasury = ITreasury(treasuryAddress);
        governance = IExecutiveGovernance(governanceAddress);

        // Set up access control
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(COMPLIANCE_OFFICER_ROLE, admin);
        _grantRole(CONTROLLER_ROLE, admin);
        _grantRole(DOCUMENT_MANAGER_ROLE, admin);

        // Create default common stock partition
        _createPartition(
            COMMON_STOCK,
            "Common Stock",
            "Standard voting shares with full dividend rights",
            1000000 * 10**decimals(), // 1M shares
            true, // transferable
            true, // voting rights
            1000  // 10% dividend rate
        );
    }

    // =============================================================
    //                   PARTITION MANAGEMENT
    // =============================================================

    /**
     * @dev Create a new security partition
     */
    function createPartition(
        bytes32 partition,
        string calldata name,
        string calldata description,
        uint256 totalSupply,
        bool transferable,
        bool votingRights,
        uint256 dividendRate
    ) external onlyRole(CONTROLLER_ROLE) {
        // Validate with constitution
        (bool valid, string memory reason) = constitution.validatePartitionCreation(
            address(this),
            partition,
            totalSupply
        );
        require(valid, reason);

        _createPartition(
            partition,
            name,
            description,
            totalSupply,
            transferable,
            votingRights,
            dividendRate
        );
    }

    /**
     * @dev Internal partition creation logic
     */
    function _createPartition(
        bytes32 partition,
        string memory name,
        string memory description,
        uint256 totalSupply,
        bool transferable,
        bool votingRights,
        uint256 dividendRate
    ) internal {
        require(!partitions[partition].exists, "Partition already exists");
        require(dividendRate <= 10000, "Dividend rate too high");

        PartitionInfo storage newPartition = partitions[partition];
        newPartition.name = name;
        newPartition.description = description;
        newPartition.totalSupply = totalSupply;
        newPartition.transferable = transferable;
        newPartition.votingRights = votingRights;
        newPartition.dividendRate = dividendRate;
        newPartition.exists = true;

        partitionList.push(partition);

        emit PartitionCreated(partition, name, description, totalSupply);
    }

    /**
     * @dev Issue tokens to a specific partition
     */
    function issueByPartition(
        bytes32 partition,
        address to,
        uint256 value,
        bytes calldata data
    ) external onlyRole(CONTROLLER_ROLE) nonReentrant {
        require(partitions[partition].exists, "Partition does not exist");
        require(to != address(0), "Cannot issue to zero address");

        // Validate with constitution
        (bool valid, string memory reason) = constitution.validateSecurityTokenAction(
            address(this),
            partition,
            address(0),
            to,
            value,
            data
        );
        require(valid, reason);

        // Check compliance
        require(_isTransferAllowed(partition, address(0), to, value), "Transfer violates compliance");

        // Update partition state
        PartitionInfo storage partInfo = partitions[partition];
        partInfo.balances[to] += value;

        if (!partInfo.isHolder[to] && value > 0) {
            partInfo.holders.push(to);
            partInfo.isHolder[to] = true;
        }

        // Mint ERC20 tokens
        _mint(to, value);

        // Collect fees to treasury (15% tithe as per constitution)
        if (value > 0) {
            treasury.collectSecurityTokenFee(address(this), partition, value);
        }

        emit IssuedByPartition(partition, to, value, data);
    }

    /**
     * @dev Redeem tokens from a specific partition
     */
    function redeemByPartition(
        bytes32 partition,
        address from,
        uint256 value,
        bytes calldata data
    ) external onlyRole(CONTROLLER_ROLE) nonReentrant {
        require(partitions[partition].exists, "Partition does not exist");
        require(from != address(0), "Cannot redeem from zero address");

        PartitionInfo storage partInfo = partitions[partition];
        require(partInfo.balances[from] >= value, "Insufficient partition balance");

        // Validate with constitution
        (bool valid, string memory reason) = constitution.validateSecurityTokenAction(
            address(this),
            partition,
            from,
            address(0),
            value,
            data
        );
        require(valid, reason);

        // Update partition state
        partInfo.balances[from] -= value;

        if (partInfo.balances[from] == 0 && partInfo.isHolder[from]) {
            partInfo.isHolder[from] = false;
            // Remove from holders array
            for (uint256 i = 0; i < partInfo.holders.length; i++) {
                if (partInfo.holders[i] == from) {
                    partInfo.holders[i] = partInfo.holders[partInfo.holders.length - 1];
                    partInfo.holders.pop();
                    break;
                }
            }
        }

        // Burn ERC20 tokens
        _burn(from, value);

        emit RedeemedByPartition(partition, from, value, data);
    }

    /**
     * @dev Transfer tokens within a specific partition
     */
    function transferByPartition(
        bytes32 partition,
        address to,
        uint256 value,
        bytes calldata data
    ) external returns (bytes32) {
        require(partitions[partition].exists, "Partition does not exist");
        require(partitions[partition].transferable, "Partition not transferable");

        return _transferByPartition(partition, msg.sender, to, value, data, "");
    }

    /**
     * @dev Internal partition transfer logic
     */
    function _transferByPartition(
        bytes32 partition,
        address from,
        address to,
        uint256 value,
        bytes memory data,
        bytes memory operatorData
    ) internal nonReentrant returns (bytes32) {
        require(to != address(0), "Cannot transfer to zero address");

        PartitionInfo storage partInfo = partitions[partition];
        require(partInfo.balances[from] >= value, "Insufficient partition balance");

        // Validate with constitution
        (bool valid, string memory reason) = constitution.validateSecurityTokenAction(
            address(this),
            partition,
            from,
            to,
            value,
            data
        );
        require(valid, reason);

        // Check compliance
        require(_isTransferAllowed(partition, from, to, value), "Transfer violates compliance");

        // Update partition balances
        partInfo.balances[from] -= value;
        partInfo.balances[to] += value;

        // Update holder tracking
        if (partInfo.balances[from] == 0 && partInfo.isHolder[from]) {
            partInfo.isHolder[from] = false;
            // Remove from holders array
            for (uint256 i = 0; i < partInfo.holders.length; i++) {
                if (partInfo.holders[i] == from) {
                    partInfo.holders[i] = partInfo.holders[partInfo.holders.length - 1];
                    partInfo.holders.pop();
                    break;
                }
            }
        }

        if (!partInfo.isHolder[to] && value > 0) {
            partInfo.holders.push(to);
            partInfo.isHolder[to] = true;
        }

        // Transfer ERC20 tokens
        _transfer(from, to, value);

        // Update daily transfer tracking
        _updateDailyTransfer(from, partition, value);

        emit TransferByPartition(partition, from, to, value, data, operatorData);

        return partition;
    }

    // =============================================================
    //                   COMPLIANCE FRAMEWORK
    // =============================================================

    /**
     * @dev Set compliance rules for a partition
     */
    function setComplianceRule(
        bytes32 partition,
        uint256 maxHolderCount,
        uint256 maxHoldingPercent,
        uint256 minHoldingAmount,
        uint256 maxDailyTransferAmount,
        bytes32[] calldata allowedPartitions,
        address[] calldata exemptAddresses,
        bool requiresKYC,
        uint256 lockupPeriod
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        require(partitions[partition].exists, "Partition does not exist");
        require(maxHoldingPercent <= 10000, "Max holding percent too high");

        ComplianceRule storage rule = complianceRules[partition];
        rule.active = true;
        rule.maxHolderCount = maxHolderCount;
        rule.maxHoldingPercent = maxHoldingPercent;
        rule.minHoldingAmount = minHoldingAmount;
        rule.maxDailyTransferAmount = maxDailyTransferAmount;
        rule.allowedPartitions = allowedPartitions;
        rule.exemptAddresses = exemptAddresses;
        rule.requiresKYC = requiresKYC;
        rule.lockupPeriod = lockupPeriod;

        emit ComplianceRuleSet(partition, maxHolderCount, maxHoldingPercent);
    }

    /**
     * @dev Approve KYC for an address
     */
    function approveKYC(address account) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        kycApproved[account] = true;
    }

    /**
     * @dev Revoke KYC for an address
     */
    function revokeKYC(address account) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        kycApproved[account] = false;
    }

    /**
     * @dev Set lockup period for a holder in a partition
     */
    function setLockupPeriod(
        address holder,
        bytes32 partition,
        uint256 lockupEnd
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        holderLockupEnd[holder][partition] = lockupEnd;
    }

    /**
     * @dev Check if a transfer is allowed under compliance rules
     */
    function _isTransferAllowed(
        bytes32 partition,
        address from,
        address to,
        uint256 value
    ) internal view returns (bool) {
        ComplianceRule storage rule = complianceRules[partition];

        if (!rule.active) {
            return true; // No compliance rules set
        }

        // Check exemptions
        bool fromExempt = _isExemptAddress(rule.exemptAddresses, from);
        bool toExempt = _isExemptAddress(rule.exemptAddresses, to);

        if (fromExempt && toExempt) {
            return true;
        }

        // Check KYC requirements
        if (rule.requiresKYC) {
            if (!kycApproved[from] || !kycApproved[to]) {
                return false;
            }
        }

        // Check lockup period
        if (holderLockupEnd[from][partition] > block.timestamp) {
            return false;
        }

        // Check daily transfer limit
        if (!toExempt && _getDailyTransferAmount(from, partition) + value > rule.maxDailyTransferAmount) {
            return false;
        }

        // Check maximum holding percentage
        if (!toExempt) {
            PartitionInfo storage partInfo = partitions[partition];
            uint256 newBalance = partInfo.balances[to] + value;
            uint256 maxAllowed = (partInfo.totalSupply * rule.maxHoldingPercent) / 10000;

            if (newBalance > maxAllowed) {
                return false;
            }
        }

        // Check minimum holding amount
        if (value > 0 && value < rule.minHoldingAmount && !toExempt) {
            return false;
        }

        // Check maximum holder count
        PartitionInfo storage partInfo = partitions[partition];
        if (!partInfo.isHolder[to] && partInfo.holders.length >= rule.maxHolderCount && !toExempt) {
            return false;
        }

        return true;
    }

    /**
     * @dev Check if address is in exempt list
     */
    function _isExemptAddress(address[] storage exemptList, address account) internal view returns (bool) {
        for (uint256 i = 0; i < exemptList.length; i++) {
            if (exemptList[i] == account) {
                return true;
            }
        }
        return false;
    }

    /**
     * @dev Update daily transfer tracking
     */
    function _updateDailyTransfer(address account, bytes32 partition, uint256 amount) internal {
        uint256 today = block.timestamp / 1 days;

        if (lastTransferDay[account][partition] < today) {
            dailyTransferAmounts[account][partition] = amount;
            lastTransferDay[account][partition] = today;
        } else {
            dailyTransferAmounts[account][partition] += amount;
        }
    }

    /**
     * @dev Get daily transfer amount for today
     */
    function _getDailyTransferAmount(address account, bytes32 partition) internal view returns (uint256) {
        uint256 today = block.timestamp / 1 days;

        if (lastTransferDay[account][partition] < today) {
            return 0;
        } else {
            return dailyTransferAmounts[account][partition];
        }
    }

    // =============================================================
    //                   DOCUMENT MANAGEMENT
    // =============================================================

    /**
     * @dev Set a document for the security token
     */
    function setDocument(
        bytes32 name,
        string calldata uri,
        bytes32 docHash
    ) external onlyRole(DOCUMENT_MANAGER_ROLE) {
        documents[name] = Document({
            name: name,
            uri: uri,
            docHash: docHash,
            timestamp: block.timestamp,
            active: true
        });

        // Add to list if new
        bool exists = false;
        for (uint256 i = 0; i < documentList.length; i++) {
            if (documentList[i] == name) {
                exists = true;
                break;
            }
        }

        if (!exists) {
            documentList.push(name);
        }

        emit DocumentSet(name, uri, docHash);
    }

    /**
     * @dev Remove a document
     */
    function removeDocument(bytes32 name) external onlyRole(DOCUMENT_MANAGER_ROLE) {
        require(documents[name].active, "Document does not exist");
        documents[name].active = false;
    }

    // =============================================================
    //                  CORPORATE ACTIONS
    // =============================================================

    /**
     * @dev Declare dividend distribution for a partition
     */
    function declareDividend(
        bytes32 partition,
        uint256 totalAmount,
        uint256 recordDate,
        uint256 paymentDate
    ) external onlyRole(CONTROLLER_ROLE) {
        require(partitions[partition].exists, "Partition does not exist");
        require(recordDate >= block.timestamp, "Record date must be in future");
        require(paymentDate > recordDate, "Payment date must be after record date");
        require(totalAmount > 0, "Total amount must be positive");

        PartitionInfo storage partInfo = partitions[partition];
        require(partInfo.totalSupply > 0, "No tokens in partition");

        uint256 perTokenAmount = totalAmount / partInfo.totalSupply;
        require(perTokenAmount > 0, "Per-token amount too small");

        DividendDistribution storage dividend = dividends[dividendCount];
        dividend.partition = partition;
        dividend.totalAmount = totalAmount;
        dividend.perTokenAmount = perTokenAmount;
        dividend.declarationTime = block.timestamp;
        dividend.recordDate = recordDate;
        dividend.paymentDate = paymentDate;
        dividend.executed = false;

        emit DividendDeclared(dividendCount, partition, totalAmount, recordDate, paymentDate);

        dividendCount++;
    }

    /**
     * @dev Claim dividend for a holder
     */
    function claimDividend(uint256 dividendId) external nonReentrant {
        DividendDistribution storage dividend = dividends[dividendId];
        require(block.timestamp >= dividend.paymentDate, "Payment date not reached");
        require(!dividend.claimed[msg.sender], "Dividend already claimed");

        PartitionInfo storage partInfo = partitions[dividend.partition];
        uint256 holderBalance = partInfo.balances[msg.sender];
        require(holderBalance > 0, "No tokens to claim dividend");

        uint256 dividendAmount = holderBalance * dividend.perTokenAmount;
        require(dividendAmount > 0, "No dividend to claim");

        dividend.claimed[msg.sender] = true;

        // Pay dividend from treasury
        treasury.paySecurityTokenDividend(
            address(this),
            dividend.partition,
            msg.sender,
            dividendAmount
        );

        emit DividendPaid(dividendId, msg.sender, dividendAmount);
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Get partition balance for a holder
     */
    function balanceOfByPartition(bytes32 partition, address account) external view returns (uint256) {
        return partitions[partition].balances[account];
    }

    /**
     * @dev Get all partitions for the token
     */
    function getPartitions() external view returns (bytes32[] memory) {
        return partitionList;
    }

    /**
     * @dev Get partition holders
     */
    function getPartitionHolders(bytes32 partition) external view returns (address[] memory) {
        return partitions[partition].holders;
    }

    /**
     * @dev Check if a transfer would be valid
     */
    function canTransfer(
        bytes32 partition,
        address from,
        address to,
        uint256 value,
        bytes calldata data
    ) external view returns (bytes1, bytes32, bytes32) {
        if (!partitions[partition].exists) {
            return (TRANSFER_FAILURE_PARTITION_MISMATCH, bytes32(0), partition);
        }

        if (!partitions[partition].transferable) {
            return (TRANSFER_FAILURE_NOT_AUTHORIZED, bytes32(0), partition);
        }

        if (partitions[partition].balances[from] < value) {
            return (TRANSFER_FAILURE_INSUFFICIENT_BALANCE, bytes32(0), partition);
        }

        // Check constitution
        (bool valid,) = constitution.validateSecurityTokenAction(
            address(this),
            partition,
            from,
            to,
            value,
            data
        );

        if (!valid) {
            return (TRANSFER_FAILURE_COMPLIANCE, bytes32(0), partition);
        }

        // Check compliance
        if (!_isTransferAllowed(partition, from, to, value)) {
            return (TRANSFER_FAILURE_COMPLIANCE, bytes32(0), partition);
        }

        return (TRANSFER_SUCCESS, bytes32(0), partition);
    }

    /**
     * @dev Get voting power for a holder across all voting partitions
     */
    function getVotingPower(address holder) external view returns (uint256 totalVotes) {
        for (uint256 i = 0; i < partitionList.length; i++) {
            bytes32 partition = partitionList[i];
            if (partitions[partition].votingRights) {
                totalVotes += partitions[partition].balances[holder];
            }
        }
        return totalVotes;
    }

    /**
     * @dev Get document information
     */
    function getDocument(bytes32 name) external view returns (
        string memory uri,
        bytes32 docHash,
        uint256 timestamp,
        bool active
    ) {
        Document storage doc = documents[name];
        return (doc.uri, doc.docHash, doc.timestamp, doc.active);
    }

    /**
     * @dev Get all document names
     */
    function getDocuments() external view returns (bytes32[] memory) {
        return documentList;
    }

    // =============================================================
    //                    ADMIN FUNCTIONS
    // =============================================================

    /**
     * @dev Emergency pause (only executive governance)
     */
    function pause() external {
        require(governance.hasExecutiveApproval(msg.sender), "Requires executive approval");
        _pause();
    }

    /**
     * @dev Unpause (only executive governance)
     */
    function unpause() external {
        require(governance.hasExecutiveApproval(msg.sender), "Requires executive approval");
        _unpause();
    }

    // =============================================================
    //                     OVERRIDES
    // =============================================================

    /**
     * @dev Override _update to add pausable functionality
     */
    function _update(address from, address to, uint256 value)
        internal
        override(ERC20, ERC20Pausable)
    {
        super._update(from, to, value);
    }

    /**
     * @dev Override supportsInterface for access control
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}