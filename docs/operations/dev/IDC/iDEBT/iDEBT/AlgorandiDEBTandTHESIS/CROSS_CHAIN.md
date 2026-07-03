# Cross-Chain Architecture: Algorand ↔ EVM via Wormhole

## Overview

The DELTAVERSE protocol spans two chains. Algorand hosts the RWA tokenization, compliance infrastructure, and oracle measurement layer. EVM chains (Ethereum, Polygon, Arbitrum, Base) host the derivatives infrastructure — the inverse debt token (iDEBT), perpetual engine, and the full `expressThesis()` flow. The Wormhole messaging protocol bridges the two.

## Why Two Chains

Algorand leads in production RWA tokenization. BlackRock's BUIDL fund, Ondo Finance, and Centrifuge all deploy on or bridge through Algorand. The chain's native ASA freeze/clawback primitives make compliance enforcement cheaper and more reliable than EVM's override-every-transfer approach. The DELTAVERSE compliance stack (AlgoIDNFT, BONAFIDE, DAIO, x402) already exists on Algorand.

EVM leads in DeFi composability. The deepest liquidity, the most battle-tested oracle infrastructure (Chainlink, Pyth), and the largest developer ecosystem are all on EVM chains. The iDEBT derivatives layer requires deep stablecoin liquidity for mint/burn and composability with existing DeFi protocols (Uniswap, Aave, Curve) for secondary market trading.

The bridge connects the strength of each chain: Algorand's RWA and compliance infrastructure feeds collateral to EVM's derivatives infrastructure.

## Wormhole Security Model

Wormhole uses a guardian set of 19 institutional validators. A supermajority of 13-of-19 must sign any cross-chain message (Verifiable Action Approval, or VAA) for it to be honored on the destination chain. The guardians include Jump Crypto, Certus One, Chorus One, and other major crypto infrastructure operators.

This is the same trust model used by Circle's Cross-Chain Transfer Protocol (CCTP) for USDC bridging and by Centrifuge for RWA cross-chain operations. The alternative — a light-client-based bridge like zkBridge — is more trust-minimized but still immature for production RWA volumes where regulatory confidence in the bridge operator matters.

## Bridge-Out Flow (Algorand → EVM)

```
User                    Algorand Bridge         Wormhole Guardians      EVM Receiver
  |                          |                        |                      |
  |-- atomic group --------->|                        |                      |
  |   (AssetTransfer +       |                        |                      |
  |    bridge_out call)      |                        |                      |
  |                          |-- lock ASA ----------->|                      |
  |                          |-- emit VAA payload --->|                      |
  |                          |   (chain=8, asset,     |                      |
  |                          |    amount, dest=2,     |                      |
  |                          |    recipient)          |                      |
  |                          |                        |-- 13/19 sign ------->|
  |                          |                        |                      |
  |                          |                        |   Relayer submits    |
  |                          |                        |   signed VAA         |
  |                          |                        |                      |
  |                          |                        |      receiveAndMint()|
  |                          |                        |-- verify signatures->|
  |                          |                        |                      |-- check epoch
  |                          |                        |                      |-- check replay
  |                          |                        |                      |-- mint wrapped
  |                          |                        |                      |   ERC-20 RWA
  |<--------------------- wrapped RWA in EVM wallet -------------------------|
```

## Bridge-In Flow (EVM → Algorand)

```
User                    EVM Receiver            Wormhole Guardians      Algorand Bridge
  |                          |                        |                      |
  |-- burnAndBridge() ------>|                        |                      |
  |   (amount, algo_recip)   |                        |                      |
  |                          |-- burn ERC-20 -------->|                      |
  |                          |-- emit Wormhole msg -->|                      |
  |                          |                        |-- 13/19 sign ------->|
  |                          |                        |                      |
  |                          |                        |   Relayer submits    |
  |                          |                        |   signed VAA         |
  |                          |                        |                      |
  |                          |                        |      bridge_in()     |
  |                          |                        |                      |-- verify VAA
  |                          |                        |                      |-- check epoch
  |                          |                        |                      |-- check replay
  |                          |                        |                      |-- unlock ASA
  |<--------------------- original ASA in Algorand wallet -------------------|
```

## Rate Limiting

Both the Algorand bridge and the EVM receiver enforce per-asset 24-hour epoch transfer limits. The limits are set by governance and refresh automatically when the epoch window expires. If the cumulative bridged amount for an asset exceeds the epoch limit, further bridge operations revert until the next epoch.

This prevents a full-drain scenario in the event that the Wormhole guardian set is compromised. Even with all 19 guardians colluding, the maximum extractable value per 24-hour period is bounded by the epoch limit.

## Replay Protection

Every consumed VAA hash is recorded in a BoxMap (Algorand) or mapping (EVM). Attempting to submit the same VAA twice reverts immediately. The hash is the Wormhole-standard keccak256 of the VAA body, which includes the sequence number, emitter chain, emitter address, and payload. This makes replay attacks impossible even if the relayer resubmits.

## Chain IDs

| Chain      | Wormhole ID |
|------------|-------------|
| Algorand   | 8           |
| Ethereum   | 2           |
| Polygon    | 5           |
| Arbitrum   | 23          |
| Base       | 30          |

## Integration with iDEBT

After receiving wrapped RWA on EVM via the bridge, the user deposits it into the `CrossCollateralVault` as collateral. From there, the standard EVM flow applies: borrow stablecoin, mint iDEBT via `InverseDebtToken`, and hold the position as the debasement index tracks the global fiat-vs-BTC basket. The wrapped RWA token is registered as a collateral type in the vault with its own LTV, liquidation threshold, and price feed configuration.

The full end-to-end flow — from sovereign debt instrument tokenized on Algorand to inverse debt exposure on EVM measured against a global currency basket — is the complete instantiation of the thesis. The debt system is used as fuel to short itself, across chains, with compliance enforced at every step.
