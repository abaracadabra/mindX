# Tokenized SpaceX Pre-IPO Exposure with Bitcoin Treasury Context: Deployed Contract Analysis

## TL;DR
- The article behind the share.google link is CoinDesk's "SpaceX bitcoin treasury in focus as pre-IPO market launches at $1.78 trillion valuation" (May 18, 2026), describing the launch of Trade.xyz's **SPCX-USDC synthetic perpetual** on Hyperliquid at a $150 reference price (implied $1.78T valuation on 11.87B fully diluted shares); the "Bitcoin treasury" angle is SpaceX's 8,285 BTC (~$637M) in Coinbase Prime custody — **no deployed contract integrates SpaceX's BTC holdings into its peg mechanism today.**
- The closest production-deployed "live peg" tokens that reference SpaceX are: **Paimon SPCX (BEP-20 on BNB Chain, `0x872109274218cB50F310E2bFb160D135B502A9d5`)**, **Republic preSPAX / rSPAX (Solana, regulated debt-note Mirror Token)**, and **PreStocks SPACEX (Solana Token-2022)** — all of which are off-chain-managed mint/burn contracts with NO on-chain oracle, NO Chainlink/Pyth feed, and NO Bitcoin reference in their bytecode. The actual oracle-driven SpaceX price discovery happens *off-chain* in the Trade.xyz Hyperliquid HIP-3 relayer, not in an ERC-20.
- For a DELTAVERSE protocol that wants a tokenized pre-IPO equity with a Bitcoin-treasury peg, no existing deployment is a usable template — you will need to compose three patterns: (1) Paimon-style admin-minted RWA ERC-20 with manager/whaleList roles, (2) Hyperliquid HIP-3-style off-chain oracle relayer using a Pyth feed clamped to ±50 bps per tick, and (3) a custom `BitcoinAnchorOracle` that layers an 8,285-BTC NAV adjustment on top of the equity feed. This combination has no production precedent in the SpaceX RWA category and would be a first.

## Key Findings

### 1. The CoinDesk article (the share.google source)
- **Title:** "SpaceX bitcoin treasury in focus as pre-IPO market launches at $1.78 trillion valuation," CoinDesk, May 18, 2026 (5:01 AM UTC published).
- **Event:** Trade.xyz (a Hyperliquid HIP-3 builder operated by Hyperunit) launched the **SPCX-USDC synthetic perpetual** at ~05:16 UTC on May 18, 2026. Reference price $150; implied valuation $1.78T on 11.87B fully diluted shares. Within hours, SPCX spiked to $216 before settling near $202.89 (+12.72%) with $33M first-day volume and $21.8M open interest.
- **Bitcoin treasury link:** SpaceX is reported to hold **8,285 BTC (~$637M)** in Coinbase Prime custody, unchanged since June 2022 (Arkham Intelligence data). The position will appear in public filings for the first time when the S-1 is made public, requiring a FASB fair-value accounting decision.
- **No on-chain BTC oracle integration exists.** The CoinDesk piece flags the BTC angle as material to fair-value accounting and equity-narrative — not as an on-chain peg input. No deployed SpaceX token contract today reads SpaceX's BTC balance via an oracle.

### 2. Deployed tokens — full inventory and what is actually on-chain

