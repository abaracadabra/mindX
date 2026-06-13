// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {BankonSubnameResolver} from "../contracts/BankonSubnameResolver.sol";
import {IBankonSubnameResolver, IBankonInftAdapter} from "../contracts/interfaces/IBankonExtensions.sol";

/// @notice Phase 0.4a — direct coverage for BankonSubnameResolver. The
///         resolver is exercised via end-to-end tests in
///         BankonSubnameRegistrar.t.sol, but several branches (REGISTRAR_ROLE
///         gates on each setter, the ENSIP-9 multichain overload, multicall
///         mixed-success, the addr↔TBA-override toggle, supportsInterface)
///         deserve dedicated assertions.

abstract contract ResolverHarness is Test {
    BankonSubnameResolver r;

    address admin     = makeAddr("admin");
    address registrar = makeAddr("registrar");
    address rando     = makeAddr("rando");

    bytes32 constant NODE = bytes32(uint256(0xfeedface));

    function setUp() public virtual {
        // adapter = address(0); resolver doesn't dereference it during these tests.
        r = new BankonSubnameResolver(admin, IBankonInftAdapter(address(0)));
        vm.prank(admin);
        r.grantRegistrar(registrar);
    }
}

/// ─── Role gates on every setter ────────────────────────────────────

contract ResolverRoleGateTest is ResolverHarness {
    function test_SetAddr_revertsForNonRegistrar() public {
        vm.expectRevert();
        r.setAddr(NODE, address(0xbeef));
    }

    function test_SetMultichainAddr_revertsForNonRegistrar() public {
        vm.expectRevert();
        r.setAddr(NODE, 0x80000001, hex"deadbeef");
    }

    function test_SetText_revertsForNonRegistrar() public {
        vm.expectRevert();
        r.setText(NODE, "mindx.endpoint", "https://example.com");
    }

    function test_SetContenthash_revertsForNonRegistrar() public {
        vm.expectRevert();
        r.setContenthash(NODE, hex"e30101701220");
    }

    function test_SetINFTBinding_revertsForNonRegistrar() public {
        vm.expectRevert();
        r.setINFTBinding(NODE, address(0xcafe), 42);
    }

    function test_GrantRegistrar_revertsForNonAdmin() public {
        vm.expectRevert();
        r.grantRegistrar(rando);
    }

    function test_RevokeRegistrar_revertsForNonAdmin() public {
        vm.expectRevert();
        r.revokeRegistrar(registrar);
    }

    function test_SetInftAdapter_revertsForNonAdmin() public {
        vm.expectRevert();
        r.setInftAdapter(IBankonInftAdapter(address(0)));
    }
}

/// ─── addr ↔ TBA override toggle ────────────────────────────────────

contract ResolverAddrOverrideTest is ResolverHarness {
    function test_AddrReturnsRawWhenUnbound() public {
        vm.prank(registrar);
        r.setAddr(NODE, address(0xab));
        assertEq(r.addr(NODE), address(0xab));
    }

    function test_AddrReturnsTbaWhenBound() public {
        vm.prank(registrar);
        r.setAddr(NODE, address(0xab));
        vm.prank(registrar);
        r.setINFTBinding(NODE, address(0xcd), 7);
        // TBA wins.
        assertEq(r.addr(NODE), address(0xcd));
    }

    function test_AddrFallsBackToRawWhenTbaCleared() public {
        vm.prank(registrar);
        r.setAddr(NODE, address(0xab));
        vm.prank(registrar);
        r.setINFTBinding(NODE, address(0xcd), 7);
        // Clear TBA.
        vm.prank(registrar);
        r.setINFTBinding(NODE, address(0), 0);
        assertEq(r.addr(NODE), address(0xab));
    }
}

/// ─── ENSIP-9 multichain setter + getter ────────────────────────────

