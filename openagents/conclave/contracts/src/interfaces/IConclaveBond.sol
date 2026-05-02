// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IConclaveBond
/// @notice Honor-stake module. Members lock a bond before being seated;
///         leaks are slashed by `Conclave.sol`.
interface IConclaveBond {
    /// @return amount the bond `member` has locked for `conclave_id`.
    function bondOf(bytes32 conclave_id, address member)
        external
        view
        returns (uint256 amount);

    /// @notice Lock a bond for a conclave. Pulls funds from msg.sender.
    function postBond(bytes32 conclave_id, uint256 amount) external payable;

    /// @notice Release a bond after the conclave's slash window expires.
    function releaseBond(bytes32 conclave_id) external;

    /// @notice Slash a member's bond. Only callable by the Conclave contract.
    /// @return amount the amount slashed (full bond at v0.1).
    function slash(bytes32 conclave_id, address member)
        external
        returns (uint256 amount);
}
