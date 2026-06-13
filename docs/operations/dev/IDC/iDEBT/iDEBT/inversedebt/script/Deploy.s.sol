// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "forge-std/console2.sol";

import "../src/RWAToken.sol";
import "../src/CrossCollateralVault.sol";
import "../src/PerpetualEngine.sol";
import "../src/DeltaVerseDebtOracle.sol";
import "../src/DebtInheritanceProtocol.sol";

/**
 * @title Deploy — DELTAVERSE Stack Mainnet Deployment
 * @notice Deploys all 5 contracts of the Debt Inheritance Protocol
 *         in dependency order with proper wiring and role grants.
 *
 * Usage:
 *   # 1. Set environment variables
 *   export PRIVATE_KEY=0x...
 *   export ADMIN_ADDRESS=0x...
 *   export STABLECOIN_ADDRESS=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48  # USDC mainnet
 *   export PYTH_ADDRESS=0x4305FB66699C3B2702D4d05CF36551390A4c69C6         # Pyth mainnet
 *   export KEEPER_ADDRESS=0x...
 *   export REPORTER_ADDRESS=0x...
 *
 *   # 2. Dry run (simulation)
 *   forge script script/Deploy.s.sol:Deploy --rpc-url $RPC_URL
 *
 *   # 3. Deploy to mainnet
 *   forge script script/Deploy.s.sol:Deploy \
 *       --rpc-url $RPC_URL \
 *       --broadcast \
 *       --verify \
 *       --etherscan-api-key $ETHERSCAN_API_KEY
 *
 * Network addresses reference:
 *   Ethereum Mainnet USDC:  0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
 *   Ethereum Pyth:          0x4305FB66699C3B2702D4d05CF36551390A4c69C6
 *   Polygon USDC:           0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
 *   Polygon Pyth:           0xff1a0f4744e8582DF1aE09D5611b887B6a12925C
 *   Arbitrum USDC:          0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8
 *   Arbitrum Pyth:          0xff1a0f4744e8582DF1aE09D5611b887B6a12925C
 *   Base USDC:              0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
 *   Base Pyth:              0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a
 */
