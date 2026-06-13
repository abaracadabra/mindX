// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {IBankonSubnameResolver, IBankonInftAdapter} from "./interfaces/IBankonExtensions.sol";

/// @title  BankonSubnameResolver
/// @notice Minimal ENS-compatible resolver for `bankon.eth` subnames + any
///         `.eth` parent enrolled via BankonDomainHosting. Adds the BANKON
///         text-record namespace and the iNFT Mode A `addr(node)` override.
///
///         Text-record keys (convention):
///             - "mindx.endpoint"          consumer URL for the agent (https://…)
///             - "bonafide.attestation"    on-chain BONAFIDE attestation hash
///             - "agent.capabilities"      JSON blob describing capabilities
///             - "inft.uri"                ERC-7857 metadata URI on 0G
///             - "agenticplace.listing"    listing id on agenticplace.pythai.net
///
/// @dev    Self-contained — does not inherit from the upstream ENS PublicResolver
///         on purpose, so the module can compile without the `ens-contracts`
///         submodule being present. The interface still matches what
///         BankonSubnameRegistrar expects from `IPublicResolver` (see IBankon.sol).
contract BankonSubnameResolver is IBankonSubnameResolver, AccessControl {
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");

    /// @dev When iNFT Mode A is bound for a node, `addr(node)` returns the TBA.
    ///      When unbound, `addr(node)` returns the raw stored address.
    mapping(bytes32 => address) private _addr;
    mapping(bytes32 => mapping(string => string)) private _text;
    mapping(bytes32 => mapping(uint256 => bytes)) private _coinAddr;
    mapping(bytes32 => bytes) private _contenthash;

    /// @dev iNFT Mode A binding: node → ERC-6551 TBA.
    mapping(bytes32 => address) private _tba;
    /// @dev iNFT Mode A binding: node → 0G iNFT tokenId.
    mapping(bytes32 => uint256) private _zeroGTokenId;

    IBankonInftAdapter public inftAdapter;

    event AddrSet(bytes32 indexed node, address a);
    event TextSet(bytes32 indexed node, string key, string value);
    event INFTBindingSet(bytes32 indexed node, address tbaAddress, uint256 zeroGTokenId);
    event InftAdapterUpdated(address indexed oldAdapter, address indexed newAdapter);

    constructor(address admin, IBankonInftAdapter adapter) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        inftAdapter = adapter;
    }

    // ── Admin ──────────────────────────────────────────────────────

    function setInftAdapter(IBankonInftAdapter newAdapter) external onlyRole(DEFAULT_ADMIN_ROLE) {
        emit InftAdapterUpdated(address(inftAdapter), address(newAdapter));
        inftAdapter = newAdapter;
    }

    function grantRegistrar(address registrar) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(REGISTRAR_ROLE, registrar);
    }

    function revokeRegistrar(address registrar) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _revokeRole(REGISTRAR_ROLE, registrar);
    }

    // ── ENS resolution surface ─────────────────────────────────────

    /// @inheritdoc IBankonSubnameResolver
    function addr(bytes32 node) external view override returns (address) {
        address tba = _tba[node];
        if (tba != address(0)) {
            return tba;
        }
        return _addr[node];
    }

    /// @inheritdoc IBankonSubnameResolver
    function text(bytes32 node, string calldata key) external view override returns (string memory) {
        return _text[node][key];
    }

    function coinAddr(bytes32 node, uint256 coinType) external view returns (bytes memory) {
        return _coinAddr[node][coinType];
    }

    function contenthash(bytes32 node) external view returns (bytes memory) {
        return _contenthash[node];
    }

    // ── ENS write surface (registrar-only) ─────────────────────────

    /// @inheritdoc IBankonSubnameResolver
    function setAddr(bytes32 node, address a) external override onlyRole(REGISTRAR_ROLE) {
        _addr[node] = a;
        emit AddrSet(node, a);
    }

    /// @notice ENSIP-9 multichain address setter (Base, Algorand, etc.).
    function setAddr(bytes32 node, uint256 coinType, bytes calldata a) external onlyRole(REGISTRAR_ROLE) {
        _coinAddr[node][coinType] = a;
    }

    /// @inheritdoc IBankonSubnameResolver
    function setText(bytes32 node, string calldata key, string calldata value) external override onlyRole(REGISTRAR_ROLE) {
        _text[node][key] = value;
        emit TextSet(node, key, value);
    }

    function setContenthash(bytes32 node, bytes calldata h) external onlyRole(REGISTRAR_ROLE) {
        _contenthash[node] = h;
    }

    /// @inheritdoc IBankonSubnameResolver
    function setINFTBinding(bytes32 node, address tbaAddress, uint256 zeroGTokenId)
        external
        override
        onlyRole(REGISTRAR_ROLE)
    {
        _tba[node] = tbaAddress;
        _zeroGTokenId[node] = zeroGTokenId;
        emit INFTBindingSet(node, tbaAddress, zeroGTokenId);
    }

    /// @notice Minimal multicall — registrar batches setAddr + setText + setContenthash
    ///         into a single tx, same shape ENS PublicResolver exposes.
    function multicall(bytes[] calldata data) external returns (bytes[] memory results) {
        results = new bytes[](data.length);
        for (uint256 i = 0; i < data.length; ++i) {
            (bool ok, bytes memory ret) = address(this).delegatecall(data[i]);
            require(ok, "BankonSubnameResolver: multicall element failed");
            results[i] = ret;
        }
    }

    /// @dev ERC-165 — advertise IBankonSubnameResolver.
    function supportsInterface(bytes4 interfaceId)
        public
        view
        virtual
        override(AccessControl)
        returns (bool)
    {
        return interfaceId == type(IBankonSubnameResolver).interfaceId
            || super.supportsInterface(interfaceId);
    }
}
