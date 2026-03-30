// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title ERC721Royalty
 * @notice ERC721 implementation with ERC2981 royalty standard support
 * @dev Implements on-chain royalty information that can be queried by anyone
 */
contract ERC721Royalty is ERC721, ERC2981, AccessControl, ReentrancyGuard {

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant ROYALTY_MANAGER_ROLE = keccak256("ROYALTY_MANAGER_ROLE");

    // Default royalty configuration
    address private _defaultRoyaltyRecipient;
    uint96 private _defaultRoyaltyFee; // In basis points (e.g., 250 = 2.5%)

    // Per-token royalty overrides
    mapping(uint256 => address) private _tokenRoyaltyRecipients;
    mapping(uint256 => uint96) private _tokenRoyaltyFees;

    // Collection information
    string private _contractURI;
    uint256 private _nextTokenId = 1;

    // Royalty splits for collaborative works
    struct RoyaltySplit {
        address recipient;
        uint96 percentage; // Basis points
    }

    mapping(uint256 => RoyaltySplit[]) private _tokenRoyaltySplits;

    // Events
    event DefaultRoyaltySet(address indexed recipient, uint96 feeNumerator);
    event TokenRoyaltySet(uint256 indexed tokenId, address indexed recipient, uint96 feeNumerator);
    event RoyaltySplitsSet(uint256 indexed tokenId, RoyaltySplit[] splits);
    event RoyaltyPayment(uint256 indexed tokenId, address indexed recipient, uint256 amount);
    event ContractURIUpdated(string contractURI);

    /**
     * @notice Initialize ERC721 with royalty support
     * @param name Token name
     * @param symbol Token symbol
     * @param defaultRecipient Default royalty recipient
     * @param defaultFeeNumerator Default royalty fee in basis points
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        address defaultRecipient,
        uint96 defaultFeeNumerator,
        address admin
    ) ERC721(name, symbol) {
        require(admin != address(0), "Admin cannot be zero address");
        require(defaultRecipient != address(0), "Default recipient cannot be zero address");
        require(defaultFeeNumerator <= 1000, "Royalty fee too high"); // Max 10%

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(ROYALTY_MANAGER_ROLE, admin);

        _defaultRoyaltyRecipient = defaultRecipient;
        _defaultRoyaltyFee = defaultFeeNumerator;
        _setDefaultRoyalty(defaultRecipient, defaultFeeNumerator);

        emit DefaultRoyaltySet(defaultRecipient, defaultFeeNumerator);
    }

    /**
     * @notice Mint token with optional custom royalty
     * @param to Address to mint to
     * @param royaltyRecipient Optional custom royalty recipient (use address(0) for default)
     * @param royaltyFee Optional custom royalty fee in basis points
     */
    function mint(
        address to,
        address royaltyRecipient,
        uint96 royaltyFee
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(to != address(0), "Cannot mint to zero address");

        uint256 tokenId = _nextTokenId++;
        _safeMint(to, tokenId);

        // Set custom royalty if specified
        if (royaltyRecipient != address(0)) {
            require(royaltyFee <= 1000, "Royalty fee too high"); // Max 10%
            _setTokenRoyalty(tokenId, royaltyRecipient, royaltyFee);
            _tokenRoyaltyRecipients[tokenId] = royaltyRecipient;
            _tokenRoyaltyFees[tokenId] = royaltyFee;
            emit TokenRoyaltySet(tokenId, royaltyRecipient, royaltyFee);
        }

        return tokenId;
    }

    /**
     * @notice Mint token with royalty splits for collaborative works
     * @param to Address to mint to
     * @param splits Array of royalty splits
     */
    function mintWithSplits(
        address to,
        RoyaltySplit[] calldata splits
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(to != address(0), "Cannot mint to zero address");
        require(splits.length > 0, "Must have at least one split");

        uint256 totalPercentage = 0;
        for (uint256 i = 0; i < splits.length; i++) {
            require(splits[i].recipient != address(0), "Split recipient cannot be zero");
            require(splits[i].percentage > 0, "Split percentage must be greater than 0");
            totalPercentage += splits[i].percentage;
        }
        require(totalPercentage <= 1000, "Total splits exceed 10%");

        uint256 tokenId = _nextTokenId++;
        _safeMint(to, tokenId);

        // Store royalty splits
        for (uint256 i = 0; i < splits.length; i++) {
            _tokenRoyaltySplits[tokenId].push(splits[i]);
        }

        emit RoyaltySplitsSet(tokenId, splits);
        return tokenId;
    }

    /**
     * @notice Update default royalty for all new tokens
     * @param recipient New default royalty recipient
     * @param feeNumerator New default royalty fee in basis points
     */
    function setDefaultRoyalty(
        address recipient,
        uint96 feeNumerator
    ) external onlyRole(ROYALTY_MANAGER_ROLE) {
        require(recipient != address(0), "Recipient cannot be zero address");
        require(feeNumerator <= 1000, "Royalty fee too high"); // Max 10%

        _defaultRoyaltyRecipient = recipient;
        _defaultRoyaltyFee = feeNumerator;
        _setDefaultRoyalty(recipient, feeNumerator);

        emit DefaultRoyaltySet(recipient, feeNumerator);
    }

    /**
     * @notice Update royalty for specific token
     * @param tokenId Token ID
     * @param recipient Royalty recipient
     * @param feeNumerator Royalty fee in basis points
     */
    function setTokenRoyalty(
        uint256 tokenId,
        address recipient,
        uint96 feeNumerator
    ) external onlyRole(ROYALTY_MANAGER_ROLE) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(recipient != address(0), "Recipient cannot be zero address");
        require(feeNumerator <= 1000, "Royalty fee too high"); // Max 10%

        _setTokenRoyalty(tokenId, recipient, feeNumerator);
        _tokenRoyaltyRecipients[tokenId] = recipient;
        _tokenRoyaltyFees[tokenId] = feeNumerator;

        // Clear any existing splits
        delete _tokenRoyaltySplits[tokenId];

        emit TokenRoyaltySet(tokenId, recipient, feeNumerator);
    }

    /**
     * @notice Set contract URI for marketplace metadata
     * @param contractURI_ New contract URI
     */
    function setContractURI(string memory contractURI_) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _contractURI = contractURI_;
        emit ContractURIUpdated(contractURI_);
    }

    /**
     * @notice Get contract URI for marketplace metadata
     * @return Contract URI
     */
    function contractURI() public view returns (string memory) {
        return _contractURI;
    }

    /**
     * @notice Get default royalty information
     * @return recipient Default royalty recipient
     * @return fee Default royalty fee in basis points
     */
    function getDefaultRoyalty() external view returns (address recipient, uint96 fee) {
        return (_defaultRoyaltyRecipient, _defaultRoyaltyFee);
    }

    /**
     * @notice Get token-specific royalty information
     * @param tokenId Token ID
     * @return recipient Token royalty recipient (address(0) if using default)
     * @return fee Token royalty fee in basis points (0 if using default)
     */
    function getTokenRoyalty(uint256 tokenId) external view returns (address recipient, uint96 fee) {
        return (_tokenRoyaltyRecipients[tokenId], _tokenRoyaltyFees[tokenId]);
    }

    /**
     * @notice Get royalty splits for a token
     * @param tokenId Token ID
     * @return splits Array of royalty splits
     */
    function getTokenRoyaltySplits(uint256 tokenId) external view returns (RoyaltySplit[] memory splits) {
        return _tokenRoyaltySplits[tokenId];
    }

    /**
     * @notice Calculate and distribute royalty payments for splits
     * @param tokenId Token ID
     * @param salePrice Sale price to calculate royalty from
     */
    function distributeRoyalty(uint256 tokenId, uint256 salePrice) external payable nonReentrant {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(msg.value >= salePrice, "Insufficient payment");

        RoyaltySplit[] memory splits = _tokenRoyaltySplits[tokenId];
        require(splits.length > 0, "No splits configured for this token");

        uint256 totalDistributed = 0;

        for (uint256 i = 0; i < splits.length; i++) {
            uint256 royaltyAmount = (salePrice * splits[i].percentage) / 10000;

            if (royaltyAmount > 0) {
                payable(splits[i].recipient).transfer(royaltyAmount);
                totalDistributed += royaltyAmount;
                emit RoyaltyPayment(tokenId, splits[i].recipient, royaltyAmount);
            }
        }

        // Refund excess payment
        if (msg.value > totalDistributed) {
            payable(msg.sender).transfer(msg.value - totalDistributed);
        }
    }

    /**
     * @notice Check if token uses royalty splits
     * @param tokenId Token ID
     * @return Whether token has royalty splits configured
     */
    function hasRoyaltySplits(uint256 tokenId) external view returns (bool) {
        return _tokenRoyaltySplits[tokenId].length > 0;
    }

    /**
     * @notice Get next token ID to be minted
     * @return Next token ID
     */
    function nextTokenId() public view returns (uint256) {
        return _nextTokenId;
    }

    /**
     * @notice Batch mint tokens with same royalty settings
     * @param recipients Array of addresses to mint to
     * @param royaltyRecipient Royalty recipient (use address(0) for default)
     * @param royaltyFee Royalty fee in basis points
     */
    function batchMint(
        address[] calldata recipients,
        address royaltyRecipient,
        uint96 royaltyFee
    ) external onlyRole(MINTER_ROLE) {
        require(recipients.length > 0 && recipients.length <= 50, "Invalid batch size");

        if (royaltyRecipient != address(0)) {
            require(royaltyFee <= 1000, "Royalty fee too high");
        }

        for (uint256 i = 0; i < recipients.length; i++) {
            require(recipients[i] != address(0), "Cannot mint to zero address");

            uint256 tokenId = _nextTokenId++;
            _safeMint(recipients[i], tokenId);

            if (royaltyRecipient != address(0)) {
                _setTokenRoyalty(tokenId, royaltyRecipient, royaltyFee);
                _tokenRoyaltyRecipients[tokenId] = royaltyRecipient;
                _tokenRoyaltyFees[tokenId] = royaltyFee;
                emit TokenRoyaltySet(tokenId, royaltyRecipient, royaltyFee);
            }
        }
    }

    // Required overrides

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721, ERC2981, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}