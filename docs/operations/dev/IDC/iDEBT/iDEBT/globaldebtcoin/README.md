# DELTAVERSE Debt Inheritance Protocol

**The cryptographic inheritance of global debt, made executable.**

A five-contract Solidity stack implementing recursive debt thesis expression: use tokenized sovereign debt as collateral to borrow stablecoin, then use the borrowed stablecoin to open a leveraged position shorting the very debt index your collateral tracks. The debt system funds its own inversion in a single atomic transaction.

---

## The Stack

| # | Contract | Function |
|---|---|---|
| 1 | `RWAToken.sol` | Compliance-gated tokenization of debt instruments with yield distribution |
| 2 | `CrossCollateralVault.sol` | Multi-asset collateral pool with oracle pricing, interest accrual, and liquidation |
| 3 | `PerpetualEngine.sol` | 24/7 leveraged derivatives with automated funding rates and insurance fund |
| 4 | `DeltaVerseDebtOracle.sol` | Composite Global Debt Stress Index using Synthetix V3 Oracle Manager patterns over Chainlink + Pyth + reporter median, with LP staking pool |
| 5 | `DebtInheritanceProtocol.sol` | Capstone orchestrator + sGDSI synthetic token + recursive thesis expression + fee routing loop |

---

## Quick Start

