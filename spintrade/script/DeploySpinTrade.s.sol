// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {SpinTradeFactory} from "../src/SpinTradeFactory.sol";
import {SpinTradePair} from "../src/SpinTradePair.sol";
import {BankonToken} from "../src/tokens/BankonToken.sol";
import {PythaiToken} from "../src/tokens/PythaiToken.sol";

/// @title DeploySpinTrade — Anvil deploy script
/// @notice Run with:
///   forge script script/DeploySpinTrade.s.sol:DeploySpinTrade \
///     --rpc-url http://127.0.0.1:8545 --broadcast \
///     --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
///
/// Deploys: BankonToken + PythaiToken + SpinTradeFactory.
/// Creates a BANKON/PYTHAI pair and seeds it with 100k/400k initial liquidity
/// (1 BANKON ≈ 4 PYTHAI starting price).
contract DeploySpinTrade is Script {
    function run() external {
        uint256 pk = vm.envOr("DEPLOYER_PK", uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80));
        address deployer = vm.addr(pk);

        vm.startBroadcast(pk);

        BankonToken bankon = new BankonToken(deployer);
        PythaiToken pythai = new PythaiToken(deployer);
        SpinTradeFactory factory = new SpinTradeFactory();
        address pairAddr = factory.createPair(address(bankon), address(pythai));
        SpinTradePair pair = SpinTradePair(pairAddr);

        // Seed initial liquidity: 100,000 BANKON + 400,000 PYTHAI
        // (sets initial price to 4 PYTHAI per BANKON)
        bankon.approve(pairAddr, type(uint256).max);
        pythai.approve(pairAddr, type(uint256).max);
        (uint256 amt0, uint256 amt1) = pair.token0() == address(bankon)
            ? (uint256(100_000 ether), uint256(400_000 ether))
            : (uint256(400_000 ether), uint256(100_000 ether));
        uint256 lp = pair.addLiquidity(amt0, amt1, deployer);

        vm.stopBroadcast();

        console2.log("=========================================");
        console2.log("SPINTRADE DEPLOYED");
        console2.log("=========================================");
        console2.log("BankonToken:      ", address(bankon));
        console2.log("PythaiToken:      ", address(pythai));
        console2.log("SpinTradeFactory: ", address(factory));
        console2.log("BANKON/PYTHAI Pair:", pairAddr);
        console2.log("Initial LP minted:", lp);
        console2.log("Deployer:         ", deployer);
        console2.log("=========================================");
        console2.log("Initial price: 1 BANKON = 4 PYTHAI");
        console2.log("Reserves:      100k BANKON, 400k PYTHAI");
        console2.log("=========================================");
    }
}
