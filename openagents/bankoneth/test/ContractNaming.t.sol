// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";

import {BankonSubnameRegistrar}  from "../contracts/BankonSubnameRegistrar.sol";
import {BankonEthRegistrar, IETHRegistrarController} from "../contracts/BankonEthRegistrar.sol";
import {BankonDomainHosting}     from "../contracts/BankonDomainHosting.sol";
import {BankonOffchainRegistrar} from "../contracts/BankonOffchainRegistrar.sol";

import {BankonPriceOracle}        from "../contracts/BankonPriceOracle.sol";
import {BankonPaymentRouter}      from "../contracts/BankonPaymentRouter.sol";
import {BankonReputationGate}     from "../contracts/BankonReputationGate.sol";
import {BankonX402Attestor}       from "../contracts/BankonX402Attestor.sol";

import {MockNameWrapper}          from "./mocks/MockNameWrapper.sol";
import {MockResolver}             from "./mocks/MockResolver.sol";
import {MockIdentityRegistry}     from "./mocks/MockIdentityRegistry.sol";
import {MockReverseRegistrar}     from "./mocks/MockReverseRegistrar.sol";
import {MockEthRegistrarController} from "./mocks/MockEthRegistrarController.sol";

import {IReverseRegistrar}        from "../contracts/interfaces/IReverseRegistrar.sol";
import {
    INameWrapper, IPublicResolver, IBankonPaymentRouter,
    IBankonPriceOracle, IBankonReputationGate, IIdentityRegistry8004
}                                  from "../contracts/interfaces/IBankon.sol";
import {IBankonX402Attestor}       from "../contracts/interfaces/IBankonExtensions.sol";

/// @notice Contract-naming review tests — Phase D. Confirms each of the
///         four registrar `setReverseName` admin methods:
///           - reverts for non-admin callers
///           - forwards to the ReverseRegistrar's setName with the right
///             name string
///           - returns the canonical ENSIP-3 reverse node
///         Plus a Solidity-side ENSIP-3 + ENSIP-19 namespace derivation
///         parity test against the TS helper.

// ─── Shared mocks setUp ────────────────────────────────────────────

abstract contract NamingHarness is Test {
    MockReverseRegistrar     rr;
    address admin   = makeAddr("admin");
    address rando   = makeAddr("rando");
    bytes32 constant ADDR_REVERSE_NODE =
        0x91d1777781884d03a6757a803996e38de2a42967fb37eeaca72729271025a9e2;

    function setUp() public virtual {
        rr = new MockReverseRegistrar();
    }

    /// @dev Expected reverse node for `a` under ENSIP-3 (parent=addr.reverse).
    function _expectedAddrReverseNode(address a) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(ADDR_REVERSE_NODE, keccak256(_lowerHex(a))));
    }

    function _lowerHex(address a) internal pure returns (bytes memory out) {
        out = new bytes(40);
        uint256 v = uint160(a);
        for (uint256 i = 0; i < 40; ++i) {
            uint8 nibble = uint8((v >> (4 * (39 - i))) & 0xf);
            out[i] = nibble < 10 ? bytes1(uint8(48 + nibble)) : bytes1(uint8(87 + nibble));
        }
    }
}

// ─── BankonEthRegistrar.setReverseName ─────────────────────────────

contract EthRegistrarNameTest is NamingHarness {
    BankonEthRegistrar reg;

    function setUp() public override {
        super.setUp();
        MockEthRegistrarController controller = new MockEthRegistrarController();
        BankonPriceOracle    oracle   = new BankonPriceOracle(admin);
        BankonPaymentRouter  router   = new BankonPaymentRouter(admin);
        BankonX402Attestor   attestor = new BankonX402Attestor(admin);
        reg = new BankonEthRegistrar(
            admin,
            IETHRegistrarController(address(controller)),
            IBankonPriceOracle(address(oracle)),
            IBankonPaymentRouter(address(router)),
            IBankonX402Attestor(address(attestor))
        );
    }

    function test_SetReverseName_byAdmin_forwardsToRR() public {
        vm.prank(admin);
        bytes32 returned = reg.setReverseName(IReverseRegistrar(address(rr)), "eth-registrar.bankon.eth");

        assertEq(rr.lastName(), "eth-registrar.bankon.eth");
        assertEq(rr.lastCaller(), address(reg));
        assertEq(returned, _expectedAddrReverseNode(address(reg)));
    }

    function test_SetReverseName_revertsForNonAdmin() public {
        vm.prank(rando);
        vm.expectRevert();
        reg.setReverseName(IReverseRegistrar(address(rr)), "eth-registrar.bankon.eth");
    }
}