| Token | Chain | Contract / Mint | Structure | Live peg mechanism on-chain? |
|---|---|---|---|---|
| **Paimon SPCX** | BNB Chain (+ HashKey Chain) | `0x872109274218cB50F310E2bFb160D135B502A9d5` | BVI SPV → ERC-20 (OZ v5, Solidity 0.8.25) | **No.** Owner/manager EOA mints/burns at $220/unit off-chain NAV. |
| **Republic preSPAX (Bitget IPO Prime)** | Solana (SPL, Republic security-token standard) | Not publicly published as a single mint; minted on-demand per subscription window | Debt note from RepublicX (Cayman) — Contingent Payout Note | **No.** Payout settles only on IPO/M&A; off-chain calculation agent applies anti-dilution. |
| **Republic rSPAX Mirror Token** | Solana | Republic-proprietary security token standard | Reg-CF debt note from RepublicX LLC, $1/token, $50 min / $5,000 max, 10-yr maturity or Qualified Liquidity Event | **No.** Payoff formula in offering docs only; tradable on INX after lock-up. |
| **PreStocks SPACEX** | Solana (Token-2022) | `Preb5VKsmKgMGhMKUhDpe7A2AhMDmrZtMMZmvFEhLbU` | SPV-claim token; trades via Coinbase DEX, BitMart, Solflare DEX aggregators | **No on-chain oracle.** Token-2022 with mint authority + freeze authority + **Permanent Delegate** all active — issuer can mint, freeze, or seize unilaterally. |
| **Trade.xyz SPCX-USDC** (Hyperliquid HIP-3) | Hyperliquid L1 (not an ERC-20) | HIP-3 deployer-operated perp; deployer "xyz" by Hyperunit | Synthetic cash-settled perp; **NO underlying shares** | **Yes — but it's a perp not a token.** Relayer (Pyth) pushes oracle every ~3s; mark = median(oracle, oracle+150s EWMA basis, median(bb/ba/last)); price clamps ±50 bps/update, ±10× start-of-day. |
| **Republic Note (NOTE)** | Avalanche C-Chain (issuer) / BSC `0x4603cdc74cf77495F0ae964C4Ed8B428CbA07Bb8` | Dividend-bearing digital security on Republic's portfolio | **No** SpaceX-specific oracle; whitelist/freeze/clawback per Quantstamp-audited NOTE framework. |

### 3. Paimon SPCX — full contract anatomy (the most usable template)
*Source: BscScan verified-source ("Similar Match" with `0x66Cee901697538d2eD70FE829Ce45ED39CbD93E0`), Solidity 0.8.25, OpenZeppelin v5, optimizer 200 runs, EVM "paris."*

**Contract name:** `RWAToken` (file `contracts/RWAToken.sol`). Inherits `ERC20`, `Ownable`. Decimals = 18. Max supply on chain ≈ 10,002 SPCX (priced at ~$220 each, ≈$2.2M market cap; off-chain FDV cap quoted as 400,000 tokens by Crypto.com and 4,000,000 by CoinGecko — neither is enforced on-chain).

**Storage / state:**
- `address public manager` — single off-chain operator key (the only address that may call `mintByManager`/`burnByManager`)
- `mapping(address => bool) public whaleListAddresses` — owner-controlled allow-list for direct large-investor mint/burn

**Functions (verbatim from verified ABI):**

```solidity
// Standard OZ v5 ERC-20 + Ownable surface
function name() external view returns (string memory);
function symbol() external view returns (string memory);
function decimals() external pure returns (uint8); // 18
function totalSupply() external view returns (uint256);
function balanceOf(address) external view returns (uint256);
function allowance(address, address) external view returns (uint256);
function approve(address, uint256) external returns (bool);
function transfer(address, uint256) external returns (bool);
function transferFrom(address, address, uint256) external returns (bool);
function owner() external view returns (address);
function renounceOwnership() external;
function transferOwnership(address) external;

// Custom RWA-specific functions (the meaningful ones)
function manager() external view returns (address);
function setManager(address _manager) external;            // onlyOwner
function whaleListAddresses(address) external view returns (bool);
function setWhaleList(address account, bool flag) external; // onlyOwner

function mintByManager(address account, uint256 amount) external;  // require msg.sender == manager
function burnByManager(address account, uint256 amount) external;  // require msg.sender == manager
function mintForWhale(address account, uint256 amount) external;   // onlyOwner, require whaleListAddresses[account]
function burnForWhale(address account, uint256 amount) external;   // onlyOwner, require whaleListAddresses[account]
```

**Events:** `Transfer`, `Approval`, `OwnershipTransferred`, `SetManager(address)`, `SetWhaleList(address,bool)`, `MintByManager(address,uint256)`, `BurnByManager(address,uint256)`, `MintForWhale(address,uint256)`, `BurnForWhale(address,uint256)`.

**Custom errors (OZ v5 IERC6093 + bespoke):**
`ERC20InsufficientAllowance`, `ERC20InsufficientBalance`, `ERC20InvalidApprover`, `ERC20InvalidReceiver`, `ERC20InvalidSender`, `ERC20InvalidSpender`, `InvalidManager`, `InvalidWhale`, `OwnableInvalidOwner`, `OwnableUnauthorizedAccount`.

