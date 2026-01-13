// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PinDealEscrow
 * @notice Manage storage deals (Filecoin-style, ARC-native)
 * @dev Part of THOT-DAIO architecture for dataset marketplace
 */
contract PinDealEscrow {
    struct PinDeal {
        bytes32 dealId;
        bytes32 rootCID;
        address provider;
        address buyer;
        uint256 startBlock;
        uint256 endBlock;
        uint256 pricePerEpoch;      // Price per block/epoch
        uint256 collateral;         // Provider collateral
        uint256 challengeFrequency; // Blocks between challenges
        uint256 totalPaid;           // Total amount paid so far
        DealStatus status;
    }
    
    enum DealStatus { Pending, Active, Completed, Cancelled, Slashed }
    
    mapping(bytes32 => PinDeal) public deals;
    mapping(address => bytes32[]) public providerDeals;
    mapping(address => bytes32[]) public buyerDeals;
    
    address public owner;
    address public challengeManager;  // ChallengeManager contract address
    
    event DealCreated(bytes32 indexed dealId, bytes32 rootCID, address provider, address buyer, uint256 pricePerEpoch);
    event DealActivated(bytes32 indexed dealId);
    event DealCompleted(bytes32 indexed dealId);
    event DealCancelled(bytes32 indexed dealId);
    event PaymentReleased(bytes32 indexed dealId, address provider, uint256 amount);
    event CollateralSlashed(bytes32 indexed dealId, address provider, uint256 amount);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    modifier onlyChallengeManager() {
        require(msg.sender == challengeManager, "Only ChallengeManager");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @notice Set ChallengeManager contract address
     * @param _challengeManager ChallengeManager contract address
     */
    function setChallengeManager(address _challengeManager) external onlyOwner {
        challengeManager = _challengeManager;
    }
    
    /**
     * @notice Create a new storage deal
     * @param rootCID Dataset root CID
     * @param provider Provider address
     * @param durationBlocks Duration in blocks
     * @param pricePerEpoch Price per block/epoch
     * @param challengeFrequency Blocks between challenges
     * @return dealId The created deal ID
     */
    function createDeal(
        bytes32 rootCID,
        address provider,
        uint256 durationBlocks,
        uint256 pricePerEpoch,
        uint256 challengeFrequency
    ) external payable returns (bytes32) {
        require(rootCID != bytes32(0), "Invalid CID");
        require(provider != address(0), "Invalid provider");
        require(durationBlocks > 0, "Invalid duration");
        require(pricePerEpoch > 0, "Invalid price");
        require(msg.value >= (pricePerEpoch * durationBlocks), "Insufficient payment");
        
        bytes32 dealId = keccak256(abi.encodePacked(rootCID, provider, msg.sender, block.timestamp, block.number));
        
        deals[dealId] = PinDeal({
            dealId: dealId,
            rootCID: rootCID,
            provider: provider,
            buyer: msg.sender,
            startBlock: 0,  // Set when activated
            endBlock: 0,    // Set when activated
            pricePerEpoch: pricePerEpoch,
            collateral: 0,  // Provider can add collateral separately
            challengeFrequency: challengeFrequency,
            totalPaid: 0,
            status: DealStatus.Pending
        });
        
        providerDeals[provider].push(dealId);
        buyerDeals[msg.sender].push(dealId);
        
        emit DealCreated(dealId, rootCID, provider, msg.sender, pricePerEpoch);
        return dealId;
    }
    
    /**
     * @notice Activate a deal (provider confirms they're ready)
     * @param dealId Deal identifier
     */
    function activateDeal(bytes32 dealId) external {
        PinDeal storage deal = deals[dealId];
        require(deal.provider == msg.sender, "Only provider");
        require(deal.status == DealStatus.Pending, "Deal not pending");
        
        deal.startBlock = block.number;
        deal.endBlock = block.number + ((address(this).balance / deal.pricePerEpoch) * deal.pricePerEpoch) / deal.pricePerEpoch;
        deal.status = DealStatus.Active;
        
        emit DealActivated(dealId);
    }
    
    /**
     * @notice Cancel a deal (before activation)
     * @param dealId Deal identifier
     */
    function cancelDeal(bytes32 dealId) external {
        PinDeal storage deal = deals[dealId];
        require(
            deal.buyer == msg.sender || deal.provider == msg.sender,
            "Not authorized"
        );
        require(deal.status == DealStatus.Pending, "Deal already active");
        
        deal.status = DealStatus.Cancelled;
        
        // Refund buyer
        uint256 refund = address(this).balance;  // Simplified - should track per-deal
        if (refund > 0) {
            payable(deal.buyer).transfer(refund);
        }
        
        emit DealCancelled(dealId);
    }
    
    /**
     * @notice Release payment to provider for completed epochs
     * @param dealId Deal identifier
     * @param epochs Number of epochs to pay for
     */
    function releasePayment(bytes32 dealId, uint256 epochs) external {
        PinDeal storage deal = deals[dealId];
        require(deal.status == DealStatus.Active, "Deal not active");
        require(block.number >= deal.startBlock, "Deal not started");
        
        uint256 payment = deal.pricePerEpoch * epochs;
        require(payment <= address(this).balance, "Insufficient balance");
        require(deal.totalPaid + payment <= (deal.pricePerEpoch * ((deal.endBlock - deal.startBlock) / 1)), "Overpayment");
        
        deal.totalPaid += payment;
        payable(deal.provider).transfer(payment);
        
        // Check if deal is completed
        if (block.number >= deal.endBlock || deal.totalPaid >= (deal.pricePerEpoch * ((deal.endBlock - deal.startBlock) / 1))) {
            deal.status = DealStatus.Completed;
            emit DealCompleted(dealId);
        }
        
        emit PaymentReleased(dealId, deal.provider, payment);
    }
    
    /**
     * @notice Slash provider collateral (called by ChallengeManager)
     * @param dealId Deal identifier
     * @param amount Amount to slash
     */
    function slashCollateral(bytes32 dealId, uint256 amount) external onlyChallengeManager {
        PinDeal storage deal = deals[dealId];
        require(deal.status == DealStatus.Active, "Deal not active");
        require(deal.collateral >= amount, "Insufficient collateral");
        
        deal.collateral -= amount;
        deal.status = DealStatus.Slashed;
        
        // Transfer slashed amount to buyer as compensation
        payable(deal.buyer).transfer(amount);
        
        emit CollateralSlashed(dealId, deal.provider, amount);
    }
    
    /**
     * @notice Add collateral to a deal (provider)
     * @param dealId Deal identifier
     */
    function addCollateral(bytes32 dealId) external payable {
        PinDeal storage deal = deals[dealId];
        require(deal.provider == msg.sender, "Only provider");
        require(deal.status == DealStatus.Active || deal.status == DealStatus.Pending, "Invalid status");
        require(msg.value > 0, "Invalid amount");
        
        deal.collateral += msg.value;
    }
}
