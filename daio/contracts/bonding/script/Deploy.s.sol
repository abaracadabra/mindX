// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";

import { BondingCurveFactory } from "../src/factory/BondingCurveFactory.sol";
import { UniV2Provisioner } from "../src/liquidity/provisioners/UniV2Provisioner.sol";
import { ILiquidityProvisioner } from "../src/liquidity/ILiquidityProvisioner.sol";
import { BondingCurvePresaleSMAIRT } from "../src/extensions/BondingCurvePresaleSMAIRT.sol";

contract Deploy is Script {
    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address owner = vm.addr(pk);

        vm.startBroadcast(pk);

        // Deploy factory
        BondingCurveFactory factory = new BondingCurveFactory(owner);

        // Deploy provisioner
        UniV2Provisioner provisioner = new UniV2Provisioner();

        // Fill these with real addresses for your chain
        address routerV2 = vm.envAddress("UNIV2_ROUTER");
        address weth = vm.envAddress("WETH");

        // Template for presale liquidity
        ILiquidityProvisioner.LiquidityRequest memory tpl;
        tpl.mode = ILiquidityProvisioner.DexMode.V2;
        tpl.enabled = true;
        tpl.v2.router = routerV2;
        tpl.v2.weth = weth;
        tpl.v2.enabled = true;

        // Presale options (example)
        BondingCurvePresaleSMAIRT.PresaleOptions memory p;
        p.hardCapNative = 100 ether;
        p.softCapNative = 20 ether;
        p.maxContributionPerUserNative = 10 ether;
        p.minContributionPerUserNative = 0.1 ether;
        p.startTime = uint112(block.timestamp + 3600);
        p.endTime = uint112(block.timestamp + 3600 + 3 days);

        p.nativeForLiquidityBps = 2000;
        p.presaleNativeForMarketingBps = 0;
        p.presaleNativeForDevBps = 0;
        p.presaleNativeForDaoBps = 0;

        p.presaleMarketingWallet = payable(owner);
        p.presaleDevWallet = payable(owner);
        p.presaleDaoWallet = payable(owner);

        p.liquidityLockDurationDays = 30;
        p.liquidityBeneficiaryAddress = payable(owner);

        p.minTokensForLiquidity = 0;
        p.minTokensForSale = 0;

        // Launch example curve
        BondingCurveFactory.LaunchPowerCurveNativeArgs memory a;
        a.name = "BOND CURV";
        a.symbol = "BOND";
        a.initialMintToOwner = 0;

        // Curve params (UD60x18). Example: k=1e12, p=1e18 (linear)
        a.kUD60x18 = 1e12;
        a.pUD60x18 = 1e18;

        a.protocolFeeBps = 0;
        a.feeRecipient = owner;

        a.enablePresale = true;
        a.presaleOptions = p;
        a.provisioner = address(provisioner);
        a.liquidityTemplate = tpl;

        factory.launchPowerCurveNative(a);

        vm.stopBroadcast();
    }
}
