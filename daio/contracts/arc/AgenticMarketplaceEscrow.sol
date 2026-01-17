// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AgenticMarketplaceEscrow
 * @notice Core settlement layer for AgenticPlace - handles escrow and payment settlement for agentic services
 * @dev Supports milestone-based payments, dispute resolution, and automated settlements
 */
contract AgenticMarketplaceEscrow {
    
    // ============ Structs ============
    
    struct ServiceAgreement {
        bytes32 agreementId;
        address buyer;              // Service buyer (human or agent)
        address seller;             // Service provider (agent)
        uint256 totalAmount;        // Total USDC amount (6 decimals)
        uint256 escrowedAmount;     // Currently escrowed amount
        uint256 releasedAmount;     // Amount released to seller
        uint256 refundedAmount;     // Amount refunded to buyer
        uint256 createdAt;
        uint256 expiresAt;
        AgreementStatus status;
        SettlementType settlementType;
        bytes32[] milestones;       // Milestone IDs for milestone-based agreements
    }
    
    struct Milestone {
        bytes32 milestoneId;
        bytes32 agreementId;
        string description;
        uint256 amount;             // USDC amount for this milestone
        uint256 dueDate;
        MilestoneStatus status;
        uint256 completedAt;
        bytes proofHash;            // Hash of completion proof
    }
    
    struct Dispute {
        bytes32 disputeId;
        bytes32 agreementId;
        address initiator;
        string reason;
        uint256 createdAt;
        uint256 resolvedAt;
        DisputeStatus status;
        DisputeResolution resolution;
        address resolver;           // Arbitrator address
    }
    
    // ============ Enums ============
    
    enum AgreementStatus {
        Pending,        // Created but not funded
        Active,         // Funded and active
        Completed,      // Successfully completed
        Cancelled,      // Cancelled before completion
        Disputed,       // Under dispute
        Expired         // Expired without completion
    }
    
    enum SettlementType {
        Immediate,      // Pay immediately upon completion
        Milestone,      // Pay per milestone
        Subscription,   // Recurring payments
        Escrow         // Hold until manual release
    }
    
    enum MilestoneStatus {
        Pending,
        InProgress,
        Completed,
        Approved,
        Rejected,
        Disputed
    }
    
    enum DisputeStatus {
        Open,
        UnderReview,
        Resolved,
        Escalated
    }
    
    enum DisputeResolution {
        None,
        RefundBuyer,
        PaySeller,
        PartialRefund,
        Cancelled
    }
    
    // ============ State Variables ============
    
    mapping(bytes32 => ServiceAgreement) public agreements;
    mapping(bytes32 => Milestone) public milestones;
    mapping(bytes32 => Dispute) public disputes;
    mapping(address => bytes32[]) public buyerAgreements;
    mapping(address => bytes32[]) public sellerAgreements;
    mapping(address => bool) public authorizedArbitrators;
    
    address public owner;
    address public feeCollector;
    uint256 public platformFeeRate;     // Basis points (e.g., 250 = 2.5%)
    uint256 public totalAgreements;
    uint256 public totalVolume;         // Total USDC volume processed
    
    // ============ Events ============
    
    event AgreementCreated(
        bytes32 indexed agreementId,
        address indexed buyer,
        address indexed seller,
        uint256 amount,
        SettlementType settlementType
    );
    
    event AgreementFunded(bytes32 indexed agreementId, uint256 amount);
    event AgreementCompleted(bytes32 indexed agreementId);
    event AgreementCancelled(bytes32 indexed agreementId);
    event AgreementExpired(bytes32 indexed agreementId);
    
    event MilestoneCreated(bytes32 indexed milestoneId, bytes32 indexed agreementId, uint256 amount);
    event MilestoneCompleted(bytes32 indexed milestoneId, bytes proofHash);
    event MilestoneApproved(bytes32 indexed milestoneId);
    event MilestoneRejected(bytes32 indexed milestoneId, string reason);
    
    event PaymentReleased(bytes32 indexed agreementId, address indexed seller, uint256 amount, uint256 fee);
    event RefundIssued(bytes32 indexed agreementId, address indexed buyer, uint256 amount);
    
    event DisputeCreated(bytes32 indexed disputeId, bytes32 indexed agreementId, address initiator);
    event DisputeResolved(bytes32 indexed disputeId, DisputeResolution resolution);
    
    // ============ Modifiers ============
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    modifier onlyArbitrator() {
        require(authorizedArbitrators[msg.sender], "Only arbitrator");
        _;
    }
    
    modifier onlyBuyer(bytes32 agreementId) {
        require(agreements[agreementId].buyer == msg.sender, "Only buyer");
        _;
    }
    
    modifier onlySeller(bytes32 agreementId) {
        require(agreements[agreementId].seller == msg.sender, "Only seller");
        _;
    }
    
    modifier agreementExists(bytes32 agreementId) {
        require(agreements[agreementId].buyer != address(0), "Agreement not found");
        _;
    }
    
    // ============ Constructor ============
    
    constructor(address _feeCollector, uint256 _platformFeeRate) {
        owner = msg.sender;
        feeCollector = _feeCollector;
        platformFeeRate = _platformFeeRate;
        authorizedArbitrators[msg.sender] = true;
    }
    
    // ============ Core Functions ============
    
    /**
     * @notice Create a new service agreement
     * @param seller Service provider address
     * @param totalAmount Total USDC amount (6 decimals)
     * @param duration Agreement duration in seconds
     * @param settlementType Type of settlement
     * @return agreementId The created agreement ID
     */
    function createAgreement(
        address seller,
        uint256 totalAmount,
        uint256 duration,
        SettlementType settlementType
    ) external payable returns (bytes32) {
        require(seller != address(0), "Invalid seller");
        require(seller != msg.sender, "Cannot create agreement with self");
        require(totalAmount > 0, "Invalid amount");
        require(duration > 0, "Invalid duration");
        
        bytes32 agreementId = keccak256(
            abi.encodePacked(
                msg.sender,
                seller,
                totalAmount,
                block.timestamp,
                totalAgreements
            )
        );
        
        agreements[agreementId] = ServiceAgreement({
            agreementId: agreementId,
            buyer: msg.sender,
            seller: seller,
            totalAmount: totalAmount,
            escrowedAmount: 0,
            releasedAmount: 0,
            refundedAmount: 0,
            createdAt: block.timestamp,
            expiresAt: block.timestamp + duration,
            status: AgreementStatus.Pending,
            settlementType: settlementType,
            milestones: new bytes32[](0)
        });
        
        buyerAgreements[msg.sender].push(agreementId);
        sellerAgreements[seller].push(agreementId);
        totalAgreements++;
        
        emit AgreementCreated(agreementId, msg.sender, seller, totalAmount, settlementType);
        
        // If immediate funding provided
        if (msg.value > 0) {
            _fundAgreement(agreementId, msg.value);
        }
        
        return agreementId;
    }
    
    /**
     * @notice Fund an agreement with USDC
     * @param agreementId Agreement identifier
     */
    function fundAgreement(bytes32 agreementId) 
        external 
        payable 
        agreementExists(agreementId)
        onlyBuyer(agreementId) 
    {
        _fundAgreement(agreementId, msg.value);
    }
    
    function _fundAgreement(bytes32 agreementId, uint256 amount) internal {
        ServiceAgreement storage agreement = agreements[agreementId];
        require(agreement.status == AgreementStatus.Pending, "Agreement not pending");
        require(amount > 0, "Invalid amount");
        require(agreement.escrowedAmount + amount <= agreement.totalAmount, "Exceeds total amount");
        
        agreement.escrowedAmount += amount;
        
        // Activate if fully funded
        if (agreement.escrowedAmount >= agreement.totalAmount) {
            agreement.status = AgreementStatus.Active;
        }
        
        emit AgreementFunded(agreementId, amount);
    }
    
    /**
     * @notice Create a milestone for an agreement
     * @param agreementId Agreement identifier
     * @param description Milestone description
     * @param amount USDC amount for milestone
     * @param dueDate Milestone due date
     * @return milestoneId The created milestone ID
     */
    function createMilestone(
        bytes32 agreementId,
        string memory description,
        uint256 amount,
        uint256 dueDate
    ) 
        external 
        agreementExists(agreementId)
        onlyBuyer(agreementId)
        returns (bytes32) 
    {
        ServiceAgreement storage agreement = agreements[agreementId];
        require(agreement.settlementType == SettlementType.Milestone, "Not milestone-based");
        require(amount > 0, "Invalid amount");
        require(dueDate > block.timestamp, "Invalid due date");
        
        bytes32 milestoneId = keccak256(
            abi.encodePacked(
                agreementId,
                description,
                amount,
                block.timestamp
            )
        );
        
        milestones[milestoneId] = Milestone({
            milestoneId: milestoneId,
            agreementId: agreementId,
            description: description,
            amount: amount,
            dueDate: dueDate,
            status: MilestoneStatus.Pending,
            completedAt: 0,
            proofHash: ""
        });
        
        agreement.milestones.push(milestoneId);
        
        emit MilestoneCreated(milestoneId, agreementId, amount);
        return milestoneId;
    }
    
    /**
     * @notice Mark milestone as completed (seller)
     * @param milestoneId Milestone identifier
     * @param proofHash Hash of completion proof
     */
    function completeMilestone(bytes32 milestoneId, bytes memory proofHash) external {
        Milestone storage milestone = milestones[milestoneId];
        require(milestone.milestoneId != bytes32(0), "Milestone not found");
        
        ServiceAgreement storage agreement = agreements[milestone.agreementId];
        require(agreement.seller == msg.sender, "Only seller");
        require(milestone.status == MilestoneStatus.Pending || milestone.status == MilestoneStatus.InProgress, "Invalid status");
        
        milestone.status = MilestoneStatus.Completed;
        milestone.completedAt = block.timestamp;
        milestone.proofHash = proofHash;
        
        emit MilestoneCompleted(milestoneId, proofHash);
    }
    
    /**
     * @notice Approve milestone and release payment (buyer)
     * @param milestoneId Milestone identifier
     */
    function approveMilestone(bytes32 milestoneId) external {
        Milestone storage milestone = milestones[milestoneId];
        require(milestone.milestoneId != bytes32(0), "Milestone not found");
        
        ServiceAgreement storage agreement = agreements[milestone.agreementId];
        require(agreement.buyer == msg.sender, "Only buyer");
        require(milestone.status == MilestoneStatus.Completed, "Not completed");
        
        milestone.status = MilestoneStatus.Approved;
        
        // Release payment
        _releasePayment(milestone.agreementId, milestone.amount);
        
        emit MilestoneApproved(milestoneId);
    }
    
    /**
     * @notice Reject milestone (buyer)
     * @param milestoneId Milestone identifier
     * @param reason Rejection reason
     */
    function rejectMilestone(bytes32 milestoneId, string memory reason) external {
        Milestone storage milestone = milestones[milestoneId];
        require(milestone.milestoneId != bytes32(0), "Milestone not found");
        
        ServiceAgreement storage agreement = agreements[milestone.agreementId];
        require(agreement.buyer == msg.sender, "Only buyer");
        require(milestone.status == MilestoneStatus.Completed, "Not completed");
        
        milestone.status = MilestoneStatus.Rejected;
        
        emit MilestoneRejected(milestoneId, reason);
    }
    
    /**
     * @notice Release payment to seller
     * @param agreementId Agreement identifier
     * @param amount Amount to release
     */
    function releasePayment(bytes32 agreementId, uint256 amount) 
        external 
        agreementExists(agreementId)
        onlyBuyer(agreementId)
    {
        _releasePayment(agreementId, amount);
    }
    
    function _releasePayment(bytes32 agreementId, uint256 amount) internal {
        ServiceAgreement storage agreement = agreements[agreementId];
        require(agreement.status == AgreementStatus.Active, "Agreement not active");
        require(amount > 0, "Invalid amount");
        require(agreement.escrowedAmount >= amount, "Insufficient escrow");
        
        // Calculate platform fee
        uint256 fee = (amount * platformFeeRate) / 10000;
        uint256 sellerAmount = amount - fee;
        
        agreement.escrowedAmount -= amount;
        agreement.releasedAmount += amount;
        totalVolume += amount;
        
        // Transfer to seller
        payable(agreement.seller).transfer(sellerAmount);
        
        // Transfer fee to collector
        if (fee > 0) {
            payable(feeCollector).transfer(fee);
        }
        
        // Check if agreement is completed
        if (agreement.releasedAmount >= agreement.totalAmount) {
            agreement.status = AgreementStatus.Completed;
            emit AgreementCompleted(agreementId);
        }
        
        emit PaymentReleased(agreementId, agreement.seller, sellerAmount, fee);
    }
    
    /**
     * @notice Refund buyer
     * @param agreementId Agreement identifier
     * @param amount Amount to refund
     */
    function refundBuyer(bytes32 agreementId, uint256 amount) 
        external 
        agreementExists(agreementId)
    {
        ServiceAgreement storage agreement = agreements[agreementId];
        require(
            msg.sender == agreement.seller || authorizedArbitrators[msg.sender],
            "Not authorized"
        );
        require(agreement.status == AgreementStatus.Active || agreement.status == AgreementStatus.Disputed, "Invalid status");
        require(amount > 0, "Invalid amount");
        require(agreement.escrowedAmount >= amount, "Insufficient escrow");
        
        agreement.escrowedAmount -= amount;
        agreement.refundedAmount += amount;
        
        payable(agreement.buyer).transfer(amount);
        
        emit RefundIssued(agreementId, agreement.buyer, amount);
    }
    
    /**
     * @notice Create a dispute
     * @param agreementId Agreement identifier
     * @param reason Dispute reason
     * @return disputeId The created dispute ID
     */
    function createDispute(bytes32 agreementId, string memory reason) 
        external 
        agreementExists(agreementId)
        returns (bytes32) 
    {
        ServiceAgreement storage agreement = agreements[agreementId];
        require(
            msg.sender == agreement.buyer || msg.sender == agreement.seller,
            "Not authorized"
        );
        require(agreement.status == AgreementStatus.Active, "Agreement not active");
        
        bytes32 disputeId = keccak256(
            abi.encodePacked(
                agreementId,
                msg.sender,
                reason,
                block.timestamp
            )
        );
        
        disputes[disputeId] = Dispute({
            disputeId: disputeId,
            agreementId: agreementId,
            initiator: msg.sender,
            reason: reason,
            createdAt: block.timestamp,
            resolvedAt: 0,
            status: DisputeStatus.Open,
            resolution: DisputeResolution.None,
            resolver: address(0)
        });
        
        agreement.status = AgreementStatus.Disputed;
        
        emit DisputeCreated(disputeId, agreementId, msg.sender);
        return disputeId;
    }
    
    /**
     * @notice Resolve a dispute (arbitrator only)
     * @param disputeId Dispute identifier
     * @param resolution Resolution type
     * @param amount Amount involved in resolution
     */
    function resolveDispute(
        bytes32 disputeId,
        DisputeResolution resolution,
        uint256 amount
    ) external onlyArbitrator {
        Dispute storage dispute = disputes[disputeId];
        require(dispute.disputeId != bytes32(0), "Dispute not found");
        require(dispute.status == DisputeStatus.Open || dispute.status == DisputeStatus.UnderReview, "Invalid status");
        
        ServiceAgreement storage agreement = agreements[dispute.agreementId];
        
        dispute.status = DisputeStatus.Resolved;
        dispute.resolvedAt = block.timestamp;
        dispute.resolution = resolution;
        dispute.resolver = msg.sender;
        
        // Execute resolution
        if (resolution == DisputeResolution.RefundBuyer) {
            _refundBuyerInternal(dispute.agreementId, amount);
        } else if (resolution == DisputeResolution.PaySeller) {
            _releasePayment(dispute.agreementId, amount);
        } else if (resolution == DisputeResolution.PartialRefund) {
            uint256 refundAmount = amount;
            uint256 paymentAmount = agreement.escrowedAmount - refundAmount;
            if (refundAmount > 0) _refundBuyerInternal(dispute.agreementId, refundAmount);
            if (paymentAmount > 0) _releasePayment(dispute.agreementId, paymentAmount);
        }
        
        agreement.status = AgreementStatus.Completed;
        
        emit DisputeResolved(disputeId, resolution);
    }
    
    function _refundBuyerInternal(bytes32 agreementId, uint256 amount) internal {
        ServiceAgreement storage agreement = agreements[agreementId];
        if (amount > agreement.escrowedAmount) {
            amount = agreement.escrowedAmount;
        }
        
        agreement.escrowedAmount -= amount;
        agreement.refundedAmount += amount;
        
        payable(agreement.buyer).transfer(amount);
        
        emit RefundIssued(agreementId, agreement.buyer, amount);
    }
    
    /**
     * @notice Cancel agreement (before activation)
     * @param agreementId Agreement identifier
     */
    function cancelAgreement(bytes32 agreementId) 
        external 
        agreementExists(agreementId)
    {
        ServiceAgreement storage agreement = agreements[agreementId];
        require(
            msg.sender == agreement.buyer || msg.sender == agreement.seller,
            "Not authorized"
        );
        require(agreement.status == AgreementStatus.Pending, "Cannot cancel active agreement");
        
        agreement.status = AgreementStatus.Cancelled;
        
        // Refund any escrowed amount
        if (agreement.escrowedAmount > 0) {
            uint256 refund = agreement.escrowedAmount;
            agreement.escrowedAmount = 0;
            agreement.refundedAmount = refund;
            payable(agreement.buyer).transfer(refund);
        }
        
        emit AgreementCancelled(agreementId);
    }
    
    /**
     * @notice Check and expire agreements past their expiration date
     * @param agreementId Agreement identifier
     */
    function expireAgreement(bytes32 agreementId) external agreementExists(agreementId) {
        ServiceAgreement storage agreement = agreements[agreementId];
        require(block.timestamp >= agreement.expiresAt, "Not expired");
        require(agreement.status == AgreementStatus.Active || agreement.status == AgreementStatus.Pending, "Invalid status");
        
        agreement.status = AgreementStatus.Expired;
        
        // Refund remaining escrow to buyer
        if (agreement.escrowedAmount > 0) {
            uint256 refund = agreement.escrowedAmount;
            agreement.escrowedAmount = 0;
            agreement.refundedAmount += refund;
            payable(agreement.buyer).transfer(refund);
        }
        
        emit AgreementExpired(agreementId);
    }
    
    // ============ Admin Functions ============
    
    function addArbitrator(address arbitrator) external onlyOwner {
        authorizedArbitrators[arbitrator] = true;
    }
    
    function removeArbitrator(address arbitrator) external onlyOwner {
        authorizedArbitrators[arbitrator] = false;
    }
    
    function updatePlatformFee(uint256 newFeeRate) external onlyOwner {
        require(newFeeRate <= 1000, "Fee too high"); // Max 10%
        platformFeeRate = newFeeRate;
    }
    
    function updateFeeCollector(address newCollector) external onlyOwner {
        require(newCollector != address(0), "Invalid address");
        feeCollector = newCollector;
    }
    
    // ============ View Functions ============
    
    function getAgreement(bytes32 agreementId) external view returns (ServiceAgreement memory) {
        return agreements[agreementId];
    }
    
    function getMilestone(bytes32 milestoneId) external view returns (Milestone memory) {
        return milestones[milestoneId];
    }
    
    function getDispute(bytes32 disputeId) external view returns (Dispute memory) {
        return disputes[disputeId];
    }
    
    function getBuyerAgreements(address buyer) external view returns (bytes32[] memory) {
        return buyerAgreements[buyer];
    }
    
    function getSellerAgreements(address seller) external view returns (bytes32[] memory) {
        return sellerAgreements[seller];
    }
    
    function getAgreementMilestones(bytes32 agreementId) external view returns (bytes32[] memory) {
        return agreements[agreementId].milestones;
    }
}