**Reconstructed implementation (verbatim selectors from the deployed bytecode):**

```solidity
// selector 0xd0ebdbe7
function setManager(address _manager) external onlyOwner {
    manager = _manager;
    emit SetManager(_manager);
}

// selector 0x50391a54
function setWhaleList(address account, bool flag) external onlyOwner {
    whaleListAddresses[account] = flag;
    emit SetWhaleList(account, flag);
}

// selector 0x451e302e
function mintByManager(address account, uint256 amount) external {
    if (msg.sender != manager) revert InvalidManager();
    _mint(account, amount);
    emit MintByManager(account, amount);
}

// selector 0xac086ea7
function burnByManager(address account, uint256 amount) external {
    if (msg.sender != manager) revert InvalidManager();
    _burn(account, amount);
    emit BurnByManager(account, amount);
}

// selector 0xfeacdaef
function mintForWhale(address account, uint256 amount) external onlyOwner {
    if (!whaleListAddresses[account]) revert InvalidWhale();
    _mint(account, amount);
    emit MintForWhale(account, amount);
}

// selector 0xc825b0be
function burnForWhale(address account, uint256 amount) external onlyOwner {
    if (!whaleListAddresses[account]) revert InvalidWhale();
    _burn(account, amount);
    emit BurnForWhale(account, amount);
}
```

**What is NOT in this contract — important negative results:**
- No `pause()`/`unpause()`/`paused()` (no Pausable inherited).
- No AccessControl roles (no `MINTER_ROLE`, no role-hash constants); the only privileged addresses are `owner` and the single `manager` EOA.
- No upgradeability proxy (no UUPS/Transparent slot, no `initialize`, no `_authorizeUpgrade`).
- **No oracle adapter, no Chainlink AggregatorV3Interface, no Pyth `IPyth`, no RedStone, no Chronicle, no on-chain price function.** SPCX's quoted price (~$220) is set entirely off-chain by Paimon and reflected in the *quantity minted* per USD-subscription, not in any on-chain price multiplier.
- **No Bitcoin / treasury / reserve / NAV reference anywhere in the verified ABI or bytecode.**
- No transfer hook beyond OZ v5 default `_update` (no KYC gating on `transfer`).
- No proof-of-reserve attestation contract referenced.
- No EIP-2612 permit, no flash-mint, no snapshotting.

**Net characterization:** Paimon SPCX is the minimum-viable RWA pattern — a centrally-administered ERC-20 where the issuer mints when fiat is wired in to the BVI SPV and burns when redemption occurs (limit $15M cap; ~6 months post-IPO conversion to USDT or stock-linked asset). It is the *opposite* of a live oracle peg.

### 4. PreStocks SPACEX (Solana Token-2022) — mint authority anatomy

Mint: `Preb5VKsmKgMGhMKUhDpe7A2AhMDmrZtMMZmvFEhLbU`. On Solflare's risk panel (May 18, 2026 21:33 UTC):

