// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IPublicResolver} from "../../interfaces/IBankon.sol";

/// @notice Minimal Public Resolver stand-in. Records every write so tests
///         can verify which records the registrar wrote.
contract MockResolver is IPublicResolver {
    mapping(bytes32 => address) public addrOf;
    mapping(bytes32 => mapping(uint256 => bytes)) public addrOfChain;
    mapping(bytes32 => mapping(string => string)) public textOf;
    mapping(bytes32 => bytes) public contenthashOf;
    uint256 public multicallCount;

    function setAddr(bytes32 node, address a) external override {
        addrOf[node] = a;
    }

    function setAddr(bytes32 node, uint256 coinType, bytes calldata a) external override {
        addrOfChain[node][coinType] = a;
    }

    function setText(bytes32 node, string calldata key, string calldata value) external override {
        textOf[node][key] = value;
    }

    function setContenthash(bytes32 node, bytes calldata hash) external override {
        contenthashOf[node] = hash;
    }

    function multicall(bytes[] calldata datas) external override returns (bytes[] memory results) {
        multicallCount++;
        results = new bytes[](datas.length);
        for (uint256 i = 0; i < datas.length; i++) {
            (bool ok, bytes memory r) = address(this).delegatecall(datas[i]);
            require(ok, "resolver multicall sub-call failed");
            results[i] = r;
        }
    }
}
