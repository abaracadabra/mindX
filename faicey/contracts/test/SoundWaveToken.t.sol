// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test, console} from "forge-std/Test.sol";
import {SoundWaveToken} from "../src/SoundWaveToken.sol";

/**
 * SOUND WAVE Token Test Suite
 *
 * © Professor Codephreak - rage.pythai.net
 * Comprehensive tests for maximum supply token with 18-decimal precision
 */
contract SoundWaveTokenTest is Test {
    SoundWaveToken public token;
    address public owner;
    address public user1;
    address public user2;

    // Test constants
    uint256 public constant MAX_SUPPLY = type(uint256).max;
    uint256 public constant PRECISION_MULTIPLIER = 10**18;

    function setUp() public {
        owner = address(this);
        user1 = address(0x1);
        user2 = address(0x2);

        // Deploy the SOUND WAVE token
        token = new SoundWaveToken();
    }

    function testInitialState() public {
        // Check basic token properties
        assertEq(token.name(), "SOUND WAVE");
        assertEq(token.symbol(), "WAVE");
        assertEq(token.decimals(), 18);
        assertEq(token.totalSupply(), MAX_SUPPLY);

        // Check owner has maximum supply
        assertEq(token.balanceOf(owner), MAX_SUPPLY);

        // Check contract state
        assertEq(token.owner(), owner);
        assertTrue(token.voiceAnalysisEnabled());
    }

    function testMaximumSupplyLimits() public {
        // Verify we have the absolute maximum uint256 value
        assertEq(token.totalSupply(), MAX_SUPPLY);

        // Get max supply info
        (
            uint256 maxSupply,
            uint256 maxSupplyWith18Decimals,
            string memory maxSupplyString,
            string memory description
        ) = token.getMaximumSupplyInfo();

        assertEq(maxSupply, MAX_SUPPLY);
        assertEq(maxSupplyWith18Decimals, MAX_SUPPLY);
        assertTrue(bytes(maxSupplyString).length > 0);
        assertTrue(bytes(description).length > 0);

        console.log("Max Supply:", maxSupplyString);
        console.log("Description:", description);
    }

    function testPrecisionMathematics() public {
        // Test 18-decimal precision conversion
        uint256 testValue = 123;
        uint256 precision18 = token.toPrecision18(testValue);
        uint256 converted = token.fromPrecision18(precision18);

        assertEq(precision18, testValue * PRECISION_MULTIPLIER);
        assertEq(converted, testValue);

        console.log("Original value:", testValue);
        console.log("18-decimal precision:", precision18);
        console.log("Converted back:", converted);
    }

    function testPrecisionMathOperations() public {
        uint256 a = 5 * PRECISION_MULTIPLIER; // 5.0
        uint256 b = 2 * PRECISION_MULTIPLIER; // 2.0

        // Test addition
        uint256 sum = token.precisionMath(a, b, "add");
        assertEq(sum, 7 * PRECISION_MULTIPLIER);

        // Test subtraction
        uint256 diff = token.precisionMath(a, b, "subtract");
        assertEq(diff, 3 * PRECISION_MULTIPLIER);

        // Test multiplication (result should be scaled)
        uint256 product = token.precisionMath(a, b, "multiply");
        assertEq(product, 10 * PRECISION_MULTIPLIER); // 5 * 2 = 10

        // Test division
        uint256 quotient = token.precisionMath(a, b, "divide");
        assertEq(quotient, (5 * PRECISION_MULTIPLIER) / 2); // 2.5

        console.log("5 + 2 =", sum / PRECISION_MULTIPLIER);
        console.log("5 - 2 =", diff / PRECISION_MULTIPLIER);
        console.log("5 * 2 =", product / PRECISION_MULTIPLIER);
        console.log("5 / 2 =", quotient * 100 / PRECISION_MULTIPLIER, "/ 100"); // Show as 250/100 = 2.5
    }

    function testVoicePrintRegistration() public {
        // Create test voice print data
        bytes32 testHash = keccak256("test-voice-print");
        uint256 precisionScore = PRECISION_MULTIPLIER * 85 / 100; // 85% quality

        // Register voice print
        vm.prank(user1);
        token.registerVoicePrint(testHash, precisionScore);

        // Verify registration
        (
            bytes32 storedHash,
            uint256 timestamp,
            uint256 storedScore,
            string memory precisionDecimal
        ) = token.getVoiceAnalysisData(user1);

        assertEq(storedHash, testHash);
        assertGt(timestamp, 0);
        assertEq(storedScore, precisionScore);
        assertTrue(bytes(precisionDecimal).length > 0);

        console.log("Voice print registered for user1");
        console.log("Precision score:", precisionDecimal);
    }

    function testVoicePrintReward() public {
        uint256 initialBalance = token.balanceOf(user1);

        // Register high-quality voice print
        bytes32 testHash = keccak256("high-quality-voice");
        uint256 precisionScore = PRECISION_MULTIPLIER * 95 / 100; // 95% quality

        vm.prank(user1);
        token.registerVoicePrint(testHash, precisionScore);

        uint256 finalBalance = token.balanceOf(user1);

        // Should receive reward (exact amount depends on reward calculation)
        assertGt(finalBalance, initialBalance);

        console.log("Initial balance:", initialBalance);
        console.log("Final balance:", finalBalance);
        console.log("Reward received:", finalBalance - initialBalance);
    }

    function testBulkVoicePrintRegistration() public {
        // Create multiple voice print hashes
        bytes32[] memory hashes = new bytes32[](3);
        uint256[] memory scores = new uint256[](3);

        hashes[0] = keccak256("voice-1");
        hashes[1] = keccak256("voice-2");
        hashes[2] = keccak256("voice-3");

        scores[0] = PRECISION_MULTIPLIER * 80 / 100; // 80%
        scores[1] = PRECISION_MULTIPLIER * 90 / 100; // 90%
        scores[2] = PRECISION_MULTIPLIER * 75 / 100; // 75%

        uint256 initialBalance = token.balanceOf(user2);

        // Bulk register
        vm.prank(user2);
        token.bulkRegisterVoicePrints(hashes, scores);

        uint256 finalBalance = token.balanceOf(user2);

        // Verify last voice print is stored
        (bytes32 storedHash, , uint256 storedScore,) = token.getVoiceAnalysisData(user2);
        assertEq(storedHash, hashes[2]); // Last one should be stored
        assertEq(storedScore, scores[2]);

        // Should receive cumulative rewards
        assertGt(finalBalance, initialBalance);

        console.log("Bulk registration completed");
        console.log("Total rewards:", finalBalance - initialBalance);
    }

    function testMarketCapCalculation() public {
        uint256 pricePerToken = PRECISION_MULTIPLIER; // $1.00 per token

        uint256 marketCap = token.calculateMarketCap(pricePerToken);

        // Market cap should equal total supply when price is $1
        assertEq(marketCap, token.totalSupply());

        console.log("Market cap at $1/token:", marketCap);

        // Test with higher price
        uint256 highPrice = 50000 * PRECISION_MULTIPLIER; // $50,000 per token
        uint256 highMarketCap = token.calculateMarketCap(highPrice);

        console.log("Market cap at $50k/token: astronomical value");
        assertGt(highMarketCap, marketCap);
    }

    function testPrecisionPercentageCalculation() public {
        uint256 part = 25 * PRECISION_MULTIPLIER;
        uint256 total = 100 * PRECISION_MULTIPLIER;

        uint256 percentage = token.calculatePrecisePercentage(part, total);

        // Should be 25% with 18-decimal precision
        assertEq(percentage, 25 * PRECISION_MULTIPLIER);

        console.log("25/100 =", percentage / PRECISION_MULTIPLIER, "%");
    }

    function testTransferFunctionality() public {
        uint256 transferAmount = 1000 * PRECISION_MULTIPLIER; // 1000 tokens

        // Transfer from owner to user1
        token.transfer(user1, transferAmount);

        assertEq(token.balanceOf(user1), transferAmount);
        assertEq(token.balanceOf(owner), MAX_SUPPLY - transferAmount);

        console.log("Transfer successful:", transferAmount / PRECISION_MULTIPLIER, "WAVE tokens");
    }

    function testPrecisionTransfer() public {
        uint256 baseAmount = 100 * PRECISION_MULTIPLIER; // 100 tokens
        uint256 precisionMultiplier = PRECISION_MULTIPLIER / 2; // 0.5 multiplier

        // Should transfer 50 tokens (100 * 0.5)
        token.precisionTransfer(user1, baseAmount, precisionMultiplier);

        uint256 expectedAmount = 50 * PRECISION_MULTIPLIER;
        assertEq(token.balanceOf(user1), expectedAmount);

        console.log("Precision transfer:", expectedAmount / PRECISION_MULTIPLIER, "WAVE tokens");
    }

    function testContractInfo() public {
        (
            string memory tokenName,
            string memory tokenSymbol,
            uint8 tokenDecimals,
            uint256 maxSupply,
            uint256 currentTotalSupply,
            uint256 precisionMultiplier,
            bool voiceEnabled
        ) = token.getContractInfo();

        assertEq(tokenName, "SOUND WAVE");
        assertEq(tokenSymbol, "WAVE");
        assertEq(tokenDecimals, 18);
        assertEq(maxSupply, MAX_SUPPLY);
        assertEq(currentTotalSupply, MAX_SUPPLY);
        assertEq(precisionMultiplier, PRECISION_MULTIPLIER);
        assertTrue(voiceEnabled);

        console.log("Contract info verified successfully");
    }

    function testOwnershipFunctions() public {
        // Test voice analysis toggle
        assertTrue(token.voiceAnalysisEnabled());

        token.toggleVoiceAnalysis();
        assertFalse(token.voiceAnalysisEnabled());

        token.toggleVoiceAnalysis();
        assertTrue(token.voiceAnalysisEnabled());

        // Test ownership transfer
        token.transferOwnership(user1);
        assertEq(token.owner(), user1);

        console.log("Ownership functions working correctly");
    }

    function testFailInvalidVoicePrint() public {
        // Should fail with zero hash
        vm.prank(user1);
        token.registerVoicePrint(bytes32(0), PRECISION_MULTIPLIER);
    }

    function testFailExcessiveBulkRegistration() public {
        // Should fail with too many voice prints
        bytes32[] memory hashes = new bytes32[](101); // Over limit
        uint256[] memory scores = new uint256[](101);

        vm.prank(user1);
        token.bulkRegisterVoicePrints(hashes, scores);
    }

    function testFailUnauthorizedOwnershipTransfer() public {
        // Should fail when non-owner tries to transfer ownership
        vm.prank(user1);
        token.transferOwnership(user2);
    }

    // Gas optimization test
    function testGasOptimization() public {
        uint256 gasStart = gasleft();

        token.registerVoicePrint(
            keccak256("gas-test"),
            PRECISION_MULTIPLIER * 50 / 100
        );

        uint256 gasUsed = gasStart - gasleft();
        console.log("Gas used for voice print registration:", gasUsed);

        // Should be reasonable gas usage
        assertLt(gasUsed, 200000); // Less than 200k gas
    }
}