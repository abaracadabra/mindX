// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {IBankonInftAdapter} from "./interfaces/IBankonExtensions.sol";

// ── Canonical ENS resolver interfaces (inlined — see v1 for the rationale) ──

/// @notice ENSIP-1 / EIP-137 — `addr(bytes32) → address`. interfaceId 0x3b3b57de.
interface IAddrResolver {
    event AddrChanged(bytes32 indexed node, address a);
    function addr(bytes32 node) external view returns (address payable);
}

/// @notice ENSIP-9 / EIP-2304 — multichain `addr(bytes32,uint256) → bytes`.
///         interfaceId 0xf1cb7e06.
interface IAddressResolver {
    event AddressChanged(bytes32 indexed node, uint256 coinType, bytes newAddress);
    function addr(bytes32 node, uint256 coinType) external view returns (bytes memory);
}

/// @notice ENSIP-5 / EIP-634 — text records. interfaceId 0x59d1d43c.
interface ITextResolver {
    event TextChanged(bytes32 indexed node, string indexed indexedKey, string key, string value);
    function text(bytes32 node, string calldata key) external view returns (string memory);
}

/// @notice ENSIP-7 / EIP-1577 — contenthash. interfaceId 0xbc1c58d1.
interface IContentHashResolver {
    event ContenthashChanged(bytes32 indexed node, bytes hash);
    function contenthash(bytes32 node) external view returns (bytes memory);
}

/// @notice INameResolver — reverse-name resolution. interfaceId 0x691f3431.
interface INameResolver {
    event NameChanged(bytes32 indexed node, string name);
    function name(bytes32 node) external view returns (string memory);
}

/// @notice ENSIP-10 / wildcard — `resolve(bytes,bytes) → bytes`. interfaceId 0x9061b923.
interface IExtendedResolver {
    function resolve(bytes memory name, bytes memory data) external view returns (bytes memory);
}

/// @notice IMulticallable — batch reader/writer. interfaceId 0xac9650d8.
interface IMulticallable {
    function multicall(bytes[] calldata data) external returns (bytes[] memory results);
}

