// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Shared custom errors for DAIO governance + treasury contracts.
/// @dev Imported by any contract that uses `.call{value:}()` for ETH-out
///      paths. Centralizing avoids redeclaring the same error in each file.
///      Custom errors are gas-cheaper than `require(..., "string")` and
///      preserve the failed receiver + amount for off-chain accounting.

/// @notice An ETH transfer via `.call{value:}()` reverted.
/// @param receiver The intended recipient of the failed transfer.
/// @param amount   The wei amount that did not land.
error NativeTransferFailed(address receiver, uint256 amount);
