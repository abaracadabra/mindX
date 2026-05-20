// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / AgenticPlace — Apache 2.0
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {ITHOTCommitmentRegistry} from "../interfaces/ITHOTCommitmentRegistry.sol";
import {THOTLib} from "../libraries/THOTLib.sol";

/**
 * @title THOTCommitmentRegistry
 * @notice Canonical, append-only-ish registry for the cryptographic
 *         substrate of the THOT family.
 *
 *         Append-only-ish, not append-only: a CENSURA_ROLE can revoke
 *         a previously-registered root (see revoke()). Revocation does
 *         not delete the registration; it sets a flag that downstream
 *         consumers (iNFT_7857.transferWithSealedKey via
 *         ITHOTCommitmentRegistry.isRevoked) honour to block trust
 *         flows tied to that root.
 *
 *         Issuers commit a THOT4096 root with its CID, ternary head, and
 *         optional metadata. Smaller prefix variants are registered as
 *         cryptographically derived from the parent (Matryoshka
 *         prefix-binding theorem via THOTLib.verifyPrefix). Diagonal
 *         edges (distillation / projection / federation) form a DAG.
 *
 *         Adapted from `docs/operations/thotconsiderations.zip` →
 *         `THOTRegistry.sol`, with security patches:
 *           - AccessControl (DEFAULT_ADMIN_ROLE + CENSURA_ROLE)
 *           - revoke() + isRevoked()
 *           - recordEdge access control + no-overwrite
 *           - registerPrefix length validation via THOTLib helper
 *           - ITHOTCommitmentRegistry interface conformance
 *
 *         Coexists with the discovery `ITHOTRegistry`
 *         (THOT/interfaces/ITHOTRegistry.sol) — different concerns.
 */
