// SPDX-License-Identifier: MIT
pragma solidity >=0.4.16 >=0.8.4 ^0.8.20 ^0.8.24;

// ens/v1/interfaces/IBankon.sol

/// @notice Subset of the ENS NameWrapper interface this registrar uses.
///         Reference: https://github.com/ensdomains/ens-contracts (NameWrapper.sol).
interface INameWrapper {
    function ownerOf(uint256 id) external view returns (address);
    function getData(uint256 id)
        external view
        returns (address owner, uint32 fuses, uint64 expiry);

    function setSubnodeOwner(
        bytes32 parentNode,
        string calldata label,
        address owner,
        uint32 fuses,
        uint64 expiry
    ) external returns (bytes32);

    function setSubnodeRecord(
        bytes32 parentNode,
        string calldata label,
        address owner,
        address resolver,
        uint64 ttl,
        uint32 fuses,
        uint64 expiry
    ) external returns (bytes32);

    function setChildFuses(
        bytes32 parentNode,
        bytes32 labelhash,
        uint32 fuses,
        uint64 expiry
    ) external;

    function setFuses(bytes32 node, uint16 ownerControlledFuses) external returns (uint32);
    function setResolver(bytes32 node, address resolver) external;
    function extendExpiry(bytes32 parentNode, bytes32 labelhash, uint64 expiry)
        external returns (uint64);

    function isWrapped(bytes32 node) external view returns (bool);
    function setApprovalForAll(address operator, bool approved) external;
    function approve(address to, uint256 tokenId) external;
}

/// @notice Subset of the ENS Public Resolver interface used by the registrar.
interface IPublicResolver {
    function setAddr(bytes32 node, address a) external;
    function setAddr(bytes32 node, uint256 coinType, bytes calldata a) external;
    function setText(bytes32 node, string calldata key, string calldata value) external;
    function setContenthash(bytes32 node, bytes calldata hash) external;
    function multicall(bytes[] calldata data) external returns (bytes[] memory);
}

/// @notice BankonPriceOracle interface — length-tier USD pricing in USDC base units (6 decimals).
interface IBankonPriceOracle {
    function priceUSD(string calldata label, uint256 durationYears)
        external view returns (uint256 usd6);
    function priceInToken(string calldata label, uint256 durationYears, address token)
        external view returns (uint256 amount);
}

/// @notice BankonReputationGate interface — agnostic eligibility surface.
///         Any reputation system (BONAFIDE, ERC-8004 attestation, custom) can
///         implement this to gate paid + free registration.
interface IBankonReputationGate {
    function isEligibleForFree(address agent) external view returns (bool);
    function isEligibleForRegistration(address agent) external view returns (bool);
    function bonafideScore(address agent) external view returns (uint256);
}

/// @notice ERC-8004-style identity registry. Hooked optionally by the registrar
///         to bundle agent identity mints with subname registrations.
interface IIdentityRegistry8004 {
    function register(address agentWallet, string calldata agentURI)
        external returns (uint256 agentId);
    function setMetadata(uint256 agentId, bytes32 key, bytes calldata value) external;
}

/// @notice BankonPaymentRouter interface — split + sweep of USDC/PYTHAI/ETH revenue.
interface IBankonPaymentRouter {
    function splitConfigured() external view returns (bool);
    function recordReceipt(bytes32 receiptHash, uint256 usd6, address asset) external;
    function distribute(address asset, uint256 amount) external;
}

// lib/openzeppelin-contracts/contracts/access/IAccessControl.sol

// OpenZeppelin Contracts (last updated v5.4.0) (access/IAccessControl.sol)

/**
 * @dev External interface of AccessControl declared to support ERC-165 detection.
 */
interface IAccessControl {
    /**
     * @dev The `account` is missing a role.
     */
    error AccessControlUnauthorizedAccount(address account, bytes32 neededRole);

    /**
     * @dev The caller of a function is not the expected one.
     *
     * NOTE: Don't confuse with {AccessControlUnauthorizedAccount}.
     */
    error AccessControlBadConfirmation();

