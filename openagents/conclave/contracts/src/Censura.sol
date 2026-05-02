// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ICensura} from "./interfaces/ICensura.sol";

/// @title Censura
/// @notice Minimal reputation registry for Conclave membership gating.
///         Tracks a uint8 score per address; a member is "seated" only if
///         their score ≥ Conclave's `censura_min`. The reporter API lets
///         Conclave decrement reputation when a member is slashed for leaks.
///
///         For a livenet deploy this is the placeholder; production would
///         use BONAFIDE Censura with weighted reports, decay, and recovery.
contract Censura is ICensura {
    address public admin;
    mapping(address => uint8) public _score;

    error NotAdmin();
    error ScoreOverflow();
    event ScoreSet(address indexed subject, uint8 score);
    event Reported(address indexed subject, bytes32 indexed reason);
    event AdminTransferred(address indexed from, address indexed to);

    modifier onlyAdmin() {
        if (msg.sender != admin) revert NotAdmin();
        _;
    }

    constructor(address admin_) {
        admin = admin_;
    }

    /// Set initial score (admin only). Used to seed Cabinet members.
    function setScore(address subject, uint8 newScore) external onlyAdmin {
        _score[subject] = newScore;
        emit ScoreSet(subject, newScore);
    }

    function transferAdmin(address newAdmin) external onlyAdmin {
        emit AdminTransferred(admin, newAdmin);
        admin = newAdmin;
    }

    // ─── ICensura ──────────────────────────────────────────

    function score(address subject) external view returns (uint8) {
        return _score[subject];
    }

    /// @inheritdoc ICensura
    /// @dev Reporter is permissionless — anyone can report — but the score
    ///      decrement is bounded (cannot underflow). Production would gate
    ///      this to authorized reporters with weight + decay.
    function report(address subject, bytes32 reason) external {
        uint8 cur = _score[subject];
        if (cur >= 10) {
            _score[subject] = cur - 10;
        } else {
            _score[subject] = 0;
        }
        emit Reported(subject, reason);
    }
}
