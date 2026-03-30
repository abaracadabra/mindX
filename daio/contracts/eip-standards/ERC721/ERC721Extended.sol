// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Pausable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title ERC721Extended
 * @notice Comprehensive ERC721 implementation with enumerable, metadata, pausing, and burning
 * @dev Combines ERC721 with all standard extensions and role-based access control
 */
contract ERC721Extended is
    ERC721,
    ERC721Enumerable,
    ERC721URIStorage,
    ERC721Pausable,
    ERC721Burnable,
    AccessControl,
    ReentrancyGuard
{
    using Strings for uint256;

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant METADATA_ROLE = keccak256("METADATA_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");

    // Metadata configuration
    string private _baseTokenURI;
    string private _contractURI;

    // Supply controls
    uint256 private _maxSupply;
    bool private _hasMaxSupply;

    // Minting configuration
    struct MintConfig {
        uint256 publicPrice;
        uint256 maxPerWallet;
        uint256 maxPerTransaction;
        bool publicSaleActive;
        bool whitelistActive;
        uint256 whitelistPrice;
    }

    MintConfig public mintConfig;

    // Whitelist and ownership tracking
    mapping(address => bool) private _whitelist;
    mapping(address => uint256) private _mintedPerWallet;

    // Token counter
    uint256 private _nextTokenId = 1;

    // Events
    event MaxSupplySet(uint256 maxSupply);
    event MintConfigUpdated(
        uint256 publicPrice,
        uint256 maxPerWallet,
        uint256 maxPerTransaction,
        bool publicSaleActive,
        bool whitelistActive,
        uint256 whitelistPrice
    );
    event WhitelistUpdated(address indexed account, bool whitelisted);
    event BaseURIUpdated(string baseURI);
    event ContractURIUpdated(string contractURI);

    /**
     * @notice Initialize ERC721Extended with full configuration
     * @param name Token name
     * @param symbol Token symbol
     * @param baseURI Base URI for token metadata
     * @param maxSupply Maximum token supply (0 = no limit)
     * @param admin Address to receive admin role
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
        _grantRole(PAUSER_ROLE, admin);
        _grantRole(METADATA_ROLE, admin);
        _grantRole(BURNER_ROLE, admin);

        _baseTokenURI = baseURI;

        if (maxSupply > 0) {
            _maxSupply = maxSupply;
            _hasMaxSupply = true;
            emit MaxSupplySet(maxSupply);
        }

        // Initialize mint config
        mintConfig = MintConfig({
            publicPrice: 0.001 ether,
            maxPerWallet: 10,
            maxPerTransaction: 5,
            publicSaleActive: false,
            whitelistActive: false,
            whitelistPrice: 0.0005 ether
        });
    }

    /**
     * @notice Mint token to address
     * @param to Address to mint to
     * @param tokenURI Optional custom token URI
     */
    function mint(address to, string memory tokenURI) public onlyRole(MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");

        if (_hasMaxSupply) {
            require(_nextTokenId <= _maxSupply, "Exceeds maximum supply");
        }

        uint256 tokenId = _nextTokenId++;
        _safeMint(to, tokenId);

        if (bytes(tokenURI).length > 0) {
            _setTokenURI(tokenId, tokenURI);
        }
    }

    /**
     * @notice Batch mint multiple tokens
     * @param to Address to mint to
     * @param quantity Number of tokens to mint
     */
    function batchMint(address to, uint256 quantity) external onlyRole(MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");
        require(quantity > 0 && quantity <= 50, "Invalid quantity");

        if (_hasMaxSupply) {
            require(_nextTokenId + quantity - 1 <= _maxSupply, "Exceeds maximum supply");
        }

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = _nextTokenId++;
            _safeMint(to, tokenId);
        }
    }

    /**
     * @notice Public mint function
     * @param quantity Number of tokens to mint
     */
    function publicMint(uint256 quantity) external payable nonReentrant {
        require(mintConfig.publicSaleActive, "Public sale not active");
        require(quantity > 0, "Quantity must be greater than 0");
        require(quantity <= mintConfig.maxPerTransaction, "Exceeds max per transaction");

        uint256 walletMinted = _mintedPerWallet[msg.sender];
        require(walletMinted + quantity <= mintConfig.maxPerWallet, "Exceeds max per wallet");

        if (_hasMaxSupply) {
            require(_nextTokenId + quantity - 1 <= _maxSupply, "Exceeds maximum supply");
        }

        require(msg.value >= mintConfig.publicPrice * quantity, "Insufficient payment");

        _mintedPerWallet[msg.sender] += quantity;

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = _nextTokenId++;
            _safeMint(msg.sender, tokenId);
        }

        // Refund excess payment
        if (msg.value > mintConfig.publicPrice * quantity) {
            payable(msg.sender).transfer(msg.value - mintConfig.publicPrice * quantity);
        }
    }

    /**
     * @notice Whitelist mint function
     * @param quantity Number of tokens to mint
     */
    function whitelistMint(uint256 quantity) external payable nonReentrant {
        require(mintConfig.whitelistActive, "Whitelist sale not active");
        require(_whitelist[msg.sender], "Not whitelisted");
        require(quantity > 0, "Quantity must be greater than 0");
        require(quantity <= mintConfig.maxPerTransaction, "Exceeds max per transaction");

        uint256 walletMinted = _mintedPerWallet[msg.sender];
        require(walletMinted + quantity <= mintConfig.maxPerWallet, "Exceeds max per wallet");

        if (_hasMaxSupply) {
            require(_nextTokenId + quantity - 1 <= _maxSupply, "Exceeds maximum supply");
        }

        require(msg.value >= mintConfig.whitelistPrice * quantity, "Insufficient payment");

        _mintedPerWallet[msg.sender] += quantity;

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = _nextTokenId++;
            _safeMint(msg.sender, tokenId);
        }

        // Refund excess payment
        if (msg.value > mintConfig.whitelistPrice * quantity) {
            payable(msg.sender).transfer(msg.value - mintConfig.whitelistPrice * quantity);
        }
    }

    /**
     * @notice Burn token (only burner role or owner)
     * @param tokenId Token ID to burn
     */
    function burn(uint256 tokenId) public override {
        require(
            hasRole(BURNER_ROLE, msg.sender) || ownerOf(tokenId) == msg.sender,
            "Not authorized to burn"
        );
        super.burn(tokenId);
    }

    /**
     * @notice Update token URI
     * @param tokenId Token ID
     * @param tokenURI New token URI
     */
    function setTokenURI(
        uint256 tokenId,
        string memory tokenURI
    ) public onlyRole(METADATA_ROLE) {
        _setTokenURI(tokenId, tokenURI);
    }

    /**
     * @notice Set base URI for all tokens
     * @param baseURI New base URI
     */
    function setBaseURI(string memory baseURI) external onlyRole(METADATA_ROLE) {
        _baseTokenURI = baseURI;
        emit BaseURIUpdated(baseURI);
    }

    /**
     * @notice Set contract URI for marketplace metadata
     * @param contractURI_ New contract URI
     */
    function setContractURI(string memory contractURI_) external onlyRole(METADATA_ROLE) {
        _contractURI = contractURI_;
        emit ContractURIUpdated(contractURI_);
    }

    /**
     * @notice Configure minting parameters
     * @param publicPrice Price for public mint
     * @param maxPerWallet Maximum tokens per wallet
     * @param maxPerTransaction Maximum tokens per transaction
     * @param publicSaleActive Whether public sale is active
     * @param whitelistActive Whether whitelist sale is active
     * @param whitelistPrice Price for whitelist mint
     */
    function setMintConfig(
        uint256 publicPrice,
        uint256 maxPerWallet,
        uint256 maxPerTransaction,
        bool publicSaleActive,
        bool whitelistActive,
        uint256 whitelistPrice
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(maxPerTransaction <= 50, "Max per transaction too high");
        require(maxPerWallet <= 1000, "Max per wallet too high");

        mintConfig = MintConfig({
            publicPrice: publicPrice,
            maxPerWallet: maxPerWallet,
            maxPerTransaction: maxPerTransaction,
            publicSaleActive: publicSaleActive,
            whitelistActive: whitelistActive,
            whitelistPrice: whitelistPrice
        });

        emit MintConfigUpdated(
            publicPrice,
            maxPerWallet,
            maxPerTransaction,
            publicSaleActive,
            whitelistActive,
            whitelistPrice
        );
    }

    /**
     * @notice Add/remove addresses from whitelist
     * @param accounts Array of addresses
     * @param whitelisted Whether to whitelist or remove
     */
    function setWhitelist(
        address[] calldata accounts,
        bool whitelisted
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        for (uint256 i = 0; i < accounts.length; i++) {
            _whitelist[accounts[i]] = whitelisted;
            emit WhitelistUpdated(accounts[i], whitelisted);
        }
    }

    /**
     * @notice Check if address is whitelisted
     * @param account Address to check
     * @return Whether address is whitelisted
     */
    function isWhitelisted(address account) external view returns (bool) {
        return _whitelist[account];
    }

    /**
     * @notice Get tokens minted by address
     * @param account Address to check
     * @return Number of tokens minted
     */
    function getMintedByAddress(address account) external view returns (uint256) {
        return _mintedPerWallet[account];
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
     * @notice Get next token ID to be minted
     * @return Next token ID
     */
    function nextTokenId() public view returns (uint256) {
        return _nextTokenId;
    }

    /**
     * @notice Get contract URI for marketplace metadata
     * @return Contract URI
     */
    function contractURI() public view returns (string memory) {
        return _contractURI;
    }

    /**
     * @notice Pause token transfers
     */
    function pause() public onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause token transfers
     */
    function unpause() public onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /**
     * @notice Withdraw contract balance
     */
    function withdraw() external onlyRole(DEFAULT_ADMIN_ROLE) {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");

        payable(msg.sender).transfer(balance);
    }

    // Required overrides for multiple inheritance

    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }

    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721, ERC721Enumerable, ERC721Pausable) returns (address) {
        return super._update(to, tokenId, auth);
    }

    function _increaseBalance(
        address account,
        uint128 value
    ) internal override(ERC721, ERC721Enumerable) {
        super._increaseBalance(account, value);
    }

    function tokenURI(
        uint256 tokenId
    ) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721, ERC721Enumerable, ERC721URIStorage, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}