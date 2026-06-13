// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

import {OpenBDKL1Escrow} from "../src/bridge/OpenBDKL1Escrow.sol";
import {OpenBDKL2MinterBurner} from "../src/bridge/OpenBDKL2MinterBurner.sol";
import {OpenBDKNativeConverter} from "../src/bridge/OpenBDKNativeConverter.sol";
import {OpenBDKL2Token} from "../src/token/OpenBDKL2Token.sol";
import {OpenBDKDeployer} from "../src/OpenBDKDeployer.sol";

/**
 * @title  DeployOpenBDK — single-chain legs with machine-readable receipts
 * @notice Reworked from the original multi-fork script to fit the mindX
 *         `agents/deployer` FoundryDriver, which runs ONE `forge script
 *         --rpc-url <one> --broadcast` per stage and reads back
 *         `deployments/<chainId>/<RECEIPT_STAGE>.json`. No `vm.createSelectFork`.
 *
 *         Pick a leg via the DEPLOY_LEG env var:
 *           governance (default) — OWNER-custodial stack via OpenBDKDeployer
 *                                  (timelock + ValidatorRegistry + allocations).
 *                                  Single chain; testable anywhere incl. anvil.
 *           l1     — L1Escrow impl + proxy (uninitialised), on Ethereum.
 *           l2     — L2Token + L2MinterBurner + NativeConverter + ValidatorRegistry,
 *                    on the L2. Reads L1_ESCROW_ADDRESS + BRIDGE_WRAPPED_TOKEN_ADDRESS.
 *           l1init — initialise L1Escrow with the L2MinterBurner counterpart.
 *
 *         Cross-leg addresses are passed by env (operator copies the L1 receipt's
 *         L1Escrow into $L1_ESCROW_ADDRESS before the l2 leg, etc.). See
 *         docs/DEPLOYMENT.md.
 *
 *         OWNER holds the key; the software/deploy key holds nothing — the
 *         governance leg hands all admin to the OWNER's timelock (OpenBDKDeployer).
 */
