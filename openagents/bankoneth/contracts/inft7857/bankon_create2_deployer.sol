// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Source: docs/…ERC-7857 iNFT and ERC-6551 TBA Integration.md (pragma relaxed to ^0.8.24).
pragma solidity ^0.8.24;

/// @title bankon_create2_deployer — thin helper around Nick's Factory for 0xBANK… vanity deploys
contract bankon_create2_deployer {
    address public constant NICKS_FACTORY = 0x4e59b44847b379578588920cA78FbF26c0B4956C;

    event Deployed(address indexed deployed, bytes32 salt);

    /// @notice Forwards (salt, initCode) to Nick's Factory → CREATE2, identical addresses on every EVM chain.
    /// @dev Nick's Factory returns the new address as 20 raw bytes (big-endian). Take the leading
    ///      20 bytes directly — casting via bytes32→uint160 would truncate the low bits and mangle it.
    function deploy(bytes32 salt, bytes calldata initCode) external returns (address d) {
        (bool ok, bytes memory ret) = NICKS_FACTORY.call(abi.encodePacked(salt, initCode));
        require(ok && ret.length >= 20, "deploy failed");
        d = address(bytes20(ret));
        emit Deployed(d, salt);
    }

    function computeAddress(bytes32 salt, bytes32 initCodeHash) external pure returns (address) {
        return address(uint160(uint256(keccak256(abi.encodePacked(
            bytes1(0xff), NICKS_FACTORY, salt, initCodeHash
        )))));
    }
}
