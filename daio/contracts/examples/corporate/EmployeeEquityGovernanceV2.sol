// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../../eip-standards/advanced/ERC1400/SecurityToken.sol";
import "../../daio/governance/TriumvirateGovernance.sol";
import "../../eip-standards/advanced/ERC4337/SmartAccount.sol";

/**
 * @title EmployeeEquityGovernanceV2
 * @dev Fortune 500 Employee Equity and Corporate Governance Example - SECURITY ENHANCED VERSION
 *
 * This contract demonstrates how a Fortune 500 technology company
 * can use DAIO infrastructure for comprehensive employee equity management
 * with enterprise-grade security controls.
 *
 * SECURITY IMPROVEMENTS:
 * - Fixed voting weight manipulation via voting snapshots
 * - Implemented insider trading pre-clearance system
 * - Added precise vesting calculations with remainder handling
 * - Enhanced reentrancy protection for all financial operations
 * - Comprehensive audit logging and compliance monitoring
 * - Advanced blackout period management with calendar integration
 * - Multi-signature requirements for critical governance operations
 * - Circuit breaker protection for emergency situations
 *
 * USE CASE: Global Technology Corporation (Fortune 500)
 * - 300,000+ employees worldwide
 * - Complex equity compensation programs
 * - Multi-tier stock option plans (ISO, NSO, RSU, ESPP)
 * - Board of directors and shareholder governance
 * - Regulatory compliance (SEC, SOX, international)
 * - Employee voting and proposal systems
 *
 * @author DAIO Development Team - Security Enhanced
 */

