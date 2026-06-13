// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";

import {BankonSubnameResolver}  from "../contracts/BankonSubnameResolver.sol";
import {BankonInftAdapter}      from "../contracts/BankonInftAdapter.sol";
import {BankonX402Attestor}     from "../contracts/BankonX402Attestor.sol";
import {BankonAgenticPlaceHook} from "../contracts/BankonAgenticPlaceHook.sol";

import {IBankonSubnameResolver, IBankonInftAdapter, IBankonAgenticPlaceHook}
    from "../contracts/interfaces/IBankonExtensions.sol";

/// @title  BankonEndToEnd
/// @notice Light end-to-end against the new bankoneth contracts.
///         The Flow A registrar's full E2E lives in the re-homed
///         BankonSubnameRegistrar.t.sol (vendored from DAIO); this file focuses
///         on the **iNFT Mode A** path: subname mint → InftAdapter receives →
///         emits RequestINFTMint → off-chain (simulated here) WIRER registers
///         the 0G tokenId → resolver `addr(node)` flips from raw addr to TBA.
contract BankonEndToEndTest is Test {
    BankonSubnameResolver  resolver;
    BankonInftAdapter      adapter;
    BankonX402Attestor     attestor;
    BankonAgenticPlaceHook hook;

    address admin     = makeAddr("admin");
    address registrar = makeAddr("registrar");  // Simulated registrar caller.
    address wirer     = makeAddr("wirer");      // 0G-side worker.
    address claimant  = makeAddr("claimant");

    bytes32 constant PARENT_NODE = bytes32(uint256(0xba17_001e));
    bytes32 constant LABEL_HASH  = keccak256("alice");
    bytes32 SUBNAME_NODE         = keccak256(abi.encodePacked(PARENT_NODE, LABEL_HASH));

    address constant ERC6551_IMPL  = address(0x1111111111111111111111111111111111111111);
    address constant ZEROG_INFT    = address(0x2222222222222222222222222222222222222222);
    uint256 constant ZEROG_CHAIN_ID = 16601;

    function setUp() public {
        vm.startPrank(admin);
        resolver = new BankonSubnameResolver(admin, IBankonInftAdapter(address(0)));
        adapter  = new BankonInftAdapter(admin, IBankonSubnameResolver(address(resolver)));
        resolver.setInftAdapter(IBankonInftAdapter(address(adapter)));

        adapter.setZeroGiNFTContract(ZEROG_INFT, ZEROG_CHAIN_ID);
        adapter.setErc6551Implementation(ERC6551_IMPL);
        adapter.grantRegistrar(registrar);
        adapter.grantWirer(wirer);

        resolver.grantRegistrar(registrar);

        attestor = new BankonX402Attestor(admin);
        hook     = new BankonAgenticPlaceHook(admin, "https://agenticplace.pythai.net/api/listings");
        hook.grantLister(registrar);
        vm.stopPrank();
    }

    function test_INFTModeA_HappyPath() public {
        // 1. Registrar mints subname (simulated — would call NameWrapper in prod).
        //    Then sets the raw addr to claimant via the resolver.
        vm.prank(registrar);
        resolver.setAddr(SUBNAME_NODE, claimant);
        assertEq(resolver.addr(SUBNAME_NODE), claimant);

        // 2. Registrar emits the InftAdapter mint request.
        vm.prank(registrar);
        adapter.requestMint(PARENT_NODE, LABEL_HASH, claimant, uint256(LABEL_HASH), "ipfs://alice-meta");

        // 3. Off-chain worker mints the iNFT on 0G and reports the tokenId back.
        uint256 zeroGTokenId = 0xc0de;
        vm.prank(wirer);
        adapter.registerZeroGTokenId(LABEL_HASH, zeroGTokenId);
        assertEq(adapter.zeroGTokenIdOf(LABEL_HASH), zeroGTokenId);

        address tba = adapter.tbaAddressOf(LABEL_HASH);
        assertTrue(tba != address(0));

        // 4. Registrar wires the iNFT binding into the resolver.
        vm.prank(registrar);
        resolver.setINFTBinding(SUBNAME_NODE, tba, zeroGTokenId);

        // 5. `addr(node)` now returns the TBA — the iNFT-Mode-A override.
        assertEq(resolver.addr(SUBNAME_NODE), tba, "addr(node) must flip to TBA");
    }

    function test_AgenticPlaceListingEmitted() public {
        // The hook is opt-in per mint. Simulate the registrar choosing to list.
        vm.prank(registrar);
        adapter.requestMint(PARENT_NODE, LABEL_HASH, claimant, uint256(LABEL_HASH), "ipfs://m");

        uint256 tokenId = 7;
        vm.prank(wirer);
        adapter.registerZeroGTokenId(LABEL_HASH, tokenId);

        address tba = adapter.tbaAddressOf(LABEL_HASH);
        vm.prank(registrar);
        vm.expectEmit(true, true, true, true, address(hook));
        emit IBankonAgenticPlaceHook.AgenticPlaceListing(PARENT_NODE, LABEL_HASH, tba, tokenId, "ipfs://m", claimant);
        hook.list(PARENT_NODE, LABEL_HASH, tba, tokenId, "ipfs://m", claimant);
    }
}
