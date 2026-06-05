// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "forge-std/console2.sol";

import "../src/SovereignDebtRegistry.sol";
import "../src/GlobalCurrencyBasket.sol";
import "../src/DebasementIndexV2.sol";

/**
 * @title DeployGlobalBasketLayer
 * @notice Deploys the SovereignDebtRegistry, GlobalCurrencyBasket, and DebasementIndexV2.
 *         Intended to run AFTER the inverse-debt layer (BitcoinAnchorOracle) is live.
 *
 * Required env vars:
 *   PRIVATE_KEY                Deployer
 *   ADMIN_ADDRESS              Admin / future Timelock target
 *   GDSI_ORACLE_ADDRESS        Existing DeltaVerseDebtOracle
 *   BTC_ORACLE_ADDRESS         Existing BitcoinAnchorOracle
 *   CL_USD_USD_FEED            Constant-1 wrapper or any USD/USD feed (use stable address)
 *   CL_EUR_USD_FEED            Chainlink EUR/USD aggregator
 *   CL_JPY_USD_FEED            Chainlink JPY/USD aggregator
 *   CL_GBP_USD_FEED            Chainlink GBP/USD aggregator
 *   CL_CNY_USD_FEED            Chainlink CNY/USD aggregator
 *
 * Reference Chainlink mainnet fx feed addresses:
 *   EUR/USD:  0xb49f677943BC038e9857d61E7d053CaA2C1734C1
 *   JPY/USD:  0xBcE206caE7f0ec07b545EddE332A47C2F75bbeb3
 *   GBP/USD:  0x5c0Ab2d9b5a7ed9f470386e82BB36A3613cDd4b5
 *   CNY/USD:  0xeF8A4aF35cd47424672E3C590aBD37FBB7A7759a
 *   AUD/USD:  0x77F9710E7d0A19669A13c055F62cd80d313dF022
 *   CHF/USD:  0x449d117117838fFA61263B61dA6301AA2a88B13A
 */
contract DeployGlobalBasketLayer is Script {

    SovereignDebtRegistry public registry;
    GlobalCurrencyBasket  public basket;
    DebasementIndexV2     public indexV2;

    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address admin       = vm.envAddress("ADMIN_ADDRESS");
        address gdsiOracle  = vm.envAddress("GDSI_ORACLE_ADDRESS");
        address btcOracle   = vm.envAddress("BTC_ORACLE_ADDRESS");

        address usdFeed = vm.envAddress("CL_USD_USD_FEED");
        address eurFeed = vm.envAddress("CL_EUR_USD_FEED");
        address jpyFeed = vm.envAddress("CL_JPY_USD_FEED");
        address gbpFeed = vm.envAddress("CL_GBP_USD_FEED");
        address cnyFeed = vm.envAddress("CL_CNY_USD_FEED");

        console2.log("=======================================");
        console2.log("GLOBAL BASKET LAYER DEPLOYMENT");
        console2.log("=======================================");
        console2.log("Chain ID:    ", block.chainid);
        console2.log("Admin:       ", admin);
        console2.log("GDSI Oracle: ", gdsiOracle);
        console2.log("BTC Oracle:  ", btcOracle);
        console2.log("=======================================");

        vm.startBroadcast(pk);

        // Step 1: SovereignDebtRegistry with seed values.
        console2.log("\n[1/3] Deploying SovereignDebtRegistry...");
        registry = new SovereignDebtRegistry(admin);

        // Seed with current (mid-2025/early-2026) sovereign debt figures.
        // All values in 18-decimal USD-equivalent.
        registry.registerCountry(bytes3("USD"), 38_300_000_000_000e18, 28_000_000_000_000e18);
        registry.registerCountry(bytes3("EUR"), 21_000_000_000_000e18, 17_500_000_000_000e18);
        registry.registerCountry(bytes3("JPY"),  9_800_000_000_000e18,  4_400_000_000_000e18);
        registry.registerCountry(bytes3("GBP"),  3_500_000_000_000e18,  3_400_000_000_000e18);
        registry.registerCountry(bytes3("CNY"), 18_700_000_000_000e18, 18_000_000_000_000e18);

        console2.log("       SovereignDebtRegistry:", address(registry));
        console2.log("       Total global debt seeded:", registry.totalGlobalDebtUsd());

        // Step 2: GlobalCurrencyBasket.
        console2.log("\n[2/3] Deploying GlobalCurrencyBasket...");
        basket = new GlobalCurrencyBasket(admin, address(registry), btcOracle);

        basket.configureCurrency(bytes3("USD"), usdFeed, 8, 2 hours);
        basket.configureCurrency(bytes3("EUR"), eurFeed, 8, 2 hours);
        basket.configureCurrency(bytes3("JPY"), jpyFeed, 8, 2 hours);
        basket.configureCurrency(bytes3("GBP"), gbpFeed, 8, 2 hours);
        basket.configureCurrency(bytes3("CNY"), cnyFeed, 8, 2 hours);

        basket.initializeBaseline();
        console2.log("       GlobalCurrencyBasket:", address(basket));
        console2.log("       Baseline locked");

        // Step 3: DebasementIndexV2.
        console2.log("\n[3/3] Deploying DebasementIndexV2...");
        indexV2 = new DebasementIndexV2(admin, gdsiOracle, address(basket), btcOracle);
        indexV2.initializeBaseline();
        console2.log("       DebasementIndexV2:", address(indexV2));

        vm.stopBroadcast();

        console2.log("\n=======================================");
        console2.log("GLOBAL BASKET LAYER DEPLOYMENT COMPLETE");
        console2.log("=======================================");
        console2.log("SovereignDebtRegistry:", address(registry));
        console2.log("GlobalCurrencyBasket: ", address(basket));
        console2.log("DebasementIndexV2:    ", address(indexV2));
        console2.log("=======================================");
        console2.log("\nPOST-DEPLOYMENT CHECKLIST:");
        console2.log("[ ] Verify each fx feed returns positive value");
        console2.log("[ ] Add quarterly reporter for SovereignDebtRegistry updates");
        console2.log("[ ] Deploy new InverseDebtToken pointing at DebasementIndexV2");
        console2.log("[ ] Or migrate existing iDEBT holders to V2 via BitcoinProfitRecognizer");
        console2.log("[ ] Transfer all admin roles to Timelock");
        console2.log("[ ] Add to EmergencyPauser.managedContracts");
        console2.log("[ ] Update subgraph schema for basket events");
    }
}
