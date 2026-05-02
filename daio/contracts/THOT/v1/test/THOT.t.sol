// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {THOT_v1} from "../THOT.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";

/// @notice Foundry suite for THOT v1 commit() primitive.
contract THOT_v1_Test is Test {
    THOT_v1 internal thot;
    address internal admin   = address(0xA11CE);
    address internal pillar1 = address(0xB0B);
    address internal pillar2 = address(0xB1B);
    address internal author  = address(0xCA11);
    address internal provider = address(0x06);

    bytes32 internal constant ROOT_A   = bytes32(uint256(0x11AA));
    bytes32 internal constant ROOT_B   = bytes32(uint256(0x22BB));
    bytes32 internal constant CHAT_A   = bytes32(uint256(0xC0FFEE));
    bytes32 internal constant CHAT_B   = bytes32(uint256(0xDECAF));

    function setUp() public {
        thot = new THOT_v1("mindX THOT v1", "THOT", admin);
        bytes32 pillarRole = thot.PILLAR_ROLE();
        vm.startPrank(admin);
        thot.grantRole(pillarRole, pillar1);
        thot.grantRole(pillarRole, pillar2);
        vm.stopPrank();
    }

    /* ────────── Construction ────────── */

    function test_Constructor_setsRolesAndName() public view {
        assertEq(thot.name(), "mindX THOT v1");
        assertEq(thot.symbol(), "THOT");
        assertTrue(thot.hasRole(thot.DEFAULT_ADMIN_ROLE(), admin));
    }

    function test_Constructor_revertsOnZeroAdmin() public {
        vm.expectRevert(THOT_v1.ZeroAddress.selector);
        new THOT_v1("X", "X", address(0));
    }

    /* ────────── Mint happy-path ────────── */

    function test_Commit_mintsTokenAndIndexesRoot() public {
        vm.prank(pillar1);
        uint256 id = thot.commit(author, ROOT_A, CHAT_A, provider, bytes32(0));
        uint256 expected = uint256(keccak256(abi.encodePacked(author, ROOT_A, CHAT_A)));
        assertEq(id, expected);
        assertEq(thot.ownerOf(id), author);
        assertEq(thot.rootIndex(ROOT_A), id);
        assertEq(thot.tokenOfRoot(ROOT_A), id);

        (bytes32 r, bytes32 c, address p, bytes32 par, , address pl, address au) =
            _readMemory(id);
        assertEq(r, ROOT_A);
        assertEq(c, CHAT_A);
        assertEq(p, provider);
        assertEq(par, bytes32(0));
        assertEq(pl, pillar1);
        assertEq(au, author);
    }

    function test_Commit_idempotentOnDuplicate() public {
        vm.prank(pillar1);
        uint256 first = thot.commit(author, ROOT_A, CHAT_A, provider, bytes32(0));

        // Second commit of the same (author, rootHash, chatID) returns same id, no new mint.
        vm.prank(pillar2);
        uint256 second = thot.commit(author, ROOT_A, CHAT_A, provider, bytes32(0));
        assertEq(first, second);
    }

    function test_Commit_emitsEvent() public {
        uint256 expectedId = uint256(keccak256(abi.encodePacked(author, ROOT_A, CHAT_A)));
        vm.expectEmit(true, true, true, true);
        emit THOT_v1.MemoryCommitted(expectedId, pillar1, author, ROOT_A, CHAT_A, provider, bytes32(0));
        vm.prank(pillar1);
        thot.commit(author, ROOT_A, CHAT_A, provider, bytes32(0));
    }

    /* ────────── Pillar role gating ────────── */

    function test_Commit_revertsForNonPillar() public {
        bytes32 pillarRole = thot.PILLAR_ROLE();
        address rando = address(0xDEAD);
        vm.prank(rando);
        vm.expectRevert(abi.encodeWithSelector(
            IAccessControl.AccessControlUnauthorizedAccount.selector, rando, pillarRole
        ));
        thot.commit(author, ROOT_A, CHAT_A, provider, bytes32(0));
    }

    function test_RevokePillarRole_blocksFurtherCommits() public {
        bytes32 pillarRole = thot.PILLAR_ROLE();
        vm.prank(admin);
        thot.revokeRole(pillarRole, pillar1);
        vm.prank(pillar1);
        vm.expectRevert();
        thot.commit(author, ROOT_A, CHAT_A, provider, bytes32(0));
    }

    /* ────────── Input validation ────────── */

    function test_Commit_revertsOnZeroAuthor() public {
        vm.prank(pillar1);
        vm.expectRevert(THOT_v1.ZeroAddress.selector);
        thot.commit(address(0), ROOT_A, CHAT_A, provider, bytes32(0));
    }

    function test_Commit_revertsOnZeroRootHash() public {
        vm.prank(pillar1);
        vm.expectRevert(THOT_v1.ZeroBytes32.selector);
        thot.commit(author, bytes32(0), CHAT_A, provider, bytes32(0));
    }

    function test_Commit_revertsOnZeroChatID() public {
        vm.prank(pillar1);
        vm.expectRevert(THOT_v1.ZeroBytes32.selector);
        thot.commit(author, ROOT_A, bytes32(0), provider, bytes32(0));
    }

    /* ────────── Parent DAG ────────── */

    function test_Commit_acceptsKnownParent() public {
        // Anchor the parent first.
        vm.prank(pillar1);
        thot.commit(author, ROOT_A, CHAT_A, provider, bytes32(0));

        // Child references the parent root.
        vm.prank(pillar1);
        uint256 child = thot.commit(author, ROOT_B, CHAT_B, provider, ROOT_A);

        ( , , , bytes32 parent, , , ) = _readMemory(child);
        assertEq(parent, ROOT_A);
    }

    function test_Commit_revertsOnUnknownParent() public {
        bytes32 unknown = bytes32(uint256(0x99FFFF));
        vm.prank(pillar1);
        vm.expectRevert(abi.encodeWithSelector(THOT_v1.UnknownParent.selector, unknown));
        thot.commit(author, ROOT_A, CHAT_A, provider, unknown);
    }

    function test_RootIndex_pointsAtFirstCommit() public {
        vm.prank(pillar1);
        uint256 first = thot.commit(author, ROOT_A, CHAT_A, provider, bytes32(0));
        // Same rootHash but different chatID: a NEW token, but rootIndex stays
        // pointing at the first commit (canonical).
        vm.prank(pillar1);
        uint256 second = thot.commit(author, ROOT_A, CHAT_B, provider, bytes32(0));
        assertTrue(first != second);
        assertEq(thot.rootIndex(ROOT_A), first);
    }

    /* ────────── Interface support ────────── */

    function test_SupportsInterface_advertisesAll() public view {
        assertTrue(thot.supportsInterface(0x80ac58cd));   // ERC-721
        assertTrue(thot.supportsInterface(0x01ffc9a7));   // ERC-165
        assertTrue(thot.supportsInterface(type(IAccessControl).interfaceId));
    }

    /* ────────── Helpers ────────── */

    function _readMemory(uint256 id) internal view
        returns (bytes32, bytes32, address, bytes32, uint40, address, address)
    {
        (bytes32 r, bytes32 c, address p, bytes32 par, uint40 t, address pl, address au)
            = thot.memories(id);
        return (r, c, p, par, t, pl, au);
    }
}
