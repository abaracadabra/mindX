// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Source: docs/…ERC-7857 iNFT and ERC-6551 TBA Integration.md (pragma relaxed to ^0.8.24).
pragma solidity ^0.8.24;

import {IERC165}           from "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import {IERC1271}          from "@openzeppelin/contracts/interfaces/IERC1271.sol";
import {IERC721}           from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {SignatureChecker}  from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";
import {ERC721Holder}      from "@openzeppelin/contracts/token/ERC721/utils/ERC721Holder.sol";
import {ERC1155Holder}     from "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";

import {IERC6551Account, IERC6551Executable} from "./bankon_interfaces.sol";

/// @title bankon_tba_account — lean BANKON ERC-6551 account implementation
/// @notice Each iNFT gets one of these as its agent wallet. Owner = current
///         ownerOf(tokenId) on the bound ERC-721 (reads live, no storage write on transfer).
contract bankon_tba_account is
    IERC165, IERC1271, IERC6551Account, IERC6551Executable, ERC721Holder, ERC1155Holder
{
    error InvalidOperation();
    error NotAuthorized();

    uint256 public state;
    bytes4 internal constant ERC1271_MAGIC = 0x1626ba7e;
    bytes4 internal constant IS_VALID_SIGNER_MAGIC = 0x523e3260;

    receive() external payable {}

    /// @dev appended-immutable-args per the canonical 6551 proxy pattern
    function token() public view returns (uint256 chainId, address tokenContract, uint256 tokenId) {
        assembly {
            chainId       := calldataload(sub(calldatasize(), 0x60))
            tokenContract := calldataload(sub(calldatasize(), 0x40))
            tokenId       := calldataload(sub(calldatasize(), 0x20))
        }
    }

    function owner() public view returns (address) {
        (uint256 chainId, address tokenContract, uint256 tokenId) = token();
        if (chainId != block.chainid) return address(0); // cross-chain TBAs cannot execute locally
        return IERC721(tokenContract).ownerOf(tokenId);
    }

    function isValidSigner(address signer, bytes calldata) external view returns (bytes4) {
        return signer == owner() ? IS_VALID_SIGNER_MAGIC : bytes4(0);
    }

    function isValidSignature(bytes32 hash, bytes calldata sig) external view returns (bytes4) {
        if (SignatureChecker.isValidSignatureNow(owner(), hash, sig)) return ERC1271_MAGIC;
        return 0xffffffff;
    }

    function execute(address to, uint256 value, bytes calldata data, uint8 op)
        external payable returns (bytes memory result)
    {
        if (msg.sender != owner()) revert NotAuthorized();
        ++state;

        if (op == 0) {
            (bool ok, bytes memory ret) = to.call{value: value}(data);
            if (!ok) { assembly { revert(add(ret, 32), mload(ret)) } }
            return ret;
        } else if (op == 1) {
            (bool ok, bytes memory ret) = to.delegatecall(data);
            if (!ok) { assembly { revert(add(ret, 32), mload(ret)) } }
            return ret;
        } else if (op == 2) {
            bytes memory initCode = data;               // calldata → memory
            address deployed;
            assembly { deployed := create(value, add(initCode, 0x20), mload(initCode)) }
            if (deployed == address(0)) revert InvalidOperation();
            return abi.encode(deployed);
        } else if (op == 3) {
            bytes32 salt;
            assembly { salt := calldataload(data.offset) }
            bytes memory initCode = data[32:];          // calldata slice → memory
            address deployed;
            assembly { deployed := create2(value, add(initCode, 0x20), mload(initCode), salt) }
            if (deployed == address(0)) revert InvalidOperation();
            return abi.encode(deployed);
        }
        revert InvalidOperation();
    }

    /// @notice AgenticPlace helper: lets the TBA approve a marketplace on its parent iNFT.
    function listOnAgenticPlace(address marketplace, bool approved) external {
        if (msg.sender != owner()) revert NotAuthorized();
        (, address tokenContract, ) = token();
        ++state;
        IERC721(tokenContract).setApprovalForAll(marketplace, approved);
    }

    function supportsInterface(bytes4 id) public pure override(ERC1155Holder, IERC165) returns (bool) {
        return id == type(IERC165).interfaceId
            || id == type(IERC1271).interfaceId
            || id == type(IERC6551Account).interfaceId       // 0x6faff5f1
            || id == type(IERC6551Executable).interfaceId
            || id == 0x4e2312e0  // ERC1155Receiver
            || id == 0x150b7a02; // ERC721Receiver
    }
}
