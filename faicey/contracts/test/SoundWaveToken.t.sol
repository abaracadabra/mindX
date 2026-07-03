// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {SoundWaveToken} from "../src/SoundWaveToken.sol";

/// SoundWave (SND / WAV) — capped supply + forensic 18-decimal voiceprints.
contract SoundWaveTokenTest is Test {
    SoundWaveToken wav;
    address alice = address(0xA11CE);
    address bob = address(0xB0B);

    function setUp() public {
        wav = new SoundWaveToken();
    }

    function test_Identity() public {
        assertEq(wav.name(), "SND");
        assertEq(wav.symbol(), "WAV");
        assertEq(wav.decimals(), 18);
    }

    function test_CappedSupply_NotInfinite() public {
        assertEq(wav.MAX_SUPPLY(), 1_000_000_000_000_000 * 1e18); // one quadrillion
        assertLt(wav.MAX_SUPPLY(), type(uint256).max);            // NOT infinite
        assertEq(wav.totalSupply(), 1_000_000_000 * 1e18);        // genesis
        assertEq(wav.balanceOf(address(this)), 1_000_000_000 * 1e18);
    }

    function test_Mint_RespectsCap() public {
        wav.mint(alice, wav.mintable());            // fill to the cap
        assertEq(wav.totalSupply(), wav.MAX_SUPPLY());
        vm.expectRevert(bytes("WAV: exceeds MAX_SUPPLY"));
        wav.mint(alice, 1);
    }

    function test_Mint_OnlyOwner() public {
        vm.prank(alice);
        vm.expectRevert(bytes("WAV: not owner"));
        wav.mint(alice, 1e18);
    }

    function test_Transfer() public {
        wav.transfer(alice, 100e18);
        assertEq(wav.balanceOf(alice), 100e18);
        vm.prank(alice);
        wav.transfer(bob, 40e18);
        assertEq(wav.balanceOf(bob), 40e18);
        assertEq(wav.balanceOf(alice), 60e18);
    }

    function _measures() internal pure returns (uint256[6] memory m) {
        m[0] = 220_500000000000000000; // dominantFrequency 220.5 Hz × 1e18
        m[1] = 421000000000000000;     // amplitude 0.421
        m[2] = 219_900000000000000000; // spectralCentroid 219.9 Hz
        m[3] = 430_700000000000000000; // spectralRolloff 430.7 Hz
        m[4] = 80000000000000000;      // zcr 0.08
        m[5] = 3_140000000000000000;   // hnr 3.14
    }

    function test_RegisterVoicePrint_18dec_and_reward() public {
        bytes32 h = keccak256("voiceprint-payload");
        vm.prank(alice);
        uint256 reward = wav.registerVoicePrint(h, 44100, _measures(), 9e17); // 0.9
        assertEq(reward, 900e18); // 1000 * 0.9
        assertEq(wav.balanceOf(alice), 900e18);
        assertEq(wav.voicePrintCount(), 1);
        assertEq(wav.voicePrintOwnerOf(h), alice);

        SoundWaveToken.VoicePrint memory vp = wav.getVoicePrint(alice);
        assertEq(vp.dominantFrequency, 220_500000000000000000);
        assertEq(vp.sampleRate, 44100);
        assertEq(vp.precisionScore, 9e17);
        assertTrue(vp.registered);
    }

    function test_VoicePrint_UniquenessEnforced() public {
        bytes32 h = keccak256("same");
        vm.prank(alice);
        wav.registerVoicePrint(h, 44100, _measures(), 5e17);
        vm.prank(bob);
        vm.expectRevert(bytes("WAV: voiceprint already registered"));
        wav.registerVoicePrint(h, 44100, _measures(), 5e17);
    }

    function test_RegisterVoicePrint_RejectsPrecisionOverOne() public {
        vm.expectRevert(bytes("WAV: precision > 1.0"));
        wav.registerVoicePrint(keccak256("x"), 44100, _measures(), 1e18 + 1);
    }

    function test_SupplyInfo() public {
        (uint256 cap, uint256 minted, uint256 remaining, uint8 dec) = wav.supplyInfo();
        assertEq(cap, wav.MAX_SUPPLY());
        assertEq(minted, 1_000_000_000 * 1e18);
        assertEq(remaining, cap - minted);
        assertEq(dec, 18);
    }
}
