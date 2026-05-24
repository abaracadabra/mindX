// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {BankonSubnameResolverV2} from "../contracts/BankonSubnameResolverV2.sol";
import {IBankonInftAdapter}      from "../contracts/interfaces/IBankonExtensions.sol";

abstract contract V2Harness is Test {
    BankonSubnameResolverV2 r;

    address admin     = makeAddr("admin");
    address registrar = makeAddr("registrar");
    address rando     = makeAddr("rando");

    bytes32 constant ROOT = bytes32(0);
    bytes32 constant ETH_NODE = keccak256(abi.encodePacked(ROOT, keccak256("eth")));
    bytes32 constant BANKON_ETH = keccak256(abi.encodePacked(ETH_NODE, keccak256("bankon")));
    bytes32 constant ALICE_BANKON_ETH = keccak256(abi.encodePacked(BANKON_ETH, keccak256("alice")));

    function setUp() public virtual {
        r = new BankonSubnameResolverV2(admin, IBankonInftAdapter(address(0)));
        vm.prank(admin);
        r.grantRegistrar(registrar);
    }
}

// ── supportsInterface — every canonical ID ──────────────────────────

contract V2SupportsInterfaceTest is V2Harness {
    function test_AdvertisesIAddrResolver() public view {
        assertTrue(r.supportsInterface(0x3b3b57de));
    }

    function test_AdvertisesIAddressResolver_ENSIP9() public view {
        assertTrue(r.supportsInterface(0xf1cb7e06));
    }

    function test_AdvertisesITextResolver() public view {
        assertTrue(r.supportsInterface(0x59d1d43c));
    }

    function test_AdvertisesIContentHashResolver() public view {
        assertTrue(r.supportsInterface(0xbc1c58d1));
    }

    function test_AdvertisesINameResolver() public view {
        assertTrue(r.supportsInterface(0x691f3431));
    }

    function test_AdvertisesIExtendedResolver_ENSIP10() public view {
        assertTrue(r.supportsInterface(0x9061b923));
    }

    function test_AdvertisesIERC165() public view {
        assertTrue(r.supportsInterface(0x01ffc9a7));
    }

    function test_RejectsUnknownInterface() public view {
        assertFalse(r.supportsInterface(bytes4(0xdeadbeef)));
    }
}

// ── addr / multichain / TBA override ───────────────────────────────

contract V2AddrTest is V2Harness {
    function test_AddrEth_payableReturn() public {
        vm.prank(registrar);
        r.setAddr(ALICE_BANKON_ETH, address(0xabcd));
        assertEq(address(r.addr(ALICE_BANKON_ETH)), address(0xabcd));
    }

    function test_AddrCoinType60_mirrorsAddrBytes32() public {
        vm.prank(registrar);
        r.setAddr(ALICE_BANKON_ETH, address(0xabcd));
        bytes memory packed = r.addr(ALICE_BANKON_ETH, 60);
        assertEq(packed.length, 20);
        assertEq(bytes20(packed), bytes20(uint160(0xabcd)));
    }

    function test_AddrCoinType60_emptyWhenUnset() public view {
        bytes memory packed = r.addr(ALICE_BANKON_ETH, 60);
        assertEq(packed.length, 0);
    }

    function test_AddrCoinTypeNon60_returnsStoredBytes() public {
        // ENSIP-11 EVM Base coinType = 0x80002105
        vm.prank(registrar);
        r.setAddr(ALICE_BANKON_ETH, 0x80002105, hex"abad1dea");
        assertEq(r.addr(ALICE_BANKON_ETH, 0x80002105), hex"abad1dea");
    }

    function test_TbaOverridesAddrEth() public {
        vm.prank(registrar);
        r.setAddr(ALICE_BANKON_ETH, address(0xabcd));
        vm.prank(registrar);
        r.setINFTBinding(ALICE_BANKON_ETH, address(0xcafe), 99);
        assertEq(address(r.addr(ALICE_BANKON_ETH)), address(0xcafe));
    }

    function test_SetAddrCoinType60_alsoMirrorsToAddrBytes32() public {
        // Per the setAddr(node, 60, a) impl: when coinType=60 and a.length=20,
        // mirror into the storage for addr(bytes32).
        vm.prank(registrar);
        r.setAddr(ALICE_BANKON_ETH, 60, abi.encodePacked(address(0xfeed)));
        assertEq(address(r.addr(ALICE_BANKON_ETH)), address(0xfeed));
    }
}

// ── text / contenthash / name ──────────────────────────────────────

