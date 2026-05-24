// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721}            from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721URIStorage}  from "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import {AccessControl}     from "@openzeppelin/contracts/access/AccessControl.sol";
import {ECDSA}             from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {EIP712}            from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";

/// @title  IAgentRegistry — minimal ERC-8004-aligned agent registration interface
/// @notice We publish our own interface ID rather than claim the in-flight
///         ERC-8004 spec — implementations of either standard can advertise this.
interface IAgentRegistry {
    function register(
        address owner,
        string calldata agentId,
        address linkedINFT_7857,
        bytes32 capabilityBitmap,
        string calldata attestationURI
    ) external returns (uint256 agentTokenId);

    function setCapabilities(uint256 agentTokenId, bytes32 newBitmap) external;

    function attest(
        uint256 agentTokenId,
        string calldata attestationURI,
        bytes calldata signature
    ) external;

    function getAgent(uint256 agentTokenId)
        external view
        returns (
            address owner,
            string memory agentId,
            address linkedINFT_7857,
            bytes32 capabilityBitmap,
            string memory attestationURI,
            uint256 attestorCount
        );
}

/// @title  AgentRegistry — agnostic ERC-8004-aligned agent identity & capability registry
/// @notice Sits above any agent token (iNFT_7857, plain ERC-721, none) and
///         records: owner address, human-readable agent_id, linked iNFT
///         (optional), capability bitmap (interpreted off-chain), and a
///         growing list of attestations (URI + signer).
///
///         **Agnostic-module statement**: any framework can register an
///         agent here. The registry does not assume mindX, AgenticPlace,
///         BANKON, or any specific cognition stack. It exposes one
///         interface (IAgentRegistry) and one EIP-712 domain.
///
///         **Roles**:
///           - DEFAULT_ADMIN_ROLE : grant/revoke other roles, set per-token
///                                  soulbound flag
///           - MINTER_ROLE        : may register on behalf of any owner.
///                                  Granted to BANKON registrar, iNFT_7857,
///                                  IDManagerAgent, etc. Without this role,
///                                  callers can only register themselves.
///           - ATTESTOR_ROLE      : may sign attestations that bind a URI to
///                                  an agent. Each attestation increments
///                                  attestorCount; the URI of the most
///                                  recent attestation is what `getAgent`
///                                  returns.
///
///         **Soulbound**: a per-token flag freezes transfers. Default false
///         (transferable). BANKON registrar typically sets soulbound=true
///         on bundled mints since the BANKON subname itself is soulbound.
contract AgentRegistry is ERC721, ERC721URIStorage, AccessControl, EIP712, IAgentRegistry {
    using ECDSA for bytes32;

    bytes32 public constant MINTER_ROLE   = keccak256("MINTER_ROLE");
    bytes32 public constant ATTESTOR_ROLE = keccak256("ATTESTOR_ROLE");

    bytes32 public constant ATTESTATION_TYPEHASH = keccak256(
        "Attestation(uint256 agentTokenId,string attestationURI,uint256 nonce)"
    );

    /// IAgentRegistry interface ID (minimal ERC-8004-aligned variant)
    bytes4 public constant IAGENT_REGISTRY_ID = type(IAgentRegistry).interfaceId;

    struct Agent {
        address owner;
        string  agentId;            // human-readable id, e.g. "ceo-mastermind"
        bytes32 agentIdHash;        // keccak256(bytes(agentId)) for indexer lookups
        address linkedINFT_7857;    // 0x0 if not linked
        bytes32 capabilityBitmap;   // interpreted off-chain
        string  attestationURI;     // most recent attestation URI
        uint256 attestorCount;      // how many distinct attestors signed
        bool    soulbound;          // if true, _update reverts non-mint/non-burn
    }

    mapping(uint256 => Agent) private _agents;
    mapping(bytes32 => uint256) public tokenOfAgentIdHash;
    mapping(uint256 => uint256) public attestNonce;
    /// agentTokenId → set of attestor addresses already counted
    mapping(uint256 => mapping(address => bool)) private _attested;

    uint256 private _nextId;

    /* ───── Events ────────────────────────────────────────────────── */
    event AgentRegistered(
        uint256 indexed agentTokenId,
        address indexed owner,
        bytes32 indexed agentIdHash,
        string  agentId,
        address linkedINFT_7857,
        bytes32 capabilityBitmap,
        string  attestationURI
    );
    event CapabilitiesUpdated(uint256 indexed agentTokenId, bytes32 newBitmap);
    event Attested(
        uint256 indexed agentTokenId,
        address indexed attestor,
        string  attestationURI,
        uint256 attestorCount
    );
    event SoulboundSet(uint256 indexed agentTokenId, bool soulbound);
    event LinkedINFTSet(uint256 indexed agentTokenId, address indexed inft);

    /* ───── Errors ────────────────────────────────────────────────── */
    error ZeroAddress();
    error EmptyAgentId();
    error AgentIdTooLong(uint256 len);
    error AgentIdAlreadyTaken(bytes32 hash);
    error TokenDoesNotExist(uint256 agentTokenId);
    error NotOwnerNorMinter(address caller);
    error NotAttestor(address caller);
    error BadAttestationSignature();
    error SoulboundCannotTransfer();

    constructor(
        string memory name_,
        string memory symbol_,
        address admin
    )
        ERC721(name_, symbol_)
        EIP712(name_, "1")
    {
        if (admin == address(0)) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /* ═══════════════════════════════════════════════════════════════ */
    /*  Register                                                        */
    /* ═══════════════════════════════════════════════════════════════ */

    /// @notice Register an agent. Caller is owner or MINTER_ROLE.
    function register(
        address owner,
        string calldata agentId,
        address linkedINFT_7857,
        bytes32 capabilityBitmap,
        string calldata attestationURI
    ) external override returns (uint256 agentTokenId) {
        if (owner == address(0)) revert ZeroAddress();
        if (msg.sender != owner && !hasRole(MINTER_ROLE, msg.sender)) {
            revert NotOwnerNorMinter(msg.sender);
        }
        uint256 len = bytes(agentId).length;
        if (len == 0) revert EmptyAgentId();
        if (len > 64) revert AgentIdTooLong(len);

        bytes32 h = keccak256(bytes(agentId));
        if (tokenOfAgentIdHash[h] != 0) revert AgentIdAlreadyTaken(h);

        unchecked { agentTokenId = ++_nextId; }
        _agents[agentTokenId] = Agent({
            owner:            owner,
            agentId:          agentId,
            agentIdHash:      h,
            linkedINFT_7857:  linkedINFT_7857,
            capabilityBitmap: capabilityBitmap,
            attestationURI:   attestationURI,
            attestorCount:    0,
            soulbound:        false
        });
        tokenOfAgentIdHash[h] = agentTokenId;
        _safeMint(owner, agentTokenId);

        emit AgentRegistered(
            agentTokenId, owner, h, agentId,
            linkedINFT_7857, capabilityBitmap, attestationURI
        );
    }

    /* ═══════════════════════════════════════════════════════════════ */
    /*  Update                                                          */
    /* ═══════════════════════════════════════════════════════════════ */

    function setCapabilities(uint256 agentTokenId, bytes32 newBitmap) external override {
        Agent storage a = _agents[agentTokenId];
        if (a.owner == address(0)) revert TokenDoesNotExist(agentTokenId);
        // Owner of the token is the source of truth for capability changes.
        address tokenOwner = _ownerOf(agentTokenId);
        if (tokenOwner != msg.sender) revert NotOwnerNorMinter(msg.sender);
        a.capabilityBitmap = newBitmap;
        emit CapabilitiesUpdated(agentTokenId, newBitmap);
    }

    function setLinkedINFT(uint256 agentTokenId, address inft) external {
        Agent storage a = _agents[agentTokenId];
        if (a.owner == address(0)) revert TokenDoesNotExist(agentTokenId);
        address tokenOwner = _ownerOf(agentTokenId);
        if (tokenOwner != msg.sender && !hasRole(MINTER_ROLE, msg.sender)) {
            revert NotOwnerNorMinter(msg.sender);
        }
        a.linkedINFT_7857 = inft;
        emit LinkedINFTSet(agentTokenId, inft);
    }

    function setSoulbound(uint256 agentTokenId, bool isSoulbound)
        external onlyRole(DEFAULT_ADMIN_ROLE)
    {
        Agent storage a = _agents[agentTokenId];
        if (a.owner == address(0)) revert TokenDoesNotExist(agentTokenId);
        a.soulbound = isSoulbound;
        emit SoulboundSet(agentTokenId, isSoulbound);
    }

    /* ═══════════════════════════════════════════════════════════════ */
    /*  Attest                                                          */
    /* ═══════════════════════════════════════════════════════════════ */

    /// @notice Record an attestation. The attestor (recovered from sig)
    ///         must hold ATTESTOR_ROLE. Each unique attestor counts once.
    function attest(
        uint256 agentTokenId,
        string calldata attestationURI,
        bytes calldata signature
    ) external override {
        Agent storage a = _agents[agentTokenId];
        if (a.owner == address(0)) revert TokenDoesNotExist(agentTokenId);

        uint256 nonce = attestNonce[agentTokenId]++;
        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(
            ATTESTATION_TYPEHASH,
            agentTokenId,
            keccak256(bytes(attestationURI)),
            nonce
        )));
        address attestor = digest.recover(signature);
        if (!hasRole(ATTESTOR_ROLE, attestor)) revert NotAttestor(attestor);

        if (!_attested[agentTokenId][attestor]) {
            _attested[agentTokenId][attestor] = true;
            unchecked { ++a.attestorCount; }
        }
        a.attestationURI = attestationURI;
        emit Attested(agentTokenId, attestor, attestationURI, a.attestorCount);
    }

    /// @notice Build the EIP-712 digest a caller would need to sign for an
    ///         attestation. Useful for off-chain testing + UI.
    function attestationDigest(
        uint256 agentTokenId,
        string calldata attestationURI,
        uint256 nonce
    ) external view returns (bytes32) {
        return _hashTypedDataV4(keccak256(abi.encode(
            ATTESTATION_TYPEHASH,
            agentTokenId,
            keccak256(bytes(attestationURI)),
            nonce
        )));
    }

    /* ═══════════════════════════════════════════════════════════════ */
    /*  Read                                                            */
    /* ═══════════════════════════════════════════════════════════════ */

    function getAgent(uint256 agentTokenId)
        external view override
        returns (
            address owner,
            string memory agentId,
            address linkedINFT_7857,
            bytes32 capabilityBitmap,
            string memory attestationURI,
            uint256 attestorCount
        )
    {
        Agent memory a = _agents[agentTokenId];
        if (a.owner == address(0)) revert TokenDoesNotExist(agentTokenId);
        return (
            _ownerOf(agentTokenId),    // current owner reflects transfers
            a.agentId,
            a.linkedINFT_7857,
            a.capabilityBitmap,
            a.attestationURI,
            a.attestorCount
        );
    }

    function isSoulbound(uint256 agentTokenId) external view returns (bool) {
        return _agents[agentTokenId].soulbound;
    }

    function totalAgents() external view returns (uint256) {
        return _nextId;
    }

    /* ═══════════════════════════════════════════════════════════════ */
    /*  Soulbound enforcement + required overrides                      */
    /* ═══════════════════════════════════════════════════════════════ */

    function _update(address to, uint256 tokenId, address auth)
        internal override(ERC721)
        returns (address)
    {
        address from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0) && _agents[tokenId].soulbound) {
            revert SoulboundCannotTransfer();
        }
        return super._update(to, tokenId, auth);
    }

    function tokenURI(uint256 tokenId)
        public view override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public view
        override(ERC721, ERC721URIStorage, AccessControl)
        returns (bool)
    {
        return interfaceId == IAGENT_REGISTRY_ID
            || super.supportsInterface(interfaceId);
    }
}
