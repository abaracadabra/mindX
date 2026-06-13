// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IReverseRegistrar} from "../../contracts/interfaces/IReverseRegistrar.sol";

/// @notice Minimal ENS ReverseRegistrar stand-in for unit-testing the
///         setReverseName admin methods that Phase 2.3 added to the four
///         bankoneth registrar contracts. Records every setName /
///         setNameForAddr / claim call so tests can assert exactly what
///         each registrar emits.
///
///         Returns the standard ENSIP-3 reverse node for `setName`:
///             keccak256(parent("addr.reverse") || keccak256(addr-hex))
///         The parent node is hard-coded to the canonical "addr.reverse"
///         namehash.
contract MockReverseRegistrar is IReverseRegistrar {
    /// @dev namehash("addr.reverse"). Verbatim from ENSIP-3.
    bytes32 public constant ADDR_REVERSE_NODE =
        0x91d1777781884d03a6757a803996e38de2a42967fb37eeaca72729271025a9e2;

    // Storage to assert against in tests.
    string  public  lastName;             // last setName arg
    address public  lastCaller;           // msg.sender at the last call
    address public  lastClaimOwner;       // last claim() owner arg
    address public  lastSetNameForAddrAddr;
    address public  lastSetNameForAddrOwner;
    address public  lastSetNameForAddrResolver;
    string  public  lastSetNameForAddrName;

    /// @dev addr → node mapping used by tests that need to look up the
    ///      reverse node for an address.
    mapping(address => bytes32) public node;

    // ── IReverseRegistrar ──────────────────────────────────────────

    function setName(string memory name) external override returns (bytes32) {
        lastName   = name;
        lastCaller = msg.sender;
        bytes32 labelhash = keccak256(_toLowerHexBytes(msg.sender));
        bytes32 n = keccak256(abi.encodePacked(ADDR_REVERSE_NODE, labelhash));
        node[msg.sender] = n;
        return n;
    }

    function setNameForAddr(
        address addr_,
        address owner_,
        address resolver_,
        string memory name_
    ) external override returns (bytes32) {
        lastSetNameForAddrAddr     = addr_;
        lastSetNameForAddrOwner    = owner_;
        lastSetNameForAddrResolver = resolver_;
        lastSetNameForAddrName     = name_;
        bytes32 labelhash = keccak256(_toLowerHexBytes(addr_));
        bytes32 n = keccak256(abi.encodePacked(ADDR_REVERSE_NODE, labelhash));
        node[addr_] = n;
        return n;
    }

    function claim(address owner_) external override returns (bytes32) {
        lastClaimOwner = owner_;
        bytes32 labelhash = keccak256(_toLowerHexBytes(msg.sender));
        bytes32 n = keccak256(abi.encodePacked(ADDR_REVERSE_NODE, labelhash));
        node[msg.sender] = n;
        return n;
    }

    // ── helpers ────────────────────────────────────────────────────

    /// @dev "0x..." → lowercase ascii bytes of the 40 hex chars (no 0x).
    ///      Mirrors the ENSIP-3 reverse-label derivation.
    function _toLowerHexBytes(address a) internal pure returns (bytes memory) {
        bytes memory out = new bytes(40);
        uint256 v = uint160(a);
        for (uint256 i = 0; i < 40; ++i) {
            uint8 nibble = uint8((v >> (4 * (39 - i))) & 0xf);
            out[i] = nibble < 10
                ? bytes1(uint8(48 + nibble))
                : bytes1(uint8(87 + nibble));   // 'a' = 0x61 = 87 + 10
        }
        return out;
    }
}
