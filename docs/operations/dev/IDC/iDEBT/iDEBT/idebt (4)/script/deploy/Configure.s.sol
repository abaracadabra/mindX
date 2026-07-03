// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Script, console2 } from "forge-std/Script.sol";

import { DeltaVerseDebtOracle } from "../../src/core/DeltaVerseDebtOracle.sol";
import { IDebtOracle }          from "../../src/interfaces/IDebtOracle.sol";
import { ChainlinkAdapter }     from "../../src/oracles/ChainlinkAdapter.sol";
import { PythAdapter }          from "../../src/oracles/PythAdapter.sol";
import { SynthetixV3Adapter }   from "../../src/oracles/SynthetixV3Adapter.sol";
import { X402PaymentGateway }  from "../../src/integrations/X402PaymentGateway.sol";
import { iDEBT }                from "../../src/core/iDEBT.sol";

/// @title Configure
/// @notice Post-deployment wiring: attach per-chain oracle adapters, register
///         the Parsec facilitator signer, set x402 prices, and link the
///         x402 gate to the core iDEBT contract.
///
///         Run AFTER Deploy.s.sol. Requires that the deployer still holds the
///         relevant roles OR is executing via the DAIO timelock.
///
///         Usage:
///           ORACLE=0x... INDEX=0x... DEBT=0x... X402=0x... \
///           forge script script/deploy/Configure.s.sol \
///             --rpc-url $NETWORK --broadcast -vvvv
contract Configure is Script {
    function run() external {
        uint256 pk    = vm.envUint("PRIVATE_KEY");
        address oracleAddr = vm.envAddress("ORACLE");
        address debtAddr   = vm.envAddress("DEBT");
        address x402Addr   = vm.envAddress("X402");

        vm.startBroadcast(pk);

        // --- 1. Oracle adapters -------------------------------------------
        _wireChainlinkFeeds(oracleAddr);
        _wirePythFeeds(oracleAddr);
        _wireSynthetix(oracleAddr);

        // --- 2. x402 prices & facilitator ---------------------------------
        X402PaymentGateway gate = X402PaymentGateway(x402Addr);
        address facilitator = vm.envAddress("PARSEC_FACILITATOR");
        gate.setFacilitator(facilitator, true);

        gate.setPrice(keccak256("iDEBT.open"),  1_000_000, bytes32("USDCa"));  // 1 USDCa
        gate.setPrice(keccak256("iDEBT.claim"),   500_000, bytes32("USDCa"));  // 0.5 USDCa

        // --- 3. Link x402 into the core iDEBT ----------------------------
        iDEBT(debtAddr).setX402(x402Addr);

        vm.stopBroadcast();

        console2.log("Configure complete for chainId", block.chainid);
    }

    function _wireChainlinkFeeds(address oracleAddr) internal {
        DeltaVerseDebtOracle oracle = DeltaVerseDebtOracle(oracleAddr);

        // Per-chain feed addresses; override via env on non-mainnet.
        address dxyFeed   = vm.envOr("CHAINLINK_DXY_FEED",   address(0));
        address vixFeed   = vm.envOr("CHAINLINK_VIX_FEED",   address(0));
        address goldFeed  = vm.envOr("CHAINLINK_GOLD_FEED",  address(0));

        if (dxyFeed != address(0)) {
            ChainlinkAdapter a = new ChainlinkAdapter(dxyFeed,  bytes32("CL_DXY"),  1 hours);
            oracle.attachAdapter(IDebtOracle.Metric.DXY, bytes32("CL_DXY"), address(a));
        }
        if (vixFeed != address(0)) {
            ChainlinkAdapter a = new ChainlinkAdapter(vixFeed,  bytes32("CL_VIX"),  1 hours);
            oracle.attachAdapter(IDebtOracle.Metric.VIX, bytes32("CL_VIX"), address(a));
        }
        if (goldFeed != address(0)) {
            ChainlinkAdapter a = new ChainlinkAdapter(goldFeed, bytes32("CL_GOLD"), 1 hours);
            oracle.attachAdapter(IDebtOracle.Metric.GoldRatio, bytes32("CL_GOLD"), address(a));
        }
    }

    function _wirePythFeeds(address oracleAddr) internal {
        DeltaVerseDebtOracle oracle = DeltaVerseDebtOracle(oracleAddr);
        address pyth = vm.envOr("PYTH_CONTRACT", address(0));
        if (pyth == address(0)) return;

        bytes32 realRateId = vm.envOr("PYTH_REAL_RATE_ID", bytes32(0));
        if (realRateId != bytes32(0)) {
            PythAdapter a = new PythAdapter(pyth, realRateId, bytes32("PY_REAL"), 10 minutes);
            oracle.attachAdapter(IDebtOracle.Metric.RealRate, bytes32("PY_REAL"), address(a));
        }
        bytes32 yieldId = vm.envOr("PYTH_YIELD_ID", bytes32(0));
        if (yieldId != bytes32(0)) {
            PythAdapter a = new PythAdapter(pyth, yieldId, bytes32("PY_YIELD"), 10 minutes);
            oracle.attachAdapter(IDebtOracle.Metric.YieldCurveInversion, bytes32("PY_YIELD"), address(a));
        }
    }

    function _wireSynthetix(address oracleAddr) internal {
        DeltaVerseDebtOracle oracle = DeltaVerseDebtOracle(oracleAddr);
        address snxCore  = vm.envOr("SYNTHETIX_V3_CORE", address(0));
        uint128 marketId = uint128(vm.envOr("SYNTHETIX_MARKET_ID", uint256(0)));
        if (snxCore == address(0) || marketId == 0) return;

        SynthetixV3Adapter a = new SynthetixV3Adapter(snxCore, marketId, bytes32("SNX_MKT"));
        oracle.attachAdapter(IDebtOracle.Metric.CDS5Y, bytes32("SNX_MKT"), address(a));
    }
}