    /**
     * @dev Emitted when `newAdminRole` is set as ``role``'s admin role, replacing `previousAdminRole`
     *
     * `DEFAULT_ADMIN_ROLE` is the starting admin for all roles, despite
     * {RoleAdminChanged} not being emitted to signal this.
     */
    event RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole);

    /**
     * @dev Emitted when `account` is granted `role`.
     *
     * `sender` is the account that originated the contract call. This account bears the admin role (for the granted role).
     * Expected in cases where the role was granted using the internal {AccessControl-_grantRole}.
     */
    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);

    /**
     * @dev Emitted when `account` is revoked `role`.
     *
     * `sender` is the account that originated the contract call:
     *   - if using `revokeRole`, it is the admin role bearer
     *   - if using `renounceRole`, it is the role bearer (i.e. `account`)
     */
    event RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender);

    /**
     * @dev Returns `true` if `account` has been granted `role`.
     */
    function hasRole(bytes32 role, address account) external view returns (bool);

    /**
     * @dev Returns the admin role that controls `role`. See {grantRole} and
     * {revokeRole}.
     *
     * To change a role's admin, use {AccessControl-_setRoleAdmin}.
     */
    function getRoleAdmin(bytes32 role) external view returns (bytes32);

    /**
     * @dev Grants `role` to `account`.
     *
     * If `account` had not been already granted `role`, emits a {RoleGranted}
     * event.
     *
     * Requirements:
     *
     * - the caller must have ``role``'s admin role.
     */
    function grantRole(bytes32 role, address account) external;

    /**
     * @dev Revokes `role` from `account`.
     *
     * If `account` had been granted `role`, emits a {RoleRevoked} event.
     *
     * Requirements:
     *
     * - the caller must have ``role``'s admin role.
     */
    function revokeRole(bytes32 role, address account) external;

    /**
     * @dev Revokes `role` from the calling account.
     *
     * Roles are often managed via {grantRole} and {revokeRole}: this function's
     * purpose is to provide a mechanism for accounts to lose their privileges
     * if they are compromised (such as when a trusted device is misplaced).
     *
     * If the calling account had been granted `role`, emits a {RoleRevoked}
     * event.
     *
     * Requirements:
     *
     * - the caller must be `callerConfirmation`.
     */
    function renounceRole(bytes32 role, address callerConfirmation) external;
}

// lib/openzeppelin-contracts/contracts/utils/Context.sol

// OpenZeppelin Contracts (last updated v5.0.1) (utils/Context.sol)

/**
 * @dev Provides information about the current execution context, including the
 * sender of the transaction and its data. While these are generally available
 * via msg.sender and msg.data, they should not be accessed in such a direct
 * manner, since when dealing with meta-transactions the account sending and
 * paying for execution may not be the actual sender (as far as an application
 * is concerned).
 *
 * This contract is only required for intermediate, library-like contracts.
 */
abstract contract Context {
    function _msgSender() internal view virtual returns (address) {
        return msg.sender;
    }

    function _msgData() internal view virtual returns (bytes calldata) {
        return msg.data;
    }

    function _contextSuffixLength() internal view virtual returns (uint256) {
        return 0;
    }
}

// lib/openzeppelin-contracts/contracts/utils/introspection/IERC165.sol

// OpenZeppelin Contracts (last updated v5.4.0) (utils/introspection/IERC165.sol)

/**
 * @dev Interface of the ERC-165 standard, as defined in the
 * https://eips.ethereum.org/EIPS/eip-165[ERC].
 *
 * Implementers can declare support of contract interfaces, which can then be
 * queried by others ({ERC165Checker}).
 *
 * For an implementation, see {ERC165}.
 */
interface IERC165 {
    /**
     * @dev Returns true if this contract implements the interface defined by
     * `interfaceId`. See the corresponding
     * https://eips.ethereum.org/EIPS/eip-165#how-interfaces-are-identified[ERC section]
     * to learn more about how these ids are created.
     *
     * This function call must use less than 30 000 gas.
     */
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}

// lib/openzeppelin-contracts/contracts/utils/introspection/ERC165.sol

// OpenZeppelin Contracts (last updated v5.4.0) (utils/introspection/ERC165.sol)

/**
 * @dev Implementation of the {IERC165} interface.
 *
 * Contracts that want to implement ERC-165 should inherit from this contract and override {supportsInterface} to check
 * for the additional interface id that will be supported. For example:
 *
 * ```solidity
 * function supportsInterface(bytes4 interfaceId) public view virtual override returns (bool) {
 *     return interfaceId == type(MyInterface).interfaceId || super.supportsInterface(interfaceId);
 * }
 * ```
 */
abstract contract ERC165 is IERC165 {
    /// @inheritdoc IERC165
    function supportsInterface(bytes4 interfaceId) public view virtual returns (bool) {
        return interfaceId == type(IERC165).interfaceId;
    }
}