contract Deploy is Script {

    // ── Deployed addresses (populated during run) ──
    RWAToken              public rwa;
    DeltaVerseDebtOracle  public oracle;
    CrossCollateralVault  public vault;
    PerpetualEngine       public perp;
    DebtInheritanceProtocol public protocol;

    // ── Configuration ──
    address public admin;
    address public stablecoin;
    address public pyth;
    address public keeper;
    address public reporter;

    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        admin       = vm.envAddress("ADMIN_ADDRESS");
        stablecoin  = vm.envAddress("STABLECOIN_ADDRESS");
        pyth        = vm.envAddress("PYTH_ADDRESS");
        keeper      = vm.envOr("KEEPER_ADDRESS", admin);
        reporter    = vm.envOr("REPORTER_ADDRESS", admin);

        console2.log("=======================================");
        console2.log("DELTAVERSE STACK DEPLOYMENT");
        console2.log("=======================================");
        console2.log("Chain ID:      ", block.chainid);
        console2.log("Admin:         ", admin);
        console2.log("Stablecoin:    ", stablecoin);
        console2.log("Pyth:          ", pyth);
        console2.log("Keeper:        ", keeper);
        console2.log("Reporter:      ", reporter);
        console2.log("=======================================");

        vm.startBroadcast(pk);

        // ═══════════════════════════════════════════════════════════
        // STEP 1: Deploy RWAToken (example tokenized Treasury)
        // ═══════════════════════════════════════════════════════════
        console2.log("\n[1/5] Deploying RWAToken...");
        rwa = new RWAToken(
            "Tokenized US Treasury 10Y",
            "tUST10",
            "Fractional ownership of US Treasury bond ISIN US912810TX66",
            "US912810TX66",
            block.timestamp + 3650 days,  // 10yr maturity
            400,                           // 4% annual coupon
            100_000_000e18,                // 100M supply cap
            stablecoin                     // yield token = USDC
        );
        console2.log("       RWAToken deployed at:", address(rwa));

        // ═══════════════════════════════════════════════════════════
        // STEP 2: Deploy DeltaVerseDebtOracle
        // ═══════════════════════════════════════════════════════════
        console2.log("\n[2/5] Deploying DeltaVerseDebtOracle...");
        oracle = new DeltaVerseDebtOracle(
            admin,
            pyth,
            stablecoin  // LP staking token = USDC
        );
        console2.log("       Oracle deployed at:", address(oracle));

        // Grant roles to keepers and reporters
        oracle.grantRole(oracle.REPORTER_ROLE(), reporter);
        oracle.grantRole(oracle.KEEPER_ROLE(), keeper);
        console2.log("       Granted REPORTER_ROLE to:", reporter);
        console2.log("       Granted KEEPER_ROLE to:   ", keeper);

        // ═══════════════════════════════════════════════════════════
        // STEP 3: Deploy CrossCollateralVault
        // ═══════════════════════════════════════════════════════════
        console2.log("\n[3/5] Deploying CrossCollateralVault...");
        vault = new CrossCollateralVault(stablecoin, 6);
        console2.log("       Vault deployed at:", address(vault));
        console2.log("       (NOTE: Call addAsset() post-deployment to register");
        console2.log("        RWAToken and any other collateral assets with");
        console2.log("        their respective Chainlink price feeds)");

        // ═══════════════════════════════════════════════════════════
        // STEP 4: Deploy PerpetualEngine
        // ═══════════════════════════════════════════════════════════
        console2.log("\n[4/5] Deploying PerpetualEngine...");
        perp = new PerpetualEngine(
            stablecoin,
            address(oracle),
            admin
        );
        console2.log("       PerpetualEngine deployed at:", address(perp));
        console2.log("       Oracle wired to:              ", address(oracle));

        // ═══════════════════════════════════════════════════════════
        // STEP 5: Deploy DebtInheritanceProtocol (capstone)
        // ═══════════════════════════════════════════════════════════
        console2.log("\n[5/5] Deploying DebtInheritanceProtocol...");
        protocol = new DebtInheritanceProtocol(
            address(oracle),
            address(vault),
            address(perp),
            stablecoin,
            admin
        );
        console2.log("       Protocol deployed at:", address(protocol));

        vm.stopBroadcast();

        // ═══════════════════════════════════════════════════════════
        // SUMMARY
        // ═══════════════════════════════════════════════════════════
        console2.log("\n=======================================");
        console2.log("DEPLOYMENT COMPLETE");
        console2.log("=======================================");
        console2.log("RWAToken:                ", address(rwa));
        console2.log("DeltaVerseDebtOracle:    ", address(oracle));
        console2.log("CrossCollateralVault:    ", address(vault));
        console2.log("PerpetualEngine:         ", address(perp));
        console2.log("DebtInheritanceProtocol: ", address(protocol));
        console2.log("=======================================");
        console2.log("\nPOST-DEPLOYMENT CHECKLIST:");
        console2.log("[ ] 1. Register collateral assets in vault (addAsset)");
        console2.log("[ ] 2. Configure Pyth feed IDs per sub-index (setPythSource)");
        console2.log("[ ] 3. Configure Chainlink feeds per sub-index (setChainlinkSource)");
        console2.log("[ ] 4. Seed oracle sub-indices via reporter submissions");
        console2.log("[ ] 5. Call updateComposite() to initialize GDSI");
        console2.log("[ ] 6. Seed CrossCollateralVault with stablecoin reserves");
        console2.log("[ ] 7. Seed PerpetualEngine insurance fund");
        console2.log("[ ] 8. Whitelist protocol + vault in RWAToken");
        console2.log("[ ] 9. Setup keeper automation for routeFees()");
        console2.log("[ ] 10. Setup keeper automation for Pyth updatePriceFeeds()");
    }
}
