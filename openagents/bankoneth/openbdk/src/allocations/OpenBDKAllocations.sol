// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable2Step, Ownable} from "@openzeppelin/contracts/access/Ownable2Step.sol";

/**
 * @title  OpenBDKAllocations — multi-beneficiary token allocations with cliff + linear vesting
 * @author Professor Codephreak / openBDK
 * @notice Holds one ERC-20 and releases it to beneficiaries on a per-allocation
 *         schedule: nothing before `cliff`, linear from `start` to `start+duration`,
 *         fully vested after. Part of "sane deployment" — team/treasury/validator
 *         allocations are timelocked by construction, not by trust.
 *
 * @dev    The OWNER (a wallet that holds its own private key — typically the OVERLORD
 *         timelock after handoff) manages schedules; the contract custodies only
 *         tokens, never keys. Revocable allocations let the owner reclaim the
 *         UNVESTED remainder (already-vested tokens are always safe to the beneficiary).
 */
contract OpenBDKAllocations is Ownable2Step {
    using SafeERC20 for IERC20;

    struct Allocation {
        uint128 total;       // total tokens allocated
        uint128 released;    // tokens already released
        uint64 start;        // vesting start (unix seconds)
        uint64 cliff;        // no release before this timestamp
        uint64 duration;     // linear vest window length (seconds)
        bool revocable;
        bool revoked;
    }

    IERC20 public immutable token;
    mapping(address => Allocation) public allocations;
    uint256 public totalAllocated; // sum of (total - released) committed to beneficiaries

    event AllocationCreated(address indexed beneficiary, uint256 total, uint64 start, uint64 cliff, uint64 duration, bool revocable);
    event Released(address indexed beneficiary, uint256 amount);
    event Revoked(address indexed beneficiary, uint256 refundedUnvested);

    error AllocationExists();
    error NoAllocation();
    error NotRevocable();
    error AlreadyRevoked();
    error BadSchedule();
    error InsufficientUnallocatedBalance();

    constructor(address tokenAddr, address owner_) Ownable(owner_) {
        token = IERC20(tokenAddr);
    }

    /// @notice Create a vesting allocation. Tokens must already be funded to this contract.
    function createAllocation(
        address beneficiary,
        uint128 total,
        uint64 start,
        uint64 cliff,
        uint64 duration,
        bool revocable
    ) external onlyOwner {
        if (allocations[beneficiary].total != 0) revert AllocationExists();
        if (total == 0 || duration == 0 || cliff < start) revert BadSchedule();
        // must be backed by un-committed balance held here
        uint256 free = token.balanceOf(address(this)) - totalAllocated;
        if (free < total) revert InsufficientUnallocatedBalance();

        allocations[beneficiary] = Allocation({
            total: total, released: 0, start: start, cliff: cliff,
            duration: duration, revocable: revocable, revoked: false
        });
        totalAllocated += total;
        emit AllocationCreated(beneficiary, total, start, cliff, duration, revocable);
    }

    /// @notice Vested-but-unreleased amount for a beneficiary at the current time.
    function releasable(address beneficiary) public view returns (uint256) {
        Allocation storage a = allocations[beneficiary];
        return _vested(a, uint64(block.timestamp)) - a.released;
    }

    function _vested(Allocation storage a, uint64 ts) internal view returns (uint256) {
        if (a.total == 0) return 0;
        // A revoked allocation is frozen: `total` was shrunk to the vested-so-far
        // amount, which stays fully claimable (no further linear vesting applies).
        if (a.revoked) return a.total;
        if (ts < a.cliff) return 0;
        if (ts >= a.start + a.duration) return a.total;
        // linear from start..start+duration (cliff only delays the first claim)
        return (uint256(a.total) * (ts - a.start)) / a.duration;
    }

    /// @notice Release vested tokens to the beneficiary (anyone may trigger; funds go to beneficiary).
    function release(address beneficiary) external {
        Allocation storage a = allocations[beneficiary];
        if (a.total == 0) revert NoAllocation();
        uint256 amount = _vested(a, uint64(block.timestamp)) - a.released;
        if (amount == 0) return;
        a.released += uint128(amount);
        totalAllocated -= amount;
        token.safeTransfer(beneficiary, amount);
        emit Released(beneficiary, amount);
    }

    /// @notice Revoke a revocable allocation; vested stays claimable, unvested returns to owner.
    function revoke(address beneficiary) external onlyOwner {
        Allocation storage a = allocations[beneficiary];
        if (a.total == 0) revert NoAllocation();
        if (!a.revocable) revert NotRevocable();
        if (a.revoked) revert AlreadyRevoked();

        uint256 vested = _vested(a, uint64(block.timestamp));
        uint256 unvested = a.total - vested; // not yet earned
        a.revoked = true;
        // shrink the allocation to the vested portion (still claimable via release())
        a.total = uint128(vested);
        totalAllocated -= unvested;
        if (unvested > 0) token.safeTransfer(owner(), unvested);
        emit Revoked(beneficiary, unvested);
    }
}
