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

// ens/v1/BankonReputationGate.sol

/// @notice External BONAFIDE / Censura-style reputation surface.
///         Any framework can implement this; this contract is the default
///         implementation backed by an admin-set score map + an optional
///         secondary oracle (BONAFIDE).
interface IExternalReputationOracle {
    function score(address agent) external view returns (uint256);
}

/// @notice External attestation registry (e.g. ERC-8004 TEE attestation).
interface IAttestationRegistry {
    function isTeeAttested(address agent) external view returns (bool);
}

/// @notice External fungible-token stake check (e.g. PYTHAI ASA bridge view).
interface IStakeView {
    function stakedOf(address agent) external view returns (uint256);
}

/// @title  BankonReputationGate
/// @notice Pluggable eligibility check for BANKON registrations.
///         Free tier requires ANY of:
///           - BONAFIDE/Censura score >= freeThreshold
///           - PYTHAI stake >= freeStakeThreshold
///           - TEE attestation (ERC-8004) flag
///         Paid tier requires only that the address is not banned.
contract BankonReputationGate is AccessControl, IBankonReputationGate {
    bytes32 public constant GOV_ROLE = keccak256("GOV_ROLE");

    /// Minimum BONAFIDE score for free registration. Default 100 per spec.
    uint256 public freeThreshold = 100;
    /// Minimum PYTHAI stake for free registration. Default 10_000 (assumes 6-dec ASA).
    uint256 public freeStakeThreshold = 10_000 * 1e6;

    /// Optional oracles. Any of zero address means: feature disabled.
    IExternalReputationOracle public bonafide;
    IAttestationRegistry public attestation;
    IStakeView public stake;

    /// Operator-set scores for dev/test or for emergencies. Takes precedence
    /// over the bonafide oracle if non-zero.
    mapping(address => uint256) private _adminScore;
    mapping(address => bool) public banned;

    event ThresholdsUpdated(uint256 freeScore, uint256 freeStake);
    event OraclesUpdated(address bonafide, address attestation, address stake);
    event AdminScoreSet(address indexed agent, uint256 score);
    event BanSet(address indexed agent, bool banned);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOV_ROLE, admin);
    }

    /* ───── Read API ──────────────────────────────────────────────── */

    function isEligibleForRegistration(address agent) external view override returns (bool) {
        if (agent == address(0)) return false;
        return !banned[agent];
    }

    function isEligibleForFree(address agent) external view override returns (bool) {
        if (agent == address(0) || banned[agent]) return false;
        if (bonafideScore(agent) >= freeThreshold) return true;
        if (address(stake) != address(0) && stake.stakedOf(agent) >= freeStakeThreshold) return true;
        if (address(attestation) != address(0) && attestation.isTeeAttested(agent)) return true;
        return false;
    }

    function bonafideScore(address agent) public view override returns (uint256) {
        uint256 admin = _adminScore[agent];
        if (admin > 0) return admin;
        if (address(bonafide) != address(0)) return bonafide.score(agent);
        return 0;
    }

    /* ───── Admin ────────────────────────────────────────────────── */

    function setThresholds(uint256 _freeScore, uint256 _freeStake)
        external onlyRole(GOV_ROLE)
    {
        freeThreshold = _freeScore;
        freeStakeThreshold = _freeStake;
        emit ThresholdsUpdated(_freeScore, _freeStake);
    }

    function setOracles(address _bonafide, address _attestation, address _stake)
        external onlyRole(GOV_ROLE)
    {
        bonafide    = IExternalReputationOracle(_bonafide);
        attestation = IAttestationRegistry(_attestation);
        stake       = IStakeView(_stake);
        emit OraclesUpdated(_bonafide, _attestation, _stake);
    }

    function setAdminScore(address agent, uint256 score) external onlyRole(GOV_ROLE) {
        _adminScore[agent] = score;
        emit AdminScoreSet(agent, score);
    }

    function setBanned(address agent, bool isBanned) external onlyRole(GOV_ROLE) {
        banned[agent] = isBanned;
        emit BanSet(agent, isBanned);
    }
}

