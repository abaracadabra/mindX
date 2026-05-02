# Uniswap V4 Integration Feedback — mindX trader

> Required artifact for **Best Uniswap API Integration** track (per ETHGlobal Open Agents qualification).
> Drafted during integration of `tools/uniswap_v4_tool.py` and `openagents/uniswap/demo_trader.py`
> against Sepolia testnet on 2026-04-27.

## Summary

mindX integrates Uniswap V4 as a tool a BDI-reasoning agent can use. The trader persona at `personas/trader.prompt` describes the deliberation contract; the tool exposes `quote / balance / swap / info` actions against the Sepolia V4 deployment. Below is the friction we encountered during integration.

## Things that worked well

- **Quoter V2 struct-based ABI** for `quoteExactInputSingle` is clean — fits a single Python ABI fragment without nested helper contracts.
- **PoolKey ordering rule** (`currency0 < currency1`) is well-documented; avoided ambiguous swap direction bugs.
- **Sepolia deployment manifest** at `https://docs.uniswap.org/contracts/v4/deployments` is comprehensive — we copied addresses straight in.

## Friction

### 1. V4 SDK is JavaScript-first; Python clients hand-roll calldata
- For the `swap` path we deferred to a JS SDK round-trip rather than encode V4 Universal Router commands manually. **Suggested:** publish a minimal Python SDK or at least a calldata-encoder helper (e.g. `uniswap-v4-codec` on PyPI).

### 2. Quoter requires `eth_call` with state override on some L2s
- On testnets we hit cases where vanilla `eth_call` reverted because pool state wasn't initialized. The V3 Quoter had a "simulate" path that gracefully returned 0; V4's revert behaviour is harder to differentiate ("uninitialized pool" vs "no liquidity at fee tier" vs "tick out of range"). **Suggested:** custom-error decoding examples in docs.

### 3. Hooks address default
- A `bytes20(0)` hooks address is implicitly "no hooks" but this isn't called out clearly in the V4 quoter docs. We had to infer it. **Suggested:** add an "if you don't use hooks, pass `address(0)`" note next to every `PoolKey` example.

### 4. Sepolia faucet rate-limiting
- For agentic systems that want to mint many fresh wallets and trade from each, the standard Sepolia faucet (1 ETH / 24h / address) is a bottleneck. Even a "Uniswap Sepolia builder faucet" tied to a GitHub OAuth would unblock multi-agent test scenarios.

### 5. Pool initialization ergonomics
- For a brand-new (token_in, token_out, fee, tickSpacing) tuple, callers must `PoolManager.initialize` first. The error path when this is missing is opaque (`PoolNotInitialized()` custom error). **Suggested:** add a top-level "first quote against this pair fails — here's why" troubleshooting box.

### 6. Subgraph parity for V4 lagged V3 on launch
- We considered a subgraph-driven candidate-trade discovery path but the Sepolia subgraph for V4 wasn't reliable at integration time (some queries returned stale state). **Suggested:** publish a status page for V4 subgraph indexers per network.

## Code references

- Tool: `tools/uniswap_v4_tool.py` (200 lines)
- Persona: `personas/trader.prompt`
- Demo: `openagents/uniswap/demo_trader.py`
- Decision log target: `data/logs/uniswap_decisions.jsonl`

## Contact

codephreak (Telegram: TBD, X: TBD) · github.com/Professor-Codephreak/mindX
