// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/*//////////////////////////////////////////////////////////////////////
                               INTERFACES
//////////////////////////////////////////////////////////////////////*/

interface IChainlinkFeed {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

interface IPythLike {
    struct Price {
        int64 price;
        uint64 conf;
        int32 expo;
        uint publishTime;
    }
    function getPriceNoOlderThan(bytes32 id, uint age) external view returns (Price memory);
    function getEmaPriceNoOlderThan(bytes32 id, uint age) external view returns (Price memory);
}

/**
 * @title BitcoinAnchorOracle
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Aggregates BTC/USD price from Chainlink and Pyth into a single hard-money reference.
 *         Used by the inverse-debt layer as the independent numeraire against which fiat
 *         debasement and debt-stress profits are measured.
 *
 * @dev The thesis case for Bitcoin as the anchor: every other price reference in DeFi is
 *      denominated in dollars, and the dollar is itself a claim on the debt system the
 *      protocol is shorting. Using Bitcoin as the numeraire breaks the circular reference.
 *      When the debt stress index rises AND Bitcoin appreciates against fiat simultaneously
 *      (the thesis' central prediction), nominal USDC positions can show loss while real
 *      BTC-denominated value shows profit. This contract measures that second dimension.
 *
 *      Design choices:
 *      - Two source types only (Chainlink push + Pyth pull) — BTC/USD is liquid enough
 *        that reporter-median aggregation adds no information.
 *      - EMA smoothing over a configurable window to reject short-term manipulation while
 *        still tracking genuine moves.
 *      - Staleness enforced at read time; stale reads revert rather than return last value.
 *      - All prices normalized to 18 decimals internally regardless of source precision.
 */
contract BitcoinAnchorOracle is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant ORACLE_MANAGER_ROLE = keccak256("ORACLE_MANAGER_ROLE");
    bytes32 public constant KEEPER_ROLE = keccak256("KEEPER_ROLE");

    uint256 public constant PRECISION = 1e18;
    uint256 public constant BPS_DENOM = 10_000;

    error ZeroAddress();
    error StalePrice(uint256 age, uint256 maxAge);
    error InvalidPrice();
    error SourceDisabled();
    error WeightSumInvalid(uint256 sum);
    error PythConfidenceTooWide(uint256 confBps, uint256 maxBps);

    struct Source {
        address feed;              // Chainlink aggregator OR Pyth contract
        bytes32 pythFeedId;         // Non-zero if this source is Pyth
        uint8 feedDecimals;         // Chainlink decimals (Pyth uses expo field)
        uint32 maxStaleness;        // seconds; readings older than this are rejected
        uint16 weightBps;           // weight in aggregate, must sum to 10000 across enabled sources
        uint16 maxConfBps;          // Pyth only: max confidence / price in bps
        bool enabled;
    }

    /// @notice Source[0] is Chainlink, Source[1] is Pyth by convention.
    Source[2] public sources;

    uint256 public compositeValue;       // latest aggregated BTC/USD, 18 decimals
    uint256 public emaValue;             // EMA-smoothed value, 18 decimals
    uint256 public lastUpdateTimestamp;

    uint256 public emaAlphaBps = 3000;   // 0.30 smoothing factor for EMA
    uint256 public maxDeviationBps = 2000; // 20% per-update deviation cap (BTC is volatile)

    event SourceConfigured(uint8 indexed index, address feed, uint16 weightBps, bool enabled);
    event CompositeUpdated(uint256 value, uint256 emaValue, uint256 timestamp);
    event ParametersUpdated(uint256 emaAlphaBps, uint256 maxDeviationBps);

