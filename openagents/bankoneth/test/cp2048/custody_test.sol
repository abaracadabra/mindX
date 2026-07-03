// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC1155} from "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import {treasury} from "../../contracts/cp2048/treasury.sol";
import {remittance} from "../../contracts/cp2048/remittance.sol";
import {bankon_custody} from "../../contracts/cp2048/bankon_custody.sol";

contract MockERC20 is ERC20 { constructor() ERC20("M","M"){} function mint(address t,uint256 a) external { _mint(t,a);} }
contract MockERC721 is ERC721 { constructor() ERC721("N","N"){} function mint(address t,uint256 id) external { _mint(t,id);} }
contract MockERC1155 is ERC1155 { constructor() ERC1155("u"){} function mint(address t,uint256 id,uint256 a) external { _mint(t,id,a,"");} }

contract custody_test is Test {
    address founder = address(0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169); // bankon.eth
    address stranger = address(0x57A1);
    treasury t;
    MockERC20 erc20; MockERC721 erc721; MockERC1155 erc1155;

    bytes32 constant DOMAIN_TYPEHASH = keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 constant EXECUTE_TYPEHASH = keccak256("Execute(address target,uint256 value,bytes32 dataHash,uint256 nonce)");

    function setUp() public {
        t = new treasury(founder);
        erc20 = new MockERC20(); erc721 = new MockERC721(); erc1155 = new MockERC1155();
    }

    function test_founding_owner_immutable_and_dictator() public view {
        assertEq(t.FOUNDER(), founder, "founder = bankon.eth");
        assertEq(t.owner(), founder, "owner = bankon.eth at birth");
        assertEq(uint256(t.mode()), uint256(bankon_custody.Mode.DICTATOR), "begins as dictator");
    }

    function test_holds_all_asset_types() public {
        vm.deal(address(t), 5 ether);
        erc20.mint(address(t), 1000e18);
        erc721.mint(address(t), 7);
        erc1155.mint(address(t), 1, 50);
        assertEq(address(t).balance, 5 ether);
        assertEq(erc20.balanceOf(address(t)), 1000e18);
        assertEq(erc721.ownerOf(7), address(t));
        assertEq(erc1155.balanceOf(address(t), 1), 50);
    }

    function test_redeem_sends_only_to_founder_permissionless() public {
        vm.deal(address(t), 3 ether);
        erc20.mint(address(t), 500e18);
        erc721.mint(address(t), 9);
        erc1155.mint(address(t), 2, 40);

        // a stranger can push everything home — destination is the immutable FOUNDER.
        vm.startPrank(stranger);
        t.redeem_native();
        t.redeem_erc20(address(erc20));
        t.redeem_erc721(address(erc721), 9);
        t.redeem_erc1155(address(erc1155), 2, 0);
        vm.stopPrank();

        assertEq(founder.balance, 3 ether, "native home");
        assertEq(erc20.balanceOf(founder), 500e18, "erc20 home");
        assertEq(erc721.ownerOf(9), founder, "erc721 home");
        assertEq(erc1155.balanceOf(founder, 2), 40, "erc1155 home");
        assertEq(address(t).balance, 0);
    }

    function test_allocate_dictator_only() public {
        vm.deal(address(t), 2 ether);
        erc20.mint(address(t), 100e18);
        // stranger cannot allocate
        vm.prank(stranger);
        vm.expectRevert(bankon_custody.not_owner.selector);
        t.allocate_native(stranger, 1 ether);
        // owner (founder, dictator) can allocate to an operational address
        vm.prank(founder);
        t.allocate_erc20(address(erc20), stranger, 40e18);
        assertEq(erc20.balanceOf(stranger), 40e18);
    }

    function test_migration_consensus_shapes() public {
        address[] memory two = new address[](2);
        two[0] = address(0xA1); two[1] = address(0xB2);
        address[] memory three = new address[](3);
        three[0] = address(0xA1); three[1] = address(0xB2); three[2] = address(0xC3);

        // bad shapes rejected
        vm.startPrank(founder);
        vm.expectRevert(bankon_custody.bad_consensus.selector); t.renounce_to(two, 1, false);   // 1:2
        vm.expectRevert(bankon_custody.bad_consensus.selector); t.renounce_to(two, 3, false);    // 3:2
        // 2:2 accepted
        t.renounce_to(two, 2, false);
        vm.stopPrank();
        assertEq(uint256(t.mode()), uint256(bankon_custody.Mode.MULTISIG));
        assertEq(t.threshold(), 2);
        assertEq(t.signerCount(), 2);

        // once multisig, dictator allocate is disabled
        vm.prank(founder);
        vm.expectRevert(bankon_custody.not_dictator.selector);
        t.allocate_native(stranger, 1);
    }

    function test_multisig_execute_two_of_three() public {
        uint256[] memory pk = new uint256[](3);
        pk[0]=0xA11CE; pk[1]=0xB0B; pk[2]=0xCa201;
        address[] memory addrs = new address[](3);
        for (uint i;i<3;i++) addrs[i]=vm.addr(pk[i]);
        // sort (pk,addr) ascending by addr (simple bubble for 3)
        for (uint i;i<3;i++) for (uint j=i+1;j<3;j++) if (addrs[j]<addrs[i]) { (addrs[i],addrs[j])=(addrs[j],addrs[i]); (pk[i],pk[j])=(pk[j],pk[i]); }

        vm.prank(founder); t.renounce_to(addrs, 2, false);
        vm.deal(address(t), 4 ether);

        // 2-of-3 send 1 ether to stranger via execute_signed
        address target = stranger; uint256 value = 1 ether; bytes memory data = "";
        bytes32 digest = _digest(target, value, data, t.nonce());
        bytes[] memory sigs = new bytes[](2);
        sigs[0] = _sig(pk[0], digest);   // lowest address first
        sigs[1] = _sig(pk[1], digest);

        uint256 before = stranger.balance;
        t.execute_signed(target, value, data, sigs);
        assertEq(stranger.balance, before + 1 ether, "2-of-3 executed");
        assertEq(t.nonce(), 1, "nonce bumped");

        // a single signature is below threshold
        bytes32 d2 = _digest(target, value, data, t.nonce());
        bytes[] memory one = new bytes[](1); one[0] = _sig(pk[0], d2);
        vm.expectRevert(bankon_custody.insufficient_approvals.selector);
        t.execute_signed(target, value, data, one);
    }

    function test_state_machine_3of3_can_instate_1to1() public {
        (uint256[] memory pk, address[] memory addrs) = _three_sorted();
        // 1:1 → 3:3 directly
        vm.prank(founder); t.renounce_to(addrs, 3, false);
        assertEq(t.threshold(), 3);
        assertEq(uint256(t.mode()), uint256(bankon_custody.Mode.MULTISIG));

        // 3:3 votes (3 sigs) to instate a 1:1 with a new owner — via execute_signed self-call
        address newOwner = address(0xDEAD11);
        address[] memory one = new address[](1); one[0] = newOwner;
        bytes memory data = abi.encodeWithSelector(bankon_custody.renounce_to.selector, one, uint256(1), false);
        bytes32 digest = _digest(address(t), 0, data, t.nonce());
        bytes[] memory sigs = new bytes[](3);
        for (uint i;i<3;i++) sigs[i] = _sig(pk[i], digest);
        t.execute_signed(address(t), 0, data, sigs);

        assertEq(uint256(t.mode()), uint256(bankon_custody.Mode.DICTATOR), "back to 1:1");
        assertEq(t.owner(), newOwner, "new dictator instated by 3:3 vote");
    }

    function test_optional_permanent_lockout_of_dictator() public {
        (uint256[] memory pk, address[] memory addrs) = _three_sorted();  // signers we hold keys for
        // 1:1 → 2:3 as a COMPLETE, never-return-to-1:1 renounce
        vm.prank(founder); t.renounce_to(addrs, 2, true);
        assertTrue(t.dictator_locked(), "dictatorship permanently locked out");

        // re-keying among multisig shapes still works: 2:3 → 3:3 (authorized by 2-of-3)
        bytes memory toThree = abi.encodeWithSelector(bankon_custody.renounce_to.selector, addrs, uint256(3), false);
        bytes32 d1 = _digestFor(address(t), address(t), 0, toThree, t.nonce());
        bytes[] memory two = new bytes[](2); two[0]=_sig(pk[0], d1); two[1]=_sig(pk[1], d1);
        t.execute_signed(address(t), 0, toThree, two);
        assertEq(t.threshold(), 3, "re-keyed to 3:3");

        // but instating a 1:1 is forbidden forever — even a full 3-of-3 vote reverts
        address[] memory one = new address[](1); one[0]=addrs[0];
        bytes memory toOne = abi.encodeWithSelector(bankon_custody.renounce_to.selector, one, uint256(1), false);
        bytes32 d2 = _digestFor(address(t), address(t), 0, toOne, t.nonce());
        bytes[] memory three = new bytes[](3); for (uint i;i<3;i++) three[i]=_sig(pk[i], d2);
        vm.expectRevert();  // inner renounce_to reverts dictator_locked_out → execute failed
        t.execute_signed(address(t), 0, toOne, three);
    }

    function test_renounce_authorized_by_mode() public {
        address[] memory two = new address[](2); two[0]=address(0xA1); two[1]=address(0xB2);
        vm.prank(founder); t.renounce_to(two, 2, false);   // now multisig
        // a stranger (or even a signer EOA) cannot re-key directly — only via execute_signed self-call
        vm.prank(stranger);
        vm.expectRevert(bankon_custody.not_multisig.selector);
        t.renounce_to(two, 2, false);
    }

    function test_remittance_batch_remit() public {
        remittance r = new remittance(founder);
        vm.deal(address(r), 2 ether);
        erc20.mint(address(r), 300e18);
        address[] memory toks = new address[](1); toks[0]=address(erc20);
        vm.prank(stranger); r.remit(toks);
        assertEq(founder.balance, 2 ether, "native remitted home");
        assertEq(erc20.balanceOf(founder), 300e18, "erc20 remitted home");
    }

    // ── helpers ──
    function _digest(address target, uint256 value, bytes memory data, uint256 nonce_) internal view returns (bytes32) {
        bytes32 domain = keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256("bankon_custody"), keccak256("1"), block.chainid, address(t)));
        bytes32 sh = keccak256(abi.encode(EXECUTE_TYPEHASH, target, value, keccak256(data), nonce_));
        return keccak256(abi.encodePacked("\x19\x01", domain, sh));
    }
    function _sig(uint256 pk, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }
    function _digestFor(address ct, address target, uint256 value, bytes memory data, uint256 nonce_) internal view returns (bytes32) {
        bytes32 domain = keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256("bankon_custody"), keccak256("1"), block.chainid, ct));
        bytes32 sh = keccak256(abi.encode(EXECUTE_TYPEHASH, target, value, keccak256(data), nonce_));
        return keccak256(abi.encodePacked("\x19\x01", domain, sh));
    }
    /// 3 keys + their addresses, sorted ascending by address (parallel arrays).
    function _three_sorted() internal pure returns (uint256[] memory pk, address[] memory addrs) {
        pk = new uint256[](3); pk[0]=0xA11CE; pk[1]=0xB0B; pk[2]=0xCa201;
        addrs = new address[](3); for (uint i;i<3;i++) addrs[i]=vm.addr(pk[i]);
        for (uint i;i<3;i++) for (uint j=i+1;j<3;j++) if (addrs[j]<addrs[i]) { (addrs[i],addrs[j])=(addrs[j],addrs[i]); (pk[i],pk[j])=(pk[j],pk[i]); }
    }
}
