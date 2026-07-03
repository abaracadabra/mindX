// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

interface IChainlinkFeed {
    function latestRoundData() external view returns (
        uint80, int256, uint256, uint256, uint80
    );
    function decimals() external view returns (uint8);
}

interface ISovereignDebtRegistry {
    function weightBps(bytes3 currencyCode) external view returns (uint16);
    function getActiveCurrencies() external view returns (bytes3[] memory);
}

interface IBitcoinAnchorOracle {
    function latestPrice() external view returns (uint256, uint256);
}

/**
 * @title GlobalCurrencyBasket
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Aggregates multiple fiat-vs-BTC price ratios into a single weighted index of
 *         global fiat strength relative to Bitcoin. The weights come from the
 *         SovereignDebtRegistry, which reflects each currency's contribution to global
 *         sovereign debt. The result is a measurement that captures debasement of the
 *         debt complex as a whole, not just bilateral movement of any single pair.
 *
 * @dev Architectural rationale:
 *
 *      The first-generation DebasementIndex used a single BTC/USD ratio. That measurement
 *      collapses a multi-dimensional global phenomenon into a US-centric scalar. The
 *      problem is concrete: in 2025 the US dollar weakened against major trading partners
 *      while CPI was positive — the dollar was losing purchasing power against goods AND
 *      against other fiat. A protocol that only watches BTC/USD misses the systemic
 *      character of debasement.
 *
 *      This contract fixes that. For each registered currency C with weight w_C in the
 *      global debt basket, it reads two prices: BTC/USD from the BitcoinAnchorOracle
 *      (the universal reference) and C/USD from a per-currency Chainlink feed. From
 *      these it computes BTC/C = (BTC/USD) / (C/USD), the price of one BTC in units of
 *      currency C. The basket-level "fiat strength" measurement is the weighted geometric
 *      mean (approximated linearly here for gas) of all (BTC/C_baseline / BTC/C_current)
 *      ratios, which rises when fiat strengthens against BTC and falls when fiat weakens.
 *
 *      Currencies supported in reference deployment with example weights:
 *        USD (United States)  — ~34%   $38.3T sovereign debt
 *        EUR (Eurozone)       — ~19%   $21T sovereign debt
 *        JPY (Japan)          — ~9%    $9.8T sovereign debt
 *        CNY (China)          — ~17%   $18.7T sovereign debt
 *        GBP (United Kingdom) — ~3%    $3.5T sovereign debt
 *        CHF (Switzerland)    — ~1%    $0.7T sovereign debt
 *        CAD, AUD, INR, BRL   — ~1-3% each
 *      Total covered: ~85-90% of global sovereign debt; remainder absorbed
 *      pro-rata by re-normalizing weights of registered currencies.
 *
 *      The weighted measurement preserves the property that when BTC rises against
 *      every fiat simultaneously (the systemic debasement scenario), the basket index
 *      moves significantly. When BTC rises only against one fiat while others
 *      strengthen, the basket index moves much less — correctly reflecting that the
 *      thesis is about systemic debasement, not bilateral noise.
 */