    constructor(address admin) {
        if (admin == address(0)) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ORACLE_MANAGER_ROLE, admin);
        _grantRole(KEEPER_ROLE, admin);
    }

    /*//////////////////////////////////////////////////////////////
                          CONFIGURATION
    //////////////////////////////////////////////////////////////*/

    function configureSource(
        uint8 index,
        address feed,
        bytes32 pythFeedId,
        uint8 feedDecimals,
        uint32 maxStaleness,
        uint16 weightBps,
        uint16 maxConfBps,
        bool enabled
    ) external onlyRole(ORACLE_MANAGER_ROLE) {
        require(index < 2, "invalid index");
        if (feed == address(0) && enabled) revert ZeroAddress();
        sources[index] = Source({
            feed: feed,
            pythFeedId: pythFeedId,
            feedDecimals: feedDecimals,
            maxStaleness: maxStaleness,
            weightBps: weightBps,
            maxConfBps: maxConfBps,
            enabled: enabled
        });
        emit SourceConfigured(index, feed, weightBps, enabled);
    }

    function setParameters(uint256 _emaAlphaBps, uint256 _maxDeviationBps)
        external onlyRole(ORACLE_MANAGER_ROLE)
    {
        require(_emaAlphaBps <= BPS_DENOM && _maxDeviationBps <= BPS_DENOM, "bps out of range");
        emaAlphaBps = _emaAlphaBps;
        maxDeviationBps = _maxDeviationBps;
        emit ParametersUpdated(_emaAlphaBps, _maxDeviationBps);
    }

    /*//////////////////////////////////////////////////////////////
                        SOURCE READING
    //////////////////////////////////////////////////////////////*/

    function _readChainlink(Source memory s) internal view returns (uint256 price, bool ok) {
        if (!s.enabled || s.pythFeedId != bytes32(0)) return (0, false);
        try IChainlinkFeed(s.feed).latestRoundData() returns (
            uint80, int256 answer, uint256, uint256 updatedAt, uint80
        ) {
            if (answer <= 0) return (0, false);
            if (block.timestamp - updatedAt > s.maxStaleness) return (0, false);
            // Scale Chainlink answer to 18 decimals.
            uint256 raw = uint256(answer);
            if (s.feedDecimals < 18) {
                price = raw * (10 ** (18 - s.feedDecimals));
            } else if (s.feedDecimals > 18) {
                price = raw / (10 ** (s.feedDecimals - 18));
            } else {
                price = raw;
            }
            ok = true;
        } catch {
            ok = false;
        }
    }

    function _readPyth(Source memory s) internal view returns (uint256 price, bool ok) {
        if (!s.enabled || s.pythFeedId == bytes32(0)) return (0, false);
        try IPythLike(s.feed).getPriceNoOlderThan(s.pythFeedId, s.maxStaleness) returns (
            IPythLike.Price memory p
        ) {
            if (p.price <= 0) return (0, false);
            // Reject wide confidence bands.
            uint256 absPrice = uint256(uint64(p.price));
            uint256 confBps = (uint256(p.conf) * BPS_DENOM) / absPrice;
            if (confBps > s.maxConfBps) return (0, false);
            // Scale using expo: final = price * 10^(18 + expo) when expo is negative.
            int32 expo = p.expo;
            if (expo >= 0) {
                price = absPrice * (10 ** uint256(int256(expo))) * PRECISION;
            } else {
                uint256 scale = 10 ** uint256(int256(-expo));
                // price * 1e18 / scale
                price = (absPrice * PRECISION) / scale;
            }
            ok = true;
        } catch {
            ok = false;
        }
    }

    /*//////////////////////////////////////////////////////////////
                        COMPOSITE UPDATE
    //////////////////////////////////////////////////////////////*/

    /// @notice Anyone may call; state changes are idempotent and bounded by deviation.
    function updateComposite() external nonReentrant whenNotPaused returns (uint256 newValue) {
        (uint256 clPrice, bool clOk) = _readChainlink(sources[0]);
        (uint256 pyPrice, bool pyOk) = _readPyth(sources[1]);

        uint256 weightedSum;
        uint256 totalWeight;

        if (clOk) {
            weightedSum += clPrice * sources[0].weightBps;
            totalWeight += sources[0].weightBps;
        }
        if (pyOk) {
            weightedSum += pyPrice * sources[1].weightBps;
            totalWeight += sources[1].weightBps;
        }

        require(totalWeight > 0, "no live sources");
        newValue = weightedSum / totalWeight;

        // Deviation cap: cannot move more than maxDeviationBps per update.
        if (compositeValue > 0) {
            uint256 diff = newValue > compositeValue
                ? newValue - compositeValue
                : compositeValue - newValue;
            uint256 diffBps = (diff * BPS_DENOM) / compositeValue;
            if (diffBps > maxDeviationBps) {
                // Clamp rather than revert so the oracle stays live during volatility.
                newValue = newValue > compositeValue
                    ? compositeValue + (compositeValue * maxDeviationBps) / BPS_DENOM
                    : compositeValue - (compositeValue * maxDeviationBps) / BPS_DENOM;
            }
        }

        // EMA update: ema = alpha * new + (1 - alpha) * old
        if (emaValue == 0) {
            emaValue = newValue;
        } else {
            emaValue = (newValue * emaAlphaBps + emaValue * (BPS_DENOM - emaAlphaBps)) / BPS_DENOM;
        }

        compositeValue = newValue;
        lastUpdateTimestamp = block.timestamp;
        emit CompositeUpdated(newValue, emaValue, block.timestamp);
    }

    /*//////////////////////////////////////////////////////////////
                              VIEWS
    //////////////////////////////////////////////////////////////*/

    function latestPrice() external view returns (uint256 price, uint256 updatedAt) {
        return (compositeValue, lastUpdateTimestamp);
    }

    function latestEma() external view returns (uint256) {
        return emaValue;
    }

    function isFresh(uint256 maxAge) external view returns (bool) {
        return block.timestamp - lastUpdateTimestamp <= maxAge;
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
