// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {INameWrapper} from "../../interfaces/IBankon.sol";

/// @notice Minimal ENS NameWrapper stand-in for testing the BANKON registrar.
///         Tracks subnode owners + fuses + expiry per (parentNode, label) and
///         exposes the surface the registrar actually calls. Not a faithful
///         reimplementation — just enough behavior to verify the
///         three-step register-records-transfer pattern, expiry capping,
///         renew via extendExpiry, and event reachability.
contract MockNameWrapper is INameWrapper {
    struct Data {
        address owner;
        uint32  fuses;
        uint64  expiry;
    }

    mapping(uint256 => Data) public data;
    mapping(bytes32 => bytes32) public lastSubnodeRecord;
    mapping(uint256 => address) public approvals;
    mapping(address => mapping(address => bool)) public approvalForAll;
    /// Operator can pre-set the parent's expiry to test capping.
    function adminSetParent(bytes32 parentNode, address owner, uint32 fuses, uint64 expiry) external {
        data[uint256(parentNode)] = Data(owner, fuses, expiry);
    }

    function ownerOf(uint256 id) external view override returns (address) {
        return data[id].owner;
    }

    function getData(uint256 id)
        external view override
        returns (address owner, uint32 fuses, uint64 expiry)
    {
        Data memory d = data[id];
        return (d.owner, d.fuses, d.expiry);
    }

    function setSubnodeOwner(
        bytes32 parentNode,
        string calldata label,
        address owner,
        uint32 fuses,
        uint64 expiry
    ) external override returns (bytes32 subnode) {
        subnode = keccak256(abi.encodePacked(parentNode, keccak256(bytes(label))));
        data[uint256(subnode)] = Data(owner, fuses, expiry);
        return subnode;
    }

    function setSubnodeRecord(
        bytes32 parentNode,
        string calldata label,
        address owner,
        address /* resolver */,
        uint64 /* ttl */,
        uint32 fuses,
        uint64 expiry
    ) external override returns (bytes32 subnode) {
        subnode = keccak256(abi.encodePacked(parentNode, keccak256(bytes(label))));
        data[uint256(subnode)] = Data(owner, fuses, expiry);
        lastSubnodeRecord[parentNode] = subnode;
        return subnode;
    }

    function setChildFuses(bytes32 parentNode, bytes32 labelhash, uint32 fuses, uint64 expiry)
        external override
    {
        bytes32 node = keccak256(abi.encodePacked(parentNode, labelhash));
        Data storage d = data[uint256(node)];
        d.fuses = fuses;
        d.expiry = expiry;
    }

    function setFuses(bytes32 node, uint16 ownerControlledFuses) external override returns (uint32) {
        Data storage d = data[uint256(node)];
        d.fuses |= uint32(ownerControlledFuses);
        return d.fuses;
    }

    function setResolver(bytes32 /* node */, address /* resolver */) external pure override {}

    function extendExpiry(bytes32 parentNode, bytes32 labelhash, uint64 expiry)
        external override
        returns (uint64)
    {
        bytes32 node = keccak256(abi.encodePacked(parentNode, labelhash));
        Data storage d = data[uint256(node)];
        // Cap at parent expiry if set
        Data memory parent = data[uint256(parentNode)];
        if (parent.expiry > 0 && expiry > parent.expiry) expiry = parent.expiry;
        d.expiry = expiry;
        return expiry;
    }

    function isWrapped(bytes32 node) external view override returns (bool) {
        return data[uint256(node)].owner != address(0);
    }

    function setApprovalForAll(address operator, bool approved) external override {
        approvalForAll[msg.sender][operator] = approved;
    }

    function approve(address to, uint256 tokenId) external override {
        approvals[tokenId] = to;
    }
}
