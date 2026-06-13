# DELTAVERSE Debt Inheritance Protocol — Frontend Integration Specification

**Target:** `agenticplace.pythai.net`
**Protocol Version:** v1 (five-contract stack)
**Stack:** TypeScript + viem + wagmi + Next.js
**Chain Support:** via `allchain.html` chain mapping convention

---

## 1. Architecture Overview

The `agenticplace.pythai.net` frontend integrates with the five-contract DELTAVERSE stack through a single unified entry point: `DebtInheritanceProtocol`. This capstone contract orchestrates the four underlying primitives, so the UI does not need to interact with each contract independently for the primary user flows.

```
┌──────────────────────────────────────────────────────────────┐
│              agenticplace.pythai.net (Next.js)               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  useDeltaVerseDebtProtocol() — React Hook              │  │
│  │  ├─ mintSGdsi()    — passive long on debt stress       │  │
│  │  ├─ burnSGdsi()    — close passive position            │  │
│  │  ├─ expressThesis()  — leveraged recursive inheritance │  │
│  │  ├─ closeThesis()    — atomic unwind                   │  │
│  │  └─ routeFees()      — keeper-callable reward loop     │  │
│  └────────────────────────────────────────────────────────┘  │
│                              │                                │
│                              ▼                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  DebtInheritanceProtocol.sol (on-chain)                │  │
│  └────────────────────────────────────────────────────────┘  │
│       │           │               │              │           │
│       ▼           ▼               ▼              ▼           │
│   RWAToken   CrossCollat    PerpetualEngine    Oracle        │
│               Vault                           (GDSI)         │
└──────────────────────────────────────────────────────────────┘
```

Supporting integrations per DELTAVERSE ecosystem conventions:

- **mindX.pythai.net API** — consciousness-vector scoring for trader risk profiling
- **bankon.pythai.net** — BANKON AlgoIDNFT sovereign identity for KYC-gated RWA access
- **agenticplace.pythai.net/allchain.html** — multi-chain address mapping registry

---

## 2. Chain Mapping (allchain.html Convention)

The frontend reads deployment addresses from a canonical chain mapping file. This allows the same UI to serve multiple chains without hard-coding.

**`/public/allchain.json`** — Canonical chain mapping:

```json
{
  "version": "1.0",
  "protocol": "DebtInheritanceProtocol",
  "chains": {
    "1": {
      "name": "Ethereum Mainnet",
      "stablecoin": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "pyth": "0x4305FB66699C3B2702D4d05CF36551390A4c69C6",
      "contracts": {
        "rwa": "",
        "oracle": "",
        "vault": "",
        "perp": "",
        "protocol": ""
      }
    },
    "137": {
      "name": "Polygon",
      "stablecoin": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
      "pyth": "0xff1a0f4744e8582DF1aE09D5611b887B6a12925C",
      "contracts": { "rwa": "", "oracle": "", "vault": "", "perp": "", "protocol": "" }
    },
    "8453": {
      "name": "Base",
      "stablecoin": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "pyth": "0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a",
      "contracts": { "rwa": "", "oracle": "", "vault": "", "perp": "", "protocol": "" }
    },
    "42161": {
      "name": "Arbitrum One",
      "stablecoin": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
      "pyth": "0xff1a0f4744e8582DF1aE09D5611b887B6a12925C",
      "contracts": { "rwa": "", "oracle": "", "vault": "", "perp": "", "protocol": "" }
    }
  }
}
```

**TypeScript loader:**

```typescript
// lib/chainmap.ts
import { getChainId } from 'wagmi/actions';

export interface ChainDeployment {
  name: string;
  stablecoin: `0x${string}`;
  pyth: `0x${string}`;
  contracts: {
    rwa: `0x${string}`;
    oracle: `0x${string}`;
    vault: `0x${string}`;
    perp: `0x${string}`;
    protocol: `0x${string}`;
  };
}

export async function loadChainDeployment(chainId: number): Promise<ChainDeployment> {
  const response = await fetch('/allchain.json');
  const mapping = await response.json();
  const deployment = mapping.chains[String(chainId)];
  if (!deployment) {
    throw new Error(`Chain ${chainId} not supported in allchain.json`);
  }
  return deployment;
}
```

---

## 3. Contract ABIs

Only the capstone ABI is required for primary flows. Sub-contract ABIs are used for read-only views (oracle price feeds, vault health, perp equity).