contract ResolverMultichainTest is ResolverHarness {
    // ENSIP-11: Base = 0x80002105, Polygon = 0x80000089, Algorand = 0x8000011B
    uint256 constant BASE_COIN_TYPE = 0x80002105;

    function test_SetCoinAddr_byRegistrar() public {
        vm.prank(registrar);
        r.setAddr(NODE, BASE_COIN_TYPE, hex"abad1dea");
        assertEq(r.coinAddr(NODE, BASE_COIN_TYPE), hex"abad1dea");
    }

    function test_CoinAddr_emptyWhenUnset() public view {
        assertEq(r.coinAddr(NODE, BASE_COIN_TYPE), hex"");
    }
}

/// ─── Text + contenthash round-trips ────────────────────────────────

contract ResolverRecordRoundTripTest is ResolverHarness {
    function test_SetText_byRegistrar() public {
        vm.prank(registrar);
        r.setText(NODE, "mindx.endpoint", "https://mindx.pythai.net/agent/x");
        assertEq(r.text(NODE, "mindx.endpoint"), "https://mindx.pythai.net/agent/x");
    }

    function test_SetContenthash_byRegistrar() public {
        bytes memory ch = hex"e30101701220000000";
        vm.prank(registrar);
        r.setContenthash(NODE, ch);
        assertEq(r.contenthash(NODE), ch);
    }
}

/// ─── Multicall mixed-success ───────────────────────────────────────

contract ResolverMulticallTest is ResolverHarness {
    function test_Multicall_batchesSettersAsRegistrar() public {
        bytes[] memory calls = new bytes[](2);
        calls[0] = abi.encodeWithSignature("setAddr(bytes32,address)", NODE, address(0xab));
        calls[1] = abi.encodeWithSignature("setText(bytes32,string,string)", NODE, "url", "https://bankon.eth");

        // Multicall does delegatecall, so the role check inside each
        // setter executes against the caller of multicall. Prank registrar.
        vm.prank(registrar);
        r.multicall(calls);

        assertEq(r.addr(NODE), address(0xab));
        assertEq(r.text(NODE, "url"), "https://bankon.eth");
    }

    function test_Multicall_revertsOnAnyElementFailure() public {
        bytes[] memory calls = new bytes[](2);
        calls[0] = abi.encodeWithSignature("setAddr(bytes32,address)", NODE, address(0xab));
        // Second call uses an unknown selector — delegatecall reverts.
        calls[1] = hex"deadbeef";

        vm.prank(registrar);
        vm.expectRevert(bytes("BankonSubnameResolver: multicall element failed"));
        r.multicall(calls);
    }

    function test_Multicall_revertsWhenCallerLacksRole() public {
        bytes[] memory calls = new bytes[](1);
        calls[0] = abi.encodeWithSignature("setAddr(bytes32,address)", NODE, address(0xab));

        // Random caller — the inner setAddr's onlyRole gate trips.
        vm.expectRevert(bytes("BankonSubnameResolver: multicall element failed"));
        r.multicall(calls);
    }
}

/// ─── ERC-165 supportsInterface ─────────────────────────────────────

contract ResolverSupportsInterfaceTest is ResolverHarness {
    function test_AdvertisesIBankonSubnameResolver() public view {
        bytes4 id = type(IBankonSubnameResolver).interfaceId;
        assertTrue(r.supportsInterface(id));
    }

    function test_AdvertisesIERC165() public view {
        bytes4 id = bytes4(0x01ffc9a7);
        assertTrue(r.supportsInterface(id));
    }

    function test_RejectsUnknownInterface() public view {
        assertFalse(r.supportsInterface(bytes4(0x12345678)));
    }
}

/// ─── Adapter swap (admin) ──────────────────────────────────────────

contract ResolverAdapterSwapTest is ResolverHarness {
    function test_SetInftAdapter_byAdmin_emitsAndUpdates() public {
        address newAdapter = makeAddr("newAdapter");
        vm.prank(admin);
        vm.expectEmit(true, true, false, false);
        emit BankonSubnameResolver.InftAdapterUpdated(address(0), newAdapter);
        r.setInftAdapter(IBankonInftAdapter(newAdapter));
        assertEq(address(r.inftAdapter()), newAdapter);
    }
}