contract DeployOpenBDK is Script {
    uint32 constant L1_NETWORK_ID = 0;            // Ethereum (AggLayer)
    uint32 constant OPENBDK_NETWORK_ID = 7;       // openBDK L2 (placeholder)
    address constant UNIFIED_BRIDGE = 0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe;
    address constant L1_USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;

    // ── env helpers (mirror daio/contracts/script/DeployTemplate.s.sol) ──
    function _envOr(string memory k, string memory d) internal view returns (string memory) {
        try vm.envString(k) returns (string memory v) { return v; } catch { return d; }
    }
    function _envAddrOr(string memory k, address d) internal view returns (address) {
        try vm.envAddress(k) returns (address a) { return a == address(0) ? d : a; } catch { return d; }
    }
    function _envUintOr(string memory k, uint256 d) internal view returns (uint256) {
        try vm.envUint(k) returns (uint256 v) { return v; } catch { return d; }
    }

    function _writeReceipt(string memory stage, string memory json) internal {
        string memory dir = string.concat("deployments/", vm.toString(block.chainid));
        vm.createDir(dir, true);
        vm.writeJson(json, string.concat(dir, "/", stage, ".json"));
    }

    function run() external {
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(pk);
        string memory leg = _envOr("DEPLOY_LEG", "governance");
        string memory stage = _envOr("RECEIPT_STAGE", string.concat("openbdk-", leg));
        bytes32 legHash = keccak256(bytes(leg));

        console2.log("=== DeployOpenBDK ===");
        console2.log("leg:     ", leg);
        console2.log("chainid: ", block.chainid);
        console2.log("deployer:", deployer);

        if (legHash == keccak256("governance")) {
            _governance(pk, deployer, stage);
        } else if (legHash == keccak256("l1")) {
            _l1(pk, stage);
        } else if (legHash == keccak256("l2")) {
            _l2(pk, stage);
        } else if (legHash == keccak256("l1init")) {
            _l1init(pk);
        } else {
            revert(string.concat("unknown DEPLOY_LEG: ", leg));
        }
    }

    /// OWNER-custodial governance stack — the canonical "sane deployment".
    function _governance(uint256 pk, address deployer, string memory stage) internal {
        address owner = _envAddrOr("OWNER_ADDRESS", deployer);
        uint256 delay = _envUintOr("TIMELOCK_MIN_DELAY", 2 days);
        address staking = _envAddrOr("STAKING_TOKEN_ADDRESS", address(0));
        uint256 minStake = _envUintOr("MINIMUM_VALIDATOR_STAKE", 1000e18);
        uint256 unbonding = _envUintOr("UNBONDING_PERIOD", 100);
        address allocTok = _envAddrOr("ALLOCATION_TOKEN_ADDRESS", address(0));

        vm.startBroadcast(pk);
        OpenBDKDeployer d = new OpenBDKDeployer(owner, delay, staking, minStake, unbonding, allocTok);
        vm.stopBroadcast();

        string memory o = "gov";
        vm.serializeAddress(o, "OpenBDKDeployer", address(d));
        vm.serializeAddress(o, "timelock", d.timelock());
        vm.serializeAddress(o, "validatorRegistry", d.validatorRegistry());
        string memory json = vm.serializeAddress(o, "allocations", d.allocations());
        _writeReceipt(stage, json);
        console2.log("OWNER (holds key):", owner);
        console2.log("timelock (OVERLORD):", d.timelock());
    }

    function _l1(uint256 pk, string memory stage) internal {
        vm.startBroadcast(pk);
        OpenBDKL1Escrow impl = new OpenBDKL1Escrow();
        ERC1967Proxy proxy = new ERC1967Proxy(address(impl), "");
        vm.stopBroadcast();

        string memory o = "l1";
        vm.serializeAddress(o, "L1EscrowImpl", address(impl));
        string memory json = vm.serializeAddress(o, "L1Escrow", address(proxy));
        _writeReceipt(stage, json);
    }

    function _l2(uint256 pk, string memory stage) internal {
        address admin = _envAddrOr("ADMIN_ADDRESS", vm.addr(pk));
        address l1Escrow = vm.envAddress("L1_ESCROW_ADDRESS");
        address bwToken = vm.envAddress("BRIDGE_WRAPPED_TOKEN_ADDRESS");

        vm.startBroadcast(pk);
        OpenBDKL2Token l2Token = OpenBDKL2Token(address(new ERC1967Proxy(
            address(new OpenBDKL2Token()),
            abi.encodeCall(OpenBDKL2Token.initialize, ("USD Coin (openBDK)", "USDC.b", 6, admin))
        )));
        OpenBDKL2MinterBurner mb = OpenBDKL2MinterBurner(address(new ERC1967Proxy(
            address(new OpenBDKL2MinterBurner()),
            abi.encodeCall(OpenBDKL2MinterBurner.initialize,
                (admin, UNIFIED_BRIDGE, l1Escrow, L1_NETWORK_ID, address(l2Token)))
        )));
        l2Token.grantRole(l2Token.MINTER_ROLE(), address(mb));
        l2Token.grantRole(l2Token.BURNER_ROLE(), address(mb));
        OpenBDKNativeConverter nc = OpenBDKNativeConverter(address(new ERC1967Proxy(
            address(new OpenBDKNativeConverter()),
            abi.encodeCall(OpenBDKNativeConverter.initialize,
                (admin, UNIFIED_BRIDGE, address(l2Token), bwToken, l1Escrow, L1_NETWORK_ID))
        )));
        l2Token.grantRole(l2Token.MINTER_ROLE(), address(nc));
        vm.stopBroadcast();

        string memory o = "l2";
        vm.serializeAddress(o, "L2Token", address(l2Token));
        vm.serializeAddress(o, "L2MinterBurner", address(mb));
        string memory json = vm.serializeAddress(o, "NativeConverter", address(nc));
        _writeReceipt(stage, json);
    }

    function _l1init(uint256 pk) internal {
        address admin = _envAddrOr("ADMIN_ADDRESS", vm.addr(pk));
        address escrowManager = _envAddrOr("ESCROW_MANAGER_ADDRESS", admin);
        OpenBDKL1Escrow l1Escrow = OpenBDKL1Escrow(vm.envAddress("L1_ESCROW_ADDRESS"));
        address minterBurner = vm.envAddress("L2_MINTERBURNER_ADDRESS");
        address l2Token = vm.envAddress("L2_TOKEN_ADDRESS");

        vm.startBroadcast(pk);
        l1Escrow.initialize(
            admin, escrowManager, UNIFIED_BRIDGE, minterBurner, OPENBDK_NETWORK_ID, L1_USDC, l2Token
        );
        vm.stopBroadcast();
        console2.log("L1Escrow initialised with L2MinterBurner:", minterBurner);
    }
}