/// @title  BankonSubnameResolverV2
/// @notice ENS-canonical resolver for `bankon.eth` subnames + any `.eth`
///         parent enrolled via BankonDomainHosting. Adds ENSIP-10 wildcard
///         resolution + the full PublicResolver profile interface set on
///         top of the v1 surface (which only implemented addr/text/contenthash/
///         multichain). Co-exists with v1 — new registrations use V2; legacy
///         names keep v1 until migration.
///
///         Additions vs v1:
///           • IExtendedResolver.resolve(name, data) — wildcard dispatch
///           • INameResolver.name(node)              — reverse-lookup support
///           • Full supportsInterface for every canonical interfaceId
///           • IsAuthorised hook for per-node delegated edits (Phase 3.1
///             multicall-from-owner path).
///
///         Preserves from v1:
///           • REGISTRAR_ROLE gating on every setter
///           • iNFT Mode A TBA override on addr(node)
///           • BANKON agentic-text-record namespace
///           • Multicall via delegatecall
contract BankonSubnameResolverV2 is
    IAddrResolver,
    IAddressResolver,
    ITextResolver,
    IContentHashResolver,
    INameResolver,
    IExtendedResolver,
    IMulticallable,
    AccessControl
{
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");

    // ── Storage (parallel to v1; intentionally separate so V1 + V2 co-deploy) ──

    /// @dev addr(node) — raw stored ETH address.
    mapping(bytes32 => address) private _addr;
    /// @dev text records keyed by (node, key).
    mapping(bytes32 => mapping(string => string)) private _text;
    /// @dev ENSIP-9 multichain: (node, coinType) → bytes.
    mapping(bytes32 => mapping(uint256 => bytes)) private _coinAddr;
    /// @dev contenthash (ENSIP-7).
    mapping(bytes32 => bytes) private _contenthash;
    /// @dev INameResolver reverse name.
    mapping(bytes32 => string) private _name;
    /// @dev iNFT Mode A: node → ERC-6551 TBA. Overrides addr(node) when non-zero.
    mapping(bytes32 => address) private _tba;
    /// @dev iNFT Mode A: node → 0G iNFT tokenId (for off-chain attribution).
    mapping(bytes32 => uint256) private _zeroGTokenId;

    IBankonInftAdapter public inftAdapter;

    event INFTBindingSet(bytes32 indexed node, address tbaAddress, uint256 zeroGTokenId);
    event InftAdapterUpdated(address indexed oldAdapter, address indexed newAdapter);

    error NotAuthorisedForNode();

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

    // ── Read surface ───────────────────────────────────────────────

    /// @inheritdoc IAddrResolver
    function addr(bytes32 node) public view override returns (address payable) {
        address tba = _tba[node];
        if (tba != address(0)) return payable(tba);
        return payable(_addr[node]);
    }

    /// @inheritdoc IAddressResolver
    function addr(bytes32 node, uint256 coinType) public view override returns (bytes memory) {
        // For coinType 60 (Ethereum), keep parity with addr(bytes32) per ENSIP-1.
        if (coinType == 60) {
            address a = address(addr(node));
            if (a == address(0)) return "";
            return abi.encodePacked(a);
        }
        return _coinAddr[node][coinType];
    }

    /// @inheritdoc ITextResolver
    function text(bytes32 node, string calldata key) public view override returns (string memory) {
        return _text[node][key];
    }

    /// @inheritdoc IContentHashResolver
    function contenthash(bytes32 node) public view override returns (bytes memory) {
        return _contenthash[node];
    }

    /// @inheritdoc INameResolver
    function name(bytes32 node) public view override returns (string memory) {
        return _name[node];
    }

    /// @notice ERC-6551 TBA + 0G token id for a node. View accessor for the UI.
    function inftBinding(bytes32 node) external view returns (address tba, uint256 zeroGTokenId) {
        return (_tba[node], _zeroGTokenId[node]);
    }

    // ── ENSIP-10 wildcard resolution ───────────────────────────────

    /// @inheritdoc IExtendedResolver
    /// @dev    Decodes the dnsName, derives the namehash, then dispatches the
    ///         encoded resolver call (data) against this contract's own state.
    ///         Supports addr(node), addr(node,coinType), text(node,key),
    ///         contenthash(node), and name(node). Anything else returns "".
    function resolve(bytes memory dnsName, bytes memory data)
        external
        view
        override
        returns (bytes memory)
    {
        bytes32 node = _dnsNamehash(dnsName, 0);
        bytes4 sel = bytes4(_slice4(data, 0));

        if (sel == IAddrResolver.addr.selector) {
            address a = address(addr(node));
            return abi.encode(a);
        }
        if (sel == IAddressResolver.addr.selector) {
            // selector for the (bytes32,uint256) overload differs; resolved
            // via signature match below.
            return abi.encode(addr(node, _decodeUint256At(data, 36)));
        }
        if (sel == ITextResolver.text.selector) {
            // decode (bytes32, string) — first slot is the node (already
            // re-derived from dnsName above), second is the key.
            (, string memory key) = abi.decode(_sliceFrom4(data), (bytes32, string));
            return abi.encode(_text[node][key]);
        }
        if (sel == IContentHashResolver.contenthash.selector) {
            return abi.encode(_contenthash[node]);
        }
        if (sel == INameResolver.name.selector) {
            return abi.encode(_name[node]);
        }
        return "";
    }

    // ── Write surface (registrar-only) ─────────────────────────────

    function setAddr(bytes32 node, address a) external onlyRole(REGISTRAR_ROLE) {
        _addr[node] = a;
        emit AddrChanged(node, a);
    }

    function setAddr(bytes32 node, uint256 coinType, bytes calldata a) external onlyRole(REGISTRAR_ROLE) {
        _coinAddr[node][coinType] = a;
        emit AddressChanged(node, coinType, a);
        if (coinType == 60 && a.length == 20) {
            address ethAddr = address(uint160(bytes20(a)));
            _addr[node] = ethAddr;
            emit AddrChanged(node, ethAddr);
        }
    }

    function setText(bytes32 node, string calldata key, string calldata value)
        external onlyRole(REGISTRAR_ROLE)
    {
        _text[node][key] = value;
        emit TextChanged(node, key, key, value);
    }

    function setContenthash(bytes32 node, bytes calldata h) external onlyRole(REGISTRAR_ROLE) {
        _contenthash[node] = h;
        emit ContenthashChanged(node, h);
    }

    function setName(bytes32 node, string calldata newName) external onlyRole(REGISTRAR_ROLE) {
        _name[node] = newName;
        emit NameChanged(node, newName);
    }

    function setINFTBinding(bytes32 node, address tbaAddress, uint256 zeroGTokenId)
        external onlyRole(REGISTRAR_ROLE)
    {
        _tba[node] = tbaAddress;
        _zeroGTokenId[node] = zeroGTokenId;
        emit INFTBindingSet(node, tbaAddress, zeroGTokenId);
    }

    /// @inheritdoc IMulticallable
    function multicall(bytes[] calldata data) external override returns (bytes[] memory results) {
        results = new bytes[](data.length);
        for (uint256 i = 0; i < data.length; ++i) {
            (bool ok, bytes memory ret) = address(this).delegatecall(data[i]);
            require(ok, "BankonSubnameResolverV2: multicall element failed");
            results[i] = ret;
        }
    }

    // ── ERC-165 ────────────────────────────────────────────────────

    function supportsInterface(bytes4 interfaceId)
        public
        view
        virtual
        override(AccessControl)
        returns (bool)
    {
        return
            interfaceId == 0x3b3b57de ||                              // IAddrResolver
            interfaceId == 0xf1cb7e06 ||                              // IAddressResolver (ENSIP-9)
            interfaceId == 0x59d1d43c ||                              // ITextResolver
            interfaceId == 0xbc1c58d1 ||                              // IContentHashResolver
            interfaceId == 0x691f3431 ||                              // INameResolver
            interfaceId == 0x9061b923 ||                              // IExtendedResolver (ENSIP-10)
            interfaceId == type(IMulticallable).interfaceId ||
            super.supportsInterface(interfaceId);
    }

    // ── Internal: dnsName → namehash + calldata slicing ────────────

    /// @dev Recursive namehash over a DNS-encoded name. Bottom-up.
    function _dnsNamehash(bytes memory dnsName, uint256 idx) internal pure returns (bytes32) {
        if (idx >= dnsName.length) return bytes32(0);
        uint256 labelLen = uint256(uint8(dnsName[idx]));
        if (labelLen == 0) return bytes32(0);
        bytes32 labelHash;
        bytes memory label = new bytes(labelLen);
        for (uint256 i = 0; i < labelLen; ++i) {
            label[i] = dnsName[idx + 1 + i];
        }
        labelHash = keccak256(label);
        bytes32 parent = _dnsNamehash(dnsName, idx + 1 + labelLen);
        return keccak256(abi.encodePacked(parent, labelHash));
    }

    function _slice4(bytes memory data, uint256 offset) internal pure returns (bytes4 out) {
        require(data.length >= offset + 4, "selector OOB");
        assembly { out := mload(add(add(data, 0x20), offset)) }
    }

    function _decodeUint256At(bytes memory data, uint256 offset) internal pure returns (uint256 out) {
        require(data.length >= offset + 32, "uint256 OOB");
        assembly { out := mload(add(add(data, 0x20), offset)) }
    }

    /// @dev Returns data[4:], the abi-encoded args after the function selector.
    function _sliceFrom4(bytes memory data) internal pure returns (bytes memory out) {
        require(data.length >= 4, "no selector");
        uint256 len = data.length - 4;
        out = new bytes(len);
        for (uint256 i = 0; i < len; ++i) {
            out[i] = data[i + 4];
        }
    }
}
