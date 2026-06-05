// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { AccessControl } from "@openzeppelin/contracts/access/AccessControl.sol";
import { Pausable }      from "@openzeppelin/contracts/utils/Pausable.sol";

import { IDebtOracle }   from "../interfaces/IDebtOracle.sol";
import { DebtMath }      from "../libraries/DebtMath.sol";

/// @dev Any oracle adapter exposing `latest()` returning an Observation.
interface IAdapter {
    function latest() external view returns (IDebtOracle.Observation memory);
}

/// @title DeltaVerseDebtOracle
/// @notice Governance-aware multi-source oracle blending Chainlink, Pyth and
///         Synthetix V3 (and any other IAdapter) observations into a single
///         confidence-weighted value per Metric.
/// @dev    Storage layout:
///           _adapters[metric]  => set of adapter addresses
///           _sources[source]   => adapter address (unique key)
///           _latest[metric]    => last-observed per-adapter values
contract DeltaVerseDebtOracle is IDebtOracle, AccessControl, Pausable {
    using DebtMath for uint256;

    bytes32 public constant ORACLE_ADMIN_ROLE = keccak256("ORACLE_ADMIN_ROLE");
    bytes32 public constant KEEPER_ROLE       = keccak256("KEEPER_ROLE");

    uint256 private _freshnessWindow = 30 minutes;
    uint256 public  minConfidence    = 0.25e18;

    // metric => list of adapter addresses
    mapping(Metric => address[]) private _adapters;
    // source id => adapter
    mapping(bytes32 => address) private _sources;
    // metric => source => last observation
    mapping(Metric => mapping(bytes32 => Observation)) private _cache;

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ORACLE_ADMIN_ROLE, admin);
    }

    // -------------------------------------------------------------- //
    //                          ADMIN ACTIONS                         //
    // -------------------------------------------------------------- //

    /// @notice Associate a Metric with an adapter (identified by its sourceId).
    function attachAdapter(Metric metric, bytes32 sourceId, address adapter)
        external
        onlyRole(ORACLE_ADMIN_ROLE)
    {
        require(adapter != address(0), "zero adapter");
        _sources[sourceId] = adapter;
        _adapters[metric].push(adapter);
        emit SourceRegistered(sourceId, adapter);
    }

    function revokeSource(bytes32 sourceId) external onlyRole(ORACLE_ADMIN_ROLE) {
        delete _sources[sourceId];
        emit SourceRevoked(sourceId);
    }

    function setFreshnessWindow(uint256 windowSeconds) external onlyRole(ORACLE_ADMIN_ROLE) {
        _freshnessWindow = windowSeconds;
        emit FreshnessWindowUpdated(windowSeconds);
    }

    function setMinConfidence(uint256 floor_) external onlyRole(ORACLE_ADMIN_ROLE) {
        require(floor_ <= 1e18, "floor > WAD");
        minConfidence = floor_;
    }

    function pause() external onlyRole(ORACLE_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(ORACLE_ADMIN_ROLE) { _unpause(); }

    // -------------------------------------------------------------- //
    //                         KEEPER ACTIONS                         //
    // -------------------------------------------------------------- //

    /// @notice Poll all adapters for a metric and cache them.
    /// @dev    Intended to be called by a keeper network; cheap fallback for
    ///         chains without Chainlink automation.
    function refresh(Metric metric) external whenNotPaused {
        address[] memory adapters = _adapters[metric];
        for (uint256 i = 0; i < adapters.length; ++i) {
            Observation memory obs = IAdapter(adapters[i]).latest();
            if (obs.confidence < minConfidence) continue;
            _cache[metric][obs.source] = obs;
            emit ObservationPublished(metric, obs);
        }
    }

    // -------------------------------------------------------------- //
    //                         PUBLIC VIEWS                           //
    // -------------------------------------------------------------- //

    function latest(Metric metric) external view returns (Observation memory best) {
        address[] memory adapters = _adapters[metric];
        for (uint256 i = 0; i < adapters.length; ++i) {
            Observation memory obs = IAdapter(adapters[i]).latest();
            if (obs.timestamp > best.timestamp && obs.confidence >= minConfidence) {
                best = obs;
            }
        }
        if (best.timestamp == 0) revert StaleObservation(metric, 0, uint64(_freshnessWindow));
        uint64 age = uint64(block.timestamp) - best.timestamp;
        if (age > uint64(_freshnessWindow)) {
            revert StaleObservation(metric, age, uint64(_freshnessWindow));
        }
    }

    function blended(Metric metric) external view returns (int256) {
        address[] memory adapters = _adapters[metric];
        int256 num;
        uint256 den;
        for (uint256 i = 0; i < adapters.length; ++i) {
            Observation memory obs = IAdapter(adapters[i]).latest();
            if (obs.confidence < minConfidence) continue;
            uint64 age = uint64(block.timestamp) - obs.timestamp;
            if (age > uint64(_freshnessWindow)) continue;
            num += obs.value * int256(obs.confidence);
            den += obs.confidence;
        }
        if (den == 0) revert StaleObservation(metric, 0, uint64(_freshnessWindow));
        return num / int256(den);
    }

    function freshnessWindow() external view returns (uint256) {
        return _freshnessWindow;
    }

    function adaptersOf(Metric metric) external view returns (address[] memory) {
        return _adapters[metric];
    }

    function sourceAdapter(bytes32 id) external view returns (address) {
        return _sources[id];
    }

    // -------------------------------------------------------------- //
    //                    INTERFACE COMPATIBILITY                     //
    // -------------------------------------------------------------- //

    /// @inheritdoc IDebtOracle
    function registerSource(bytes32 source, address adapter) external onlyRole(ORACLE_ADMIN_ROLE) {
        require(adapter != address(0), "zero adapter");
        _sources[source] = adapter;
        emit SourceRegistered(source, adapter);
    }
}