```typescript
// lib/abis/debtInheritanceProtocol.ts
export const debtInheritanceProtocolAbi = [
  // ── Writes ──
  { name: 'mintSGdsi', type: 'function', stateMutability: 'nonpayable',
    inputs: [
      { name: 'stableAmount', type: 'uint256' },
      { name: 'minSGdsiOut', type: 'uint256' }
    ],
    outputs: [{ name: 'sGdsiOut', type: 'uint256' }]
  },
  { name: 'burnSGdsi', type: 'function', stateMutability: 'nonpayable',
    inputs: [
      { name: 'sGdsiAmount', type: 'uint256' },
      { name: 'minStableOut', type: 'uint256' }
    ],
    outputs: [{ name: 'stableOut', type: 'uint256' }]
  },
  { name: 'expressThesis', type: 'function', stateMutability: 'nonpayable',
    inputs: [
      { name: 'rwaToken', type: 'address' },
      { name: 'rwaAmount', type: 'uint256' },
      { name: 'borrowAmount', type: 'uint256' },
      { name: 'leverage', type: 'uint256' },
      { name: 'isLong', type: 'bool' }
    ],
    outputs: []
  },
  { name: 'closeThesis', type: 'function', stateMutability: 'nonpayable',
    inputs: [],
    outputs: [
      { name: 'perpPnl', type: 'int256' },
      { name: 'stableReturned', type: 'uint256' }
    ]
  },
  { name: 'routeFees', type: 'function', stateMutability: 'nonpayable',
    inputs: [], outputs: []
  },
  // ── Reads ──
  { name: 'balanceOf', type: 'function', stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ type: 'uint256' }]
  },
  { name: 'hasActiveThesis', type: 'function', stateMutability: 'view',
    inputs: [{ name: 'user', type: 'address' }],
    outputs: [{ type: 'bool' }]
  },
  { name: 'thesisPnLBps', type: 'function', stateMutability: 'view',
    inputs: [{ name: 'user', type: 'address' }],
    outputs: [{ type: 'int256' }]
  },
  { name: 'sGdsiRedemptionValue', type: 'function', stateMutability: 'view',
    inputs: [], outputs: [{ type: 'uint256' }]
  },
  { name: 'collateralizationRatio', type: 'function', stateMutability: 'view',
    inputs: [], outputs: [{ type: 'uint256' }]
  },
  { name: 'currentStressLevel', type: 'function', stateMutability: 'view',
    inputs: [], outputs: [{ type: 'uint8' }]
  },
  { name: 'pendingFees', type: 'function', stateMutability: 'view',
    inputs: [], outputs: [{ type: 'uint256' }]
  },
  { name: 'thesisPositions', type: 'function', stateMutability: 'view',
    inputs: [{ type: 'address' }],
    outputs: [
      { name: 'rwaCollateral', type: 'address' },
      { name: 'rwaAmount', type: 'uint256' },
      { name: 'borrowedStable', type: 'uint256' },
      { name: 'perpCollateral', type: 'uint256' },
      { name: 'openedAt', type: 'uint256' },
      { name: 'openRoundId', type: 'uint256' },
      { name: 'openIndexValue', type: 'uint256' },
      { name: 'isLong', type: 'bool' },
      { name: 'leverage', type: 'uint256' },
      { name: 'active', type: 'bool' }
    ]
  },
] as const;
```

---

## 4. Primary User Flows

### 4.1 Mint sGDSI (Passive Long on Debt Stress)

```typescript
// hooks/useMintSGdsi.ts
import { useWriteContract, useReadContract } from 'wagmi';
import { parseUnits, formatUnits } from 'viem';

export function useMintSGdsi(deployment: ChainDeployment) {
  const { writeContractAsync } = useWriteContract();

  const mint = async (usdcAmount: string, slippageBps: number = 50) => {
    const stableAmount = parseUnits(usdcAmount, 6);  // USDC is 6 decimals

    // 1. Quote the mint to compute minOut for slippage protection
    const price = await readContract(config, {
      address: deployment.contracts.oracle,
      abi: debtOracleAbi,
      functionName: 'latestPrice',
    });
    const expectedOut = (stableAmount * 1000n * 10n**18n) / (price[0] * 10n**6n);
    const minOut = (expectedOut * (10000n - BigInt(slippageBps))) / 10000n;

    // 2. Approve USDC spend
    await writeContractAsync({
      address: deployment.stablecoin,
      abi: erc20Abi,
      functionName: 'approve',
      args: [deployment.contracts.protocol, stableAmount],
    });

    // 3. Execute mint
    const hash = await writeContractAsync({
      address: deployment.contracts.protocol,
      abi: debtInheritanceProtocolAbi,
      functionName: 'mintSGdsi',
      args: [stableAmount, minOut],
    });

    return hash;
  };

  return { mint };
}
```

### 4.2 Express Full Thesis (Leveraged Recursive Inheritance)

