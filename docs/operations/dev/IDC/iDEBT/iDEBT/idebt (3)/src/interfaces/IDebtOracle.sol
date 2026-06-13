// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IDebtOracle
/// @notice Unified oracle interface for sovereign and global debt metrics.
/// @dev Consumed by GlobalDebtStressIndex and the iDEBT core contracts.
interface IDebtOracle {
    // -------------------------------------------------------------- //
    //                             TYPES                              //
    // -------------------------------------------------------------- //

    /// @notice Single observation from an upstream oracle.
    /// @param value       18-decimal fixed-point magnitude of the metric.
    /// @param timestamp   Seconds since unix epoch at publication.
    /// @param confidence  0..1e18 confidence weight (1e18 = absolute).
    /// @param source      keccak256 identifier of the data source.
    struct Observation {
        int256 value;
        uint64 timestamp;
        uint256 confidence;
        bytes32 source;
    }

    /// @notice Metric categories tracked by the oracle.
    enum Metric {
        SovereignDebtGDP,     // global debt / global GDP
        CDS5Y,                // weighted 5Y sovereign CDS
        YieldCurveInversion,  // weighted inversion depth
        RealRate,             // weighted real rate
        DXY,                  // dollar strength
        VIX,                  // equity volatility
        GoldRatio             // gold / reserve ratio
    }

    // -------------------------------------------------------------- //
    //                             EVENTS                             //
    // -------------------------------------------------------------- //

    event ObservationPublished(Metric indexed metric, Observation obs);
    event SourceRegistered(bytes32 indexed source, address adapter);
    event SourceRevoked(bytes32 indexed source);
    event FreshnessWindowUpdated(uint256 window);

    // -------------------------------------------------------------- //
    //                            ERRORS                              //
    // -------------------------------------------------------------- //

    error StaleObservation(Metric metric, uint64 age, uint64 maxAge);
    error UnregisteredSource(bytes32 source);
    error ConfidenceTooLow(uint256 confidence, uint256 minimum);

    // -------------------------------------------------------------- //
    //                            METHODS                             //
    // -------------------------------------------------------------- //

    /// @notice Return the latest observation for a given metric.
    function latest(Metric metric) external view returns (Observation memory);

    /// @notice Return the confidence-weighted blended value in 1e18.
    function blended(Metric metric) external view returns (int256);

    /// @notice Register a new upstream adapter under a source identifier.
    function registerSource(bytes32 source, address adapter) external;

    /// @notice Freshness window in seconds.
    function freshnessWindow() external view returns (uint256);
}
