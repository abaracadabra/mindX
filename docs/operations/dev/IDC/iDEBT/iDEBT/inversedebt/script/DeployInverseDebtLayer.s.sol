// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "forge-std/console2.sol";

import "../src/BitcoinAnchorOracle.sol";
import "../src/DebasementIndex.sol";
import "../src/InverseDebtToken.sol";
import "../src/BitcoinProfitRecognizer.sol";

/**
 * @title DeployInverseDebtLayer
 * @notice Deploys the four new inverse-debt contracts that layer on top of the existing
 *         DELTAVERSE base stack. Intended to run AFTER the main Deploy.s.sol has already
 *         produced a live deployment, so the existing GDSI oracle and DebtInheritanceProtocol
 *         addresses can be passed in via env vars.
 *
 * Required environment variables:
 *   PRIVATE_KEY                     Deployer key
 *   ADMIN_ADDRESS                   Admin for the new contracts (should be Timelock post-handover)
 *   STABLECOIN_ADDRESS              USDC address on target chain
 *   GDSI_ORACLE_ADDRESS             Existing DeltaVerseDebtOracle address
 *   DIP_ADDRESS                     Existing DebtInheritanceProtocol address
 *   CHAINLINK_BTC_FEED              Chainlink BTC/USD aggregator (chain-specific)
 *   PYTH_ADDRESS                    Pyth contract on target chain
 *   PYTH_BTC_FEED_ID                Pyth price feed ID for BTC/USD (hex bytes32)
 *
 * Chain references for CHAINLINK_BTC_FEED:
 *   Ethereum mainnet: 0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c
 *   Polygon:          0xc907E116054Ad103354f2D350FD2514433D57F6f
 *   Arbitrum:         0x6ce185860a4963106506C203335A2910413708e9
 *   Base:             0x64c911996D3c6aC71f9b455B1E8E7266BcbD848F
 *
 * PYTH_BTC_FEED_ID (global, same on all chains):
 *   0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43
 */
contract DeployInverseDebtLayer is Script {

    BitcoinAnchorOracle     public btcOracle;
    DebasementIndex          public debasement;
    InverseDebtToken         public idebt;
    BitcoinProfitRecognizer  public recognizer;

    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address admin       = vm.envAddress("ADMIN_ADDRESS");
        address stable      = vm.envAddress("STABLECOIN_ADDRESS");
        address gdsiOracle  = vm.envAddress("GDSI_ORACLE_ADDRESS");
        address dip         = vm.envAddress("DIP_ADDRESS");
        address clBtcFeed   = vm.envAddress("CHAINLINK_BTC_FEED");
        address pythAddr    = vm.envAddress("PYTH_ADDRESS");
        bytes32 pythBtcId   = vm.envBytes32("PYTH_BTC_FEED_ID");

        console2.log("=======================================");
        console2.log("INVERSE DEBT LAYER DEPLOYMENT");
        console2.log("=======================================");
        console2.log("Chain ID:     ", block.chainid);
        console2.log("Admin:        ", admin);
        console2.log("Stablecoin:   ", stable);
        console2.log("GDSI Oracle:  ", gdsiOracle);
        console2.log("DIP:          ", dip);
        console2.log("CL BTC Feed:  ", clBtcFeed);
        console2.log("Pyth:         ", pythAddr);
        console2.log("=======================================");

        vm.startBroadcast(pk);

        // Step 1: BitcoinAnchorOracle.
        console2.log("\n[1/4] Deploying BitcoinAnchorOracle...");
        btcOracle = new BitcoinAnchorOracle(admin);
        console2.log("       BitcoinAnchorOracle:", address(btcOracle));

        // Configure Chainlink BTC source (50% weight).
        btcOracle.configureSource({
            index: 0,
            feed: clBtcFeed,
            pythFeedId: bytes32(0),
            feedDecimals: 8,
            maxStaleness: 2 hours,
            weightBps: 5000,
            maxConfBps: 0,
            enabled: true
        });

        // Configure Pyth BTC source (50% weight, max 2% confidence band).
        btcOracle.configureSource({
            index: 1,
            feed: pythAddr,
            pythFeedId: pythBtcId,
            feedDecimals: 0,
            maxStaleness: 2 hours,
            weightBps: 5000,
            maxConfBps: 200,
            enabled: true
        });

        // Seed first composite.
        btcOracle.updateComposite();
        console2.log("       Composite seeded at:", btcOracle.compositeValue());

        // Step 2: DebasementIndex.
        console2.log("\n[2/4] Deploying DebasementIndex...");
        debasement = new DebasementIndex(admin, gdsiOracle, address(btcOracle));
        debasement.initializeBaseline();
        console2.log("       DebasementIndex:", address(debasement));
        console2.log("       Baseline index: 1.0 (locked)");

        // Step 3: InverseDebtToken.
        console2.log("\n[3/4] Deploying InverseDebtToken...");
        idebt = new InverseDebtToken(admin, stable, address(debasement));
        console2.log("       InverseDebtToken:", address(idebt));

        // Step 4: BitcoinProfitRecognizer.
        console2.log("\n[4/4] Deploying BitcoinProfitRecognizer...");
        recognizer = new BitcoinProfitRecognizer(
            admin, dip, address(idebt), address(debasement), stable
        );
        console2.log("       BitcoinProfitRecognizer:", address(recognizer));

        vm.stopBroadcast();

        console2.log("\n=======================================");
        console2.log("INVERSE DEBT LAYER DEPLOYMENT COMPLETE");
        console2.log("=======================================");
        console2.log("BitcoinAnchorOracle:      ", address(btcOracle));
        console2.log("DebasementIndex:          ", address(debasement));
        console2.log("InverseDebtToken:         ", address(idebt));
        console2.log("BitcoinProfitRecognizer:  ", address(recognizer));
        console2.log("=======================================");
        console2.log("\nPOST-DEPLOYMENT CHECKLIST:");
        console2.log("[ ] 1. Verify Chainlink BTC feed returns positive price");
        console2.log("[ ] 2. Verify Pyth BTC feed within confidence threshold");
        console2.log("[ ] 3. Register BTC oracle updater in keeper rotation");
        console2.log("[ ] 4. Seed InverseDebtToken reserve via topUpReserve()");
        console2.log("[ ] 5. Transfer DEFAULT_ADMIN_ROLE on all four contracts to Timelock");
        console2.log("[ ] 6. Add four contracts to EmergencyPauser.managedContracts");
        console2.log("[ ] 7. Update allchain.json with new addresses");
        console2.log("[ ] 8. Extend subgraph to index iDEBT events");
    }
}
