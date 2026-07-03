// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "forge-std/console2.sol";

import "../src/SovereignDebtRegistry.sol";
import "../src/GlobalCurrencyBasket.sol";
import "../src/DebasementIndexV2.sol";
import "../src/BitcoinAnchorOracle.sol";

/*//////////////////////////////////////////////////////////////
                              MOCKS
//////////////////////////////////////////////////////////////*/

contract MockChainlinkFx {
    int256 public price;
    uint256 public updatedAt;
    uint8 public _decimals;
    constructor(int256 p, uint8 d) { price = p; updatedAt = block.timestamp; _decimals = d; }
    function setPrice(int256 p) external { price = p; updatedAt = block.timestamp; }
    function setStale(uint256 s) external { updatedAt = block.timestamp - s; }
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80) {
        return (1, price, updatedAt, updatedAt, 1);
    }
    function decimals() external view returns (uint8) { return _decimals; }
}

contract MockBtcOracle {
    uint256 public _price;
    uint256 public _ts;
    function set(uint256 p) external { _price = p; _ts = block.timestamp; }
    function latestPrice() external view returns (uint256, uint256) { return (_price, _ts); }
    function latestEma() external view returns (uint256) { return _price; }
    function isFresh(uint256) external pure returns (bool) { return true; }
}

contract MockGdsi {
    uint256 public _p;
    uint256 public _ts;
    function set(uint256 p) external { _p = p; _ts = block.timestamp; }
    function latestPrice() external view returns (uint256, uint256) { return (_p, _ts); }
    function stressLevel() external pure returns (uint8) { return 1; }
}