// ─── BankonDomainHosting.setReverseName ────────────────────────────

contract DomainHostingNameTest is NamingHarness {
    BankonDomainHosting host;

    function setUp() public override {
        super.setUp();
        MockNameWrapper wrapper = new MockNameWrapper();
        MockResolver    res     = new MockResolver();
        BankonPaymentRouter router = new BankonPaymentRouter(admin);
        BankonX402Attestor  attestor = new BankonX402Attestor(admin);

        host = new BankonDomainHosting(
            admin,
            INameWrapper(address(wrapper)),
            IPublicResolver(address(res)),
            IBankonPaymentRouter(address(router)),
            IBankonX402Attestor(address(attestor))
        );
    }

    function test_SetReverseName_byAdmin_forwardsToRR() public {
        vm.prank(admin);
        host.setReverseName(IReverseRegistrar(address(rr)), "host.bankon.eth");
        assertEq(rr.lastName(), "host.bankon.eth");
        assertEq(rr.lastCaller(), address(host));
    }

    function test_SetReverseName_revertsForNonAdmin() public {
        vm.prank(rando);
        vm.expectRevert();
        host.setReverseName(IReverseRegistrar(address(rr)), "host.bankon.eth");
    }
}

// ─── BankonOffchainRegistrar.setReverseName ────────────────────────

contract OffchainRegistrarNameTest is NamingHarness {
    BankonOffchainRegistrar off;

    function setUp() public override {
        super.setUp();
        BankonPriceOracle    oracle   = new BankonPriceOracle(admin);
        BankonPaymentRouter  router   = new BankonPaymentRouter(admin);
        BankonX402Attestor   attestor = new BankonX402Attestor(admin);
        off = new BankonOffchainRegistrar(
            admin, bytes32(uint256(1)),
            IBankonPriceOracle(address(oracle)),
            IBankonPaymentRouter(address(router)),
            IBankonX402Attestor(address(attestor))
        );
    }

    function test_SetReverseName_byAdmin_forwardsToRR() public {
        vm.prank(admin);
        off.setReverseName(IReverseRegistrar(address(rr)), "offchain.bankon.eth");
        assertEq(rr.lastName(), "offchain.bankon.eth");
        assertEq(rr.lastCaller(), address(off));
    }

    function test_SetReverseName_revertsForNonAdmin() public {
        vm.prank(rando);
        vm.expectRevert();
        off.setReverseName(IReverseRegistrar(address(rr)), "offchain.bankon.eth");
    }
}

// ─── BankonSubnameRegistrar.setReverseName ─────────────────────────

contract SubnameRegistrarNameTest is NamingHarness {
    BankonSubnameRegistrar reg;

    function setUp() public override {
        super.setUp();
        MockNameWrapper       wrapper = new MockNameWrapper();
        MockResolver          res     = new MockResolver();
        BankonPriceOracle     oracle  = new BankonPriceOracle(admin);
        BankonReputationGate  gate    = new BankonReputationGate(admin);
        BankonPaymentRouter   router  = new BankonPaymentRouter(admin);
        MockIdentityRegistry  idreg   = new MockIdentityRegistry();
        bytes32 parentNode = bytes32(uint256(0xb0017e));
        wrapper.adminSetParent(parentNode, admin, 0, type(uint64).max);

        reg = new BankonSubnameRegistrar(
            address(wrapper),
            address(res),
            parentNode,
            address(router),
            address(oracle),
            address(gate),
            address(idreg),
            admin
        );
    }

    function test_SetReverseName_byAdmin_forwardsToRR() public {
        vm.prank(admin);
        reg.setReverseName(IReverseRegistrar(address(rr)), "registrar.bankon.eth");
        assertEq(rr.lastName(), "registrar.bankon.eth");
        assertEq(rr.lastCaller(), address(reg));
    }

    function test_SetReverseName_revertsForNonAdmin() public {
        vm.prank(rando);
        vm.expectRevert();
        reg.setReverseName(IReverseRegistrar(address(rr)), "registrar.bankon.eth");
    }
}

