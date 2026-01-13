// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

import { BondingCurveFactory } from "../src/factory/BondingCurveFactory.sol";
import { CurveToken } from "../src/token/CurveToken.sol";
import { BondingCurvePoolNative } from "../src/pool/BondingCurvePoolNative.sol";
import { UniV2Provisioner } from "../src/liquidity/provisioners/UniV2Provisioner.sol";
import { ILiquidityProvisioner } from "../src/liquidity/ILiquidityProvisioner.sol";
import { BondingCurvePresaleSMAIRT } from "../src/extensions/BondingCurvePresaleSMAIRT.sol";

contract BondingCurveFactoryTest is Test {
    BondingCurveFactory factory;
    UniV2Provisioner provisioner;

    function setUp() public {
        factory = new BondingCurveFactory(address(this));
        provisioner = new UniV2Provisioner();
    }

    function testLaunchCurveWithDefaults() public {
        BondingCurveFactory.LaunchPowerCurveNativeArgs memory args;
        args.name = "";  // Should default to "REFLECT REWARD"
        args.symbol = ""; // Should default to "REWARD"
        args.initialMintToOwner = 0;
        args.kUD60x18 = 1e12;
        args.pUD60x18 = 1e18;
        args.protocolFeeBps = 0;
        args.enablePresale = false;

        (address token, address pool,) = factory.launchPowerCurveNative(args);

        CurveToken tokenContract = CurveToken(token);
        assertEq(tokenContract.name(), "REFLECT REWARD");
        assertEq(tokenContract.symbol(), "REWARD");
    }

    function testLaunchCurveWithCustomToken() public {
        BondingCurveFactory.LaunchPowerCurveNativeArgs memory args;
        args.name = "My Custom Token";
        args.symbol = "MCT";
        args.initialMintToOwner = 1000e18;
        args.kUD60x18 = 1e12;
        args.pUD60x18 = 1e18;
        args.protocolFeeBps = 200;
        args.enablePresale = false;

        (address token, address pool,) = factory.launchPowerCurveNative(args);

        CurveToken tokenContract = CurveToken(token);
        assertEq(tokenContract.name(), "My Custom Token");
        assertEq(tokenContract.symbol(), "MCT");
        assertEq(tokenContract.balanceOf(address(this)), 1000e18);
    }
}
