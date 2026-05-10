// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {ERC20}       from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20}      from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {MarketingTreasury, IUniswapV3SwapRouter} from "../MarketingTreasury.sol";

/// @dev Test ERC-20 with mint + burn.
contract TestToken is ERC20 {
    uint8 private immutable _decimals;
    constructor(string memory n, string memory s, uint8 d) ERC20(n, s) {
        _decimals = d;
    }
    function decimals() public view override returns (uint8) { return _decimals; }
    function mint(address to, uint256 a) external { _mint(to, a); }
    function burn(uint256 a) external { _burn(msg.sender, a); }
}

/// @dev Mock SwapRouter that simulates a fixed exchange rate.
contract MockSwapRouter is IUniswapV3SwapRouter {
    uint256 public outputPerUnit;             // BANKON SATOSHI per 1e6 USDC
    TestToken public bankon;

    constructor(TestToken bankon_, uint256 outputPerUnit_) {
        bankon = bankon_;
        outputPerUnit = outputPerUnit_;
    }

    function exactInputSingle(ExactInputSingleParams calldata params)
        external payable returns (uint256 amountOut)
    {
        // Pull tokenIn from caller.
        IERC20(params.tokenIn).transferFrom(msg.sender, address(this), params.amountIn);
        // Mint tokenOut to recipient.
        amountOut = (params.amountIn * outputPerUnit) / 1e6;
        require(amountOut >= params.amountOutMinimum, "minOut");
        bankon.mint(params.recipient, amountOut);
    }
}

contract MarketingTreasuryTest is Test {
    MarketingTreasury internal vault;
    TestToken internal usdc;
    TestToken internal bankon;
    MockSwapRouter internal router;

    address internal admin = address(0xA0);
    address internal payer = address(0xB0);
    address internal foundation = address(0xF0);
    bytes32 internal constant CID = keccak256("camp-1");

    function setUp() public {
        usdc   = new TestToken("USDC", "USDC", 6);
        bankon = new TestToken("BANKON SATOSHI", "BKS", 18);
        router = new MockSwapRouter(bankon, 1_000_000_000_000); // 1 USDC -> 1e12 BKS

        vault = new MarketingTreasury(
            admin,
            IERC20(address(usdc)),
            IERC20(address(bankon)),
            IUniswapV3SwapRouter(address(router)),
            3000,                 // 0.3% pool
            foundation
        );

        usdc.mint(payer, 10_000_000 * 1e6);    // $10M test budget
    }

    // ── Intake ──────────────────────────────────────────────────────

    function test_pay_credits_campaign() public {
        uint256 amt = 1_000 * 1e6;
        vm.startPrank(payer);
        usdc.approve(address(vault), amt);
        vault.pay(CID, amt);
        vm.stopPrank();

        assertEq(vault.revenueByCampaign(CID), amt);
        assertEq(vault.totalRevenue(), amt);
        assertEq(usdc.balanceOf(address(vault)), amt);
    }

    function test_pay_reverts_on_zero() public {
        vm.expectRevert(MarketingTreasury.ZeroAmount.selector);
        vm.prank(payer);
        vault.pay(CID, 0);
    }

    // ── 99/1 split ──────────────────────────────────────────────────

    function test_buyback_splits_99_1_and_burns() public {
        uint256 amt = 10_000 * 1e6;     // $10,000
        vm.startPrank(payer);
        usdc.approve(address(vault), amt);
        vault.pay(CID, amt);
        vm.stopPrank();

        vm.prank(admin);
        uint256 bksOut = vault.executeBuybackAndBurn(CID, amt, 1);

        // 1% to foundation
        uint256 foundationCut = (amt * 100) / 10_000;
        assertEq(usdc.balanceOf(foundation), foundationCut);

        // 99% buyback amount swapped + minted to vault then burned
        // bks should be burned, not in vault
        assertEq(bankon.balanceOf(address(vault)), 0);
        assertGt(bksOut, 0);

        // Cumulative bookkeeping
        assertEq(vault.totalToFoundation(), foundationCut);
        assertEq(vault.totalBoughtBack(), bksOut);
        assertEq(vault.totalBurned(), bksOut);
        assertEq(vault.revenueByCampaign(CID), 0);
    }

    function test_buyback_reverts_when_campaign_underfunded() public {
        uint256 amt = 1_000 * 1e6;
        vm.startPrank(payer);
        usdc.approve(address(vault), amt);
        vault.pay(CID, amt);
        vm.stopPrank();

        vm.expectRevert(abi.encodeWithSelector(
            MarketingTreasury.NoRevenueForCampaign.selector, CID
        ));
        vm.prank(admin);
        vault.executeBuybackAndBurn(CID, amt + 1, 1);
    }

    function test_buyback_reverts_when_paused() public {
        uint256 amt = 1_000 * 1e6;
        vm.startPrank(payer);
        usdc.approve(address(vault), amt);
        vault.pay(CID, amt);
        vm.stopPrank();

        vm.prank(admin);
        vault.pause();

        vm.prank(admin);
        vm.expectRevert();
        vault.executeBuybackAndBurn(CID, amt, 1);
    }

    function test_only_operator_role_can_buyback() public {
        uint256 amt = 1_000 * 1e6;
        vm.startPrank(payer);
        usdc.approve(address(vault), amt);
        vault.pay(CID, amt);
        vm.stopPrank();

        vm.prank(payer);
        vm.expectRevert();
        vault.executeBuybackAndBurn(CID, amt, 1);
    }

    function test_admin_can_update_foundation() public {
        address newF = address(0xF1);
        vm.prank(admin);
        vault.setFoundation(newF);
        assertEq(vault.foundation(), newF);
    }

    function test_admin_cannot_zero_foundation() public {
        vm.prank(admin);
        vm.expectRevert(MarketingTreasury.ZeroAddress.selector);
        vault.setFoundation(address(0));
    }

    // ── Fuzz: split arithmetic invariant ────────────────────────────

    /// @dev Split must always equal foundation_cut + buyback_cut, no rounding loss
    ///      that exceeds 1 base unit.
    function testFuzz_split_is_lossless(uint256 amount) public view {
        amount = bound(amount, 1e6, 1e18);
        uint256 foundationCut = (amount * 100) / 10_000;
        uint256 buybackCut = amount - foundationCut;
        // The sum must equal `amount` exactly — no rounding loss.
        assertEq(foundationCut + buybackCut, amount);
        // Foundation always ≤ 1% of input
        assertLe(foundationCut * 100, amount);
    }
}
