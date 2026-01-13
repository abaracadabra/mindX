// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.20;

import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title Universal Identity and Compliance System for Human-Robot Societies
 * @dev Custom identity and compliance management system for human-robot interactions in daio
 * @notice Defines interfaces for managing identities of humans and robots, hardware verification, and establishing rule sets with compliance checking
 */
interface IUniversalIdentity {
    struct HardwareIdentity {
        bytes32 publicKey;            // Hardware-bound public key
        string manufacturer;          // Robot manufacturer
        string operator;             // Robot operator/owner
        string model;                // Robot model identifier
        string serialNumber;         // Unique serial number
        bytes32 initialHashSignature; // Initial firmware signature
        bytes32 currentHashSignature; // Current state signature
    }

    function getHardwareIdentity() external view returns (HardwareIdentity memory);
    function generateChallenge() external returns (bytes32);
    function verifyChallenge(bytes32 challenge, bytes memory signature) external returns (bool);
    function addRule(bytes memory rule) external;
    function removeRule(bytes memory rule) external;
    function checkCompliance(bytes memory rule) external view returns (bool);

    event RuleAdded(bytes rule);
    event RuleRemoved(bytes rule);
    event SubscribedToCharter(address indexed charter);
    event UnsubscribedFromCharter(address indexed charter);
}

interface IUniversalCharter {
    enum UserType { Human, Robot }

    function registerUser(UserType userType, bytes[] memory ruleSet) external;
    function leaveSystem() external;
    function checkCompliance(address user, bytes[] memory ruleSet) external returns (bool);
    function updateRuleSet(bytes[] memory newRuleSet) external;
    function terminateContract() external;

    event UserRegistered(address indexed user, UserType userType, bytes[] ruleSet);
    event UserLeft(address indexed user);
    event ComplianceChecked(address indexed user, bytes[] ruleSet);
    event RuleSetUpdated(bytes[] newRuleSet, address updatedBy);
}

contract UniversalIdentity is IUniversalIdentity, OwnableUpgradeable {
    string public constant VERSION = "v0.0.1";
    
    HardwareIdentity public hardwareIdentity;
    mapping(bytes => bool) private robotRules;
    mapping(bytes => bool) private complianceStatus;
    mapping(address => bool) private subscribedCharters;
    mapping(bytes32 => bool) private activeChallenge;
    mapping(address => bytes32) private lastVerifiedChallenge;

    error RuleNotAgreed(bytes rule);
    error RuleNotCompliant(bytes rule);
    error RuleAlreadyAdded(bytes rule);
    error InvalidChallenge();
    error InvalidSignature();
    error ChallengePending();
    error NoActiveChallenge();

    event ComplianceUpdated(bytes rule, bool status);
    event ChallengeGenerated(bytes32 indexed challenge);
    event ChallengeVerified(bytes32 indexed challenge, bool success);
    event HardwareIdentityUpdated(HardwareIdentity newIdentity);

    modifier ruleExists(bytes memory rule) {
        require(robotRules[rule], "Rule does not exist");
        _;
    }

    modifier validChallenge(bytes32 challenge) {
        if (!activeChallenge[challenge]) revert InvalidChallenge();
        _;
    }

    function initialize(
        address initialOwner, 
        HardwareIdentity memory _hardwareIdentity
    ) public initializer {
        __Ownable_init(initialOwner);
        hardwareIdentity = _hardwareIdentity;
        emit HardwareIdentityUpdated(_hardwareIdentity);
    }

    function getHardwareIdentity() external view override returns (HardwareIdentity memory) {
        return hardwareIdentity;
    }

    function generateChallenge() external override returns (bytes32) {
        if (lastVerifiedChallenge[msg.sender] != 0) revert ChallengePending();

        bytes32 challenge = keccak256(abi.encodePacked(
            block.timestamp,
            block.prevrandao,
            msg.sender,
            address(this)
        ));
        
        activeChallenge[challenge] = true;
        lastVerifiedChallenge[msg.sender] = challenge;
        
        emit ChallengeGenerated(challenge);
        return challenge;
    }

    function verifyChallenge(
        bytes32 challenge, 
        bytes memory signature
    ) external override validChallenge(challenge) returns (bool) {
        if (lastVerifiedChallenge[msg.sender] == 0) revert NoActiveChallenge();

        delete activeChallenge[challenge];
        delete lastVerifiedChallenge[msg.sender];

        bytes32 messageHash = keccak256(abi.encodePacked(challenge));
        bytes32 ethSignedMessageHash = MessageHashUtils.toEthSignedMessageHash(messageHash);
        
        address hardwareAddress = address(uint160(uint256(hardwareIdentity.publicKey)));
        
        bool isValid = SignatureChecker.isValidSignatureNow(
            hardwareAddress, 
            ethSignedMessageHash, 
            signature
        );

        emit ChallengeVerified(challenge, isValid);

        if (!isValid) {
            revert InvalidSignature();
        }

        return true;
    }

    function addRule(bytes memory rule) external override onlyOwner {
        if (robotRules[rule]) {
            revert RuleAlreadyAdded(rule);
        }
        robotRules[rule] = true;
        emit RuleAdded(rule);
    }

    function removeRule(bytes memory rule) external override onlyOwner ruleExists(rule) {
        robotRules[rule] = false;
        complianceStatus[rule] = false;
        emit RuleRemoved(rule);
    }

    function checkCompliance(bytes memory rule) external view override returns (bool) {
        if (!robotRules[rule]) {
            revert RuleNotAgreed(rule);
        }
        return complianceStatus[rule];
    }

    function updateCompliance(
        bytes memory rule, 
        bool status
    ) external onlyOwner ruleExists(rule) {
        complianceStatus[rule] = status;
        emit ComplianceUpdated(rule, status);
    }

    function updateHardwareIdentity(
        HardwareIdentity memory newIdentity
    ) external onlyOwner {
        hardwareIdentity = newIdentity;
        emit HardwareIdentityUpdated(newIdentity);
    }

    function getRule(bytes memory rule) external view returns (bool) {
        return robotRules[rule];
    }

    function getComplianceStatus(bytes memory rule) external view returns (bool) {
        return complianceStatus[rule];
    }

    function getSubscribedCharter(address charter) external view returns (bool) {
        return subscribedCharters[charter];
    }

    function getLastVerifiedChallenge(address user) external view returns (bytes32) {
        return lastVerifiedChallenge[user];
    }
}

