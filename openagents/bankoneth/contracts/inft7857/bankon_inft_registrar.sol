// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Source: docs/…ERC-7857 iNFT and ERC-6551 TBA Integration.md (`bankon_subname_registrar`
// renamed → `bankon_inft_registrar` to avoid clash with the existing ENS
// BankonSubnameRegistrar.sol). Pragma relaxed to ^0.8.24.
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";

import {INameWrapper, IntelligentData, IERC6551Registry} from "./bankon_interfaces.sol";
import {bankon_inft_subname} from "./bankon_inft_subname.sol";
import {bankon_inft_extension} from "./bankon_inft_extension.sol";

/// @title bankon_inft_registrar — routes minting between Mode A / Mode B / WRAPPED_ONLY,
///        validates an x402 facilitator receipt, and derives the ERC-6551 TBA.
contract bankon_inft_registrar is Ownable, ReentrancyGuard, EIP712 {
    using ECDSA for bytes32;

    enum MintMode {
        WRAPPED_ONLY,
        UNIFIED_INFT,
        PARALLEL_INFT,
        UNIFIED_INFT_SOULBOUND,
        PARALLEL_INFT_SOULBOUND
    }

    error UnknownMode();
    error ReceiptUsed(bytes32 receipt);
    error BadSignature();

    bytes32 public constant X402_TYPEHASH = keccak256(
        "X402Mint(address to,bytes32 parentNode,string label,uint8 mode,uint64 expiry,bytes32 receipt)"
    );

    INameWrapper          public immutable nameWrapper;
    bankon_inft_subname   public immutable unifiedInft;
    bankon_inft_extension public immutable parallelInft;
    IERC6551Registry      public immutable tbaRegistry;
    address               public immutable tbaImplementation;
    address               public x402Facilitator;
    mapping(bytes32 => bool) public usedReceipts;

    event SubnameMinted(
        MintMode indexed mode, uint256 indexed tokenId, address indexed to,
        bytes32 parentNode, string label, address tba
    );

    constructor(
        address admin_,
        INameWrapper nameWrapper_,
        bankon_inft_subname unified_,
        bankon_inft_extension parallel_,
        IERC6551Registry tbaRegistry_,
        address tbaImpl_,
        address x402Facilitator_
    ) Ownable(admin_) EIP712("BankonRegistrar", "1") {
        nameWrapper = nameWrapper_;
        unifiedInft = unified_;
        parallelInft = parallel_;
        tbaRegistry = tbaRegistry_;
        tbaImplementation = tbaImpl_;
        x402Facilitator = x402Facilitator_;
    }

    function setFacilitator(address f) external onlyOwner { x402Facilitator = f; }

    function mintWithX402(
        address to,
        bytes32 parentNode,
        string calldata label,
        MintMode mode,
        uint64 expiry,
        IntelligentData[] calldata iDatas,
        bytes32 receipt,
        bytes calldata sig
    ) external nonReentrant returns (uint256 tokenId, address tba) {
        if (usedReceipts[receipt]) revert ReceiptUsed(receipt);
        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(
            X402_TYPEHASH, to, parentNode, keccak256(bytes(label)), uint8(mode), expiry, receipt
        )));
        if (digest.recover(sig) != x402Facilitator) revert BadSignature();
        usedReceipts[receipt] = true;
        return _route(to, parentNode, label, mode, expiry, iDatas);
    }

    function _route(
        address to, bytes32 parentNode, string calldata label,
        MintMode mode, uint64 expiry, IntelligentData[] calldata iDatas
    ) internal returns (uint256 tokenId, address tba) {
        if (mode == MintMode.UNIFIED_INFT || mode == MintMode.UNIFIED_INFT_SOULBOUND) {
            bool sb = mode == MintMode.UNIFIED_INFT_SOULBOUND;
            (tokenId, ) = unifiedInft.mintUnified(label, to, parentNode, iDatas, sb, expiry);
            tba = tbaRegistry.createAccount(
                tbaImplementation, bytes32(0), block.chainid, address(unifiedInft), tokenId
            );
        } else if (mode == MintMode.PARALLEL_INFT || mode == MintMode.PARALLEL_INFT_SOULBOUND) {
            bool sb = mode == MintMode.PARALLEL_INFT_SOULBOUND;
            uint32 fuses = sb
                ? (uint32(4) | uint32(1) | uint32(1 << 16) | uint32(1 << 18)) // CANNOT_TRANSFER|CANNOT_UNWRAP|PCC|CEE
                : (uint32(1) | uint32(1 << 16) | uint32(1 << 18));
            nameWrapper.setSubnodeOwner(parentNode, label, to, fuses, expiry);
            // user calls parallelInft.mintExtension themselves (cheaper UX)
            tokenId = 0;
            tba = address(0);
        } else if (mode == MintMode.WRAPPED_ONLY) {
            uint32 fuses = uint32(1) | uint32(1 << 16) | uint32(1 << 18);
            nameWrapper.setSubnodeOwner(parentNode, label, to, fuses, expiry);
            tokenId = 0; tba = address(0);
        } else {
            revert UnknownMode();
        }
        emit SubnameMinted(mode, tokenId, to, parentNode, label, tba);
    }
}