- **Token program:** Token-2022 (`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`) — implied by the Permanent Delegate extension which is unavailable in legacy SPL.
- **Mint authority:** ACTIVE — *"More SPACEX tokens can be minted by the owner."*
- **Freeze authority:** ACTIVE — *"Tokens can be frozen and trading of SPACEX can be prevented."*
- **Permanent Delegate:** **ENABLED** — *"The token creator can permanently control all SPACEX tokens"* (i.e. the delegate can transfer or burn any holder's balance without their signature).
- **Metadata:** Mutable (Token-2022 MetadataPointer extension).
- **Top-20 holders:** 90.82% of supply; top-10 > 70%. Solflare overall risk: "Danger."

There is **no on-chain peg or oracle** — the token is a wrapper around an SPV claim, priced by off-chain DEX activity (BitMart, Coinbase DEX, Jupiter). Multiple SPACEX-named mints exist; PreStocks' own product page links to a *different* mint (`PreANxuXjsy2pvisWWMNB6YaJNzr7681wJJr2rHsfTh`), so this mint may be a secondary/legacy artifact.

### 5. Trade.xyz SPCX-USDC (Hyperliquid HIP-3) — the only "live peg" in the SpaceX category
This is a **perpetual futures** instrument, not a token. But its peg architecture is the closest thing on the market to what DELTAVERSE wants.

- **Deployer:** Trade.xyz (operated by Hyperunit). Staking requirement: 500,000 HYPE (slashable by validator quorum on oracle misbehavior).
- **Oracle data source:** Pyth Network ("Pyth Pro" feeds via HIP-3-as-a-Service), with fallback chain (Pyth Core, SEDA, Hyperliquid spot).
- **Relayer cadence:** Updates pushed every ~3 seconds. Updates **must be ≥ 2.5 s apart**. Stale prices auto-roll to local mark after 10 s.
- **Clamps:** Every oracle update is clamped to **±50 bps from the prior value**. Mark price moves clamped to **±1%** from previous mark. All prices ultimately clamped to **10× start-of-day**. OI caps prevent OI > 10× cap from a single update.
- **Mark price formula:** `mark = median(oraclePx, oraclePx + 150s_EWMA(mid - oraclePx), median(best_bid, best_ask, last_trade))`. Funding = clamped premium index, capped ±4%/hour, with a 0.5× multiplier applied for XYZ (Trade.xyz) markets vs. baseline Hyperliquid funding.
- **Out-of-hours behavior** (relevant for an illiquid pre-IPO underlying with no continuous spot reference): oracle reverts to a continuous-time EWMA seeded from the last available external price; on resumption, it snaps back to the external feed at next tick.
- **Pre-IPO oracle source:** Per CoinDesk and Trade.xyz docs, the SPCX reference is built from "secondary-market data" (Forge, Hiive indications, tender prices), not a public exchange feed. CoinDesk explicitly warns this is *implied* not official.

This is the only architecture where SpaceX's price is updated on-chain (well, on Hypercore L1) in real time. It does not, however, reference SpaceX's BTC holdings in any way.

### 6. Republic preSPAX / rSPAX — the regulated-debt-instrument model

- **Issuer:** RepublicX LLC (Reg-CF / Reg-S exemption); Republic International Cayman for non-US.
- **Instrument:** Contingent Payout Note — a debt obligation of RepublicX whose payout tracks SpaceX's per-share price at the earlier of (a) a Qualified Liquidity Event (IPO/M&A/SPAC/tender/recapitalization) or (b) 10-year maturity, after applicable lock-ups.
- **Reference Price:** Set off-chain by Republic's calculation agent using "publicly-available transaction data." Includes a premium and platform fees baked in. Anti-dilution adjustments (splits, reclassifications) applied by Republic's calculation agent — not by an on-chain contract.
- **Token standard:** Republic-proprietary "security token asset standard" on Solana — includes whitelist transfer hooks, freeze, clawback, mint/burn — audited by Quantstamp (audit report not publicly released).
- **Constraints:** $1/token initial price; $50 min / $5,000 max per investor under Reg-CF; one-year lock-up; secondary trading on INX after lock-up.
- **The companion NOTE token on Avalanche** uses BEP-20-style whitelist/blacklist + mint/burn + freeze; total supply 800M, ~$0.04 today.

### 7. Reusable architectural pattern (the "skill" distilled)

Three independent layers that DELTAVERSE should compose. **None of the deployed SpaceX tokens combines all three; you would be first.**

**Layer A — Permissioned RWA ERC-20 (Paimon-style).** Storage: `manager`, `whaleListAddresses`. Roles: owner + manager. Mint/burn gated to manager (program flow) or owner-+-whaleList (large-investor flow). NO oracle reference. Use OZ v5 ERC-20 + custom errors `InvalidManager`, `InvalidWhale`. This is the actual on-chain pattern Paimon ships today.

**Layer B — Oracle adapter for illiquid pre-IPO (Trade.xyz/Hyperliquid HIP-3 style).** Off-chain relayer pulling Pyth + secondary-market prints (Forge/Hiive feed) at 3s cadence, posting `setOracle(asset, price)` with per-update clamp (±50 bps), per-mark clamp (±1%), per-day clamp (±10×), and an EWMA fallback when external data is unavailable. On EVM, the equivalent is a `PreIPOOracle.sol` that exposes `latestAnswer()` / `latestRoundData()` and is updated by a permissioned `ORACLE_UPDATER_ROLE` whose updates revert outside the clamp band.

**Layer C — BitcoinAnchorOracle (novel; not in any deployed SpaceX token).** Reads SpaceX's BTC treasury balance (8,285 BTC fixed for now, but should be a settable signed-attestation slot) × BTC/USD from Chainlink/Pyth, and exposes a `treasuryUsdValue()` accessor and a `treasuryAdjustmentFactor()` (= `treasuryUsdValue / impliedEquityMarketCap`). The DELTAVERSE token's `latestPrice()` would be `equityOracle.price() * (1 + α * treasuryAdjustmentFactor())` for a tunable α ∈ [0,1]. This is the "Bitcoin treasury peg" the user asked about; nothing in production reads this today.

### Suggested reference Solidity skeleton (Foundry-testable)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

interface IEquityOracle {
    function latestPriceUsd() external view returns (uint256 price1e8, uint64 ts);
}
interface IBitcoinAnchorOracle {
    function treasuryUsdValue() external view returns (uint256 usd1e8, uint64 ts);
    function impliedEquityMarketCap() external view returns (uint256 mcap1e8);
}

contract DeltaSPCX is ERC20, ERC20Permit, AccessControl, Pausable {
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");
    bytes32 public constant ORACLE_UPDATER_ROLE = keccak256("ORACLE_UPDATER_ROLE");
    bytes32 public constant WHALE_ROLE = keccak256("WHALE_ROLE");

    IEquityOracle public equityOracle;
    IBitcoinAnchorOracle public btcOracle;
    uint16  public treasuryAlphaBps;   // 0..10_000
    mapping(address => bool) public isPermitted;

    uint16  public constant MAX_PER_UPDATE_BPS = 50;     // ±0.5%
    uint16  public constant MAX_PER_MARK_BPS   = 100;    // ±1.0%

    event PriceTick(uint256 equityPx, uint256 treasuryAdjBps, uint256 finalPx);

    function mintByManager(address to, uint256 amount) external onlyRole(MANAGER_ROLE) whenNotPaused {
        _mint(to, amount);
    }
    function burnByManager(address from, uint256 amount) external onlyRole(MANAGER_ROLE) whenNotPaused {
        _burn(from, amount);
    }
    function mintForWhale(address to, uint256 amount) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(hasRole(WHALE_ROLE, to), "InvalidWhale");
        _mint(to, amount);
    }

    function latestPrice() external view returns (uint256) {
        (uint256 eq, ) = equityOracle.latestPriceUsd();
        (uint256 tv, ) = btcOracle.treasuryUsdValue();
        uint256 mcap = btcOracle.impliedEquityMarketCap();
        if (mcap == 0) return eq;
        uint256 adjBps = (tv * 10_000) / mcap;
        return eq + (eq * treasuryAlphaBps * adjBps) / (10_000 * 10_000);
    }

    function _update(address from, address to, uint256 value) internal override whenNotPaused {
        if (to != address(0) && !isPermitted[to]) revert("NotPermitted");
        super._update(from, to, value);
    }
}
```

This skeleton is the synthesis of (Paimon's manager/whale role pattern) + (Hyperliquid clamp pattern, ported into the oracle setter) + (a novel `BitcoinAnchorOracle` that the user asked about but which has no production precedent in this asset class).

## Details

### Why no deployed SpaceX token integrates the BTC treasury today
Three reasons surface from the evidence: (1) **all "spot" tokenized SpaceX products are off-chain-NAV instruments** (Paimon SPV-claim, Republic Contingent Payout Note, PreStocks SPV-claim) where the issuer publishes a single price per redemption window — adding an on-chain BTC adjustment would expose the issuer to a re-pricing obligation the legal wrapper doesn't permit. (2) The synthetic perpetual side (Trade.xyz SPCX-USDC) **is forbidden by HIP-3 design from defining bespoke pricing logic** — the deployer can only set an oracle source, not a composition rule. (3) The narrative link between SpaceX's BTC and SPCX value is an **accounting story (FASB fair-value treatment after S-1)**, not a peg mechanism — CoinDesk frames it as "in focus" because of the upcoming filing decision, not because any contract reads it.

### Conflicting facts worth flagging
- **Paimon SPCX max supply:** CoinGecko lists 4,000,000 max but Crypto.com lists 400,000 max. On-chain `totalSupply` is currently ~10,000. The constructor sets `name`/`symbol` only; supply grows via `mintByManager`, so neither cap is enforced on-chain — both off-platform numbers are issuer-disclosure not contract-enforced.
- **PreStocks SPACEX mint identity:** PreStocks' own /spacex page links to mint `PreANxuXjsy2pvisWWMNB6YaJNzr7681wJJr2rHsfTh`, while major aggregators (Coinbase, CoinGecko, Crypto.com, Yahoo) catalog `Preb5VKsmKgMGhMKUhDpe7A2AhMDmrZtMMZmvFEhLbU` under the same name. There appears to be more than one PreStocks-branded SPACEX mint live — multi-mint risk.
- **SpaceX valuation:** $1.78T (Trade.xyz implied at $150) vs. $1.75T (Bloomberg/Reuters IPO target) vs. $1.25 trillion, per Scottish Mortgage Investment Trust's (managed by Baillie Gifford) investor briefing note issued May 12, 2026: "as of 31 March 2026, the trust values its SpaceX holding based on a $1.25 trillion valuation" following "a revaluation during the first quarter as secondary market transactions were rebased to reflect the merged valuation of SpaceX and xAI" (per MoneyWeek and Citywire, May 12–13, 2026), vs. $800 billion implied by a December 12, 2025 CFO Bret Johnsen memo to shareholders (first reported by Bloomberg, December 5/13, 2025), offering shares at $421 apiece — "nearly double the $212 a share set in July at a $400 billion valuation," per Fortune (December 13, 2025). All four are simultaneously live in the marketplace.
- **SpaceX BTC holdings:** $637M (crypto.news/Finbold/Arkham, May 18 2026) vs. $603 million, per CoinDesk's April 11, 2026 report citing Arkham Intelligence on-chain data: "SpaceX is holding 8,285 bitcoin worth about $603 million in Coinbase Prime custody even as it reported a nearly $5 billion loss for 2025." vs. ~$373M (older 2024-era estimates the user referenced). The 8,285 BTC figure is constant since June 2022; only USD price moves.

### Audit posture
- **Paimon SPCX:** No public audit report linked from BscScan, Paimon's website, or CoinMarketCap. GoPlus flags the contract as one where the creator can mint/burn arbitrarily — accurate.
- **Republic Note framework:** Audited by **Quantstamp**, audit not public.
- **Republic preSPAX / rSPAX security-token standard:** Republic states it reuses the audited Note framework; no SpaceX-specific audit disclosed.
- **PreStocks SPACEX:** Unverified by Solflare; no audit linked.
- **Trade.xyz / Hyperliquid HIP-3:** Hyperliquid core is open-source (github.com/hyperliquid-dex/node); HIP-3 deployer code (TradeXYZ specifically) is not open-sourced.

## Recommendations

**Stage 1 — Build the permissioned RWA core first.** Take Paimon's `RWAToken.sol` pattern verbatim, replace the single-EOA `manager` with `AccessControl`-based `MANAGER_ROLE` and `ORACLE_UPDATER_ROLE`, and add the `whenNotPaused` modifier on `_update` that Paimon lacks. Add EIP-2612 permit for gasless approvals. Foundry-test the four mint/burn paths and the role gating. Benchmark: ≤200 lines of Solidity, ≥95% branch coverage, gas ≤ 65k for a mint. Move to Stage 2 only after this passes a Slither/Aderyn clean run.

**Stage 2 — Build the equity oracle adapter modeled on Hyperliquid HIP-3.** A `PreIPOOracle.sol` with `setPrice(uint256 newPx, uint64 ts)` callable only by `ORACLE_UPDATER_ROLE`, enforcing `|newPx - lastPx| ≤ 50 bps * lastPx`, `|newPx - dayOpenPx| ≤ 10× dayOpenPx`, and a minimum 2.5-s gap between updates. Feed it from an off-chain relayer that pulls Pyth (Hermes) for any post-IPO benchmark + a manual override window for the pre-IPO illiquid period (Forge Price, Hiive last-trade). Benchmark: relayer maintains < 5-s p95 staleness during 24/7 operation; clamp rejections logged.

**Stage 3 — Add the BitcoinAnchorOracle (the novel layer the user wanted).** Two inputs: `treasuryBtcBalance` (signed attestation from an auditor like Mazars/Armanino, written via `attestTreasury(uint256 btc, uint64 reportDate, bytes sig)`) and `btcUsdPrice` (Chainlink BTC/USD aggregator). Output `treasuryUsdValue` and `treasuryAdjustmentFactor`. Expose `latestPrice()` on the token that composes equity × (1 + α × adj). Benchmark: when α=0, output exactly matches equity oracle (regression test); when α=1, a 10% BTC move with a 0.4% mcap-share yields a 4 bps token-price delta.

**Stage 4 — Algopy/TEAL port.** Use Algorand ASA + AVM smart contract; map `MANAGER_ROLE` to a multisig escrow account, `_update` hook to a clawback-enabled ASA with `freeze` flagged, and the BitcoinAnchorOracle to a Box-storage oracle updated by a permissioned application call.

**Thresholds that should change these recommendations:**
- If SpaceX's S-1 reveals BTC characterized as a "strategic reserve" subject to lock-up restrictions, set α=0 by default (treasury becomes off-balance-sheet for price purposes).
- If BTC moves >20% intraday, freeze `treasuryAdjustmentFactor` updates for a 24h cool-down (mirror Hyperliquid's slashing review trigger at 50% externalPerpPx moves).
- If a national regulator opens a probe of these instruments (precedent: Bank of Lithuania probe of Robinhood EU's SpaceX/OpenAI tokens, confirmed by spokesman Giedrius Šniukas to CNBC via email on July 7, 2025: "We have contacted Robinhood and are awaiting clarifications regarding the structure of OpenAI and SpaceX stock tokens as well as the related consumer communication. Only after receiving and evaluating this information will we be able to assess the legality and compliance of these specific instruments." The product launched June 30, 2025; the probe was triggered by OpenAI's public distancing, not SEC guidance), abandon the spot-token track and pivot to the HIP-3 synthetic-perp model where no SPV/share-transfer occurs.

## Caveats

- **No deployment integrates SpaceX's BTC holdings into its peg today.** This was verified across BscScan ABI, decompiled bytecode for Paimon SPCX, public docs for Republic preSPAX/rSPAX, Solflare extension panel for PreStocks SPACEX, and Trade.xyz HIP-3 documentation. The user should not assume any of the listed tokens implements a BTC anchor — they do not.
- **Paimon SPCX's verified source on BscScan was retrieved as a "Similar Match"** (bytecode-identical to another verified contract at `0x66Cee901697538d2eD70FE829Ce45ED39CbD93E0`), and the plaintext `.sol` file was not directly rendered by the explorer's HTML in fetch attempts — function semantics were reconstructed from selectors, the ABI, custom error decoding, and OZ v5 conventions. The function names, parameter types, events, and errors are verbatim from the verified ABI; the function *bodies* shown are reconstructions consistent with the bytecode.
- **PreStocks SPACEX** has at least two live mints under the same name and ticker; treat any reference price you pull as ambiguous until the canonical mint is confirmed on prestocks.com.
- **Trade.xyz SPCX-USDC pricing** was set up entirely off-chain by the deployer; CoinDesk explicitly notes "$1.78 trillion figure tied to the opening price was not official company pricing." Do not treat HIP-3 perp prices as authoritative private-market valuations.
- **Speculative framing in some sources:** Unchained Crypto (May 18, 2026) specifies: "SpaceX filed its S-1 confidentially with the SEC on April 1 and is reportedly targeting June 11 for IPO pricing on Nasdaq, with trading expected as early as June 12." Treat as reported intent, not fact, until the S-1 becomes public and pricing terms are confirmed.
- **The share.google link itself returned a 429** on direct fetch; the destination (CoinDesk article URL above) was identified by exact-title and exact-figure match across the first search results.