contract GlobalCurrencyBasketTest is Test {

    SovereignDebtRegistry registry;
    GlobalCurrencyBasket basket;
    DebasementIndexV2 index;
    MockBtcOracle btc;
    MockGdsi gdsi;

    MockChainlinkFx eurFeed;  // EUR per USD (~0.92 at baseline)
    MockChainlinkFx jpyFeed;  // JPY per USD (~150)
    MockChainlinkFx gbpFeed;  // GBP per USD (~0.79)
    MockChainlinkFx cnyFeed;  // CNY per USD (~7.25)
    MockChainlinkFx usdFeed;  // USD per USD (always 1.0)

    address admin = address(0xA);

    bytes3 constant USD = bytes3("USD");
    bytes3 constant EUR = bytes3("EUR");
    bytes3 constant JPY = bytes3("JPY");
    bytes3 constant GBP = bytes3("GBP");
    bytes3 constant CNY = bytes3("CNY");

    function setUp() public {
        vm.startPrank(admin);

        registry = new SovereignDebtRegistry(admin);

        // Realistic 2025 sovereign debt figures in USD-equivalent (18 dec).
        registry.registerCountry(USD, 38_300_000_000_000e18, 28_000_000_000_000e18);  // US
        registry.registerCountry(EUR, 21_000_000_000_000e18, 17_500_000_000_000e18);  // EZ
        registry.registerCountry(JPY,  9_800_000_000_000e18,  4_400_000_000_000e18);  // JP
        registry.registerCountry(GBP,  3_500_000_000_000e18,  3_400_000_000_000e18);  // UK
        registry.registerCountry(CNY, 18_700_000_000_000e18, 18_000_000_000_000e18);  // CN

        btc = new MockBtcOracle();
        btc.set(60_000e18);
        gdsi = new MockGdsi();
        gdsi.set(1000e18);

        basket = new GlobalCurrencyBasket(admin, address(registry), address(btc));

        // FX feeds — Chainlink convention: the value is "C per USD" with 8 decimals.
        usdFeed = new MockChainlinkFx(1e8, 8);
        eurFeed = new MockChainlinkFx(int256(92e6), 8);    // 0.92 EUR/USD
        jpyFeed = new MockChainlinkFx(int256(150e8), 8);   // 150 JPY/USD
        gbpFeed = new MockChainlinkFx(int256(79e6), 8);    // 0.79 GBP/USD
        cnyFeed = new MockChainlinkFx(int256(7_25e6), 8);  // 7.25 CNY/USD

        basket.configureCurrency(USD, address(usdFeed), 8, 2 hours);
        basket.configureCurrency(EUR, address(eurFeed), 8, 2 hours);
        basket.configureCurrency(JPY, address(jpyFeed), 8, 2 hours);
        basket.configureCurrency(GBP, address(gbpFeed), 8, 2 hours);
        basket.configureCurrency(CNY, address(cnyFeed), 8, 2 hours);

        basket.initializeBaseline();

        index = new DebasementIndexV2(admin, address(gdsi), address(basket), address(btc));
        index.initializeBaseline();

        vm.stopPrank();
    }

    /*//////////////////////////////////////////////////////////////
                        REGISTRY BASICS
    //////////////////////////////////////////////////////////////*/

    function test_01_RegistryAggregatesGlobalDebt() public view {
        // 38.3T + 21T + 9.8T + 3.5T + 18.7T = 91.3T
        assertEq(registry.totalGlobalDebtUsd(), 91_300_000_000_000e18);
    }

    function test_02_WeightsSumProportionally() public view {
        // US weight: 38.3/91.3 ≈ 41.95%
        uint16 usWeight = registry.weightBps(USD);
        assertApproxEqAbs(uint256(usWeight), 4195, 5);

        // JP weight: 9.8/91.3 ≈ 10.73%
        uint16 jpWeight = registry.weightBps(JPY);
        assertApproxEqAbs(uint256(jpWeight), 1073, 5);
    }

    function test_03_UpdateCountryWithinDeviation() public {
        vm.prank(admin);
        registry.updateCountry(USD, 40_000_000_000_000e18, 28_500_000_000_000e18);

        (, uint256 newDebt, , , , ) = registry.records(USD);
        assertEq(newDebt, 40_000_000_000_000e18);
    }

    function test_04_UpdateCountryRevertsExcessiveDeviation() public {
        vm.prank(admin);
        vm.expectRevert();
        registry.updateCountry(USD, 50_000_000_000_000e18, 28_500_000_000_000e18);  // +30%
    }

    /*//////////////////////////////////////////////////////////////
                       BASKET MEASUREMENT
    //////////////////////////////////////////////////////////////*/

    function test_05_BasketAtBaselineEqualsOne() public view {
        uint256 strength = basket.fiatStrengthIndex();
        // At baseline all currencies and BTC are unchanged → strength = 1e18.
        assertApproxEqRel(strength, 1e18, 0.001e18);
        uint256 debasement = basket.fiatDebasementIndex();
        assertApproxEqRel(debasement, 1e18, 0.001e18);
    }

    function test_06_BtcRallyMakesAllFiatWeaken() public {
        // BTC doubles. Every fiat in the basket loses half its value vs BTC.
        // Basket debasement should rise to ~2.0.
        btc.set(120_000e18);

        uint256 deb = basket.fiatDebasementIndex();
        assertApproxEqRel(deb, 2e18, 0.01e18);
    }

    function test_07_OnlyOneFiatWeakensPartialBasketMove() public {
        // JPY weakens 50% (yen crisis). Other fiat unchanged. BTC unchanged.
        jpyFeed.setPrice(int256(225e8));  // from 150 to 225

        uint256 deb = basket.fiatDebasementIndex();
        // JPY weight ≈ 10.7%, weakened 50% → basket-wide debasement ≈ 5.4%
        assertGt(deb, 1.04e18);
        assertLt(deb, 1.07e18);
    }

    function test_08_StaleFeedExcludedNotReverted() public {
        // GBP feed goes stale. Basket should re-weight across remaining 4 currencies.
        gbpFeed.setStale(3 hours);

        // BTC doubles to provoke debasement signal.
        btc.set(120_000e18);
        uint256 deb = basket.fiatDebasementIndex();

        // Should still report ~2x debasement using the remaining currencies.
        assertApproxEqRel(deb, 2e18, 0.02e18);
    }

    function test_09_AllFeedsStaleReverts() public {
        eurFeed.setStale(3 hours);
        jpyFeed.setStale(3 hours);
        gbpFeed.setStale(3 hours);
        cnyFeed.setStale(3 hours);
        usdFeed.setStale(3 hours);

        vm.expectRevert();
        basket.fiatDebasementIndex();
    }

    /*//////////////////////////////////////////////////////////////
                    DEBASEMENT INDEX V2 INTEGRATION
    //////////////////////////////////////////////////////////////*/

    function test_10_V2IndexAtBaseline() public view {
        uint256 idx = index.currentIndex();
        assertApproxEqRel(idx, 1e18, 0.001e18);
    }

    function test_11_V2IndexRespondsToBtcAndGdsi() public {
        // BTC doubles AND GDSI rises 50%.
        btc.set(120_000e18);
        gdsi.set(1500e18);

        uint256 idx = index.currentIndex();
        // gdsi contribution: 0.3 * 1.5 = 0.45
        // basket contribution: 0.7 * 2.0 = 1.40
        // total: 1.85
        assertApproxEqRel(idx, 1.85e18, 0.02e18);
    }

    function test_12_IndexComponentsDecomposition() public {
        btc.set(120_000e18);
        gdsi.set(1200e18);

        (uint256 gdsiC, uint256 basketC, uint256 total) = index.indexComponents();
        // gdsi: 0.3 * 1.2 = 0.36
        // basket: 0.7 * 2.0 = 1.40
        // total: 1.76
        assertApproxEqRel(gdsiC, 0.36e18, 0.02e18);
        assertApproxEqRel(basketC, 1.40e18, 0.02e18);
        assertApproxEqRel(total, 1.76e18, 0.02e18);
    }

    function test_13_DivergentFiatScenario() public {
        // Stress test: USD strengthens (DXY rally) while JPY collapses.
        // Net basket-wide effect should be modest because the moves partially cancel.
        usdFeed.setPrice(int256(105e6));  // USD 5% stronger (notional)
        jpyFeed.setPrice(int256(180e8));  // JPY 20% weaker
        // BTC unchanged.

        uint256 deb = basket.fiatDebasementIndex();
        // Move depends on signs: when USD strengthens against itself it's a nop in our
        // model because we compare to the basket. JPY weakening alone contributes
        // ~10.7% weight × 20% move = ~2% basket debasement.
        assertGt(deb, 1.0e18);
        assertLt(deb, 1.03e18);
    }
}
