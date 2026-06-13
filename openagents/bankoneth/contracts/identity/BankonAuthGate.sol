// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {ECDSA}    from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {Strings}  from "@openzeppelin/contracts/utils/Strings.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

import {INameWrapper} from "../interfaces/IBankon.sol";

/// @notice Resolver subset BankonAuthGate uses for mode-2 text-record checks.
interface IAuthGateResolver {
    function text(bytes32 node, string calldata key) external view returns (string memory);
}

/// @title  BankonAuthGate
/// @notice Phase 2.4 — on-chain SIWE / EIP-4361 verifier for ENS-gated
///         downstream services. Two modes:
///
///         **Mode 1: NameWrapper-ownership**
///         Given a SIWE message digest + signature + label, recovers the
///         signer and asserts they own `label.bankon.eth` per NameWrapper.
///         Use when the gating predicate is "must hold *.bankon.eth".
///
///         **Mode 2: Resolver-text-record claim**
///         Given a digest + signature + name + key, recovers the signer
///         and asserts the resolver's text(node, key) equals the
///         lowercased hex address of the signer. Use when names declare
///         their authorised users via an arbitrary resolver text key
///         (the pattern github.com/mDeisen/ensauth chose).
///
///         The gate verifies signatures over an EIP-191 ("\x19Ethereum
///         Signed Message:\n…") digest — the same format MetaMask
///         personal_sign produces. This matches the SIWE/EIP-4361 default.
///         CAIP-122 callers using EIP-712 typed-data should hash their
///         payload via _hashTypedDataV4 and pass the result directly.
///
///         Stateless — no storage writes. Anyone can call. Anyone can
///         re-deploy. The SIWE bundle (message + signature) should be
///         scoped via nonce + domain + expirationTime fields in the
///         message itself; replay defence lives in the caller, not here.
contract BankonAuthGate {
    using ECDSA for bytes32;
    using Strings for uint160;

    INameWrapper public immutable nameWrapper;
    bytes32      public immutable bankonEthNode;

    error LabelEmpty();

    constructor(INameWrapper _nameWrapper, bytes32 _bankonEthNode) {
        nameWrapper   = _nameWrapper;
        bankonEthNode = _bankonEthNode;
    }

    // ── Mode 1: NameWrapper-ownership ─────────────────────────────

    /// @notice Returns true when the EIP-191 personal_sign signature over
    ///         `siweMessage` recovers an address that owns
    ///         `label.bankon.eth` via NameWrapper. View-only; no replay
    ///         protection (callers manage nonce + expiry in the SIWE body).
    function verifyOwnsLabel(
        string calldata siweMessage,
        bytes  calldata signature,
        string calldata label
    ) external view returns (bool) {
        if (bytes(label).length == 0) revert LabelEmpty();
        address signer = _recoverEip191(siweMessage, signature);
        bytes32 subnode = keccak256(abi.encodePacked(bankonEthNode, keccak256(bytes(label))));
        return nameWrapper.ownerOf(uint256(subnode)) == signer;
    }

    /// @notice Like `verifyOwnsLabel` but the caller supplies the digest
    ///         directly. Use for EIP-712 typed-data callers.
    function verifyOwnsLabelDigest(
        bytes32 digest,
        bytes  calldata signature,
        string calldata label
    ) external view returns (bool) {
        if (bytes(label).length == 0) revert LabelEmpty();
        address signer = digest.recover(signature);
        bytes32 subnode = keccak256(abi.encodePacked(bankonEthNode, keccak256(bytes(label))));
        return nameWrapper.ownerOf(uint256(subnode)) == signer;
    }

    // ── Mode 2: Resolver-text-record claim ─────────────────────────

    /// @notice Returns true when the signer (recovered from a personal_sign
    ///         signature over `siweMessage`) is also the address declared
    ///         in `resolver.text(node, key)`. The text record must be the
    ///         lowercased hex (EIP-55 form NOT supported) of the signer.
    function verifyTextClaim(
        string calldata siweMessage,
        bytes  calldata signature,
        IAuthGateResolver resolver,
        bytes32 node,
        string calldata key
    ) external view returns (bool) {
        address signer = _recoverEip191(siweMessage, signature);
        string memory val = resolver.text(node, key);
        return _eqLower(val, _addrToLowerHex(signer));
    }

    /// @notice Digest-direct variant of `verifyTextClaim` (EIP-712-friendly).
    function verifyTextClaimDigest(
        bytes32 digest,
        bytes  calldata signature,
        IAuthGateResolver resolver,
        bytes32 node,
        string calldata key
    ) external view returns (bool) {
        address signer = digest.recover(signature);
        string memory val = resolver.text(node, key);
        return _eqLower(val, _addrToLowerHex(signer));
    }

    // ── Internal ───────────────────────────────────────────────────

    function _recoverEip191(string calldata msg_, bytes calldata sig)
        internal pure returns (address)
    {
        bytes32 digest = MessageHashUtils.toEthSignedMessageHash(bytes(msg_));
        return digest.recover(sig);
    }

    function _addrToLowerHex(address a) internal pure returns (string memory) {
        // Strings.toHexString(uint160, 20) returns lowercased "0x...".
        return uint160(a).toHexString(20);
    }

    function _eqLower(string memory a, string memory b) internal pure returns (bool) {
        bytes memory ba = bytes(a);
        bytes memory bb = bytes(b);
        if (ba.length != bb.length) return false;
        for (uint256 i = 0; i < ba.length; ++i) {
            bytes1 c = ba[i];
            if (c >= 0x41 && c <= 0x5A) c = bytes1(uint8(c) + 32); // ASCII A→a
            if (c != bb[i]) return false;
        }
        return true;
    }
}
