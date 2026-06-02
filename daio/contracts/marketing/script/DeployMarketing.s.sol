// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {IERC20}           from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {MarketingAttributionReceipt} from "../MarketingAttributionReceipt.sol";
import {MarketingTreasury, IUniswapV3SwapRouter} from "../MarketingTreasury.sol";
import {ITessera} from "../interfaces/ITessera.sol";
import {ICensura} from "../interfaces/ICensura.sol";

/// @notice Deploy the marketing receipts + treasury pair.
///
///         Two-leg deploy:
///           - leg A (default): MarketingAttributionReceipt → Base mainnet
///                              (sub-cent per receipt)
///           - leg B (optional): MarketingTreasury          → Ethereum L1
///                              (constitutional finality for buyback rule)
///
///         Operator runs:
///           forge script daio/contracts/marketing/script/DeployMarketing.s.sol:DeployMarketing \
///             --rpc-url $BASE_RPC_URL --broadcast --verify    # leg A
///           forge script daio/contracts/marketing/script/DeployMarketing.s.sol:DeployMarketingTreasury \
///             --rpc-url $MAINNET_RPC_URL --broadcast --verify # leg B
contract DeployMarketing is Script {
    function run() external {
        uint256 pk         = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address admin      = vm.envAddress("OWNER_MULTISIG");
        address tesseraAddr = vm.envAddress("MARKETING_TESSERA_ADDR");
        address censuraAddr = vm.envAddress("MARKETING_CENSURA_ADDR");
        uint8   floor      = uint8(vm.envOr("MARKETING_CENSURA_FLOOR", uint256(50)));

        vm.startBroadcast(pk);
        MarketingAttributionReceipt rcpt = new MarketingAttributionReceipt(
            admin,
            ITessera(tesseraAddr),
            ICensura(censuraAddr),
            floor
        );
        vm.stopBroadcast();

        console2.log("MarketingAttributionReceipt:", address(rcpt));
        console2.log("admin:", admin);
        console2.log("tessera:", tesseraAddr);
        console2.log("censura:", censuraAddr);
        console2.log("censuraFloor:", floor);
    }
}

contract DeployMarketingTreasury is Script {
    function run() external {
        uint256 pk         = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address admin      = vm.envAddress("OWNER_MULTISIG");
        address revenue    = vm.envAddress("MARKETING_REVENUE_ASSET");      // USDC L1
        address bankon     = vm.envAddress("MARKETING_BANKON_SATOSHI");     // BKS L1
        address swap       = vm.envAddress("MARKETING_UNI_V3_ROUTER");      // SwapRouter02
        uint24  poolFee    = uint24(vm.envOr("MARKETING_POOL_FEE", uint256(3000)));
        address foundation = vm.envAddress("MARKETING_FOUNDATION_ADDR");

        vm.startBroadcast(pk);
        MarketingTreasury vault = new MarketingTreasury(
            admin,
            IERC20(revenue),
            IERC20(bankon),
            IUniswapV3SwapRouter(swap),
            poolFee,
            foundation
        );
        vm.stopBroadcast();

        console2.log("MarketingTreasury:", address(vault));
        console2.log("admin:", admin);
        console2.log("revenueAsset:", revenue);
        console2.log("bankonSatoshi:", bankon);
        console2.log("swapRouter:", swap);
        console2.log("poolFee:", poolFee);
        console2.log("foundation:", foundation);
    }
}
