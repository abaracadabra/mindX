// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Pausable.sol";
import "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Burnable.sol";
import "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Supply.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title ERC1155Extended
 * @notice Comprehensive ERC1155 implementation with supply tracking and advanced features
 * @dev Multi-token standard with pausable, burnable, supply tracking, and role-based access
 */
contract ERC1155Extended is
    ERC1155,
    ERC1155Pausable,
    ERC1155Burnable,
    ERC1155Supply,
    AccessControl,
    ReentrancyGuard
{
    using Strings for uint256;

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant URI_SETTER_ROLE = keccak256("URI_SETTER_ROLE");

    // Token metadata and configuration
    mapping(uint256 => string) private _tokenURIs;
    mapping(uint256 => string) private _tokenNames;
    mapping(uint256 => uint256) private _tokenMaxSupplies;
    mapping(uint256 => bool) private _tokenExists;

    // Contract metadata
    string private _contractURI;
    string private _name;
    string private _symbol;

    // Minting configuration per token
    struct TokenConfig {
        uint256 price;              // Price per token
        uint256 maxSupply;          // Maximum supply (0 = unlimited)
        uint256 maxPerWallet;       // Maximum per wallet
        uint256 maxPerTransaction;  // Maximum per transaction
        bool mintingEnabled;        // Whether minting is enabled
        bool transferable;          // Whether token is transferable
        address creator;            // Token creator
    }

    mapping(uint256 => TokenConfig) public tokenConfigs;
    mapping(uint256 => mapping(address => uint256)) private _walletMinted;

    // Token creation tracking
    uint256 private _nextTokenId = 1;
    uint256 private _totalTokenTypes;

    // Events
    event TokenCreated(
        uint256 indexed tokenId,
        string name,
        uint256 maxSupply,
        address indexed creator
    );
    event TokenConfigUpdated(uint256 indexed tokenId, TokenConfig config);
    event ContractURIUpdated(string contractURI);
    event TokenURIUpdated(uint256 indexed tokenId, string tokenURI);

    /**
     * @notice Initialize ERC1155Extended
     * @param uri Base URI for token metadata
     * @param name_ Collection name
     * @param symbol_ Collection symbol
     * @param admin Admin address
     */
    constructor(
        string memory uri,
        string memory name_,
        string memory symbol_,
        address admin
    ) ERC1155(uri) {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
        _grantRole(BURNER_ROLE, admin);
        _grantRole(URI_SETTER_ROLE, admin);

        _name = name_;
        _symbol = symbol_;
    }

    /**
     * @notice Create a new token type
     * @param name Token name
     * @param maxSupply Maximum supply (0 = unlimited)
     * @param price Price per token
     * @param maxPerWallet Maximum per wallet
     * @param maxPerTransaction Maximum per transaction
     * @param transferable Whether token is transferable
     * @param creator Token creator
     */
    function createToken(
        string memory name,
        uint256 maxSupply,
        uint256 price,
        uint256 maxPerWallet,
        uint256 maxPerTransaction,
        bool transferable,
        address creator
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(bytes(name).length > 0, "Name cannot be empty");
        require(creator != address(0), "Creator cannot be zero address");

        uint256 tokenId = _nextTokenId++;
        _totalTokenTypes++;

        _tokenExists[tokenId] = true;
        _tokenNames[tokenId] = name;
        _tokenMaxSupplies[tokenId] = maxSupply;

        tokenConfigs[tokenId] = TokenConfig({
            price: price,
            maxSupply: maxSupply,
            maxPerWallet: maxPerWallet,
            maxPerTransaction: maxPerTransaction,
            mintingEnabled: true,
            transferable: transferable,
            creator: creator
        });

        emit TokenCreated(tokenId, name, maxSupply, creator);
        return tokenId;
    }

    /**
     * @notice Mint tokens to address
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

        TokenConfig memory config = tokenConfigs[tokenId];
        require(config.mintingEnabled, "Minting disabled for this token");

        if (config.maxSupply > 0) {
            require(totalSupply(tokenId) + amount <= config.maxSupply, "Exceeds maximum supply");
        }

        _mint(to, tokenId, amount, data);
    }

    /**
     * @notice Batch mint multiple tokens
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

            TokenConfig memory config = tokenConfigs[tokenIds[i]];
            require(config.mintingEnabled, "Minting disabled");

            if (config.maxSupply > 0) {
                require(
                    totalSupply(tokenIds[i]) + amounts[i] <= config.maxSupply,
                    "Exceeds maximum supply"
                );
            }
        }

        _mintBatch(to, tokenIds, amounts, data);
    }

    /**
     * @notice Public mint function
     * @param tokenId Token ID
     * @param amount Amount to mint
     */
    function publicMint(uint256 tokenId, uint256 amount) external payable nonReentrant {
        require(_tokenExists[tokenId], "Token does not exist");
        require(amount > 0, "Amount must be greater than 0");

        TokenConfig memory config = tokenConfigs[tokenId];
        require(config.mintingEnabled, "Minting disabled");
        require(amount <= config.maxPerTransaction, "Exceeds max per transaction");

        uint256 walletMinted = _walletMinted[tokenId][msg.sender];
        require(walletMinted + amount <= config.maxPerWallet, "Exceeds max per wallet");

        if (config.maxSupply > 0) {
            require(totalSupply(tokenId) + amount <= config.maxSupply, "Exceeds maximum supply");
        }

        require(msg.value >= config.price * amount, "Insufficient payment");

        _walletMinted[tokenId][msg.sender] += amount;
        _mint(msg.sender, tokenId, amount, "");

        // Refund excess payment
        if (msg.value > config.price * amount) {
            payable(msg.sender).transfer(msg.value - config.price * amount);
        }
    }

    /**
     * @notice Burn tokens (only burner role or owner)
     * @param account Account to burn from
     * @param tokenId Token ID
     * @param amount Amount to burn
     */
    function burn(
        address account,
        uint256 tokenId,
        uint256 amount
    ) public override {
        require(
            hasRole(BURNER_ROLE, msg.sender) || account == msg.sender || isApprovedForAll(account, msg.sender),
            "Not authorized to burn"
        );
        super.burn(account, tokenId, amount);
    }

    /**
     * @notice Update token configuration
     * @param tokenId Token ID
     * @param config New token configuration
     */
    function updateTokenConfig(
        uint256 tokenId,
        TokenConfig memory config
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_tokenExists[tokenId], "Token does not exist");
        require(config.creator != address(0), "Creator cannot be zero address");

        tokenConfigs[tokenId] = config;
        emit TokenConfigUpdated(tokenId, config);
    }

    /**
     * @notice Set token URI
     * @param tokenId Token ID
     * @param tokenURI New token URI
     */
    function setTokenURI(uint256 tokenId, string memory tokenURI) external onlyRole(URI_SETTER_ROLE) {
        require(_tokenExists[tokenId], "Token does not exist");
        _tokenURIs[tokenId] = tokenURI;
        emit TokenURIUpdated(tokenId, tokenURI);
    }

    /**
     * @notice Set contract URI
     * @param contractURI_ New contract URI
     */
    function setContractURI(string memory contractURI_) external onlyRole(URI_SETTER_ROLE) {
        _contractURI = contractURI_;
        emit ContractURIUpdated(contractURI_);
    }

    /**
     * @notice Set base URI for all tokens
     * @param newuri New base URI
     */
    function setURI(string memory newuri) external onlyRole(URI_SETTER_ROLE) {
        _setURI(newuri);
    }

    /**
     * @notice Toggle minting for a token
     * @param tokenId Token ID
     * @param enabled Whether minting is enabled
     */
    function setMintingEnabled(uint256 tokenId, bool enabled) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_tokenExists[tokenId], "Token does not exist");
        tokenConfigs[tokenId].mintingEnabled = enabled;
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

        string memory baseURI = super.uri(tokenId);
        return bytes(baseURI).length > 0 ?
            string(abi.encodePacked(baseURI, tokenId.toString())) : "";
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
     * @notice Check if token exists
     * @param tokenId Token ID
     * @return Whether token exists
     */
    function tokenExists(uint256 tokenId) public view returns (bool) {
        return _tokenExists[tokenId];
    }

    /**
     * @notice Get total number of token types
     * @return Total token types
     */
    function totalTokenTypes() public view returns (uint256) {
        return _totalTokenTypes;
    }

    /**
     * @notice Get next token ID
     * @return Next token ID
     */
    function nextTokenId() public view returns (uint256) {
        return _nextTokenId;
    }

    /**
     * @notice Get amount minted by wallet for token
     * @param tokenId Token ID
     * @param wallet Wallet address
     * @return Amount minted
     */
    function walletMinted(uint256 tokenId, address wallet) public view returns (uint256) {
        return _walletMinted[tokenId][wallet];
    }

    /**
     * @notice Withdraw contract balance
     */
    function withdraw() external onlyRole(DEFAULT_ADMIN_ROLE) {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");
        payable(msg.sender).transfer(balance);
    }

    // Override transfer to check transferability
    function _update(
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory values
    ) internal override(ERC1155, ERC1155Pausable, ERC1155Supply) {
        // Check transferability for each token
        if (from != address(0) && to != address(0)) {
            for (uint256 i = 0; i < ids.length; i++) {
                if (_tokenExists[ids[i]]) {
                    require(tokenConfigs[ids[i]].transferable, "Token not transferable");
                }
            }
        }

        super._update(from, to, ids, values);
    }

    // Required overrides

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC1155, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}