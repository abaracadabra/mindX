// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./PinDealEscrow.sol";
import "./ProviderRegistry.sol";

/**
 * @title ChallengeManager
 * @notice Proof-of-Availability challenges for dataset providers
 * @dev Part of THOT-DAIO architecture for dataset marketplace
 */
contract ChallengeManager {
    struct Challenge {
        bytes32 challengeId;
        bytes32 dealId;
        bytes32 rootCID;
        address provider;
        uint256 blockNumber;
        bytes32 blockHash;          // Random block to serve
        bytes32 responseHash;       // Provider's response hash
        uint256 issuedAt;
        uint256 respondedAt;
        ChallengeStatus status;
    }
    
    enum ChallengeStatus { Pending, Responded, Verified, Failed }
    
    mapping(bytes32 => Challenge) public challenges;
    mapping(address => bytes32[]) public providerChallenges;
    mapping(bytes32 => bytes32[]) public dealChallenges;  // Challenges per deal
    
    PinDealEscrow public pinDealEscrow;
    ProviderRegistry public providerRegistry;
    
    address public owner;
    uint256 public challengeTimeout;  // Blocks before challenge times out
    
    event ChallengeIssued(bytes32 indexed challengeId, bytes32 dealId, address provider, bytes32 blockHash);
    event ChallengeResponded(bytes32 indexed challengeId, bytes32 responseHash);
    event ChallengeVerified(bytes32 indexed challengeId, bool success);
    event ChallengeFailed(bytes32 indexed challengeId);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    constructor(address _pinDealEscrow, address _providerRegistry) {
        owner = msg.sender;
        pinDealEscrow = PinDealEscrow(_pinDealEscrow);
        providerRegistry = ProviderRegistry(_providerRegistry);
        challengeTimeout = 100;  // 100 blocks default timeout
    }
    
    /**
     * @notice Set challenge timeout
     * @param _timeout Blocks before challenge times out
     */
    function setChallengeTimeout(uint256 _timeout) external onlyOwner {
        challengeTimeout = _timeout;
    }
    
    /**
     * @notice Issue a challenge for a deal
     * @param dealId Deal identifier
     * @return challengeId The created challenge ID
     */
    function issueChallenge(bytes32 dealId) external returns (bytes32) {
        // Get deal info from PinDealEscrow
        (, bytes32 rootCID, address provider, , , , , , , , PinDealEscrow.DealStatus status) = pinDealEscrow.deals(dealId);
        require(status == PinDealEscrow.DealStatus.Active, "Deal not active");
        
        // Generate random block hash for challenge
        bytes32 blockHash = keccak256(abi.encodePacked(blockhash(block.number - 1), block.timestamp, dealId));
        
        bytes32 challengeId = keccak256(abi.encodePacked(dealId, provider, block.number, blockHash));
        
        challenges[challengeId] = Challenge({
            challengeId: challengeId,
            dealId: dealId,
            rootCID: rootCID,
            provider: provider,
            blockNumber: block.number,
            blockHash: blockHash,
            responseHash: bytes32(0),
            issuedAt: block.timestamp,
            respondedAt: 0,
            status: ChallengeStatus.Pending
        });
        
        providerChallenges[provider].push(challengeId);
        dealChallenges[dealId].push(challengeId);
        
        emit ChallengeIssued(challengeId, dealId, provider, blockHash);
        return challengeId;
    }
    
    /**
     * @notice Respond to a challenge
     * @param challengeId Challenge identifier
     * @param responseHash Hash of the response data
     */
    function respondToChallenge(
        bytes32 challengeId,
        bytes32 responseHash
    ) external {
        Challenge storage challenge = challenges[challengeId];
        require(challenge.provider == msg.sender, "Only provider");
        require(challenge.status == ChallengeStatus.Pending, "Challenge not pending");
        require(block.number <= challenge.blockNumber + challengeTimeout, "Challenge timed out");
        
        challenge.responseHash = responseHash;
        challenge.respondedAt = block.timestamp;
        challenge.status = ChallengeStatus.Responded;
        
        emit ChallengeResponded(challengeId, responseHash);
    }
    
    /**
     * @notice Verify a challenge response
     * @param challengeId Challenge identifier
     * @param responseData Actual response data to verify
     * @return success Whether verification was successful
     */
    function verifyChallenge(
        bytes32 challengeId,
        bytes memory responseData
    ) external returns (bool) {
        Challenge storage challenge = challenges[challengeId];
        require(challenge.status == ChallengeStatus.Responded, "Challenge not responded");
        
        // Verify response hash matches
        bytes32 computedHash = keccak256(responseData);
        bool success = (computedHash == challenge.responseHash);
        
        if (success) {
            challenge.status = ChallengeStatus.Verified;
            // Update provider reputation
            providerRegistry.recordChallenge(challenge.provider, true);
        } else {
            challenge.status = ChallengeStatus.Failed;
            providerRegistry.recordChallenge(challenge.provider, false);
            // Slash collateral if deal exists
            // pinDealEscrow.slashCollateral(challenge.dealId, slashAmount);
        }
        
        emit ChallengeVerified(challengeId, success);
        return success;
    }
    
    /**
     * @notice Get challenges for a provider
     * @param provider Provider address
     * @return challengeIds Array of challenge IDs
     */
    function getProviderChallenges(address provider) external view returns (bytes32[] memory) {
        return providerChallenges[provider];
    }
    
    /**
     * @notice Get challenges for a deal
     * @param dealId Deal identifier
     * @return challengeIds Array of challenge IDs
     */
    function getDealChallenges(bytes32 dealId) external view returns (bytes32[] memory) {
        return dealChallenges[dealId];
    }
}
