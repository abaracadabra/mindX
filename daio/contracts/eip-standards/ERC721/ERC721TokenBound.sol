// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Create2.sol";

/**
 * @title ERC721TokenBound
 * @notice ERC721 implementation with ERC6551 token bound accounts
 * @dev Each NFT can have its own smart contract wallet for holding assets
 */
contract ERC721TokenBound is ERC721, AccessControl, ReentrancyGuard {

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant ACCOUNT_MANAGER_ROLE = keccak256("ACCOUNT_MANAGER_ROLE");

    // ERC6551 Registry interface
    interface IERC6551Registry {
        function createAccount(
            address implementation,
            uint256 chainId,
            address tokenContract,
            uint256 tokenId,
            uint256 salt,
            bytes calldata initData
        ) external returns (address);

        function account(
            address implementation,
            uint256 chainId,
            address tokenContract,
            uint256 tokenId,
            uint256 salt
        ) external view returns (address);
    }

    // Token bound account implementation
    address public immutable accountImplementation;
    address public immutable registry;
    uint256 public immutable chainId;

    // Token metadata and accounts
    mapping(uint256 => string) private _tokenURIs;
    mapping(uint256 => address) private _tokenAccounts;
    mapping(uint256 => bool) private _accountCreated;

    string private _baseTokenURI;
    uint256 private _nextTokenId = 1;
    uint256 private _totalSupply;

    // Account configuration
    struct AccountConfig {
        bool autoCreateAccount;     // Whether to auto-create account on mint
        uint256 defaultSalt;        // Default salt for account creation
        bytes initData;             // Default initialization data
    }

    AccountConfig public accountConfig;

    // Events
    event TokenAccountCreated(uint256 indexed tokenId, address indexed account);
    event TokenMinted(uint256 indexed tokenId, address indexed to, bool accountCreated);
    event AccountConfigUpdated(bool autoCreateAccount, uint256 defaultSalt);

    /**
     * @notice Initialize ERC721 with token bound accounts
     * @param name Token name
     * @param symbol Token symbol
     * @param baseURI Base URI for metadata
     * @param accountImplementation_ TBA implementation contract
     * @param registry_ ERC6551 registry address
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        string memory baseURI,
        address accountImplementation_,
        address registry_,
        address admin
    ) ERC721(name, symbol) {
        require(admin != address(0), "Admin cannot be zero address");
        require(accountImplementation_ != address(0), "Implementation cannot be zero address");
        require(registry_ != address(0), "Registry cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(ACCOUNT_MANAGER_ROLE, admin);

        _baseTokenURI = baseURI;
        accountImplementation = accountImplementation_;
        registry = registry_;
        chainId = block.chainid;

        // Default configuration
        accountConfig = AccountConfig({
            autoCreateAccount: true,
            defaultSalt: 0,
            initData: ""
        });
    }

    /**
     * @notice Mint token with optional token bound account
     * @param to Address to mint to
     * @param tokenURI Optional custom token URI
     * @param createAccount Whether to create token bound account
     * @param salt Salt for account creation
     * @param initData Initialization data for account
     */
    function mint(
        address to,
        string memory tokenURI,
        bool createAccount,
        uint256 salt,
        bytes memory initData
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(to != address(0), "Cannot mint to zero address");

        uint256 tokenId = _nextTokenId++;
        _totalSupply++;

        _mint(to, tokenId);

        if (bytes(tokenURI).length > 0) {
            _tokenURIs[tokenId] = tokenURI;
        }

        bool accountCreated = false;
        if (createAccount || accountConfig.autoCreateAccount) {
            address account = _createTokenAccount(tokenId, salt, initData);
            _tokenAccounts[tokenId] = account;
            _accountCreated[tokenId] = true;
            accountCreated = true;
            emit TokenAccountCreated(tokenId, account);
        }

        emit TokenMinted(tokenId, to, accountCreated);
        return tokenId;
    }

    /**
     * @notice Simple mint with default account settings
     * @param to Address to mint to
     */
    function simpleMint(address to) external onlyRole(MINTER_ROLE) returns (uint256) {
        return mint(to, "", accountConfig.autoCreateAccount, accountConfig.defaultSalt, accountConfig.initData);
    }

    /**
     * @notice Create token bound account for existing token
     * @param tokenId Token ID
     * @param salt Salt for account creation
     * @param initData Initialization data
     */
    function createTokenAccount(
        uint256 tokenId,
        uint256 salt,
        bytes memory initData
    ) external onlyRole(ACCOUNT_MANAGER_ROLE) returns (address) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(!_accountCreated[tokenId], "Account already created");

        address account = _createTokenAccount(tokenId, salt, initData);
        _tokenAccounts[tokenId] = account;
        _accountCreated[tokenId] = true;

        emit TokenAccountCreated(tokenId, account);
        return account;
    }

    /**
     * @notice Get token bound account address
     * @param tokenId Token ID
     * @return account Token bound account address (zero if not created)
     */
    function getTokenAccount(uint256 tokenId) external view returns (address account) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _tokenAccounts[tokenId];
    }

    /**
     * @notice Check if token has bound account
     * @param tokenId Token ID
     * @return Whether token has bound account
     */
    function hasTokenAccount(uint256 tokenId) external view returns (bool) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _accountCreated[tokenId];
    }

    /**
     * @notice Compute token bound account address (without creating)
     * @param tokenId Token ID
     * @param salt Salt for account creation
     * @return Predicted account address
     */
    function computeTokenAccount(
        uint256 tokenId,
        uint256 salt
    ) external view returns (address) {
        return IERC6551Registry(registry).account(
            accountImplementation,
            chainId,
            address(this),
            tokenId,
            salt
        );
    }

    /**
     * @notice Batch create accounts for multiple tokens
     * @param tokenIds Array of token IDs
     * @param salt Salt for account creation
     * @param initData Initialization data
     */
    function batchCreateAccounts(
        uint256[] calldata tokenIds,
        uint256 salt,
        bytes memory initData
    ) external onlyRole(ACCOUNT_MANAGER_ROLE) {
        require(tokenIds.length > 0 && tokenIds.length <= 50, "Invalid batch size");

        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];

            if (_ownerOf(tokenId) != address(0) && !_accountCreated[tokenId]) {
                address account = _createTokenAccount(tokenId, salt, initData);
                _tokenAccounts[tokenId] = account;
                _accountCreated[tokenId] = true;
                emit TokenAccountCreated(tokenId, account);
            }
        }
    }

    /**
     * @notice Configure account creation settings
     * @param autoCreateAccount Whether to auto-create accounts on mint
     * @param defaultSalt Default salt for account creation
     * @param initData Default initialization data
     */
    function setAccountConfig(
        bool autoCreateAccount,
        uint256 defaultSalt,
        bytes memory initData
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        accountConfig = AccountConfig({
            autoCreateAccount: autoCreateAccount,
            defaultSalt: defaultSalt,
            initData: initData
        });

        emit AccountConfigUpdated(autoCreateAccount, defaultSalt);
    }

    /**
     * @notice Execute call from token bound account (for account owner)
     * @param tokenId Token ID
     * @param to Target address
     * @param value ETH value
     * @param data Call data
     */
    function executeFromAccount(
        uint256 tokenId,
        address to,
        uint256 value,
        bytes calldata data
    ) external nonReentrant returns (bytes memory) {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(_accountCreated[tokenId], "No account for token");

        address account = _tokenAccounts[tokenId];

        // Call the execute function on the token bound account
        (bool success, bytes memory result) = account.call(
            abi.encodeWithSignature("execute(address,uint256,bytes)", to, value, data)
        );

        require(success, "Account execution failed");
        return result;
    }

    /**
     * @notice Get total supply
     * @return Total number of tokens minted
     */
    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    /**
     * @notice Get next token ID
     * @return Next token ID to be minted
     */
    function nextTokenId() public view returns (uint256) {
        return _nextTokenId;
    }

    /**
     * @notice Update token URI
     * @param tokenId Token ID
     * @param tokenURI New token URI
     */
    function setTokenURI(uint256 tokenId, string memory tokenURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        _tokenURIs[tokenId] = tokenURI;
    }

    /**
     * @notice Set base URI
     * @param baseURI New base URI
     */
    function setBaseURI(string memory baseURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _baseTokenURI = baseURI;
    }

    // Internal functions

    function _createTokenAccount(
        uint256 tokenId,
        uint256 salt,
        bytes memory initData
    ) internal returns (address) {
        return IERC6551Registry(registry).createAccount(
            accountImplementation,
            chainId,
            address(this),
            tokenId,
            salt,
            initData
        );
    }

    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");

        string memory customURI = _tokenURIs[tokenId];
        if (bytes(customURI).length > 0) {
            return customURI;
        }

        string memory baseURI = _baseURI();
        return bytes(baseURI).length > 0 ?
            string(abi.encodePacked(baseURI, tokenId.toString())) : "";
    }

    // Override transfer to update account ownership
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address) {
        address from = super._update(to, tokenId, auth);

        // If token has an account, the account's owner is now the new token holder
        // The ERC6551 implementation should handle this automatically

        return from;
    }

    // Required overrides

    using Strings for uint256;

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, AccessControl) returns (bool) {
        // ERC6551 interface support can be added here if needed
        return super.supportsInterface(interfaceId);
    }
}