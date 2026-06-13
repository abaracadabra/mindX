// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "forge-std/console2.sol";

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

import "../src/BitcoinAnchorOracle.sol";
import "../src/DebasementIndex.sol";
import "../src/InverseDebtToken.sol";
import "../src/BitcoinProfitRecognizer.sol";

/*//////////////////////////////////////////////////////////////////////
                           MOCKS
//////////////////////////////////////////////////////////////////////*/

contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "mUSDC") {}
    function decimals() public pure override returns (uint8) { return 6; }
    function mint(address to, uint256 amt) external { _mint(to, amt); }
}

contract MockChainlinkBtc {
    int256 public price;
    uint256 public updatedAt;
    uint8 public _decimals = 8;
    constructor(int256 p) { price = p; updatedAt = block.timestamp; }
    function setPrice(int256 p) external { price = p; updatedAt = block.timestamp; }
    function setStale(uint256 s) external { updatedAt = block.timestamp - s; }
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80) {
        return (1, price, updatedAt, updatedAt, 1);
    }
    function decimals() external view returns (uint8) { return _decimals; }
}

contract MockPyth {
    struct Price { int64 price; uint64 conf; int32 expo; uint publishTime; }
    mapping(bytes32 => Price) public prices;
    function setPrice(bytes32 id, int64 p, uint64 c, int32 e) external {
        prices[id] = Price(p, c, e, block.timestamp);
    }
    function getPriceNoOlderThan(bytes32 id, uint) external view returns (Price memory) {
        return prices[id];
    }
    function getEmaPriceNoOlderThan(bytes32 id, uint) external view returns (Price memory) {
        return prices[id];
    }
}

contract MockGdsiOracle {
    uint256 public _price;
    uint256 public _ts;
    uint8 public _level;
    function set(uint256 p, uint8 l) external { _price = p; _level = l; _ts = block.timestamp; }
    function latestPrice() external view returns (uint256, uint256) { return (_price, _ts); }
    function stressLevel() external view returns (uint8) { return _level; }
}

/*//////////////////////////////////////////////////////////////////////
                       INVERSE DEBT INTEGRATION
//////////////////////////////////////////////////////////////////////*/

