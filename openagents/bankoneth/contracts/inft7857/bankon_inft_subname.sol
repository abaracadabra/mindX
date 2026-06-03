// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Source: docs/…ERC-7857 iNFT and ERC-6551 TBA Integration.md (pragma relaxed to ^0.8.24).
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC1155Holder} from "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";
import {ERC2981} from "@openzeppelin/contracts/token/common/ERC2981.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";
import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";

import {
    IERC7857, IERC7857Metadata, IERC7857DataVerifier,
    IERC5192, IERC4906, IERC7572,
    IntelligentData, TransferValidityProof, TransferValidityProofOutput,
    INameWrapper, bankon_fuses
} from "./bankon_interfaces.sol";

/// @title bankon_inft_subname — Mode A: Unified iNFT-ENS
/// @notice One canonical ERC-721 token that also implements ERC-7857, ERC-5192,
///         ERC-2981, ERC-4906, ERC-7572. Backs itself with the ENS NameWrapper
///         ERC-1155 subname (held by this contract). The ERC-6551 TBA derived
///         from (chainId, this, tokenId) is the agent's wallet.
/// @custom:security-contact security@bankon.eth
contract bankon_inft_subname is
    ERC721, ERC1155Holder, ERC2981, Ownable, ReentrancyGuard,
    IERC7857, IERC7857Metadata, IERC5192, IERC4906, IERC7572
{
    error NotOwnerOrApproved();
    error TokenSoulbound(uint256 tokenId);
    error EmptyData();
    error ZeroAddress();
    error ProofCountMismatch();
    error OldHashMismatch();
    error AccessAssistantMismatch();
    error NotMinter();
    error LabelTaken(string label);

    struct TokenData {
        address[] authorizedUsers;
        IntelligentData[] iDatas;
        bytes32 parentNode;
        bytes32 ensNode;
        bool soulbound;
    }
    mapping(uint256 => TokenData) private _tokens;
    mapping(address => address) public delegateAccessOf;
    mapping(bytes32 => bool) private _ensNodeIssued;

    uint256 public nextTokenId = 1;
    string  public storageInfo;       // e.g. "0g-storage://" or "lighthouse://ipfs"
    string  private _contractURI;
    address public minter;            // registrar contract
    INameWrapper public immutable nameWrapper;
    IERC7857DataVerifier public verifierContract;

    modifier onlyMinter() { if (msg.sender != minter) revert NotMinter(); _; }

    constructor(
        string memory name_,
        string memory symbol_,
        string memory storageInfo_,
        string memory contractURI_,
        address admin_,
        address minter_,
        INameWrapper nameWrapper_,
        IERC7857DataVerifier verifier_,
        address royaltyReceiver,
        uint96 royaltyBps
    ) ERC721(name_, symbol_) Ownable(admin_) {
        if (address(nameWrapper_) == address(0) || address(verifier_) == address(0)) revert ZeroAddress();
        storageInfo = storageInfo_;
        _contractURI = contractURI_;
        minter = minter_;
        nameWrapper = nameWrapper_;
        verifierContract = verifier_;
        _setDefaultRoyalty(royaltyReceiver, royaltyBps);
    }

    /* ─────────────────────── MINT ─────────────────────── */

    /// @notice Mint a unified iNFT-ENS token. Called by the registrar only.
    function mintUnified(
        string calldata label,
        address to,
        bytes32 parentNode,
        IntelligentData[] calldata iDatas,
        bool soulbound,
        uint64 expiry
    ) external onlyMinter nonReentrant returns (uint256 tokenId, bytes32 ensNode) {
        if (to == address(0)) revert ZeroAddress();
        if (iDatas.length == 0) revert EmptyData();

        uint32 fuses = soulbound
            ? bankon_fuses.BANKON_SOULBOUND
            : bankon_fuses.BANKON_EMANCIPATED_TRANSFERABLE;

        ensNode = nameWrapper.setSubnodeOwner(parentNode, label, address(this), fuses, expiry);
        if (_ensNodeIssued[ensNode]) revert LabelTaken(label);
        _ensNodeIssued[ensNode] = true;

        tokenId = nextTokenId++;
        TokenData storage t = _tokens[tokenId];
        t.parentNode = parentNode;
        t.ensNode = ensNode;
        t.soulbound = soulbound;
        for (uint256 i; i < iDatas.length; ++i) t.iDatas.push(iDatas[i]);

        _safeMint(to, tokenId);
        if (soulbound) emit Locked(tokenId);
    }

    /* ─── IERC7857Metadata name/symbol (shared with ERC721) ─── */
    function name() public view override(ERC721, IERC7857Metadata) returns (string memory) { return ERC721.name(); }
    function symbol() public view override(ERC721, IERC7857Metadata) returns (string memory) { return ERC721.symbol(); }

    /* ─────────────────────── ERC-7857 ─────────────────────── */

    function verifier() external view returns (IERC7857DataVerifier) { return verifierContract; }

    function iTransfer(
        address to,
        uint256 tokenId,
        TransferValidityProof[] calldata proofs
    ) external override nonReentrant {
        if (_tokens[tokenId].soulbound) revert TokenSoulbound(tokenId);
        if (!_isOwnerOrApproved(msg.sender, tokenId)) revert NotOwnerOrApproved();
        _doTransfer(ownerOf(tokenId), to, tokenId, proofs);
    }

    function iClone(
        address to,
        uint256 tokenId,
        TransferValidityProof[] calldata proofs
    ) external override nonReentrant returns (uint256 newTokenId) {
        if (!_isOwnerOrApproved(msg.sender, tokenId)) revert NotOwnerOrApproved();
        address from = ownerOf(tokenId);
        TokenData storage src = _tokens[tokenId];
        (, IntelligentData[] memory newDatas) = _proofCheck(from, to, tokenId, proofs);

        newTokenId = nextTokenId++;
        TokenData storage dst = _tokens[newTokenId];
        dst.parentNode = src.parentNode;
        dst.ensNode = bytes32(0); // clones do not carry the ENS subname
        dst.soulbound = false;
        for (uint256 i; i < newDatas.length; ++i) dst.iDatas.push(newDatas[i]);
        _safeMint(to, newTokenId);
        emit Cloned(tokenId, newTokenId, from, to);
    }

    function authorizeUsage(uint256 tokenId, address user) external override {
        if (!_isOwnerOrApproved(msg.sender, tokenId)) revert NotOwnerOrApproved();
        _tokens[tokenId].authorizedUsers.push(user);
        emit Authorization(msg.sender, user, tokenId);
    }

    function revokeAuthorization(uint256 tokenId, address user) external override {
        if (!_isOwnerOrApproved(msg.sender, tokenId)) revert NotOwnerOrApproved();
        address[] storage arr = _tokens[tokenId].authorizedUsers;
        for (uint256 i; i < arr.length; ++i) {
            if (arr[i] == user) { arr[i] = arr[arr.length - 1]; arr.pop(); break; }
        }
        emit AuthorizationRevoked(msg.sender, user, tokenId);
    }

    function delegateAccess(address assistant) external override {
        delegateAccessOf[msg.sender] = assistant;
        emit DelegateAccess(msg.sender, assistant);
    }

    function authorizedUsersOf(uint256 tokenId) external view returns (address[] memory) {
        return _tokens[tokenId].authorizedUsers;
    }

    function getDelegateAccess(address user) external view returns (address) {
        return delegateAccessOf[user];
    }

    /* ───── proof helpers ───── */
    function _proofCheck(
        address from, address to, uint256 tokenId, TransferValidityProof[] calldata proofs
    ) internal returns (bytes[] memory sealedKeys, IntelligentData[] memory newDatas) {
        if (to == address(0)) revert ZeroAddress();
        TokenData storage t = _tokens[tokenId];
        if (proofs.length != t.iDatas.length) revert ProofCountMismatch();

        TransferValidityProofOutput[] memory outs = verifierContract.verifyTransferValidity(proofs);
        sealedKeys = new bytes[](outs.length);
        newDatas   = new IntelligentData[](outs.length);
        for (uint256 i; i < outs.length; ++i) {
            if (outs[i].oldDataHash != t.iDatas[i].dataHash) revert OldHashMismatch();
            if (outs[i].accessAssistant != delegateAccessOf[to] && outs[i].accessAssistant != to)
                revert AccessAssistantMismatch();
            sealedKeys[i] = outs[i].sealedKey;
            newDatas[i] = IntelligentData({
                dataDescription: t.iDatas[i].dataDescription,
                dataHash: outs[i].newDataHash
            });
        }
        from; // silence unused
    }

    function _doTransfer(
        address from, address to, uint256 tokenId, TransferValidityProof[] calldata proofs
    ) internal {
        (bytes[] memory sealedKeys, IntelligentData[] memory newDatas) =
            _proofCheck(from, to, tokenId, proofs);
        TokenData storage t = _tokens[tokenId];
        delete t.iDatas;
        for (uint256 i; i < newDatas.length; ++i) t.iDatas.push(newDatas[i]);

        // 6551 TBA follows automatically: tokenId+contract is constant, ERC-721 owner is the source of truth.
        _safeTransfer(from, to, tokenId, "");
        emit Transferred(tokenId, from, to);
        emit PublishedSealedKey(to, tokenId, sealedKeys);
        emit MetadataUpdate(tokenId);
    }

    /* ─────────────────────── ERC-721 hook: soulbound ─────────────────────── */
    function _update(address to, uint256 tokenId, address auth)
        internal override returns (address from)
    {
        from = super._update(to, tokenId, auth);
        // mint (from==0) and burn (to==0) allowed; only owner→owner transfer is gated
        if (from != address(0) && to != address(0)) {
            if (_tokens[tokenId].soulbound) revert TokenSoulbound(tokenId);
            emit MetadataUpdate(tokenId);
        }
    }

    /* ─────────────────────── ERC-5192 ─────────────────────── */
    function locked(uint256 tokenId) external view override returns (bool) {
        return _tokens[tokenId].soulbound;
    }

    /* ─────────────────────── ERC-7572 ─────────────────────── */
    function contractURI() external view override returns (string memory) { return _contractURI; }
    function setContractURI(string calldata newURI) external onlyOwner {
        _contractURI = newURI;
        emit ContractURIUpdated();
    }

    /* ─────────────────────── ERC-721 Metadata ─────────────────────── */
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        return string.concat(storageInfo, "/", Strings.toString(tokenId), ".json");
    }

    function intelligentDataOf(uint256 tokenId) external view returns (IntelligentData[] memory) {
        return _tokens[tokenId].iDatas;
    }

    function ensNodeOf(uint256 tokenId) external view returns (bytes32) { return _tokens[tokenId].ensNode; }

    /* ─────────────────────── admin ─────────────────────── */
    function setMinter(address m) external onlyOwner { minter = m; }
    function setVerifier(IERC7857DataVerifier v) external onlyOwner { verifierContract = v; }
    function setStorageInfo(string calldata s) external onlyOwner { storageInfo = s; emit ContractURIUpdated(); }
    function bumpMetadata(uint256 tokenId) external onlyOwner { emit MetadataUpdate(tokenId); }
    function setDefaultRoyalty(address r, uint96 bps) external onlyOwner { _setDefaultRoyalty(r, bps); }
    function setTokenRoyalty(uint256 id, address r, uint96 bps) external onlyOwner { _setTokenRoyalty(id, r, bps); }

    /* ─────────────────────── introspection ─────────────────────── */
    function supportsInterface(bytes4 id)
        public view virtual override(ERC721, ERC1155Holder, ERC2981) returns (bool)
    {
        return id == type(IERC7857).interfaceId
            || id == type(IERC7857Metadata).interfaceId
            || id == type(IERC5192).interfaceId          // 0xb45a3c0e
            || id == bytes4(0x49064906)                  // ERC-4906
            || id == type(IERC7572).interfaceId
            || super.supportsInterface(id);
    }

    function _isOwnerOrApproved(address spender, uint256 tokenId) internal view returns (bool) {
        address o = _ownerOf(tokenId);
        return o == spender || getApproved(tokenId) == spender || isApprovedForAll(o, spender);
    }
}
