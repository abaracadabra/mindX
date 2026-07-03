// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {AccessControlDefaultAdminRulesUpgradeable} from
    "@openzeppelin/contracts-upgradeable/access/extensions/AccessControlDefaultAdminRulesUpgradeable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {PausableUpgradeable} from "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {PolygonERC20BridgeBaseUpgradeable} from "../base/PolygonERC20BridgeBaseUpgradeable.sol";

/**
 * @title OpenBDKL1Escrow
 * @notice L1 escrow contract for openBDK token bridging
 * @dev Derived from BuildOnPolygon/zkevm-stb canonical L1Escrow implementation
 *      Original: github.com/BuildOnPolygon/zkevm-stb/blob/main/src/L1Escrow.sol
 *      Original license: MIT (Polygon Labs / sepyke.eth)
 *
 *      This contract:
 *      1. Receives native tokens (e.g., USDC) on L1 from users
 *      2. Triggers L2MinterBurner via Unified Bridge to mint L2 representation
 *      3. Holds the L1 backing for the entire L2 token supply
 *      4. Is triggered by the bridge to release L1 tokens on withdrawal
 *
 *      Security properties inherited from the BuildOnPolygon production deployment:
 *      - 3-day admin transfer delay (AccessControlDefaultAdminRules)
 *      - UUPS upgradeability with admin-only authorization
 *      - Pausable for emergency response
 *      - ERC-7201 storage isolation (no upgrade collision risks)
 *      - SafeERC20 for non-standard token compatibility
 *
 *      What openBDK adds beyond the canonical implementation:
 *      - Compatible with the Relayer-Validator consensus model
 *      - Inherits AggLayer pessimistic proof guarantees automatically
 *      - Validator slashing cannot affect L1 escrow funds
 *
 * @custom:security-contact security@openbdk.org
 */
contract OpenBDKL1Escrow is
    AccessControlDefaultAdminRulesUpgradeable,
    UUPSUpgradeable,
    PausableUpgradeable,
    PolygonERC20BridgeBaseUpgradeable
{
    using SafeERC20 for IERC20;

    // ============ Roles ============

    /// @notice Escrow manager can perform yield-generating operations on locked backing
    bytes32 public constant ESCROW_MANAGER_ROLE = keccak256("ESCROW_MANAGER_ROLE");

    // ============ ERC-7201 Storage ============

    /// @custom:storage-location erc7201:openbdk.storage.L1Escrow
    struct L1EscrowStorage {
        IERC20 originTokenAddress;     // L1 token (e.g., USDC on Ethereum)
        IERC20 wrappedTokenAddress;    // L2 token address (informational)
    }

    // keccak256(abi.encode(uint256(keccak256("openbdk.storage.L1Escrow")) - 1)) & ~bytes32(uint256(0xff))
    bytes32 private constant L1EscrowStorageLocation =
        0x140f3cfefcf2a2d0dfb2f8ca769e5b9056bc06d7300b21ef485df9bfa13c6800;

    function _getL1EscrowStorage() private pure returns (L1EscrowStorage storage $) {
        assembly {
            $.slot := L1EscrowStorageLocation
        }
    }

    function originTokenAddress() public view returns (IERC20) {
        return _getL1EscrowStorage().originTokenAddress;
    }

    function wrappedTokenAddress() public view returns (IERC20) {
        return _getL1EscrowStorage().wrappedTokenAddress;
    }

    // ============ Events ============

    event Withdraw(address indexed recipient, uint256 amount);
    event YieldDeposited(address indexed strategy, uint256 amount);

    // ============ Initializer ============

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /**
     * @notice Initialize L1Escrow
     * @param _admin DEFAULT_ADMIN_ROLE holder (3-day delay for changes)
     * @param _manager ESCROW_MANAGER_ROLE holder (yield management)
     * @param _polygonZkEVMBridge Unified Bridge address (0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe on mainnet)
     * @param _counterpartContract L2MinterBurner address on the openBDK chain
     * @param _counterpartNetwork AggLayer network ID of the openBDK chain
     * @param _originTokenAddress L1 ERC-20 token (e.g., USDC at 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48)
     * @param _wrappedTokenAddress L2 representation address (informational)
     */
    function initialize(
        address _admin,
        address _manager,
        address _polygonZkEVMBridge,
        address _counterpartContract,
        uint32 _counterpartNetwork,
        address _originTokenAddress,
        address _wrappedTokenAddress
    ) public virtual initializer {
        __AccessControlDefaultAdminRules_init(3 days, _admin);
        __UUPSUpgradeable_init();
        __Pausable_init();
        __PolygonERC20BridgeBase_init(
            _polygonZkEVMBridge,
            _counterpartContract,
            _counterpartNetwork
        );

        _grantRole(ESCROW_MANAGER_ROLE, _manager);

        L1EscrowStorage storage $ = _getL1EscrowStorage();
        $.originTokenAddress = IERC20(_originTokenAddress);
        $.wrappedTokenAddress = IERC20(_wrappedTokenAddress);
    }

    // ============ Upgrade authorization ============

    function _authorizeUpgrade(address _newVersion)
        internal override onlyRole(DEFAULT_ADMIN_ROLE)
    {}

    // ============ Pause ============

    function pause() external virtual onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external virtual onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    // ============ Bridge hooks ============

    /// @dev Pull tokens from user when bridgeToken is called
    function _receiveTokens(uint256 amount)
        internal virtual override whenNotPaused
    {
        L1EscrowStorage storage $ = _getL1EscrowStorage();
        $.originTokenAddress.safeTransferFrom(msg.sender, address(this), amount);
    }

    /// @dev Release tokens to user when claimMessage triggers onMessageReceived
    function _transferTokens(address destinationAddress, uint256 amount)
        internal virtual override whenNotPaused
    {
        L1EscrowStorage storage $ = _getL1EscrowStorage();
        $.originTokenAddress.safeTransfer(destinationAddress, amount);
    }

    // ============ Manager functions ============

    /**
     * @notice Withdraw escrowed tokens for yield-generating strategies
     * @dev IMPORTANT: This is the "Staking the Bridge" feature. The escrow manager
     *      can deploy backing into approved yield strategies, but the openBDK
     *      governance MUST ensure that any withdrawn amount remains recoverable
     *      to honor user withdrawals.
     */
    function withdraw(address _recipient, uint256 _amount)
        external virtual onlyRole(ESCROW_MANAGER_ROLE) whenNotPaused
    {
        L1EscrowStorage storage $ = _getL1EscrowStorage();
        $.originTokenAddress.safeTransfer(_recipient, _amount);
        emit Withdraw(_recipient, _amount);
    }

    /// @notice Get the current L1 backing balance held by this escrow
    function escrowBalance() external view returns (uint256) {
        return _getL1EscrowStorage().originTokenAddress.balanceOf(address(this));
    }
}
