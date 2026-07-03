// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title  IProofOracle — the proof.oracle required to connect with the "world".
/// @author cypherpunk2048
/// @notice The trust bridge between on-chain entitlement (persistence.state) and
///         an off-chain reality a gated room may require before admission:
///         personhood, presence, geolocation, a DeltaVerse room membership, a
///         modular-NFT possession proof, a zk attestation, etc.
///
///         The gate stays agnostic — it calls `proven(...)` and admits only if it
///         returns true. New world-conditions are new oracles, not new gate code:
///         that is the modular boundary. Reference modular-NFT expansion:
///         github.com/deltav-deltaverse.
interface IProofOracle {
    /// @param subject The wallet seeking connection (the identity).
    /// @param context The room / resource id the proof is for.
    /// @param proof   Opaque proof bytes (signed attestation, zk proof, NFT ref…).
    /// @return true iff `subject` satisfies the world-condition for `context`.
    function proven(address subject, bytes32 context, bytes calldata proof)
        external
        view
        returns (bool);
}