contract THOTCommitmentRegistry is ITHOTCommitmentRegistry, AccessControl {
    using THOTLib for bytes32;

    // -----------------------------------------------------------------
    //                            Roles
    // -----------------------------------------------------------------

    /// @notice Holds the right to revoke a registered THOT4096 root.
    ///         Operationally this is the `Censura` 2-of-3 sub-quorum of
    ///         the BONAFIDE substrate (see THOTS.md §E).
    bytes32 public constant CENSURA_ROLE = keccak256("CENSURA_ROLE");

    // -----------------------------------------------------------------
    //                            Types
    // -----------------------------------------------------------------

    struct THOT4096Record {
        bytes32 root;             // Canonical Merkle root.
        bytes32 ternaryHead;      // Dedicated THOT8 sub-leaf hash.
        uint256 ternaryHeadIndex; // Position of the ternary head leaf.
        address issuer;           // Bound to msg.sender at issuance.
        uint64  timestamp;        // Block.timestamp at issuance.
        string  cid;              // ipfs:// or 0g:// CID for the payload.
        string  metadataURI;      // Off-chain metadata (training run, etc.).
        bool    exists;
    }

    struct PrefixRecord {
        bytes32 parentRoot;
        bytes32 prefixRoot;
        uint16  prefixDim;        // One of {768, 1024, 2048}. THOT8 lives
                                  // in the parent record's ternaryHead.
        uint64  timestamp;
        bool    exists;
    }

    enum EdgeKind { Distillation, Projection, Federation }

    struct DiagonalEdge {
        bytes32 fromRoot;
        bytes32 toRoot;
        EdgeKind kind;
        bytes32 attestationHash;
        address recorder;
        uint64  timestamp;
    }

    // -----------------------------------------------------------------
    //                            Storage
    // -----------------------------------------------------------------

    /// parentRoot => THOT4096 record
    mapping(bytes32 => THOT4096Record) public parents;

    /// keccak256(parentRoot ‖ prefixDim) => PrefixRecord
    mapping(bytes32 => PrefixRecord) public prefixes;

    /// edgeId => DiagonalEdge (edgeId = keccak256(fromRoot ‖ toRoot ‖ kind ‖ recorder))
    mapping(bytes32 => DiagonalEdge) public edges;

    /// Authorized issuers (gate-managed).
    mapping(address => bool) public authorizedIssuers;

    /// Revoked roots — see revoke().
    mapping(bytes32 => bool) public revokedRoots;
    mapping(bytes32 => string) public revocationReasons;

    /// The BANKON identity gate (an AlgoIDNFT-bound EOA / multisig). Holds
    /// the right to grant/revoke issuer status. Distinct from
    /// DEFAULT_ADMIN_ROLE (which holds the right to grant CENSURA_ROLE).
    address public bankonIdentityGate;

    // -----------------------------------------------------------------
    //                            Events
    // -----------------------------------------------------------------

    event THOT4096Issued(
        bytes32 indexed root,
        address indexed issuer,
        bytes32 ternaryHead,
        string  cid
    );

    event PrefixRegistered(
        bytes32 indexed parentRoot,
        uint16  indexed prefixDim,
        bytes32 prefixRoot
    );

    event DiagonalEdgeRecorded(
        bytes32 indexed fromRoot,
        bytes32 indexed toRoot,
        EdgeKind kind,
        bytes32  attestationHash,
        address  recorder
    );

    event IssuerAuthorized(address indexed issuer);
    event IssuerRevoked(address indexed issuer);

    event THOTRevoked(bytes32 indexed root, string reason);
    event THOTUnrevoked(bytes32 indexed root);

    event BankonGateUpdated(address indexed oldGate, address indexed newGate);

    // -----------------------------------------------------------------
    //                            Errors
    // -----------------------------------------------------------------

    error NotAuthorizedIssuer(address sender);
    error THOTAlreadyExists(bytes32 root);
    error THOTNotFound(bytes32 root);
    error THOTRevokedAtIssuance(bytes32 root);
    error PrefixAlreadyRegistered(bytes32 parentRoot, uint16 prefixDim);
    error PrefixVerificationFailed();
    error InvalidPrefixDimension(uint16 dim);
    error NotIdentityGate(address sender);
    error EdgeAlreadyRecorded(bytes32 edgeId);
    error ZeroAddress();

    // -----------------------------------------------------------------
    //                          Construction
    // -----------------------------------------------------------------

    /// @param identityGate The BANKON identity gate (EOA or multisig that
    ///                     authorizes issuers).
    /// @param admin        Holds DEFAULT_ADMIN_ROLE + CENSURA_ROLE at
    ///                     deployment. In production this is a 3-of-5
    ///                     multisig.
    constructor(address identityGate, address admin) {
        if (identityGate == address(0)) revert ZeroAddress();
        if (admin == address(0)) revert ZeroAddress();
        bankonIdentityGate = identityGate;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CENSURA_ROLE, admin);
        emit BankonGateUpdated(address(0), identityGate);
    }

    modifier onlyGate() {
        if (msg.sender != bankonIdentityGate) revert NotIdentityGate(msg.sender);
        _;
    }

    modifier onlyAuthorized() {
        if (!authorizedIssuers[msg.sender]) revert NotAuthorizedIssuer(msg.sender);
        _;
    }

    // -----------------------------------------------------------------
    //                       Gate management
    // -----------------------------------------------------------------

    /// @notice Rotate the identity gate. Reserved for DEFAULT_ADMIN_ROLE
    ///         because if the gate is lost or compromised the recovery
    ///         path is multisig-driven.
    function setBankonIdentityGate(address newGate)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (newGate == address(0)) revert ZeroAddress();
        address old = bankonIdentityGate;
        bankonIdentityGate = newGate;
        emit BankonGateUpdated(old, newGate);
    }

    // -----------------------------------------------------------------
    //                       Issuer authorization
    // -----------------------------------------------------------------

    function authorizeIssuer(address issuer) external onlyGate {
        if (issuer == address(0)) revert ZeroAddress();
        authorizedIssuers[issuer] = true;
        emit IssuerAuthorized(issuer);
    }

    function revokeIssuer(address issuer) external onlyGate {
        authorizedIssuers[issuer] = false;
        emit IssuerRevoked(issuer);
    }

    // -----------------------------------------------------------------
    //                       Canonical issuance
    // -----------------------------------------------------------------

    /**
     * @notice Issue a new canonical THOT4096.
     * @param  root              Merkle root (computed off-chain from 64 leaves).
     * @param  ternaryHead       Dedicated THOT8 sub-leaf hash.
     * @param  ternaryHeadIndex  Leaf position of the ternary head.
     * @param  cid               IPFS/0G CID for the encrypted payload.
     * @param  metadataURI       Off-chain metadata pointer.
     */
    function issueTHOT4096(
        bytes32 root,
        bytes32 ternaryHead,
        uint256 ternaryHeadIndex,
        string calldata cid,
        string calldata metadataURI
    ) external onlyAuthorized {
        if (parents[root].exists) revert THOTAlreadyExists(root);
        if (revokedRoots[root]) revert THOTRevokedAtIssuance(root);

        parents[root] = THOT4096Record({
            root: root,
            ternaryHead: ternaryHead,
            ternaryHeadIndex: ternaryHeadIndex,
            issuer: msg.sender,
            timestamp: uint64(block.timestamp),
            cid: cid,
            metadataURI: metadataURI,
            exists: true
        });

        emit THOT4096Issued(root, msg.sender, ternaryHead, cid);
    }

    // -----------------------------------------------------------------
    //                       Revocation (Censura)
    // -----------------------------------------------------------------

    /**
     * @notice Revoke a registered THOT4096 root. Operational use:
     *         backdoor discovered, training-data licensing violation,
     *         constitutional violation per BONAFIDE substrate.
     *
     *         Revocation does not erase the registration; it flips a
     *         flag that downstream consumers honour. iNFT_7857.transfer
     *         path checks isRevoked() and refuses to move sealed keys.
     */
    function revoke(bytes32 root, string calldata reason)
        external
        onlyRole(CENSURA_ROLE)
    {
        if (!parents[root].exists) revert THOTNotFound(root);
        revokedRoots[root] = true;
        revocationReasons[root] = reason;
        emit THOTRevoked(root, reason);
    }

    /// @notice Lift a revocation. Useful for false-positive cases or
    ///         where the constitutional review concludes the root may
    ///         remain in service.
    function unrevoke(bytes32 root) external onlyRole(CENSURA_ROLE) {
        if (!parents[root].exists) revert THOTNotFound(root);
        revokedRoots[root] = false;
        delete revocationReasons[root];
        emit THOTUnrevoked(root);
    }

    // -----------------------------------------------------------------
    //                ITHOTCommitmentRegistry views
    // -----------------------------------------------------------------

    function isRegistered(bytes32 root) external view returns (bool) {
        return parents[root].exists;
    }

    function isRevoked(bytes32 root) external view returns (bool) {
        return revokedRoots[root];
    }

    function ternaryHeadOf(bytes32 root) external view returns (bytes32) {
        return parents[root].ternaryHead;
    }

    function getPrefix(bytes32 parentRoot, uint16 prefixDim)
        external
        view
        returns (bytes32 prefixRoot, bool exists)
    {
        PrefixRecord storage p = prefixes[
            keccak256(abi.encodePacked(parentRoot, prefixDim))
        ];
        return (p.prefixRoot, p.exists);
    }

    /// @notice Original lookup retained for compatibility with downstream
    ///         tooling that wants the full PrefixRecord struct.
    function getPrefixRecord(bytes32 parentRoot, uint16 prefixDim)
        external
        view
        returns (PrefixRecord memory)
    {
        return prefixes[keccak256(abi.encodePacked(parentRoot, prefixDim))];
    }

    // -----------------------------------------------------------------
    //                Matryoshka prefix registration
    // -----------------------------------------------------------------

    /**
     * @notice Register a prefix variant of an existing THOT4096.
     * @dev    Verifies the asserted prefixRoot is the canonical Matryoshka
     *         prefix of parentRoot at dim via THOTLib.verifyPrefix.
     *         Reverts on any mismatch.
     */
    function registerPrefix(
        bytes32 parentRoot,
        uint16 prefixDim,
        bytes32 prefixRoot,
        bytes32[] calldata prefixLeaves,
        bytes32[] calldata coWitnessLeaves,
        bytes32[] calldata rightSiblings
    ) external {
        if (!parents[parentRoot].exists) revert THOTNotFound(parentRoot);
        if (prefixDim != 768 && prefixDim != 1024 && prefixDim != 2048) {
            // THOT8 is registered via the parent's ternaryHead field, not here.
            revert InvalidPrefixDimension(prefixDim);
        }

        bytes32 key = keccak256(abi.encodePacked(parentRoot, prefixDim));
        if (prefixes[key].exists) revert PrefixAlreadyRegistered(parentRoot, prefixDim);

        // Cheap upfront length sanity (the library reasserts but we want
        // a friendly error before any memory copy).
        THOTLib.assertPrefixLeavesLength(prefixDim, prefixLeaves.length);

        // Copy calldata arrays to memory for the library call.
        bytes32[] memory leaves = new bytes32[](prefixLeaves.length);
        for (uint256 i = 0; i < prefixLeaves.length; i++) leaves[i] = prefixLeaves[i];

        bytes32[] memory coWit = new bytes32[](coWitnessLeaves.length);
        for (uint256 i = 0; i < coWitnessLeaves.length; i++) coWit[i] = coWitnessLeaves[i];

        bytes32[] memory siblings = new bytes32[](rightSiblings.length);
        for (uint256 i = 0; i < rightSiblings.length; i++) siblings[i] = rightSiblings[i];

        bool ok = THOTLib.verifyPrefix(parentRoot, prefixDim, prefixRoot, leaves, coWit, siblings);
        if (!ok) revert PrefixVerificationFailed();

        prefixes[key] = PrefixRecord({
            parentRoot: parentRoot,
            prefixRoot: prefixRoot,
            prefixDim:  prefixDim,
            timestamp:  uint64(block.timestamp),
            exists:     true
        });

        emit PrefixRegistered(parentRoot, prefixDim, prefixRoot);
    }

    // -----------------------------------------------------------------
    //                    Diagonal edge recording
    // -----------------------------------------------------------------

    /**
     * @notice Record a diagonal edge (distillation / projection / federation).
     *
     *         Authorized-only to keep the DAG spam-resistant. Duplicate
     *         edges from the same recorder with the same (from, to, kind)
     *         tuple are rejected — the recorder must use a fresh kind or
     *         a different recorder address to update an attestation.
     */
    function recordEdge(
        bytes32 fromRoot,
        bytes32 toRoot,
        EdgeKind kind,
        bytes32 attestationHash
    ) external onlyAuthorized returns (bytes32 edgeId) {
        if (!parents[fromRoot].exists) revert THOTNotFound(fromRoot);
        if (!parents[toRoot].exists)   revert THOTNotFound(toRoot);

        edgeId = keccak256(abi.encodePacked(fromRoot, toRoot, kind, msg.sender));
        if (edges[edgeId].timestamp != 0) revert EdgeAlreadyRecorded(edgeId);

        edges[edgeId] = DiagonalEdge({
            fromRoot: fromRoot,
            toRoot:   toRoot,
            kind:     kind,
            attestationHash: attestationHash,
            recorder: msg.sender,
            timestamp: uint64(block.timestamp)
        });

        emit DiagonalEdgeRecorded(fromRoot, toRoot, kind, attestationHash, msg.sender);
    }
}