contract GlobalCurrencyBasket is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant BASKET_MANAGER_ROLE = keccak256("BASKET_MANAGER_ROLE");

    uint256 public constant PRECISION = 1e18;
    uint256 public constant BPS_DENOM = 10_000;

    error ZeroAddress();
    error InvalidCurrency();
    error CurrencyNotConfigured();
    error CurrencyAlreadyConfigured();
    error AllSourcesStale();
    error NotInitialized();
    error AlreadyInitialized();

    struct CurrencyConfig {
        bytes3 code;                  // ISO 4217 currency code
        address fxFeed;               // Chainlink C/USD aggregator
        uint8 fxDecimals;             // Chainlink decimals (typically 8)
        uint32 maxStaleness;          // seconds before excluded from basket
        uint256 baselineFxPerUsd;     // C per USD at baseline (1e18)
        uint256 baselineBtcPerC;      // BTC per unit C at baseline (1e18)
        bool enabled;
    }

    /// @notice currency code → config
    mapping(bytes3 => CurrencyConfig) public configs;

    ISovereignDebtRegistry public immutable registry;
    IBitcoinAnchorOracle public immutable btcOracle;

    uint256 public baselineBtcUsd;
    uint256 public baselineTimestamp;
    bool public initialized;

    event CurrencyConfigured(bytes3 indexed code, address feed);
    event BaselineLocked(uint256 btcUsd, uint256 timestamp);

    constructor(address admin, address _registry, address _btcOracle) {
        if (admin == address(0) || _registry == address(0) || _btcOracle == address(0))
            revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(BASKET_MANAGER_ROLE, admin);
        registry = ISovereignDebtRegistry(_registry);
        btcOracle = IBitcoinAnchorOracle(_btcOracle);
    }

    /*//////////////////////////////////////////////////////////////
                          CONFIGURATION
    //////////////////////////////////////////////////////////////*/

    function configureCurrency(
        bytes3 code,
        address fxFeed,
        uint8 fxDecimals,
        uint32 maxStaleness
    ) external onlyRole(BASKET_MANAGER_ROLE) {
        if (code == bytes3(0)) revert InvalidCurrency();
        if (fxFeed == address(0)) revert ZeroAddress();
        if (configs[code].enabled) revert CurrencyAlreadyConfigured();

        configs[code] = CurrencyConfig({
            code: code,
            fxFeed: fxFeed,
            fxDecimals: fxDecimals,
            maxStaleness: maxStaleness,
            baselineFxPerUsd: 0,
            baselineBtcPerC: 0,
            enabled: true
        });

        emit CurrencyConfigured(code, fxFeed);
    }

    /// @notice Lock baseline values for all configured currencies. Single-shot.
    function initializeBaseline() external onlyRole(BASKET_MANAGER_ROLE) {
        if (initialized) revert AlreadyInitialized();

        (uint256 btcUsd, ) = btcOracle.latestPrice();
        require(btcUsd > 0, "btc oracle empty");
        baselineBtcUsd = btcUsd;

        bytes3[] memory codes = registry.getActiveCurrencies();
        for (uint256 i; i < codes.length; i++) {
            CurrencyConfig storage cfg = configs[codes[i]];
            if (!cfg.enabled) continue;
            uint256 fxPerUsd = _readFxPerUsd(cfg);
            require(fxPerUsd > 0, "fx feed not ready");
            cfg.baselineFxPerUsd = fxPerUsd;
            // BTC priced in C: btcPerC = btcUsd / (1/fxPerUsd) = btcUsd * fxPerUsd / 1e18
            // (giving us how much C one BTC costs at baseline)
            cfg.baselineBtcPerC = (btcUsd * fxPerUsd) / PRECISION;
        }

        initialized = true;
        baselineTimestamp = block.timestamp;
        emit BaselineLocked(btcUsd, block.timestamp);
    }

    /*//////////////////////////////////////////////////////////////
                          PRICE READING
    //////////////////////////////////////////////////////////////*/

    /// @dev Returns C/USD ratio in 1e18: how many units of currency C per 1 USD.
    ///      Chainlink fx feeds are typically denominated as USD/C (e.g. USD/JPY = 150),
    ///      so this normalizes the convention.
    function _readFxPerUsd(CurrencyConfig storage cfg) internal view returns (uint256) {
        try IChainlinkFeed(cfg.fxFeed).latestRoundData() returns (
            uint80, int256 answer, uint256, uint256 updatedAt, uint80
        ) {
            if (answer <= 0) return 0;
            if (block.timestamp - updatedAt > cfg.maxStaleness) return 0;
            // Chainlink convention varies. We assume the feed returns "C per USD"
            // directly. For inverted feeds the BASKET_MANAGER deploys a small
            // wrapper that flips the value before exposing it.
            uint256 raw = uint256(answer);
            if (cfg.fxDecimals < 18) {
                return raw * (10 ** (18 - cfg.fxDecimals));
            } else if (cfg.fxDecimals > 18) {
                return raw / (10 ** (cfg.fxDecimals - 18));
            }
            return raw;
        } catch {
            return 0;
        }
    }

    /*//////////////////////////////////////////////////////////////
                       BASKET MEASUREMENT
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Computes the weighted "fiat-vs-BTC" basket index, scaled to 1e18 at baseline.
     *         Index > 1e18 means fiat (basket-weighted) has STRENGTHENED against BTC since
     *         baseline. Index < 1e18 means fiat has WEAKENED against BTC since baseline.
     *         For the debasement index, we care about the inverse: when fiat weakens, the
     *         debasement signal rises.
     */
    function fiatStrengthIndex() public view returns (uint256 index) {
        if (!initialized) revert NotInitialized();
        (uint256 btcUsd, ) = btcOracle.latestPrice();
        require(btcUsd > 0, "btc stale");

        bytes3[] memory codes = registry.getActiveCurrencies();
        uint256 weightedSum;
        uint256 totalWeight;

        for (uint256 i; i < codes.length; i++) {
            CurrencyConfig storage cfg = configs[codes[i]];
            if (!cfg.enabled || cfg.baselineBtcPerC == 0) continue;

            uint256 fxPerUsd = _readFxPerUsd(cfg);
            if (fxPerUsd == 0) continue;  // skip stale source

            uint256 currentBtcPerC = (btcUsd * fxPerUsd) / PRECISION;
            // Strength ratio for this currency:
            // ratio > 1e18 means fewer C per BTC now than at baseline → fiat strengthened
            uint256 strengthRatio = (cfg.baselineBtcPerC * PRECISION) / currentBtcPerC;

            uint16 w = registry.weightBps(cfg.code);
            if (w == 0) continue;

            weightedSum += strengthRatio * w;
            totalWeight += w;
        }

        if (totalWeight == 0) revert AllSourcesStale();
        index = weightedSum / totalWeight;
    }

    /**
     * @notice The complement: how much has fiat collectively WEAKENED against BTC.
     *         This is what the DebasementIndex consumes. Returns 1e18 at baseline,
     *         > 1e18 when fiat is debasing, < 1e18 when fiat is strengthening.
     */
    function fiatDebasementIndex() public view returns (uint256) {
        uint256 strength = fiatStrengthIndex();
        if (strength == 0) return type(uint256).max;
        // debasement = 1/strength * BASE = (BASE * BASE) / strength
        return (PRECISION * PRECISION) / strength;
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
