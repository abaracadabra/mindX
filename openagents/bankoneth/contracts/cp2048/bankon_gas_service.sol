// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// bankon_gas_service — "gas as a service" on the settlement chain (Base).
// A native-ETH reservoir, topped up by the golden-ratio BANKON fee, that drops
// PRECISELY ONE TRANSACTION worth of gas to an address that just arrived with a
// bridged asset from the Ethereum onboard chain — so a sovereign agent lands on
// Base already able to act, without pre-holding Base ETH. The drop is sized live
// from the chain's own basefee (block.basefee × DEFAULT_GAS_UNITS), capped, and
// one-shot per address by default. The reservoir can only ever be swept home to
// the immutable beneficiary (bankon.eth) — same invariant as scientific_token.
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {scientific_math} from "./scientific_math.sol";
import {cp2048_constants as C} from "./cp2048_constants.sol";

contract bankon_gas_service is Ownable {
    /// @notice immutable home for any swept reservoir funds (bankon.eth).
    address public immutable BENEFICIARY;

    /// @notice gas units one drop is sized to cover (≈ one swap/transfer on Base).
    uint256 public default_gas_units;
    /// @notice hard ceiling on a single drop, in wei (guards against basefee spikes).
    uint256 public max_drop_wei;
    /// @notice when true (default), each address may receive exactly one drop.
    bool public one_shot;
    /// @notice addresses that have already received their one transaction of gas.
    mapping(address => bool) public funded;
    /// @notice addresses permitted to trigger drops (e.g. bridge_collect on arrival). owner always may.
    mapping(address => bool) public allocator;

    event GasDropped(address indexed to, uint256 weiAmount, uint256 basefee, uint256 units);
    event GasIssued(address indexed to, uint256 gasWei, uint256 feeWei, uint256 sides);
    event Funded(address indexed from, uint256 weiAmount);
    event Config(uint256 units, uint256 cap, bool oneShot);
    event AllocatorSet(address indexed who, bool allowed);
    event Purged(uint256 weiAmount);

    error not_allocator();
    error already_funded();
    error reservoir_empty();
    error underpaid();

    constructor(address admin_, address beneficiary_, uint256 units_, uint256 cap_) Ownable(admin_) {
        BENEFICIARY = beneficiary_;
        default_gas_units = units_;
        max_drop_wei = cap_;
        one_shot = true;
    }

    /// @notice φ fee / treasury / autoconvert tops up the native reservoir.
    receive() external payable { emit Funded(msg.sender, msg.value); }

    /// @notice The size of the next drop at the current basefee (view helper for UIs).
    function quote_drop() public view returns (uint256 amt) {
        amt = block.basefee * default_gas_units;
        if (amt > max_drop_wei) amt = max_drop_wei;
    }

    /// @notice Drop exactly one transaction of gas to `to`. Permissioned to owner or
    ///         a registered allocator (e.g. the bridge-collect contract on arrival).
    function allocate_gas(address payable to) external returns (uint256 amt) {
        if (msg.sender != owner() && !allocator[msg.sender]) revert not_allocator();
        if (one_shot && funded[to]) revert already_funded();

        amt = quote_drop();
        if (address(this).balance < amt) revert reservoir_empty();

        funded[to] = true;
        (bool ok, ) = to.call{value: amt}("");
        require(ok, "drop failed");
        emit GasDropped(to, amt, block.basefee, default_gas_units);
    }

    // ── custom client-paid gas issuance ──

    /// @notice The BANKON fee for issuing `cost_wei` of gas across `sides` contract calls:
    ///         the golden-ratio markup φ/10 = 0.1618033988749894848 (16.18%, 18 dp), times
    ///         `sides` (1 when gas is needed on a single side, 2 when on each side of a
    ///         cross-chain transaction). e.g. quote_fee(0.001 ether, 1) ≈ 0.000161803… ETH.
    function quote_fee(uint256 cost_wei, uint256 sides) public pure returns (uint256) {
        return scientific_math.goldenGasFeeWad(cost_wei, sides);
    }

    /// @notice What a custom purchase costs: the gas issued to the user on this chain
    ///         (`gas_wei`) plus the golden BANKON fee on `sides` call-costs.
    function quote_buy(uint256 gas_wei, uint256 sides)
        public pure returns (uint256 issue, uint256 fee, uint256 total)
    {
        issue = gas_wei;
        fee = scientific_math.goldenGasFeeWad(gas_wei, sides);
        total = issue + fee;
    }

    /// @notice The golden multiplier (WAD) for an expedited priority `tier`: tier 0 = normalized
    ///         (φ/10), each step ×φ; the resulting fee is still capped at 3× cost. UI convenience.
    function tier_mult(uint256 tier) public pure returns (uint256) {
        return scientific_math.goldenTierMult(tier);
    }

    /// @notice The BANKON fee at a custom priority `mult_wad` (1e18 = normalized). Increases
    ///         proportionally with priority, hard-capped at 3× the contract cost.
    function quote_fee_priority(uint256 cost_wei, uint256 sides, uint256 mult_wad) public pure returns (uint256) {
        return scientific_math.goldenFeePriority(cost_wei, sides, mult_wad);
    }

    /// @notice Custom gas issuance where the CLIENT pays. Send `gas_wei + quote_fee(gas_wei,
    ///         sides)` (or more) as msg.value; `gas_wei` is delivered to `to` on this chain and
    ///         the golden fee (plus any excess) stays in the reservoir, swept home to bankon.eth.
    ///         `sides` = 1 same-chain, 2 when the rail needs gas on each side of a bridge.
    function buy_gas(address payable to, uint256 gas_wei, uint256 sides)
        external payable returns (uint256 fee)
    {
        return _buy_gas(to, gas_wei, sides, C.WAD);
    }

    /// @notice As buy_gas, but at an expedited priority `mult_wad` (1e18 = normalized; higher =
    ///         faster, fee climbs by golden steps, capped at 3× cost). Use tier_mult(tier) for
    ///         the golden tier ladder.
    function buy_gas_priority(address payable to, uint256 gas_wei, uint256 sides, uint256 mult_wad)
        external payable returns (uint256 fee)
    {
        return _buy_gas(to, gas_wei, sides, mult_wad);
    }

    function _buy_gas(address payable to, uint256 gas_wei, uint256 sides, uint256 mult_wad)
        internal returns (uint256 fee)
    {
        fee = scientific_math.goldenFeePriority(gas_wei, sides, mult_wad);
        if (msg.value < gas_wei + fee) revert underpaid();
        (bool ok, ) = to.call{value: gas_wei}("");
        require(ok, "issue failed");
        // fee + any overpayment remain in this contract's reservoir (→ BENEFICIARY via self_purge).
        emit GasIssued(to, gas_wei, fee, sides);
    }

    // ── owner controls ──
    function set_units(uint256 units_) external onlyOwner { default_gas_units = units_; emit Config(units_, max_drop_wei, one_shot); }
    function set_cap(uint256 cap_) external onlyOwner { max_drop_wei = cap_; emit Config(default_gas_units, cap_, one_shot); }
    function set_one_shot(bool v) external onlyOwner { one_shot = v; emit Config(default_gas_units, max_drop_wei, v); }
    function set_allocator(address who, bool allowed) external onlyOwner { allocator[who] = allowed; emit AllocatorSet(who, allowed); }

    /// @notice Permissionless sweep of the entire reservoir — funds can ONLY ever reach
    ///         the immutable beneficiary (bankon.eth). Mirrors scientific_token.self_purge.
    function self_purge() external {
        uint256 bal = address(this).balance;
        if (bal == 0) revert reservoir_empty();
        (bool ok, ) = payable(BENEFICIARY).call{value: bal}("");
        require(ok, "purge failed");
        emit Purged(bal);
    }
}