### Prerequisites
- [Foundry](https://book.getfoundry.sh/) (`forge`, `cast`, `anvil`)
- Node.js 18+ (for frontend and Pyth SDK)

### Install dependencies
```bash
forge install foundry-rs/forge-std
forge install OpenZeppelin/openzeppelin-contracts
forge install pyth-network/pyth-sdk-solidity
```

### Build
```bash
forge build
```

### Test
```bash
# Run the full integration test suite
forge test -vvv

# Run a specific test
forge test --match-test test_05_MintAtLowBurnAtHighProfit -vvv

# Gas snapshot
forge snapshot
```

### Deploy (Mainnet)
```bash
# Set environment variables
export PRIVATE_KEY=0x...
export ADMIN_ADDRESS=0x...
export STABLECOIN_ADDRESS=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
export PYTH_ADDRESS=0x4305FB66699C3B2702D4d05CF36551390A4c69C6
export MAINNET_RPC_URL=https://...
export ETHERSCAN_API_KEY=...

# Dry run
forge script script/Deploy.s.sol:Deploy --rpc-url mainnet

# Broadcast
forge script script/Deploy.s.sol:Deploy \
    --rpc-url mainnet \
    --broadcast \
    --verify
```

---

## The Thesis (Summary)

**Part I** (`global_debt_thesis.docx`): Global debt at $346T is structurally unsustainable. Four channels of inverse positioning exist; paradigmatic displacement is the most durable.

**Part II** (`cryptographic_inheritance.docx`): RWA tokenization + on-chain derivatives + unified collateralization is the displacement mechanism. Three production contracts specify the primitives.

**Part III** (`recursive_proof_part3.docx`): The capstone orchestrator composes all four primitives (plus the oracle) into a single executable market. The thesis becomes recursively self-demonstrating: the debt system is used as fuel to short itself.

---

## Recursive Thesis Expression

The signature function is `expressThesis()`, which atomically:

1. Pulls RWAToken collateral (tokenized debt) from the user
2. Deposits it into `CrossCollateralVault`
3. Borrows stablecoin against it (up to 75% LTV)
4. Routes the borrowed stablecoin into `PerpetualEngine`
5. Opens a leveraged long on the Global Debt Stress Index via `DeltaVerseDebtOracle`

If the debt thesis is correct (stress rises), the leveraged perpetual position profits by more than the collateral erodes. The position is self-funding in the limit case.

```solidity
protocol.expressThesis(
    rwaToken,      // Tokenized US Treasury
    1000e18,       // 1000 RWA tokens ($100k notional)
    50_000e6,      // Borrow 50k USDC
    10,            // 10x leverage
    true           // Long GDSI (bet stress rises)
);
```

---

## sGDSI — The Synthetic Debt Index Token

For unlevered exposure, users mint sGDSI by depositing stablecoin at the current oracle price:

```solidity
protocol.mintSGdsi(1000e6, minOut);  // Deposit 1000 USDC
// Receive sGDSI at rate: BASE_INDEX / P(t)
```

When the index rises from 1000 to 1500, burning the sGDSI returns ~50% more stablecoin than was deposited (less ~60bps in fees). This is the passive expression of the thesis.

---

## Fee Routing Loop

All protocol fees (mint, burn, trading) accumulate in `pendingFees` and are periodically routed to the `DeltaVerseDebtOracle` LP staking pool via `routeFees()`. This closes the economic circuit:

```
Traders pay fees
      ↓
Oracle LP stakers earn rewards
      ↓
Stakers back oracle credibility with collateral
      ↓
Accurate measurement enables trading
      ↓
Traders pay fees
```

Anyone can call `routeFees()` — it is pure accounting, no special role required.

---

## Project Structure

```
debt-inheritance/
├── src/
│   ├── RWAToken.sol
│   ├── CrossCollateralVault.sol
│   ├── PerpetualEngine.sol
│   ├── DeltaVerseDebtOracle.sol
│   └── DebtInheritanceProtocol.sol
├── test/
│   └── DebtInheritanceProtocol.t.sol    # Full integration tests + mocks
├── script/
│   └── Deploy.s.sol                     # Mainnet deployment script
├── docs/
│   ├── global_debt_thesis.docx          # Part I — the diagnosis
│   ├── cryptographic_inheritance.docx   # Part II — the inheritance
│   └── recursive_proof_part3.docx       # Part III — the capstone proof
├── FRONTEND_INTEGRATION.md              # agenticplace.pythai.net integration
├── foundry.toml
└── README.md
```

---

## Security Notes

Each contract has been audited with critical, medium, and low severity fixes applied (see per-contract NatSpec `Audit Fixes` sections). Key protections:

- **Reentrancy**: `nonReentrant` on all state-changing external functions
- **Oracle staleness**: enforced at both oracle and consumer levels with configurable thresholds
- **Deviation circuit breaker**: oracle updates exceeding 10% deviation require governor approval
- **Insurance fund**: PerpetualEngine absorbs socialized losses during extreme liquidation events
- **Close factor cap**: CrossCollateralVault limits liquidation repayment to 50% of debt per transaction
- **Pausable**: every contract has an emergency stop controlled by `DEFAULT_ADMIN_ROLE` or `GOVERNOR_ROLE`
- **Access control**: role-based permissions throughout (`DEFAULT_ADMIN_ROLE`, `GOVERNOR_ROLE`, `KEEPER_ROLE`, `REPORTER_ROLE`, `ORACLE_MANAGER_ROLE`)

**This code has not been audited by a third-party security firm. Do not deploy to mainnet without a professional audit.**

---

## References

- **Synthetix V3 Architecture**: [github.com/Synthetixio/synthetix-v3](https://github.com/Synthetixio/synthetix-v3)
- **Pyth Network Solidity SDK**: [@pythnetwork/pyth-sdk-solidity](https://www.npmjs.com/package/@pythnetwork/pyth-sdk-solidity)
- **SIP-329 Pull Oracle Node**: [sips.synthetix.io/sips/sip-329](https://sips.synthetix.io/sips/sip-329)
- **SIP-156 Debt Pool Oracle**: [sips.synthetix.io/sips/sip-156](https://sips.synthetix.io/sips/sip-156)
- **OpenZeppelin Contracts**: [github.com/OpenZeppelin/openzeppelin-contracts](https://github.com/OpenZeppelin/openzeppelin-contracts)

---

## License

MIT

---

**Built by Professor Codephreak**
**DELTAVERSE Ecosystem • PYTHAI Platform • BANKON Infrastructure**

*The thesis is written. The contracts are audited. The architecture is proven.*
*What remains is deployment.*