// ─── ENSIP-19 multichain reverse namespace derivation parity ──────

contract Ensip19NamespaceTest is Test {
    bytes32 constant ADDR_REVERSE_NODE =
        0x91d1777781884d03a6757a803996e38de2a42967fb37eeaca72729271025a9e2;

    address constant FIX_ADDR = 0x1234567890AbcdEF1234567890aBcdef12345678;

    function test_Ensip3_addrReverse_default() public pure {
        // ENSIP-3 default — coinType 60. Namespace is "<lower>.addr.reverse".
        bytes32 expected = keccak256(abi.encodePacked(
            ADDR_REVERSE_NODE,
            keccak256(_lowerHex(FIX_ADDR))
        ));
        bytes32 got = _reverseNode(FIX_ADDR, 60);
        assertEq(got, expected);
    }

    function test_Ensip19_optimism_coinType() public pure {
        // Optimism EVM coinType = 0x8000000a (chainId 10).
        // Namespace: "<lower>.8000000a.reverse".
        bytes32 parent = _namehash2("8000000a", "reverse");
        bytes32 expected = keccak256(abi.encodePacked(parent, keccak256(_lowerHex(FIX_ADDR))));
        bytes32 got = _reverseNode(FIX_ADDR, 0x8000000a);
        assertEq(got, expected);
    }

    function test_Ensip19_base_coinType() public pure {
        // Base EVM coinType = 0x80002105 (chainId 8453).
        bytes32 parent = _namehash2("80002105", "reverse");
        bytes32 expected = keccak256(abi.encodePacked(parent, keccak256(_lowerHex(FIX_ADDR))));
        bytes32 got = _reverseNode(FIX_ADDR, 0x80002105);
        assertEq(got, expected);
    }

    function test_Ensip19_arbitrum_coinType() public pure {
        // Arbitrum EVM coinType = 0x8000a4b1 (chainId 42161).
        bytes32 parent = _namehash2("8000a4b1", "reverse");
        bytes32 expected = keccak256(abi.encodePacked(parent, keccak256(_lowerHex(FIX_ADDR))));
        bytes32 got = _reverseNode(FIX_ADDR, 0x8000a4b1);
        assertEq(got, expected);
    }

    // ── helpers (mirror packages/core/src/contract-naming.ts) ──────

    function _reverseNode(address a, uint256 coinType) internal pure returns (bytes32) {
        bytes32 parent = coinType == 60
            ? ADDR_REVERSE_NODE
            : _namehash2(_coinTypeHex(coinType), "reverse");
        return keccak256(abi.encodePacked(parent, keccak256(_lowerHex(a))));
    }

    /// @dev Two-label namehash: <left>.<right>
    function _namehash2(string memory left, string memory right) internal pure returns (bytes32) {
        bytes32 root = bytes32(0);
        bytes32 r = keccak256(abi.encodePacked(root, keccak256(bytes(right))));
        return keccak256(abi.encodePacked(r, keccak256(bytes(left))));
    }

    /// @dev coinType → lowercase hex, no 0x, no leading zeros.
    function _coinTypeHex(uint256 v) internal pure returns (string memory) {
        if (v == 0) return "0";
        uint256 width = 0;
        uint256 t = v;
        while (t > 0) { width++; t >>= 4; }
        bytes memory out = new bytes(width);
        for (uint256 i = 0; i < width; ++i) {
            uint8 nibble = uint8((v >> (4 * (width - 1 - i))) & 0xf);
            out[i] = nibble < 10 ? bytes1(uint8(48 + nibble)) : bytes1(uint8(87 + nibble));
        }
        return string(out);
    }

    function _lowerHex(address a) internal pure returns (bytes memory out) {
        out = new bytes(40);
        uint256 v = uint160(a);
        for (uint256 i = 0; i < 40; ++i) {
            uint8 nibble = uint8((v >> (4 * (39 - i))) & 0xf);
            out[i] = nibble < 10 ? bytes1(uint8(48 + nibble)) : bytes1(uint8(87 + nibble));
        }
    }
}
