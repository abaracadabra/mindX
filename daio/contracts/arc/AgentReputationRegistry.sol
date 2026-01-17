// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AgentReputationRegistry
 * @notice Track reputation and performance metrics for agents in AgenticPlace
 * @dev Integrates with AgenticMarketplaceEscrow for automated reputation updates
 */
contract AgentReputationRegistry {
    
    struct AgentProfile {
        address agentAddress;
        string agentId;             // Off-chain agent identifier
        string name;
        string category;            // e.g., "data-analysis", "content-creation", "trading"
        uint256 reputationScore;    // 0-10000 (basis points)
        uint256 totalJobs;
        uint256 completedJobs;
        uint256 disputedJobs;
        uint256 totalEarnings;      // Total USDC earned
        uint256 averageRating;      // 0-5000 (basis points, 5.00 = 5000)
        uint256 totalRatings;
        uint256 responseTime;       // Average response time in seconds
        uint256 completionRate;     // Percentage in basis points
        bool isActive;
        bool isVerified;
        uint256 registeredAt;
        uint256 lastActiveAt;
    }
    
    struct Review {
        bytes32 reviewId;
        bytes32 agreementId;
        address reviewer;
        address agent;
        uint256 rating;             // 0-5000 (basis points)
        string comment;
        uint256 createdAt;
    }
    
    struct PerformanceMetrics {
        uint256 onTimeDeliveries;
        uint256 lateDeliveries;
        uint256 averageCompletionTime;
        uint256 customerSatisfaction;
        uint256 repeatCustomerRate;
    }
    
    mapping(address => AgentProfile) public agents;
    mapping(address => PerformanceMetrics) public metrics;
    mapping(bytes32 => Review) public reviews;
    mapping(address => bytes32[]) public agentReviews;
    mapping(string => address) public agentIdToAddress;
    
    address public owner;
    address public escrowContract;
    uint256 public totalAgents;
    
    event AgentRegistered(address indexed agent, string agentId, string name);
    event AgentVerified(address indexed agent);
    event AgentDeactivated(address indexed agent);
    event ReputationUpdated(address indexed agent, uint256 newScore);
    event ReviewSubmitted(bytes32 indexed reviewId, address indexed agent, uint256 rating);
    event MetricsUpdated(address indexed agent);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    modifier onlyEscrow() {
        require(msg.sender == escrowContract, "Only escrow contract");
        _;
    }
    
    modifier onlyActiveAgent() {
        require(agents[msg.sender].isActive, "Agent not active");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    function setEscrowContract(address _escrowContract) external onlyOwner {
        escrowContract = _escrowContract;
    }
    
    /**
     * @notice Register a new agent
     * @param agentId Off-chain agent identifier
     * @param name Agent name
     * @param category Agent category
     */
    function registerAgent(
        string memory agentId,
        string memory name,
        string memory category
    ) external returns (bool) {
        require(!agents[msg.sender].isActive, "Already registered");
        require(bytes(agentId).length > 0, "Invalid agent ID");
        require(agentIdToAddress[agentId] == address(0), "Agent ID taken");
        
        agents[msg.sender] = AgentProfile({
            agentAddress: msg.sender,
            agentId: agentId,
            name: name,
            category: category,
            reputationScore: 5000,  // Start at 50%
            totalJobs: 0,
            completedJobs: 0,
            disputedJobs: 0,
            totalEarnings: 0,
            averageRating: 0,
            totalRatings: 0,
            responseTime: 0,
            completionRate: 0,
            isActive: true,
            isVerified: false,
            registeredAt: block.timestamp,
            lastActiveAt: block.timestamp
        });
        
        agentIdToAddress[agentId] = msg.sender;
        totalAgents++;
        
        emit AgentRegistered(msg.sender, agentId, name);
        return true;
    }
    
    /**
     * @notice Update agent profile
     * @param name New name
     * @param category New category
     */
    function updateProfile(string memory name, string memory category) external onlyActiveAgent {
        AgentProfile storage agent = agents[msg.sender];
        agent.name = name;
        agent.category = category;
        agent.lastActiveAt = block.timestamp;
    }
    
    /**
     * @notice Verify an agent (owner only)
     * @param agent Agent address
     */
    function verifyAgent(address agent) external onlyOwner {
        require(agents[agent].isActive, "Agent not active");
        agents[agent].isVerified = true;
        emit AgentVerified(agent);
    }
    
    /**
     * @notice Submit a review for an agent
     * @param agreementId Agreement identifier
     * @param agent Agent address
     * @param rating Rating (0-5000 basis points)
     * @param comment Review comment
     */
    function submitReview(
        bytes32 agreementId,
        address agent,
        uint256 rating,
        string memory comment
    ) external returns (bytes32) {
        require(agents[agent].isActive, "Agent not active");
        require(rating <= 5000, "Invalid rating");
        
        bytes32 reviewId = keccak256(
            abi.encodePacked(
                agreementId,
                msg.sender,
                agent,
                block.timestamp
            )
        );
        
        reviews[reviewId] = Review({
            reviewId: reviewId,
            agreementId: agreementId,
            reviewer: msg.sender,
            agent: agent,
            rating: rating,
            comment: comment,
            createdAt: block.timestamp
        });
        
        agentReviews[agent].push(reviewId);
        
        // Update agent's average rating
        AgentProfile storage agentProfile = agents[agent];
        agentProfile.totalRatings++;
        agentProfile.averageRating = 
            ((agentProfile.averageRating * (agentProfile.totalRatings - 1)) + rating) / 
            agentProfile.totalRatings;
        
        // Update reputation based on rating
        _updateReputation(agent);
        
        emit ReviewSubmitted(reviewId, agent, rating);
        return reviewId;
    }
    
    /**
     * @notice Record job completion (called by escrow contract)
     * @param agent Agent address
     * @param earnings Amount earned
     * @param onTime Whether delivered on time
     */
    function recordJobCompletion(
        address agent,
        uint256 earnings,
        bool onTime
    ) external onlyEscrow {
        AgentProfile storage agentProfile = agents[agent];
        PerformanceMetrics storage agentMetrics = metrics[agent];
        
        agentProfile.totalJobs++;
        agentProfile.completedJobs++;
        agentProfile.totalEarnings += earnings;
        agentProfile.lastActiveAt = block.timestamp;
        
        if (onTime) {
            agentMetrics.onTimeDeliveries++;
        } else {
            agentMetrics.lateDeliveries++;
        }
        
        // Update completion rate
        agentProfile.completionRate = 
            (agentProfile.completedJobs * 10000) / agentProfile.totalJobs;
        
        _updateReputation(agent);
        
        emit MetricsUpdated(agent);
    }
    
    /**
     * @notice Record job dispute (called by escrow contract)
     * @param agent Agent address
     */
    function recordDispute(address agent) external onlyEscrow {
        AgentProfile storage agentProfile = agents[agent];
        agentProfile.disputedJobs++;
        
        _updateReputation(agent);
        
        emit MetricsUpdated(agent);
    }
    
    /**
     * @notice Update agent reputation score
     * @param agent Agent address
     */
    function _updateReputation(address agent) internal {
        AgentProfile storage agentProfile = agents[agent];
        
        // Calculate reputation based on multiple factors
        uint256 ratingScore = agentProfile.averageRating * 2;  // 0-10000
        uint256 completionScore = agentProfile.completionRate;  // 0-10000
        
        // Dispute penalty
        uint256 disputeRate = agentProfile.totalJobs > 0 
            ? (agentProfile.disputedJobs * 10000) / agentProfile.totalJobs 
            : 0;
        uint256 disputePenalty = disputeRate * 2;  // Double weight for disputes
        
        // Weighted average
        uint256 newScore = (ratingScore * 40 + completionScore * 40 + (10000 - disputePenalty) * 20) / 100;
        
        // Ensure score is within bounds
        if (newScore > 10000) newScore = 10000;
        
        agentProfile.reputationScore = newScore;
        
        emit ReputationUpdated(agent, newScore);
    }
    
    /**
     * @notice Deactivate agent
     */
    function deactivateAgent() external onlyActiveAgent {
        agents[msg.sender].isActive = false;
        emit AgentDeactivated(msg.sender);
    }
    
    /**
     * @notice Get agent profile
     * @param agent Agent address
     */
    function getAgentProfile(address agent) external view returns (AgentProfile memory) {
        return agents[agent];
    }
    
    /**
     * @notice Get agent metrics
     * @param agent Agent address
     */
    function getAgentMetrics(address agent) external view returns (PerformanceMetrics memory) {
        return metrics[agent];
    }
    
    /**
     * @notice Get agent reviews
     * @param agent Agent address
     */
    function getAgentReviews(address agent) external view returns (bytes32[] memory) {
        return agentReviews[agent];
    }
    
    /**
     * @notice Get review details
     * @param reviewId Review identifier
     */
    function getReview(bytes32 reviewId) external view returns (Review memory) {
        return reviews[reviewId];
    }
    
    /**
     * @notice Get agent address by ID
     * @param agentId Agent identifier
     */
    function getAgentByAgentId(string memory agentId) external view returns (address) {
        return agentIdToAddress[agentId];
    }
}
