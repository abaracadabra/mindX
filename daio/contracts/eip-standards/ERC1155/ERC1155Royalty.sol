// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title ERC1155Royalty
 * @notice ERC1155 implementation with ERC2981 royalty standard support for multi-tokens
 * @dev Implements per-token royalty configuration and collaborative royalty splits
 */
contract ERC1155Royalty is ERC1155, ERC2981, AccessControl, ReentrancyGuard {

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant ROYALTY_MANAGER_ROLE = keccak256("ROYALTY_MANAGER_ROLE");

    // Per-token royalty configuration
    struct TokenRoyalty {
        address recipient;
        uint96 feeNumerator;
        bool hasCustomRoyalty;
    }

    mapping(uint256 => TokenRoyalty) private _tokenRoyalties;

    // Royalty splits for collaborative works
    struct RoyaltySplit {
        address recipient;
        uint96 percentage; // Basis points
    }

    mapping(uint256 => RoyaltySplit[]) private _tokenRoyaltySplits;

    // Token creation and metadata
    mapping(uint256 => bool) private _tokenExists;
    mapping(uint256 => string) private _tokenURIs;
    mapping(uint256 => string) private _tokenNames;
    mapping(uint256 => address) private _tokenCreators;
    mapping(uint256 => uint256) private _tokenSupplies;
    mapping(uint256 => uint256) private _tokenMaxSupplies;

    // Collection information
    string private _contractURI;
    string private _name;
    string private _symbol;
    uint256 private _nextTokenId = 1;

    // Default royalty configuration
    address private _defaultRoyaltyRecipient;
    uint96 private _defaultRoyaltyFee;

    // Events
    event TokenCreated(
        uint256 indexed tokenId,
        address indexed creator,
        string name,
        uint256 maxSupply,
        address royaltyRecipient,
        uint96 royaltyFee
    );
    event DefaultRoyaltySet(address indexed recipient, uint96 feeNumerator);
    event TokenRoyaltySet(uint256 indexed tokenId, address indexed recipient, uint96 feeNumerator);
    event RoyaltySplitsSet(uint256 indexed tokenId, RoyaltySplit[] splits);
    event RoyaltyPayment(uint256 indexed tokenId, address indexed recipient, uint256 amount);
    event ContractURIUpdated(string contractURI);

    /**
     * @notice Initialize ERC1155 with royalty support
     * @param uri Base URI for tokens
     * @param name_ Collection name
     * @param symbol_ Collection symbol
     * @param defaultRecipient Default royalty recipient
     * @param defaultFeeNumerator Default royalty fee in basis points
     * @param admin Admin address
     */
    constructor(
        string memory uri,
        string memory name_,
        string memory symbol_,
        address defaultRecipient,
        uint96 defaultFeeNumerator,
        address admin
    ) ERC1155(uri) {
        require(admin != address(0), "Admin cannot be zero address");
        require(defaultRecipient != address(0), "Default recipient cannot be zero address");
        require(defaultFeeNumerator <= 1000, "Royalty fee too high"); // Max 10%

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(ROYALTY_MANAGER_ROLE, admin);

        _name = name_;
        _symbol = symbol_;
        _defaultRoyaltyRecipient = defaultRecipient;
        _defaultRoyaltyFee = defaultFeeNumerator;
        _setDefaultRoyalty(defaultRecipient, defaultFeeNumerator);

        emit DefaultRoyaltySet(defaultRecipient, defaultFeeNumerator);
    }

    /**
     * @notice Create a new token with royalty configuration
     * @param creator Token creator
     * @param name Token name
     * @param maxSupply Maximum supply (0 = unlimited)
     * @param royaltyRecipient Royalty recipient (use address(0) for default)
     * @param royaltyFee Royalty fee in basis points
     */
    function createToken(
        address creator,
        string memory name,
        uint256 maxSupply,
        address royaltyRecipient,
        uint96 royaltyFee
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(creator != address(0), "Creator cannot be zero address");
        require(bytes(name).length > 0, "Name cannot be empty");

        if (royaltyRecipient != address(0)) {
            require(royaltyFee <= 1000, "Royalty fee too high"); // Max 10%
        }

        uint256 tokenId = _nextTokenId++;
        _tokenExists[tokenId] = true;
        _tokenNames[tokenId] = name;
        _tokenCreators[tokenId] = creator;
        _tokenMaxSupplies[tokenId] = maxSupply;

        // Set custom royalty if specified
        if (royaltyRecipient != address(0)) {
            _tokenRoyalties[tokenId] = TokenRoyalty({
                recipient: royaltyRecipient,
                feeNumerator: royaltyFee,
                hasCustomRoyalty: true
            });
            _setTokenRoyalty(tokenId, royaltyRecipient, royaltyFee);
        }

        emit TokenCreated(tokenId, creator, name, maxSupply, royaltyRecipient, royaltyFee);
        return tokenId;
    }

    /**
     * @notice Create token with royalty splits for collaborative works
     * @param creator Token creator
     * @param name Token name
     * @param maxSupply Maximum supply
     * @param splits Array of royalty splits
     */
    function createTokenWithSplits(
        address creator,
        string memory name,
        uint256 maxSupply,
        RoyaltySplit[] calldata splits
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(creator != address(0), "Creator cannot be zero address");
        require(bytes(name).length > 0, "Name cannot be empty");
        require(splits.length > 0, "Must have at least one split");

        uint256 totalPercentage = 0;
        for (uint256 i = 0; i < splits.length; i++) {
            require(splits[i].recipient != address(0), "Split recipient cannot be zero");
            require(splits[i].percentage > 0, "Split percentage must be greater than 0");
            totalPercentage += splits[i].percentage;
        }
        require(totalPercentage <= 1000, "Total splits exceed 10%");

        uint256 tokenId = _nextTokenId++;
        _tokenExists[tokenId] = true;
        _tokenNames[tokenId] = name;
        _tokenCreators[tokenId] = creator;
        _tokenMaxSupplies[tokenId] = maxSupply;

        // Store royalty splits
        for (uint256 i = 0; i < splits.length; i++) {
            _tokenRoyaltySplits[tokenId].push(splits[i]);
        }

        emit TokenCreated(tokenId, creator, name, maxSupply, address(0), 0);
        emit RoyaltySplitsSet(tokenId, splits);
        return tokenId;
    }

    /**
     * @notice Mint tokens
     * @param to Address to mint to
     * @param tokenId Token ID
     * @param amount Amount to mint
     * @param data Additional data
     */
    function mint(
        address to,
        uint256 tokenId,
        uint256 amount,
        bytes memory data
    ) public onlyRole(MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");
        require(_tokenExists[tokenId], "Token does not exist");
        require(amount > 0, "Amount must be greater than 0");

        uint256 maxSupply = _tokenMaxSupplies[tokenId];
        if (maxSupply > 0) {
            require(_tokenSupplies[tokenId] + amount <= maxSupply, "Exceeds maximum supply");
        }

        _tokenSupplies[tokenId] += amount;
        _mint(to, tokenId, amount, data);
    }

    /**
     * @notice Batch mint tokens
     * @param to Address to mint to
     * @param tokenIds Array of token IDs
     * @param amounts Array of amounts
     * @param data Additional data
     */
    function mintBatch(
        address to,
        uint256[] memory tokenIds,
        uint256[] memory amounts,
        bytes memory data
    ) public onlyRole(MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");
        require(tokenIds.length == amounts.length, "Arrays length mismatch");

        for (uint256 i = 0; i < tokenIds.length; i++) {
            require(_tokenExists[tokenIds[i]], "Token does not exist");
            require(amounts[i] > 0, "Amount must be greater than 0");

            uint256 maxSupply = _tokenMaxSupplies[tokenIds[i]];
            if (maxSupply > 0) {
                require(
                    _tokenSupplies[tokenIds[i]] + amounts[i] <= maxSupply,
                    "Exceeds maximum supply"
                );
            }
            _tokenSupplies[tokenIds[i]] += amounts[i];
        }

        _mintBatch(to, tokenIds, amounts, data);
    }

    /**
     * @notice Update default royalty
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
        require(_tokenExists[tokenId], "Token does not exist");
        require(recipient != address(0), "Recipient cannot be zero address");
        require(feeNumerator <= 1000, "Royalty fee too high"); // Max 10%

        _tokenRoyalties[tokenId] = TokenRoyalty({
            recipient: recipient,
            feeNumerator: feeNumerator,
            hasCustomRoyalty: true
        });
        _setTokenRoyalty(tokenId, recipient, feeNumerator);

        // Clear any existing splits
        delete _tokenRoyaltySplits[tokenId];

        emit TokenRoyaltySet(tokenId, recipient, feeNumerator);
    }

    /**
     * @notice Set token URI
     * @param tokenId Token ID
     * @param tokenURI New token URI
     */
    function setTokenURI(uint256 tokenId, string memory tokenURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_tokenExists[tokenId], "Token does not exist");
        _tokenURIs[tokenId] = tokenURI;
    }

    /**
     * @notice Set contract URI
     * @param contractURI_ New contract URI
     */
    function setContractURI(string memory contractURI_) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _contractURI = contractURI_;
        emit ContractURIUpdated(contractURI_);
    }

    /**
     * @notice Distribute royalty payments for splits
     * @param tokenId Token ID
     * @param salePrice Sale price to calculate royalty from
     */
    function distributeRoyalty(uint256 tokenId, uint256 salePrice) external payable nonReentrant {
        require(_tokenExists[tokenId], "Token does not exist");
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
     * @notice Get token URI
     * @param tokenId Token ID
     * @return Token URI
     */
    function uri(uint256 tokenId) public view override returns (string memory) {
        require(_tokenExists[tokenId], "Token does not exist");

        string memory tokenURI = _tokenURIs[tokenId];
        if (bytes(tokenURI).length > 0) {
            return tokenURI;
        }

        return super.uri(tokenId);
    }

    /**
     * @notice Get contract URI
     * @return Contract URI
     */
    function contractURI() public view returns (string memory) {
        return _contractURI;
    }

    /**
     * @notice Get collection name
     * @return Collection name
     */
    function name() public view returns (string memory) {
        return _name;
    }

    /**
     * @notice Get collection symbol
     * @return Collection symbol
     */
    function symbol() public view returns (string memory) {
        return _symbol;
    }

    /**
     * @notice Get token name
     * @param tokenId Token ID
     * @return Token name
     */
    function tokenName(uint256 tokenId) public view returns (string memory) {
        require(_tokenExists[tokenId], "Token does not exist");
        return _tokenNames[tokenId];
    }

    /**
     * @notice Get token creator
     * @param tokenId Token ID
     * @return Token creator
     */
    function tokenCreator(uint256 tokenId) public view returns (address) {
        require(_tokenExists[tokenId], "Token does not exist");
        return _tokenCreators[tokenId];
    }

    /**
     * @notice Get token supply
     * @param tokenId Token ID
     * @return Current supply
     */
    function tokenSupply(uint256 tokenId) public view returns (uint256) {
        return _tokenSupplies[tokenId];
    }

    /**
     * @notice Get token max supply
     * @param tokenId Token ID
     * @return Maximum supply
     */
    function tokenMaxSupply(uint256 tokenId) public view returns (uint256) {
        return _tokenMaxSupplies[tokenId];
    }

    /**
     * @notice Check if token exists
     * @param tokenId Token ID
     * @return Whether token exists
     */
    function tokenExists(uint256 tokenId) public view returns (bool) {
        return _tokenExists[tokenId];
    }

    /**
     * @notice Get token royalty information
     * @param tokenId Token ID
     * @return recipient Royalty recipient
     * @return fee Royalty fee in basis points
     * @return hasCustom Whether token has custom royalty
     */
    function getTokenRoyalty(uint256 tokenId) external view returns (
        address recipient,
        uint96 fee,
        bool hasCustom
    ) {
        TokenRoyalty memory royalty = _tokenRoyalties[tokenId];
        return (royalty.recipient, royalty.feeNumerator, royalty.hasCustomRoyalty);
    }

    /**
     * @notice Get token royalty splits
     * @param tokenId Token ID
     * @return splits Array of royalty splits
     */
    function getTokenRoyaltySplits(uint256 tokenId) external view returns (RoyaltySplit[] memory splits) {
        return _tokenRoyaltySplits[tokenId];
    }

    /**
     * @notice Check if token has royalty splits
     * @param tokenId Token ID
     * @return Whether token has royalty splits
     */
    function hasRoyaltySplits(uint256 tokenId) external view returns (bool) {
        return _tokenRoyaltySplits[tokenId].length > 0;
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
     * @notice Get next token ID
     * @return Next token ID
     */
    function nextTokenId() public view returns (uint256) {
        return _nextTokenId;
    }

    // Required overrides

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC1155, ERC2981, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}