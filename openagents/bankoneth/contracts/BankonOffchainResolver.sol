// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {EIP712}        from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA}         from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/// @notice ENSIP-10 wildcard resolver interface — same as v2 inline.
interface IExtendedResolver {
    function resolve(bytes memory name, bytes memory data) external view returns (bytes memory);
}

/// @title  BankonOffchainResolver
/// @notice Phase 2.2 — CCIP-Read (EIP-3668) resolver. Reverts with
///         `OffchainLookup` when `resolve()` is called; the gateway at one
///         of the configured `urls` answers with a signed payload that the
///         client passes back through `resolveWithProof`. Verifies the
///         payload's EIP-712 signature against an allowlist of gateway
///         signers (multi-sig friendly + rotation-friendly).
///
///         Reference implementations consulted:
///           - gskril/ens-offchain-registrar
///           - github.com/ensdomains (CCIP-Read examples)
///           - docs.ens.domains/resolvers/ccip-read
///
///         CCIP-Read handshake:
///           1. Client calls resolve(name, data) on this contract.
///           2. We revert with OffchainLookup(sender, urls, callData,
///              callbackFunction = resolveWithProof.selector, extraData).
///           3. Client picks one URL from `urls`, POSTs {sender, data} JSON.
///           4. Gateway looks up the record from its store (SQLite/IPFS),
///              EIP-712-signs (result, expires, hash(callData)), and
///              returns the signed bytes.
///           5. Client calls resolveWithProof(response, extraData) on this
///              contract; we verify the signature, the expiry, and the
///              callData hash binding, then return the result.
contract BankonOffchainResolver is IExtendedResolver, EIP712, AccessControl {
    using ECDSA for bytes32;

    bytes32 public constant SIGNER_ROLE = keccak256("SIGNER_ROLE");

    /// @dev EIP-712 type hash for the gateway's signed response.
    ///      result:    the raw bytes the resolver would have returned
    ///      expires:   unix seconds after which the signed response stops being valid
    ///      sender:    the resolver contract address (this one)
    ///      callHash:  keccak256 of the original calldata, binds the proof to a specific query
    bytes32 private constant _OFFCHAIN_LOOKUP_TYPEHASH = keccak256(
        "OffchainLookupResponse(bytes result,uint64 expires,address sender,bytes32 callHash)"
    );

    /// @dev URLs the client should hit. Indexed for rotation.
    string[] private _urls;

    /// @dev OffchainLookup revert shape — must match EIP-3668 verbatim.
    error OffchainLookup(
        address sender,
        string[] urls,
        bytes callData,
        bytes4 callbackFunction,
        bytes extraData
    );

    error ProofExpired();
    error ProofSignerNotAllowed(address recovered);
    error ProofCallDataMismatch();

    event GatewayUrlsUpdated(string[] urls);
    event SignerSet(address indexed signer, bool active);

    constructor(address admin, string[] memory urls_, address initialSigner)
        EIP712("BankonOffchainResolver", "1")
    {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        if (initialSigner != address(0)) _grantRole(SIGNER_ROLE, initialSigner);
        _urls = urls_;
        emit GatewayUrlsUpdated(urls_);
        if (initialSigner != address(0)) emit SignerSet(initialSigner, true);
    }

    // ── Admin ──────────────────────────────────────────────────────

    function setUrls(string[] calldata urls_) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _urls = urls_;
        emit GatewayUrlsUpdated(urls_);
    }

    function grantSigner(address signer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(SIGNER_ROLE, signer);
        emit SignerSet(signer, true);
    }

    function revokeSigner(address signer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _revokeRole(SIGNER_ROLE, signer);
        emit SignerSet(signer, false);
    }

    function urls() external view returns (string[] memory) { return _urls; }

    // ── ENSIP-10 / EIP-3668 entry ─────────────────────────────────

    /// @inheritdoc IExtendedResolver
    function resolve(bytes memory name, bytes memory data)
        external
        view
        override
        returns (bytes memory)
    {
        // Per EIP-3668: revert with OffchainLookup. The client's wallet /
        // viem / ethers extracts the URLs + calldata, fetches the gateway,
        // and invokes resolveWithProof with the response.
        //
        // extraData carries the original (name, data) so the callback can
        // re-derive the namehash + bind the proof's callHash. We hash the
        // calldata here (cheaper than re-hashing in the callback) and pass
        // it through extraData.
        bytes memory callHash = abi.encode(keccak256(data));
        bytes memory extraData = abi.encode(name, data, callHash);

        revert OffchainLookup(
            address(this),
            _urls,
            data,
            this.resolveWithProof.selector,
            extraData
        );
    }

    // ── EIP-3668 callback ─────────────────────────────────────────

    /// @notice CCIP-Read callback. Verifies the gateway's EIP-712 signature
    ///         over (result, expires, sender, callHash), checks the expiry,
    ///         binds the proof to the original calldata, and returns the
    ///         result for the client to decode.
    function resolveWithProof(bytes calldata response, bytes calldata extraData)
        external
        view
        returns (bytes memory)
    {
        (
            bytes memory result,
            uint64       expires,
            bytes        memory signature
        ) = abi.decode(response, (bytes, uint64, bytes));

        if (block.timestamp > expires) revert ProofExpired();

        // Re-derive callHash from extraData so the gateway can't substitute
        // a response for a different query.
        (, bytes memory originalData, ) = abi.decode(extraData, (bytes, bytes, bytes));
        bytes32 callHash = keccak256(originalData);

        bytes32 structHash = keccak256(abi.encode(
            _OFFCHAIN_LOOKUP_TYPEHASH,
            keccak256(result),
            expires,
            address(this),
            callHash
        ));
        bytes32 digest = _hashTypedDataV4(structHash);
        address recovered = digest.recover(signature);

        if (!hasRole(SIGNER_ROLE, recovered)) revert ProofSignerNotAllowed(recovered);

        return result;
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
            interfaceId == 0x9061b923 ||                          // IExtendedResolver
            interfaceId == type(IExtendedResolver).interfaceId ||
            super.supportsInterface(interfaceId);
    }
}