// lib/openzeppelin-contracts/contracts/access/AccessControl.sol

// OpenZeppelin Contracts (last updated v5.6.0) (access/AccessControl.sol)

/**
 * @dev Contract module that allows children to implement role-based access
 * control mechanisms. This is a lightweight version that doesn't allow enumerating role
 * members except through off-chain means by accessing the contract event logs. Some
 * applications may benefit from on-chain enumerability, for those cases see
 * {AccessControlEnumerable}.
 *
 * Roles are referred to by their `bytes32` identifier. These should be exposed
 * in the external API and be unique. The best way to achieve this is by
 * using `public constant` hash digests:
 *
 * ```solidity
 * bytes32 public constant MY_ROLE = keccak256("MY_ROLE");
 * ```
 *
 * Roles can be used to represent a set of permissions. To restrict access to a
 * function call, use {hasRole}:
 *
 * ```solidity
 * function foo() public {
 *     require(hasRole(MY_ROLE, msg.sender));
 *     ...
 * }
 * ```
 *
 * Roles can be granted and revoked dynamically via the {grantRole} and
 * {revokeRole} functions. Each role has an associated admin role, and only
 * accounts that have a role's admin role can call {grantRole} and {revokeRole}.
 *
 * By default, the admin role for all roles is `DEFAULT_ADMIN_ROLE`, which means
 * that only accounts with this role will be able to grant or revoke other
 * roles. More complex role relationships can be created by using
 * {_setRoleAdmin}.
 *
 * WARNING: The `DEFAULT_ADMIN_ROLE` is also its own admin: it has permission to
 * grant and revoke this role. Extra precautions should be taken to secure
 * accounts that have been granted it. We recommend using {AccessControlDefaultAdminRules}
 * to enforce additional security measures for this role.
 */
abstract contract AccessControl is Context, IAccessControl, ERC165 {
    struct RoleData {
        mapping(address account => bool) hasRole;
        bytes32 adminRole;
    }

    mapping(bytes32 role => RoleData) private _roles;

    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;

    /**
     * @dev Modifier that checks that an account has a specific role. Reverts
     * with an {AccessControlUnauthorizedAccount} error including the required role.
     */
    modifier onlyRole(bytes32 role) {
        _checkRole(role);
        _;
    }

    /// @inheritdoc ERC165
    function supportsInterface(bytes4 interfaceId) public view virtual override returns (bool) {
        return interfaceId == type(IAccessControl).interfaceId || super.supportsInterface(interfaceId);
    }

    /**
     * @dev Returns `true` if `account` has been granted `role`.
     */
    function hasRole(bytes32 role, address account) public view virtual returns (bool) {
        return _roles[role].hasRole[account];
    }

    /**
     * @dev Reverts with an {AccessControlUnauthorizedAccount} error if `_msgSender()`
     * is missing `role`. Overriding this function changes the behavior of the {onlyRole} modifier.
     */
    function _checkRole(bytes32 role) internal view virtual {
        _checkRole(role, _msgSender());
    }

    /**
     * @dev Reverts with an {AccessControlUnauthorizedAccount} error if `account`
     * is missing `role`.
     */
    function _checkRole(bytes32 role, address account) internal view virtual {
        if (!hasRole(role, account)) {
            revert AccessControlUnauthorizedAccount(account, role);
        }
    }

    /**
     * @dev Returns the admin role that controls `role`. See {grantRole} and
     * {revokeRole}.
     *
     * To change a role's admin, use {_setRoleAdmin}.
     */
    function getRoleAdmin(bytes32 role) public view virtual returns (bytes32) {
        return _roles[role].adminRole;
    }

    /**
     * @dev Grants `role` to `account`.
     *
     * If `account` had not been already granted `role`, emits a {RoleGranted}
     * event.
     *
     * Requirements:
     *
     * - the caller must have ``role``'s admin role.
     *
     * May emit a {RoleGranted} event.
     */
    function grantRole(bytes32 role, address account) public virtual onlyRole(getRoleAdmin(role)) {
        _grantRole(role, account);
    }

    /**
     * @dev Revokes `role` from `account`.
     *
     * If `account` had been granted `role`, emits a {RoleRevoked} event.
     *
     * Requirements:
     *
     * - the caller must have ``role``'s admin role.
     *
     * May emit a {RoleRevoked} event.
     */
    function revokeRole(bytes32 role, address account) public virtual onlyRole(getRoleAdmin(role)) {
        _revokeRole(role, account);
    }

    /**
     * @dev Revokes `role` from the calling account.
     *
     * Roles are often managed via {grantRole} and {revokeRole}: this function's
     * purpose is to provide a mechanism for accounts to lose their privileges
     * if they are compromised (such as when a trusted device is misplaced).
     *
     * If the calling account had been revoked `role`, emits a {RoleRevoked}
     * event.
     *
     * Requirements:
     *
     * - the caller must be `callerConfirmation`.
     *
     * May emit a {RoleRevoked} event.
     */
    function renounceRole(bytes32 role, address callerConfirmation) public virtual {
        if (callerConfirmation != _msgSender()) {
            revert AccessControlBadConfirmation();
        }

        _revokeRole(role, callerConfirmation);
    }

    /**
     * @dev Sets `adminRole` as ``role``'s admin role.
     *
     * Emits a {RoleAdminChanged} event.
     */
    function _setRoleAdmin(bytes32 role, bytes32 adminRole) internal virtual {
        bytes32 previousAdminRole = getRoleAdmin(role);
        _roles[role].adminRole = adminRole;
        emit RoleAdminChanged(role, previousAdminRole, adminRole);
    }

    /**
     * @dev Attempts to grant `role` to `account` and returns a boolean indicating if `role` was granted.
     *
     * Internal function without access restriction.
     *
     * May emit a {RoleGranted} event.
     */
    function _grantRole(bytes32 role, address account) internal virtual returns (bool) {
        if (!hasRole(role, account)) {
            _roles[role].hasRole[account] = true;
            emit RoleGranted(role, account, _msgSender());
            return true;
        } else {
            return false;
        }
    }

    /**
     * @dev Attempts to revoke `role` from `account` and returns a boolean indicating if `role` was revoked.
     *
     * Internal function without access restriction.
     *
     * May emit a {RoleRevoked} event.
     */
    function _revokeRole(bytes32 role, address account) internal virtual returns (bool) {
        if (hasRole(role, account)) {
            _roles[role].hasRole[account] = false;
            emit RoleRevoked(role, account, _msgSender());
            return true;
        } else {
            return false;
        }
    }
}

