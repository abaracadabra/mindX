// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {Conclave} from "../src/Conclave.sol";
import {ConclaveBond} from "../src/ConclaveBond.sol";
import {ITessera} from "../src/interfaces/ITessera.sol";
import {ICensura} from "../src/interfaces/ICensura.sol";

/// @dev Mocks. Replace with the real BONAFIDE deployments at script time.
contract MockTessera is ITessera {
    mapping(address => bool) public valid;
    mapping(address => string) public dids;
    mapping(address => bytes32) public keys;

    function setValid(address h, bool v) external { valid[h] = v; }
    function setKey(address h, bytes32 k) external { keys[h] = k; }
    function setDid(address h, string calldata d) external { dids[h] = d; }

    function hasValidCredential(address h) external view returns (bool) {
        return valid[h];
    }
    function didOf(address h) external view returns (string memory) {
        return dids[h];
    }
    function transportKeyOf(address h) external view returns (bytes32) {
        return keys[h];
    }
}

contract MockCensura is ICensura {
    mapping(address => uint8) public scores;
    function setScore(address s, uint8 v) external { scores[s] = v; }
    function score(address s) external view returns (uint8) {
        return scores[s];
    }
    function report(address, bytes32) external pure {}
}

contract ConclaveTest is Test {
    Conclave conclave;
    ConclaveBond bondCtr;
    MockTessera tessera;
    MockCensura censura;

    address constant CEO  = address(0xC1);
    address constant COO  = address(0xC2);
    address constant CFO  = address(0xC3);
    address constant CTO  = address(0xC4);
    address constant CISO = address(0xC5);
    address constant GC   = address(0xC6);
    address constant COS  = address(0xC7);
    address constant OPS  = address(0xC8);
    address constant LEAKER = COO;

    bytes32 constant CONCLAVE_ID = keccak256("Cabinet-Q3-2026");
    bytes32 constant SESSION_ID  = keccak256("session-1");
    bytes32 constant MOTION_ID   = keccak256("motion-1");
    bytes32 constant RES_HASH    = keccak256("resolution-1");
    uint256 constant BOND_AMOUNT = 1 ether;
    uint8   constant CENSURA_MIN = 50;

    function setUp() public {
        tessera = new MockTessera();
        censura = new MockCensura();

        // The two contracts have circular immutable references:
        //   Conclave._bond       = bondCtr
        //   ConclaveBond.conclave = conclave
        // Predict bondCtr's address before deploying conclave.
        // Our two upcoming deployments will use this contract's
        // current nonce and current+1 respectively.
        uint64 myNonce = vm.getNonce(address(this));
        address predictedBond = computeCreateAddress(address(this), myNonce + 1);

        conclave = new Conclave(
            address(tessera), address(censura), predictedBond
        );
        bondCtr = new ConclaveBond(address(conclave), address(0));
        require(address(bondCtr) == predictedBond, "bond address mismatch");

        // Seat each Cabinet member with mock Tessera + Censura.
        address[8] memory all = [CEO, COO, CFO, CTO, CISO, GC, COS, OPS];
        for (uint256 i = 0; i < all.length; ++i) {
            tessera.setValid(all[i], true);
            tessera.setKey(all[i], bytes32(uint256(i + 1)));
            censura.setScore(all[i], 200);
            // Fund and post bond.
            vm.deal(all[i], 10 ether);
            vm.prank(all[i]);
            bondCtr.postBond{value: BOND_AMOUNT}(CONCLAVE_ID, BOND_AMOUNT);
        }
    }

    function _registerCabinet() internal {
        address[] memory members = new address[](8);
        bytes32[] memory pubkeys = new bytes32[](8);
        uint8[] memory roles = new uint8[](8);
        address[8] memory all = [CEO, COO, CFO, CTO, CISO, GC, COS, OPS];
        for (uint256 i = 0; i < 8; ++i) {
            members[i] = all[i];
            pubkeys[i] = bytes32(uint256(i + 1));
            roles[i] = uint8(i);
        }
        vm.prank(CEO);
        conclave.registerConclave(
            CONCLAVE_ID, members, pubkeys, roles, CENSURA_MIN, BOND_AMOUNT
        );
    }

    // ------------------------------------------------------------ //
    // Tests                                                        //
    // ------------------------------------------------------------ //

    function test_register_and_seated() public {
        _registerCabinet();
        assertEq(conclave.memberCount(CONCLAVE_ID), 8);
        assertEq(conclave.convenerOf(CONCLAVE_ID), CEO);
        assertTrue(conclave.isMemberSeated(CONCLAVE_ID, CEO));
        assertTrue(conclave.isMemberSeated(CONCLAVE_ID, OPS));
    }

    function test_unseated_when_tessera_revoked() public {
        _registerCabinet();
        tessera.setValid(CFO, false);
        assertFalse(conclave.isMemberSeated(CONCLAVE_ID, CFO));
        assertTrue(conclave.isMemberSeated(CONCLAVE_ID, CEO));
    }

    function test_unseated_when_censura_below_min() public {
        _registerCabinet();
        censura.setScore(CTO, 10);  // < 50
        assertFalse(conclave.isMemberSeated(CONCLAVE_ID, CTO));
    }

    function test_record_resolution_with_quorum() public {
        _registerCabinet();
        address[] memory voters = new address[](5);
        voters[0] = CEO;
        voters[1] = CFO;
        voters[2] = CTO;
        voters[3] = GC;
        voters[4] = COO;

        vm.prank(CEO);
        conclave.recordResolution(
            CONCLAVE_ID, SESSION_ID, MOTION_ID, RES_HASH, voters, true
        );
        assertEq(
            conclave.resolutionOf(CONCLAVE_ID, SESSION_ID, MOTION_ID),
            RES_HASH
        );
    }

    function test_record_reverts_when_voter_unseated() public {
        _registerCabinet();
        address[] memory voters = new address[](5);
        voters[0] = CEO;
        voters[1] = CFO;
        voters[2] = CTO;
        voters[3] = GC;
        voters[4] = COO;

        // Revoke CFO's tessera -> not seated
        tessera.setValid(CFO, false);

        vm.prank(CEO);
        vm.expectRevert(
            abi.encodeWithSelector(Conclave.MemberNotSeated.selector, CFO)
        );
        conclave.recordResolution(
            CONCLAVE_ID, SESSION_ID, MOTION_ID, RES_HASH, voters, true
        );
    }

    function test_double_anchor_reverts() public {
        _registerCabinet();
        address[] memory voters = new address[](5);
        voters[0] = CEO;
        voters[1] = CFO;
        voters[2] = CTO;
        voters[3] = GC;
        voters[4] = COO;

        vm.prank(CEO);
        conclave.recordResolution(
            CONCLAVE_ID, SESSION_ID, MOTION_ID, RES_HASH, voters, true
        );
        vm.prank(CEO);
        vm.expectRevert(Conclave.AlreadyAnchored.selector);
        conclave.recordResolution(
            CONCLAVE_ID, SESSION_ID, MOTION_ID, RES_HASH, voters, true
        );
    }

    function test_only_convener_anchors() public {
        _registerCabinet();
        address[] memory voters = new address[](1);
        voters[0] = CEO;
        vm.prank(COO);
        vm.expectRevert(Conclave.NotConvener.selector);
        conclave.recordResolution(
            CONCLAVE_ID, SESSION_ID, MOTION_ID, RES_HASH, voters, true
        );
    }

    function test_slash_unseats_and_burns_bond() public {
        _registerCabinet();
        uint256 leakerBondBefore = bondCtr.bondOf(CONCLAVE_ID, LEAKER);
        assertEq(leakerBondBefore, BOND_AMOUNT);

        vm.prank(CEO);
        conclave.slashForLeak(CONCLAVE_ID, SESSION_ID, LEAKER, hex"deadbeef");

        assertFalse(conclave.isMemberSeated(CONCLAVE_ID, LEAKER));
        assertEq(bondCtr.bondOf(CONCLAVE_ID, LEAKER), 0);
    }

    function test_register_rejects_length_mismatch() public {
        address[] memory members = new address[](2);
        members[0] = CEO; members[1] = COO;
        bytes32[] memory pubkeys = new bytes32[](1);
        pubkeys[0] = bytes32(uint256(1));
        uint8[] memory roles = new uint8[](2);
        roles[0] = 0; roles[1] = 1;

        vm.prank(CEO);
        vm.expectRevert(Conclave.LengthMismatch.selector);
        conclave.registerConclave(
            CONCLAVE_ID, members, pubkeys, roles, CENSURA_MIN, BOND_AMOUNT
        );
    }

    function test_register_rejects_duplicate() public {
        _registerCabinet();
        address[] memory members = new address[](1);
        members[0] = CEO;
        bytes32[] memory pubkeys = new bytes32[](1);
        pubkeys[0] = bytes32(uint256(1));
        uint8[] memory roles = new uint8[](1);
        roles[0] = 0;

        vm.prank(CEO);
        vm.expectRevert(Conclave.ConclaveExists.selector);
        conclave.registerConclave(
            CONCLAVE_ID, members, pubkeys, roles, CENSURA_MIN, BOND_AMOUNT
        );
    }
}
