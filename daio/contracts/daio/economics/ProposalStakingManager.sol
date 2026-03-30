// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../governance/TriumvirateGovernance.sol";
import "../treasury/TreasuryFeeCollector.sol";

/**
 * @title ProposalStakingManager
 * @notice Economic incentives and staking for proposals with winner-takes-all mechanics
 * @dev Manages proposal staking, competition pools, and reward distribution
 */
contract ProposalStakingManager is AccessControl, ReentrancyGuard {

    bytes32 public constant STAKING_MANAGER_ROLE = keccak256("STAKING_MANAGER_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");

    enum ProposalCategory {
        OPERATIONAL,    // 0.1-1 ETH stake
        STRATEGIC,      // 1-5 ETH stake
        CONSTITUTIONAL, // 5-20 ETH stake
        ECONOMIC,       // 2-10 ETH stake
        EMERGENCY       // 0.01-0.5 ETH stake
    }

    enum StakeStatus {
        ACTIVE,         // Stake is active in competition
        WON,            // Proposal won, stake returned + rewards
        LOST,           // Proposal lost, stake forfeited
        REFUNDED,       // Stake refunded (cancelled proposal)
        SLASHED         // Stake slashed (malicious proposal)
    }

    struct StakePool {
        uint256 poolId;
        string poolName;
        ProposalCategory category;
        uint256[] competingProposals;
        uint256 totalStaked;
        uint256 winnerProposalId;
        bool finalized;
        uint256 createdAt;
        uint256 finalizedAt;

        // Distribution percentages
        uint256 winnerShare;        // 70% to winner
        uint256 treasuryShare;      // 20% to treasury
        uint256 sponsorShare;       // 10% to sponsors
    }

    struct ProposalStake {
        uint256 proposalId;
        uint256 poolId;
        address proposer;
        uint256 stakeAmount;
        uint256 totalBacking;       // Total backing from supporters
        address[] supporters;
        mapping(address => uint256) supporterStakes;
        StakeStatus status;
        uint256 stakedAt;
        bool withdrawn;
    }

    struct StakingTiers {
        uint256 minStake;
        uint256 maxStake;
        uint256 multiplier;         // Reward multiplier for this tier
        string description;
    }

    struct CompetitionRound {
        uint256 roundId;
        uint256 poolId;
        uint256 startTime;
        uint256 endTime;
        uint256[] participatingProposals;
        mapping(uint256 => uint256) proposalVotes;
        uint256 totalVotes;
        bool concluded;
        uint256 winnerProposalId;
    }

    // Storage
    mapping(uint256 => StakePool) public stakePools;
    mapping(uint256 => ProposalStake) public proposalStakes;
    mapping(ProposalCategory => StakingTiers) public stakingTiers;
    mapping(uint256 => CompetitionRound) public competitionRounds;
    mapping(address => uint256) public totalStaked;
    mapping(address => uint256) public totalRewardsEarned;
    mapping(uint256 => uint256[]) public poolsByCategory; // Category => Pool IDs

    uint256 public poolCount;
    uint256 public roundCount;
    uint256 public totalValueLocked;
    uint256 public totalRewardsDistributed;

    // Configuration
    uint256 public constant BASIS_POINTS = 10000;
    uint256 public defaultWinnerShare = 7000;    // 70%
    uint256 public defaultTreasuryShare = 2000;  // 20%
    uint256 public defaultSponsorShare = 1000;   // 10%
    uint256 public minCompetitors = 2;           // Minimum proposals for competition
    uint256 public maxCompetitors = 10;          // Maximum proposals per pool

    // Integration contracts
    TriumvirateGovernance public triumvirateGovernance;
    TreasuryFeeCollector public feeCollector;

    // Events
    event StakePoolCreated(
        uint256 indexed poolId,
        string poolName,
        ProposalCategory category,
        uint256 timestamp
    );

    event ProposalStaked(
        uint256 indexed proposalId,
        uint256 indexed poolId,
        address indexed proposer,
        uint256 stakeAmount
    );

    event SupporterBackingAdded(
        uint256 indexed proposalId,
        address indexed supporter,
        uint256 backingAmount,
        uint256 totalBacking
    );

    event CompetitionFinalized(
        uint256 indexed poolId,
        uint256 indexed winnerProposalId,
        uint256 totalPool,
        uint256 winnerReward
    );

    event RewardsDistributed(
        uint256 indexed poolId,
        address indexed winner,
        uint256 winnerAmount,
        uint256 treasuryAmount,
        uint256 sponsorAmount
    );

    event StakeWithdrawn(
        uint256 indexed proposalId,
        address indexed staker,
        uint256 amount,
        StakeStatus status
    );

    event StakingTierUpdated(
        ProposalCategory category,
        uint256 minStake,
        uint256 maxStake,
        uint256 multiplier
    );

    modifier validPool(uint256 poolId) {
        require(poolId > 0 && poolId <= poolCount, "Invalid pool ID");
        require(stakePools[poolId].poolId > 0, "Pool doesn't exist");
        _;
    }

    modifier validProposal(uint256 proposalId) {
        require(proposalStakes[proposalId].proposalId > 0, "Proposal stake doesn't exist");
        _;
    }

    modifier onlyStakingManager() {
        require(hasRole(STAKING_MANAGER_ROLE, msg.sender), "Not staking manager");
        _;
    }

    constructor(
        address _triumvirateGovernance,
        address _feeCollector
    ) {
        require(_triumvirateGovernance != address(0), "Invalid governance");
        require(_feeCollector != address(0), "Invalid fee collector");

        triumvirateGovernance = TriumvirateGovernance(_triumvirateGovernance);
        feeCollector = TreasuryFeeCollector(payable(_feeCollector));

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(STAKING_MANAGER_ROLE, msg.sender);
        _grantRole(TREASURY_ROLE, msg.sender);

        _initializeStakingTiers();
    }

    /**
     * @notice Create new stake pool for proposal competition
     * @param poolName Pool name/description
     * @param category Proposal category
     * @param customShares Custom distribution shares (optional)
     */
    function createStakePool(
        string memory poolName,
        ProposalCategory category,
        uint256[3] memory customShares // [winner, treasury, sponsor] percentages
    ) external onlyStakingManager returns (uint256 poolId) {
        require(bytes(poolName).length > 0, "Pool name required");

        poolCount++;
        uint256 winnerShare = customShares[0] > 0 ? customShares[0] : defaultWinnerShare;
        uint256 treasuryShare = customShares[1] > 0 ? customShares[1] : defaultTreasuryShare;
        uint256 sponsorShare = customShares[2] > 0 ? customShares[2] : defaultSponsorShare;

        require(winnerShare + treasuryShare + sponsorShare == BASIS_POINTS, "Shares must equal 100%");

        stakePools[poolCount] = StakePool({
            poolId: poolCount,
            poolName: poolName,
            category: category,
            competingProposals: new uint256[](0),
            totalStaked: 0,
            winnerProposalId: 0,
            finalized: false,
            createdAt: block.timestamp,
            finalizedAt: 0,
            winnerShare: winnerShare,
            treasuryShare: treasuryShare,
            sponsorShare: sponsorShare
        });

        poolsByCategory[uint256(category)].push(poolCount);

        emit StakePoolCreated(poolCount, poolName, category, block.timestamp);
        return poolCount;
    }

    /**
     * @notice Stake ETH on a proposal
     * @param proposalId Proposal ID
     * @param poolId Pool ID to compete in
     */
    function stakeOnProposal(
        uint256 proposalId,
        uint256 poolId
    ) external payable validPool(poolId) nonReentrant {
        require(msg.value > 0, "Must stake ETH");
        require(proposalStakes[proposalId].proposalId == 0, "Proposal already staked");

        StakePool storage pool = stakePools[poolId];
        require(!pool.finalized, "Pool already finalized");
        require(pool.competingProposals.length < maxCompetitors, "Pool full");

        StakingTiers memory tier = stakingTiers[pool.category];
        require(msg.value >= tier.minStake && msg.value <= tier.maxStake, "Stake amount out of range");

        // Create proposal stake
        ProposalStake storage stake = proposalStakes[proposalId];
        stake.proposalId = proposalId;
        stake.poolId = poolId;
        stake.proposer = msg.sender;
        stake.stakeAmount = msg.value;
        stake.totalBacking = msg.value;
        stake.status = StakeStatus.ACTIVE;
        stake.stakedAt = block.timestamp;
        stake.withdrawn = false;

        stake.supporters.push(msg.sender);
        stake.supporterStakes[msg.sender] = msg.value;

        // Update pool
        pool.competingProposals.push(proposalId);
        pool.totalStaked += msg.value;

        // Update global tracking
        totalStaked[msg.sender] += msg.value;
        totalValueLocked += msg.value;

        emit ProposalStaked(proposalId, poolId, msg.sender, msg.value);
    }

    /**
     * @notice Add backing support to existing proposal
     * @param proposalId Proposal ID
     */
    function addBacking(uint256 proposalId) external payable validProposal(proposalId) nonReentrant {
        require(msg.value > 0, "Must send ETH");

        ProposalStake storage stake = proposalStakes[proposalId];
        require(stake.status == StakeStatus.ACTIVE, "Proposal not active");

        StakePool storage pool = stakePools[stake.poolId];
        require(!pool.finalized, "Pool finalized");

        // Add supporter if new
        if (stake.supporterStakes[msg.sender] == 0) {
            stake.supporters.push(msg.sender);
        }

        stake.supporterStakes[msg.sender] += msg.value;
        stake.totalBacking += msg.value;
        pool.totalStaked += msg.value;

        totalStaked[msg.sender] += msg.value;
        totalValueLocked += msg.value;

        emit SupporterBackingAdded(proposalId, msg.sender, msg.value, stake.totalBacking);
    }

    /**
     * @notice Finalize competition and declare winner
     * @param poolId Pool ID
     * @param winnerProposalId Winning proposal ID
     */
    function finalizeCompetition(
        uint256 poolId,
        uint256 winnerProposalId
    ) external validPool(poolId) onlyStakingManager nonReentrant {
        StakePool storage pool = stakePools[poolId];
        require(!pool.finalized, "Pool already finalized");
        require(pool.competingProposals.length >= minCompetitors, "Insufficient competitors");
        require(_isProposalInPool(poolId, winnerProposalId), "Winner not in pool");

        pool.winnerProposalId = winnerProposalId;
        pool.finalized = true;
        pool.finalizedAt = block.timestamp;

        // Update proposal statuses
        for (uint i = 0; i < pool.competingProposals.length; i++) {
            uint256 proposalId = pool.competingProposals[i];
            if (proposalId == winnerProposalId) {
                proposalStakes[proposalId].status = StakeStatus.WON;
            } else {
                proposalStakes[proposalId].status = StakeStatus.LOST;
            }
        }

        // Calculate rewards
        uint256 winnerReward = (pool.totalStaked * pool.winnerShare) / BASIS_POINTS;

        emit CompetitionFinalized(poolId, winnerProposalId, pool.totalStaked, winnerReward);

        _distributeRewards(poolId);
    }

    /**
     * @notice Withdraw stakes and rewards
     * @param proposalId Proposal ID
     */
    function withdrawStake(uint256 proposalId) external validProposal(proposalId) nonReentrant {
        ProposalStake storage stake = proposalStakes[proposalId];
        require(!stake.withdrawn, "Already withdrawn");

        StakePool storage pool = stakePools[stake.poolId];
        require(pool.finalized, "Pool not finalized");

        uint256 supporterStakeAmount = stake.supporterStakes[msg.sender];
        require(supporterStakeAmount > 0, "No stake to withdraw");

        stake.supporterStakes[msg.sender] = 0;
        stake.withdrawn = true;

        uint256 withdrawAmount = 0;

        if (stake.status == StakeStatus.WON) {
            // Calculate proportional share of winnings
            uint256 totalWinnerReward = (pool.totalStaked * pool.winnerShare) / BASIS_POINTS;
            withdrawAmount = supporterStakeAmount +
                           ((totalWinnerReward * supporterStakeAmount) / stake.totalBacking);
        } else if (stake.status == StakeStatus.REFUNDED) {
            withdrawAmount = supporterStakeAmount;
        }
        // For LOST status, withdrawAmount remains 0

        if (withdrawAmount > 0) {
            totalValueLocked -= supporterStakeAmount;
            payable(msg.sender).transfer(withdrawAmount);

            if (stake.status == StakeStatus.WON) {
                totalRewardsEarned[msg.sender] += (withdrawAmount - supporterStakeAmount);
            }
        }

        emit StakeWithdrawn(proposalId, msg.sender, withdrawAmount, stake.status);
    }

    /**
     * @notice Emergency refund for cancelled proposals
     * @param proposalId Proposal ID
     */
    function emergencyRefund(uint256 proposalId) external validProposal(proposalId) onlyStakingManager {
        ProposalStake storage stake = proposalStakes[proposalId];
        require(stake.status == StakeStatus.ACTIVE, "Not eligible for refund");

        stake.status = StakeStatus.REFUNDED;

        StakePool storage pool = stakePools[stake.poolId];

        // Remove from competition
        for (uint i = 0; i < pool.competingProposals.length; i++) {
            if (pool.competingProposals[i] == proposalId) {
                pool.competingProposals[i] = pool.competingProposals[pool.competingProposals.length - 1];
                pool.competingProposals.pop();
                break;
            }
        }

        pool.totalStaked -= stake.totalBacking;
    }

    /**
     * @notice Update staking tiers for proposal categories
     * @param category Proposal category
     * @param minStake Minimum stake amount
     * @param maxStake Maximum stake amount
     * @param multiplier Reward multiplier
     * @param description Tier description
     */
    function updateStakingTier(
        ProposalCategory category,
        uint256 minStake,
        uint256 maxStake,
        uint256 multiplier,
        string memory description
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(minStake <= maxStake, "Invalid stake range");
        require(multiplier > 0, "Invalid multiplier");

        stakingTiers[category] = StakingTiers({
            minStake: minStake,
            maxStake: maxStake,
            multiplier: multiplier,
            description: description
        });

        emit StakingTierUpdated(category, minStake, maxStake, multiplier);
    }

    /**
     * @notice Get stake pool details
     * @param poolId Pool ID
     * @return poolName Pool name
     * @return category Pool category
     * @return poolTotalStaked Total amount staked
     * @return winnerProposalId Winner proposal ID
     * @return finalized Whether pool is finalized
     * @return competitorsCount Number of competitors
     */
    function getStakePool(uint256 poolId) external view validPool(poolId) returns (
        string memory poolName,
        ProposalCategory category,
        uint256 poolTotalStaked,
        uint256 winnerProposalId,
        bool finalized,
        uint256 competitorsCount
    ) {
        StakePool storage pool = stakePools[poolId];
        return (
            pool.poolName,
            pool.category,
            pool.totalStaked,
            pool.winnerProposalId,
            pool.finalized,
            pool.competingProposals.length
        );
    }

    /**
     * @notice Get proposal stake details
     * @param proposalId Proposal ID
     * @return poolId Pool ID
     * @return proposer Proposer address
     * @return stakeAmount Stake amount
     * @return totalBacking Total backing amount
     * @return status Stake status
     * @return supportersCount Number of supporters
     */
    function getProposalStake(uint256 proposalId) external view validProposal(proposalId) returns (
        uint256 poolId,
        address proposer,
        uint256 stakeAmount,
        uint256 totalBacking,
        StakeStatus status,
        uint256 supportersCount
    ) {
        ProposalStake storage stake = proposalStakes[proposalId];
        return (
            stake.poolId,
            stake.proposer,
            stake.stakeAmount,
            stake.totalBacking,
            stake.status,
            stake.supporters.length
        );
    }

    /**
     * @notice Get supporter stake amount
     * @param proposalId Proposal ID
     * @param supporter Supporter address
     * @return Stake amount by supporter
     */
    function getSupporterStake(uint256 proposalId, address supporter) external view returns (uint256) {
        return proposalStakes[proposalId].supporterStakes[supporter];
    }

    /**
     * @notice Get competing proposals in pool
     * @param poolId Pool ID
     * @return Array of competing proposal IDs
     */
    function getPoolCompetitors(uint256 poolId) external view validPool(poolId) returns (uint256[] memory) {
        return stakePools[poolId].competingProposals;
    }

    /**
     * @notice Get pools by category
     * @param category Proposal category
     * @return Array of pool IDs
     */
    function getPoolsByCategory(ProposalCategory category) external view returns (uint256[] memory) {
        return poolsByCategory[uint256(category)];
    }

    /**
     * @notice Initialize staking tiers with default values
     */
    function _initializeStakingTiers() internal {
        stakingTiers[ProposalCategory.OPERATIONAL] = StakingTiers({
            minStake: 0.1 ether,
            maxStake: 1 ether,
            multiplier: 100,
            description: "Operational proposals"
        });

        stakingTiers[ProposalCategory.STRATEGIC] = StakingTiers({
            minStake: 1 ether,
            maxStake: 5 ether,
            multiplier: 150,
            description: "Strategic direction proposals"
        });

        stakingTiers[ProposalCategory.CONSTITUTIONAL] = StakingTiers({
            minStake: 5 ether,
            maxStake: 20 ether,
            multiplier: 200,
            description: "Constitutional changes"
        });

        stakingTiers[ProposalCategory.ECONOMIC] = StakingTiers({
            minStake: 2 ether,
            maxStake: 10 ether,
            multiplier: 175,
            description: "Economic and treasury decisions"
        });

        stakingTiers[ProposalCategory.EMERGENCY] = StakingTiers({
            minStake: 0.01 ether,
            maxStake: 0.5 ether,
            multiplier: 120,
            description: "Emergency actions"
        });
    }

    /**
     * @notice Distribute rewards from finalized pool
     * @param poolId Pool ID
     */
    function _distributeRewards(uint256 poolId) internal {
        StakePool storage pool = stakePools[poolId];
        require(pool.finalized, "Pool not finalized");

        uint256 winnerAmount = (pool.totalStaked * pool.winnerShare) / BASIS_POINTS;
        uint256 treasuryAmount = (pool.totalStaked * pool.treasuryShare) / BASIS_POINTS;
        uint256 sponsorAmount = (pool.totalStaked * pool.sponsorShare) / BASIS_POINTS;

        // Send treasury fee
        if (treasuryAmount > 0) {
            feeCollector.collectFee{value: treasuryAmount}("competition_treasury_fee", poolId);
        }

        // Sponsor rewards would be distributed to proposal sponsors
        // Winner rewards are claimed via withdrawStake()

        totalRewardsDistributed += winnerAmount + sponsorAmount;

        emit RewardsDistributed(poolId, proposalStakes[pool.winnerProposalId].proposer, winnerAmount, treasuryAmount, sponsorAmount);
    }

    /**
     * @notice Check if proposal is in the specified pool
     * @param poolId Pool ID
     * @param proposalId Proposal ID
     * @return exists Whether proposal exists in pool
     */
    function _isProposalInPool(uint256 poolId, uint256 proposalId) internal view returns (bool) {
        uint256[] memory competitors = stakePools[poolId].competingProposals;
        for (uint i = 0; i < competitors.length; i++) {
            if (competitors[i] == proposalId) {
                return true;
            }
        }
        return false;
    }

    /**
     * @notice Emergency withdrawal for contract admin
     */
    function emergencyWithdraw() external onlyRole(DEFAULT_ADMIN_ROLE) {
        payable(msg.sender).transfer(address(this).balance);
    }

    /**
     * @notice Fallback function to receive ETH
     */
    receive() external payable {
        // Allow contract to receive ETH
    }
}