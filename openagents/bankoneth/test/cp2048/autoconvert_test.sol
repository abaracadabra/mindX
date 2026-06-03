// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {bankon_autoconvert, ISwapRouterV3} from "../../contracts/cp2048/bankon_autoconvert.sol";
import {bridge_collect} from "../../contracts/cp2048/bridge_collect.sol";
import {scientific_math} from "../../contracts/cp2048/scientific_math.sol";

contract MockERC20 is ERC20 {
    constructor(string memory n, string memory s) ERC20(n, s) {}
    function mint(address to, uint256 a) external { _mint(to, a); }
}

contract cp2048_flow_test is Test {
    address admin = address(0xC0DE);
    address rakeAddr = address(0x4A4E);   // stand-in RAKE collector
    address payer = address(0xBEEF);
    address recipient = address(0x4EC0);

    function test_autoconvert_same_token_routes_fee_to_rake() public {
        MockERC20 usdc = new MockERC20("USDC", "USDC");
        bankon_autoconvert ac = new bankon_autoconvert(admin, ISwapRouterV3(address(0)), rakeAddr, 10_000);
        uint256 amt = 1000e18;
        usdc.mint(payer, amt);
        vm.prank(payer); usdc.approve(address(ac), amt);

        uint256 expectedFee = scientific_math.goldenFeeWad(amt, 10_000);
        vm.prank(payer);
        uint256 out = ac.convert(address(usdc), amt, address(usdc), 0, 0, recipient);

        assertEq(usdc.balanceOf(rakeAddr), expectedFee, "fee to RAKE");
        assertEq(usdc.balanceOf(recipient), amt - expectedFee, "remainder to recipient");
        assertEq(out, amt - expectedFee);
        assertGt(expectedFee, 0);
    }

    function test_bridge_collect_routes_fee_and_emits() public {
        MockERC20 tok = new MockERC20("Tok", "TOK");
        bridge_collect bc = new bridge_collect(admin, rakeAddr, 10_000);
        uint256 amt = 500e18;
        tok.mint(payer, amt);
        vm.prank(payer); tok.approve(address(bc), amt);

        uint256 expectedFee = scientific_math.goldenFeeWad(amt, 10_000);
        vm.prank(payer);
        uint256 fwd = bc.collect_for_bridge(address(tok), amt, 8453, bytes32("alice.bankon.eth"), recipient);

        assertEq(tok.balanceOf(rakeAddr), expectedFee, "fee to RAKE");
        assertEq(fwd, amt - expectedFee);
        assertEq(tok.balanceOf(address(bc)), amt - expectedFee, "remainder held for relayer");
    }
}
