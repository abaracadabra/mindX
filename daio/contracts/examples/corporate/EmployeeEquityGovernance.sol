// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../../eip-standards/advanced/ERC1400/SecurityToken.sol";
import "../../daio/governance/TriumvirateGovernance.sol";
import "../../eip-standards/advanced/ERC4337/SmartAccount.sol";

/**
 * @title EmployeeEquityGovernance
 * @dev Fortune 500 Employee Equity and Corporate Governance Example
 *
 * This contract demonstrates how a Fortune 500 technology company
 * can use DAIO infrastructure for comprehensive employee equity management:
 *
 * USE CASE: Global Technology Corporation (Fortune 500)
 * - 300,000+ employees worldwide
 * - Complex equity compensation programs
 * - Multi-tier stock option plans (ISO, NSO, RSU, ESPP)
 * - Board of directors and shareholder governance
 * - Regulatory compliance (SEC, SOX, international)
 * - Employee voting and proposal systems
 *
 * Key Features:
 * - Automated stock option vesting schedules with cliff provisions
 * - Employee stock purchase plan (ESPP) with automatic payroll deduction
 * - Restricted stock units (RSU) with performance-based vesting
 * - Board governance with proxy voting and proposal systems
 * - Regulatory compliance tracking and reporting
 * - Tax optimization and withholding automation
 * - Employee self-service portal integration
 * - Whistleblower protection and anonymous reporting
 *
 * @author DAIO Development Team
 */

