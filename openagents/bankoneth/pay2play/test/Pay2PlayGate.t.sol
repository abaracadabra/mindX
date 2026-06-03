// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {BankonServiceRegistry} from "../src/BankonServiceRegistry.sol";
import {BankonEntitlement}     from "../src/BankonEntitlement.sol";
import {Pay2PlayGate}          from "../src/Pay2PlayGate.sol";
import {IProofOracle}          from "../src/interfaces/IProofOracle.sol";

/// Trivial proof oracle: world-condition met iff proof == keccak256("OPEN").
contract MockProofOracle is IProofOracle {
    function proven(address, bytes32, bytes calldata proof) external pure returns (bool) {
        return proof.length == 32 && bytes32(proof) == keccak256("OPEN");
    }
}

/// Minimal ERC-1155-style balance token (modular-NFT gate stand-in).
contract MockModularNFT {
    mapping(address => mapping(uint256 => uint256)) public bal;
    function mint(address to, uint256 id, uint256 amt) external { bal[to][id] += amt; }
    function balanceOf(address a, uint256 id) external view returns (uint256) { return bal[a][id]; }
}

contract Pay2PlayGateTest is Test {
    BankonEntitlement ent;
    Pay2PlayGate      gate;
    MockProofOracle   oracle;
    MockModularNFT    nft;

    address admin   = address(0xA11CE);
    address granter = address(0x6417E2); // stands in for the router/settlement
    address user;
    uint256 userPk;

    bytes32 constant SVC  = keccak256("deltaverse.member");
    bytes32 constant ROOM = keccak256("deltaverse.room.obsidian");
    uint256 constant NFT_ID = 7;

    function setUp() public {
        (user, userPk) = makeAddrAndKey("member");
        vm.startPrank(admin);
        ent    = new BankonEntitlement(admin);
        gate   = new Pay2PlayGate(admin, ent);
        oracle = new MockProofOracle();
        nft    = new MockModularNFT();
        ent.grantRole(ent.GRANTER_ROLE(), granter);
        gate.setRoom(ROOM, Pay2PlayGate.Room({
            service: SVC,
            proofOracle: address(oracle),
            nft: address(nft),
            nftKind: Pay2PlayGate.NftKind.ERC1155,
            nftId: NFT_ID,
            minNft: 1,
            active: true,
            name: "deltaverse.room.obsidian"
        }));
        vm.stopPrank();
    }

    function _grantMembership() internal {
        vm.prank(granter);
        ent.grant(user, SVC, 5, type(uint64).max); // permanent member, tier 5
    }

    function _openProof() internal pure returns (bytes memory) {
        return abi.encodePacked(keccak256("OPEN"));
    }

    function test_NotEligibleWithoutEntitlement() public {
        assertFalse(gate.eligible(user, ROOM), "no entitlement = ineligible");
    }

    function test_Admit_requiresEntitlement_nft_andWorldProof() public {
        // missing everything
        vm.prank(user);
        vm.expectRevert(abi.encodeWithSelector(Pay2PlayGate.NotEntitled.selector, user, SVC));
        gate.admit(ROOM, _openProof());

        _grantMembership();
        // entitled but no NFT
        vm.prank(user);
        vm.expectRevert(abi.encodeWithSelector(Pay2PlayGate.NftGateFailed.selector, ROOM, user));
        gate.admit(ROOM, _openProof());

        nft.mint(user, NFT_ID, 1);
        assertTrue(gate.eligible(user, ROOM), "now eligible (entitlement + nft)");

        // wrong world proof
        vm.prank(user);
        vm.expectRevert(abi.encodeWithSelector(Pay2PlayGate.WorldProofFailed.selector, ROOM, user));
        gate.admit(ROOM, abi.encodePacked(keccak256("CLOSED")));

        // full admission
        vm.expectEmit(true, true, true, true);
        emit Pay2PlayGate.Admitted(ROOM, user, user);
        vm.prank(user);
        gate.admit(ROOM, _openProof());
    }

    function test_AdmitWithSig_bindsToSigner_seamlessConnect() public {
        _grantMembership();
        nft.mint(user, NFT_ID, 1);

        bytes32 typehash = keccak256("Connect(bytes32 roomId,address user,uint256 nonce)");
        bytes32 structHash = keccak256(abi.encode(typehash, ROOM, user, uint256(0)));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", gate.domainSeparator(), structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(userPk, digest);

        address relayer = address(0x5E1F);
        vm.expectEmit(true, true, true, true);
        emit Pay2PlayGate.Admitted(ROOM, user, relayer);
        vm.prank(relayer);
        gate.admitWithSig(ROOM, user, _openProof(), abi.encodePacked(r, s, v));

        assertEq(gate.nonces(user), 1, "nonce consumed");
    }

    function test_NoOracleNoNft_entitlementOnly() public {
        vm.prank(admin);
        gate.setRoom(keccak256("open.room"), Pay2PlayGate.Room({
            service: SVC, proofOracle: address(0), nft: address(0),
            nftKind: Pay2PlayGate.NftKind.None, nftId: 0, minNft: 0,
            active: true, name: "open.room"
        }));
        _grantMembership();
        assertTrue(gate.eligible(user, keccak256("open.room")), "entitlement-only eligible");
        vm.prank(user);
        gate.admit(keccak256("open.room"), "");
    }
}
