// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
// Security-audit PoCs for the custody contracts (adversarial verification).
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {treasury} from "../../contracts/cp2048/treasury.sol";
import {bankon_custody} from "../../contracts/cp2048/bankon_custody.sol";

/// Malicious contract: when called by the treasury (via execute), tries to re-enter.
contract Reenter {
    treasury public t;
    function set(treasury _t) external { t = _t; }
    function attack() external { t.redeem_native(); }          // re-entry attempt
    receive() external payable { t.redeem_native(); }          // re-entry on value receipt
}

contract custody_poc_test is Test {
    address founder = address(0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169);
    address stranger = address(0x57A1);
    treasury t;

    bytes32 constant DOMAIN_TYPEHASH = keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 constant EXECUTE_TYPEHASH = keccak256("Execute(address target,uint256 value,bytes32 dataHash,uint256 nonce)");

    function setUp() public { t = new treasury(founder); }

    function _three_sorted() internal pure returns (uint256[] memory pk, address[] memory a) {
        pk = new uint256[](3); pk[0]=0xA11CE; pk[1]=0xB0B; pk[2]=0xCa201;
        a = new address[](3); for (uint i;i<3;i++) a[i]=vm.addr(pk[i]);
        for (uint i;i<3;i++) for (uint j=i+1;j<3;j++) if (a[j]<a[i]) { (a[i],a[j])=(a[j],a[i]); (pk[i],pk[j])=(pk[j],pk[i]); }
    }
    function _digest(address target, uint256 value, bytes memory data, uint256 n) internal view returns (bytes32) {
        bytes32 dom = keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256("bankon_custody"), keccak256("1"), block.chainid, address(t)));
        bytes32 sh = keccak256(abi.encode(EXECUTE_TYPEHASH, target, value, keccak256(data), n));
        return keccak256(abi.encodePacked("\x19\x01", dom, sh));
    }
    function _sig(uint256 pk, bytes32 d) internal pure returns (bytes memory) { (uint8 v,bytes32 r,bytes32 s)=vm.sign(pk,d); return abi.encodePacked(r,s,v); }

    /// PoC: a multisig signature bundle cannot be replayed (nonce advances).
    function test_poc_no_signature_replay() public {
        (uint256[] memory pk, address[] memory a) = _three_sorted();
        vm.prank(founder); t.renounce_to(a, 2, false);
        vm.deal(address(t), 3 ether);

        bytes memory data = "";
        bytes32 d = _digest(stranger, 1 ether, data, t.nonce());
        bytes[] memory sigs = new bytes[](2); sigs[0]=_sig(pk[0],d); sigs[1]=_sig(pk[1],d);

        t.execute_signed(stranger, 1 ether, data, sigs);          // first use OK
        assertEq(t.nonce(), 1);

        // replay the exact same sigs → digest now binds nonce=1, recovered addrs are garbage → revert
        vm.expectRevert();
        t.execute_signed(stranger, 1 ether, data, sigs);
    }

    /// PoC: cross-contract reentrancy through execute is blocked by the shared guard.
    function test_poc_reentrancy_blocked() public {
        Reenter r = new Reenter(); r.set(t);
        vm.deal(address(t), 2 ether);
        // owner (dictator) executes a call into the malicious contract, which re-enters redeem_native.
        bytes memory data = abi.encodeWithSelector(Reenter.attack.selector);
        vm.prank(founder);
        vm.expectRevert();                                         // ReentrancyGuardReentrantCall
        t.execute(address(r), 0, data);
    }

    /// PoC: a stranger can never move assets to a non-FOUNDER address (no outbound path).
    function test_poc_stranger_cannot_exfiltrate() public {
        vm.deal(address(t), 5 ether);
        vm.startPrank(stranger);
        vm.expectRevert(bankon_custody.not_owner.selector);  t.allocate_native(stranger, 1 ether);
        vm.expectRevert(bankon_custody.not_multisig.selector);
        bytes[] memory none = new bytes[](0);
        t.execute_signed(stranger, 1 ether, "", none);
        vm.stopPrank();
        // the only thing a stranger can do is push it HOME
        vm.prank(stranger); t.redeem_native();
        assertEq(founder.balance, 5 ether);
    }
}
