// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ERC20Upgradeable} from "@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import {ERC20PermitUpgradeable} from
    "@openzeppelin/contracts-upgradeable/token/ERC20/extensions/ERC20PermitUpgradeable.sol";
import {AccessControlUpgradeable} from
    "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {PausableUpgradeable} from "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";

/**
 * @title OpenBDKL2Token
 * @notice Native L2 token representation for openBDK chains
 * @dev Modeled after USDC.e on Polygon zkEVM (FiatTokenV2_2)
 *      Includes mint/burn, blacklist, and permit functionality
 *
 *      Roles:
 *      - DEFAULT_ADMIN_ROLE: contract administration (3-day delay recommended)
 *      - MINTER_ROLE: granted to L2MinterBurner and NativeConverter
 *      - BURNER_ROLE: granted to L2MinterBurner only
 *      - BLACKLISTER_ROLE: compliance address freezing
 *      - PAUSER_ROLE: emergency pause
 *
 * @custom:security-contact security@openbdk.org
 */
contract OpenBDKL2Token is
    ERC20Upgradeable,
    ERC20PermitUpgradeable,
    AccessControlUpgradeable,
    UUPSUpgradeable,
    PausableUpgradeable
{
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant BLACKLISTER_ROLE = keccak256("BLACKLISTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    /// @custom:storage-location erc7201:openbdk.storage.L2Token
    struct L2TokenStorage {
        uint8 _decimals;
        mapping(address => bool) blacklisted;
    }

    bytes32 private constant L2TokenStorageLocation =
        0xebe5a9a820d52eb0ad514e70386908fc6c2198d124e221c027251c56b9f1bf00;

    function _getStorage() private pure returns (L2TokenStorage storage $) {
        assembly { $.slot := L2TokenStorageLocation }
    }

    error AccountBlacklisted(address account);

    event AddressBlacklisted(address indexed account);
    event AddressUnblacklisted(address indexed account);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() { _disableInitializers(); }

    function initialize(
        string memory name_,
        string memory symbol_,
        uint8 decimals_,
        address admin_
    ) public initializer {
        __ERC20_init(name_, symbol_);
        __ERC20Permit_init(name_);
        __AccessControl_init();
        __UUPSUpgradeable_init();
        __Pausable_init();

        _grantRole(DEFAULT_ADMIN_ROLE, admin_);
        _grantRole(PAUSER_ROLE, admin_);
        _grantRole(BLACKLISTER_ROLE, admin_);

        _getStorage()._decimals = decimals_;
    }

    function decimals() public view override returns (uint8) {
        return _getStorage()._decimals;
    }

    function _authorizeUpgrade(address) internal override onlyRole(DEFAULT_ADMIN_ROLE) {}

    // ============ Mint / Burn ============

    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) whenNotPaused {
        if (_getStorage().blacklisted[to]) revert AccountBlacklisted(to);
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external onlyRole(BURNER_ROLE) whenNotPaused {
        _burn(from, amount);
    }

    // ============ Blacklist ============

    function blacklist(address account) external onlyRole(BLACKLISTER_ROLE) {
        _getStorage().blacklisted[account] = true;
        emit AddressBlacklisted(account);
    }

    function unBlacklist(address account) external onlyRole(BLACKLISTER_ROLE) {
        _getStorage().blacklisted[account] = false;
        emit AddressUnblacklisted(account);
    }

    function isBlacklisted(address account) external view returns (bool) {
        return _getStorage().blacklisted[account];
    }

    // ============ Pause ============

    function pause() external onlyRole(PAUSER_ROLE) { _pause(); }
    function unpause() external onlyRole(PAUSER_ROLE) { _unpause(); }

    // ============ Transfer hooks (block blacklisted addresses) ============

    function _update(address from, address to, uint256 value)
        internal override whenNotPaused
    {
        L2TokenStorage storage $ = _getStorage();
        if ($.blacklisted[from]) revert AccountBlacklisted(from);
        if ($.blacklisted[to]) revert AccountBlacklisted(to);
        super._update(from, to, value);
    }
}
