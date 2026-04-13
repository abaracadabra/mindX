// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title RobertsRulesDAIO
 * @notice Robert's Rules of Order encoded as on-chain governance.
 *
 * Parliamentary procedure since 1876, now cryptographic.
 *
 * Two interfaces:
 *   BOARDROOM — full Robert's Rules: motion classes, precedence stack,
 *               second requirement, debate periods, weighted votes,
 *               2/3 for debate-silencing motions, quorum enforcement.
 *               CEO + Seven Soldiers. The Security Council.
 *
 *   DOJO      — simplified to yes or no. Any member, one vote, advisory.
 *               No precedence, no seconds, no amendments. Binary signal.
 *               The General Assembly.
 *
 * The boardroom decides. The dojo legitimizes.
 *
 * Prior art: Rob's Rules DAO LCA (Vocdoni/Aragon).
 * See: daio/docs/daio/governance/ROBERTS_RULES.md
 */
contract RobertsRulesDAIO is AccessControl, ReentrancyGuard {

    // ─── Roles ───────────────────────────────────────────────────────
    bytes32 public constant CHAIR_ROLE = keccak256("CHAIR_ROLE");         // CEO — presents directives
    bytes32 public constant SOLDIER_ROLE = keccak256("SOLDIER_ROLE");     // Board members — vote
    bytes32 public constant DOJO_MEMBER_ROLE = keccak256("DOJO_MEMBER_ROLE"); // Any agent — yes/no

    // ─── Motion State Machine ────────────────────────────────────────
    //
    //  NO_MOTION → PROPOSED → STATED → DEBATED → VOTED → ADOPTED/REJECTED/TABLED
    //
    enum MotionState {
        NO_MOTION,    // Floor is open
        PROPOSED,     // Moved, awaiting second
        STATED,       // Chair stated the question, debate open
        DEBATED,      // Under active debate (time-bound)
        VOTED,        // Vote taken, pending finalization
        ADOPTED,      // Motion carries
        REJECTED,     // Motion fails
        TABLED,       // Laid on table (temporary, can be taken up later)
        REFERRED      // Sent to committee / exploration branch
    }

    // ─── Motion Classes ──────────────────────────────────────────────
    // Robert's Rules: 4 classes, strict precedence.
    // Higher class interrupts lower. Within a class, higher rank interrupts lower.
    enum MotionClass {
        MAIN,          // 0 — lowest precedence. The directive.
        SUBSIDIARY,    // 1 — modifies the main motion (amend, table, close debate)
        INCIDENTAL,    // 2 — arises from procedure (point of order, appeal)
        PRIVILEGED     // 3 — highest precedence (adjourn, recess, privilege)
    }

    // ─── Motion Types ────────────────────────────────────────────────
    enum MotionType {
        // Main motions (class 0)
        MAIN_MOTION,           // 0  — the directive itself
        RECONSIDER,            // 1  — reopen a decided question
        RESCIND,               // 2  — undo previous action (2/3 vote)
        TAKE_FROM_TABLE,       // 3  — resume a tabled motion

        // Subsidiary motions (class 1) — precedence order low→high
        POSTPONE_INDEFINITELY, // 4  — kill the motion
        AMEND,                 // 5  — modify the motion
        COMMIT_REFER,          // 6  — send to committee
        POSTPONE_DEFINITELY,   // 7  — delay to specific time
        LIMIT_DEBATE,          // 8  — 2/3 vote required
        PREVIOUS_QUESTION,     // 9  — close debate, force vote. 2/3 vote
        LAY_ON_TABLE,          // 10 — temporarily set aside

        // Incidental motions (class 2) — no fixed precedence among themselves
        POINT_OF_ORDER,        // 11 — procedure violated
        APPEAL,                // 12 — challenge chair's ruling
        SUSPEND_RULES,         // 13 — 2/3 vote required
        OBJECTION_TO_CONSIDER, // 14 — block a question. 2/3 against
        DIVISION_OF_QUESTION,  // 15 — split a compound motion
        WITHDRAW,              // 16 — maker takes back motion

        // Privileged motions (class 3) — precedence order low→high
        CALL_ORDERS_OF_DAY,    // 17
        RAISE_PRIVILEGE,       // 18
        RECESS,                // 19
        ADJOURN,               // 20
        FIX_TIME_TO_ADJOURN    // 21 — highest precedence
    }

    // ─── Vote Choice ─────────────────────────────────────────────────
    enum VoteChoice {
        NONE,
        AYE,       // approve
        NAY,       // reject
        ABSTAIN
    }

    // ─── Consensus Thresholds (basis points, 10000 = 100%) ───────────
    uint256 public constant BASIS = 10000;
    uint256 public constant MAJORITY = 5001;           // > 50%
    uint256 public constant TWO_THIRDS = 6667;         // ≥ 66.67%
    uint256 public constant DICTATOR_THRESHOLD = 3334; // > 33.33% — diffusion, not consensus
    uint256 public constant UNANIMOUS = 10000;          // 100%

    // Configurable boardroom threshold (default 2/3)
    uint256 public boardroomThreshold = TWO_THIRDS;

    // ─── Structs ─────────────────────────────────────────────────────

    struct Motion {
        uint256 id;
        MotionType motionType;
        MotionClass motionClass;
        MotionState state;
        address mover;             // who moved it
        address seconder;          // who seconded it (address(0) if none)
        string text;               // the directive / motion text
        uint256 parentMotionId;    // 0 if main, else the motion this modifies
        uint256 createdAt;
        uint256 debateEndsAt;      // timestamp when debate closes
        uint256 executionDelay;    // timelock after adoption
        bool requiresSecond;
        bool debatable;
        bool amendable;
        uint256 voteThreshold;     // MAJORITY or TWO_THIRDS (basis points)
        // Vote tallies
        uint256 weightAye;
        uint256 weightNay;
        uint256 weightAbstain;
        uint256 voterCount;
        mapping(address => VoteChoice) votes;
        mapping(address => uint256) voteWeights;
    }

    // Dojo question — binary yes/no, one member one vote, advisory
    struct DojoQuestion {
        uint256 id;
        string question;
        address proposer;
        uint256 createdAt;
        uint256 closesAt;
        uint256 yesCount;
        uint256 noCount;
        uint256 totalVoters;
        bool closed;
        mapping(address => bool) hasVoted;
    }

    // Soldier weight registration
    struct SoldierWeight {
        uint256 weight;     // basis points (10000 = 1.0x, 12000 = 1.2x, 8000 = 0.8x)
        bool isVetoHolder;  // CISO, CRO
        bool isAdvisory;    // CLO
        bool active;
    }

    // ─── State ───────────────────────────────────────────────────────

    // Boardroom
    uint256 public motionCount;
    mapping(uint256 => Motion) public motions;
    uint256[] public motionStack;  // precedence stack — highest precedence on top
    uint256 public quorumBasisPoints = 5000; // 50% of soldier weight must participate
    uint256 public debateDuration = 1 days;  // default debate period

    // Soldiers
    mapping(address => SoldierWeight) public soldiers;
    address[] public soldierList;
    uint256 public totalSoldierWeight;

    // Dojo
    uint256 public dojoQuestionCount;
    mapping(uint256 => DojoQuestion) public dojoQuestions;
    uint256 public dojoDuration = 3 days; // default voting period for dojo questions

    // ─── Events ──────────────────────────────────────────────────────

    event MotionMoved(uint256 indexed id, MotionType motionType, address mover, string text);
    event MotionSeconded(uint256 indexed id, address seconder);
    event MotionStated(uint256 indexed id, uint256 debateEndsAt);
    event VoteCast(uint256 indexed id, address voter, VoteChoice choice, uint256 weight);
    event MotionAdopted(uint256 indexed id, uint256 weightAye, uint256 weightNay);
    event MotionRejected(uint256 indexed id, uint256 weightAye, uint256 weightNay);
    event MotionTabled(uint256 indexed id);
    event MotionReferred(uint256 indexed id, string committee);
    event MotionWithdrawn(uint256 indexed id);
    event ThresholdChanged(uint256 oldThreshold, uint256 newThreshold);

    event DojoQuestionCreated(uint256 indexed id, address proposer, string question);
    event DojoVoteCast(uint256 indexed id, address voter, bool yes);
    event DojoQuestionClosed(uint256 indexed id, uint256 yesCount, uint256 noCount);

    // ─── Constructor ─────────────────────────────────────────────────

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(CHAIR_ROLE, msg.sender);
    }

    // ═══════════════════════════════════════════════════════════════════
    //  BOARDROOM — Full Robert's Rules
    // ═══════════════════════════════════════════════════════════════════

    // ─── Soldier Management ──────────────────────────────────────────

    /// @notice Register a soldier with voting weight
    /// @param soldier Address of the soldier
    /// @param weight Weight in basis points (10000 = 1.0x)
    /// @param vetoHolder Whether this soldier has veto weight (CISO, CRO)
    /// @param advisory Whether this soldier is advisory only (CLO)
    function registerSoldier(
        address soldier,
        uint256 weight,
        bool vetoHolder,
        bool advisory
    ) external onlyRole(CHAIR_ROLE) {
        require(weight > 0 && weight <= 20000, "Weight: 1-20000 bp");
        if (!soldiers[soldier].active) {
            soldierList.push(soldier);
        } else {
            totalSoldierWeight -= soldiers[soldier].weight;
        }
        soldiers[soldier] = SoldierWeight(weight, vetoHolder, advisory, true);
        totalSoldierWeight += weight;
        _grantRole(SOLDIER_ROLE, soldier);
    }

    /// @notice Remove a soldier
    function removeSoldier(address soldier) external onlyRole(CHAIR_ROLE) {
        require(soldiers[soldier].active, "Not a soldier");
        totalSoldierWeight -= soldiers[soldier].weight;
        soldiers[soldier].active = false;
        _revokeRole(SOLDIER_ROLE, soldier);
    }

    // ─── Motion Properties ───────────────────────────────────────────

    function _motionClass(MotionType t) internal pure returns (MotionClass) {
        if (t <= MotionType.TAKE_FROM_TABLE) return MotionClass.MAIN;
        if (t <= MotionType.LAY_ON_TABLE) return MotionClass.SUBSIDIARY;
        if (t <= MotionType.WITHDRAW) return MotionClass.INCIDENTAL;
        return MotionClass.PRIVILEGED;
    }

    function _requiresSecond(MotionType t) internal pure returns (bool) {
        // Incidental motions that don't need a second
        if (t == MotionType.POINT_OF_ORDER) return false;
        if (t == MotionType.OBJECTION_TO_CONSIDER) return false;
        if (t == MotionType.WITHDRAW) return false;
        if (t == MotionType.RAISE_PRIVILEGE) return false;
        if (t == MotionType.CALL_ORDERS_OF_DAY) return false;
        return true;
    }

    function _isDebatable(MotionType t) internal pure returns (bool) {
        if (t == MotionType.MAIN_MOTION) return true;
        if (t == MotionType.RECONSIDER) return true;
        if (t == MotionType.RESCIND) return true;
        if (t == MotionType.POSTPONE_INDEFINITELY) return true;
        if (t == MotionType.AMEND) return true;
        if (t == MotionType.COMMIT_REFER) return true;
        if (t == MotionType.POSTPONE_DEFINITELY) return true;
        if (t == MotionType.APPEAL) return true;
        if (t == MotionType.FIX_TIME_TO_ADJOURN) return true;
        return false;
    }

    function _isAmendable(MotionType t) internal pure returns (bool) {
        if (t == MotionType.MAIN_MOTION) return true;
        if (t == MotionType.RESCIND) return true;
        if (t == MotionType.AMEND) return true;
        if (t == MotionType.COMMIT_REFER) return true;
        if (t == MotionType.POSTPONE_DEFINITELY) return true;
        if (t == MotionType.LIMIT_DEBATE) return true;
        if (t == MotionType.RECESS) return true;
        if (t == MotionType.FIX_TIME_TO_ADJOURN) return true;
        return false;
    }

    function _voteThreshold(MotionType t) internal pure returns (uint256) {
        // 2/3 required for motions that silence debate or override rules
        if (t == MotionType.PREVIOUS_QUESTION) return TWO_THIRDS;
        if (t == MotionType.LIMIT_DEBATE) return TWO_THIRDS;
        if (t == MotionType.SUSPEND_RULES) return TWO_THIRDS;
        if (t == MotionType.OBJECTION_TO_CONSIDER) return TWO_THIRDS;
        if (t == MotionType.RESCIND) return TWO_THIRDS;
        return MAJORITY;
    }

    /// @dev Precedence rank within the 13 ranked motions (Robert's Rules order).
    ///      Higher number = higher precedence. 0 = not ranked (incidental).
    function _precedenceRank(MotionType t) internal pure returns (uint256) {
        if (t == MotionType.MAIN_MOTION) return 1;
        if (t == MotionType.POSTPONE_INDEFINITELY) return 2;
        if (t == MotionType.AMEND) return 3;
        if (t == MotionType.COMMIT_REFER) return 4;
        if (t == MotionType.POSTPONE_DEFINITELY) return 5;
        if (t == MotionType.LIMIT_DEBATE) return 6;
        if (t == MotionType.PREVIOUS_QUESTION) return 7;
        if (t == MotionType.LAY_ON_TABLE) return 8;
        if (t == MotionType.CALL_ORDERS_OF_DAY) return 9;
        if (t == MotionType.RAISE_PRIVILEGE) return 10;
        if (t == MotionType.RECESS) return 11;
        if (t == MotionType.ADJOURN) return 12;
        if (t == MotionType.FIX_TIME_TO_ADJOURN) return 13;
        return 0; // incidental — no fixed rank, always in order
    }

    // ─── Core Parliamentary Actions ──────────────────────────────────

    /// @notice Move a motion (the "I move that..." action)
    /// @param motionType The type of motion
    /// @param text The motion text (directive for main motions)
    /// @param parentMotionId The motion this modifies (0 for main motions)
    function moveMotion(
        MotionType motionType,
        string calldata text,
        uint256 parentMotionId
    ) external onlyRole(SOLDIER_ROLE) nonReentrant returns (uint256) {
        // Check precedence — motion must outrank current top of stack
        if (motionStack.length > 0) {
            uint256 topId = motionStack[motionStack.length - 1];
            Motion storage top = motions[topId];
            uint256 newRank = _precedenceRank(motionType);
            uint256 topRank = _precedenceRank(top.motionType);
            // Incidental motions (rank 0) are always in order
            // Ranked motions must have higher precedence than current top
            require(
                newRank == 0 || newRank > topRank,
                "Out of order: motion does not have sufficient precedence"
            );
        } else {
            // Empty stack — only main motions or privileged motions
            require(
                _motionClass(motionType) == MotionClass.MAIN ||
                _motionClass(motionType) == MotionClass.PRIVILEGED,
                "Out of order: no pending motion to modify"
            );
        }

        // Subsidiary/incidental motions need a parent
        MotionClass mc = _motionClass(motionType);
        if (mc == MotionClass.SUBSIDIARY || mc == MotionClass.INCIDENTAL) {
            require(parentMotionId > 0 && parentMotionId <= motionCount, "Subsidiary needs parent");
        }

        motionCount++;
        Motion storage m = motions[motionCount];
        m.id = motionCount;
        m.motionType = motionType;
        m.motionClass = mc;
        m.mover = msg.sender;
        m.text = text;
        m.parentMotionId = parentMotionId;
        m.createdAt = block.timestamp;
        m.requiresSecond = _requiresSecond(motionType);
        m.debatable = _isDebatable(motionType);
        m.amendable = _isAmendable(motionType);
        m.voteThreshold = _voteThreshold(motionType);

        if (m.requiresSecond) {
            m.state = MotionState.PROPOSED;
        } else {
            // No second needed — chair rules or immediate
            m.state = MotionState.STATED;
            m.debateEndsAt = m.debatable ? block.timestamp + debateDuration : block.timestamp;
            motionStack.push(motionCount);
        }

        emit MotionMoved(motionCount, motionType, msg.sender, text);
        return motionCount;
    }

    /// @notice Second a proposed motion
    function secondMotion(uint256 motionId) external onlyRole(SOLDIER_ROLE) {
        Motion storage m = motions[motionId];
        require(m.state == MotionState.PROPOSED, "Not awaiting second");
        require(m.mover != msg.sender, "Cannot second own motion");

        m.seconder = msg.sender;
        m.state = MotionState.STATED;
        m.debateEndsAt = m.debatable ? block.timestamp + debateDuration : block.timestamp;
        motionStack.push(motionId);

        emit MotionSeconded(motionId, msg.sender);
        emit MotionStated(motionId, m.debateEndsAt);
    }

    /// @notice Cast a vote on the highest-precedence pending motion
    function vote(uint256 motionId, VoteChoice choice) external onlyRole(SOLDIER_ROLE) nonReentrant {
        Motion storage m = motions[motionId];
        require(
            m.state == MotionState.STATED || m.state == MotionState.DEBATED,
            "Not in voting state"
        );
        // If debatable, debate period must have ended (or previous question passed)
        if (m.debatable && m.debateEndsAt > block.timestamp) {
            m.state = MotionState.DEBATED;
            // Debate still open — vote is allowed but records during debate
        }
        require(m.votes[msg.sender] == VoteChoice.NONE, "Already voted");
        require(soldiers[msg.sender].active, "Not an active soldier");

        SoldierWeight storage sw = soldiers[msg.sender];
        m.votes[msg.sender] = choice;
        m.voteWeights[msg.sender] = sw.weight;
        m.voterCount++;

        if (choice == VoteChoice.AYE) {
            m.weightAye += sw.weight;
        } else if (choice == VoteChoice.NAY) {
            m.weightNay += sw.weight;
        } else if (choice == VoteChoice.ABSTAIN) {
            m.weightAbstain += sw.weight;
        }

        emit VoteCast(motionId, msg.sender, choice, sw.weight);
    }

    /// @notice Finalize the vote on a motion — anyone can call after debate ends
    function finalizeVote(uint256 motionId) external nonReentrant {
        Motion storage m = motions[motionId];
        require(
            m.state == MotionState.STATED || m.state == MotionState.DEBATED,
            "Cannot finalize"
        );
        require(block.timestamp >= m.debateEndsAt, "Debate still open");

        // Quorum check — total participating weight (aye + nay, ignoring abstain)
        uint256 participatingWeight = m.weightAye + m.weightNay;
        uint256 quorumRequired = (totalSoldierWeight * quorumBasisPoints) / BASIS;

        if (participatingWeight < quorumRequired) {
            // Inquorate — no decision made, motion dies
            m.state = MotionState.REJECTED;
            emit MotionRejected(motionId, m.weightAye, m.weightNay);
            _popMotionStack(motionId);
            return;
        }

        // Calculate threshold
        // Score = weightAye / (weightAye + weightNay) in basis points
        uint256 score = (m.weightAye * BASIS) / participatingWeight;

        if (score >= m.voteThreshold) {
            m.state = MotionState.ADOPTED;
            emit MotionAdopted(motionId, m.weightAye, m.weightNay);
        } else {
            m.state = MotionState.REJECTED;
            emit MotionRejected(motionId, m.weightAye, m.weightNay);
        }

        _popMotionStack(motionId);
    }

    /// @notice Chair lays a motion on the table
    function tableMotion(uint256 motionId) external onlyRole(CHAIR_ROLE) {
        Motion storage m = motions[motionId];
        require(
            m.state == MotionState.STATED || m.state == MotionState.DEBATED,
            "Cannot table"
        );
        m.state = MotionState.TABLED;
        _popMotionStack(motionId);
        emit MotionTabled(motionId);
    }

    /// @notice Take a tabled motion back to the floor (majority vote assumed)
    function takeFromTable(uint256 motionId) external onlyRole(SOLDIER_ROLE) {
        Motion storage m = motions[motionId];
        require(m.state == MotionState.TABLED, "Not tabled");
        m.state = MotionState.STATED;
        m.debateEndsAt = block.timestamp + debateDuration;
        // Reset votes for new consideration
        m.weightAye = 0;
        m.weightNay = 0;
        m.weightAbstain = 0;
        m.voterCount = 0;
        motionStack.push(motionId);
        emit MotionStated(motionId, m.debateEndsAt);
    }

    /// @notice Refer a motion to committee / exploration branch
    function referMotion(uint256 motionId, string calldata committee)
        external onlyRole(CHAIR_ROLE)
    {
        Motion storage m = motions[motionId];
        require(
            m.state == MotionState.STATED || m.state == MotionState.DEBATED,
            "Cannot refer"
        );
        m.state = MotionState.REFERRED;
        _popMotionStack(motionId);
        emit MotionReferred(motionId, committee);
    }

    /// @notice Mover withdraws their own motion
    function withdrawMotion(uint256 motionId) external {
        Motion storage m = motions[motionId];
        require(m.mover == msg.sender, "Only mover can withdraw");
        require(
            m.state == MotionState.PROPOSED || m.state == MotionState.STATED,
            "Too late to withdraw"
        );
        m.state = MotionState.REJECTED;
        _popMotionStack(motionId);
        emit MotionWithdrawn(motionId);
    }

    // ─── Boardroom Configuration ─────────────────────────────────────

    /// @notice Set the consensus threshold for main motions
    /// @param threshold Basis points (3334=1/3 dictator, 6667=2/3 majority, 10000=3/3 unilateral)
    function setThreshold(uint256 threshold) external onlyRole(CHAIR_ROLE) {
        require(threshold >= DICTATOR_THRESHOLD && threshold <= UNANIMOUS, "Invalid threshold");
        uint256 old = boardroomThreshold;
        boardroomThreshold = threshold;
        emit ThresholdChanged(old, threshold);
    }

    /// @notice Set debate duration
    function setDebateDuration(uint256 duration) external onlyRole(CHAIR_ROLE) {
        require(duration >= 1 hours && duration <= 30 days, "1h-30d");
        debateDuration = duration;
    }

    /// @notice Set quorum requirement
    function setQuorum(uint256 basisPoints) external onlyRole(CHAIR_ROLE) {
        require(basisPoints > 0 && basisPoints <= BASIS, "1-10000 bp");
        quorumBasisPoints = basisPoints;
    }

    // ─── Stack Management ────────────────────────────────────────────

    function _popMotionStack(uint256 motionId) internal {
        for (uint256 i = motionStack.length; i > 0; i--) {
            if (motionStack[i - 1] == motionId) {
                motionStack[i - 1] = motionStack[motionStack.length - 1];
                motionStack.pop();
                return;
            }
        }
    }

    /// @notice Get the current top of the precedence stack
    function currentMotion() external view returns (uint256) {
        if (motionStack.length == 0) return 0;
        return motionStack[motionStack.length - 1];
    }

    /// @notice Get the full precedence stack
    function getMotionStack() external view returns (uint256[] memory) {
        return motionStack;
    }

    // ═══════════════════════════════════════════════════════════════════
    //  DOJO — Yes or No
    // ═══════════════════════════════════════════════════════════════════
    //
    //  The simplest possible governance. One member, one vote, yes or no.
    //  No precedence. No seconds. No amendments. No weighted votes.
    //  Advisory — the dojo does not execute, it signals.
    //
    //  The General Assembly to the boardroom's Security Council.

    /// @notice Propose a yes/no question to the dojo
    function askDojo(string calldata question) external onlyRole(DOJO_MEMBER_ROLE) returns (uint256) {
        dojoQuestionCount++;
        DojoQuestion storage q = dojoQuestions[dojoQuestionCount];
        q.id = dojoQuestionCount;
        q.question = question;
        q.proposer = msg.sender;
        q.createdAt = block.timestamp;
        q.closesAt = block.timestamp + dojoDuration;

        emit DojoQuestionCreated(dojoQuestionCount, msg.sender, question);
        return dojoQuestionCount;
    }

    /// @notice Vote yes or no on a dojo question
    function voteDojo(uint256 questionId, bool yes) external onlyRole(DOJO_MEMBER_ROLE) {
        DojoQuestion storage q = dojoQuestions[questionId];
        require(q.id > 0, "Question does not exist");
        require(!q.closed, "Question closed");
        require(block.timestamp <= q.closesAt, "Voting period ended");
        require(!q.hasVoted[msg.sender], "Already voted");

        q.hasVoted[msg.sender] = true;
        q.totalVoters++;

        if (yes) {
            q.yesCount++;
        } else {
            q.noCount++;
        }

        emit DojoVoteCast(questionId, msg.sender, yes);
    }

    /// @notice Close a dojo question after voting period ends
    function closeDojo(uint256 questionId) external {
        DojoQuestion storage q = dojoQuestions[questionId];
        require(q.id > 0, "Question does not exist");
        require(!q.closed, "Already closed");
        require(block.timestamp > q.closesAt, "Voting still open");

        q.closed = true;
        emit DojoQuestionClosed(questionId, q.yesCount, q.noCount);
    }

    /// @notice Set dojo voting duration
    function setDojoDuration(uint256 duration) external onlyRole(CHAIR_ROLE) {
        require(duration >= 1 hours && duration <= 30 days, "1h-30d");
        dojoDuration = duration;
    }

    // ─── View Functions ──────────────────────────────────────────────

    /// @notice Get motion details (without mappings)
    function getMotion(uint256 motionId) external view returns (
        uint256 id,
        MotionType motionType,
        MotionState state,
        address mover,
        address seconder,
        string memory text,
        uint256 debateEndsAt,
        uint256 voteThreshold,
        uint256 weightAye,
        uint256 weightNay,
        uint256 weightAbstain,
        uint256 voterCount
    ) {
        Motion storage m = motions[motionId];
        return (
            m.id, m.motionType, m.state, m.mover, m.seconder, m.text,
            m.debateEndsAt, m.voteThreshold, m.weightAye, m.weightNay,
            m.weightAbstain, m.voterCount
        );
    }

    /// @notice Get dojo question details (without mappings)
    function getDojoQuestion(uint256 questionId) external view returns (
        uint256 id,
        string memory question,
        address proposer,
        uint256 closesAt,
        uint256 yesCount,
        uint256 noCount,
        uint256 totalVoters,
        bool closed
    ) {
        DojoQuestion storage q = dojoQuestions[questionId];
        return (
            q.id, q.question, q.proposer, q.closesAt,
            q.yesCount, q.noCount, q.totalVoters, q.closed
        );
    }

    /// @notice Number of registered soldiers
    function soldierCount() external view returns (uint256) {
        return soldierList.length;
    }
}
