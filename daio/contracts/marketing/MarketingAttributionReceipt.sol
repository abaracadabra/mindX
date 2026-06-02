// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {EIP712}            from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA}             from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {AccessControl}     from "@openzeppelin/contracts/access/AccessControl.sol";

import {ITessera}          from "./interfaces/ITessera.sol";
import {ICensura}          from "./interfaces/ICensura.sol";

/// @title  MarketingAttributionReceipt
/// @author marketinga.bankon.eth
///
/// @notice The CAMPAIGN ENVELOPE in the three-receipt model.
///
///         A campaign emits three orthogonal receipt types. This is the third:
///           1. `Tessera.sol`        — WHO acted, with what authority, and when (per-action identity).
///           2. `X402Receipt.sol`    — WAS A PAYMENT settled (per-payment proof).
///           3. `MarketingAttributionReceipt` — WHAT was the campaign, why, total cost,
///                                              what outcome (per-campaign envelope).
///
///         A typical campaign emits 1 of these + N Tessera credentials + M X402Receipts.
///         All three cross-reference each other by `traceId` (32-byte hash off-chain
///         derived from `campaignId | sub-agent | step`).
///
/// @dev    Storage discipline:
///         - Replay protection via per-(agent, campaignId) nonce. Strict.
///         - We do not store the receipt struct on-chain. Indexed events are the
///           durable artifact; subgraphs / Dune dashboards reconstruct from logs.
///           Storage cost on Base is sub-cent; event-only is cheaper still.
///         - Censura hook reverts on faded/ghosted/blocked agents. The Conclave
///           Censura contract uses uint8 reputation; faded ≡ score below the
///           registrar-set floor.
///         - We deliberately do NOT validate the economic content of the
///           envelope (spend, outcome metric). The signature is the trust
///           boundary; agent asserts the values by signing.
///
///         Deploy target: Base mainnet (sub-cent per receipt).
///         The `MarketingTreasury.sol` companion lives on Ethereum L1 and is
///         reachable via off-chain join on `campaignId`.
contract MarketingAttributionReceipt is EIP712, AccessControl {
    using ECDSA for bytes32;

    bytes32 public constant TESSERA_AUTHORITY_ROLE = keccak256("TESSERA_AUTHORITY_ROLE");
    bytes32 public constant CENSURA_AUTHORITY_ROLE = keccak256("CENSURA_AUTHORITY_ROLE");

    /// @notice Conclave Tessera credential issuer. The signer must currently
    ///         hold a valid Tessera credential.
    ITessera public tessera;

    /// @notice Conclave Censura reputation registry. Agents below `censuraFloor`
    ///         are faded — receipts revert.
    ICensura public censura;

    /// @notice Reputation floor; below this an agent is faded.
    uint8 public censuraFloor;

    /// @notice Per-(agent, campaignId) nonce — strict replay protection.
    mapping(address => mapping(bytes32 => uint64)) public nonces;

    /// @notice EIP-712 typehash for the campaign envelope.
    ///         Keep field set in lockstep with `CampaignEnvelope` in
    ///         `agents/marketing/boardroom_orchestrator.py`.
    ///         Version bumped from 1 → 2 to add `boardroomSessionId`. The
    ///         `bytes32 boardroomSessionId` is the `BoardroomSession.session_id`
    ///         that approved the campaign — joins the on-chain receipt to the
    ///         off-chain weighted-vote record (CEO + Seven Soldiers).
    bytes32 public constant ENVELOPE_TYPEHASH = keccak256(
        "MarketingCampaign("
        "bytes32 campaignId,"
        "bytes32 briefCid,"
        "bytes32 audienceClusterHash,"
        "uint32  channelSetMask,"
        "uint128 totalSpendUsdMicro,"
        "bytes32 outcomeMetricCid,"
        "bytes32 boardroomSessionId,"
        "bytes32 traceId,"
        "uint64  nonce,"
        "uint64  signedAt"
        ")"
    );

    event AttributionReceiptRecorded(
        bytes32 indexed campaignId,
        address indexed agent,
        bytes32 indexed boardroomSessionId,
        bytes32 traceId,
        bytes32 briefCid,
        bytes32 audienceClusterHash,
        uint32  channelSetMask,
        uint128 totalSpendUsdMicro,
        bytes32 outcomeMetricCid,
        uint64  nonce,
        uint64  signedAt,
        uint64  blockNumber
    );

    event TesseraUpdated(address indexed previous, address indexed current);
    event CensuraUpdated(address indexed previous, address indexed current);
    event CensuraFloorUpdated(uint8 previous, uint8 current);

    error AgentMissingTessera(address agent);
    error AgentFaded(address agent, uint8 score, uint8 floor);
    error InvalidNonce(address agent, bytes32 campaignId, uint64 expected, uint64 provided);
    error InvalidSignature(address recovered, address expected);
    error ZeroAgent();

    constructor(
        address admin,
        ITessera tessera_,
        ICensura censura_,
        uint8 censuraFloor_
    ) EIP712("MarketingAttributionReceipt", "2") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(TESSERA_AUTHORITY_ROLE, admin);
        _grantRole(CENSURA_AUTHORITY_ROLE, admin);
        tessera = tessera_;
        censura = censura_;
        censuraFloor = censuraFloor_;
    }

    // ─────────────────────────────────────────────────────────────────
    // Admin
    // ─────────────────────────────────────────────────────────────────

    function setTessera(ITessera tessera_) external onlyRole(TESSERA_AUTHORITY_ROLE) {
        emit TesseraUpdated(address(tessera), address(tessera_));
        tessera = tessera_;
    }

    function setCensura(ICensura censura_) external onlyRole(CENSURA_AUTHORITY_ROLE) {
        emit CensuraUpdated(address(censura), address(censura_));
        censura = censura_;
    }

    function setCensuraFloor(uint8 floor_) external onlyRole(CENSURA_AUTHORITY_ROLE) {
        emit CensuraFloorUpdated(censuraFloor, floor_);
        censuraFloor = floor_;
    }

    // ─────────────────────────────────────────────────────────────────
    // Public surface
    // ─────────────────────────────────────────────────────────────────

    /// @notice Compute the EIP-712 digest for a campaign envelope. Off-chain
    ///         signer hashes this and signs with the agent's wallet.
    function envelopeDigest(
        bytes32 campaignId,
        bytes32 briefCid,
        bytes32 audienceClusterHash,
        uint32  channelSetMask,
        uint128 totalSpendUsdMicro,
        bytes32 outcomeMetricCid,
        bytes32 boardroomSessionId,
        bytes32 traceId,
        uint64  nonce,
        uint64  signedAt
    ) public view returns (bytes32) {
        bytes32 structHash = keccak256(
            abi.encode(
                ENVELOPE_TYPEHASH,
                campaignId,
                briefCid,
                audienceClusterHash,
                channelSetMask,
                totalSpendUsdMicro,
                outcomeMetricCid,
                boardroomSessionId,
                traceId,
                nonce,
                signedAt
            )
        );
        return _hashTypedDataV4(structHash);
    }

    /// @notice Record one MarketingAttributionReceipt.
    ///
    /// @dev    Reverts on:
    ///          - agent == address(0)
    ///          - agent has no valid Tessera credential
    ///          - agent's Censura score < censuraFloor
    ///          - nonce mismatch (must equal current nonce; auto-increments on success)
    ///          - signature does not recover to `agent`
    function record(
        address agent,
        bytes32 campaignId,
        bytes32 briefCid,
        bytes32 audienceClusterHash,
        uint32  channelSetMask,
        uint128 totalSpendUsdMicro,
        bytes32 outcomeMetricCid,
        bytes32 boardroomSessionId,
        bytes32 traceId,
        uint64  nonce,
        uint64  signedAt,
        bytes calldata signature
    ) external {
        if (agent == address(0)) revert ZeroAgent();

        // Tessera identity gate
        if (address(tessera) != address(0) && !tessera.hasValidCredential(agent)) {
            revert AgentMissingTessera(agent);
        }

        // Censura reputation gate
        if (address(censura) != address(0)) {
            uint8 s = censura.score(agent);
            if (s < censuraFloor) revert AgentFaded(agent, s, censuraFloor);
        }

        // Nonce gate
        uint64 expected = nonces[agent][campaignId];
        if (nonce != expected) revert InvalidNonce(agent, campaignId, expected, nonce);

        // Signature gate
        bytes32 digest = envelopeDigest(
            campaignId,
            briefCid,
            audienceClusterHash,
            channelSetMask,
            totalSpendUsdMicro,
            outcomeMetricCid,
            boardroomSessionId,
            traceId,
            nonce,
            signedAt
        );
        address recovered = digest.recover(signature);
        if (recovered != agent) revert InvalidSignature(recovered, agent);

        // Effects
        unchecked { nonces[agent][campaignId] = expected + 1; }

        emit AttributionReceiptRecorded(
            campaignId,
            agent,
            boardroomSessionId,
            traceId,
            briefCid,
            audienceClusterHash,
            channelSetMask,
            totalSpendUsdMicro,
            outcomeMetricCid,
            nonce,
            signedAt,
            uint64(block.number)
        );
    }
}
