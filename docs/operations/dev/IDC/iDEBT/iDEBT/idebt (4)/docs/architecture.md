# iDEBT Architecture

```
                                      ┌────────────────────────────┐
                                      │        DAIO (Governor)     │
                                      │  ┌──────────────────────┐  │
                                      │  │   DAIOTreasury       │  │
                                      │  │  (TimelockController)│  │
                                      │  └──────────┬───────────┘  │
                                      └─────────────┼──────────────┘
                                                    │ admin role on all
                        ┌───────────────────────────┼───────────────────────────┐
                        ▼                           ▼                           ▼
         ┌──────────────────────┐   ┌───────────────────────┐   ┌────────────────────┐
         │ DeltaVerseDebtOracle │   │ GlobalDebtStressIndex │   │ iDEBT (ERC-721)    │
         │ (blended adapters)   │──▶│ (weighted 7-metric)   │──▶│ mark-to-market     │
         └──────────┬───────────┘   └───────────────────────┘   │ heirs (Merkle)     │
                    │                                           │ heartbeat/dormancy │
         ┌──────────┼──────────┐                                └─┬──────────────────┘
         ▼          ▼          ▼                                  │
 ┌──────────┐ ┌──────────┐ ┌──────────┐                           │ settlement (USDC)
 │Chainlink │ │Pyth      │ │SnxV3     │                           ▼
 │Adapter   │ │Adapter   │ │Adapter   │                  ┌──────────────────┐
 └──────────┘ └──────────┘ └──────────┘                  │ DAIOTreasury     │
                                                         │ protocol reserve │
  off-chain:                                             └──────────────────┘
    mindX (mindx.pythai.net)   ───▶  MindXBridge.settle (EIP-712 attestation)
    AgenticPlace (agenticplace.pythai.net) ───▶ AgenticPlaceRegistry (BONAFIDE rep)
    BANKON (bankon.pythai.net) ───▶  BANKONConnector.bind (AlgoIDNFT → EVM)
    Parsec x402 (parsec.finance)     ───▶ X402PaymentGateway.consume
```

## Deployment topology per chain

Each supported chain runs the full stack independently. There is no
cross-chain bridge in v0.1; sovereign identity (BANKON) and agent identity
(AgenticPlace) serve as the shared coordination layer.

## State ownership

| Contract                    | State controlled                                  |
| --------------------------- | ------------------------------------------------- |
| `DeltaVerseDebtOracle`      | adapter registry, source ids, confidence floor    |
| `GlobalDebtStressIndex`     | weights, thresholds, last snapshot                |
| `iDEBT`                     | positions, heir roots, claimed leaves, settlement |
| `X402PaymentGateway`        | facilitators, scope prices, used nonces, paidUntil|
| `MindXBridge`               | signing key, consumed requestIds, last scores     |
| `AgenticPlaceRegistry`      | agents, reputation, decay bps                     |
| `BANKONConnector`           | bindings, root→owner, bankonSigner                |
| `DAIO` + `DAIOTreasury`     | proposals, votes, queued ops                      |
| `iDEBTVoteToken`            | voting balances, delegations, checkpoints         |
