// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

import { CurveToken } from "../src/token/CurveToken.sol";
import { BondingCurvePoolNative } from "../src/pool/BondingCurvePoolNative.sol";
import { CurveType } from "../src/math/CurveType.sol";
import { MultiCurveMath } from "../src/math/MultiCurveMath.sol";
import { UD60x18, ud } from "prb-math/UD60x18.sol";

import { BondingCurvePresaleSMAIRT } from "../src/extensions/BondingCurvePresaleSMAIRT.sol";
import { UniV2Provisioner } from "../src/liquidity/provisioners/UniV2Provisioner.sol";
import { ILiquidityProvisioner } from "../src/liquidity/ILiquidityProvisioner.sol";

import { MockUniswapV2Router } from "./mocks/MockUniswapV2Router.sol";

contract PresaleSMAIRTTest is Test {
    CurveToken token;
    BondingCurvePoolNative pool;

    UniV2Provisioner provisioner;
    MockUniswapV2Router router;

    address weth = address(0xBEEF);

    address owner = address(this);
    address alice = address(0xA11CE);
    address bob = address(0xB0B);

    function setUp() public {
        token = new CurveToken("BOND CURV", "BOND", owner, 0);

        MultiCurveMath.CurveParams memory cp;
        cp.curveType = CurveType.POWER;
        cp.k = ud(1e12);
        cp.p = ud(1e18);

        pool = new BondingCurvePoolNative(token, cp, owner);
        token.setPool(address(pool));

        provisioner = new UniV2Provisioner();
        router = new MockUniswapV2Router(weth);
        router.wirePair(address(token));

        vm.deal(alice, 100 ether);
        vm.deal(bob, 100 ether);
    }

    function testPresaleFinalizeAndClaim() public {
        BondingCurvePresaleSMAIRT.PresaleOptions memory o;
        o.hardCapNative = 10 ether;
        o.softCapNative = 1 ether;
        o.maxContributionPerUserNative = 10 ether;
        o.minContributionPerUserNative = 0.1 ether;
        o.startTime = uint112(block.timestamp);
        o.endTime = uint112(block.timestamp + 1 days);

        o.nativeForLiquidityBps = 2000; // 20%
        o.presaleNativeForMarketingBps = 0;
        o.presaleNativeForDevBps = 0;
        o.presaleNativeForDaoBps = 0;

        o.presaleMarketingWallet = payable(address(0));
        o.presaleDevWallet = payable(address(0));
        o.presaleDaoWallet = payable(address(0));

        o.liquidityLockDurationDays = 7;
        o.liquidityBeneficiaryAddress = payable(owner);

        o.minTokensForLiquidity = 0;
        o.minTokensForSale = 0;

        ILiquidityProvisioner.LiquidityRequest memory tpl;
        tpl.mode = ILiquidityProvisioner.DexMode.V2;
        tpl.enabled = true;
        tpl.v2.router = address(router);
        tpl.v2.weth = weth;
        tpl.v2.enabled = true;

        BondingCurvePresaleSMAIRT presale = new BondingCurvePresaleSMAIRT(
            address(pool),
            address(token),
            address(provisioner),
            o,
            tpl,
            owner
        );

        // Contribute
        vm.prank(alice);
        (bool ok,) = address(presale).call{value: 1 ether}("");
        assertTrue(ok);

        // Finalize
        presale.finalize();

        // Claim
        vm.prank(alice);
        presale.claim();
        assertGt(token.balanceOf(alice), 0);

        // LP should exist and be locked in locker
        address lp = presale.lpTokenAddress();
        assertTrue(lp != address(0));
    }
}
