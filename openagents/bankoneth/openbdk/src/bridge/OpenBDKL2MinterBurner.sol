// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {AccessControlDefaultAdminRulesUpgradeable} from
    "@openzeppelin/contracts-upgradeable/access/extensions/AccessControlDefaultAdminRulesUpgradeable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {PausableUpgradeable} from "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";

import {PolygonERC20BridgeBaseUpgradeable} from "../base/PolygonERC20BridgeBaseUpgradeable.sol";

/**
 * @title IMintableBurnableERC20
 * @notice Interface for the L2 native token (e.g., USDC.e on the openBDK chain)
 * @dev The L2 token must grant MINTER_ROLE and BURNER_ROLE to L2MinterBurner
 */
interface IMintableBurnableERC20 {
    function mint(address to, uint256 amount) external;
    function burn(address from, uint256 amount) external;
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title OpenBDKL2MinterBurner
 * @notice L2 mint/burn contract for openBDK token bridging
 * @dev Derived from BuildOnPolygon/usdc-lxly ZkMinterBurner pattern
 *      Source: github.com/BuildOnPolygon/usdc-lxly
 *      License: MIT (Polygon Labs)
 *
 *      This contract:
 *      1. Burns user's L2 tokens when they bridge to L1
 *      2. Sends a message via Unified Bridge to L1Escrow to release L1 tokens
 *      3. Receives messages from L1Escrow and mints L2 tokens to recipients
 *
 *      Production reference (Polygon zkEVM mainnet):
 *      L1Escrow:        0x70E70e58ed7B1Cec0D8ef7464072ED8A52d755eB
 *      ZkMinterBurner:  0xBDa0B27f93B2FD3f076725b89cf02e48609bC189
 *      USDC.e:          0x37eAA0eF3549a5Bb7D431be78a3D99BD360d19e5
 *
 *      This pattern has been securing real value on Polygon zkEVM since 2023.
 *      No exploits, no fund losses. openBDK adopts it directly.
 *
 * @custom:security-contact security@openbdk.org
 */
contract OpenBDKL2MinterBurner is
    AccessControlDefaultAdminRulesUpgradeable,
    UUPSUpgradeable,
    PausableUpgradeable,
    PolygonERC20BridgeBaseUpgradeable
{
    // ============ ERC-7201 Storage ============

    /// @custom:storage-location erc7201:openbdk.storage.L2MinterBurner
    struct L2MinterBurnerStorage {
        IMintableBurnableERC20 l2Token;  // The L2 native token (e.g., USDC.e)
    }

    // keccak256(abi.encode(uint256(keccak256("openbdk.storage.L2MinterBurner")) - 1)) & ~bytes32(uint256(0xff))
    bytes32 private constant L2MinterBurnerStorageLocation =
        0xbc289f8a47b5662e46c501b5b1869837f0c5bffab07d953961594b21ecd19900;

    function _getL2MinterBurnerStorage()
        private pure returns (L2MinterBurnerStorage storage $)
    {
        assembly {
            $.slot := L2MinterBurnerStorageLocation
        }
    }

    function l2Token() public view returns (IMintableBurnableERC20) {
        return _getL2MinterBurnerStorage().l2Token;
    }

    // ============ Events ============

    event Minted(address indexed to, uint256 amount);
    event Burned(address indexed from, uint256 amount);

    // ============ Initializer ============

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /**
     * @notice Initialize the L2MinterBurner
     * @param _admin DEFAULT_ADMIN_ROLE holder (3-day delay)
     * @param _polygonZkEVMBridge Unified Bridge address on the L2 chain
     * @param _counterpartContract L1Escrow address on Ethereum
     * @param _counterpartNetwork AggLayer network ID 0 (Ethereum L1)
     * @param _l2Token Address of the L2 native token contract
     */
    function initialize(
        address _admin,
        address _polygonZkEVMBridge,
        address _counterpartContract,
        uint32 _counterpartNetwork,
        address _l2Token
    ) public virtual initializer {
        __AccessControlDefaultAdminRules_init(3 days, _admin);
        __UUPSUpgradeable_init();
        __Pausable_init();
        __PolygonERC20BridgeBase_init(
            _polygonZkEVMBridge,
            _counterpartContract,
            _counterpartNetwork
        );

        L2MinterBurnerStorage storage $ = _getL2MinterBurnerStorage();
        $.l2Token = IMintableBurnableERC20(_l2Token);
    }

    // ============ Upgrade authorization ============

    function _authorizeUpgrade(address)
        internal override onlyRole(DEFAULT_ADMIN_ROLE)
    {}

    // ============ Pause ============

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    // ============ Bridge hooks ============

    /// @dev Burn user's L2 tokens when they bridge back to L1
    function _receiveTokens(uint256 amount)
        internal virtual override whenNotPaused
    {
        L2MinterBurnerStorage storage $ = _getL2MinterBurnerStorage();
        $.l2Token.burn(msg.sender, amount);
        emit Burned(msg.sender, amount);
    }

    /// @dev Mint L2 tokens to recipient when L1Escrow signals a deposit
    function _transferTokens(address destinationAddress, uint256 amount)
        internal virtual override whenNotPaused
    {
        L2MinterBurnerStorage storage $ = _getL2MinterBurnerStorage();
        $.l2Token.mint(destinationAddress, amount);
        emit Minted(destinationAddress, amount);
    }
}
