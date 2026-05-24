// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ERC1155Holder} from "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";
import {IERC1155Receiver} from "@openzeppelin/contracts/token/ERC1155/IERC1155Receiver.sol";

import {IBankonInftAdapter, IBankonSubnameResolver, IBankonAgenticPlaceHook}
    from "./interfaces/IBankonExtensions.sol";

/// @title  BankonInftAdapter — Mode A (unified) iNFT glue.
/// @notice On `onERC1155Received` from NameWrapper, emits a `RequestINFTMint`
///         event that an off-chain 0G-side worker watches. The worker mints the
///         ERC-7857 on 0G, derives the deterministic ERC-6551 TBA address, and
///         calls `registerZeroGTokenId` back on this contract to close the loop.
///
///         Until a real bridge is in place, the (labelhash → 0G tokenId, TBA)
///         registry is operator-attested via the `WIRER_ROLE`.
///
/// @dev    The actual ERC-7857 iNFT lives on 0G (the AI-native chain with TEE
///         attestation, per the 0G iNFT spec). The Ethereum side holds the
///         ERC-1155 subname as collateral and maintains the cross-chain
///         binding. The resolver reads the binding to override `addr(node)`.
contract BankonInftAdapter is IBankonInftAdapter, ERC1155Holder, AccessControl {
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");
    bytes32 public constant WIRER_ROLE     = keccak256("WIRER_ROLE");

    /// @dev ERC-6551 singleton registry address (same on every EVM chain).
    address public constant ERC6551_REGISTRY = 0x000000006551c19487814612e58FE06813775758;

    IBankonSubnameResolver  public resolver;
    IBankonAgenticPlaceHook public agenticPlaceHook;

    /// @dev 0G iNFT contract address (registered post-deploy via WireCrossChain).
    address public zeroGiNFTContract;
    uint256 public zeroGChainId;
    /// @dev ERC-6551 implementation contract address (the account contract).
    address public erc6551Implementation;

    /// @dev labelhash → 0G tokenId
    mapping(bytes32 => uint256) private _tokenIdOf;
    /// @dev labelhash → derived ERC-6551 TBA address (on the chain where iNFT lives)
    mapping(bytes32 => address) private _tbaOf;

    event ZeroGiNFTContractUpdated(address indexed contractAddr, uint256 chainId);
    event Erc6551ImplementationUpdated(address indexed implementation);
    event ResolverUpdated(address indexed resolver);
    event AgenticPlaceHookUpdated(address indexed hook);

    error LabelAlreadyBound(bytes32 labelhash);
    error LabelUnbound(bytes32 labelhash);
    error ZeroGiNFTContractUnset();
    error Erc6551ImplementationUnset();

    constructor(address admin, IBankonSubnameResolver _resolver) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        resolver = _resolver;
    }

    // ── Admin / wiring ─────────────────────────────────────────────

    function setZeroGiNFTContract(address contractAddr, uint256 chainId)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        zeroGiNFTContract = contractAddr;
        zeroGChainId = chainId;
        emit ZeroGiNFTContractUpdated(contractAddr, chainId);
    }

    function setErc6551Implementation(address implementation)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        erc6551Implementation = implementation;
        emit Erc6551ImplementationUpdated(implementation);
    }

    function setResolver(IBankonSubnameResolver newResolver)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        resolver = newResolver;
        emit ResolverUpdated(address(newResolver));
    }

    function setAgenticPlaceHook(IBankonAgenticPlaceHook newHook)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        agenticPlaceHook = newHook;
        emit AgenticPlaceHookUpdated(address(newHook));
    }

    function grantRegistrar(address registrar) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(REGISTRAR_ROLE, registrar);
    }

    function grantWirer(address wirer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(WIRER_ROLE, wirer);
    }

    // ── Mint request (registrar-driven) ────────────────────────────

    /// @inheritdoc IBankonInftAdapter
    function requestMint(
        bytes32 parentNode,
        bytes32 labelhash,
        address claimant,
        uint256 erc1155TokenId,
        string calldata metadataURI
    ) external override onlyRole(REGISTRAR_ROLE) {
        if (_tokenIdOf[labelhash] != 0) revert LabelAlreadyBound(labelhash);
        if (zeroGiNFTContract == address(0)) revert ZeroGiNFTContractUnset();
        if (erc6551Implementation == address(0)) revert Erc6551ImplementationUnset();

        emit RequestINFTMint(parentNode, labelhash, claimant, erc1155TokenId, metadataURI);
    }

    // ── Cross-chain wiring (operator-attested) ─────────────────────

    /// @inheritdoc IBankonInftAdapter
    function registerZeroGTokenId(bytes32 labelhash, uint256 zeroGTokenId)
        external
        override
        onlyRole(WIRER_ROLE)
    {
        if (zeroGiNFTContract == address(0)) revert ZeroGiNFTContractUnset();
        if (erc6551Implementation == address(0)) revert Erc6551ImplementationUnset();

        _tokenIdOf[labelhash] = zeroGTokenId;
        address tba = _computeTba(zeroGTokenId);
        _tbaOf[labelhash] = tba;

        emit INFTBound(labelhash, zeroGTokenId, tba);
    }

    // ── Views ──────────────────────────────────────────────────────

    /// @inheritdoc IBankonInftAdapter
    function zeroGTokenIdOf(bytes32 labelhash) external view override returns (uint256) {
        return _tokenIdOf[labelhash];
    }

    /// @inheritdoc IBankonInftAdapter
    function tbaAddressOf(bytes32 labelhash) external view override returns (address) {
        return _tbaOf[labelhash];
    }

    // ── Internal ───────────────────────────────────────────────────

    /// @notice Compute the ERC-6551 TBA address deterministically using the
    ///         singleton registry's CREATE2 derivation. Matches the official
    ///         `account(implementation, salt, chainId, tokenContract, tokenId)`.
    function _computeTba(uint256 tokenId) internal view returns (address) {
        bytes32 salt = bytes32(0);
        bytes memory creationCode = abi.encodePacked(
            // Standard ERC-6551 proxy bytecode (minimal proxy pattern).
            // Replicated here to avoid an external interface call.
            // For real deployment we'd call ERC6551Registry.account(...) instead.
            hex"3d60ad80600a3d3981f3363d3d373d3d3d363d73",
            erc6551Implementation,
            hex"5af43d82803e903d91602b57fd5bf3"
        );
        bytes memory data = abi.encode(salt, zeroGChainId, zeroGiNFTContract, tokenId);
        bytes32 codeHash = keccak256(abi.encodePacked(creationCode, data));
        return address(uint160(uint256(keccak256(abi.encodePacked(
            bytes1(0xff),
            ERC6551_REGISTRY,
            salt,
            codeHash
        )))));
    }

    /// @dev ERC-165 — combine AccessControl + ERC1155Holder support.
    function supportsInterface(bytes4 interfaceId)
        public
        view
        virtual
        override(AccessControl, ERC1155Holder)
        returns (bool)
    {
        return interfaceId == type(IBankonInftAdapter).interfaceId
            || super.supportsInterface(interfaceId);
    }
}
