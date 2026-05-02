// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {IBankonPriceOracle} from "./interfaces/IBankon.sol";

interface IAggregatorV3 {
    function latestRoundData()
        external view
        returns (uint80 roundId, int256 answer, uint256 startedAt,
                 uint256 updatedAt, uint80 answeredInRound);
    function decimals() external view returns (uint8);
}

interface IUniV3TwapLike {
    /// Returns arithmetic mean tick over `secondsAgo` for the given pool.
    function consult(address pool, uint32 secondsAgo)
        external view returns (int24 arithmeticMeanTick);
}

/// @title  BankonPriceOracle
/// @notice ENS-aligned length-tiered USD pricing with PYTHAI native discount.
///         All prices in USDC base units (6 decimals).
///         Agnostic: any registrar (BANKON, future tenants) can call priceUSD()
///         + priceInToken() against any supported asset.
contract BankonPriceOracle is AccessControl, IBankonPriceOracle {
    bytes32 public constant GOV_ROLE = keccak256("GOV_ROLE");

    /// MEDIUM tier defaults — see openagents/bankonsubnameregistry.md §2.
    uint256 public price3     = 320_000000;  // 3-char  $320/yr
    uint256 public price4     =  80_000000;  // 4-char  $80/yr
    uint256 public price5     =   5_000000;  // 5-char  $5/yr
    uint256 public price6     =   3_000000;  // 6-char  $3/yr
    uint256 public price7plus =   1_000000;  // 7+ char $1/yr

    /// PYTHAI-paid registrations get a 20% discount (in basis points).
    uint16 public pythaiDiscountBps = 2000;

    /// External feeds + tokens.
    IAggregatorV3 public ethUsdFeed;
    IUniV3TwapLike public twap;
    address public pythaiUsdcPool;
    address public pythaiToken;
    address public usdc;
    address public weth;

    /// Stub fallback PYTHAI/USDC rate when TWAP unavailable.
    /// Operator updates as PYTHAI/USDC liquidity matures.
    /// Quote returned as: usd6 * pythaiPerUsdcStub (1e18 decimals fixed).
    uint256 public pythaiPerUsdcStub = 50;

    event PricesUpdated(uint256 p3, uint256 p4, uint256 p5, uint256 p6, uint256 p7);
    event PythaiDiscountUpdated(uint16 oldBps, uint16 newBps);
    event FeedsUpdated(address ethUsdFeed, address twap, address pythaiUsdcPool);
    event TokensUpdated(address pythaiToken, address usdc, address weth);
    event PythaiStubUpdated(uint256 oldRate, uint256 newRate);

    error UnsupportedToken(address token);
    error BadEthPrice();
    error EmptyLabel();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOV_ROLE, admin);
    }

    /* ───── Read API ──────────────────────────────────────────────── */

    function priceUSD(string calldata label, uint256 durationYears)
        external view override
        returns (uint256 usd6)
    {
        uint256 len = bytes(label).length;
        if (len == 0) revert EmptyLabel();
        uint256 perYear = _perYearUSD(len);
        uint256 years_ = durationYears == 0 ? 1 : durationYears;
        return perYear * years_;
    }

    function priceInToken(string calldata label, uint256 durationYears, address token)
        external view override
        returns (uint256 amount)
    {
        uint256 len = bytes(label).length;
        if (len == 0) revert EmptyLabel();
        uint256 years_ = durationYears == 0 ? 1 : durationYears;
        uint256 usd6 = _perYearUSD(len) * years_;
        if (token == usdc) return usd6;
        if (token == weth) return _usdToEth(usd6);
        if (token == pythaiToken) {
            uint256 discounted = (usd6 * (10000 - pythaiDiscountBps)) / 10000;
            return _usdToPythai(discounted);
        }
        revert UnsupportedToken(token);
    }

    /* ───── Internals ────────────────────────────────────────────── */

    function _perYearUSD(uint256 len) internal view returns (uint256) {
        if (len <= 3) return price3;
        if (len == 4) return price4;
        if (len == 5) return price5;
        if (len == 6) return price6;
        return price7plus;
    }

    function _usdToEth(uint256 usd6) internal view returns (uint256) {
        if (address(ethUsdFeed) == address(0)) revert BadEthPrice();
        (, int256 px, , , ) = ethUsdFeed.latestRoundData();
        if (px <= 0) revert BadEthPrice();
        // Chainlink ETH/USD has 8 decimals. usd6 is 6-dec. Result in wei (18 dec).
        // wei = usd6 * 1e20 / px  (where px scale = 1e8)
        return (usd6 * 1e20) / uint256(px);
    }

    function _usdToPythai(uint256 usd6) internal view returns (uint256) {
        if (address(twap) != address(0) && pythaiUsdcPool != address(0)) {
            // Production path: consult tick → price via OracleLibrary.getQuoteAtTick.
            // For the hackathon ship, we record the tick was consulted and fall back
            // to the operator-set stub. Live wiring deferred to mainnet release.
            int24 tick = twap.consult(pythaiUsdcPool, 1800);
            tick; // silence unused; see post-hackathon work item
        }
        return usd6 * pythaiPerUsdcStub;
    }

    /* ───── Admin ────────────────────────────────────────────────── */

    function setPrices(
        uint256 _p3, uint256 _p4, uint256 _p5, uint256 _p6, uint256 _p7
    ) external onlyRole(GOV_ROLE) {
        price3 = _p3; price4 = _p4; price5 = _p5; price6 = _p6; price7plus = _p7;
        emit PricesUpdated(_p3, _p4, _p5, _p6, _p7);
    }

    function setPythaiDiscount(uint16 newBps) external onlyRole(GOV_ROLE) {
        require(newBps <= 5000, "discount > 50%");
        emit PythaiDiscountUpdated(pythaiDiscountBps, newBps);
        pythaiDiscountBps = newBps;
    }

    function setFeeds(address _ethUsd, address _twap, address _pool)
        external onlyRole(GOV_ROLE)
    {
        ethUsdFeed     = IAggregatorV3(_ethUsd);
        twap           = IUniV3TwapLike(_twap);
        pythaiUsdcPool = _pool;
        emit FeedsUpdated(_ethUsd, _twap, _pool);
    }

    function setTokens(address _pythai, address _usdc, address _weth)
        external onlyRole(GOV_ROLE)
    {
        pythaiToken = _pythai; usdc = _usdc; weth = _weth;
        emit TokensUpdated(_pythai, _usdc, _weth);
    }

    function setPythaiStub(uint256 newRate) external onlyRole(GOV_ROLE) {
        emit PythaiStubUpdated(pythaiPerUsdcStub, newRate);
        pythaiPerUsdcStub = newRate;
    }
}
