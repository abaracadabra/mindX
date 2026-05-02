// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721}        from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721URIStorage} from "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title  THOT v1 — memory-anchoring primitive
/// @notice Adds a Memory struct + pillar-gated `commit()` to the original
///         Transferable Hyper-Optimized Tensor token. Each commit anchors a
///         single reasoning step on chain via three orthogonal hashes:
///           - rootHash      : 0G Storage merkle root (the encrypted blob)
///           - chatID        : 0G Compute TEE attestation hash (verifiable
///                             inference from ZG-Res-Key)
///           - parentRootHash: optional pointer to the parent commit, forming
///                             an episodic-memory DAG
///
///         **Agnostic-module**: any agent framework can register its reasoning
///         loop as a pillar by being granted PILLAR_ROLE and then calling
///         `commit()`. mindX wires its BDI / RAGE / Mastermind pillars; other
///         frameworks (OpenClaw, NanoClaw, …) wire their own reasoning loops
///         the same way. THOT does not depend on any specific framework.
///
///         **Idempotency**: tokenId = uint256(keccak256(author, rootHash,
///         chatID)). A repeat commit of the same triple returns the existing
///         token id without minting again.
///
///         **Horizontal scaling**: any number of pillars can commit
///         concurrently to the same registry — each (author, rootHash,
///         chatID) triple is independent. **Vertical scaling**: parent-DAG
///         depth is unbounded; commits compose into arbitrarily deep
///         episodic memory chains.
///
///         The legacy `daio/contracts/THOT/core/THOT.sol` is preserved
///         untouched as prior art (Apr 11 2026 timestamps); v1 lives here.
contract THOT_v1 is ERC721, ERC721URIStorage, AccessControl {
    bytes32 public constant PILLAR_ROLE = keccak256("PILLAR_ROLE");

    /// @notice One reasoning step anchored on chain.
    struct Memory {
        bytes32 rootHash;        // 0G Storage merkle root
        bytes32 chatID;          // 0G Compute TEE attestation
        address provider;        // 0G provider that served the inference
        bytes32 parentRootHash;  // 0 if root memory; else parent rootHash
        uint40  timestamp;
        address pillar;          // who anchored
        address author;          // logical agent on whose behalf
    }

    mapping(uint256 => Memory) public memories;

    event MemoryCommitted(
        uint256 indexed tokenId,
        address indexed pillar,
        address indexed author,
        bytes32 rootHash,
        bytes32 chatID,
        address provider,
        bytes32 parentRootHash
    );

    error ZeroBytes32();
    error ZeroAddress();
    error UnknownParent(bytes32 parentRootHash);

    constructor(string memory name_, string memory symbol_, address admin)
        ERC721(name_, symbol_)
    {
        if (admin == address(0)) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice Anchor a reasoning step. Returns the (existing or newly-minted)
    ///         token id. Idempotent — re-committing the same triple is a no-op
    ///         that returns the original tokenId.
    /// @param author          logical agent identity (typically the pillar's
    ///                        own caller; the pillar contract supplies this)
    /// @param rootHash        0G Storage merkle root of the encrypted memory blob
    /// @param chatID          0G Compute TEE attestation hash (ZG-Res-Key)
    /// @param provider        the 0G provider address that served the inference
    /// @param parentRootHash  0 if this is a root memory; else the parent's rootHash
    function commit(
        address author,
        bytes32 rootHash,
        bytes32 chatID,
        address provider,
        bytes32 parentRootHash
    )
        external
        onlyRole(PILLAR_ROLE)
        returns (uint256 tokenId)
    {
        if (author == address(0))     revert ZeroAddress();
        if (rootHash == bytes32(0))   revert ZeroBytes32();
        if (chatID == bytes32(0))     revert ZeroBytes32();

        tokenId = uint256(keccak256(abi.encodePacked(author, rootHash, chatID)));

        // Idempotent — return existing tokenId without re-minting.
        if (_ownerOf(tokenId) != address(0)) {
            return tokenId;
        }

        // Validate parent — must be a known commit (or zero for root).
        if (parentRootHash != bytes32(0)) {
            // Parent exists if there's any memory whose rootHash matches.
            // Cheap check: require the parent commit was made by *some*
            // pillar previously. We don't enforce same-author lineage.
            if (!_parentExists(parentRootHash)) {
                revert UnknownParent(parentRootHash);
            }
        }

        memories[tokenId] = Memory({
            rootHash:       rootHash,
            chatID:         chatID,
            provider:       provider,
            parentRootHash: parentRootHash,
            timestamp:      uint40(block.timestamp),
            pillar:         msg.sender,
            author:         author
        });

        _safeMint(author, tokenId);

        emit MemoryCommitted(
            tokenId, msg.sender, author,
            rootHash, chatID, provider, parentRootHash
        );
    }

    /// @notice True if any commit has stored `rootHash`. Tracked via index.
    function _parentExists(bytes32 rootHash) internal view returns (bool) {
        return rootIndex[rootHash] != 0;
    }

    /// rootHash → tokenId of the FIRST commit that used that rootHash.
    /// Subsequent commits with the same rootHash but different chatID are
    /// allowed (and get their own tokenId), but parent lookups resolve to
    /// the canonical first one.
    mapping(bytes32 => uint256) public rootIndex;

    /// @notice Return the canonical tokenId for a given rootHash, if any.
    function tokenOfRoot(bytes32 rootHash) external view returns (uint256) {
        return rootIndex[rootHash];
    }

    // -- Required overrides ------------------------------------------------

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
        return super.supportsInterface(interfaceId);
    }

    /// @dev Override _update so we can populate `rootIndex` on mint without
    ///      duplicating bookkeeping in `commit()`.
    function _update(address to, uint256 tokenId, address auth)
        internal override(ERC721)
        returns (address)
    {
        address from = _ownerOf(tokenId);
        address result = super._update(to, tokenId, auth);
        if (from == address(0) && to != address(0)) {
            // Mint path — record the first time this rootHash was seen.
            bytes32 root = memories[tokenId].rootHash;
            if (rootIndex[root] == 0) {
                rootIndex[root] = tokenId;
            }
        }
        return result;
    }
}
