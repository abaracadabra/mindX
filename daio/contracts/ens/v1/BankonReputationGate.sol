// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IBankonReputationGate} from "./interfaces/IBankon.sol";

/// @notice External BONAFIDE / Censura-style reputation surface.
///         Any framework can implement this; this contract is the default
///         implementation backed by an admin-set score map + an optional
///         secondary oracle (BONAFIDE).
interface IExternalReputationOracle {
    function score(address agent) external view returns (uint256);
}

/// @notice External attestation registry (e.g. ERC-8004 TEE attestation).
interface IAttestationRegistry {
    function isTeeAttested(address agent) external view returns (bool);
}

/// @notice External fungible-token stake check (e.g. PYTHAI ASA bridge view).
interface IStakeView {
    function stakedOf(address agent) external view returns (uint256);
}

/// @title  BankonReputationGate
/// @notice Pluggable eligibility check for BANKON registrations.
///         Free tier requires ANY of:
///           - BONAFIDE/Censura score >= freeThreshold
///           - PYTHAI stake >= freeStakeThreshold
///           - TEE attestation (ERC-8004) flag
///         Paid tier requires only that the address is not banned.
contract BankonReputationGate is AccessControl, IBankonReputationGate {
    bytes32 public constant GOV_ROLE = keccak256("GOV_ROLE");

    /// Minimum BONAFIDE score for free registration. Default 100 per spec.
    uint256 public freeThreshold = 100;
    /// Minimum PYTHAI stake for free registration. Default 10_000 (assumes 6-dec ASA).
    uint256 public freeStakeThreshold = 10_000 * 1e6;

    /// Optional oracles. Any of zero address means: feature disabled.
    IExternalReputationOracle public bonafide;
    IAttestationRegistry public attestation;
    IStakeView public stake;

    /// Operator-set scores for dev/test or for emergencies. Takes precedence
    /// over the bonafide oracle if non-zero.
    mapping(address => uint256) private _adminScore;
    mapping(address => bool) public banned;

    event ThresholdsUpdated(uint256 freeScore, uint256 freeStake);
    event OraclesUpdated(address bonafide, address attestation, address stake);
    event AdminScoreSet(address indexed agent, uint256 score);
    event BanSet(address indexed agent, bool banned);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOV_ROLE, admin);
    }

    /* ───── Read API ──────────────────────────────────────────────── */

    function isEligibleForRegistration(address agent) external view override returns (bool) {
        if (agent == address(0)) return false;
        return !banned[agent];
    }

    function isEligibleForFree(address agent) external view override returns (bool) {
        if (agent == address(0) || banned[agent]) return false;
        if (bonafideScore(agent) >= freeThreshold) return true;
        if (address(stake) != address(0) && stake.stakedOf(agent) >= freeStakeThreshold) return true;
        if (address(attestation) != address(0) && attestation.isTeeAttested(agent)) return true;
        return false;
    }

    function bonafideScore(address agent) public view override returns (uint256) {
        uint256 admin = _adminScore[agent];
        if (admin > 0) return admin;
        if (address(bonafide) != address(0)) return bonafide.score(agent);
        return 0;
    }

    /* ───── Admin ────────────────────────────────────────────────── */

    function setThresholds(uint256 _freeScore, uint256 _freeStake)
        external onlyRole(GOV_ROLE)
    {
        freeThreshold = _freeScore;
        freeStakeThreshold = _freeStake;
        emit ThresholdsUpdated(_freeScore, _freeStake);
    }

    function setOracles(address _bonafide, address _attestation, address _stake)
        external onlyRole(GOV_ROLE)
    {
        bonafide    = IExternalReputationOracle(_bonafide);
        attestation = IAttestationRegistry(_attestation);
        stake       = IStakeView(_stake);
        emit OraclesUpdated(_bonafide, _attestation, _stake);
    }

    function setAdminScore(address agent, uint256 score) external onlyRole(GOV_ROLE) {
        _adminScore[agent] = score;
        emit AdminScoreSet(agent, score);
    }

    function setBanned(address agent, bool isBanned) external onlyRole(GOV_ROLE) {
        banned[agent] = isBanned;
        emit BanSet(agent, isBanned);
    }
}
