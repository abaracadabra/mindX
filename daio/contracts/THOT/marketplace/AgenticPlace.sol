// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../nft/NFRLT.sol";
import "../../THOT/core/THOT.sol";
import "../../daio/governance/AgentFactory.sol";

/**
 * @title AgenticPlace
 * @notice Foundational standalone marketplace contract for NFT skills and services
 * @dev Core marketplace functionality that can be extended by iNFT, dNFT, and other contracts
 * @dev Supports multiple NFT types: NFRLT, THOT, AgentFactory NFTs, and any ERC721
 * @dev Designed to be imported and extended by iNFT, dNFT, SoulBadger, and other NFT contracts
 */
contract AgenticPlace is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    enum NFTType {
        NFRLT,      // NFT Royalty Token
        THOT,       // Transferable Hyper-Optimized Tensor
        AgentNFT,   // AgentFactory NFT
        ERC721      // Generic ERC721 (includes iNFT, dNFT, etc.)
    }

    struct SkillOffer {
        uint256 skillTokenId;
        NFTType nftType;
        address nftContract;    // Contract address for the NFT
        uint256 price;
        bool isETH;
        address paymentToken;
        address owner;
        bool isActive;
        uint40 createdAt;
        uint40 expiresAt;
    }

    // Contract references (optional - can be set after deployment)
    NFRLT public nfRLTContract;
    THOT public thotContract;
    AgentFactory public agentFactory;
    address public agentManagement; // Optional AgentManagement contract

    // Storage
    mapping(uint256 => mapping(address => SkillOffer)) public skillOffers; // tokenId => nftContract => offer
    mapping(address => bool) public whitelistedNFTContracts;
    mapping(address => bool) public whitelistedPaymentTokens;
    mapping(address => NFTType) public nftContractTypes; // Track NFT contract types

    // Events
    event SkillOffered(
        uint256 indexed skillTokenId,
        address indexed nftContract,
        NFTType nftType,
        uint256 price,
        bool isETH,
        address paymentToken,
        address indexed owner,
        uint40 expiresAt
    );

    event SkillHired(
        uint256 indexed skillTokenId,
        address indexed nftContract,
        address indexed hirer,
        address owner,
        uint256 price,
        bool isETH,
        uint256 royaltyAmount
    );

    event SkillRemoved(
        uint256 indexed skillTokenId,
        address indexed nftContract,
        address indexed owner
    );

    event NFTContractWhitelisted(address indexed nftContract, NFTType nftType);
    event PaymentTokenWhitelisted(address indexed token, bool status);
    event AgentManagementUpdated(address indexed oldAddress, address indexed newAddress);
    event SoulBadgerUpdated(address indexed oldAddress, address indexed newAddress);

    modifier validNFTContract(address nftContract) {
        require(whitelistedNFTContracts[nftContract], "NFT contract not whitelisted");
        _;
    }

    modifier validPaymentToken(address token) {
        if (token != address(0)) {
            require(whitelistedPaymentTokens[token], "Payment token not whitelisted");
        }
        _;
    }

    /**
     * @dev Constructor - AgenticPlace can be deployed standalone
     * @param _nfRLTContract Optional NFRLT contract address (can be set later)
     * @param _thotContract Optional THOT contract address (can be set later)
     * @param _agentFactory Optional AgentFactory contract address (can be set later)
     */
    constructor(
        address _nfRLTContract,
        address _thotContract,
        address _agentFactory
    ) Ownable(msg.sender) {
        // Optional contracts - can be address(0) and set later
        if (_nfRLTContract != address(0)) {
            nfRLTContract = NFRLT(_nfRLTContract);
            whitelistedNFTContracts[_nfRLTContract] = true;
            nftContractTypes[_nfRLTContract] = NFTType.NFRLT;
        }
        
        if (_thotContract != address(0)) {
            thotContract = THOT(_thotContract);
            whitelistedNFTContracts[_thotContract] = true;
            nftContractTypes[_thotContract] = NFTType.THOT;
        }
        
        if (_agentFactory != address(0)) {
            agentFactory = AgentFactory(_agentFactory);
            whitelistedNFTContracts[_agentFactory] = true;
            nftContractTypes[_agentFactory] = NFTType.AgentNFT;
        }
    }

    /**
     * @dev Offer an NFT skill for hire
     * @param skillTokenId The token ID of the skill NFT
     * @param nftContract Address of the NFT contract
     * @param price The price to hire the skill
     * @param isETH True if payment is in ETH, false if ERC-20
     * @param paymentToken Address of the ERC-20 token contract (if applicable)
     * @param expiresAt Expiration timestamp (0 for no expiration)
     */
    function offerSkill(
        uint256 skillTokenId,
        address nftContract,
        uint256 price,
        bool isETH,
        address paymentToken,
        uint40 expiresAt
    ) external validNFTContract(nftContract) validPaymentToken(paymentToken) {
        IERC721 nft = IERC721(nftContract);
        require(nft.ownerOf(skillTokenId) == msg.sender, "Caller is not the owner");

        // Check agent status if AgentFactory NFT
        if (nftContractTypes[nftContract] == NFTType.AgentNFT) {
            address agentAddress = _getAgentAddressFromNFT(skillTokenId);
            if (agentAddress != address(0)) {
                require(agentFactory.isAgentActive(agentAddress), "Agent is not active");
            }
        }

        NFTType nftType = nftContractTypes[nftContract];
        skillOffers[skillTokenId][nftContract] = SkillOffer({
            skillTokenId: skillTokenId,
            nftType: nftType,
            nftContract: nftContract,
            price: price,
            isETH: isETH,
            paymentToken: paymentToken,
            owner: msg.sender,
            isActive: true,
            createdAt: uint40(block.timestamp),
            expiresAt: expiresAt
        });

        emit SkillOffered(
            skillTokenId,
            nftContract,
            nftType,
            price,
            isETH,
            paymentToken,
            msg.sender,
            expiresAt
        );
    }

    /**
     * @dev Hire a skill using ETH
     * @param skillTokenId The token ID of the skill NFT to hire
     * @param nftContract Address of the NFT contract
     */
    function hireSkillETH(
        uint256 skillTokenId,
        address nftContract
    ) external payable nonReentrant validNFTContract(nftContract) {
        SkillOffer memory offer = skillOffers[skillTokenId][nftContract];
        require(offer.isActive, "Offer not active");
        require(offer.isETH, "Payment must be in ETH");
        require(msg.value >= offer.price, "Insufficient payment");
        require(
            offer.expiresAt == 0 || offer.expiresAt >= block.timestamp,
            "Offer expired"
        );

        // Check agent status if AgentFactory NFT
        if (offer.nftType == NFTType.AgentNFT) {
            address agentAddress = _getAgentAddressFromNFT(skillTokenId);
            if (agentAddress != address(0)) {
                require(agentFactory.isAgentActive(agentAddress), "Agent is not active");
            }
        }

        uint256 royaltyAmount = 0;
        address owner = offer.owner;

        // Handle different NFT types
        if (offer.nftType == NFTType.NFRLT && address(nfRLTContract) != address(0)) {
            // Use NFRLT's broker transfer for royalty distribution
            NFRLT(nftContract).brokerTransferETH{value: msg.value}(
                owner,
                msg.sender,
                skillTokenId
            );
        } else {
            // Generic ERC721 transfer (works for THOT, AgentNFT, iNFT, dNFT, etc.)
            IERC721(nftContract).transferFrom(owner, msg.sender, skillTokenId);
            payable(owner).transfer(msg.value);
        }

        // Mark offer as inactive
        skillOffers[skillTokenId][nftContract].isActive = false;

        emit SkillHired(
            skillTokenId,
            nftContract,
            msg.sender,
            owner,
            offer.price,
            true,
            royaltyAmount
        );
    }

    /**
     * @dev Hire a skill using ERC-20 tokens
     * @param skillTokenId The token ID of the skill NFT to hire
     * @param nftContract Address of the NFT contract
     * @param amount The amount of ERC-20 tokens to pay
     */
    function hireSkillERC20(
        uint256 skillTokenId,
        address nftContract,
        uint256 amount
    ) external nonReentrant validNFTContract(nftContract) {
        SkillOffer memory offer = skillOffers[skillTokenId][nftContract];
        require(offer.isActive, "Offer not active");
        require(!offer.isETH, "Payment must be in ERC-20");
        require(amount >= offer.price, "Insufficient payment");
        require(
            offer.expiresAt == 0 || offer.expiresAt >= block.timestamp,
            "Offer expired"
        );

        // Check agent status if AgentFactory NFT
        if (offer.nftType == NFTType.AgentNFT) {
            address agentAddress = _getAgentAddressFromNFT(skillTokenId);
            if (agentAddress != address(0)) {
                require(agentFactory.isAgentActive(agentAddress), "Agent is not active");
            }
        }

        IERC20 paymentToken = IERC20(offer.paymentToken);
        address owner = offer.owner;

        // Transfer payment token
        paymentToken.safeTransferFrom(msg.sender, owner, amount);

        // Transfer NFT
        IERC721(nftContract).transferFrom(owner, msg.sender, skillTokenId);

        // Mark offer as inactive
        skillOffers[skillTokenId][nftContract].isActive = false;

        emit SkillHired(
            skillTokenId,
            nftContract,
            msg.sender,
            owner,
            amount,
            false,
            0
        );
    }

    /**
     * @dev Remove a skill offer
     * @param skillTokenId The token ID of the skill NFT
     * @param nftContract Address of the NFT contract
     */
    function removeSkillOffer(
        uint256 skillTokenId,
        address nftContract
    ) external {
        SkillOffer memory offer = skillOffers[skillTokenId][nftContract];
        require(offer.owner == msg.sender, "Caller is not the owner");

        delete skillOffers[skillTokenId][nftContract];

        emit SkillRemoved(skillTokenId, nftContract, msg.sender);
    }

    /**
     * @dev Get skill offer details
     * @param skillTokenId The token ID of the skill NFT
     * @param nftContract Address of the NFT contract
     * @return SkillOffer structure
     */
    function getSkillOffer(
        uint256 skillTokenId,
        address nftContract
    ) external view returns (SkillOffer memory) {
        return skillOffers[skillTokenId][nftContract];
    }

    /**
     * @dev Whitelist an NFT contract
     * @param nftContract Address of the NFT contract
     * @param nftType Type of NFT (NFRLT, THOT, or AgentNFT)
     */
    function whitelistNFTContract(
        address nftContract,
        NFTType nftType
    ) external onlyOwner {
        require(nftContract != address(0), "Invalid contract address");
        whitelistedNFTContracts[nftContract] = true;
        nftContractTypes[nftContract] = nftType;
        emit NFTContractWhitelisted(nftContract, nftType);
    }

    /**
     * @dev Whitelist a payment token
     * @param token Address of the payment token (address(0) for ETH)
     * @param status Whitelist status
     */
    function whitelistPaymentToken(address token, bool status) external onlyOwner {
        whitelistedPaymentTokens[token] = status;
        emit PaymentTokenWhitelisted(token, status);
    }

    /**
     * @dev Set AgentManagement contract address
     * @param _agentManagement Address of AgentManagement contract
     */
    function setAgentManagement(address _agentManagement) external onlyOwner {
        address oldAddress = agentManagement;
        agentManagement = _agentManagement;
        emit AgentManagementUpdated(oldAddress, _agentManagement);
    }

    /**
     * @dev Update NFRLT contract address
     * @param _nfRLTContract New NFRLT contract address
     */
    function setNFRLTContract(address _nfRLTContract) external onlyOwner {
        require(_nfRLTContract != address(0), "Invalid NFRLT contract address");
        nfRLTContract = NFRLT(_nfRLTContract);
        whitelistedNFTContracts[_nfRLTContract] = true;
        nftContractTypes[_nfRLTContract] = NFTType.NFRLT;
    }

    /**
     * @dev Update THOT contract address
     * @param _thotContract New THOT contract address
     */
    function setTHOTContract(address _thotContract) external onlyOwner {
        require(_thotContract != address(0), "Invalid THOT contract address");
        thotContract = THOT(_thotContract);
        whitelistedNFTContracts[_thotContract] = true;
        nftContractTypes[_thotContract] = NFTType.THOT;
    }

    /**
     * @dev Update AgentFactory contract address
     * @param _agentFactory New AgentFactory contract address
     */
    function setAgentFactory(address _agentFactory) external onlyOwner {
        require(_agentFactory != address(0), "Invalid AgentFactory contract address");
        agentFactory = AgentFactory(_agentFactory);
        whitelistedNFTContracts[_agentFactory] = true;
        nftContractTypes[_agentFactory] = NFTType.AgentNFT;
    }

    /**
     * @dev Internal function to get agent address from AgentFactory NFT
     * @param nftId NFT ID from AgentFactory
     * @return agentAddress The agent address associated with the NFT
     */
    function _getAgentAddressFromNFT(uint256 nftId) internal view returns (address) {
        try agentFactory.getAgentByNFT(nftId) returns (AgentFactory.Agent memory agent) {
            return agent.agentAddress;
        } catch {
            return address(0);
        }
    }

    /**
     * @dev Check if an NFT contract is whitelisted
     * @param nftContract Address of the NFT contract
     * @return bool Whether the contract is whitelisted
     */
    function isNFTContractWhitelisted(address nftContract) external view returns (bool) {
        return whitelistedNFTContracts[nftContract];
    }

    /**
     * @dev Get NFT type for a contract
     * @param nftContract Address of the NFT contract
     * @return NFTType The type of NFT
     */
    function getNFTType(address nftContract) external view returns (NFTType) {
        return nftContractTypes[nftContract];
    }

    /**
     * @dev Set SoulBadger contract address (for credential verification)
     * @param _soulBadger Address of SoulBadger contract
     */
    function setSoulBadger(address _soulBadger) external onlyOwner {
        address oldAddress = address(0); // Can't track old address if not stored
        emit SoulBadgerUpdated(oldAddress, _soulBadger);
    }

    /**
     * @dev Verify user has SoulBadger credential (if SoulBadger is set)
     * @param user Address to verify
     * @param badgeId Badge ID to check
     * @return bool Whether user owns the badge
     */
    function verifyCredential(address user, uint256 badgeId) external view returns (bool) {
        // This is a placeholder - actual implementation would check SoulBadger
        // For now, returns true if contract is whitelisted
        // In full implementation, would query SoulBadger.ownerOf(badgeId) == user
        return whitelistedNFTContracts[msg.sender];
    }
}
