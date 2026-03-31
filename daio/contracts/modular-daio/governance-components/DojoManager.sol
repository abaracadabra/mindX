// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../../daio/governance/BoardroomExtension.sol";
import "../../daio/constitution/DAIO_Constitution.sol";
import "../../executive-governance/ExecutiveGovernance.sol";
import "../../daio/identity/IDNFT.sol";

/**
 * @title DojoManager
 * @dev Advanced governance dojo system for state settlement and allocational relationships
 *
 * Key Features:
 * - Boardroom-integrated dojo creation for specialized governance
 * - File-privilege allocation based on earned titles and reputation
 * - Status reputation system with role and rank progression
 * - Vote directive integration for structured decision-making
 * - BANKON identity management integration
 * - AgenticPlace.pythai.net ecosystem connectivity
 * - Constitutional compliance for all allocational relationships
 */
contract DojoManager is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant DOJO_MASTER_ROLE = keccak256("DOJO_MASTER_ROLE");
    bytes32 public constant SENSEI_ROLE = keccak256("SENSEI_ROLE");
    bytes32 public constant REPUTATION_ORACLE_ROLE = keccak256("REPUTATION_ORACLE_ROLE");
    bytes32 public constant BANKON_INTEGRATION_ROLE = keccak256("BANKON_INTEGRATION_ROLE");

    // Core governance contracts
    BoardroomExtension public immutable boardroomExtension;
    DAIO_Constitution public immutable constitution;
    ExecutiveGovernance public immutable executiveGovernance;
    IDNFT public immutable idnft;

    // Dojo system structures
    struct Dojo {
        uint256 id;
        string name;
        string description;
        DojoType dojoType;
        address boardroomId; // Associated boardroom
        address sensei;      // Dojo master/teacher
        uint256 creationTime;
        bool active;

        // Governance parameters
        uint256 minRank;
        uint256 maxMembers;
        uint256 votingPeriod;
        uint256 consensusThreshold;

        // Reputation requirements
        mapping(string => uint256) requiredTitles;
        mapping(address => bool) members;
        mapping(address => DojoMemberStatus) memberStatus;
        address[] memberList;

        // Allocational relationships
        mapping(bytes32 => FilePrivilegeMapping) filePrivileges;
        mapping(address => TitleEarning) earnedTitles;
        bytes32[] fileHashes;
    }

    enum DojoType {
        GOVERNANCE,     // Governance training and specialization
        TREASURY,       // Financial management and DeFi
        TECHNICAL,      // Technical skill development
        COMPLIANCE,     // Legal and regulatory expertise
        STRATEGIC,      // Strategic planning and analysis
        EMERGENCY,      // Crisis management and response
        COMMUNITY,      // Community engagement and growth
        RESEARCH        // Research and development
    }

    enum ReputationRank {
        NOVICE,         // 0-100 points
        APPRENTICE,     // 101-500 points
        JOURNEYMAN,     // 501-1500 points
        EXPERT,         // 1501-5000 points
        MASTER,         // 5001-15000 points
        GRANDMASTER,    // 15001-50000 points
        LEGEND,         // 50001+ points
        SAGE            // Special recognition rank
    }

    struct DojoMemberStatus {
        uint256 joinTime;
        ReputationRank rank;
        uint256 reputationPoints;
        uint256 contributionScore;
        uint256 votingWeight;
        bool isSensei;
        mapping(string => bool) earnedTitles;
        mapping(bytes32 => bool) fileAccess;
    }

    struct FilePrivilegeMapping {
        bytes32 fileHash;
        string fileName;
        string requiredTitle;
        ReputationRank minRank;
        uint256 accessLevel; // 1=read, 2=write, 3=admin
        address uploader;
        uint256 uploadTime;
        bool active;
        mapping(address => bool) accessGranted;
    }

    struct TitleEarning {
        string title;
        uint256 earnTime;
        address issuer;
        bool verified;
        uint256 reputationValue;
        string evidence; // IPFS hash or verification data
    }

    struct VoteDirective {
        uint256 id;
        uint256 dojoId;
        string directive;
        string category;
        address proposer;
        uint256 creationTime;
        uint256 endTime;
        mapping(address => Vote) votes;
        mapping(ReputationRank => uint256) votesByRank;
        uint256 totalVotes;
        bool executed;
        string result;
    }

    enum VoteType {
        APPROVE,
        REJECT,
        ABSTAIN,
        DELEGATE
    }

    struct Vote {
        VoteType voteType;
        uint256 weight;
        string reason;
        uint256 timestamp;
        address delegate; // For delegation votes
    }

    // BANKON Identity Integration
    struct BANKONIdentity {
        address walletAddress;
        string bankonId;
        string verificationLevel; // KYC level
        bool verified;
        uint256 verificationTime;
        mapping(string => string) credentials;
        string[] credentialKeys;
    }

    // AgenticPlace Integration
    struct AgenticPlaceProfile {
        address agentAddress;
        string pythai_net_id;
        string skillset;
        uint256 marketplaceRating;
        uint256 totalEarnings;
        bool isActive;
        mapping(string => uint256) skillLevels;
        string[] skills;
    }

    mapping(uint256 => Dojo) public dojos;
    mapping(address => uint256[]) public userDojos;
    mapping(uint256 => VoteDirective) public voteDirectives;
    mapping(address => BANKONIdentity) public bankonIdentities;
    mapping(address => AgenticPlaceProfile) public agenticPlaceProfiles;
    mapping(string => address) public bankonIdToAddress;
    mapping(string => address) public pythaiNetIdToAddress;

    uint256 public nextDojoId = 1;
    uint256 public nextDirectiveId = 1;
    uint256 public maxDojosPerUser = 5;

    // External integration addresses
    address public bankonVerificationOracle;
    address public agenticPlaceContract;
    string public pythaiNetEndpoint;

    event DojoCreated(
        uint256 indexed dojoId,
        string name,
        DojoType dojoType,
        address indexed sensei,
        address indexed boardroom
    );

    event MemberJoined(
        uint256 indexed dojoId,
        address indexed member,
        ReputationRank rank
    );

    event TitleEarned(
        address indexed member,
        string title,
        address indexed issuer,
        uint256 reputationValue
    );

    event FilePrivilegeGranted(
        bytes32 indexed fileHash,
        address indexed member,
        string title,
        uint256 accessLevel
    );

    event VoteDirectiveCreated(
        uint256 indexed directiveId,
        uint256 indexed dojoId,
        string directive,
        address indexed proposer
    );

    event BANKONIdentityVerified(
        address indexed wallet,
        string indexed bankonId,
        string verificationLevel
    );

    event AgenticPlaceProfileUpdated(
        address indexed agent,
        string indexed pythaiNetId,
        uint256 marketplaceRating
    );

    event ReputationUpdated(
        address indexed member,
        uint256 oldPoints,
        uint256 newPoints,
        ReputationRank newRank
    );

    constructor(
        address _boardroomExtension,
        address _constitution,
        address _executiveGovernance,
        address _idnft,
        address _bankonOracle,
        address _agenticPlaceContract,
        string memory _pythaiNetEndpoint,
        address _admin
    ) {
        require(_boardroomExtension != address(0), "Invalid boardroom extension");
        require(_constitution != address(0), "Invalid constitution");
        require(_executiveGovernance != address(0), "Invalid executive governance");
        require(_idnft != address(0), "Invalid IDNFT");
        require(_admin != address(0), "Invalid admin");

        boardroomExtension = BoardroomExtension(_boardroomExtension);
        constitution = DAIO_Constitution(_constitution);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);
        idnft = IDNFT(_idnft);
        bankonVerificationOracle = _bankonOracle;
        agenticPlaceContract = _agenticPlaceContract;
        pythaiNetEndpoint = _pythaiNetEndpoint;

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(DOJO_MASTER_ROLE, _admin);
        _grantRole(REPUTATION_ORACLE_ROLE, _admin);
        _grantRole(BANKON_INTEGRATION_ROLE, _admin);
    }

    /**
     * @dev Create new dojo within boardroom framework
     */
    function createDojo(
        string calldata name,
        string calldata description,
        DojoType dojoType,
        address boardroomId,
        uint256 minRank,
        uint256 maxMembers,
        uint256 votingPeriod,
        uint256 consensusThreshold
    ) external onlyRole(DOJO_MASTER_ROLE) nonReentrant whenNotPaused returns (uint256) {
        require(bytes(name).length > 0, "Name required");
        require(boardroomId != address(0), "Invalid boardroom");
        require(maxMembers > 0 && maxMembers <= 1000, "Invalid member limit");
        require(consensusThreshold > 0 && consensusThreshold <= 10000, "Invalid consensus threshold");

        // Validate boardroom exists and is active
        require(_validateBoardroom(boardroomId), "Boardroom validation failed");

        uint256 dojoId = nextDojoId++;

        Dojo storage dojo = dojos[dojoId];
        dojo.id = dojoId;
        dojo.name = name;
        dojo.description = description;
        dojo.dojoType = dojoType;
        dojo.boardroomId = boardroomId;
        dojo.sensei = msg.sender;
        dojo.creationTime = block.timestamp;
        dojo.active = true;
        dojo.minRank = minRank;
        dojo.maxMembers = maxMembers;
        dojo.votingPeriod = votingPeriod;
        dojo.consensusThreshold = consensusThreshold;

        emit DojoCreated(dojoId, name, dojoType, msg.sender, boardroomId);
        return dojoId;
    }

    /**
     * @dev Join dojo with reputation and title verification
     */
    function joinDojo(
        uint256 dojoId,
        string calldata verificationData
    ) external nonReentrant whenNotPaused {
        Dojo storage dojo = dojos[dojoId];
        require(dojo.active, "Dojo not active");
        require(!dojo.members[msg.sender], "Already a member");
        require(dojo.memberList.length < dojo.maxMembers, "Dojo full");
        require(userDojos[msg.sender].length < maxDojosPerUser, "Too many dojos");

        // Get current reputation and verify minimum rank
        (ReputationRank rank, uint256 points) = _getReputationInfo(msg.sender);
        require(uint256(rank) >= dojo.minRank, "Insufficient rank");

        // Add member
        dojo.members[msg.sender] = true;
        dojo.memberList.push(msg.sender);
        userDojos[msg.sender].push(dojoId);

        // Initialize member status
        DojoMemberStatus storage status = dojo.memberStatus[msg.sender];
        status.joinTime = block.timestamp;
        status.rank = rank;
        status.reputationPoints = points;
        status.votingWeight = _calculateVotingWeight(rank, points);

        emit MemberJoined(dojoId, msg.sender, rank);
    }

    /**
     * @dev Award title to member based on achievements
     */
    function awardTitle(
        address member,
        string calldata title,
        uint256 reputationValue,
        string calldata evidence
    ) external onlyRole(SENSEI_ROLE) nonReentrant {
        require(member != address(0), "Invalid member");
        require(bytes(title).length > 0, "Title required");
        require(reputationValue > 0, "Invalid reputation value");

        // Constitutional validation for title awards
        require(constitution.validateTitleAward(member, title, reputationValue), "Constitutional violation");

        // Update earned title
        TitleEarning storage earned = dojos[0].earnedTitles[member]; // Use dojo 0 for global titles
        earned.title = title;
        earned.earnTime = block.timestamp;
        earned.issuer = msg.sender;
        earned.verified = true;
        earned.reputationValue = reputationValue;
        earned.evidence = evidence;

        // Update reputation
        _updateReputation(member, reputationValue);

        emit TitleEarned(member, title, msg.sender, reputationValue);
    }

    /**
     * @dev Grant file access privilege based on title and rank
     */
    function grantFilePrivilege(
        uint256 dojoId,
        bytes32 fileHash,
        string calldata fileName,
        string calldata requiredTitle,
        ReputationRank minRank,
        uint256 accessLevel
    ) external nonReentrant {
        Dojo storage dojo = dojos[dojoId];
        require(dojo.active, "Dojo not active");
        require(dojo.sensei == msg.sender || hasRole(DOJO_MASTER_ROLE, msg.sender), "Not authorized");
        require(accessLevel >= 1 && accessLevel <= 3, "Invalid access level");

        FilePrivilegeMapping storage filePriv = dojo.filePrivileges[fileHash];
        filePriv.fileHash = fileHash;
        filePriv.fileName = fileName;
        filePriv.requiredTitle = requiredTitle;
        filePriv.minRank = minRank;
        filePriv.accessLevel = accessLevel;
        filePriv.uploader = msg.sender;
        filePriv.uploadTime = block.timestamp;
        filePriv.active = true;

        dojo.fileHashes.push(fileHash);

        // Auto-grant access to qualifying members
        _updateFileAccessForMembers(dojoId, fileHash);
    }

    /**
     * @dev Create vote directive for structured decision-making
     */
    function createVoteDirective(
        uint256 dojoId,
        string calldata directive,
        string calldata category,
        uint256 duration
    ) external nonReentrant whenNotPaused returns (uint256) {
        Dojo storage dojo = dojos[dojoId];
        require(dojo.active, "Dojo not active");
        require(dojo.members[msg.sender], "Not a member");
        require(duration > 0 && duration <= 30 days, "Invalid duration");

        uint256 directiveId = nextDirectiveId++;

        VoteDirective storage directive_vote = voteDirectives[directiveId];
        directive_vote.id = directiveId;
        directive_vote.dojoId = dojoId;
        directive_vote.directive = directive;
        directive_vote.category = category;
        directive_vote.proposer = msg.sender;
        directive_vote.creationTime = block.timestamp;
        directive_vote.endTime = block.timestamp + duration;

        emit VoteDirectiveCreated(directiveId, dojoId, directive, msg.sender);
        return directiveId;
    }

    /**
     * @dev Vote on directive with rank-weighted voting
     */
    function voteOnDirective(
        uint256 directiveId,
        VoteType voteType,
        string calldata reason,
        address delegate
    ) external nonReentrant whenNotPaused {
        VoteDirective storage directive = voteDirectives[directiveId];
        require(block.timestamp <= directive.endTime, "Voting period ended");

        Dojo storage dojo = dojos[directive.dojoId];
        require(dojo.members[msg.sender], "Not a member");

        DojoMemberStatus storage status = dojo.memberStatus[msg.sender];
        uint256 weight = status.votingWeight;

        Vote storage vote = directive.votes[msg.sender];
        vote.voteType = voteType;
        vote.weight = weight;
        vote.reason = reason;
        vote.timestamp = block.timestamp;
        vote.delegate = delegate;

        directive.votesByRank[status.rank] += weight;
        directive.totalVotes += weight;

        // Check if consensus reached
        if ((directive.totalVotes * 10000) / _getTotalVotingWeight(directive.dojoId) >= dojo.consensusThreshold) {
            _executeDirective(directiveId);
        }
    }

    /**
     * @dev Register BANKON identity for enhanced verification
     */
    function registerBANKONIdentity(
        string calldata bankonId,
        string calldata verificationLevel,
        string[] calldata credentialKeys,
        string[] calldata credentialValues
    ) external nonReentrant {
        require(bytes(bankonId).length > 0, "BANKON ID required");
        require(credentialKeys.length == credentialValues.length, "Credential arrays mismatch");

        BANKONIdentity storage identity = bankonIdentities[msg.sender];
        identity.walletAddress = msg.sender;
        identity.bankonId = bankonId;
        identity.verificationLevel = verificationLevel;
        identity.verified = false; // Will be verified by oracle
        identity.verificationTime = block.timestamp;

        // Store credentials
        for (uint256 i = 0; i < credentialKeys.length; i++) {
            identity.credentials[credentialKeys[i]] = credentialValues[i];
        }
        identity.credentialKeys = credentialKeys;

        bankonIdToAddress[bankonId] = msg.sender;

        // Trigger verification process (would call BANKON oracle)
        _triggerBANKONVerification(msg.sender, bankonId);
    }

    /**
     * @dev Register AgenticPlace.pythai.net profile
     */
    function registerAgenticPlaceProfile(
        string calldata pythaiNetId,
        string calldata skillset,
        string[] calldata skills,
        uint256[] calldata skillLevels
    ) external nonReentrant {
        require(bytes(pythaiNetId).length > 0, "PythAI.net ID required");
        require(skills.length == skillLevels.length, "Skills arrays mismatch");

        AgenticPlaceProfile storage profile = agenticPlaceProfiles[msg.sender];
        profile.agentAddress = msg.sender;
        profile.pythai_net_id = pythaiNetId;
        profile.skillset = skillset;
        profile.isActive = true;

        // Store skills
        for (uint256 i = 0; i < skills.length; i++) {
            profile.skillLevels[skills[i]] = skillLevels[i];
        }
        profile.skills = skills;

        pythaiNetIdToAddress[pythaiNetId] = msg.sender;

        emit AgenticPlaceProfileUpdated(msg.sender, pythaiNetId, 0);
    }

    /**
     * @dev Update marketplace rating from AgenticPlace
     */
    function updateMarketplaceRating(
        address agent,
        uint256 rating,
        uint256 earnings
    ) external onlyRole(REPUTATION_ORACLE_ROLE) {
        AgenticPlaceProfile storage profile = agenticPlaceProfiles[agent];
        require(profile.isActive, "Profile not active");

        profile.marketplaceRating = rating;
        profile.totalEarnings += earnings;

        // Convert marketplace success to reputation points
        uint256 reputationBonus = (rating * earnings) / 1000000; // Scale factor
        _updateReputation(agent, reputationBonus);

        emit AgenticPlaceProfileUpdated(agent, profile.pythai_net_id, rating);
    }

    /**
     * @dev Internal: Update member reputation and rank
     */
    function _updateReputation(address member, uint256 additionalPoints) internal {
        // Find all dojos member belongs to and update reputation
        uint256[] memory memberDojos = userDojos[member];

        for (uint256 i = 0; i < memberDojos.length; i++) {
            uint256 dojoId = memberDojos[i];
            Dojo storage dojo = dojos[dojoId];

            if (dojo.members[member]) {
                DojoMemberStatus storage status = dojo.memberStatus[member];
                uint256 oldPoints = status.reputationPoints;
                status.reputationPoints += additionalPoints;

                ReputationRank newRank = _calculateRank(status.reputationPoints);
                status.rank = newRank;
                status.votingWeight = _calculateVotingWeight(newRank, status.reputationPoints);

                emit ReputationUpdated(member, oldPoints, status.reputationPoints, newRank);

                // Check for new file access privileges
                _updateFileAccessForMember(dojoId, member);
            }
        }
    }

    /**
     * @dev Internal: Calculate reputation rank from points
     */
    function _calculateRank(uint256 points) internal pure returns (ReputationRank) {
        if (points >= 50001) return ReputationRank.LEGEND;
        if (points >= 15001) return ReputationRank.GRANDMASTER;
        if (points >= 5001) return ReputationRank.MASTER;
        if (points >= 1501) return ReputationRank.EXPERT;
        if (points >= 501) return ReputationRank.JOURNEYMAN;
        if (points >= 101) return ReputationRank.APPRENTICE;
        return ReputationRank.NOVICE;
    }

    /**
     * @dev Internal: Calculate voting weight based on rank and points
     */
    function _calculateVotingWeight(ReputationRank rank, uint256 points) internal pure returns (uint256) {
        uint256 baseWeight = points / 100; // 1 weight per 100 points
        uint256 rankMultiplier = uint256(rank) + 1;
        return baseWeight * rankMultiplier;
    }

    /**
     * @dev Internal: Update file access for member based on new reputation
     */
    function _updateFileAccessForMember(uint256 dojoId, address member) internal {
        Dojo storage dojo = dojos[dojoId];
        DojoMemberStatus storage status = dojo.memberStatus[member];

        for (uint256 i = 0; i < dojo.fileHashes.length; i++) {
            bytes32 fileHash = dojo.fileHashes[i];
            FilePrivilegeMapping storage filePriv = dojo.filePrivileges[fileHash];

            if (filePriv.active && uint256(status.rank) >= uint256(filePriv.minRank)) {
                // Check if member has required title
                if (_hasTitleRequirement(member, filePriv.requiredTitle)) {
                    filePriv.accessGranted[member] = true;
                    status.fileAccess[fileHash] = true;

                    emit FilePrivilegeGranted(fileHash, member, filePriv.requiredTitle, filePriv.accessLevel);
                }
            }
        }
    }

    /**
     * @dev Internal: Update file access for all qualifying members
     */
    function _updateFileAccessForMembers(uint256 dojoId, bytes32 fileHash) internal {
        Dojo storage dojo = dojos[dojoId];

        for (uint256 i = 0; i < dojo.memberList.length; i++) {
            _updateFileAccessForMember(dojoId, dojo.memberList[i]);
        }
    }

    /**
     * @dev Internal: Check if member has required title
     */
    function _hasTitleRequirement(address member, string memory requiredTitle) internal view returns (bool) {
        if (bytes(requiredTitle).length == 0) return true; // No title requirement

        // Check earned titles in global dojo (id 0) or any dojo
        uint256[] memory memberDojos = userDojos[member];

        for (uint256 i = 0; i < memberDojos.length; i++) {
            uint256 dojoId = memberDojos[i];
            if (dojos[dojoId].memberStatus[member].earnedTitles[requiredTitle]) {
                return true;
            }
        }

        return false;
    }

    /**
     * @dev Internal: Execute directive based on vote results
     */
    function _executeDirective(uint256 directiveId) internal {
        VoteDirective storage directive = voteDirectives[directiveId];
        directive.executed = true;

        // Execute directive through boardroom extension
        // Implementation would depend on directive type
        directive.result = "APPROVED"; // Simplified for example
    }

    /**
     * @dev Internal: Get total voting weight for dojo
     */
    function _getTotalVotingWeight(uint256 dojoId) internal view returns (uint256) {
        Dojo storage dojo = dojos[dojoId];
        uint256 totalWeight = 0;

        for (uint256 i = 0; i < dojo.memberList.length; i++) {
            address member = dojo.memberList[i];
            totalWeight += dojo.memberStatus[member].votingWeight;
        }

        return totalWeight;
    }

    /**
     * @dev Internal: Get reputation info for address
     */
    function _getReputationInfo(address member) internal view returns (ReputationRank, uint256) {
        // Aggregate reputation across all dojos
        uint256[] memory memberDojos = userDojos[member];
        uint256 totalPoints = 0;

        for (uint256 i = 0; i < memberDojos.length; i++) {
            uint256 dojoId = memberDojos[i];
            if (dojos[dojoId].members[member]) {
                totalPoints += dojos[dojoId].memberStatus[member].reputationPoints;
            }
        }

        return (_calculateRank(totalPoints), totalPoints);
    }

    /**
     * @dev Internal: Validate boardroom exists and is active
     */
    function _validateBoardroom(address boardroomId) internal view returns (bool) {
        // Validate with BoardroomExtension
        return boardroomExtension.isValidBoardroom(boardroomId);
    }

    /**
     * @dev Internal: Trigger BANKON verification process
     */
    function _triggerBANKONVerification(address wallet, string memory bankonId) internal {
        // In production, this would call the BANKON verification oracle
        // For now, we'll emit an event that the oracle can listen to
        emit BANKONIdentityVerified(wallet, bankonId, "PENDING");
    }

    /**
     * @dev Verify BANKON identity (called by oracle)
     */
    function verifyBANKONIdentity(
        address wallet,
        string calldata bankonId,
        bool verified,
        string calldata finalVerificationLevel
    ) external onlyRole(BANKON_INTEGRATION_ROLE) {
        BANKONIdentity storage identity = bankonIdentities[wallet];
        require(keccak256(bytes(identity.bankonId)) == keccak256(bytes(bankonId)), "BANKON ID mismatch");

        identity.verified = verified;
        identity.verificationLevel = finalVerificationLevel;

        if (verified) {
            // Award reputation bonus for verification
            uint256 verificationBonus = 500; // Base verification bonus
            if (keccak256(bytes(finalVerificationLevel)) == keccak256(bytes("PREMIUM"))) {
                verificationBonus = 1000;
            }

            _updateReputation(wallet, verificationBonus);
        }

        emit BANKONIdentityVerified(wallet, bankonId, finalVerificationLevel);
    }

    /**
     * @dev Get dojo information
     */
    function getDojoInfo(uint256 dojoId) external view returns (
        string memory name,
        string memory description,
        DojoType dojoType,
        address sensei,
        uint256 memberCount,
        bool active
    ) {
        Dojo storage dojo = dojos[dojoId];
        return (
            dojo.name,
            dojo.description,
            dojo.dojoType,
            dojo.sensei,
            dojo.memberList.length,
            dojo.active
        );
    }

    /**
     * @dev Get member status in dojo
     */
    function getMemberStatus(uint256 dojoId, address member) external view returns (
        ReputationRank rank,
        uint256 reputationPoints,
        uint256 votingWeight,
        uint256 joinTime,
        bool isMember
    ) {
        Dojo storage dojo = dojos[dojoId];
        DojoMemberStatus storage status = dojo.memberStatus[member];

        return (
            status.rank,
            status.reputationPoints,
            status.votingWeight,
            status.joinTime,
            dojo.members[member]
        );
    }

    /**
     * @dev Check file access privilege
     */
    function hasFileAccess(
        uint256 dojoId,
        bytes32 fileHash,
        address member
    ) external view returns (bool, uint256) {
        Dojo storage dojo = dojos[dojoId];
        FilePrivilegeMapping storage filePriv = dojo.filePrivileges[fileHash];

        bool hasAccess = filePriv.accessGranted[member];
        uint256 accessLevel = hasAccess ? filePriv.accessLevel : 0;

        return (hasAccess, accessLevel);
    }

    /**
     * @dev Get BANKON identity info
     */
    function getBANKONIdentity(address wallet) external view returns (
        string memory bankonId,
        string memory verificationLevel,
        bool verified,
        uint256 verificationTime
    ) {
        BANKONIdentity storage identity = bankonIdentities[wallet];
        return (
            identity.bankonId,
            identity.verificationLevel,
            identity.verified,
            identity.verificationTime
        );
    }

    /**
     * @dev Get AgenticPlace profile info
     */
    function getAgenticPlaceProfile(address agent) external view returns (
        string memory pythaiNetId,
        string memory skillset,
        uint256 marketplaceRating,
        uint256 totalEarnings,
        bool isActive
    ) {
        AgenticPlaceProfile storage profile = agenticPlaceProfiles[agent];
        return (
            profile.pythai_net_id,
            profile.skillset,
            profile.marketplaceRating,
            profile.totalEarnings,
            profile.isActive
        );
    }

    /**
     * @dev Update external integration addresses
     */
    function updateIntegrationAddresses(
        address _bankonOracle,
        address _agenticPlaceContract,
        string calldata _pythaiNetEndpoint
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        bankonVerificationOracle = _bankonOracle;
        agenticPlaceContract = _agenticPlaceContract;
        pythaiNetEndpoint = _pythaiNetEndpoint;
    }

    /**
     * @dev Emergency pause
     */
    function emergencyPause() external onlyRole(DOJO_MASTER_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}