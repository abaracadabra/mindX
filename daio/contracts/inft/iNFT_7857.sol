// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Burnable.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";

/// @title  iNFT_7857
/// @notice ERC-7857 Intelligent NFT for the mindX ecosystem.
///         Encrypted intelligence + persistent memory live in 0G Storage
///         (or any content-addressed store). The merkle root is anchored
///         on chain; the AES-256 key is sealed for the current owner and
///         re-sealed on transfer via an oracle-signed handoff.
///
///         Designed for inclusion in:
///           - mindX           (agnostic agentic infrastructure)
///           - AgenticPlace    (skill marketplace; offerOnAgenticPlace hook)
///           - BANKON          (encrypted credential vault; bankonVault binding)
///
/// @dev    Standards-aligned variant. The prior-art iNFT.sol (Apr 11 2026
///         commits fff941a7 / 468de468 / f07b025a) is preserved untouched
///         in the same directory.
interface IERC7857 {
    /* ───── Events ─────────────────────────────────────────────────── */
    event AgentMinted(uint256 indexed tokenId, bytes32 indexed contentRoot, uint32 dimensions, address indexed owner);
    event MetadataUpdated(uint256 indexed tokenId, bytes32 newRoot, string newURI);
    event SealedKeyRotated(uint256 indexed tokenId, address indexed newOwner, bytes32 newSealedKeyHash);
    event UsageAuthorized(uint256 indexed tokenId, address indexed executor, uint256 permissions, uint64 expiresAt, address indexed grantor);
    event UsageRevoked(uint256 indexed tokenId, address indexed executor, address indexed revoker);
    event AgentCloned(uint256 indexed parentTokenId, uint256 indexed childTokenId, address indexed cloner);
    event AgentBurned(uint256 indexed tokenId, address indexed burner);
    event OracleUpdated(address indexed oldOracle, address indexed newOracle);
    event AgentIdBound(uint256 indexed tokenId, bytes32 indexed agentIdHash, string agentId);
    event AgenticPlaceListed(uint256 indexed tokenId, address indexed marketplace, uint256 price, bool isETH, address paymentToken);
    event BankonVaultBound(uint256 indexed tokenId, address indexed vault, bytes32 vaultRef);
    event CloneFeeUpdated(uint256 oldFeeWei, uint256 newFeeWei);
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);

    /* ───── ERC-7857 core ─────────────────────────────────────────── */
    function transferWithSealedKey(
        address from,
        address to,
        uint256 tokenId,
        bytes calldata sealedKey,
        bytes calldata oracleProof
    ) external;

    function cloneAgent(
        uint256 tokenId,
        address to,
        bytes calldata sealedKey,
        bytes calldata oracleProof
    ) external payable returns (uint256 childId);

    function authorizeUsage(uint256 tokenId, address executor, uint256 permissions, uint64 expiresAt) external;

    function revokeUsage(uint256 tokenId, address executor) external;
}

