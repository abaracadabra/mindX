// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Source: docs/…ERC-7857 iNFT and ERC-6551 TBA Integration.md (pragma relaxed to ^0.8.24).
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC2981} from "@openzeppelin/contracts/token/common/ERC2981.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

import {
    IERC7857, IERC7857Metadata, IERC7857DataVerifier,
    IERC5192, IERC4906,
    IntelligentData, TransferValidityProof, TransferValidityProofOutput,
    INameWrapper
} from "./bankon_interfaces.sol";

/// @title bankon_inft_extension — Mode B parallel iNFT bolted onto an existing NameWrapper subname
/// @notice Stores (ensNode) → tokenId and checks ownership against NameWrapper live on mint.
contract bankon_inft_extension is
    ERC721, ERC2981, Ownable, ReentrancyGuard,
    IERC7857, IERC7857Metadata, IERC5192, IERC4906
{
    error NotSubnameOwner();
    error TokenSoulbound(uint256 tokenId);
    error AlreadyExtended(bytes32 node);
    error EmptyData();
    error ZeroAddress();
    error NotOwnerOrApproved();
    error OldHashMismatch();

    struct ExtData {
        bytes32 ensNode;
        IntelligentData[] iDatas;
        address[] authorizedUsers;
        bool soulbound;
    }

    INameWrapper public immutable nameWrapper;
    IERC7857DataVerifier public verifierContract;
    uint256 public nextTokenId = 1;
    string  public storageInfo;
    mapping(uint256 => ExtData) private _tokens;
    mapping(bytes32 => uint256) public tokenOfNode;
    mapping(address => address) public delegateAccessOf;

    constructor(
        string memory name_, string memory symbol_, string memory storageInfo_,
        address admin_, INameWrapper nameWrapper_, IERC7857DataVerifier verifier_,
        address royaltyReceiver, uint96 royaltyBps
    ) ERC721(name_, symbol_) Ownable(admin_) {
        if (address(nameWrapper_) == address(0)) revert ZeroAddress();
        nameWrapper = nameWrapper_;
        verifierContract = verifier_;
        storageInfo = storageInfo_;
        _setDefaultRoyalty(royaltyReceiver, royaltyBps);
    }

    function mintExtension(
        bytes32 ensNode,
        IntelligentData[] calldata iDatas,
        bool soulbound
    ) external nonReentrant returns (uint256 tokenId) {
        if (iDatas.length == 0) revert EmptyData();
        if (nameWrapper.ownerOf(uint256(ensNode)) != msg.sender) revert NotSubnameOwner();
        if (tokenOfNode[ensNode] != 0) revert AlreadyExtended(ensNode);

        tokenId = nextTokenId++;
        ExtData storage t = _tokens[tokenId];
        t.ensNode = ensNode;
        t.soulbound = soulbound;
        for (uint256 i; i < iDatas.length; ++i) t.iDatas.push(iDatas[i]);
        tokenOfNode[ensNode] = tokenId;

        _safeMint(msg.sender, tokenId);
        if (soulbound) emit Locked(tokenId);
    }

    function name() public view override(ERC721, IERC7857Metadata) returns (string memory) { return ERC721.name(); }
    function symbol() public view override(ERC721, IERC7857Metadata) returns (string memory) { return ERC721.symbol(); }

    function verifier() external view returns (IERC7857DataVerifier) { return verifierContract; }

    function iTransfer(address to, uint256 tokenId, TransferValidityProof[] calldata proofs)
        external override nonReentrant
    {
        if (_tokens[tokenId].soulbound) revert TokenSoulbound(tokenId);
        if (!_isOwnerOrApproved(msg.sender, tokenId)) revert NotOwnerOrApproved();
        address from = ownerOf(tokenId);
        ExtData storage t = _tokens[tokenId];
        TransferValidityProofOutput[] memory outs = verifierContract.verifyTransferValidity(proofs);
        require(outs.length == t.iDatas.length, "proof count");
        bytes[] memory sealedKeys = new bytes[](outs.length);
        for (uint256 i; i < outs.length; ++i) {
            if (outs[i].oldDataHash != t.iDatas[i].dataHash) revert OldHashMismatch();
            t.iDatas[i].dataHash = outs[i].newDataHash;
            sealedKeys[i] = outs[i].sealedKey;
        }
        _safeTransfer(from, to, tokenId, "");
        emit Transferred(tokenId, from, to);
        emit PublishedSealedKey(to, tokenId, sealedKeys);
        emit MetadataUpdate(tokenId);
    }

    function iClone(address, uint256, TransferValidityProof[] calldata) external pure override returns (uint256) {
        revert("clone not supported in extension mode");
    }
    function authorizeUsage(uint256 tokenId, address user) external override {
        if (!_isOwnerOrApproved(msg.sender, tokenId)) revert NotOwnerOrApproved();
        _tokens[tokenId].authorizedUsers.push(user);
        emit Authorization(msg.sender, user, tokenId);
    }
    function revokeAuthorization(uint256 tokenId, address user) external override {
        if (!_isOwnerOrApproved(msg.sender, tokenId)) revert NotOwnerOrApproved();
        address[] storage arr = _tokens[tokenId].authorizedUsers;
        for (uint256 i; i < arr.length; ++i) if (arr[i] == user) { arr[i]=arr[arr.length-1]; arr.pop(); break; }
        emit AuthorizationRevoked(msg.sender, user, tokenId);
    }
    function delegateAccess(address a) external override { delegateAccessOf[msg.sender]=a; emit DelegateAccess(msg.sender,a); }
    function authorizedUsersOf(uint256 id) external view returns (address[] memory) { return _tokens[id].authorizedUsers; }
    function getDelegateAccess(address u) external view returns (address) { return delegateAccessOf[u]; }
    function intelligentDataOf(uint256 id) external view returns (IntelligentData[] memory) { return _tokens[id].iDatas; }
    function locked(uint256 id) external view override returns (bool) { return _tokens[id].soulbound; }

    function _update(address to, uint256 id, address auth) internal override returns (address from) {
        from = super._update(to, id, auth);
        if (from != address(0) && to != address(0) && _tokens[id].soulbound) revert TokenSoulbound(id);
    }

    function tokenURI(uint256 id) public view override returns (string memory) {
        _requireOwned(id);
        return string.concat(storageInfo, "/", Strings.toString(id), ".json");
    }

    function supportsInterface(bytes4 id) public view virtual override(ERC721, ERC2981) returns (bool) {
        return id == type(IERC7857).interfaceId
            || id == type(IERC5192).interfaceId
            || id == bytes4(0x49064906)
            || super.supportsInterface(id);
    }

    function _isOwnerOrApproved(address s, uint256 id) internal view returns (bool) {
        address o = _ownerOf(id);
        return o == s || getApproved(id) == s || isApprovedForAll(o, s);
    }
}