contract V2TextContentNameTest is V2Harness {
    function test_TextRoundTrip() public {
        vm.prank(registrar);
        r.setText(ALICE_BANKON_ETH, "url", "https://bankon.eth");
        assertEq(r.text(ALICE_BANKON_ETH, "url"), "https://bankon.eth");
    }

    function test_ContenthashRoundTrip() public {
        bytes memory ch = hex"e30101701220deadbeef";
        vm.prank(registrar);
        r.setContenthash(ALICE_BANKON_ETH, ch);
        assertEq(r.contenthash(ALICE_BANKON_ETH), ch);
    }

    function test_NameRoundTrip() public {
        vm.prank(registrar);
        r.setName(ALICE_BANKON_ETH, "alice.bankon.eth");
        assertEq(r.name(ALICE_BANKON_ETH), "alice.bankon.eth");
    }
}

// ── ENSIP-10 wildcard resolve(name, data) ──────────────────────────

contract V2WildcardResolveTest is V2Harness {
    /// @dev DNS-encode "alice.bankon.eth": \x05alice\x06bankon\x03eth\x00
    function _dnsName_alice_bankon_eth() internal pure returns (bytes memory) {
        return abi.encodePacked(
            bytes1(0x05), "alice",
            bytes1(0x06), "bankon",
            bytes1(0x03), "eth",
            bytes1(0x00)
        );
    }

    function test_ResolveDnsNamehashMatchesIterative() public {
        // Sanity: the wildcard path uses the same namehash construction the
        // test harness derives manually. If this assertion fails, every other
        // wildcard test below will too.
        bytes memory dns = _dnsName_alice_bankon_eth();
        // Use resolve(name, data) with the addr selector; if we get the same
        // result as calling addr(node) directly, the dnsName-to-node logic is
        // correct.
        vm.prank(registrar);
        r.setAddr(ALICE_BANKON_ETH, address(0xc0de));

        bytes memory callData = abi.encodeWithSelector(
            bytes4(0x3b3b57de),  // IAddrResolver.addr.selector
            ALICE_BANKON_ETH
        );
        bytes memory result = r.resolve(dns, callData);
        address got = abi.decode(result, (address));
        assertEq(got, address(0xc0de));
    }

    function test_ResolveText() public {
        vm.prank(registrar);
        r.setText(ALICE_BANKON_ETH, "mindx.endpoint", "https://mindx.pythai.net/agent/alice");

        bytes memory dns = _dnsName_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(
            bytes4(0x59d1d43c),  // ITextResolver.text.selector
            ALICE_BANKON_ETH,
            "mindx.endpoint"
        );
        bytes memory result = r.resolve(dns, callData);
        string memory got = abi.decode(result, (string));
        assertEq(got, "https://mindx.pythai.net/agent/alice");
    }

    function test_ResolveContenthash() public {
        bytes memory ch = hex"e30101701220cafebabe";
        vm.prank(registrar);
        r.setContenthash(ALICE_BANKON_ETH, ch);

        bytes memory dns = _dnsName_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(
            bytes4(0xbc1c58d1),  // IContentHashResolver.contenthash.selector
            ALICE_BANKON_ETH
        );
        bytes memory result = r.resolve(dns, callData);
        bytes memory got = abi.decode(result, (bytes));
        assertEq(got, ch);
    }

    function test_ResolveName() public {
        vm.prank(registrar);
        r.setName(ALICE_BANKON_ETH, "alice.bankon.eth");

        bytes memory dns = _dnsName_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(
            bytes4(0x691f3431),  // INameResolver.name.selector
            ALICE_BANKON_ETH
        );
        bytes memory result = r.resolve(dns, callData);
        string memory got = abi.decode(result, (string));
        assertEq(got, "alice.bankon.eth");
    }

    function test_ResolveUnknownSelector_returnsEmpty() public view {
        bytes memory dns = _dnsName_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(bytes4(0xdeadbeef), ALICE_BANKON_ETH);
        bytes memory result = r.resolve(dns, callData);
        assertEq(result.length, 0);
    }
}

// ── Role gates (parity with v1) ────────────────────────────────────

contract V2RoleGateTest is V2Harness {
    function test_SetAddrEth_revertsForNonRegistrar() public {
        vm.expectRevert();
        r.setAddr(ALICE_BANKON_ETH, address(0xabcd));
    }

    function test_SetText_revertsForNonRegistrar() public {
        vm.expectRevert();
        r.setText(ALICE_BANKON_ETH, "url", "https://bankon.eth");
    }

    function test_SetName_revertsForNonRegistrar() public {
        vm.expectRevert();
        r.setName(ALICE_BANKON_ETH, "alice.bankon.eth");
    }
}