// ens/v1/BankonPriceOracle.sol

interface IAggregatorV3 {
    function latestRoundData()
        external view
        returns (uint80 roundId, int256 answer, uint256 startedAt,
                 uint256 updatedAt, uint80 answeredInRound);
    function decimals() external view returns (uint8);
}

interface IUniV3TwapLike {
    /// Returns arithmetic mean tick over `secondsAgo` for the given pool.
    function consult(address pool, uint32 secondsAgo)
        external view returns (int24 arithmeticMeanTick);
}

/// @title  BankonPriceOracle
/// @notice ENS-aligned length-tiered USD pricing with PYTHAI native discount.
///         All prices in USDC base units (6 decimals).
///         Agnostic: any registrar (BANKON, future tenants) can call priceUSD()
///         + priceInToken() against any supported asset.
contract BankonPriceOracle is AccessControl, IBankonPriceOracle {
    bytes32 public constant GOV_ROLE = keccak256("GOV_ROLE");

    /// MEDIUM tier defaults — see openagents/bankonsubnameregistry.md §2.
    uint256 public price3     = 320_000000;  // 3-char  $320/yr
    uint256 public price4     =  80_000000;  // 4-char  $80/yr
    uint256 public price5     =   5_000000;  // 5-char  $5/yr
    uint256 public price6     =   3_000000;  // 6-char  $3/yr
    uint256 public price7plus =   1_000000;  // 7+ char $1/yr

    /// PYTHAI-paid registrations get a 20% discount (in basis points).
    uint16 public pythaiDiscountBps = 2000;

    /// External feeds + tokens.
    IAggregatorV3 public ethUsdFeed;
    IUniV3TwapLike public twap;
    address public pythaiUsdcPool;
    address public pythaiToken;
    address public usdc;
    address public weth;

    /// Stub fallback PYTHAI/USDC rate when TWAP unavailable.
    /// Operator updates as PYTHAI/USDC liquidity matures.
    /// Quote returned as: usd6 * pythaiPerUsdcStub (1e18 decimals fixed).
    uint256 public pythaiPerUsdcStub = 50;

    event PricesUpdated(uint256 p3, uint256 p4, uint256 p5, uint256 p6, uint256 p7);
    event PythaiDiscountUpdated(uint16 oldBps, uint16 newBps);
    event FeedsUpdated(address ethUsdFeed, address twap, address pythaiUsdcPool);
    event TokensUpdated(address pythaiToken, address usdc, address weth);
    event PythaiStubUpdated(uint256 oldRate, uint256 newRate);

    error UnsupportedToken(address token);
    error BadEthPrice();
    error EmptyLabel();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOV_ROLE, admin);
    }

    /* ───── Read API ──────────────────────────────────────────────── */

    function priceUSD(string calldata label, uint256 durationYears)
        external view override
        returns (uint256 usd6)
    {
        uint256 len = bytes(label).length;
        if (len == 0) revert EmptyLabel();
        uint256 perYear = _perYearUSD(len);
        uint256 years_ = durationYears == 0 ? 1 : durationYears;
        return perYear * years_;
    }

    function priceInToken(string calldata label, uint256 durationYears, address token)
        external view override
        returns (uint256 amount)
    {
        uint256 len = bytes(label).length;
        if (len == 0) revert EmptyLabel();
        uint256 years_ = durationYears == 0 ? 1 : durationYears;
        uint256 usd6 = _perYearUSD(len) * years_;
        if (token == usdc) return usd6;
        if (token == weth) return _usdToEth(usd6);
        if (token == pythaiToken) {
            uint256 discounted = (usd6 * (10000 - pythaiDiscountBps)) / 10000;
            return _usdToPythai(discounted);
        }
        revert UnsupportedToken(token);
    }

    /* ───── Internals ────────────────────────────────────────────── */

    function _perYearUSD(uint256 len) internal view returns (uint256) {
        if (len <= 3) return price3;
        if (len == 4) return price4;
        if (len == 5) return price5;
        if (len == 6) return price6;
        return price7plus;
    }

    function _usdToEth(uint256 usd6) internal view returns (uint256) {
        if (address(ethUsdFeed) == address(0)) revert BadEthPrice();
        (, int256 px, , , ) = ethUsdFeed.latestRoundData();
        if (px <= 0) revert BadEthPrice();
        // Chainlink ETH/USD has 8 decimals. usd6 is 6-dec. Result in wei (18 dec).
        // wei = usd6 * 1e20 / px  (where px scale = 1e8)
        return (usd6 * 1e20) / uint256(px);
    }

    function _usdToPythai(uint256 usd6) internal view returns (uint256) {
        if (address(twap) != address(0) && pythaiUsdcPool != address(0)) {
            // Production path: consult tick → price via OracleLibrary.getQuoteAtTick.
            // For the hackathon ship, we record the tick was consulted and fall back
            // to the operator-set stub. Live wiring deferred to mainnet release.
            int24 tick = twap.consult(pythaiUsdcPool, 1800);
            tick; // silence unused; see post-hackathon work item
        }
        return usd6 * pythaiPerUsdcStub;
    }

    /* ───── Admin ────────────────────────────────────────────────── */

    function setPrices(
        uint256 _p3, uint256 _p4, uint256 _p5, uint256 _p6, uint256 _p7
    ) external onlyRole(GOV_ROLE) {
        price3 = _p3; price4 = _p4; price5 = _p5; price6 = _p6; price7plus = _p7;
        emit PricesUpdated(_p3, _p4, _p5, _p6, _p7);
    }

    function setPythaiDiscount(uint16 newBps) external onlyRole(GOV_ROLE) {
        require(newBps <= 5000, "discount > 50%");
        emit PythaiDiscountUpdated(pythaiDiscountBps, newBps);
        pythaiDiscountBps = newBps;
    }

    function setFeeds(address _ethUsd, address _twap, address _pool)
        external onlyRole(GOV_ROLE)
    {
        ethUsdFeed     = IAggregatorV3(_ethUsd);
        twap           = IUniV3TwapLike(_twap);
        pythaiUsdcPool = _pool;
        emit FeedsUpdated(_ethUsd, _twap, _pool);
    }

    function setTokens(address _pythai, address _usdc, address _weth)
        external onlyRole(GOV_ROLE)
    {
        pythaiToken = _pythai; usdc = _usdc; weth = _weth;
        emit TokensUpdated(_pythai, _usdc, _weth);
    }

    function setPythaiStub(uint256 newRate) external onlyRole(GOV_ROLE) {
        emit PythaiStubUpdated(pythaiPerUsdcStub, newRate);
        pythaiPerUsdcStub = newRate;
    }
}

