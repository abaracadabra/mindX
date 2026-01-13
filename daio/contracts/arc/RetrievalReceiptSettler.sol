// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title RetrievalReceiptSettler
 * @notice Batch settlement of retrieval payments
 * @dev Part of THOT-DAIO architecture for dataset marketplace
 */
contract RetrievalReceiptSettler {
    struct RetrievalReceipt {
        bytes32 receiptId;
        bytes32 rootCID;
        address provider;
        address buyer;
        uint256 bytesServed;
        uint256 pricePerMB;
        uint256 timestamp;
        bytes signature;            // Provider signature
        bool settled;
    }
    
    mapping(bytes32 => RetrievalReceipt) public receipts;
    mapping(address => bytes32[]) public providerReceipts;
    mapping(address => bytes32[]) public buyerReceipts;
    
    address public owner;
    uint256 public totalReceipts;
    uint256 public totalSettled;
    
    event ReceiptCreated(bytes32 indexed receiptId, bytes32 rootCID, address provider, address buyer, uint256 bytesServed);
    event ReceiptSettled(bytes32 indexed receiptId, uint256 amount);
    event ReceiptsBatchSettled(bytes32[] receiptIds, uint256 totalAmount);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @notice Create a retrieval receipt
     * @param rootCID Dataset root CID
     * @param provider Provider address
     * @param bytesServed Bytes served
     * @param pricePerMB Price per MB
     * @param signature Provider signature
     * @return receiptId The created receipt ID
     */
    function createReceipt(
        bytes32 rootCID,
        address provider,
        uint256 bytesServed,
        uint256 pricePerMB,
        bytes memory signature
    ) external returns (bytes32) {
        require(rootCID != bytes32(0), "Invalid CID");
        require(provider != address(0), "Invalid provider");
        require(bytesServed > 0, "Invalid bytes");
        require(pricePerMB > 0, "Invalid price");
        
        bytes32 receiptId = keccak256(abi.encodePacked(rootCID, provider, msg.sender, block.timestamp, block.number));
        
        receipts[receiptId] = RetrievalReceipt({
            receiptId: receiptId,
            rootCID: rootCID,
            provider: provider,
            buyer: msg.sender,
            bytesServed: bytesServed,
            pricePerMB: pricePerMB,
            timestamp: block.timestamp,
            signature: signature,
            settled: false
        });
        
        providerReceipts[provider].push(receiptId);
        buyerReceipts[msg.sender].push(receiptId);
        totalReceipts++;
        
        emit ReceiptCreated(receiptId, rootCID, provider, msg.sender, bytesServed);
        return receiptId;
    }
    
    /**
     * @notice Settle a single receipt
     * @param receiptId Receipt identifier
     */
    function settleReceipt(bytes32 receiptId) external payable {
        RetrievalReceipt storage receipt = receipts[receiptId];
        require(!receipt.settled, "Already settled");
        require(receipt.buyer == msg.sender, "Only buyer can settle");
        
        uint256 amount = (receipt.bytesServed * receipt.pricePerMB) / (1024 * 1024);  // Convert bytes to MB
        require(msg.value >= amount, "Insufficient payment");
        
        receipt.settled = true;
        totalSettled++;
        
        // Transfer payment to provider
        payable(receipt.provider).transfer(amount);
        
        // Refund excess if any
        if (msg.value > amount) {
            payable(msg.sender).transfer(msg.value - amount);
        }
        
        emit ReceiptSettled(receiptId, amount);
    }
    
    /**
     * @notice Batch settle multiple receipts
     * @param receiptIds Array of receipt IDs
     */
    function batchSettleReceipts(bytes32[] memory receiptIds) external payable {
        uint256 totalAmount = 0;
        
        // Calculate total amount
        for (uint256 i = 0; i < receiptIds.length; i++) {
            RetrievalReceipt storage receipt = receipts[receiptIds[i]];
            require(!receipt.settled, "Receipt already settled");
            require(receipt.buyer == msg.sender, "Not authorized");
            
            uint256 amount = (receipt.bytesServed * receipt.pricePerMB) / (1024 * 1024);
            totalAmount += amount;
        }
        
        require(msg.value >= totalAmount, "Insufficient payment");
        
        // Settle all receipts
        for (uint256 i = 0; i < receiptIds.length; i++) {
            RetrievalReceipt storage receipt = receipts[receiptIds[i]];
            uint256 amount = (receipt.bytesServed * receipt.pricePerMB) / (1024 * 1024);
            
            receipt.settled = true;
            totalSettled++;
            
            // Transfer payment to provider
            payable(receipt.provider).transfer(amount);
        }
        
        // Refund excess if any
        if (msg.value > totalAmount) {
            payable(msg.sender).transfer(msg.value - totalAmount);
        }
        
        emit ReceiptsBatchSettled(receiptIds, totalAmount);
    }
    
    /**
     * @notice Get receipts for a provider
     * @param provider Provider address
     * @return receiptIds Array of receipt IDs
     */
    function getProviderReceipts(address provider) external view returns (bytes32[] memory) {
        return providerReceipts[provider];
    }
    
    /**
     * @notice Get receipts for a buyer
     * @param buyer Buyer address
     * @return receiptIds Array of receipt IDs
     */
    function getBuyerReceipts(address buyer) external view returns (bytes32[] memory) {
        return buyerReceipts[buyer];
    }
}