contract InverseDebtTest is Test {

    MockUSDC usdc;
    MockChainlinkBtc clBtc;
    MockPyth pyth;
    MockGdsiOracle gdsi;
    BitcoinAnchorOracle btcOracle;
    DebasementIndex debasement;
    InverseDebtToken idebt;

    address admin = address(0xA);
    address alice = address(0xB);
    address bob   = address(0xC);

    bytes32 constant BTC_PYTH_ID = keccak256("BTC/USD");

    function setUp() public {
        vm.startPrank(admin);

        usdc = new MockUSDC();
        clBtc = new MockChainlinkBtc(60_000e8);   // $60k BTC
        pyth = new MockPyth();
        pyth.setPrice(BTC_PYTH_ID, 60_000e8, 30e8, -8);

        gdsi = new MockGdsiOracle();
        gdsi.set(1000e18, 1);

        btcOracle = new BitcoinAnchorOracle(admin);
        btcOracle.configureSource(0, address(clBtc), bytes32(0), 8, 2 hours, 5000, 0, true);
        btcOracle.configureSource(1, address(pyth), BTC_PYTH_ID, 0, 2 hours, 5000, 200, true);
        btcOracle.updateComposite();

        debasement = new DebasementIndex(admin, address(gdsi), address(btcOracle));
        debasement.initializeBaseline();

        idebt = new InverseDebtToken(admin, address(usdc), address(debasement));

        vm.stopPrank();

        usdc.mint(alice, 1_000_000e6);
        usdc.mint(bob, 1_000_000e6);
    }

    /*//////////////////////////////////////////////////////////////
                    ORACLE AND INDEX BASICS
    //////////////////////////////////////////////////////////////*/

    function test_01_OracleAggregatesBtcPrice() public view {
        (uint256 p, ) = btcOracle.latestPrice();
        assertApproxEqRel(p, 60_000e18, 0.01e18);
    }

    function test_02_DebasementIndexAtBaseline() public view {
        uint256 idx = debasement.currentIndex();
        assertApproxEqRel(idx, 1e18, 0.01e18);
    }

    function test_03_BtcRallyLiftsDebasementIndex() public {
        // BTC doubles: should lift index by ~60% (BTC weight) * 100% = 60%
        clBtc.setPrice(120_000e8);
        pyth.setPrice(BTC_PYTH_ID, 120_000e8, 60e8, -8);
        btcOracle.updateComposite();

        uint256 idx = debasement.currentIndex();
        // gdsiRatio = 1.0, btcRatio = 2.0 -> 0.4*1 + 0.6*2 = 1.6
        assertApproxEqRel(idx, 1.6e18, 0.02e18);
    }

    function test_04_GdsiRiseLiftsDebasementIndex() public {
        // GDSI rises 50%, BTC flat: index should rise ~20% (0.4 weight * 50%)
        gdsi.set(1500e18, 3);
        uint256 idx = debasement.currentIndex();
        assertApproxEqRel(idx, 1.2e18, 0.01e18);
    }

    /*//////////////////////////////////////////////////////////////
                  MINT / BURN ROUND TRIP
    //////////////////////////////////////////////////////////////*/

    function test_05_MintAtBaseline() public {
        vm.startPrank(alice);
        usdc.approve(address(idebt), 10_000e6);
        uint256 minted = idebt.mint(10_000e6, 0);
        vm.stopPrank();

        assertGt(minted, 0);
        // Net after 30bps fee: 9970 USDC -> 9970e18 iDEBT at baseline index.
        assertApproxEqRel(minted, 9970e18, 0.001e18);
    }

    function test_06_BurnAtBaselineReturnsUsdcLessFees() public {
        vm.startPrank(alice);
        usdc.approve(address(idebt), 10_000e6);
        uint256 minted = idebt.mint(10_000e6, 0);
        uint256 balBefore = usdc.balanceOf(alice);
        uint256 out = idebt.burn(minted, 0);
        uint256 balAfter = usdc.balanceOf(alice);
        vm.stopPrank();

        assertEq(balAfter - balBefore, out);
        // Round-trip loss: ~60bps total fees.
        assertLt(out, 10_000e6);
        assertGt(out, 9900e6);
    }

    function test_07_ProfitFromLoss_BtcRallyPayout() public {
        // Alice mints 10,000 USDC of iDEBT at baseline.
        vm.startPrank(alice);
        usdc.approve(address(idebt), 10_000e6);
        uint256 minted = idebt.mint(10_000e6, 0);
        vm.stopPrank();

        // BTC rallies 50% while GDSI stays flat -> index rises ~30%.
        clBtc.setPrice(90_000e8);
        pyth.setPrice(BTC_PYTH_ID, 90_000e8, 45e8, -8);
        btcOracle.updateComposite();

        // Alice burns. She should receive more USDC than she deposited.
        // Fund the contract's reserve so the payout has backing.
        usdc.mint(address(idebt), 50_000e6);

        vm.startPrank(alice);
        uint256 balBefore = usdc.balanceOf(alice);
        uint256 out = idebt.burn(minted, 0);
        uint256 balAfter = usdc.balanceOf(alice);
        vm.stopPrank();

        assertEq(balAfter - balBefore, out);
        // Expected: minted * 1.3 / 1e18 / 1e12 minus 30bps burn fee.
        // Roughly ~12,900 USDC.
        assertGt(out, 12_500e6);
        assertLt(out, 13_000e6);

        console2.log("Mint:", 10_000e6);
        console2.log("Burn:", out);
        console2.log("Nominal USDC gain:", out - 10_000e6);
    }

    function test_08_LossFromBtcCrash() public {
        vm.startPrank(alice);
        usdc.approve(address(idebt), 10_000e6);
        uint256 minted = idebt.mint(10_000e6, 0);
        vm.stopPrank();

        // BTC crashes 30% -> index falls ~18%.
        clBtc.setPrice(42_000e8);
        pyth.setPrice(BTC_PYTH_ID, 42_000e8, 21e8, -8);
        btcOracle.updateComposite();

        vm.prank(alice);
        uint256 out = idebt.burn(minted, 0);

        // User realizes a loss in USDC terms — this is correct behavior.
        assertLt(out, 10_000e6);
        assertGt(out, 8_000e6);
    }

    /*//////////////////////////////////////////////////////////////
                 SOLVENCY HAIRCUT WHEN UNDER-RESERVED
    //////////////////////////////////////////////////////////////*/

    function test_09_ProportionalHaircutOnInsufficientReserve() public {
        // Alice mints a modest position.
        vm.startPrank(alice);
        usdc.approve(address(idebt), 1000e6);
        uint256 minted = idebt.mint(1000e6, 0);
        vm.stopPrank();

        // Massive BTC rally: index should 3x.
        clBtc.setPrice(240_000e8);
        pyth.setPrice(BTC_PYTH_ID, 240_000e8, 120e8, -8);
        btcOracle.updateComposite();
        btcOracle.updateComposite();  // second update to let the 20% clamp catch up
        btcOracle.updateComposite();

        // Without reserve top-up, the contract cannot pay 3x nominal.
        vm.prank(alice);
        uint256 out = idebt.burn(minted, 0);

        // She gets what is available rather than a revert.
        assertGt(out, 0);
        assertLe(out, 1000e6); // clamped to contract's own balance
    }

    function test_10_BtcEquivalentReporting() public {
        // 60k USDC should equal ~1 BTC at $60k BTC.
        uint256 sats = debasement.btcEquivalent(60_000e6);
        // 1 BTC = 1e8 satoshis.
        assertApproxEqRel(sats, 1e8, 0.01e18);
    }

    function test_11_CollateralizationRatio() public {
        assertEq(idebt.collateralizationRatioBps(), type(uint256).max);

        vm.startPrank(alice);
        usdc.approve(address(idebt), 10_000e6);
        idebt.mint(10_000e6, 0);
        vm.stopPrank();

        uint256 ratio = idebt.collateralizationRatioBps();
        // At baseline index, ratio should be near 100% (minus fee drag).
        assertGt(ratio, 9900);
        assertLt(ratio, 10100);
    }
}
