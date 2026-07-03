// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// bankon_agent_market — the EXPANSION that wires the copied ARC "Agent Reputation
// Collection" contracts (AgentReputationRegistry / AgenticMarketplaceEscrow /
// SubscriptionManager) to the canonical iNFT identity (contracts/inft7857/) and the
// x402 settlement (contracts/x402/X402Receipt.sol). A listed agent is an iNFT
// tokenId; the marketspace UI (packages/web/marketspace.html) and the AgenticPlace
// indexer consume the `AgentListed` event. USDC-denominated (6 decimals).
pragma solidity ^0.8.24;

interface IERC721Min { function ownerOf(uint256 tokenId) external view returns (address); }

interface IAgentReputationMin {
    function getAgentProfile(address agent) external view returns (bytes memory);
}

contract bankon_agent_market {
    error NotTokenOwner();
    error NotListed(uint256 tokenId);
    error ZeroPrice();

    struct Listing {
        address seller;       // iNFT owner at list time
        uint256 priceUsdc6;   // USDC base units (6 dp)
        string  metadataURI;  // agenticplace.pythai.net/marketspace card
        bool    active;
        uint64  listedAt;
    }

    IERC721Min public immutable inft;            // bankon_inft_subname
    address public immutable reputationRegistry; // AgentReputationRegistry (optional reads)
    address public immutable escrow;             // AgenticMarketplaceEscrow (milestone deals)
    address public immutable x402Attestor;       // X402Receipt (settlement proof, optional)

    mapping(uint256 => Listing) public listings;

    event AgentListed(uint256 indexed tokenId, address indexed seller, uint256 priceUsdc6, string metadataURI);
    event AgentUnlisted(uint256 indexed tokenId, address indexed seller);
    event AgentRepriced(uint256 indexed tokenId, uint256 oldPrice, uint256 newPrice);

    constructor(address inft_, address reputationRegistry_, address escrow_, address x402Attestor_) {
        inft = IERC721Min(inft_);
        reputationRegistry = reputationRegistry_;
        escrow = escrow_;
        x402Attestor = x402Attestor_;
    }

    modifier onlyTokenOwner(uint256 tokenId) {
        if (inft.ownerOf(tokenId) != msg.sender) revert NotTokenOwner();
        _;
    }

    /// @notice List an agent iNFT on the BANKON / AgenticPlace marketspace.
    function listAgent(uint256 tokenId, uint256 priceUsdc6, string calldata metadataURI)
        external onlyTokenOwner(tokenId)
    {
        if (priceUsdc6 == 0) revert ZeroPrice();
        listings[tokenId] = Listing({
            seller: msg.sender, priceUsdc6: priceUsdc6, metadataURI: metadataURI,
            active: true, listedAt: uint64(block.timestamp)
        });
        emit AgentListed(tokenId, msg.sender, priceUsdc6, metadataURI);
    }

    function reprice(uint256 tokenId, uint256 newPriceUsdc6) external onlyTokenOwner(tokenId) {
        Listing storage l = listings[tokenId];
        if (!l.active) revert NotListed(tokenId);
        if (newPriceUsdc6 == 0) revert ZeroPrice();
        emit AgentRepriced(tokenId, l.priceUsdc6, newPriceUsdc6);
        l.priceUsdc6 = newPriceUsdc6;
    }

    function unlistAgent(uint256 tokenId) external onlyTokenOwner(tokenId) {
        Listing storage l = listings[tokenId];
        if (!l.active) revert NotListed(tokenId);
        l.active = false;
        emit AgentUnlisted(tokenId, msg.sender);
    }

    function listingOf(uint256 tokenId) external view returns (Listing memory) { return listings[tokenId]; }
}