```typescript
// hooks/useExpressThesis.ts
export function useExpressThesis(deployment: ChainDeployment) {
  const { writeContractAsync } = useWriteContract();

  const expressThesis = async ({
    rwaAmount,       // string, e.g. "1000" (1000 RWA tokens)
    borrowAmount,    // string, e.g. "50000" (50k USDC)
    leverage,        // number, e.g. 5 (5x)
    isLong,          // boolean, true = thesis bet (rising stress)
  }: ExpressThesisParams) => {
    // 1. Approve RWA spend
    const rwaWei = parseUnits(rwaAmount, 18);
    await writeContractAsync({
      address: deployment.contracts.rwa,
      abi: erc20Abi,
      functionName: 'approve',
      args: [deployment.contracts.protocol, rwaWei],
    });

    // 2. Execute the recursive thesis
    const hash = await writeContractAsync({
      address: deployment.contracts.protocol,
      abi: debtInheritanceProtocolAbi,
      functionName: 'expressThesis',
      args: [
        deployment.contracts.rwa,
        rwaWei,
        parseUnits(borrowAmount, 6),
        BigInt(leverage),
        isLong,
      ],
    });

    return hash;
  };

  return { expressThesis };
}
```

### 4.3 Live Thesis Position Monitoring

```typescript
// hooks/useThesisPosition.ts
export function useThesisPosition(userAddress: `0x${string}`, deployment: ChainDeployment) {
  const { data: position } = useReadContract({
    address: deployment.contracts.protocol,
    abi: debtInheritanceProtocolAbi,
    functionName: 'thesisPositions',
    args: [userAddress],
    query: { refetchInterval: 5000 },  // poll every 5s
  });

  const { data: pnlBps } = useReadContract({
    address: deployment.contracts.protocol,
    abi: debtInheritanceProtocolAbi,
    functionName: 'thesisPnLBps',
    args: [userAddress],
    query: { refetchInterval: 5000 },
  });

  const { data: stressLevel } = useReadContract({
    address: deployment.contracts.protocol,
    abi: debtInheritanceProtocolAbi,
    functionName: 'currentStressLevel',
    query: { refetchInterval: 15000 },
  });

  return {
    position,
    pnlPercent: pnlBps ? Number(pnlBps) / 100 : 0,
    stressLevel: STRESS_LEVELS[Number(stressLevel ?? 0)],
    isActive: position?.[9] ?? false,
  };
}

export const STRESS_LEVELS = [
  'Low',        // 0
  'Moderate',   // 1
  'Elevated',   // 2
  'High',       // 3
  'Critical',   // 4
  'Systemic',   // 5
];
```

---

## 5. Keeper Automation

Two keeper jobs are required for protocol operation. These should run on dedicated infrastructure (not the frontend).

### 5.1 Pyth Price Update Keeper

```typescript
// keeper/pythUpdater.ts
import { HermesClient } from '@pythnetwork/hermes-client';
import { privateKeyToAccount } from 'viem/accounts';

const hermes = new HermesClient('https://hermes.pyth.network');

async function updatePythFeeds() {
  // Fetch price updates for all sub-index feed IDs
  const priceIds = [
    '0x...',  // SDR sub-index Pyth feed
    '0x...',  // YSI sub-index Pyth feed
    // ... etc
  ];

  const priceUpdates = await hermes.getLatestPriceUpdates(priceIds);

  // Calculate required fee
  const fee = await publicClient.readContract({
    address: deployment.contracts.oracle,
    abi: debtOracleAbi,
    functionName: 'getUpdateFee',
    args: [priceUpdates.binary.data],
  });

  // Submit update with fee
  const hash = await walletClient.writeContract({
    address: deployment.contracts.oracle,
    abi: debtOracleAbi,
    functionName: 'updatePythFeeds',
    args: [priceUpdates.binary.data],
    value: fee,
  });

  console.log('Pyth feeds updated:', hash);
}

// Run every 60 seconds
setInterval(updatePythFeeds, 60_000);
```

### 5.2 Fee Routing Keeper

```typescript
// keeper/feeRouter.ts
async function routeFees() {
  const pending = await publicClient.readContract({
    address: deployment.contracts.protocol,
    abi: debtInheritanceProtocolAbi,
    functionName: 'pendingFees',
  });

  // Only route when pending fees exceed gas cost threshold
  if (pending < 100_000_000n) return;  // < 100 USDC

  await walletClient.writeContract({
    address: deployment.contracts.protocol,
    abi: debtInheritanceProtocolAbi,
    functionName: 'routeFees',
  });
}

setInterval(routeFees, 3600_000);  // hourly
```

### 5.3 Sub-Index Finalization Keeper

```typescript
// keeper/subIndexFinalizer.ts
async function finalizeAllSubIndices() {
  for (let i = 0; i < 5; i++) {
    try {
      await walletClient.writeContract({
        address: deployment.contracts.oracle,
        abi: debtOracleAbi,
        functionName: 'finalizeSubIndex',
        args: [i],
      });
    } catch (e) {
      console.log(`Sub-index ${i} skipped:`, e);
    }
  }

  // Then update composite
  await walletClient.writeContract({
    address: deployment.contracts.oracle,
    abi: debtOracleAbi,
    functionName: 'updateComposite',
  });
}

setInterval(finalizeAllSubIndices, 4 * 3600_000);  // every 4 hours
```

