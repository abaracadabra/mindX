// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.20;

/**
 * @title IBridgeMessageReceiver
 * @notice Interface that destination contracts must implement to receive bridge messages
 * @dev Called by PolygonZkEVMBridgeV2.claimMessage on the destination chain
 *
 *      CRITICAL SECURITY: Implementations MUST verify:
 *        1. msg.sender == bridgeAddress
 *        2. originAddress == trustedSender
 *        3. originNetwork == trustedOriginNetwork
 *
 *      Failure to verify origin is the root cause of multiple historical bridge exploits.
 *
 * @custom:security-contact security@openbdk.org
 */
interface IBridgeMessageReceiver {
    /**
     * @notice Called by the bridge when a cross-chain message is claimed
     * @param originAddress Address that called bridgeMessage on the source chain
     * @param originNetwork AggLayer network ID of the source chain
     * @param data Arbitrary calldata sent by the origin contract
     */
    function onMessageReceived(
        address originAddress,
        uint32 originNetwork,
        bytes memory data
    ) external payable;
}