contract UniversalCharter is IUniversalCharter, OwnableUpgradeable {
    struct UserInfo {
        bool isRegistered;
        UserType userType;
        uint256 ruleSetVersion;
        uint256 registrationTime;
        uint256 lastUpdateTime;
        bytes32 lastComplianceHash;
    }

    struct RuleSetInfo {
        bytes[] rules;
        uint256 creationTime;
        address creator;
        bool isActive;
        bytes32 ruleSetHash;
    }

    mapping(address => UserInfo) private users;
    mapping(uint256 => RuleSetInfo) private ruleSets;
    mapping(bytes32 => uint256) private ruleSetVersions;
    
    uint256 private currentVersion;
    bool public paused;
    
    uint256 public constant MIN_RULES = 1;
    uint256 public constant MAX_RULES = 100;
    uint256 public constant COMPLIANCE_CHECK_PERIOD = 1 days;

    error EmptyRuleSet();
    error RuleSetTooLarge();
    error RuleSetExists();
    error InvalidRuleSet();
    error UserAlreadyRegistered();
    error UserNotRegistered();
    error ComplianceCheckFailed();
    error SystemIsPaused(); 
    error InvalidUserType();
    error UnauthorizedAccess();

    event RuleSetCreated(uint256 indexed version, bytes32 indexed ruleSetHash);
    event RuleSetDeactivated(uint256 indexed version);
    event ComplianceCheckInitiated(address indexed user, uint256 indexed version);
    event ComplianceCheckCompleted(address indexed user, bool success);
    event SystemPaused(address indexed by);
    event SystemUnpaused(address indexed by);
    event UserUpdated(address indexed user, uint256 indexed newVersion);

    modifier whenNotPaused() {
        if (paused) revert SystemIsPaused();
        _;
    }

    modifier onlyRegistered() {
        if (!users[msg.sender].isRegistered) revert UserNotRegistered();
        _;
    }

    modifier validRuleSet(bytes[] memory ruleSet) {
        if (ruleSet.length < MIN_RULES) revert EmptyRuleSet();
        if (ruleSet.length > MAX_RULES) revert RuleSetTooLarge();
        _;
    }

    function initialize(address initialOwner) public initializer {
        __Ownable_init(initialOwner);
        currentVersion = 0;
        paused = false;
    }

    function registerUser(
        UserType userType, 
        bytes[] memory ruleSet
    ) external override whenNotPaused validRuleSet(ruleSet) {
        if (users[msg.sender].isRegistered) revert UserAlreadyRegistered();
        if (userType != UserType.Human && userType != UserType.Robot) revert InvalidUserType();

        bytes32 ruleSetHash = keccak256(abi.encode(ruleSet));
        uint256 version = ruleSetVersions[ruleSetHash];
        if (version == 0 || !ruleSets[version].isActive) revert InvalidRuleSet();

        if (userType == UserType.Robot) {
            bool isCompliant = _checkRobotCompliance(msg.sender, version);
            if (!isCompliant) revert ComplianceCheckFailed();
        }

        users[msg.sender] = UserInfo({
            isRegistered: true,
            userType: userType,
            ruleSetVersion: version,
            registrationTime: block.timestamp,
            lastUpdateTime: block.timestamp,
            lastComplianceHash: ruleSetHash
        });

        emit UserRegistered(msg.sender, userType, ruleSet);
    }

    function leaveSystem() external override whenNotPaused onlyRegistered {
        UserInfo memory userInfo = users[msg.sender];

        if (userInfo.userType == UserType.Robot) {
            bool isCompliant = _checkRobotCompliance(msg.sender, userInfo.ruleSetVersion);
            if (!isCompliant) revert ComplianceCheckFailed();
        }

        delete users[msg.sender];
        emit UserLeft(msg.sender);
    }

    function checkCompliance(
        address user, 
        bytes[] memory ruleSet
    ) external override returns (bool) {
        UserInfo memory userInfo = users[user];
        if (!userInfo.isRegistered) revert UserNotRegistered();

        bytes32 ruleSetHash = keccak256(abi.encode(ruleSet));
        uint256 version = ruleSetVersions[ruleSetHash];
        
        if (version == 0 || !ruleSets[version].isActive || 
            userInfo.ruleSetVersion != version) revert InvalidRuleSet();

        emit ComplianceCheckInitiated(user, version);

        if (userInfo.userType == UserType.Robot) {
            return _checkRobotCompliance(user, version);
        }
        
        return true;
    }

    function _checkRobotCompliance(
        address robotAddress, 
        uint256 version
    ) internal returns (bool) {
        IUniversalIdentity robot = IUniversalIdentity(robotAddress);
        bytes[] memory rules = ruleSets[version].rules;

        for (uint256 i = 0; i < rules.length; i++) {
            try robot.checkCompliance(rules[i]) returns (bool compliant) {
                if (!compliant) {
                    return false;
                }
            } catch {
                return false;
            }
        }
        
        emit ComplianceCheckCompleted(robotAddress, true);
        return true;
    }

    function updateRuleSet(
        bytes[] memory newRuleSet
    ) external override onlyOwner whenNotPaused validRuleSet(newRuleSet) {
        bytes32 ruleSetHash = keccak256(abi.encode(newRuleSet));
        if (ruleSetVersions[ruleSetHash] != 0) revert RuleSetExists();

        currentVersion++;
        
        RuleSetInfo storage newRuleSetInfo = ruleSets[currentVersion];
        newRuleSetInfo.rules = newRuleSet;
        newRuleSetInfo.creationTime = block.timestamp;
        newRuleSetInfo.creator = msg.sender;
        newRuleSetInfo.isActive = true;
        newRuleSetInfo.ruleSetHash = ruleSetHash;

        ruleSetVersions[ruleSetHash] = currentVersion;

        emit RuleSetCreated(currentVersion, ruleSetHash);
        emit RuleSetUpdated(newRuleSet, msg.sender);
    }

    function deactivateRuleSet(uint256 version) external onlyOwner {
        if (version == 0 || version > currentVersion) revert InvalidRuleSet();
        ruleSets[version].isActive = false;
        emit RuleSetDeactivated(version);
    }

    function terminateContract() external override onlyOwner {
        paused = true;
        emit SystemPaused(msg.sender);
    }

    function unpauseContract() external onlyOwner {
        paused = false;
        emit SystemUnpaused(msg.sender);
    }

    // Getter functions
    function getRuleSet(uint256 version) external view returns (bytes[] memory) {
        return ruleSets[version].rules;
    }

    function getRuleSetInfo(uint256 version) external view returns (RuleSetInfo memory) {
        return ruleSets[version];
    }

    function getCurrentVersion() external view returns (uint256) {
        return currentVersion;
    }

    function getUserInfo(address user) external view returns (UserInfo memory) {
        return users[user];
    }

    function isUserRegistered(address user) external view returns (bool) {
        return users[user].isRegistered;
    }

    function getRuleSetVersion(bytes[] memory ruleSet) external view returns (uint256) {
        bytes32 ruleSetHash = keccak256(abi.encode(ruleSet));
        return ruleSetVersions[ruleSetHash];
    }

    function isPaused() external view returns (bool) {
        return paused;
    }
}
