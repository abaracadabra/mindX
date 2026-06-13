// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {cp2048_constants as C} from "../../contracts/cp2048/cp2048_constants.sol";
import {scientific_math} from "../../contracts/cp2048/scientific_math.sol";
import {scientific_token} from "../../contracts/cp2048/scientific_token.sol";
import {bankon_oracle} from "../../contracts/cp2048/bankon_oracle.sol";
import {rake} from "../../contracts/cp2048/rake.sol";

contract MockERC20 is ERC20 {
    constructor(string memory n, string memory s) ERC20(n, s) {}
    function mint(address to, uint256 a) external { _mint(to, a); }
}

contract MockPair {
    address public token0;
    address public token1;
    uint112 r0; uint112 r1;
    constructor(address t0, address t1, uint112 _r0, uint112 _r1) { token0 = t0; token1 = t1; r0 = _r0; r1 = _r1; }
    function getReserves() external view returns (uint112, uint112, uint32) { return (r0, r1, 0); }
}

contract cp2048_test is Test {
    using scientific_math for uint256;

    address admin = address(0xC0DE);
    address owner = address(0xBA5E);     // bankon.eth owner
    address issuance = address(0x1551);

    /* ── scientific_math: φ² = φ + 1 to 36-dp precision ── */
    function test_phi_squared_identity() public pure {
        uint256 phi = C.PHI_E36;
        uint256 sq = scientific_math.mul36(phi, phi);     // φ² in E36
        uint256 phiPlus1 = phi + C.E36;                   // φ + 1 in E36
        // equal within 1e20 (the last ~16 of 36 dp), proving full-rail precision
        uint256 diff = sq > phiPlus1 ? sq - phiPlus1 : phiPlus1 - sq;
        assertLt(diff, 1e20);
    }

    function test_golden_fee_is_positive_and_small() public pure {
        // 1000e18 amount, feeDiv 10_000 → fee ≈ 1000 * 0.618 / 10000 ≈ 0.0618e18
        uint256 fee = scientific_math.goldenFeeWad(1000e18, 10_000);
        assertGt(fee, 0);
        assertLt(fee, 1e18); // well under 1 unit
    }

    /* ── scientific_token: single issuance, immutable beneficiary, self_purge ── */
    function test_token_single_issuance_and_beneficiary() public {
        scientific_token t = new scientific_token(issuance, 1_000_000e18, owner);
        assertEq(t.totalSupply(), 1_000_000e18);
        assertEq(t.balanceOf(issuance), 1_000_000e18);
        assertEq(t.BENEFICIARY(), owner);
        assertEq(t.decimals(), 18);
    }

    function test_self_purge_only_to_beneficiary() public {
        scientific_token t = new scientific_token(issuance, 1_000e18, owner);
        MockERC20 stray = new MockERC20("Stray", "STR");
        stray.mint(address(t), 500e18);                  // someone sends tokens to the contract
        assertEq(stray.balanceOf(owner), 0);
        t.self_purge(address(stray));                    // permissionless
        assertEq(stray.balanceOf(owner), 500e18);        // funds can only reach the beneficiary
        assertEq(stray.balanceOf(address(t)), 0);
    }

    function test_owner_can_renounce() public {
        scientific_token t = new scientific_token(issuance, 1e18, owner);
        t.renounceOwnership();
        assertEq(t.owner(), address(0));
        // beneficiary stays immutable after renounce
        assertEq(t.BENEFICIARY(), owner);
    }

    /* ── bankon_oracle: price straight from the pair ── */
    function test_oracle_value_from_pair() public {
        MockERC20 tok = new MockERC20("Tok", "TOK");
        address usdc = address(0x5DC);
        // pair: 100 TOK ↔ 250 USDC(6dp) → 1 TOK = 2.5 USDC
        MockPair pair = new MockPair(address(tok), usdc, 100e18, 250e6);
        bankon_oracle o = new bankon_oracle(admin, usdc);
        vm.prank(admin); o.setPair(address(tok), address(pair));
        // value of 4 TOK = 10 USDC(6dp)
        assertEq(o.valueUsd6(address(tok), 4e18), 10e6);
        assertEq(o.valueUsd6(usdc, 7e6), 7e6); // usdc passthrough
    }

    /* ── rake: sweeps home only when value beats the chain threshold ── */
    function test_rake_only_above_threshold() public {
        MockERC20 tok = new MockERC20("Tok", "TOK");
        address usdc = address(0x5DC);
        MockPair pair = new MockPair(address(tok), usdc, 100e18, 250e6); // 1 TOK = 2.5 USDC
        bankon_oracle o = new bankon_oracle(admin, usdc);
        vm.prank(admin); o.setPair(address(tok), address(pair));

        rake r = new rake(admin, owner, o, 5e6); // threshold $5
        // 1 TOK = $2.5 < $5 → no sweep
        tok.mint(address(r), 1e18);
        assertEq(r.collect(address(tok)), false);
        assertEq(tok.balanceOf(owner), 0);
        // +2 TOK → 3 TOK = $7.5 > $5 → sweep home
        tok.mint(address(r), 2e18);
        assertEq(r.collect(address(tok)), true);
        assertEq(tok.balanceOf(owner), 3e18);     // raked to bankon.eth
        assertEq(tok.balanceOf(address(r)), 0);
    }
}
