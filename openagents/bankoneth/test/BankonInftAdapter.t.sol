// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console}        from "forge-std/Test.sol";
import {BankonInftAdapter}    from "../contracts/BankonInftAdapter.sol";
import {BankonSubnameResolver} from "../contracts/BankonSubnameResolver.sol";
import {IBankonSubnameResolver, IBankonInftAdapter}
    from "../contracts/interfaces/IBankonExtensions.sol";

contract BankonInftAdapterTest is Test {
    BankonSubnameResolver resolver;
    BankonInftAdapter     adapter;

    address admin     = makeAddr("admin");
    address registrar = makeAddr("registrar");
    address wirer     = makeAddr("wirer");
    address claimant  = makeAddr("claimant");

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
        vm.stopPrank();
    }

    function test_RequestMintEmits() public {
        bytes32 parent = bytes32(uint256(0xbacc));
        bytes32 label  = keccak256("alice");

        vm.prank(registrar);
        vm.expectEmit(true, true, true, true, address(adapter));
        emit IBankonInftAdapter.RequestINFTMint(parent, label, claimant, uint256(label), "ipfs://meta");
        adapter.requestMint(parent, label, claimant, uint256(label), "ipfs://meta");
    }

    function test_RequestMintTwiceForSameLabelReverts() public {
        bytes32 parent = bytes32(uint256(0xbacc));
        bytes32 label  = keccak256("alice");

        vm.prank(registrar);
        adapter.requestMint(parent, label, claimant, uint256(label), "ipfs://meta");

        // Without registerZeroGTokenId being called the registry slot is still 0
        // for tokenId, so duplicate detection guards against re-requesting after
        // tokenId is bound. Bind it now:
        vm.prank(wirer);
        adapter.registerZeroGTokenId(label, 999);

        vm.prank(registrar);
        vm.expectRevert(abi.encodeWithSelector(BankonInftAdapter.LabelAlreadyBound.selector, label));
        adapter.requestMint(parent, label, claimant, uint256(label), "ipfs://meta-2");
    }

    function test_TbaIsDeterministic() public {
        bytes32 label = keccak256("deterministic");
        vm.prank(wirer);
        adapter.registerZeroGTokenId(label, 1);

        address tba1 = adapter.tbaAddressOf(label);
        assertTrue(tba1 != address(0));

        // Re-registering the same labelhash → tokenId pair would revert (already bound),
        // so verify a *different* labelhash with the same tokenId produces a *different*
        // TBA (because TBA depends on tokenId only, all else equal, both produce the
        // same TBA — assert that property here).
        bytes32 otherLabel = keccak256("other");
        vm.prank(wirer);
        adapter.registerZeroGTokenId(otherLabel, 1);
        assertEq(adapter.tbaAddressOf(otherLabel), tba1, "same tokenId => same TBA");
    }

    function test_NonWirerCannotRegister() public {
        vm.prank(claimant);
        vm.expectRevert();
        adapter.registerZeroGTokenId(keccak256("nope"), 1);
    }
}
