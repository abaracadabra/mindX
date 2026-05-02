// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {SpinTradePair} from "../src/SpinTradePair.sol";
import {ISpinTradePair} from "../src/interfaces/ISpinTradePair.sol";
import {SpinTradeFactory} from "../src/SpinTradeFactory.sol";
import {BankonToken} from "../src/tokens/BankonToken.sol";
import {PythaiToken} from "../src/tokens/PythaiToken.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract SpinTradeTest is Test {
    BankonToken bankon;
    PythaiToken pythai;
    SpinTradeFactory factory;
    SpinTradePair    pair;

    address deployer = address(0xDE);
    address alice    = address(0xA1);
    address bob      = address(0xB0);

    function setUp() public {
        vm.startPrank(deployer);
        bankon = new BankonToken(deployer);
        pythai = new PythaiToken(deployer);
        factory = new SpinTradeFactory();
        address pairAddr = factory.createPair(address(bankon), address(pythai));
        pair = SpinTradePair(pairAddr);

        // Fund alice and bob
        bankon.mint(alice, 100_000 ether);
        pythai.mint(alice, 100_000 ether);
        bankon.mint(bob,   10_000 ether);
        pythai.mint(bob,   10_000 ether);
        vm.stopPrank();
    }

    /* ─────────── Factory ─────────── */

    function test_factory_creates_canonical_pair() public {
        // token0 < token1 by address regardless of constructor order
        address t0 = pair.token0();
        address t1 = pair.token1();
        assertTrue(t0 < t1, "canonical ordering broken");
        assertTrue(
            (t0 == address(bankon) && t1 == address(pythai)) ||
            (t0 == address(pythai) && t1 == address(bankon))
        );
    }

    function test_factory_rejects_duplicate() public {
        vm.expectRevert(SpinTradeFactory.PairExists.selector);
        factory.createPair(address(bankon), address(pythai));
        vm.expectRevert(SpinTradeFactory.PairExists.selector);
        factory.createPair(address(pythai), address(bankon));   // reverse args
    }

    function test_factory_rejects_identical() public {
        vm.expectRevert(SpinTradeFactory.IdenticalTokens.selector);
        factory.createPair(address(bankon), address(bankon));
    }

    function test_factory_rejects_zero() public {
        vm.expectRevert(SpinTradeFactory.ZeroAddress.selector);
        factory.createPair(address(0), address(bankon));
    }

    /* ─────────── Liquidity ─────────── */

    function _seedAlice(uint256 a0, uint256 a1) internal returns (uint256 lp) {
        vm.startPrank(alice);
        bankon.approve(address(pair), type(uint256).max);
        pythai.approve(address(pair), type(uint256).max);
        // canonical mapping: depending on ordering pass amounts via token0/token1 mapping
        (uint256 amount0, uint256 amount1) = pair.token0() == address(bankon) ? (a0, a1) : (a1, a0);
        lp = pair.addLiquidity(amount0, amount1, alice);
        vm.stopPrank();
    }

    function test_addLiquidity_first_LP_is_geometric_mean_minus_dust() public {
        uint256 lp = _seedAlice(1_000 ether, 4_000 ether);
        // sqrt(1000e18 * 4000e18) = sqrt(4e6 * 1e36) = 2000e18
        // minus MINIMUM_LIQUIDITY (1000) locked
        assertEq(lp, 2_000 ether - 1000);
        assertEq(pair.balanceOf(alice), 2_000 ether - 1000);
        assertEq(pair.balanceOf(address(0xdead)), 1000);
    }

    function test_addLiquidity_second_LP_proportional() public {
        _seedAlice(1_000 ether, 4_000 ether);
        // Bob adds 250/1000 = 1/4 of pool → should mint 1/4 of total LP
        vm.startPrank(bob);
        bankon.approve(address(pair), type(uint256).max);
        pythai.approve(address(pair), type(uint256).max);
        (uint256 b0, uint256 b1) = pair.token0() == address(bankon) ? (uint256(250 ether), uint256(1_000 ether)) : (uint256(1_000 ether), uint256(250 ether));
        uint256 lp = pair.addLiquidity(b0, b1, bob);
        vm.stopPrank();
        // Total supply was 2000e18 (incl 1000 dust); 1/4 of that ≈ 500e18
        assertApproxEqRel(lp, 500 ether, 1e15); // 0.1% tolerance
    }

    function test_addLiquidity_imbalanced_picks_smaller_share() public {
        _seedAlice(1_000 ether, 4_000 ether);
        // Bob deposits 250 BANKON + 4000 PYTHAI (over-supplies PYTHAI)
        // LP should be capped at the BANKON ratio (1/4 of total)
        vm.startPrank(bob);
        bankon.approve(address(pair), type(uint256).max);
        pythai.approve(address(pair), type(uint256).max);
        (uint256 b0, uint256 b1) = pair.token0() == address(bankon) ? (uint256(250 ether), uint256(4_000 ether)) : (uint256(4_000 ether), uint256(250 ether));
        uint256 lp = pair.addLiquidity(b0, b1, bob);
        vm.stopPrank();
        assertApproxEqRel(lp, 500 ether, 1e15);
    }

    function test_addLiquidity_rejects_zero() public {
        vm.startPrank(alice);
        bankon.approve(address(pair), type(uint256).max);
        pythai.approve(address(pair), type(uint256).max);
        vm.expectRevert(ISpinTradePair.ZeroAmount.selector);
        pair.addLiquidity(0, 1 ether, alice);
        vm.expectRevert(ISpinTradePair.ZeroAmount.selector);
        pair.addLiquidity(1 ether, 0, alice);
        vm.stopPrank();
    }

    /* ─────────── Quote ─────────── */

    function test_quote_zero_amount_reverts() public {
        _seedAlice(1_000 ether, 4_000 ether);
        vm.expectRevert(ISpinTradePair.ZeroAmount.selector);
        pair.quote(0, address(bankon));
    }

    function test_quote_invalid_token_reverts() public {
        _seedAlice(1_000 ether, 4_000 ether);
        vm.expectRevert(ISpinTradePair.InvalidToken.selector);
        pair.quote(1 ether, address(0xBEEF));
    }

    function test_quote_matches_v2_formula() public {
        _seedAlice(1_000 ether, 4_000 ether);
        // Selling 100 BANKON. Reserves: 1000 BANKON, 4000 PYTHAI.
        // amountInWithFee = 100e18 * 997 = 99700e18
        // numerator       = 99700e18 * 4000e18
        // denominator     = 1000e18 * 1000 + 99700e18 = 1099700e18
        // out             = numerator / denominator ≈ 362.644 PYTHAI (398800/1099700 * 1e18)
        uint256 out = pair.quote(100 ether, address(bankon));
        assertApproxEqRel(out, 362_644_357_552_059_652_632, 1e14); // 0.01% tolerance
    }

    /* ─────────── Swap ─────────── */

    function test_swap_executes_and_emits() public {
        _seedAlice(1_000 ether, 4_000 ether);
        uint256 expected = pair.quote(100 ether, address(bankon));
        uint256 bobPythaiBefore = pythai.balanceOf(bob);

        vm.startPrank(bob);
        bankon.approve(address(pair), type(uint256).max);
        vm.expectEmit(true, true, true, true);
        emit ISpinTradePair.Swap(bob, address(bankon), 100 ether, expected, bob);
        uint256 amountOut = pair.swap(100 ether, address(bankon), 0, bob);
        vm.stopPrank();

        assertEq(amountOut, expected);
        assertEq(pythai.balanceOf(bob), bobPythaiBefore + expected);
    }

    function test_swap_slippage_protection() public {
        _seedAlice(1_000 ether, 4_000 ether);
        uint256 expected = pair.quote(100 ether, address(bankon));

        vm.startPrank(bob);
        bankon.approve(address(pair), type(uint256).max);
        vm.expectRevert(ISpinTradePair.InsufficientOutput.selector);
        pair.swap(100 ether, address(bankon), expected + 1, bob);
        vm.stopPrank();
    }

    function test_swap_invalid_token_reverts() public {
        _seedAlice(1_000 ether, 4_000 ether);
        vm.startPrank(bob);
        vm.expectRevert(ISpinTradePair.InvalidToken.selector);
        pair.swap(1 ether, address(0xCAFE), 0, bob);
        vm.stopPrank();
    }

    function test_swap_no_liquidity_reverts() public {
        // No addLiquidity yet
        vm.startPrank(bob);
        bankon.approve(address(pair), type(uint256).max);
        vm.expectRevert(ISpinTradePair.InsufficientLiquidity.selector);
        pair.swap(1 ether, address(bankon), 0, bob);
        vm.stopPrank();
    }

    function test_swap_two_directions_round_trip_loses_fees() public {
        _seedAlice(1_000 ether, 4_000 ether);
        vm.startPrank(bob);
        bankon.approve(address(pair), type(uint256).max);
        pythai.approve(address(pair), type(uint256).max);

        // Swap 100 BANKON → PYTHAI
        uint256 pythaiOut = pair.swap(100 ether, address(bankon), 0, bob);
        // Swap that PYTHAI back → BANKON
        uint256 bankonBack = pair.swap(pythaiOut, address(pythai), 0, bob);
        vm.stopPrank();

        // Fees compound: should get back less than 100 (~99.4 from 2x 0.3% fee)
        assertLt(bankonBack, 100 ether);
        assertGt(bankonBack, 99 ether); // but not catastrophically less
    }

    /* ─────────── removeLiquidity ─────────── */

    function test_removeLiquidity_returns_proportional_share() public {
        uint256 lp = _seedAlice(1_000 ether, 4_000 ether);

        // Burn half of LP, expect ~half of reserves back
        vm.startPrank(alice);
        (uint256 amt0, uint256 amt1) = pair.removeLiquidity(lp / 2, alice);
        vm.stopPrank();

        // After dust lock, alice owns lp = 2000e18 - 1000.
        // Burning lp/2 returns approximately half of the underlying.
        (uint256 expected0, uint256 expected1) = pair.token0() == address(bankon)
            ? (uint256(500 ether), uint256(2_000 ether))
            : (uint256(2_000 ether), uint256(500 ether));
        assertApproxEqRel(amt0, expected0, 1e14);
        assertApproxEqRel(amt1, expected1, 1e14);
    }

    /* ─────────── Reserve invariant ─────────── */

    function test_swap_preserves_k_after_fee() public {
        _seedAlice(1_000 ether, 4_000 ether);
        (uint256 r0Before, uint256 r1Before, ) = pair.reserves();
        uint256 kBefore = r0Before * r1Before;

        vm.startPrank(bob);
        bankon.approve(address(pair), type(uint256).max);
        pair.swap(100 ether, address(bankon), 0, bob);
        vm.stopPrank();

        (uint256 r0After, uint256 r1After, ) = pair.reserves();
        uint256 kAfter = r0After * r1After;
        // k must INCREASE post-swap because the 0.3% fee stays in the pool.
        assertGt(kAfter, kBefore);
    }
}