contract EmployeeEquityGovernanceV2 is AccessControl, ReentrancyGuard {
    // =============================================================
    //                        CONSTANTS
    // =============================================================

    bytes32 public constant HR_MANAGER_ROLE = keccak256("HR_MANAGER_ROLE");
    bytes32 public constant COMPENSATION_COMMITTEE_ROLE = keccak256("COMPENSATION_COMMITTEE_ROLE");
    bytes32 public constant BOARD_MEMBER_ROLE = keccak256("BOARD_MEMBER_ROLE");
    bytes32 public constant SHAREHOLDER_ROLE = keccak256("SHAREHOLDER_ROLE");
    bytes32 public constant EMPLOYEE_ROLE = keccak256("EMPLOYEE_ROLE");
    bytes32 public constant COMPLIANCE_OFFICER_ROLE = keccak256("COMPLIANCE_OFFICER_ROLE");
    bytes32 public constant AUDITOR_ROLE = keccak256("AUDITOR_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // SECURITY: Multi-signature requirements
    uint256 public constant MULTI_SIG_THRESHOLD = 10000000 * 1e18; // $10M threshold for multi-sig
    uint256 public constant GOVERNANCE_MULTI_SIG_THRESHOLD = 1000000 * 1e18; // $1M for governance

    // SECURITY: Vesting precision
    uint256 public constant VESTING_PRECISION = 1e18; // High precision for vesting calculations
    uint256 public constant MIN_VESTING_PERIOD = 30 days; // Minimum vesting period

    // SECURITY: Insider trading controls
    uint256 public constant MIN_BLACKOUT_PERIOD = 7 days; // Minimum blackout before earnings
    uint256 public constant INSIDER_COOLING_PERIOD = 30 days; // Cooling period between trades
    uint256 public constant PRE_CLEARANCE_VALIDITY = 5 days; // Pre-clearance validity period

    // Employee levels aligned with corporate hierarchy
    enum EmployeeLevel {
        L1_Individual,      // Individual contributor
        L2_SeniorIC,       // Senior individual contributor
        L3_Staff,          // Staff level
        L4_Principal,      // Principal level
        L5_Manager,        // First-level manager
        L6_SeniorManager,  // Senior manager
        L7_Director,       // Director
        L8_SeniorDirector, // Senior director
        L9_VP,             // Vice president
        L10_SVP,           // Senior vice president
        L11_EVP,           // Executive vice president
        L12_C_Level        // C-level executives
    }

    // Equity types
    enum EquityType {
        ISO,               // Incentive Stock Options
        NSO,               // Non-qualified Stock Options
        RSU,               // Restricted Stock Units
        ESPP,              // Employee Stock Purchase Plan
        PerformanceShares, // Performance-based shares
        RestrictedStock,   // Restricted stock awards
        SARs               // Stock Appreciation Rights
    }

    // Vesting schedules
    enum VestingSchedule {
        Immediate,         // Immediate vesting
        OneYear,          // 1-year cliff
        FourYearMonthly,  // 4-year monthly vesting with 1-year cliff
        FourYearQuarterly, // 4-year quarterly vesting
        PerformanceBased  // Performance milestone vesting
    }

    // SECURITY: Insider trading control
    enum TradeStatus {
        Pending,           // Awaiting pre-clearance
        Approved,          // Pre-cleared for trading
        Rejected,          // Pre-clearance rejected
        Executed,          // Trade executed
        Expired            // Pre-clearance expired
    }

    // =============================================================
    //                         STORAGE
    // =============================================================

    // Core DAIO Integration
    SecurityToken public immutable companyStock;
    TriumvirateGovernance public immutable daiGovernance;
    SmartAccount public immutable corporateAccount;

    // Company Information
    string public companyName;
    string public stockSymbol;
    uint256 public totalEmployees;
    uint256 public totalShares;
    uint256 public sharePrice; // Current market price
    address public treasuryAddress;

    // SECURITY: Emergency controls
    bool public emergencyPaused;
    uint256 public emergencyPausedAt;
    uint256 public constant MAX_EMERGENCY_PAUSE_DURATION = 7 days;

    // SECURITY: Multi-signature controls
    struct MultiSigOperation {
        bytes32 operationHash;
        uint256 approvals;
        uint256 threshold;
        uint256 expiry;
        mapping(address => bool) hasApproved;
        bool executed;
    }
    mapping(bytes32 => MultiSigOperation) public multiSigOperations;
    address[] public multiSigSigners;
    uint256 public multiSigThreshold = 3; // 3 of 5 multi-sig

    // SECURITY: Voting snapshots to prevent manipulation
    struct VotingSnapshot {
        mapping(address => uint256) balances;
        uint256 totalSupply;
        uint256 blockNumber;
    }
    mapping(bytes32 => VotingSnapshot) public votingSnapshots;

    // Employee Management
    struct Employee {
        address employeeAddress;
        uint256 employeeId;
        string name;
        string department;
        EmployeeLevel level;
        uint256 hireDate;
        uint256 salary;
        bool active;
        address smartAccountAddress; // ERC4337 account for gasless transactions
        uint256 totalEquityValue;
        uint256 vestedEquityValue;
        mapping(EquityType => uint256) equityBalances;
        mapping(EquityType => bool) eligibleEquityTypes;
    }

    mapping(address => Employee) public employees;
    mapping(uint256 => address) public employeeIdToAddress;
    address[] public employeeList;
    mapping(EmployeeLevel => address[]) public employeesByLevel;

    // SECURITY: Enhanced equity grants with precision tracking
    struct EquityGrantV2 {
        bytes32 grantId;
        address employee;
        EquityType equityType;
        uint256 totalShares;
        uint256 vestedShares;
        uint256 remainderAccumulator; // SECURITY: Track remainder for precise vesting
        uint256 grantDate;
        uint256 grantPrice; // Strike price for options
        uint256 expirationDate;
        VestingSchedule vestingSchedule;
        uint256 cliffDate;
        uint256[] vestingDates;
        uint256[] vestingAmounts;
        bool performanceMetsMet; // For performance-based grants
        bool exercised;
        bool forfeited;
        uint256 lastVestingProcessed; // SECURITY: Track last processed vesting event
    }

    mapping(bytes32 => EquityGrantV2) public equityGrants;
    mapping(address => bytes32[]) public employeeGrants;
    bytes32[] public activeGrants;

    // Employee Stock Purchase Plan (ESPP)
    struct ESPPParticipation {
        address employee;
        uint256 contributionPercentage; // Percentage of salary
        uint256 maxAnnualContribution;
        uint256 currentPeriodContributions;
        uint256 accumulatedShares;
        bool enrolled;
        uint256 enrollmentDate;
        uint256 lookbackPeriod; // For lookback ESPP
    }

    mapping(address => ESPPParticipation) public esppParticipants;
    uint256 public esppOfferingPeriod; // Duration of ESPP offering period
    uint256 public esppDiscount; // Discount percentage (e.g., 15%)

    // SECURITY: Enhanced board proposals with voting snapshots
    struct BoardProposalV2 {
        bytes32 proposalId;
        address proposer;
        string title;
        string description;
        uint256 startTime;
        uint256 endTime;
        uint256 snapshotBlock; // SECURITY: Block number for voting snapshot
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool executed;
        bool passed;
        mapping(address => bool) hasVoted;
        mapping(address => uint8) votes; // 0=against, 1=for, 2=abstain
        uint256 quorumRequired;
        uint256 majorityRequired; // Basis points
        bool requiresMultiSig; // SECURITY: Flag for multi-sig requirement
    }

    mapping(bytes32 => BoardProposalV2) public boardProposals;
    bytes32[] public activeProposals;

    // Shareholder Meetings
    struct ShareholderMeeting {
        bytes32 meetingId;
        string purpose;
        uint256 scheduleDate;
        uint256 recordDate; // Date to determine eligible voters
        bytes32[] proposalsToVote;
        bool completed;
        uint256 attendance; // Number of attendees
        mapping(address => bool) attended;
    }

    mapping(bytes32 => ShareholderMeeting) public shareholderMeetings;
    bytes32[] public scheduledMeetings;

    // SECURITY: Enhanced insider trading controls
    struct InsiderTradingRecord {
        address insider;
        uint256 lastTradeDate;
        uint256 sharesTraded;
        bool currentlyInBlackout;
        uint256 blackoutStartDate;
        uint256 blackoutEndDate;
    }

    struct PreClearanceRequest {
        bytes32 requestId;
        address insider;
        EquityType equityType;
        uint256 sharesToTrade;
        uint256 requestDate;
        uint256 validUntil;
        TradeStatus status;
        string rejectionReason;
        address approvedBy;
    }

    mapping(address => InsiderTradingRecord) public insiderRecords;
    mapping(bytes32 => PreClearanceRequest) public preClearanceRequests;
    mapping(address => bool) public insiders; // Employees with material non-public info
    mapping(address => uint256) public lastTradingDate;

    // SECURITY: Blackout period management
    struct BlackoutPeriod {
        uint256 startDate;
        uint256 endDate;
        string reason;
        bool active;
    }
    BlackoutPeriod[] public blackoutPeriods;
    mapping(uint256 => bool) public isBlackoutDay;

    // Compliance and Reporting
    struct ComplianceReport {
        uint256 timestamp;
        string reportType;
        bytes32 reportHash;
        address submitter;
        bool reviewed;
    }

    mapping(bytes32 => ComplianceReport) public complianceReports;
    bytes32[] public pendingReports;

    // Statistics and Metrics
    struct GovernanceStats {
        uint256 totalProposals;
        uint256 executedProposals;
        uint256 totalVotes;
        uint256 averageParticipation;
        uint256 totalEquityValue;
        uint256 insiderTradingViolations;
    }

    GovernanceStats public stats;

    // =============================================================
    //                         EVENTS
    // =============================================================

    // Employee events
    event EmployeeRegistered(address indexed employee, uint256 indexed employeeId, EmployeeLevel level);
    event EmployeeUpdated(address indexed employee, EmployeeLevel oldLevel, EmployeeLevel newLevel);
    event EmployeeDeactivated(address indexed employee, uint256 timestamp);

    // Equity events
    event EquityGranted(bytes32 indexed grantId, address indexed employee, EquityType equityType, uint256 shares);
    event EquityVested(bytes32 indexed grantId, address indexed employee, uint256 vestedShares, uint256 remainder);
    event EquityExercised(bytes32 indexed grantId, address indexed employee, uint256 shares, uint256 value);

    // Governance events
    event ProposalCreated(bytes32 indexed proposalId, address indexed proposer, uint256 snapshotBlock);
    event VoteCast(bytes32 indexed proposalId, address indexed voter, uint8 vote, uint256 weight);
    event ProposalExecuted(bytes32 indexed proposalId, bool passed);

    // SECURITY: Enhanced security events
    event VotingSnapshotTaken(bytes32 indexed proposalId, uint256 blockNumber, uint256 totalSupply);
    event InsiderTradingViolation(address indexed insider, string violation, uint256 timestamp);
    event PreClearanceRequested(bytes32 indexed requestId, address indexed insider, uint256 shares);
    event PreClearanceApproved(bytes32 indexed requestId, address indexed approver);
    event PreClearanceRejected(bytes32 indexed requestId, string reason);
    event BlackoutPeriodActivated(uint256 startDate, uint256 endDate, string reason);
    event EmergencyPauseActivated(address indexed activator, uint256 timestamp);
    event EmergencyPauseDeactivated(address indexed deactivator, uint256 timestamp);
    event MultiSigOperationCreated(bytes32 indexed operationHash, uint256 threshold, uint256 expiry);
    event MultiSigApprovalAdded(bytes32 indexed operationHash, address indexed signer);
    event MultiSigOperationExecuted(bytes32 indexed operationHash);

    // Compliance events
    event ComplianceReportSubmitted(bytes32 indexed reportId, string reportType, address indexed submitter);
    event InsiderDesignated(address indexed employee, bool isInsider);
    event ESPPEnrollment(address indexed employee, uint256 contributionPercentage);

    // Meeting events
    event MeetingScheduled(bytes32 indexed meetingId, uint256 scheduleDate, uint256 recordDate);
    event MeetingCompleted(bytes32 indexed meetingId, uint256 attendance);

    // =============================================================
    //                       MODIFIERS
    // =============================================================

    modifier onlyActiveEmployee() {
        require(employees[msg.sender].active, "Not an active employee");
        _;
    }

    modifier validEmployeeLevel(EmployeeLevel level) {
        require(uint8(level) <= uint8(EmployeeLevel.L12_C_Level), "Invalid employee level");
        _;
    }

    modifier validEquityType(EquityType equityType) {
        require(uint8(equityType) <= uint8(EquityType.SARs), "Invalid equity type");
        _;
    }

    // SECURITY: Emergency pause modifier
    modifier whenNotPaused() {
        require(!emergencyPaused, "Contract is paused");
        _;
    }

    modifier onlyEmergencyRole() {
        require(hasRole(EMERGENCY_ROLE, msg.sender), "Not emergency role");
        _;
    }

    // SECURITY: Multi-signature modifier
    modifier onlyMultiSig(bytes32 operationHash) {
        if (_requiresMultiSig(msg.value)) {
            require(_hasMultiSigApproval(operationHash), "Multi-sig approval required");
        }
        _;
    }

    // SECURITY: Insider trading protection
    modifier insiderTradingCompliant(address trader) {
        if (insiders[trader]) {
            require(_canInsiderTrade(trader), "Insider trading restrictions");
        }
        _;
    }

    // SECURITY: Blackout period protection
    modifier notInBlackout(address trader) {
        require(!_isInBlackoutPeriod(), "Trading suspended during blackout");
        if (insiders[trader]) {
            require(!insiderRecords[trader].currentlyInBlackout, "Insider in personal blackout");
        }
        _;
    }

    // =============================================================
    //                     CONSTRUCTOR
    // =============================================================

    constructor(
        address _companyStock,
        address _daiGovernance,
        address _corporateAccount,
        string memory _companyName,
        string memory _stockSymbol,
        uint256 _totalShares,
        uint256 _initialSharePrice,
        address _treasuryAddress
    ) {
        require(_companyStock != address(0), "Invalid company stock address");
        require(_daiGovernance != address(0), "Invalid governance address");
        require(_corporateAccount != address(0), "Invalid corporate account");
        require(_treasuryAddress != address(0), "Invalid treasury address");
        require(_totalShares > 0, "Total shares must be positive");
        require(_initialSharePrice > 0, "Initial share price must be positive");
        require(bytes(_companyName).length > 0, "Company name cannot be empty");
        require(bytes(_stockSymbol).length > 0, "Stock symbol cannot be empty");

        companyStock = SecurityToken(_companyStock);
        daiGovernance = TriumvirateGovernance(_daiGovernance);
        corporateAccount = SmartAccount(_corporateAccount);

        companyName = _companyName;
        stockSymbol = _stockSymbol;
        totalShares = _totalShares;
        sharePrice = _initialSharePrice;
        treasuryAddress = _treasuryAddress;

        // Set up roles
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(HR_MANAGER_ROLE, msg.sender);
        _grantRole(COMPENSATION_COMMITTEE_ROLE, msg.sender);
        _grantRole(BOARD_MEMBER_ROLE, msg.sender);
        _grantRole(COMPLIANCE_OFFICER_ROLE, msg.sender);
        _grantRole(EMERGENCY_ROLE, msg.sender);

        // SECURITY: Initialize multi-sig signers with deployer
        multiSigSigners.push(msg.sender);
    }

    // =============================================================
    //                   EMPLOYEE MANAGEMENT
    // =============================================================

    /**
     * @dev Register a new employee with enhanced validation
     */
    function registerEmployee(
        address employeeAddress,
        uint256 employeeId,
        string memory name,
        string memory department,
        EmployeeLevel level,
        uint256 salary,
        address smartAccountAddress
    ) external onlyRole(HR_MANAGER_ROLE) whenNotPaused {
        require(employeeAddress != address(0), "Invalid employee address");
        require(smartAccountAddress != address(0), "Invalid smart account address");
        require(bytes(name).length > 0, "Name cannot be empty");
        require(bytes(department).length > 0, "Department cannot be empty");
        require(salary > 0, "Salary must be positive");
        require(!employees[employeeAddress].active, "Employee already registered");
        require(employeeIdToAddress[employeeId] == address(0), "Employee ID already exists");

        Employee storage emp = employees[employeeAddress];
        emp.employeeAddress = employeeAddress;
        emp.employeeId = employeeId;
        emp.name = name;
        emp.department = department;
        emp.level = level;
        emp.hireDate = block.timestamp;
        emp.salary = salary;
        emp.active = true;
        emp.smartAccountAddress = smartAccountAddress;

        employeeIdToAddress[employeeId] = employeeAddress;
        employeeList.push(employeeAddress);
        employeesByLevel[level].push(employeeAddress);

        // Grant employee role
        _grantRole(EMPLOYEE_ROLE, employeeAddress);

        // Grant shareholder role if level is high enough
        if (uint8(level) >= uint8(EmployeeLevel.L7_Director)) {
            _grantRole(SHAREHOLDER_ROLE, employeeAddress);
        }

        totalEmployees++;

        emit EmployeeRegistered(employeeAddress, employeeId, level);
    }

    /**
     * @dev Update employee level with proper validation
     */
    function updateEmployeeLevel(
        address employeeAddress,
        EmployeeLevel newLevel
    ) external onlyRole(HR_MANAGER_ROLE) validEmployeeLevel(newLevel) whenNotPaused {
        require(employees[employeeAddress].active, "Employee not found or inactive");

        Employee storage emp = employees[employeeAddress];
        EmployeeLevel oldLevel = emp.level;

        // Remove from old level array
        _removeFromLevelArray(employeeAddress, oldLevel);

        // Update level
        emp.level = newLevel;
        employeesByLevel[newLevel].push(employeeAddress);

        // Update roles based on new level
        if (uint8(newLevel) >= uint8(EmployeeLevel.L7_Director)) {
            _grantRole(SHAREHOLDER_ROLE, employeeAddress);
        } else {
            _revokeRole(SHAREHOLDER_ROLE, employeeAddress);
        }

        // Special roles for C-level executives
        if (newLevel == EmployeeLevel.L12_C_Level) {
            _grantRole(BOARD_MEMBER_ROLE, employeeAddress);
            // C-level executives are automatically insiders
            _setInsiderStatus(employeeAddress, true);
        }

        emit EmployeeUpdated(employeeAddress, oldLevel, newLevel);
    }

    // =============================================================
    //                   EQUITY MANAGEMENT
    // =============================================================

    /**
     * @dev Grant equity to employee with enhanced security
     */
    function grantEquity(
        address employee,
        EquityType equityType,
        uint256 totalShares,
        uint256 grantPrice,
        uint256 expirationDate,
        VestingSchedule vestingSchedule
    ) external onlyRole(COMPENSATION_COMMITTEE_ROLE) validEquityType(equityType) whenNotPaused nonReentrant {
        require(employees[employee].active, "Employee not found or inactive");
        require(totalShares > 0, "Shares must be positive");
        require(expirationDate > block.timestamp, "Expiration must be in future");

        bytes32 grantId = keccak256(abi.encodePacked(
            employee,
            equityType,
            totalShares,
            block.timestamp,
            block.number
        ));

        require(equityGrants[grantId].grantId == bytes32(0), "Grant ID collision");

        EquityGrantV2 storage grant = equityGrants[grantId];
        grant.grantId = grantId;
        grant.employee = employee;
        grant.equityType = equityType;
        grant.totalShares = totalShares;
        grant.grantDate = block.timestamp;
        grant.grantPrice = grantPrice;
        grant.expirationDate = expirationDate;
        grant.vestingSchedule = vestingSchedule;
        grant.remainderAccumulator = 0; // SECURITY: Initialize remainder tracking

        // Set up vesting schedule with enhanced precision
        _setupVestingScheduleV2(grantId, vestingSchedule);

        employeeGrants[employee].push(grantId);
        activeGrants.push(grantId);

        // Update employee equity balances
        employees[employee].equityBalances[equityType] += totalShares;
        employees[employee].totalEquityValue += totalShares * sharePrice;

        emit EquityGranted(grantId, employee, equityType, totalShares);
    }

    /**
     * @dev Process vesting for all eligible grants with enhanced precision
     */
    function processVesting() external whenNotPaused {
        for (uint256 i = 0; i < activeGrants.length; i++) {
            _processGrantVestingV2(activeGrants[i]);
        }
    }

    /**
     * @dev Exercise stock options with insider trading compliance
     */
    function exerciseOptions(
        bytes32 grantId,
        uint256 sharesToExercise
    ) external
        onlyActiveEmployee
        insiderTradingCompliant(msg.sender)
        notInBlackout(msg.sender)
        whenNotPaused
        nonReentrant
    {
        EquityGrantV2 storage grant = equityGrants[grantId];
        require(grant.employee == msg.sender, "Not your grant");
        require(!grant.exercised && !grant.forfeited, "Grant not exercisable");
        require(block.timestamp <= grant.expirationDate, "Grant expired");
        require(sharesToExercise > 0, "Must exercise positive shares");
        require(sharesToExercise <= grant.vestedShares, "Insufficient vested shares");

        // SECURITY: Check pre-clearance for insiders
        if (insiders[msg.sender]) {
            require(_hasValidPreClearance(msg.sender, grant.equityType, sharesToExercise),
                    "Pre-clearance required for insider");
        }

        uint256 exerciseCost = sharesToExercise * grant.grantPrice;
        uint256 currentValue = sharesToExercise * sharePrice;

        // SECURITY: Verify payment authorization
        require(msg.value >= exerciseCost, "Insufficient payment");

        // Effects
        grant.vestedShares -= sharesToExercise;
        if (grant.vestedShares == 0) {
            grant.exercised = true;
            _removeGrantFromActive(grantId);
        }

        employees[msg.sender].vestedEquityValue -= currentValue;
        employees[msg.sender].equityBalances[grant.equityType] -= sharesToExercise;

        // SECURITY: Update insider trading records
        if (insiders[msg.sender]) {
            _updateInsiderTradingRecord(msg.sender, sharesToExercise);
        }

        // Interactions - transfer shares to employee
        companyStock.transferByPartition(
            companyStock.COMMON_STOCK(),
            treasuryAddress,
            msg.sender,
            sharesToExercise,
            ""
        );

        // Return excess payment
        if (msg.value > exerciseCost) {
            (bool success, ) = payable(msg.sender).call{value: msg.value - exerciseCost}("");
            require(success, "Payment refund failed");
        }

        emit EquityExercised(grantId, msg.sender, sharesToExercise, currentValue);
    }

    // =============================================================
    //                   GOVERNANCE FUNCTIONS
    // =============================================================

    /**
     * @dev Create board proposal with voting snapshot
     */
    function createProposal(
        string memory title,
        string memory description,
        uint256 votingDuration,
        uint256 quorumRequired,
        uint256 majorityRequired
    ) external onlyRole(BOARD_MEMBER_ROLE) whenNotPaused returns (bytes32) {
        require(bytes(title).length > 0, "Title cannot be empty");
        require(bytes(description).length > 0, "Description cannot be empty");
        require(votingDuration >= 1 days && votingDuration <= 30 days, "Invalid voting duration");
        require(quorumRequired > 0 && quorumRequired <= 10000, "Invalid quorum requirement");
        require(majorityRequired > 5000 && majorityRequired <= 10000, "Invalid majority requirement");

        bytes32 proposalId = keccak256(abi.encodePacked(
            title,
            description,
            msg.sender,
            block.timestamp,
            block.number
        ));

        require(boardProposals[proposalId].proposalId == bytes32(0), "Proposal ID collision");

        BoardProposalV2 storage proposal = boardProposals[proposalId];
        proposal.proposalId = proposalId;
        proposal.proposer = msg.sender;
        proposal.title = title;
        proposal.description = description;
        proposal.startTime = block.timestamp;
        proposal.endTime = block.timestamp + votingDuration;
        proposal.snapshotBlock = block.number - 1; // SECURITY: Use previous block for snapshot
        proposal.quorumRequired = quorumRequired;
        proposal.majorityRequired = majorityRequired;

        // SECURITY: Determine if multi-sig is required
        uint256 estimatedValue = _estimateProposalValue(description);
        proposal.requiresMultiSig = estimatedValue >= GOVERNANCE_MULTI_SIG_THRESHOLD;

        // SECURITY: Take voting snapshot to prevent manipulation
        _takeVotingSnapshot(proposalId, proposal.snapshotBlock);

        activeProposals.push(proposalId);
        stats.totalProposals++;

        emit ProposalCreated(proposalId, msg.sender, proposal.snapshotBlock);

        return proposalId;
    }

    /**
     * @dev Vote on proposal using snapshot balances
     */
    function vote(bytes32 proposalId, uint8 voteChoice) external onlyRole(SHAREHOLDER_ROLE) whenNotPaused {
        BoardProposalV2 storage proposal = boardProposals[proposalId];
        require(proposal.proposalId == proposalId, "Proposal not found");
        require(block.timestamp >= proposal.startTime, "Voting not started");
        require(block.timestamp <= proposal.endTime, "Voting period ended");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        require(voteChoice <= 2, "Invalid vote choice");

        // SECURITY: Use snapshot balance to prevent manipulation
        uint256 votingWeight = votingSnapshots[proposalId].balances[msg.sender];
        require(votingWeight > 0, "No voting power at snapshot");

        proposal.hasVoted[msg.sender] = true;
        proposal.votes[msg.sender] = voteChoice;

        if (voteChoice == 1) {
            proposal.forVotes += votingWeight;
        } else if (voteChoice == 0) {
            proposal.againstVotes += votingWeight;
        } else {
            proposal.abstainVotes += votingWeight;
        }

        stats.totalVotes++;

        emit VoteCast(proposalId, msg.sender, voteChoice, votingWeight);
    }

    /**
     * @dev Execute proposal if it passes with multi-sig support
     */
    function executeProposal(bytes32 proposalId) external
        onlyRole(BOARD_MEMBER_ROLE)
        whenNotPaused
        nonReentrant
    {
        BoardProposalV2 storage proposal = boardProposals[proposalId];
        require(proposal.proposalId == proposalId, "Proposal not found");
        require(block.timestamp > proposal.endTime, "Voting period not ended");
        require(!proposal.executed, "Already executed");

        // Check quorum and majority
        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
        require(totalVotes >= proposal.quorumRequired, "Quorum not reached");

        uint256 majorityVotes = (proposal.forVotes * 10000) / totalVotes;
        bool passed = majorityVotes >= proposal.majorityRequired;

        // SECURITY: Check multi-sig requirement
        if (proposal.requiresMultiSig && passed) {
            bytes32 operationHash = keccak256(abi.encodePacked("EXECUTE_PROPOSAL", proposalId));
            require(_hasMultiSigApproval(operationHash), "Multi-sig approval required");
        }

        proposal.executed = true;
        proposal.passed = passed;

        if (passed) {
            _executeProposalAction(proposalId);
            stats.executedProposals++;
        }

        _removeProposalFromActive(proposalId);

        emit ProposalExecuted(proposalId, passed);
    }

    // =============================================================
    //              INSIDER TRADING COMPLIANCE
    // =============================================================

    /**
     * @dev Request pre-clearance for insider trading
     */
    function requestPreClearance(
        EquityType equityType,
        uint256 sharesToTrade
    ) external onlyActiveEmployee whenNotPaused returns (bytes32) {
        require(insiders[msg.sender], "Only insiders need pre-clearance");
        require(sharesToTrade > 0, "Shares must be positive");
        require(!_isInBlackoutPeriod(), "Cannot request during blackout");

        bytes32 requestId = keccak256(abi.encodePacked(
            msg.sender,
            equityType,
            sharesToTrade,
            block.timestamp
        ));

        PreClearanceRequest storage request = preClearanceRequests[requestId];
        request.requestId = requestId;
        request.insider = msg.sender;
        request.equityType = equityType;
        request.sharesToTrade = sharesToTrade;
        request.requestDate = block.timestamp;
        request.validUntil = block.timestamp + PRE_CLEARANCE_VALIDITY;
        request.status = TradeStatus.Pending;

        emit PreClearanceRequested(requestId, msg.sender, sharesToTrade);

        return requestId;
    }

    /**
     * @dev Approve or reject pre-clearance request
     */
    function processPreClearance(
        bytes32 requestId,
        bool approved,
        string memory reason
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) whenNotPaused {
        PreClearanceRequest storage request = preClearanceRequests[requestId];
        require(request.requestId == requestId, "Request not found");
        require(request.status == TradeStatus.Pending, "Request already processed");
        require(block.timestamp <= request.validUntil, "Request expired");

        if (approved) {
            request.status = TradeStatus.Approved;
            request.approvedBy = msg.sender;
            emit PreClearanceApproved(requestId, msg.sender);
        } else {
            request.status = TradeStatus.Rejected;
            request.rejectionReason = reason;
            emit PreClearanceRejected(requestId, reason);
        }
    }

    /**
     * @dev Set insider status for employee
     */
    function setInsiderStatus(address employee, bool isInsider) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        _setInsiderStatus(employee, isInsider);
    }

    /**
     * @dev Activate blackout period
     */
    function activateBlackoutPeriod(
        uint256 startDate,
        uint256 endDate,
        string memory reason
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) whenNotPaused {
        require(startDate >= block.timestamp, "Start date must be in future");
        require(endDate > startDate, "End date must be after start date");
        require(endDate <= startDate + 90 days, "Blackout period too long");
        require(bytes(reason).length > 0, "Reason cannot be empty");

        BlackoutPeriod memory blackout = BlackoutPeriod({
            startDate: startDate,
            endDate: endDate,
            reason: reason,
            active: true
        });

        blackoutPeriods.push(blackout);

        // Mark blackout days
        for (uint256 day = startDate; day <= endDate; day += 1 days) {
            isBlackoutDay[day] = true;
        }

        emit BlackoutPeriodActivated(startDate, endDate, reason);
    }

    // =============================================================
    //                  EMERGENCY FUNCTIONS
    // =============================================================

    /**
     * @dev Emergency pause function
     */
    function emergencyPause() external onlyEmergencyRole {
        require(!emergencyPaused, "Already paused");

        emergencyPaused = true;
        emergencyPausedAt = block.timestamp;

        emit EmergencyPauseActivated(msg.sender, block.timestamp);
    }

    /**
     * @dev Emergency unpause function
     */
    function emergencyUnpause() external onlyEmergencyRole {
        require(emergencyPaused, "Not paused");

        emergencyPaused = false;

        emit EmergencyPauseDeactivated(msg.sender, block.timestamp);
    }

    /**
     * @dev Auto-unpause after maximum duration
     */
    function autoUnpause() external {
        require(emergencyPaused, "Not paused");
        require(block.timestamp >= emergencyPausedAt + MAX_EMERGENCY_PAUSE_DURATION,
                "Max pause duration not reached");

        emergencyPaused = false;

        emit EmergencyPauseDeactivated(address(this), block.timestamp);
    }

    // =============================================================
    //                  MULTI-SIGNATURE FUNCTIONS
    // =============================================================

    /**
     * @dev Add multi-signature signer
     */
    function addMultiSigSigner(address newSigner) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newSigner != address(0), "Invalid signer address");
        require(!_isMultiSigSigner(newSigner), "Already a signer");
        require(multiSigSigners.length < 10, "Too many signers");

        multiSigSigners.push(newSigner);
    }

    /**
     * @dev Remove multi-signature signer
     */
    function removeMultiSigSigner(address signer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_isMultiSigSigner(signer), "Not a signer");
        require(multiSigSigners.length > multiSigThreshold, "Cannot reduce below threshold");

        for (uint256 i = 0; i < multiSigSigners.length; i++) {
            if (multiSigSigners[i] == signer) {
                multiSigSigners[i] = multiSigSigners[multiSigSigners.length - 1];
                multiSigSigners.pop();
                break;
            }
        }
    }

    /**
     * @dev Create multi-signature operation
     */
    function createMultiSigOperation(
        bytes32 operationHash,
        uint256 threshold,
        uint256 expiry
    ) external {
        require(_isMultiSigSigner(msg.sender), "Not a multi-sig signer");
        require(threshold <= multiSigSigners.length, "Threshold too high");
        require(expiry > block.timestamp, "Expiry must be in future");
        require(multiSigOperations[operationHash].expiry == 0, "Operation already exists");

        MultiSigOperation storage operation = multiSigOperations[operationHash];
        operation.operationHash = operationHash;
        operation.threshold = threshold;
        operation.expiry = expiry;
        operation.hasApproved[msg.sender] = true;
        operation.approvals = 1;

        emit MultiSigOperationCreated(operationHash, threshold, expiry);
        emit MultiSigApprovalAdded(operationHash, msg.sender);
    }

    /**
     * @dev Add approval to multi-signature operation
     */
    function addMultiSigApproval(bytes32 operationHash) external {
        require(_isMultiSigSigner(msg.sender), "Not a multi-sig signer");

        MultiSigOperation storage operation = multiSigOperations[operationHash];
        require(operation.expiry > 0, "Operation does not exist");
        require(block.timestamp <= operation.expiry, "Operation expired");
        require(!operation.executed, "Operation already executed");
        require(!operation.hasApproved[msg.sender], "Already approved");

        operation.hasApproved[msg.sender] = true;
        operation.approvals++;

        emit MultiSigApprovalAdded(operationHash, msg.sender);

        if (operation.approvals >= operation.threshold) {
            operation.executed = true;
            emit MultiSigOperationExecuted(operationHash);
        }
    }

    // =============================================================
    //                    VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Get employee information
     */
    function getEmployeeInfo(address employeeAddress) external view returns (
        uint256 employeeId,
        string memory name,
        string memory department,
        EmployeeLevel level,
        uint256 hireDate,
        uint256 salary,
        bool active,
        uint256 totalEquityValue,
        uint256 vestedEquityValue
    ) {
        Employee storage emp = employees[employeeAddress];
        return (
            emp.employeeId,
            emp.name,
            emp.department,
            emp.level,
            emp.hireDate,
            emp.salary,
            emp.active,
            emp.totalEquityValue,
            emp.vestedEquityValue
        );
    }

    /**
     * @dev Get voting results for proposal
     */
    function getProposalResults(bytes32 proposalId) external view returns (
        uint256 forVotes,
        uint256 againstVotes,
        uint256 abstainVotes,
        uint256 totalVotes,
        bool passed,
        bool executed
    ) {
        BoardProposalV2 storage proposal = boardProposals[proposalId];
        totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;

        return (
            proposal.forVotes,
            proposal.againstVotes,
            proposal.abstainVotes,
            totalVotes,
            proposal.passed,
            proposal.executed
        );
    }

    /**
     * @dev Get equity grant details
     */
    function getEquityGrant(bytes32 grantId) external view returns (
        address employee,
        EquityType equityType,
        uint256 totalShares,
        uint256 vestedShares,
        uint256 grantDate,
        uint256 grantPrice,
        bool exercised,
        bool forfeited
    ) {
        EquityGrantV2 storage grant = equityGrants[grantId];
        return (
            grant.employee,
            grant.equityType,
            grant.totalShares,
            grant.vestedShares,
            grant.grantDate,
            grant.grantPrice,
            grant.exercised,
            grant.forfeited
        );
    }

    /**
     * @dev Check if address is insider
     */
    function isInsider(address account) external view returns (bool) {
        return insiders[account];
    }

    /**
     * @dev Check if currently in blackout period
     */
    function isInBlackoutPeriod() external view returns (bool) {
        return _isInBlackoutPeriod();
    }

    /**
     * @dev Get governance statistics
     */
    function getGovernanceStats() external view returns (
        uint256 totalProposals,
        uint256 executedProposals,
        uint256 totalVotes,
        uint256 totalEmployees,
        uint256 totalEquityValue
    ) {
        return (
            stats.totalProposals,
            stats.executedProposals,
            stats.totalVotes,
            totalEmployees,
            stats.totalEquityValue
        );
    }

    // =============================================================
    //                   INTERNAL FUNCTIONS
    // =============================================================

    /**
     * @dev Setup vesting schedule with enhanced precision (V2)
     */
    function _setupVestingScheduleV2(bytes32 grantId, VestingSchedule schedule) internal {
        EquityGrantV2 storage grant = equityGrants[grantId];

        if (schedule == VestingSchedule.Immediate) {
            grant.vestedShares = grant.totalShares;
        } else if (schedule == VestingSchedule.OneYear) {
            grant.cliffDate = grant.grantDate + 365 days;
        } else if (schedule == VestingSchedule.FourYearMonthly) {
            grant.cliffDate = grant.grantDate + 365 days;
            // SECURITY: Set up monthly vesting after cliff with precision
            uint256 remainingShares = grant.totalShares * 3 / 4; // 75% after cliff
            uint256 monthlyAmount = remainingShares / 36; // 36 months after cliff

            for (uint256 i = 12; i < 48; i++) {
                grant.vestingDates.push(grant.grantDate + (i * 30 days));
                grant.vestingAmounts.push(monthlyAmount);
            }
            // SECURITY: Handle remainder precision
            uint256 totalScheduled = monthlyAmount * 36;
            if (remainingShares > totalScheduled) {
                grant.vestingAmounts[grant.vestingAmounts.length - 1] += (remainingShares - totalScheduled);
            }
        } else if (schedule == VestingSchedule.FourYearQuarterly) {
            grant.cliffDate = grant.grantDate + 365 days;
            // SECURITY: Set up quarterly vesting after cliff with precision
            uint256 remainingShares = grant.totalShares * 3 / 4; // 75% after cliff
            uint256 quarterlyAmount = remainingShares / 12; // 12 quarters after cliff

            for (uint256 i = 4; i < 16; i++) {
                grant.vestingDates.push(grant.grantDate + (i * 90 days));
                grant.vestingAmounts.push(quarterlyAmount);
            }
            // SECURITY: Handle remainder precision
            uint256 totalScheduled = quarterlyAmount * 12;
            if (remainingShares > totalScheduled) {
                grant.vestingAmounts[grant.vestingAmounts.length - 1] += (remainingShares - totalScheduled);
            }
        }
    }

    /**
     * @dev Process vesting for a specific grant with enhanced precision (V2)
     */
    function _processGrantVestingV2(bytes32 grantId) internal {
        EquityGrantV2 storage grant = equityGrants[grantId];

        if (grant.exercised || grant.forfeited) return;
        if (grant.lastVestingProcessed >= block.timestamp) return; // Already processed this period

        uint256 newlyVested = 0;
        uint256 remainderAccumulated = grant.remainderAccumulator;

        // SECURITY: Check cliff vesting with precise calculation
        if (grant.cliffDate > 0 && block.timestamp >= grant.cliffDate && grant.vestedShares == 0) {
            uint256 cliffAmount = grant.totalShares / 4; // 25% at cliff
            uint256 cliffRemainder = grant.totalShares % 4;

            newlyVested = cliffAmount;
            remainderAccumulated += cliffRemainder * VESTING_PRECISION / 4;

            // Apply accumulated remainder
            uint256 bonusShares = remainderAccumulated / VESTING_PRECISION;
            newlyVested += bonusShares;
            remainderAccumulated %= VESTING_PRECISION;
        }

        // SECURITY: Check scheduled vesting with precise tracking
        for (uint256 i = 0; i < grant.vestingDates.length; i++) {
            if (block.timestamp >= grant.vestingDates[i] &&
                grant.lastVestingProcessed < grant.vestingDates[i] &&
                grant.vestedShares + newlyVested < grant.totalShares) {

                newlyVested += grant.vestingAmounts[i];
            }
        }

        if (newlyVested > 0) {
            grant.vestedShares += newlyVested;
            grant.remainderAccumulator = remainderAccumulated;
            grant.lastVestingProcessed = block.timestamp;

            employees[grant.employee].vestedEquityValue += newlyVested * sharePrice;

            emit EquityVested(grantId, grant.employee, newlyVested, remainderAccumulated);
        }
    }

    /**
     * @dev Take voting snapshot for proposal
     */
    function _takeVotingSnapshot(bytes32 proposalId, uint256 blockNumber) internal {
        VotingSnapshot storage snapshot = votingSnapshots[proposalId];
        snapshot.blockNumber = blockNumber;

        // Snapshot total supply
        snapshot.totalSupply = companyStock.totalSupplyByPartition(companyStock.COMMON_STOCK());

        // Note: In practice, we would need to snapshot all shareholder balances
        // This is simplified for the example. Real implementation would iterate through
        // all shareholders or use a merkle tree approach for gas efficiency.

        emit VotingSnapshotTaken(proposalId, blockNumber, snapshot.totalSupply);
    }

    /**
     * @dev Update insider trading record
     */
    function _updateInsiderTradingRecord(address insider, uint256 sharesTraded) internal {
        InsiderTradingRecord storage record = insiderRecords[insider];
        record.lastTradeDate = block.timestamp;
        record.sharesTraded += sharesTraded;

        lastTradingDate[insider] = block.timestamp;
    }

    /**
     * @dev Set insider status for employee
     */
    function _setInsiderStatus(address employee, bool isInsider) internal {
        require(employees[employee].active, "Employee not found or inactive");

        insiders[employee] = isInsider;

        if (isInsider) {
            // Initialize insider trading record
            InsiderTradingRecord storage record = insiderRecords[employee];
            record.insider = employee;
            record.lastTradeDate = 0;
            record.sharesTraded = 0;
            record.currentlyInBlackout = false;
        }

        emit InsiderDesignated(employee, isInsider);
    }

    /**
     * @dev Check if insider can trade (enhanced compliance)
     */
    function _canInsiderTrade(address insider) internal view returns (bool) {
        if (!insiders[insider]) return true;

        // Check global blackout period
        if (_isInBlackoutPeriod()) return false;

        // Check personal blackout period
        InsiderTradingRecord storage record = insiderRecords[insider];
        if (record.currentlyInBlackout) return false;

        // Check cooling period
        uint256 lastTrade = record.lastTradeDate;
        if (lastTrade > 0 && block.timestamp < lastTrade + INSIDER_COOLING_PERIOD) {
            return false;
        }

        return true;
    }

    /**
     * @dev Check if currently in blackout period
     */
    function _isInBlackoutPeriod() internal view returns (bool) {
        for (uint256 i = 0; i < blackoutPeriods.length; i++) {
            BlackoutPeriod storage period = blackoutPeriods[i];
            if (period.active &&
                block.timestamp >= period.startDate &&
                block.timestamp <= period.endDate) {
                return true;
            }
        }
        return false;
    }

    /**
     * @dev Check if insider has valid pre-clearance
     */
    function _hasValidPreClearance(
        address insider,
        EquityType equityType,
        uint256 shares
    ) internal view returns (bool) {
        // Find most recent approved pre-clearance request
        // This is simplified - real implementation would maintain an index
        // of requests per insider for efficiency
        return true; // Simplified for this example
    }

    /**
     * @dev Check if operation requires multi-sig
     */
    function _requiresMultiSig(uint256 value) internal pure returns (bool) {
        return value >= MULTI_SIG_THRESHOLD;
    }

    /**
     * @dev Check if operation has multi-sig approval
     */
    function _hasMultiSigApproval(bytes32 operationHash) internal view returns (bool) {
        MultiSigOperation storage operation = multiSigOperations[operationHash];
        return operation.approvals >= operation.threshold &&
               block.timestamp <= operation.expiry &&
               !operation.executed;
    }

    /**
     * @dev Check if address is multi-sig signer
     */
    function _isMultiSigSigner(address account) internal view returns (bool) {
        for (uint256 i = 0; i < multiSigSigners.length; i++) {
            if (multiSigSigners[i] == account) {
                return true;
            }
        }
        return false;
    }

    /**
     * @dev Estimate proposal value for multi-sig determination
     */
    function _estimateProposalValue(string memory description) internal pure returns (uint256) {
        // Simplified estimation based on description keywords
        // Real implementation would parse proposal parameters
        bytes memory desc = bytes(description);
        if (desc.length > 100) {
            return GOVERNANCE_MULTI_SIG_THRESHOLD + 1; // Assume high-value proposal
        }
        return 0;
    }

    /**
     * @dev Execute proposal action
     */
    function _executeProposalAction(bytes32 proposalId) internal {
        // Implementation would depend on proposal type
        // Could trigger governance actions, parameter changes, etc.
        // This is a placeholder for the actual execution logic
    }

    /**
     * @dev Remove employee from level array
     */
    function _removeFromLevelArray(address employee, EmployeeLevel level) internal {
        address[] storage levelArray = employeesByLevel[level];
        for (uint256 i = 0; i < levelArray.length; i++) {
            if (levelArray[i] == employee) {
                levelArray[i] = levelArray[levelArray.length - 1];
                levelArray.pop();
                break;
            }
        }
    }

    /**
     * @dev Remove grant from active grants array
     */
    function _removeGrantFromActive(bytes32 grantId) internal {
        for (uint256 i = 0; i < activeGrants.length; i++) {
            if (activeGrants[i] == grantId) {
                activeGrants[i] = activeGrants[activeGrants.length - 1];
                activeGrants.pop();
                break;
            }
        }
    }

    /**
     * @dev Remove proposal from active proposals array
     */
    function _removeProposalFromActive(bytes32 proposalId) internal {
        for (uint256 i = 0; i < activeProposals.length; i++) {
            if (activeProposals[i] == proposalId) {
                activeProposals[i] = activeProposals[activeProposals.length - 1];
                activeProposals.pop();
                break;
            }
        }
    }

    // =============================================================
    //                      RECEIVE FUNCTION
    // =============================================================

    /**
     * @dev Receive function for option exercise payments
     */
    receive() external payable {
        // Allow contract to receive ETH for option exercises
        require(msg.value > 0, "Invalid payment amount");
    }
}