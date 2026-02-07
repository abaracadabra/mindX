// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

import { CurveToken } from "../src/token/CurveToken.sol";
import { BondingCurvePoolNative } from "../src/pool/BondingCurvePoolNative.sol";
import { CurveType } from "../src/math/CurveType.sol";
import { MultiCurveMath } from "../src/math/MultiCurveMath.sol";
import { UD60x18, ud } from "prb-math/UD60x18.sol";

contract BondingCurvePoolNativeTest is Test {
    CurveToken token;
    BondingCurvePoolNative pool;

    address alice = address(0xA11CE);
    address feeRecip = address(0xFEE);

    function setUp() public {
        token = new CurveToken("BOND CURV", "BOND", address(this), 0);

        MultiCurveMath.CurveParams memory cp;
        cp.curveType = CurveType.POWER;
        cp.k = ud(1e12);   // 1e-6 ETH scaling (cheap for tests)
        cp.p = ud(1e18);   // p=1 (linear price)

        pool = new BondingCurvePoolNative(token, cp, address(this));
        token.setPool(address(pool));

        pool.setProtocolFee(200, feeRecip); // 2%
        vm.deal(alice, 100 ether);
        vm.deal(address(pool), 0 ether);
    }

    function testBuyAndSellWithFee() public {
        vm.startPrank(alice);

        uint256 ethIn = 1 ether;
        uint256 feeBefore = feeRecip.balance;

        uint256 out = pool.buy{value: ethIn}(0, alice);
        assertGt(out, 0);
        assertEq(feeRecip.balance - feeBefore, ethIn * 200 / 10_000);

        // Approve + sell half
        token.approve(address(pool), out / 2);
        uint256 ethOut = pool.sell(out / 2, 0, alice);

        assertGt(ethOut, 0);
        vm.stopPrank();
    }

    function testQuoteMatchesBuyApprox() public {
        vm.startPrank(alice);
        uint256 q = pool.quoteBuy(1 ether);
        uint256 out = pool.buy{value: 1 ether}(0, alice);
        assertEq(out, q);
        vm.stopPrank();
    }

    function testCustomTokenNameAndSymbol() public {
        CurveToken customToken = new CurveToken("My Token", "MTK", address(this), 1000e18);
        assertEq(customToken.name(), "My Token");
        assertEq(customToken.symbol(), "MTK");
        assertEq(customToken.balanceOf(address(this)), 1000e18);
    }
}
