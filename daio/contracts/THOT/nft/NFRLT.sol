// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title NFRLT - NFT Royalty Token
 * @dev NFT with royalty distribution and soulbound support
 */
contract NFRLT is ERC721, AccessControl, ReentrancyGuard {
    using SafeERC20 for IERC20;
    using Address for address payable;
    using Strings for uint256;

    // Role definitions
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    // State variables
    uint256 private _tokenIdCounter;
    address payable public immutable creator;
    uint256 public immutable creatorFixedRoyalty;      // in wei
    uint256 public immutable creatorRoyaltyPercentage; // from 0 to 25%
    uint256 public constant MAX_ROYALTY_PERCENTAGE = 25;  // Maximum 25% total royalty
    uint256 public constant PERCENTAGE_BASE = 100;        // Base for percentage calculations
    uint256 public constant MAX_ROYALTY_RECIPIENTS = 5;   // Maximum number of royalty recipients per token

    // Structs
    struct TokenSaleInfo {
        uint256 salePriceETH;          // Sale price in wei
        SalePriceERC20 salePriceERC20; // Sale price in ERC20 tokens
        bool isListed;                 // Is the token listed for sale
        uint256 lastUpdateTime;        // Timestamp of the last update
    }

    struct SalePriceERC20 {
        string name;                   // ERC20 token name
        string symbol;                 // ERC20 token symbol
        string chain;                  // Blockchain network
        address contractAddress;       // ERC20 token contract address
        uint256 salePrice;            // Sale price in token units
        bool isValid;                 // Is the sale price valid
    }

    struct RoyaltyInfo {
        address payable recipient;     // Royalty recipient address
        uint256 percentage;            // Royalty percentage (0-25%)
        uint256 fixedAmount;           // Fixed royalty amount in wei
        bool isActive;                 // Is the royalty active
    }

    struct UserIdentity {
        string username;      
        string class;
        uint32 level;
        uint32 health;
        uint32 stamina;
        uint32 strength;
        uint32 intelligence;
        uint32 dexterity;
        bool isSoulbound;     // Added soulbound flag
    }

    // Mappings
    mapping(uint256 => TokenSaleInfo) private _tokenSalePrices;
    mapping(uint256 => RoyaltyInfo[]) private _royalties;
    mapping(uint256 => uint256) private _totalRoyaltyPercentage;
    mapping(address => bool) public whitelistedERC20Tokens;
    mapping(uint256 => UserIdentity) private _userIdentities;
    mapping(uint256 => address) private _soulboundOwners;
    mapping(uint256 => string) private _tokenURIs;

    // Events
    event RoyaltyPaid(
        address indexed recipient,
        uint256 indexed tokenId,
        uint256 amount,
        address indexed currency
    );
    event NFTTransferred(
        address indexed from,
        address indexed to,
        uint256 indexed tokenId,
        uint256 salePrice,
        address currency
    );
    event SalePriceUpdated(
        uint256 indexed tokenId,
        uint256 newPrice,
        address indexed currency
    );
    event RoyaltyUpdated(
        uint256 indexed tokenId,
        address indexed recipient,
        uint256 percentage,
        uint256 fixedAmount
    );
    event TokenListed(uint256 indexed tokenId, bool isListed);
    event ERC20TokenWhitelisted(address indexed token, bool status);

    // Modifiers
    modifier validateTokenExists(uint256 tokenId) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        _;
    }

    modifier onlyAdmin() {
        require(hasRole(ADMIN_ROLE, msg.sender), "Caller is not an admin");
        _;
    }

    modifier onlyMinter() {
        require(hasRole(MINTER_ROLE, msg.sender), "Caller is not a minter");
        _;
    }

    modifier validRoyaltyPercentage(uint256 percentage) {
        require(percentage <= MAX_ROYALTY_PERCENTAGE, "Royalty percentage too high");
        _;
    }

    constructor(
        string memory name_,
        string memory symbol_,
        address payable _creator,
        uint256 _creatorFixedRoyaltyInEther,
        uint256 _creatorRoyaltyPercentage
    ) ERC721(name_, symbol_) {
        require(_creator != address(0), "Invalid creator address");
        require(
            _creatorRoyaltyPercentage <= MAX_ROYALTY_PERCENTAGE,
            "Royalty percentage too high"
        );

        creator = _creator;
        creatorFixedRoyalty = _creatorFixedRoyaltyInEther * 1 ether;
        creatorRoyaltyPercentage = _creatorRoyaltyPercentage;
        _tokenIdCounter = 1;

        _grantRole(DEFAULT_ADMIN_ROLE, _creator);
        _grantRole(ADMIN_ROLE, _creator);
        _grantRole(MINTER_ROLE, _creator);

        _setRoleAdmin(ADMIN_ROLE, DEFAULT_ADMIN_ROLE);
        _setRoleAdmin(MINTER_ROLE, ADMIN_ROLE);
    }

    // Internal functions
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address) {
        address from = _ownerOf(tokenId);
        if (from != address(0) && _userIdentities[tokenId].isSoulbound) {
            require(to == address(0), "Soulbound token cannot be transferred");
        }
        return super._update(to, tokenId, auth);
    }

    function _setTokenURI(uint256 tokenId, string memory _tokenURI) internal {
        require(_ownerOf(tokenId) != address(0), "URI set of nonexistent token");
        _tokenURIs[tokenId] = _tokenURI;
    }

    function _addRoyalty(
        uint256 tokenId,
        address payable recipient,
        uint256 percentage,
        uint256 fixedAmount
    ) internal validRoyaltyPercentage(percentage) {
        require(
            _royalties[tokenId].length < MAX_ROYALTY_RECIPIENTS,
            "Maximum royalty recipients reached"
        );

        _royalties[tokenId].push(RoyaltyInfo({
            recipient: recipient,
            percentage: percentage,
            fixedAmount: fixedAmount,
            isActive: true
        }));

        _totalRoyaltyPercentage[tokenId] += percentage;
        require(
            _totalRoyaltyPercentage[tokenId] <= MAX_ROYALTY_PERCENTAGE,
            "Total royalty percentage exceeds maximum"
        );

        emit RoyaltyUpdated(tokenId, recipient, percentage, fixedAmount);
    }

    function _distributeRoyalties(
        uint256 tokenId,
        uint256 salePrice,
        address currency
    ) internal returns (uint256) {
        uint256 totalRoyalties = 0;
        RoyaltyInfo[] storage recipients = _royalties[tokenId];

        for (uint256 i = 0; i < recipients.length; i++) {
            if (!recipients[i].isActive) continue;

            uint256 royaltyAmount = _calculateRoyalty(
                salePrice,
                recipients[i].percentage,
                recipients[i].fixedAmount
            );

            if (royaltyAmount > 0) {
                totalRoyalties += royaltyAmount;
                require(
                    totalRoyalties <= salePrice,
                    "Total royalties exceed sale price"
                );

                if (currency == address(0)) {
                    recipients[i].recipient.sendValue(royaltyAmount);
                } else {
                    IERC20(currency).safeTransferFrom(
                        msg.sender,
                        recipients[i].recipient,
                        royaltyAmount
                    );
                }

                emit RoyaltyPaid(
                    recipients[i].recipient,
                    tokenId,
                    royaltyAmount,
                    currency
                );
            }
        }

        return salePrice - totalRoyalties;
    }

    function _calculateRoyalty(
        uint256 salePrice,
        uint256 percentage,
        uint256 fixedAmount
    ) internal pure returns (uint256) {
        uint256 percentageAmount = (salePrice * percentage) / PERCENTAGE_BASE;
        return percentageAmount > fixedAmount ? percentageAmount : fixedAmount;
    }

    function _baseURI() internal pure override returns (string memory) {
        return "";
    }

    // Public functions
    function tokenURI(uint256 tokenId) 
        public 
        view 
        override 
        returns (string memory) 
    {
        require(_ownerOf(tokenId) != address(0), "URI query for nonexistent token");
        string memory _tokenURI = _tokenURIs[tokenId];
        string memory base = _baseURI();

        if (bytes(base).length == 0) {
            return _tokenURI;
        }
        if (bytes(_tokenURI).length > 0) {
            return string(abi.encodePacked(base, _tokenURI));
        }
        return string(abi.encodePacked(base, tokenId.toString()));
    }

    function createSoulboundNFT(
        address to,
        string memory _tokenURI,
        string memory username,
        string memory class_,
        uint32 level,
        uint32 health,
        uint32 stamina,
        uint32 strength,
        uint32 intelligence,
        uint32 dexterity
    ) public onlyMinter returns (uint256) {
        uint256 tokenId = _tokenIdCounter++;

        _safeMint(to, tokenId);
        _setTokenURI(tokenId, _tokenURI);

        _userIdentities[tokenId] = UserIdentity({
            username: username,
            class: class_,
            level: level,
            health: health,
            stamina: stamina,
            strength: strength,
            intelligence: intelligence,
            dexterity: dexterity,
            isSoulbound: true
        });

        _soulboundOwners[tokenId] = to;

        _addRoyalty(
            tokenId,
            creator,
            creatorRoyaltyPercentage,
            creatorFixedRoyalty
        );

        return tokenId;
    }

    function createNFT(string memory _tokenURI) public onlyMinter returns (uint256) {
        uint256 tokenId = _tokenIdCounter++;

        _safeMint(msg.sender, tokenId);
        _setTokenURI(tokenId, _tokenURI);

        _addRoyalty(
            tokenId,
            creator,
            creatorRoyaltyPercentage,
            creatorFixedRoyalty
        );

        return tokenId;
    }

    /**
     * @dev Broker transfer with royalty distribution (for marketplace)
     */
    function brokerTransferETH(
        address from,
        address to,
        uint256 tokenId
    ) external payable nonReentrant {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(ownerOf(tokenId) == from, "Not token owner");
        require(!_userIdentities[tokenId].isSoulbound, "Cannot transfer soulbound token");

        uint256 salePrice = msg.value;
        uint256 netAmount = _distributeRoyalties(tokenId, salePrice, address(0));
        
        payable(from).sendValue(netAmount);
        
        _transfer(from, to, tokenId);
        
        emit NFTTransferred(from, to, tokenId, salePrice, address(0));
    }

    function getUserIdentity(uint256 tokenId)
        external
        view
        validateTokenExists(tokenId)
        returns (
            string memory,  // username
            string memory,  // class
            uint32,         // level
            uint32,         // health
            uint32,         // stamina
            uint32,         // strength
            uint32,         // intelligence
            uint32,         // dexterity
            bool           // isSoulbound
        )
    {
        UserIdentity storage identity = _userIdentities[tokenId];
        return (
            identity.username,
            identity.class,
            identity.level,
            identity.health,
            identity.stamina,
            identity.strength,
            identity.intelligence,
            identity.dexterity,
            identity.isSoulbound
        );
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    function isTokenSoulbound(uint256 tokenId) public view returns (bool) {
        return _userIdentities[tokenId].isSoulbound;
    }

    function isSoulboundOwner(address account, uint256 tokenId) public view returns (bool) {
        return _soulboundOwners[tokenId] == account;
    }
}
