// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../DatoCore.sol";
import "../DatoNamingRegistry.sol";
import "../DatoMembership.sol";

contract DatoCoreTest is Test {
    DatoCore core;
    DatoNamingRegistry naming;
    address daio = address(0xDA10);
    address deployer = address(0xDEED);
    address alice = address(0xA11CE);

    function setUp() public {
        DatoCore.Settings memory s = DatoCore.Settings({
            defaultTier: DatoCore.Tier.Immutable,
            joinFeeMicroUSD: 10000,
            openJoin: true,
            maxMembers: 0
        });
        vm.prank(daio);
        core = new DatoCore(daio, deployer, "archive.immutable.blockchain", s);
        naming = new DatoNamingRegistry(daio);
    }

    function test_owner_is_daio_and_deployer_is_founding_member() public view {
        assertEq(core.owner(), daio);
        assertEq(core.deployer(), deployer);
        assertTrue(core.isMember(deployer));
        assertEq(core.memberCount(), 1);
    }

    function test_owner_admits_member() public {
        vm.prank(daio);
        core.admitMember(alice, keccak256("settings"), 10000);
        assertTrue(core.isMember(alice));
        assertEq(core.memberCount(), 2);
    }

    function test_immutable_record_is_hash_locked() public {
        vm.prank(daio);
        core.commitRecord("doc1.immutable.blockchain", keccak256("v1"), DatoCore.Tier.Immutable, "anchor:v1");
        // re-commit same hash ok
        vm.prank(daio);
        core.commitRecord("doc1.immutable.blockchain", keccak256("v1"), DatoCore.Tier.Immutable, "anchor:v1");
        // different hash reverts (immutable lock)
        vm.prank(daio);
        vm.expectRevert(DatoCore.ImmutableLock.selector);
        core.commitRecord("doc1.immutable.blockchain", keccak256("v2"), DatoCore.Tier.Immutable, "anchor:v2");
    }

    function test_mutable_record_versions() public {
        vm.prank(daio);
        core.commitRecord("note.mutable.blockchain", keccak256("a"), DatoCore.Tier.Mutable, "");
        vm.prank(daio);
        uint32 v = core.commitRecord("note.mutable.blockchain", keccak256("b"), DatoCore.Tier.Mutable, "");
        assertEq(v, 2);
    }

    function test_immortal_record_carries_arweave_proof() public {
        vm.prank(daio);
        core.commitRecord("vault.immortal.blockchain", keccak256("bytes"), DatoCore.Tier.Immortal, "arweave://TXID123");
        DatoCore.Record memory r = core.getRecord("vault.immortal.blockchain");
        assertEq(uint8(r.tier), uint8(DatoCore.Tier.Immortal));
        assertEq(r.proof, "arweave://TXID123");
    }

    function test_naming_extensible_roots_and_tier_encoding() public {
        // default root "blockchain" works; add a new root "ar"
        vm.prank(daio);
        bytes32 node = naming.registerName("archive", "immortal", "blockchain", alice, "arweave://TX", address(core), true);
        DatoNamingRegistry.NameRecord memory rec = naming.resolveNode(node);
        assertEq(rec.controller, alice);
        assertEq(rec.tier, 0); // immortal
        assertTrue(rec.soulbound);

        vm.prank(daio);
        naming.addRoot("ar");
        vm.prank(daio);
        naming.registerName("data", "mutable", "ar", alice, "", address(core), false);
        assertEq(naming.rootsCount(), 2);

        // bad tier reverts
        vm.prank(daio);
        vm.expectRevert(DatoNamingRegistry.BadTier.selector);
        naming.registerName("x", "forever", "blockchain", alice, "", address(core), false);
    }

    function test_membership_join_with_fee_admits_on_core() public {
        // owner sets the membership manager as a member-admitter by making it the dato's manager:
        // here we test DatoMembership collects fee + calls admitMember (core.openJoin=true allows self path,
        // but membership calls as msg.sender=manager → must be owner; so transfer core ownership to manager).
        DatoMembership mgr = new DatoMembership(address(core), 1 ether);
        vm.prank(daio);
        core.transferOwnership(address(mgr)); // DAIO delegates admission to the membership manager
        vm.deal(alice, 2 ether);
        vm.prank(alice);
        mgr.requestJoin{value: 1 ether}(keccak256("reader"), "ipfs://settings");
        assertTrue(core.isMember(alice));
        assertEq(mgr.collected(), 1 ether);
    }

    function test_join_fee_too_low_reverts() public {
        DatoMembership mgr = new DatoMembership(address(core), 1 ether);
        vm.prank(daio);
        core.transferOwnership(address(mgr));
        vm.deal(alice, 1 ether);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(DatoMembership.FeeTooLow.selector, uint256(1 ether)));
        mgr.requestJoin{value: 0.5 ether}(keccak256("reader"), "");
    }
}