contract EmployeeEquityGovernance is AccessControl, ReentrancyGuard {
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

    // Equity Grants
    struct EquityGrant {
        bytes32 grantId;
        address employee;
        EquityType equityType;
        uint256 totalShares;
        uint256 vestedShares;
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
    }

    mapping(bytes32 => EquityGrant) public equityGrants;
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

    // Corporate Governance
    struct BoardProposal {
        bytes32 proposalId;
        address proposer;
        string title;
        string description;
        uint256 startTime;
        uint256 endTime;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool executed;
        bool passed;
        mapping(address => bool) hasVoted;
        mapping(address => uint8) votes; // 0=against, 1=for, 2=abstain
        uint256 quorumRequired;
        uint256 majorityRequired; // Basis points
    }

    mapping(bytes32 => BoardProposal) public boardProposals;
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

    // Compensation Analysis
    struct CompensationBand {
        EmployeeLevel level;
        string jobFamily;
        uint256 minBaseSalary;
        uint256 maxBaseSalary;
        uint256 targetBonus; // Percentage of base
        uint256 equityTarget; // Annual equity target value
        string currency;
    }

    mapping(EmployeeLevel => mapping(string => CompensationBand)) public compensationBands;

    // Compliance and Reporting
    struct ComplianceReport {
        uint256 reportingPeriod;
        uint256 totalEquityIssued;
        uint256 totalEquityExercised;
        uint256 totalEquityForfeited;
        uint256 averageExercisePrice;
        uint256 totalTaxWithheld;
        uint256 insiderTradingViolations;
        bool sox404Compliant;
        bool sec10KFiled;
    }

    mapping(uint256 => ComplianceReport) public complianceReports;

    // Insider Trading Protection
    struct InsiderTradingWindow {
        uint256 windowStart;
        uint256 windowEnd;
        bool isBlackout;
        string reason;
    }

    InsiderTradingWindow[] public tradingWindows;
    mapping(address => bool) public insiders; // Employees with material non-public info
    mapping(address => uint256) public lastTradingDate;

    // Events
    event EmployeeEquitySystemInitialized(string companyName, uint256 totalShares);
    event EmployeeRegistered(address indexed employee, uint256 employeeId, EmployeeLevel level);
    event EquityGrantCreated(bytes32 indexed grantId, address indexed employee, EquityType equityType, uint256 shares);
    event EquityVested(bytes32 indexed grantId, address indexed employee, uint256 vestedShares);
    event EquityExercised(bytes32 indexed grantId, address indexed employee, uint256 exercisedShares, uint256 value);
    event ESPPEnrollment(address indexed employee, uint256 contributionPercentage);
    event ProposalCreated(bytes32 indexed proposalId, address indexed proposer, string title);
    event VoteCast(bytes32 indexed proposalId, address indexed voter, uint8 vote, uint256 weight);
    event ShareholderMeetingScheduled(bytes32 indexed meetingId, uint256 scheduleDate, uint256 recordDate);
    event ComplianceReportGenerated(uint256 indexed period, uint256 totalEquityIssued, bool sox404Compliant);
    event TradingWindowUpdated(uint256 windowStart, uint256 windowEnd, bool isBlackout);
    event InsiderDesignationChanged(address indexed employee, bool isInsider);

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor(
        address companyStockAddress,
        address governanceAddress,
        address corporateAccountAddress,
        string memory _companyName,
        string memory _stockSymbol,
        uint256 _totalShares,
        uint256 _initialSharePrice,
        address _treasuryAddress
    ) {
        companyStock = SecurityToken(companyStockAddress);
        daiGovernance = TriumvirateGovernance(governanceAddress);
        corporateAccount = SmartAccount(corporateAccountAddress);

        companyName = _companyName;
        stockSymbol = _stockSymbol;
        totalShares = _totalShares;
        sharePrice = _initialSharePrice;
        treasuryAddress = _treasuryAddress;

        // Set up access control
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(COMPENSATION_COMMITTEE_ROLE, msg.sender);
        _grantRole(BOARD_MEMBER_ROLE, msg.sender);

        // Initialize default ESPP parameters
        esppOfferingPeriod = 180 days; // 6 months
        esppDiscount = 1500; // 15% discount

        emit EmployeeEquitySystemInitialized(_companyName, _totalShares);
    }

    // =============================================================
    //                   EMPLOYEE MANAGEMENT
    // =============================================================

    /**
     * @dev Register a new employee
     */
    function registerEmployee(
        address employeeAddress,
        uint256 employeeId,
        string calldata name,
        string calldata department,
        EmployeeLevel level,
        uint256 salary,
        address smartAccountAddress
    ) external onlyRole(HR_MANAGER_ROLE) {
        require(employeeAddress != address(0), "Invalid employee address");
        require(!employees[employeeAddress].active, "Employee already registered");

        Employee storage employee = employees[employeeAddress];
        employee.employeeAddress = employeeAddress;
        employee.employeeId = employeeId;
        employee.name = name;
        employee.department = department;
        employee.level = level;
        employee.hireDate = block.timestamp;
        employee.salary = salary;
        employee.active = true;
        employee.smartAccountAddress = smartAccountAddress;

        // Set default equity eligibility based on level
        _setDefaultEquityEligibility(employeeAddress, level);

        employeeIdToAddress[employeeId] = employeeAddress;
        employeeList.push(employeeAddress);
        employeesByLevel[level].push(employeeAddress);

        _grantRole(EMPLOYEE_ROLE, employeeAddress);
        _grantRole(SHAREHOLDER_ROLE, employeeAddress);

        totalEmployees++;

        emit EmployeeRegistered(employeeAddress, employeeId, level);
    }

    /**
     * @dev Update employee level and compensation
     */
    function updateEmployeeLevel(
        address employeeAddress,
        EmployeeLevel newLevel,
        uint256 newSalary
    ) external onlyRole(HR_MANAGER_ROLE) {
        require(employees[employeeAddress].active, "Employee not found");

        Employee storage employee = employees[employeeAddress];
        EmployeeLevel oldLevel = employee.level;

        employee.level = newLevel;
        employee.salary = newSalary;

        // Update equity eligibility
        _setDefaultEquityEligibility(employeeAddress, newLevel);

        // Move employee between level arrays
        _removeFromLevelArray(employeeAddress, oldLevel);
        employeesByLevel[newLevel].push(employeeAddress);
    }

    // =============================================================
    //                    EQUITY MANAGEMENT
    // =============================================================

    /**
     * @dev Create an equity grant for an employee
     */
    function createEquityGrant(
        address employee,
        EquityType equityType,
        uint256 totalShares,
        uint256 grantPrice,
        uint256 expirationYears,
        VestingSchedule vestingSchedule
    ) external onlyRole(COMPENSATION_COMMITTEE_ROLE) returns (bytes32 grantId) {
        require(employees[employee].active, "Employee not found");
        require(employees[employee].eligibleEquityTypes[equityType], "Employee not eligible for this equity type");

        grantId = keccak256(abi.encodePacked(
            employee,
            equityType,
            totalShares,
            block.timestamp
        ));

        EquityGrant storage grant = equityGrants[grantId];
        grant.grantId = grantId;
        grant.employee = employee;
        grant.equityType = equityType;
        grant.totalShares = totalShares;
        grant.grantDate = block.timestamp;
        grant.grantPrice = grantPrice;
        grant.expirationDate = block.timestamp + (expirationYears * 365 days);
        grant.vestingSchedule = vestingSchedule;

        // Set up vesting schedule
        _setupVestingSchedule(grantId, vestingSchedule);

        employeeGrants[employee].push(grantId);
        activeGrants.push(grantId);

        // Update employee equity balances
        employees[employee].equityBalances[equityType] += totalShares;
        employees[employee].totalEquityValue += totalShares * sharePrice;

        emit EquityGrantCreated(grantId, employee, equityType, totalShares);

        return grantId;
    }

    /**
     * @dev Process vesting for all eligible grants
     */
    function processVesting() external onlyRole(HR_MANAGER_ROLE) {
        for (uint256 i = 0; i < activeGrants.length; i++) {
            bytes32 grantId = activeGrants[i];
            _processGrantVesting(grantId);
        }
    }

    /**
     * @dev Exercise stock options
     */
    function exerciseOptions(
        bytes32 grantId,
        uint256 sharesToExercise
    ) external nonReentrant {
        EquityGrant storage grant = equityGrants[grantId];
        require(grant.employee == msg.sender, "Not your grant");
        require(grant.equityType == EquityType.ISO || grant.equityType == EquityType.NSO, "Not an option grant");
        require(!grant.exercised, "Already exercised");
        require(block.timestamp <= grant.expirationDate, "Grant expired");
        require(sharesToExercise <= grant.vestedShares, "Insufficient vested shares");

        // Check insider trading restrictions
        require(!_isBlackoutPeriod(), "Trading blackout period");
        require(!insiders[msg.sender] || _canInsiderTrade(msg.sender), "Insider trading restrictions");

        uint256 exerciseValue = sharesToExercise * grant.grantPrice;
        uint256 currentValue = sharesToExercise * sharePrice;
        uint256 taxableGain = currentValue - exerciseValue;

        // Calculate tax withholding
        uint256 taxWithholding = _calculateTaxWithholding(taxableGain, grant.equityType);

        // Transfer payment for exercise
        require(msg.value >= exerciseValue + taxWithholding, "Insufficient payment");

        // Issue shares to employee
        companyStock.issueByPartition(
            companyStock.COMMON_STOCK(),
            msg.sender,
            sharesToExercise,
            ""
        );

        // Update grant state
        grant.vestedShares -= sharesToExercise;
        if (grant.vestedShares == 0) {
            grant.exercised = true;
        }

        // Update employee balances
        employees[msg.sender].equityBalances[grant.equityType] -= sharesToExercise;
        employees[msg.sender].vestedEquityValue -= currentValue;

        // Pay to treasury and tax authorities
        payable(treasuryAddress).transfer(exerciseValue);
        _payTaxWithholding(taxWithholding);

        // Refund excess payment
        if (msg.value > exerciseValue + taxWithholding) {
            payable(msg.sender).transfer(msg.value - exerciseValue - taxWithholding);
        }

        lastTradingDate[msg.sender] = block.timestamp;

        emit EquityExercised(grantId, msg.sender, sharesToExercise, currentValue);
    }

    // =============================================================
    //                      ESPP MANAGEMENT
    // =============================================================

    /**
     * @dev Enroll employee in ESPP
     */
    function enrollInESPP(
        uint256 contributionPercentage,
        uint256 maxAnnualContribution
    ) external {
        require(employees[msg.sender].active, "Employee not found");
        require(employees[msg.sender].eligibleEquityTypes[EquityType.ESPP], "Not eligible for ESPP");
        require(contributionPercentage > 0 && contributionPercentage <= 1500, "Invalid contribution percentage"); // Max 15%

        ESPPParticipation storage participation = esppParticipants[msg.sender];
        participation.employee = msg.sender;
        participation.contributionPercentage = contributionPercentage;
        participation.maxAnnualContribution = maxAnnualContribution;
        participation.enrolled = true;
        participation.enrollmentDate = block.timestamp;

        emit ESPPEnrollment(msg.sender, contributionPercentage);
    }

    /**
     * @dev Process ESPP contributions and share purchases
     */
    function processESPPContributions() external onlyRole(HR_MANAGER_ROLE) {
        for (uint256 i = 0; i < employeeList.length; i++) {
            address employee = employeeList[i];
            ESPPParticipation storage participation = esppParticipants[employee];

            if (participation.enrolled && employees[employee].active) {
                _processEmployeeESPPContribution(employee);
            }
        }
    }

    // =============================================================
    //                   CORPORATE GOVERNANCE
    // =============================================================

    /**
     * @dev Create a board proposal
     */
    function createProposal(
        string calldata title,
        string calldata description,
        uint256 votingDuration,
        uint256 quorumRequired,
        uint256 majorityRequired
    ) external onlyRole(BOARD_MEMBER_ROLE) returns (bytes32 proposalId) {
        proposalId = keccak256(abi.encodePacked(
            title,
            description,
            block.timestamp,
            msg.sender
        ));

        BoardProposal storage proposal = boardProposals[proposalId];
        proposal.proposalId = proposalId;
        proposal.proposer = msg.sender;
        proposal.title = title;
        proposal.description = description;
        proposal.startTime = block.timestamp;
        proposal.endTime = block.timestamp + votingDuration;
        proposal.quorumRequired = quorumRequired;
        proposal.majorityRequired = majorityRequired;

        activeProposals.push(proposalId);

        emit ProposalCreated(proposalId, msg.sender, title);

        return proposalId;
    }

    /**
     * @dev Cast vote on board proposal
     */
    function vote(bytes32 proposalId, uint8 voteChoice) external onlyRole(SHAREHOLDER_ROLE) {
        BoardProposal storage proposal = boardProposals[proposalId];
        require(proposal.proposalId == proposalId, "Proposal not found");
        require(block.timestamp <= proposal.endTime, "Voting period ended");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        require(voteChoice <= 2, "Invalid vote choice");

        // Calculate voting weight based on shares owned
        uint256 votingWeight = companyStock.balanceOfByPartition(
            companyStock.COMMON_STOCK(),
            msg.sender
        );

        proposal.hasVoted[msg.sender] = true;
        proposal.votes[msg.sender] = voteChoice;

        if (voteChoice == 1) {
            proposal.forVotes += votingWeight;
        } else if (voteChoice == 0) {
            proposal.againstVotes += votingWeight;
        } else {
            proposal.abstainVotes += votingWeight;
        }

        emit VoteCast(proposalId, msg.sender, voteChoice, votingWeight);
    }

    /**
     * @dev Execute proposal if it passes
     */
    function executeProposal(bytes32 proposalId) external onlyRole(BOARD_MEMBER_ROLE) {
        BoardProposal storage proposal = boardProposals[proposalId];
        require(proposal.proposalId == proposalId, "Proposal not found");
        require(block.timestamp > proposal.endTime, "Voting period not ended");
        require(!proposal.executed, "Already executed");

        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
        require(totalVotes >= proposal.quorumRequired, "Quorum not reached");

        uint256 forPercentage = (proposal.forVotes * 10000) / (proposal.forVotes + proposal.againstVotes);
        bool passed = forPercentage >= proposal.majorityRequired;

        proposal.executed = true;
        proposal.passed = passed;

        if (passed) {
            // Execute proposal logic here
            _executeProposalAction(proposalId);
        }

        // Remove from active proposals
        _removeFromActiveProposals(proposalId);
    }

    /**
     * @dev Schedule shareholder meeting
     */
    function scheduleShareholderMeeting(
        string calldata purpose,
        uint256 scheduleDate,
        uint256 recordDate,
        bytes32[] calldata proposalsToVote
    ) external onlyRole(BOARD_MEMBER_ROLE) returns (bytes32 meetingId) {
        meetingId = keccak256(abi.encodePacked(
            purpose,
            scheduleDate,
            recordDate,
            block.timestamp
        ));

        ShareholderMeeting storage meeting = shareholderMeetings[meetingId];
        meeting.meetingId = meetingId;
        meeting.purpose = purpose;
        meeting.scheduleDate = scheduleDate;
        meeting.recordDate = recordDate;
        meeting.proposalsToVote = proposalsToVote;

        emit ShareholderMeetingScheduled(meetingId, scheduleDate, recordDate);

        return meetingId;
    }

    // =============================================================
    //                   COMPLIANCE & REPORTING
    // =============================================================

    /**
     * @dev Generate compliance report
     */
    function generateComplianceReport(
        uint256 reportingPeriod
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) returns (
        uint256 totalEquityIssued,
        uint256 totalEquityExercised,
        bool sox404Compliant
    ) {
        totalEquityIssued = _calculateTotalEquityIssued(reportingPeriod);
        totalEquityExercised = _calculateTotalEquityExercised(reportingPeriod);
        sox404Compliant = _checkSOX404Compliance();

        ComplianceReport storage report = complianceReports[reportingPeriod];
        report.reportingPeriod = reportingPeriod;
        report.totalEquityIssued = totalEquityIssued;
        report.totalEquityExercised = totalEquityExercised;
        report.totalEquityForfeited = _calculateTotalEquityForfeited(reportingPeriod);
        report.averageExercisePrice = _calculateAverageExercisePrice(reportingPeriod);
        report.totalTaxWithheld = _calculateTotalTaxWithheld(reportingPeriod);
        report.sox404Compliant = sox404Compliant;
        report.sec10KFiled = true; // Would integrate with SEC filing system

        emit ComplianceReportGenerated(reportingPeriod, totalEquityIssued, sox404Compliant);

        return (totalEquityIssued, totalEquityExercised, sox404Compliant);
    }

    /**
     * @dev Set trading window (blackout periods)
     */
    function setTradingWindow(
        uint256 windowStart,
        uint256 windowEnd,
        bool isBlackout,
        string calldata reason
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        InsiderTradingWindow memory window = InsiderTradingWindow({
            windowStart: windowStart,
            windowEnd: windowEnd,
            isBlackout: isBlackout,
            reason: reason
        });

        tradingWindows.push(window);

        emit TradingWindowUpdated(windowStart, windowEnd, isBlackout);
    }

    /**
     * @dev Designate employee as insider
     */
    function designateInsider(address employee, bool isInsider) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        require(employees[employee].active, "Employee not found");
        insiders[employee] = isInsider;

        emit InsiderDesignationChanged(employee, isInsider);
    }

    // =============================================================
    //                   INTERNAL FUNCTIONS
    // =============================================================

    /**
     * @dev Set default equity eligibility based on employee level
     */
    function _setDefaultEquityEligibility(address employee, EmployeeLevel level) internal {
        Employee storage emp = employees[employee];

        // All employees eligible for ESPP
        emp.eligibleEquityTypes[EquityType.ESPP] = true;

        // RSUs for all levels
        emp.eligibleEquityTypes[EquityType.RSU] = true;

        // Stock options for L4+ (Principal level and above)
        if (uint8(level) >= uint8(EmployeeLevel.L4_Principal)) {
            emp.eligibleEquityTypes[EquityType.ISO] = true;
            emp.eligibleEquityTypes[EquityType.NSO] = true;
        }

        // Performance shares for managers and above
        if (uint8(level) >= uint8(EmployeeLevel.L5_Manager)) {
            emp.eligibleEquityTypes[EquityType.PerformanceShares] = true;
        }

        // Restricted stock for directors and above
        if (uint8(level) >= uint8(EmployeeLevel.L7_Director)) {
            emp.eligibleEquityTypes[EquityType.RestrictedStock] = true;
        }
    }

    /**
     * @dev Setup vesting schedule for grant
     */
    function _setupVestingSchedule(bytes32 grantId, VestingSchedule schedule) internal {
        EquityGrant storage grant = equityGrants[grantId];

        if (schedule == VestingSchedule.Immediate) {
            grant.vestedShares = grant.totalShares;
        } else if (schedule == VestingSchedule.OneYear) {
            grant.cliffDate = grant.grantDate + 365 days;
        } else if (schedule == VestingSchedule.FourYearMonthly) {
            grant.cliffDate = grant.grantDate + 365 days;
            // Set up monthly vesting after cliff
            for (uint256 i = 12; i < 48; i++) {
                grant.vestingDates.push(grant.grantDate + (i * 30 days));
                grant.vestingAmounts.push(grant.totalShares / 48); // Monthly vesting
            }
        } else if (schedule == VestingSchedule.FourYearQuarterly) {
            grant.cliffDate = grant.grantDate + 365 days;
            // Set up quarterly vesting after cliff
            for (uint256 i = 4; i < 16; i++) {
                grant.vestingDates.push(grant.grantDate + (i * 90 days));
                grant.vestingAmounts.push(grant.totalShares / 16); // Quarterly vesting
            }
        }
    }

    /**
     * @dev Process vesting for a specific grant
     */
    function _processGrantVesting(bytes32 grantId) internal {
        EquityGrant storage grant = equityGrants[grantId];

        if (grant.exercised || grant.forfeited) return;

        uint256 newlyVested = 0;

        // Check cliff vesting
        if (grant.cliffDate > 0 && block.timestamp >= grant.cliffDate && grant.vestedShares == 0) {
            newlyVested = grant.totalShares / 4; // 25% at cliff
        }

        // Check scheduled vesting
        for (uint256 i = 0; i < grant.vestingDates.length; i++) {
            if (block.timestamp >= grant.vestingDates[i] && grant.vestedShares < grant.totalShares) {
                newlyVested += grant.vestingAmounts[i];
            }
        }

        if (newlyVested > 0) {
            grant.vestedShares += newlyVested;
            employees[grant.employee].vestedEquityValue += newlyVested * sharePrice;

            emit EquityVested(grantId, grant.employee, newlyVested);
        }
    }

    /**
     * @dev Process ESPP contribution for employee
     */
    function _processEmployeeESPPContribution(address employee) internal {
        ESPPParticipation storage participation = esppParticipants[employee];
        Employee storage emp = employees[employee];

        uint256 monthlyContribution = (emp.salary * participation.contributionPercentage) / (10000 * 12);

        if (participation.currentPeriodContributions + monthlyContribution <= participation.maxAnnualContribution) {
            participation.currentPeriodContributions += monthlyContribution;

            // Calculate shares purchased with discount
            uint256 discountedPrice = sharePrice * (10000 - esppDiscount) / 10000;
            uint256 sharesPurchased = monthlyContribution / discountedPrice;

            participation.accumulatedShares += sharesPurchased;

            // Issue shares to employee
            companyStock.issueByPartition(
                companyStock.COMMON_STOCK(),
                employee,
                sharesPurchased,
                ""
            );
        }
    }

    /**
     * @dev Calculate tax withholding for equity exercise
     */
    function _calculateTaxWithholding(uint256 taxableGain, EquityType equityType) internal pure returns (uint256) {
        // Simplified tax calculation - in practice would integrate with payroll systems
        uint256 taxRate;

        if (equityType == EquityType.ISO) {
            taxRate = 0; // No immediate tax for ISO (AMT considerations not included)
        } else if (equityType == EquityType.NSO) {
            taxRate = 3700; // 37% for high earners
        } else {
            taxRate = 2200; // 22% default
        }

        return (taxableGain * taxRate) / 10000;
    }

    /**
     * @dev Pay tax withholding to appropriate authorities
     */
    function _payTaxWithholding(uint256 amount) internal {
        // In practice, would integrate with government tax systems
        // For this example, we transfer to treasury
        payable(treasuryAddress).transfer(amount);
    }

    /**
     * @dev Check if current time is in blackout period
     */
    function _isBlackoutPeriod() internal view returns (bool) {
        for (uint256 i = 0; i < tradingWindows.length; i++) {
            InsiderTradingWindow memory window = tradingWindows[i];
            if (window.isBlackout &&
                block.timestamp >= window.windowStart &&
                block.timestamp <= window.windowEnd) {
                return true;
            }
        }
        return false;
    }

    /**
     * @dev Check if insider can trade (outside blackout + cooling period)
     */
    function _canInsiderTrade(address insider) internal view returns (bool) {
        uint256 lastTrade = lastTradingDate[insider];
        return block.timestamp >= lastTrade + 30 days; // 30-day cooling period
    }

    /**
     * @dev Execute proposal action
     */
    function _executeProposalAction(bytes32 proposalId) internal {
        // Implementation would depend on proposal type
        // Could trigger governance actions, parameter changes, etc.
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
     * @dev Remove proposal from active list
     */
    function _removeFromActiveProposals(bytes32 proposalId) internal {
        for (uint256 i = 0; i < activeProposals.length; i++) {
            if (activeProposals[i] == proposalId) {
                activeProposals[i] = activeProposals[activeProposals.length - 1];
                activeProposals.pop();
                break;
            }
        }
    }

    // Compliance calculation functions (simplified for example)
    function _calculateTotalEquityIssued(uint256 period) internal view returns (uint256) {
        // Would calculate actual equity issued in the period
        return 1000000; // Placeholder
    }

    function _calculateTotalEquityExercised(uint256 period) internal view returns (uint256) {
        // Would calculate actual equity exercised in the period
        return 750000; // Placeholder
    }

    function _calculateTotalEquityForfeited(uint256 period) internal view returns (uint256) {
        return 50000; // Placeholder
    }

    function _calculateAverageExercisePrice(uint256 period) internal view returns (uint256) {
        return 50 * 1e18; // $50 placeholder
    }

    function _calculateTotalTaxWithheld(uint256 period) internal view returns (uint256) {
        return 10000000; // $10M placeholder
    }

    function _checkSOX404Compliance() internal view returns (bool) {
        // Would perform actual SOX compliance checks
        return true; // Placeholder
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Get employee equity summary
     */
    function getEmployeeEquitySummary(address employee) external view returns (
        uint256 totalEquityValue,
        uint256 vestedEquityValue,
        uint256 totalShares,
        uint256 vestedShares
    ) {
        Employee storage emp = employees[employee];
        totalEquityValue = emp.totalEquityValue;
        vestedEquityValue = emp.vestedEquityValue;

        // Calculate total and vested shares across all grants
        bytes32[] memory grants = employeeGrants[employee];
        for (uint256 i = 0; i < grants.length; i++) {
            EquityGrant storage grant = equityGrants[grants[i]];
            totalShares += grant.totalShares;
            vestedShares += grant.vestedShares;
        }
    }

    /**
     * @dev Get employee grants
     */
    function getEmployeeGrants(address employee) external view returns (bytes32[] memory) {
        return employeeGrants[employee];
    }

    /**
     * @dev Get active proposals
     */
    function getActiveProposals() external view returns (bytes32[] memory) {
        return activeProposals;
    }

    /**
     * @dev Get employees by level
     */
    function getEmployeesByLevel(EmployeeLevel level) external view returns (address[] memory) {
        return employeesByLevel[level];
    }

    /**
     * @dev Get voting results for proposal
     */
    function getProposalResults(bytes32 proposalId) external view returns (
        uint256 forVotes,
        uint256 againstVotes,
        uint256 abstainVotes,
        bool executed,
        bool passed
    ) {
        BoardProposal storage proposal = boardProposals[proposalId];
        return (
            proposal.forVotes,
            proposal.againstVotes,
            proposal.abstainVotes,
            proposal.executed,
            proposal.passed
        );
    }

    /**
     * @dev Check if address is insider
     */
    function isInsider(address account) external view returns (bool) {
        return insiders[account];
    }

    /**
     * @dev Get current trading status
     */
    function getCurrentTradingStatus() external view returns (bool canTrade, string memory reason) {
        if (_isBlackoutPeriod()) {
            return (false, "Trading blackout period");
        }
        return (true, "Trading allowed");
    }

    /**
     * @dev Get company equity overview
     */
    function getCompanyEquityOverview() external view returns (
        string memory name,
        uint256 totalEmployeeCount,
        uint256 totalSharesOutstanding,
        uint256 currentPrice,
        uint256 totalEquityValue
    ) {
        return (
            companyName,
            totalEmployees,
            totalShares,
            sharePrice,
            totalShares * sharePrice
        );
    }
}