contract iNFT_7857 is
    ERC721,
    ERC721URIStorage,
    ERC721Burnable,
    ERC2981,
    AccessControl,
    Pausable,
    ReentrancyGuard,
    EIP712,
    IERC7857
{
    using ECDSA for bytes32;

    /* ───── Roles ─────────────────────────────────────────────────── */
    bytes32 public constant MINTER_ROLE   = keccak256("MINTER_ROLE");
    bytes32 public constant ORACLE_ROLE   = keccak256("ORACLE_ROLE");
    bytes32 public constant PAUSER_ROLE   = keccak256("PAUSER_ROLE");
    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");

    /* ───── Errors ────────────────────────────────────────────────── */
    error TransferRequiresSealedKey();   // standard transfer attempted; must use transferWithSealedKey
    error InvalidDimension(uint32 d);
    error ZeroAddress();
    error ZeroBytes32();
    error EmptyString();
    error StringTooLong(uint256 len);
    error ContentRootAlreadyMinted(bytes32 root);
    error TokenDoesNotExist(uint256 tokenId);
    error NotAuthorized(address caller);
    error BadOracleProof();
    error ExpiryInPast(uint64 expiry);
    error CloneFeeUnderpaid(uint256 sent, uint256 required);
    error AgentIdAlreadyBound(uint256 tokenId);
    error TreasuryUnset();
    error EthTransferFailed();
    error WrongOracleSigner(address recovered, address expected);

    /* ───── Storage ───────────────────────────────────────────────── */
    struct IntelligencePayload {
        bytes32 contentRoot;       // 0G Storage merkle root or IPFS-CID-as-bytes32
        string  storageURI;        // gateway hint, e.g. "0g://galileo/<root>" or "ipfs://<cid>"
        bytes32 metadataRoot;      // unencrypted metadata root (separate manifest)
        uint32  dimensions;        // THOT dimension — one of the 11 supported
        uint8   parallelUnits;
        uint40  mintedAt;
        bytes32 sealedKeyHash;     // hash of the AES-256 key sealed for the current owner
        bool    verified;
    }

    struct UsageGrant {
        uint256 permissions;       // bitmap interpreted off-chain
        uint64  expiresAt;
        address grantor;
    }

    /// EIP-712 typehashes — domain-separated to prevent cross-protocol replay
    bytes32 public constant SEALED_KEY_TYPEHASH = keccak256(
        "SealedKeyHandoff(uint256 tokenId,address from,address to,bytes32 contentRoot,bytes32 newSealedKeyHash,uint256 nonce)"
    );
    bytes32 public constant CLONE_TYPEHASH = keccak256(
        "AgentClone(uint256 parentTokenId,address to,bytes32 contentRoot,bytes32 newSealedKeyHash,uint256 nonce)"
    );

    uint256 public constant MAX_URI_LENGTH      = 2048;
    uint256 public constant MAX_AGENTID_LENGTH  = 64;
    uint96  public constant MAX_ROYALTY_BPS     = 2500;   // 25% hard cap
    uint16  public constant MAX_THOT_DIMENSIONS = 11;     // for off-chain enumeration

    address public oracle;             // ECDSA signer trusted to authorize re-encryption
    address public treasury;           // receives clone fees
    uint256 public cloneFeeWei;        // payment required per clone (0 = free)
    uint256 private _nextTokenId;

    mapping(uint256 => IntelligencePayload) private _payload;
    mapping(uint256 => mapping(address => UsageGrant)) private _grants;
    mapping(bytes32 => bool) private _rootEverUsed;       // includes burned tokens — roots are one-shot

    // Per-token oracle nonces (replay protection for sealed-key handoffs)
    mapping(uint256 => uint256) private _oracleNonce;

    // mindX/AgenticPlace/BANKON binding
    mapping(uint256 => string)  private _agentId;
    mapping(uint256 => bytes32) private _agentIdHash;
    mapping(uint256 => address) public  agenticPlaceFor;     // last marketplace this token was listed on
    mapping(uint256 => address) public  bankonVaultFor;      // BANKON vault holding the sealed key escrow
    mapping(uint256 => bytes32) public  bankonVaultRef;      // opaque ref the vault uses to look up the key

    // Clone tracking
    mapping(uint256 => uint256) public cloneCount;
    mapping(uint256 => uint256) public clonedFrom;           // 0 if root, else parent tokenId

    // Transfer gate — set true while we're inside transferWithSealedKey or cloneAgent
    bool private _gateOpen;

    /* ───── Constructor ───────────────────────────────────────────── */
    constructor(
        string memory name_,
        string memory symbol_,
        address admin,
        address royaltyReceiver,
        uint96  royaltyFeeBps,
        address oracle_,
        address treasury_,
        uint256 cloneFeeWei_
    )
        ERC721(name_, symbol_)
        EIP712(name_, "1")
    {
        if (admin == address(0)) revert ZeroAddress();
        if (royaltyReceiver == address(0)) revert ZeroAddress();
        if (royaltyFeeBps > MAX_ROYALTY_BPS) revert ZeroBytes32(); // reuse error sparingly
        _setDefaultRoyalty(royaltyReceiver, royaltyFeeBps);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE,        admin);
        _grantRole(PAUSER_ROLE,        admin);
        _grantRole(TREASURER_ROLE,     admin);
        if (oracle_ != address(0)) {
            oracle = oracle_;
            _grantRole(ORACLE_ROLE, oracle_);
            emit OracleUpdated(address(0), oracle_);
        }
        if (treasury_ != address(0)) {
            treasury = treasury_;
            emit TreasuryUpdated(address(0), treasury_);
        }
        cloneFeeWei = cloneFeeWei_;
        emit CloneFeeUpdated(0, cloneFeeWei_);
    }

    /* ───── Dimension whitelist (mirrors iNFT.sol prior art) ──────── */
    function _isValidDimension(uint32 d) internal pure returns (bool) {
        return (
            d == 8       || d == 64      || d == 256     ||
            d == 512     || d == 768     || d == 1024    ||
            d == 2048    || d == 4096    || d == 8192    ||
            d == 65536   || d == 1048576
        );
    }

    function validDimensions() external pure returns (uint32[11] memory dims) {
        dims = [
            uint32(8), 64, 256, 512, 768, 1024, 2048, 4096, 8192, 65536, 1048576
        ];
    }

    /* ───── Admin ─────────────────────────────────────────────────── */
    function setOracle(address newOracle) external onlyRole(DEFAULT_ADMIN_ROLE) {
        address old = oracle;
        if (old != address(0)) _revokeRole(ORACLE_ROLE, old);
        oracle = newOracle;
        if (newOracle != address(0)) _grantRole(ORACLE_ROLE, newOracle);
        emit OracleUpdated(old, newOracle);
    }

    function setTreasury(address newTreasury) external onlyRole(TREASURER_ROLE) {
        address old = treasury;
        treasury = newTreasury;
        emit TreasuryUpdated(old, newTreasury);
    }

    function setCloneFee(uint256 newFeeWei) external onlyRole(TREASURER_ROLE) {
        uint256 old = cloneFeeWei;
        cloneFeeWei = newFeeWei;
        emit CloneFeeUpdated(old, newFeeWei);
    }

    function setDefaultRoyalty(address receiver, uint96 feeBps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (receiver == address(0)) revert ZeroAddress();
        if (feeBps > MAX_ROYALTY_BPS) revert StringTooLong(feeBps);
        _setDefaultRoyalty(receiver, feeBps);
    }

    function setTokenRoyalty(uint256 tokenId, address receiver, uint96 feeBps)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (_ownerOf(tokenId) == address(0)) revert TokenDoesNotExist(tokenId);
        if (receiver == address(0)) revert ZeroAddress();
        if (feeBps > MAX_ROYALTY_BPS) revert StringTooLong(feeBps);
        _setTokenRoyalty(tokenId, receiver, feeBps);
    }

    function pause()   external onlyRole(PAUSER_ROLE) { _pause(); }
    function unpause() external onlyRole(PAUSER_ROLE) { _unpause(); }

    /* ───── Mint ──────────────────────────────────────────────────── */
    /// @notice Mint a new iNFT-7857. Restricted to MINTER_ROLE so AgenticPlace,
    ///         BANKON vault, IDManagerAgent etc. can be granted minting rights.
    function mintAgent(
        address to,
        bytes32 contentRoot,
        string calldata storageURI,
        bytes32 metadataRoot,
        uint32  dimensions,
        uint8   parallelUnits,
        bytes32 sealedKeyHash,
        string  calldata tokenURI_
    )
        external
        whenNotPaused
        onlyRole(MINTER_ROLE)
        nonReentrant
        returns (uint256 tokenId)
    {
        if (to == address(0))                         revert ZeroAddress();
        if (contentRoot == bytes32(0))                revert ZeroBytes32();
        if (sealedKeyHash == bytes32(0))              revert ZeroBytes32();
        if (parallelUnits == 0)                       revert InvalidDimension(uint32(parallelUnits));
        if (!_isValidDimension(dimensions))           revert InvalidDimension(dimensions);
        if (_rootEverUsed[contentRoot])               revert ContentRootAlreadyMinted(contentRoot);
        uint256 storageURIlen = bytes(storageURI).length;
        if (storageURIlen == 0)                       revert EmptyString();
        if (storageURIlen > MAX_URI_LENGTH)           revert StringTooLong(storageURIlen);
        uint256 tokenURIlen   = bytes(tokenURI_).length;
        if (tokenURIlen > MAX_URI_LENGTH)             revert StringTooLong(tokenURIlen);

        unchecked { tokenId = ++_nextTokenId; }

        _payload[tokenId] = IntelligencePayload({
            contentRoot:   contentRoot,
            storageURI:    storageURI,
            metadataRoot:  metadataRoot,
            dimensions:    dimensions,
            parallelUnits: parallelUnits,
            mintedAt:      uint40(block.timestamp),
            sealedKeyHash: sealedKeyHash,
            verified:      true
        });

        // Mark root used AFTER state was set but BEFORE _safeMint, so a revert
        // in onERC721Received doesn't leave us with the payload but no token.
        _rootEverUsed[contentRoot] = true;

        _gateOpen = true;
        _safeMint(to, tokenId);
        _gateOpen = false;

        if (tokenURIlen > 0) {
            _setTokenURI(tokenId, tokenURI_);
        }
        emit AgentMinted(tokenId, contentRoot, dimensions, to);
    }

    /* ───── Transfer with sealed key (ERC-7857) ───────────────────── */
    /// @notice Transfer a token AND deliver a re-sealed key to the new owner.
    ///         The oracle ECDSA-signs (tokenId, from, to, contentRoot,
    ///         newSealedKeyHash, nonce) under EIP-712 to prove the sealed key
    ///         was generated in a TEE for `to`. `sealedKey` is the off-chain
    ///         ciphertext (we only store its hash).
    function transferWithSealedKey(
        address from,
        address to,
        uint256 tokenId,
        bytes calldata sealedKey,
        bytes calldata oracleProof
    )
        external
        override
        whenNotPaused
        nonReentrant
    {
        if (to == address(0)) revert ZeroAddress();
        address tokenOwner = _ownerOf(tokenId);
        if (tokenOwner == address(0)) revert TokenDoesNotExist(tokenId);
        if (tokenOwner != from)       revert NotAuthorized(from);
        if (!_isAuthorized(tokenOwner, msg.sender, tokenId)) revert NotAuthorized(msg.sender);

        bytes32 newSealedKeyHash = keccak256(sealedKey);
        uint256 nonce = _oracleNonce[tokenId]++;
        _verifyOracleSignature(
            keccak256(abi.encode(
                SEALED_KEY_TYPEHASH,
                tokenId,
                from,
                to,
                _payload[tokenId].contentRoot,
                newSealedKeyHash,
                nonce
            )),
            oracleProof
        );

        _payload[tokenId].sealedKeyHash = newSealedKeyHash;
        // Clear all delegations on transfer — new owner starts clean.
        // Per-executor revocations not iterable here; off-chain must read events.
        _gateOpen = true;
        _transfer(from, to, tokenId);
        _gateOpen = false;

        emit SealedKeyRotated(tokenId, to, newSealedKeyHash);
        emit MetadataUpdated(tokenId, _payload[tokenId].contentRoot, _payload[tokenId].storageURI);
    }

    /* ───── Clone (ERC-7857) ──────────────────────────────────────── */
    function cloneAgent(
        uint256 tokenId,
        address to,
        bytes calldata sealedKey,
        bytes calldata oracleProof
    )
        external
        payable
        override
        whenNotPaused
        nonReentrant
        returns (uint256 childId)
    {
        if (to == address(0)) revert ZeroAddress();
        address tokenOwner = _ownerOf(tokenId);
        if (tokenOwner == address(0)) revert TokenDoesNotExist(tokenId);
        if (!_isAuthorized(tokenOwner, msg.sender, tokenId)) revert NotAuthorized(msg.sender);
        if (msg.value < cloneFeeWei) revert CloneFeeUnderpaid(msg.value, cloneFeeWei);

        bytes32 newSealedKeyHash = keccak256(sealedKey);
        uint256 nonce = _oracleNonce[tokenId]++;
        IntelligencePayload memory parent = _payload[tokenId];

        _verifyOracleSignature(
            keccak256(abi.encode(
                CLONE_TYPEHASH,
                tokenId,
                to,
                parent.contentRoot,
                newSealedKeyHash,
                nonce
            )),
            oracleProof
        );

        unchecked { childId = ++_nextTokenId; }

        _payload[childId] = IntelligencePayload({
            contentRoot:   parent.contentRoot,
            storageURI:    parent.storageURI,
            metadataRoot:  parent.metadataRoot,
            dimensions:    parent.dimensions,
            parallelUnits: parent.parallelUnits,
            mintedAt:      uint40(block.timestamp),
            sealedKeyHash: newSealedKeyHash,
            verified:      true
        });
        clonedFrom[childId] = tokenId;
        unchecked { ++cloneCount[tokenId]; }

        // Pay the clone fee to treasury (best-effort revert on send failure)
        if (msg.value > 0) {
            if (treasury == address(0)) revert TreasuryUnset();
            (bool ok,) = treasury.call{value: msg.value}("");
            if (!ok) revert EthTransferFailed();
        }

        _gateOpen = true;
        _safeMint(to, childId);
        _gateOpen = false;

        emit AgentCloned(tokenId, childId, msg.sender);
    }

    /* ───── Usage authorization ───────────────────────────────────── */
    function authorizeUsage(uint256 tokenId, address executor, uint256 permissions, uint64 expiresAt)
        external
        override
        whenNotPaused
    {
        if (executor == address(0)) revert ZeroAddress();
        address tokenOwner = _ownerOf(tokenId);
        if (tokenOwner == address(0)) revert TokenDoesNotExist(tokenId);
        if (!_isAuthorized(tokenOwner, msg.sender, tokenId)) revert NotAuthorized(msg.sender);
        if (expiresAt <= block.timestamp) revert ExpiryInPast(expiresAt);

        _grants[tokenId][executor] = UsageGrant({
            permissions: permissions,
            expiresAt:   expiresAt,
            grantor:     msg.sender
        });
        emit UsageAuthorized(tokenId, executor, permissions, expiresAt, msg.sender);
    }

    function revokeUsage(uint256 tokenId, address executor) external override whenNotPaused {
        address tokenOwner = _ownerOf(tokenId);
        if (tokenOwner == address(0)) revert TokenDoesNotExist(tokenId);
        if (!_isAuthorized(tokenOwner, msg.sender, tokenId)) revert NotAuthorized(msg.sender);
        delete _grants[tokenId][executor];
        emit UsageRevoked(tokenId, executor, msg.sender);
    }

    function isUsageAuthorized(uint256 tokenId, address executor) external view returns (bool) {
        if (executor == address(0)) return false;
        UsageGrant memory g = _grants[tokenId][executor];
        return (g.expiresAt >= block.timestamp && g.expiresAt != 0);
    }

    function getUsageGrant(uint256 tokenId, address executor) external view returns (UsageGrant memory) {
        return _grants[tokenId][executor];
    }

    /* ───── Burn (ERC721Burnable + state cleanup) ─────────────────── */
    function burn(uint256 tokenId) public override(ERC721Burnable) nonReentrant {
        address tokenOwner = _ownerOf(tokenId);
        if (tokenOwner == address(0)) revert TokenDoesNotExist(tokenId);
        if (!_isAuthorized(tokenOwner, msg.sender, tokenId)) revert NotAuthorized(msg.sender);

        _gateOpen = true;
        super.burn(tokenId);
        _gateOpen = false;

        // Cleanup intelligence payload + grants storage. Root remains in
        // _rootEverUsed to prevent silent re-mint with leaked content.
        delete _payload[tokenId];
        delete agenticPlaceFor[tokenId];
        delete bankonVaultFor[tokenId];
        delete bankonVaultRef[tokenId];
        // _grants per-executor cannot be iterated from chain; off-chain must
        // observe UsageRevoked events to know they are stale post-burn.

        emit AgentBurned(tokenId, msg.sender);
    }

    /* ───── mindX agent_id binding ────────────────────────────────── */
    /// @notice Bind this iNFT to a mindX agent identifier. One-shot per token.
    function bindAgentId(uint256 tokenId, string calldata agentId) external {
        address tokenOwner = _ownerOf(tokenId);
        if (tokenOwner == address(0)) revert TokenDoesNotExist(tokenId);
        if (!_isAuthorized(tokenOwner, msg.sender, tokenId)) revert NotAuthorized(msg.sender);
        if (_agentIdHash[tokenId] != bytes32(0)) revert AgentIdAlreadyBound(tokenId);
        uint256 len = bytes(agentId).length;
        if (len == 0)                  revert EmptyString();
        if (len > MAX_AGENTID_LENGTH)  revert StringTooLong(len);

        bytes32 h = keccak256(bytes(agentId));
        _agentId[tokenId]     = agentId;
        _agentIdHash[tokenId] = h;
        emit AgentIdBound(tokenId, h, agentId);
    }

    function getAgentId(uint256 tokenId) external view returns (string memory) {
        return _agentId[tokenId];
    }

    function getAgentIdHash(uint256 tokenId) external view returns (bytes32) {
        return _agentIdHash[tokenId];
    }

    /* ───── AgenticPlace marketplace hook ─────────────────────────── */
    /// @notice Record a marketplace listing. The actual offerSkill() call
    ///         happens via the marketplace contract directly; this stores
    ///         the binding so off-chain readers can correlate.
    function offerOnAgenticPlace(
        uint256 tokenId,
        address marketplace,
        uint256 price,
        bool    isETH,
        address paymentToken
    ) external whenNotPaused {
        address tokenOwner = _ownerOf(tokenId);
        if (tokenOwner == address(0)) revert TokenDoesNotExist(tokenId);
        if (!_isAuthorized(tokenOwner, msg.sender, tokenId)) revert NotAuthorized(msg.sender);
        if (marketplace == address(0)) revert ZeroAddress();
        agenticPlaceFor[tokenId] = marketplace;
        emit AgenticPlaceListed(tokenId, marketplace, price, isETH, paymentToken);
    }

    /* ───── BANKON vault binding ──────────────────────────────────── */
    /// @notice Register that the sealed key for this token is escrowed in a
    ///         BANKON vault (encrypted under the owner's BANKON identity).
    ///         `vaultRef` is opaque — vault uses it to look up the key.
    function bindBankonVault(uint256 tokenId, address vault, bytes32 vaultRef) external whenNotPaused {
        address tokenOwner = _ownerOf(tokenId);
        if (tokenOwner == address(0)) revert TokenDoesNotExist(tokenId);
        if (!_isAuthorized(tokenOwner, msg.sender, tokenId)) revert NotAuthorized(msg.sender);
        if (vault == address(0)) revert ZeroAddress();
        bankonVaultFor[tokenId] = vault;
        bankonVaultRef[tokenId] = vaultRef;
        emit BankonVaultBound(tokenId, vault, vaultRef);
    }

    /* ───── Read helpers ──────────────────────────────────────────── */
    function getPayload(uint256 tokenId) external view returns (IntelligencePayload memory) {
        if (_ownerOf(tokenId) == address(0)) revert TokenDoesNotExist(tokenId);
        return _payload[tokenId];
    }

    function totalMinted() external view returns (uint256) {
        return _nextTokenId;
    }

    function exists(uint256 tokenId) external view returns (bool) {
        return _ownerOf(tokenId) != address(0);
    }

    function oracleNonce(uint256 tokenId) external view returns (uint256) {
        return _oracleNonce[tokenId];
    }

    function isRootUsed(bytes32 root) external view returns (bool) {
        return _rootEverUsed[root];
    }

    /// @notice Build the EIP-712 digest a caller would need to sign for a
    ///         sealed-key handoff. Useful for off-chain testing + UI.
    function sealedKeyDigest(
        uint256 tokenId,
        address from,
        address to,
        bytes32 contentRoot,
        bytes32 newSealedKeyHash,
        uint256 nonce
    ) external view returns (bytes32) {
        return _hashTypedDataV4(keccak256(abi.encode(
            SEALED_KEY_TYPEHASH, tokenId, from, to, contentRoot, newSealedKeyHash, nonce
        )));
    }

    function cloneDigest(
        uint256 parentTokenId,
        address to,
        bytes32 contentRoot,
        bytes32 newSealedKeyHash,
        uint256 nonce
    ) external view returns (bytes32) {
        return _hashTypedDataV4(keccak256(abi.encode(
            CLONE_TYPEHASH, parentTokenId, to, contentRoot, newSealedKeyHash, nonce
        )));
    }

    /* ───── Internal: oracle signature verification ───────────────── */
    function _verifyOracleSignature(bytes32 structHash, bytes calldata sig) internal view {
        if (oracle == address(0)) {
            // No oracle configured = any signature accepted (dev mode). Production
            // deployments MUST set an oracle in the constructor or via setOracle.
            return;
        }
        bytes32 digest = _hashTypedDataV4(structHash);
        address recovered = digest.recover(sig);
        if (recovered != oracle) revert WrongOracleSigner(recovered, oracle);
    }

    /* ───── Transfer gate ─────────────────────────────────────────── */
    /// @dev Enforce that NON-mint NON-burn transfers can only happen through
    ///      transferWithSealedKey() or cloneAgent(). This is the heart of the
    ///      ERC-7857 security model.
    function _update(address to, uint256 tokenId, address auth)
        internal
        override(ERC721)
        whenNotPaused
        returns (address)
    {
        address from = _ownerOf(tokenId);
        bool isMint = (from == address(0));
        bool isBurn = (to == address(0));
        if (!isMint && !isBurn && !_gateOpen) {
            revert TransferRequiresSealedKey();
        }
        return super._update(to, tokenId, auth);
    }

    /* ───── Required overrides ────────────────────────────────────── */
    function tokenURI(uint256 tokenId)
        public view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public view
        override(ERC721, ERC721URIStorage, ERC2981, AccessControl)
        returns (bool)
    {
        return interfaceId == type(IERC7857).interfaceId
            || super.supportsInterface(interfaceId);
    }

    /// @notice Receive function for direct ETH funding (clone fees route via
    ///         the cloneAgent payable path; this is a fallback for treasury top-up).
    receive() external payable {
        if (treasury == address(0)) {
            // accumulate in the contract; only TREASURER_ROLE can sweep
        }
    }

    /// @notice Sweep stuck ETH to the configured treasury (operator escape hatch).
    function sweepEth(uint256 amount) external onlyRole(TREASURER_ROLE) {
        if (treasury == address(0)) revert TreasuryUnset();
        (bool ok,) = treasury.call{value: amount}("");
        if (!ok) revert EthTransferFailed();
    }
}
