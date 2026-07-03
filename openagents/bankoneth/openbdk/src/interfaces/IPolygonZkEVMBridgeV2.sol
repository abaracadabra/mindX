// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.20;

/**
 * @title IPolygonZkEVMBridgeV2
 * @notice Interface for the AggLayer Unified Bridge (LxLy)
 * @dev Canonical bridge deployed on Ethereum mainnet at:
 *      0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe
 *      Same address on every AggLayer-connected chain (deterministic deployment)
 *
 *      Source reference: github.com/agglayer/agglayer-contracts
 *      License: AGPL-3.0 (Polygon canonical)
 *
 * @custom:security-contact security@openbdk.org
 */
interface IPolygonZkEVMBridgeV2 {
    /// @notice Bridge an asset (native or ERC-20) to a destination network
    /// @param destinationNetwork Network ID (0=Ethereum, 1=zkEVM, N=connected chain)
    /// @param destinationAddress Recipient on destination chain
    /// @param amount Token amount in wei
    /// @param token ERC-20 address; address(0) for native ETH/gas token
    /// @param forceUpdateGlobalExitRoot Update GER immediately for faster claims
    /// @param permitData Optional ERC-2612 permit signature
    function bridgeAsset(
        uint32 destinationNetwork,
        address destinationAddress,
        uint256 amount,
        address token,
        bool forceUpdateGlobalExitRoot,
        bytes calldata permitData
    ) external payable;

    /// @notice Bridge an arbitrary message to a destination network
    /// @param destinationNetwork Destination AggLayer network ID
    /// @param destinationAddress Receiver contract on destination
    /// @param forceUpdateGlobalExitRoot Update GER immediately
    /// @param metadata Arbitrary calldata for the receiver
    function bridgeMessage(
        uint32 destinationNetwork,
        address destinationAddress,
        bool forceUpdateGlobalExitRoot,
        bytes calldata metadata
    ) external payable;

    /// @notice Claim a bridged asset on the destination chain
    /// @dev Verifies two 32-depth Sparse Merkle Tree proofs against committed exit roots
    function claimAsset(
        bytes32[32] calldata smtProofLocalExitRoot,
        bytes32[32] calldata smtProofRollupExitRoot,
        uint256 globalIndex,
        bytes32 mainnetExitRoot,
        bytes32 rollupExitRoot,
        uint32 originNetwork,
        address originTokenAddress,
        uint32 destinationNetwork,
        address destinationAddress,
        uint256 amount,
        bytes calldata metadata
    ) external;

    /// @notice Claim a bridged message on the destination chain
    /// @dev Calls IBridgeMessageReceiver.onMessageReceived on the destination
    function claimMessage(
        bytes32[32] calldata smtProofLocalExitRoot,
        bytes32[32] calldata smtProofRollupExitRoot,
        uint256 globalIndex,
        bytes32 mainnetExitRoot,
        bytes32 rollupExitRoot,
        uint32 originNetwork,
        address originAddress,
        uint32 destinationNetwork,
        address destinationAddress,
        uint256 amount,
        bytes calldata metadata
    ) external;

    /// @notice Force update of the Global Exit Root with the latest deposit
    function updateGlobalExitRoot() external;

    /// @notice Check whether a specific bridge exit has been claimed
    function isClaimed(uint32 leafIndex, uint32 sourceBridgeNetwork)
        external view returns (bool);

    /// @notice Get the current local exit root (commits all local bridge exits)
    function getRoot() external view returns (bytes32);

    /// @notice Get the network ID of this bridge instance
    function networkID() external view returns (uint32);

    /// @notice Total deposits processed by this bridge
    function depositCount() external view returns (uint256);

    /// @notice Emitted when an asset or message is bridged out
    event BridgeEvent(
        uint8 leafType,              // 0=asset, 1=message
        uint32 originNetwork,
        address originAddress,
        uint32 destinationNetwork,
        address destinationAddress,
        uint256 amount,
        bytes metadata,
        uint32 depositCount
    );

    /// @notice Emitted when a bridged asset or message is claimed
    event ClaimEvent(
        uint256 globalIndex,
        uint32 originNetwork,
        address originAddress,
        address destinationAddress,
        uint256 amount
    );
}
