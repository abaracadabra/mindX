// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Consecutive.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title ERC721ConsecutiveToken
 * @notice ERC721 implementation with ERC2309 consecutive minting for gas efficiency
 * @dev Uses ERC2309 ConsecutiveTransfer event for batch minting optimization
 */
contract ERC721ConsecutiveToken is ERC721, ERC721Consecutive, AccessControl, ReentrancyGuard {

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BATCH_MINTER_ROLE = keccak256("BATCH_MINTER_ROLE");

    // Metadata
    string private _baseTokenURI;
    string private _contractURI;

    // Supply tracking
    uint256 private _maxSupply;
    bool private _hasMaxSupply;

    // Batch minting configuration
    struct BatchConfig {
        uint256 maxBatchSize;       // Maximum tokens per batch mint
        uint256 batchPrice;         // Price per batch
        bool batchSaleActive;       // Whether batch sale is active
        uint256 minBatchSize;       // Minimum tokens per batch
    }

    BatchConfig public batchConfig;

    // Batch tracking
    mapping(uint256 => uint256) private _batchStartIds; // batchId => startTokenId
    mapping(uint256 => uint256) private _batchSizes;    // batchId => size
    mapping(uint256 => address) private _batchMinters;  // batchId => minter
    uint256 private _nextBatchId = 1;

    // Events
    event BatchConfigUpdated(
        uint256 maxBatchSize,
        uint256 batchPrice,
        bool batchSaleActive,
        uint256 minBatchSize
    );
    event BatchMinted(
        uint256 indexed batchId,
        address indexed to,
        uint256 startTokenId,
        uint256 quantity
    );
    event MaxSupplySet(uint256 maxSupply);
    event BaseURIUpdated(string baseURI);

    /**
     * @notice Initialize ERC721 with consecutive minting support
     * @param name Token name
     * @param symbol Token symbol
     * @param baseURI Base URI for metadata
     * @param maxSupply Maximum token supply (0 = no limit)
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        string memory baseURI,
        uint256 maxSupply,
        address admin
    ) ERC721(name, symbol) {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(BATCH_MINTER_ROLE, admin);

        _baseTokenURI = baseURI;

        if (maxSupply > 0) {
            _maxSupply = maxSupply;
            _hasMaxSupply = true;
            emit MaxSupplySet(maxSupply);
        }

        // Initialize batch configuration
        batchConfig = BatchConfig({
            maxBatchSize: 100,
            batchPrice: 0.1 ether,
            batchSaleActive: false,
            minBatchSize: 10
        });
    }

    /**
     * @notice Mint consecutive tokens in a batch (gas optimized)
     * @param to Address to mint to
     * @param quantity Number of tokens to mint consecutively
     */
    function batchMint(address to, uint96 quantity) public onlyRole(BATCH_MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");
        require(quantity > 0, "Quantity must be greater than 0");
        require(quantity <= batchConfig.maxBatchSize, "Exceeds max batch size");

        if (_hasMaxSupply) {
            require(_totalConsecutiveSupply() + quantity <= _maxSupply, "Exceeds maximum supply");
        }

        uint256 batchId = _nextBatchId++;
        uint256 startTokenId = _nextConsecutiveId();

        // Store batch information
        _batchStartIds[batchId] = startTokenId;
        _batchSizes[batchId] = quantity;
        _batchMinters[batchId] = to;

        // Use consecutive minting for gas efficiency
        _mintConsecutive(to, quantity);

        emit BatchMinted(batchId, to, startTokenId, quantity);
    }

    /**
     * @notice Public batch mint function
     * @param quantity Number of tokens to mint in batch
     */
    function publicBatchMint(uint96 quantity) external payable nonReentrant {
        require(batchConfig.batchSaleActive, "Batch sale not active");
        require(quantity >= batchConfig.minBatchSize, "Below minimum batch size");
        require(quantity <= batchConfig.maxBatchSize, "Exceeds maximum batch size");

        if (_hasMaxSupply) {
            require(_totalConsecutiveSupply() + quantity <= _maxSupply, "Exceeds maximum supply");
        }

        uint256 totalPrice = (batchConfig.batchPrice * quantity) / batchConfig.maxBatchSize;
        require(msg.value >= totalPrice, "Insufficient payment");

        uint256 batchId = _nextBatchId++;
        uint256 startTokenId = _nextConsecutiveId();

        // Store batch information
        _batchStartIds[batchId] = startTokenId;
        _batchSizes[batchId] = quantity;
        _batchMinters[batchId] = msg.sender;

        // Use consecutive minting for gas efficiency
        _mintConsecutive(msg.sender, quantity);

        emit BatchMinted(batchId, msg.sender, startTokenId, quantity);

        // Refund excess payment
        if (msg.value > totalPrice) {
            payable(msg.sender).transfer(msg.value - totalPrice);
        }
    }

    /**
     * @notice Mint single token (standard ERC721)
     * @param to Address to mint to
     */
    function mint(address to) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(to != address(0), "Cannot mint to zero address");

        if (_hasMaxSupply) {
            require(totalSupply() < _maxSupply, "Exceeds maximum supply");
        }

        uint256 tokenId = _nextTokenId();
        _mint(to, tokenId);

        return tokenId;
    }

    /**
     * @notice Configure batch minting parameters
     * @param maxBatchSize Maximum tokens per batch
     * @param batchPrice Price per batch
     * @param batchSaleActive Whether batch sale is active
     * @param minBatchSize Minimum tokens per batch
     */
    function setBatchConfig(
        uint256 maxBatchSize,
        uint256 batchPrice,
        bool batchSaleActive,
        uint256 minBatchSize
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(maxBatchSize > 0 && maxBatchSize <= 1000, "Invalid max batch size");
        require(minBatchSize > 0 && minBatchSize <= maxBatchSize, "Invalid min batch size");

        batchConfig = BatchConfig({
            maxBatchSize: maxBatchSize,
            batchPrice: batchPrice,
            batchSaleActive: batchSaleActive,
            minBatchSize: minBatchSize
        });

        emit BatchConfigUpdated(maxBatchSize, batchPrice, batchSaleActive, minBatchSize);
    }

    /**
     * @notice Set base URI for metadata
     * @param baseURI New base URI
     */
    function setBaseURI(string memory baseURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _baseTokenURI = baseURI;
        emit BaseURIUpdated(baseURI);
    }

    /**
     * @notice Get batch information
     * @param batchId Batch ID
     * @return startTokenId First token ID in batch
     * @return size Number of tokens in batch
     * @return minter Address that minted the batch
     */
    function getBatchInfo(uint256 batchId) external view returns (
        uint256 startTokenId,
        uint256 size,
        address minter
    ) {
        return (_batchStartIds[batchId], _batchSizes[batchId], _batchMinters[batchId]);
    }

    /**
     * @notice Check if a token is part of a consecutive batch
     * @param tokenId Token ID to check
     * @return Whether token is from consecutive minting
     */
    function isConsecutiveToken(uint256 tokenId) external view returns (bool) {
        return _exists(tokenId) && tokenId < _nextConsecutiveId();
    }

    /**
     * @notice Get total supply including consecutive tokens
     * @return Total number of tokens minted
     */
    function totalSupply() public view returns (uint256) {
        return _totalConsecutiveSupply() + _totalMinted() - _totalConsecutiveSupply();
    }

    /**
     * @notice Get maximum supply
     * @return Maximum supply (0 if unlimited)
     */
    function maxSupply() public view returns (uint256) {
        return _hasMaxSupply ? _maxSupply : 0;
    }

    /**
     * @notice Check if token has maximum supply limit
     * @return Whether token has supply limit
     */
    function hasMaxSupply() public view returns (bool) {
        return _hasMaxSupply;
    }

    /**
     * @notice Get next token ID for single minting
     * @return Next token ID
     */
    function nextTokenId() public view returns (uint256) {
        return _nextTokenId();
    }

    /**
     * @notice Get next consecutive starting ID
     * @return Next consecutive start ID
     */
    function nextConsecutiveId() public view returns (uint256) {
        return _nextConsecutiveId();
    }

    /**
     * @notice Get consecutive supply count
     * @return Number of consecutive tokens minted
     */
    function consecutiveSupply() public view returns (uint256) {
        return _totalConsecutiveSupply();
    }

    /**
     * @notice Get current batch ID
     * @return Current batch ID
     */
    function currentBatchId() public view returns (uint256) {
        return _nextBatchId;
    }

    /**
     * @notice Withdraw contract balance
     */
    function withdraw() external onlyRole(DEFAULT_ADMIN_ROLE) {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");

        payable(msg.sender).transfer(balance);
    }

    // Internal functions

    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }

    // Required overrides

    function _ownerOf(uint256 tokenId) internal view override(ERC721, ERC721Consecutive) returns (address) {
        return super._ownerOf(tokenId);
    }

    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721, ERC721Consecutive) returns (address) {
        return super._update(to, tokenId, auth);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721, ERC721Consecutive, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}