---

## 6. DELTAVERSE Ecosystem Integration

### 6.1 mindX Risk Scoring (mindx.pythai.net API)

Before allowing high-leverage thesis expression, the UI queries the mindX API to score the trader's consciousness vector against a risk profile. This leverages the existing mindX infrastructure.

```typescript
// lib/mindx.ts
export async function scoreMindXRiskProfile(walletAddress: string) {
  const response = await fetch(`https://mindx.pythai.net/api/v1/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      wallet: walletAddress,
      context: 'debt_inheritance_leverage',
    }),
  });
  const { alignmentScore, riskCategory, maxLeverage } = await response.json();

  return {
    alignmentScore,    // 0-1000 mindX alignment
    riskCategory,      // 'conservative' | 'balanced' | 'aggressive'
    maxLeverage,       // recommended max leverage based on profile
  };
}
```

### 6.2 BANKON Identity Gating

For tokenized RWA access, the UI checks BANKON AlgoIDNFT sovereign identity. Users without verified KYC credentials are restricted to sGDSI mint/burn (non-KYC-gated), while `expressThesis()` requires full identity verification.

```typescript
// lib/bankon.ts
export async function verifyBankonIdentity(walletAddress: string) {
  const response = await fetch(`https://bankon.pythai.net/api/v1/identity/${walletAddress}`);
  const { hasValidCredential, credentialTypes, jurisdictionAllowed } = await response.json();

  return {
    canExpressThesis: hasValidCredential &&
                       credentialTypes.includes('accredited_investor') &&
                       jurisdictionAllowed,
    canMintSGdsi: hasValidCredential,
  };
}
```

---

## 7. UI Components Reference

Minimum component inventory for the debt inheritance dashboard:

- **GDSIStressGauge** — circular gauge showing current stress level (0-5) with color coding
- **IndexHistoryChart** — recharts line chart of `getRecentSnapshots()` data
- **MintBurnPanel** — sGDSI mint/burn form with live quote
- **ThesisExpressionWizard** — multi-step form for `expressThesis()` with risk profiling
- **ThesisPositionCard** — live PnL display with unwind button
- **OracleHealthPanel** — sub-index status, Pyth freshness, heartbeat indicator
- **LPStakingPanel** — stake USDC into oracle LP pool, claim rewards
- **FeeRoutingMonitor** — displays `pendingFees` and manual route trigger

---

## 8. Security Considerations

1. **Always validate chain ID** against `allchain.json` before prompting signatures. Users connected to the wrong chain should see a "Switch Network" prompt, not a broken flow.

2. **Quote before executing** — for every mint/burn/thesis call, fetch the current oracle price and compute expected outputs client-side. Pass a slippage-adjusted `minOut` to protect against front-running and oracle jitter.

3. **Staleness checks** — before showing the UI as "tradeable", call `oracle.isHeartbeatAlive()`. If false, display a warning banner and disable write functions.

4. **Circuit breaker state** — poll `oracle.hasPendingUpdate()` and display a notice when governor review is pending. Trading should continue on the prior accepted value.

5. **BANKON identity cache** — cache identity verification results for 1 hour maximum. Never cache the wallet's private credentials or PII.

6. **mindX score expiry** — re-query mindX risk scoring before each high-leverage operation (>5x). Scores older than 24 hours should be treated as stale.

---

## 9. Deployment Checklist

Before pointing `agenticplace.pythai.net` at a new chain deployment:

- [ ] All 5 contracts deployed and verified on block explorer
- [ ] Contract addresses populated in `allchain.json`
- [ ] RWAToken supply minted and distributed to test accounts
- [ ] Vault reserves seeded with stablecoin
- [ ] PerpetualEngine insurance fund initialized
- [ ] Oracle sub-indices seeded to baseline (1000)
- [ ] `updateComposite()` called to initialize GDSI
- [ ] Pyth feed IDs configured for each sub-index (if using Pyth)
- [ ] Chainlink feeds configured for each sub-index (if using Chainlink)
- [ ] Keeper infrastructure running (Pyth updates, fee routing, sub-index finalization)
- [ ] BANKON identity API connected and tested
- [ ] mindX scoring API connected and tested
- [ ] Frontend E2E test suite passing against deployment
- [ ] Monitoring dashboards configured (Grafana / Tenderly)
- [ ] Emergency pause role assigned to multi-sig

---

**End of Frontend Integration Specification**

*The thesis is executable. The frontend makes it accessible. Deploy and inherit.*
