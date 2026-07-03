// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {AccessControlDefaultAdminRulesUpgradeable} from
    "@openzeppelin/contracts-upgradeable/access/extensions/AccessControlDefaultAdminRulesUpgradeable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {PausableUpgradeable} from "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IPolygonZkEVMBridgeV2} from "../interfaces/IPolygonZkEVMBridgeV2.sol";
import {IMintableBurnableERC20} from "./OpenBDKL2MinterBurner.sol";

/**
 * @title OpenBDKNativeConverter
 * @notice Converts BridgeWrappedToken to native L2 token
 * @dev Derived from BuildOnPolygon/usdc-lxly NativeConverter
 *      Source: github.com/BuildOnPolygon/usdc-lxly
 *      License: MIT (Polygon Labs)
 *
 *      THE PROBLEM THIS SOLVES:
 *      When users bridge a token through the default Unified Bridge (without using
 *      L1Escrow + L2MinterBurner), they receive a "BridgeWrappedToken" — created
 *      automatically by PolygonZkEVMBridgeV2's TokenWrapped pattern.
 *
 *      But for tokens like USDC, you want users to hold the *native* L2 representation
 *      (with proper minter/burner roles, blacklist functionality, etc.) — not the
 *      generic bridge wrapper.
 *
 *      THE SOLUTION:
 *      NativeConverter accepts BridgeWrappedToken from users and mints native L2 tokens
 *      1:1 in return. The accumulated BridgeWrappedToken is held in this contract.
 *
 *      THE MIGRATION:
 *      Anyone can call migrate() to send all accumulated BridgeWrappedToken back to L1
 *      via the Unified Bridge, with the L1Escrow as the recipient. This settles the
 *      accounting: L1Escrow now holds the L1 backing for the converted supply.
 *
 *      This is the canonical pattern that secured USDC.e on Polygon zkEVM mainnet.
 *      Production address: 0xd4F3531Fc95572D9e7b9e9328D9FEaa8e8496054
 *
 * @custom:security-contact security@openbdk.org
 */
contract OpenBDKNativeConverter is
    Initializable,
    AccessControlDefaultAdminRulesUpgradeable,
    UUPSUpgradeable,
    PausableUpgradeable
{
    using SafeERC20 for IERC20;

    // ============ Errors ============

    error AmountZero();
    error NoBalanceToMigrate();

    // ============ ERC-7201 Storage ============

    /// @custom:storage-location erc7201:openbdk.storage.NativeConverter
    struct NativeConverterStorage {
        IPolygonZkEVMBridgeV2 polygonZkEVMBridge;
        IMintableBurnableERC20 l2Token;          // Native L2 token (e.g., USDC.e)
        IERC20 bridgeWrappedToken;                // Default bridge wrapper (e.g., bwUSDC)
        address l1EscrowContract;                 // Recipient on L1 for migration
        uint32  l1Network;                        // Always 0 (Ethereum L1)
    }

    bytes32 private constant NativeConverterStorageLocation =
        0xc456845583450946898ce4035bf8e232aad8ff9157dede35ea0260c2ab40b800;

    function _getStorage() private pure returns (NativeConverterStorage storage $) {
        assembly {
            $.slot := NativeConverterStorageLocation
        }
    }

    // ============ Events ============

    event Converted(address indexed user, address indexed recipient, uint256 amount);
    event Migrated(uint256 amount, address indexed l1Recipient);

    // ============ Initializer ============

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(
        address _admin,
        address _polygonZkEVMBridge,
        address _l2Token,
        address _bridgeWrappedToken,
        address _l1EscrowContract,
        uint32 _l1Network
    ) public initializer {
        __AccessControlDefaultAdminRules_init(3 days, _admin);
        __UUPSUpgradeable_init();
        __Pausable_init();

        NativeConverterStorage storage $ = _getStorage();
        $.polygonZkEVMBridge = IPolygonZkEVMBridgeV2(_polygonZkEVMBridge);
        $.l2Token = IMintableBurnableERC20(_l2Token);
        $.bridgeWrappedToken = IERC20(_bridgeWrappedToken);
        $.l1EscrowContract = _l1EscrowContract;
        $.l1Network = _l1Network;
    }

    function _authorizeUpgrade(address) internal override onlyRole(DEFAULT_ADMIN_ROLE) {}

    // ============ Pause ============

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }

    // ============ Conversion ============

    /**
     * @notice Convert BridgeWrappedToken to native L2 token at 1:1 ratio
     * @param recipient Address to receive the native L2 token
     * @param amount Amount of BridgeWrappedToken to convert
     * @param permitData Optional ERC-2612 permit data
     */
    function convert(
        address recipient,
        uint256 amount,
        bytes calldata permitData
    ) external whenNotPaused {
        if (amount == 0) revert AmountZero();

        NativeConverterStorage storage $ = _getStorage();

        // Optional: handle permit for gasless approval
        if (permitData.length > 0) {
            (bool success,) = address($.bridgeWrappedToken).call(permitData);
            // Permit failure is non-fatal; user may have already approved
            success;
        }

        // Pull BridgeWrappedToken from user (held in this contract)
        $.bridgeWrappedToken.safeTransferFrom(msg.sender, address(this), amount);

        // Mint equivalent native L2 token to recipient
        $.l2Token.mint(recipient, amount);

        emit Converted(msg.sender, recipient, amount);
    }

    /**
     * @notice Permissionless: send accumulated BridgeWrappedToken back to L1
     * @dev Recipient is L1Escrow, which migrates the L1 backing.
     *      Anyone can call this — there's no privileged role.
     */
    function migrate() external whenNotPaused {
        NativeConverterStorage storage $ = _getStorage();

        uint256 balance = $.bridgeWrappedToken.balanceOf(address(this));
        if (balance == 0) revert NoBalanceToMigrate();

        // Approve the bridge to pull the wrapped tokens
        $.bridgeWrappedToken.forceApprove(address($.polygonZkEVMBridge), balance);

        // Bridge all wrapped tokens back to L1Escrow
        $.polygonZkEVMBridge.bridgeAsset(
            $.l1Network,                          // destinationNetwork = 0 (Ethereum)
            $.l1EscrowContract,                   // destinationAddress = L1Escrow
            balance,                              // amount = full balance
            address($.bridgeWrappedToken),        // token
            true,                                 // forceUpdateGlobalExitRoot
            ""                                    // no permit
        );

        emit Migrated(balance, $.l1EscrowContract);
    }

    // ============ View functions ============

    function l2Token() external view returns (IMintableBurnableERC20) {
        return _getStorage().l2Token;
    }

    function bridgeWrappedToken() external view returns (IERC20) {
        return _getStorage().bridgeWrappedToken;
    }

    function pendingMigrationAmount() external view returns (uint256) {
        return _getStorage().bridgeWrappedToken.balanceOf(address(this));
    }
}
