// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Source: docs/BANKON ENS Subname Registrar_ ERC-7857 iNFT and ERC-6551 TBA
// Integration.md (Definitive Deliverable). Pragma relaxed ^0.8.26 → ^0.8.24 to
// match the bankoneth toolchain. Modular by design: every third-party interface
// lives here so the iNFT / oracle / registrar / TBA modules import one file.
pragma solidity ^0.8.24;

/// @title bankon_interfaces — Canonical interface bundle for BANKON iNFT + TBA stack
/// @notice Canonical ERC-7857 (TEE/ZKP), ERC-6551, ERC-5192, ERC-4906, ERC-7572,
///         ERC-2981 (via OZ), and the ENS NameWrapper subset + fuse library.

/* ─────────────────────────── ERC-7857 ─────────────────────────── */
enum OracleType { TEE, ZKP }

struct AccessProof {
    bytes32 oldDataHash;
    bytes32 newDataHash;
    bytes nonce;
    bytes encryptedPubKey;
    bytes proof;
}

struct OwnershipProof {
    OracleType oracleType;
    bytes32 oldDataHash;
    bytes32 newDataHash;
    bytes sealedKey;
    bytes encryptedPubKey;
    bytes nonce;
    bytes proof;
}

struct TransferValidityProof {
    AccessProof accessProof;
    OwnershipProof ownershipProof;
}

struct TransferValidityProofOutput {
    bytes32 oldDataHash;
    bytes32 newDataHash;
    bytes sealedKey;
    bytes encryptedPubKey;
    bytes wantedKey;
    address accessAssistant;
    bytes accessProofNonce;
    bytes ownershipProofNonce;
}

struct IntelligentData {
    string dataDescription;
    bytes32 dataHash;
}

interface IERC7857DataVerifier {
    function verifyTransferValidity(TransferValidityProof[] calldata proofs)
        external returns (TransferValidityProofOutput[] memory);
}

interface IERC7857Metadata {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function intelligentDataOf(uint256 tokenId) external view returns (IntelligentData[] memory);
}

interface IERC7857 {
    event Transferred(uint256 tokenId, address indexed from, address indexed to);
    event Cloned(uint256 indexed tokenId, uint256 indexed newTokenId, address from, address to);
    event PublishedSealedKey(address indexed to, uint256 indexed tokenId, bytes[] sealedKeys);
    event Authorization(address indexed from, address indexed to, uint256 indexed tokenId);
    event AuthorizationRevoked(address indexed from, address indexed to, uint256 indexed tokenId);
    event DelegateAccess(address indexed user, address indexed assistant);

    function verifier() external view returns (IERC7857DataVerifier);
    function iTransfer(address to, uint256 tokenId, TransferValidityProof[] calldata proofs) external;
    function iClone(address to, uint256 tokenId, TransferValidityProof[] calldata proofs)
        external returns (uint256 newTokenId);
    function authorizeUsage(uint256 tokenId, address user) external;
    function revokeAuthorization(uint256 tokenId, address user) external;
    function delegateAccess(address assistant) external;
    function authorizedUsersOf(uint256 tokenId) external view returns (address[] memory);
    function getDelegateAccess(address user) external view returns (address);
}

/* ─────────────────────────── ERC-6551 ─────────────────────────── */
interface IERC6551Registry {
    event ERC6551AccountCreated(
        address account, address indexed implementation, bytes32 salt,
        uint256 chainId, address indexed tokenContract, uint256 indexed tokenId
    );
    error AccountCreationFailed();

    function createAccount(
        address implementation, bytes32 salt, uint256 chainId,
        address tokenContract, uint256 tokenId
    ) external returns (address);

    function account(
        address implementation, bytes32 salt, uint256 chainId,
        address tokenContract, uint256 tokenId
    ) external view returns (address);
}

interface IERC6551Account {
    receive() external payable;
    function token() external view returns (uint256 chainId, address tokenContract, uint256 tokenId);
    function state() external view returns (uint256);
    function isValidSigner(address signer, bytes calldata context) external view returns (bytes4 magicValue);
}

interface IERC6551Executable {
    function execute(address to, uint256 value, bytes calldata data, uint8 operation)
        external payable returns (bytes memory);
}

/* ─────────────────────────── ERC-5192 ─────────────────────────── */
interface IERC5192 {
    event Locked(uint256 tokenId);
    event Unlocked(uint256 tokenId);
    function locked(uint256 tokenId) external view returns (bool);
}

/* ─────────────────────────── ERC-4906 ─────────────────────────── */
interface IERC4906 {
    event MetadataUpdate(uint256 _tokenId);
    event BatchMetadataUpdate(uint256 _fromTokenId, uint256 _toTokenId);
}

/* ─────────────────────────── ERC-7572 ─────────────────────────── */
interface IERC7572 {
    function contractURI() external view returns (string memory);
    event ContractURIUpdated();
}

/* ─────────────────────────── ENS NameWrapper subset ─────────────────────────── */
interface INameWrapper {
    function setSubnodeOwner(
        bytes32 parentNode, string calldata label, address owner,
        uint32 fuses, uint64 expiry
    ) external returns (bytes32 node);

    function setSubnodeRecord(
        bytes32 parentNode, string calldata label, address owner, address resolver,
        uint64 ttl, uint32 fuses, uint64 expiry
    ) external returns (bytes32 node);

    function ownerOf(uint256 id) external view returns (address);
    function safeTransferFrom(address from, address to, uint256 id, uint256 amount, bytes calldata data) external;
    function getData(uint256 id) external view returns (address owner, uint32 fuses, uint64 expiry);
    function allFusesBurned(bytes32 node, uint32 fuseMask) external view returns (bool);
    function setApprovalForAll(address operator, bool approved) external;
}

/* ─────────────────────────── ENS fuse constants ─────────────────────────── */
library bankon_fuses {
    uint32 internal constant CANNOT_UNWRAP            = 1;
    uint32 internal constant CANNOT_BURN_FUSES        = 2;
    uint32 internal constant CANNOT_TRANSFER          = 4;
    uint32 internal constant CANNOT_SET_RESOLVER      = 8;
    uint32 internal constant CANNOT_SET_TTL           = 16;
    uint32 internal constant CANNOT_CREATE_SUBDOMAIN  = 32;
    uint32 internal constant CANNOT_APPROVE           = 64;
    uint32 internal constant PARENT_CANNOT_CONTROL    = uint32(1) << 16;
    uint32 internal constant IS_DOT_ETH               = uint32(1) << 17;
    uint32 internal constant CAN_EXTEND_EXPIRY        = uint32(1) << 18;

    /// @notice Canonical BANKON soulbound subname fuse mask
    uint32 internal constant BANKON_SOULBOUND =
        CAN_EXTEND_EXPIRY | PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CANNOT_TRANSFER;

    /// @notice Standard emancipated, transferable BANKON subname mask
    uint32 internal constant BANKON_EMANCIPATED_TRANSFERABLE =
        CAN_EXTEND_EXPIRY | PARENT_CANNOT_CONTROL | CANNOT_UNWRAP;
}
