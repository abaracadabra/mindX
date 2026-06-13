// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title SovereignDebtRegistry
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice On-chain registry of per-country sovereign debt and currency identifiers.
 *         Provides the weighting input that the GlobalCurrencyBasket uses to assign
 *         each currency's contribution to the global debasement signal.
 *
 * @dev The thesis case for this contract: iDEBT measures debasement of "the debt system"
 *      not "the dollar". To do that, the protocol must know how much each currency
 *      contributes to the global debt stock. A country with $38 trillion of sovereign
 *      debt (United States) should weigh more in the basket than a country with
 *      $2 trillion (United Kingdom), because the protocol's job is to short the
 *      systemic debasement of the debt complex, not the bilateral move of any one pair.
 *
 *      Data sources for production deployment:
 *      - IMF Global Debt Database for total debt
 *      - IMF World Economic Outlook for nominal GDP
 *      - National central bank publications for currency conversion to USD
 *
 *      The registry is updateable by REPORTER_ROLE on a quarterly cadence matching
 *      the IMF release schedule. Updates flow through a deviation circuit breaker
 *      similar to the GDSI oracle to prevent any single bad submission from
 *      reweighting the basket dramatically.
 */
contract SovereignDebtRegistry is AccessControl, Pausable {

    bytes32 public constant REGISTRY_MANAGER_ROLE = keccak256("REGISTRY_MANAGER_ROLE");
    bytes32 public constant REPORTER_ROLE = keccak256("REPORTER_ROLE");

    uint256 public constant BPS_DENOM = 10_000;
    uint256 public constant MAX_DEVIATION_BPS = 2000;  // 20% per update

    error ZeroAddress();
    error InvalidCurrency();
    error CurrencyNotRegistered();
    error CurrencyAlreadyRegistered();
    error DeviationExceeded(uint256 newValue, uint256 oldValue);
    error ZeroValue();

    /**
     * @notice Per-country debt record. All amounts in USD-equivalent at update time
     *         to make basket weighting straightforward without per-currency cross-rates.
     */
    struct CountryRecord {
        bytes3 currencyCode;       // ISO 4217 (USD, EUR, JPY, GBP, CNY, ...)
        uint256 totalDebtUsd;      // sovereign debt in USD-equivalent, 18 decimals
        uint256 gdpUsd;            // nominal GDP in USD, 18 decimals
        uint256 debtToGdpBps;      // ratio in basis points (10000 = 100%)
        uint64 lastUpdated;        // timestamp
        bool registered;
    }

    /// @notice Currency code → record. The bytes3 key allows iteration by currency.
    mapping(bytes3 => CountryRecord) public records;

    /// @notice Iterable list of registered currency codes for basket enumeration.
    bytes3[] public currencyList;

    /// @notice Aggregate global sovereign debt in USD-equivalent, 18 decimals.
    ///         Used as the denominator for per-currency basket weights.
    uint256 public totalGlobalDebtUsd;

    event CountryRegistered(bytes3 indexed currencyCode, uint256 totalDebtUsd, uint256 gdpUsd);
    event CountryUpdated(bytes3 indexed currencyCode, uint256 totalDebtUsd, uint256 gdpUsd);
    event CountryDelisted(bytes3 indexed currencyCode);

    constructor(address admin) {
        if (admin == address(0)) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REGISTRY_MANAGER_ROLE, admin);
        _grantRole(REPORTER_ROLE, admin);
    }

    /*//////////////////////////////////////////////////////////////
                          REGISTRATION
    //////////////////////////////////////////////////////////////*/

    function registerCountry(
        bytes3 currencyCode,
        uint256 totalDebtUsd,
        uint256 gdpUsd
    ) external onlyRole(REGISTRY_MANAGER_ROLE) {
        if (currencyCode == bytes3(0)) revert InvalidCurrency();
        if (records[currencyCode].registered) revert CurrencyAlreadyRegistered();
        if (totalDebtUsd == 0 || gdpUsd == 0) revert ZeroValue();

        uint256 ratioBps = (totalDebtUsd * BPS_DENOM) / gdpUsd;
        records[currencyCode] = CountryRecord({
            currencyCode: currencyCode,
            totalDebtUsd: totalDebtUsd,
            gdpUsd: gdpUsd,
            debtToGdpBps: ratioBps,
            lastUpdated: uint64(block.timestamp),
            registered: true
        });
        currencyList.push(currencyCode);
        totalGlobalDebtUsd += totalDebtUsd;

        emit CountryRegistered(currencyCode, totalDebtUsd, gdpUsd);
    }

    function updateCountry(
        bytes3 currencyCode,
        uint256 newTotalDebtUsd,
        uint256 newGdpUsd
    ) external onlyRole(REPORTER_ROLE) {
        CountryRecord storage rec = records[currencyCode];
        if (!rec.registered) revert CurrencyNotRegistered();
        if (newTotalDebtUsd == 0 || newGdpUsd == 0) revert ZeroValue();

        // Deviation check on debt figure to prevent reporter-error blowups.
        uint256 oldDebt = rec.totalDebtUsd;
        uint256 deviation = newTotalDebtUsd > oldDebt
            ? ((newTotalDebtUsd - oldDebt) * BPS_DENOM) / oldDebt
            : ((oldDebt - newTotalDebtUsd) * BPS_DENOM) / oldDebt;
        if (deviation > MAX_DEVIATION_BPS) revert DeviationExceeded(newTotalDebtUsd, oldDebt);

        // Update global aggregate.
        totalGlobalDebtUsd = totalGlobalDebtUsd - oldDebt + newTotalDebtUsd;

        rec.totalDebtUsd = newTotalDebtUsd;
        rec.gdpUsd = newGdpUsd;
        rec.debtToGdpBps = (newTotalDebtUsd * BPS_DENOM) / newGdpUsd;
        rec.lastUpdated = uint64(block.timestamp);

        emit CountryUpdated(currencyCode, newTotalDebtUsd, newGdpUsd);
    }

    function delistCountry(bytes3 currencyCode) external onlyRole(REGISTRY_MANAGER_ROLE) {
        CountryRecord storage rec = records[currencyCode];
        if (!rec.registered) revert CurrencyNotRegistered();
        totalGlobalDebtUsd -= rec.totalDebtUsd;
        rec.registered = false;
        rec.totalDebtUsd = 0;
        // currencyList not pruned to avoid index shifts; consumers must check `registered`
        emit CountryDelisted(currencyCode);
    }

    /*//////////////////////////////////////////////////////////////
                              VIEWS
    //////////////////////////////////////////////////////////////*/

    /// @notice Weight of a currency in the global debt basket, in basis points.
    function weightBps(bytes3 currencyCode) external view returns (uint16) {
        CountryRecord memory rec = records[currencyCode];
        if (!rec.registered || totalGlobalDebtUsd == 0) return 0;
        return uint16((rec.totalDebtUsd * BPS_DENOM) / totalGlobalDebtUsd);
    }

    function getCurrencyCount() external view returns (uint256) {
        return currencyList.length;
    }

    function getActiveCurrencies() external view returns (bytes3[] memory active) {
        uint256 count;
        for (uint256 i; i < currencyList.length; i++) {
            if (records[currencyList[i]].registered) count++;
        }
        active = new bytes3[](count);
        uint256 idx;
        for (uint256 i; i < currencyList.length; i++) {
            if (records[currencyList[i]].registered) {
                active[idx++] = currencyList[i];
            }
        }
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
