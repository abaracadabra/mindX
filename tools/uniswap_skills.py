"""Uniswap AI Skills — agent-callable handler for all 8 official skills.

Mirrors the skill registry at https://developers.uniswap.org/docs/uniswap-ai/skills
in a structured way so both:
  (a) The mindX BDI trader can invoke skills programmatically (agent path)
  (b) The /uniswap UI can offer a "Run skill" button per skill (human path)

Skills come in two flavors:

  1. DETERMINISTIC skills — we can fully implement them server-side because
     they produce structured output (URLs, code, calldata, checklists):
       - swap-planner          → app.uniswap.org/swap deep link
       - liquidity-planner     → app.uniswap.org/positions deep link
       - pay-with-any-token    → trade-api quote in EXACT_OUTPUT mode
       - swap-integration      → Python/TS code snippets
       - viem-integration      → viem TS scaffolding
       - v4-security-foundations → curated hook security checklist

  2. AGENT-FIRST skills — these are designed for an LLM session (Claude Code,
     Cursor) and produce free-form prose. Server-side we return a "skill
     manifest" envelope: {plugin, invocation, install_cmd, description, slot
     definitions} that an agent (or the UI) consumes.
       - configurator (CCA auction params)
       - deployer (CCA factory deployment)

The CLI invocation `npx skills add Uniswap/uniswap-ai` installs them into a
Claude Code / Cursor environment for `/<skill-name>` slash invocation; this
module is mindX's own implementation so the BDI trader can use the same
surface without an external Claude Code session.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


# ─── Catalog ───────────────────────────────────────────────────────────
SKILLS: List[Dict[str, Any]] = [
    {
        "name": "swap-integration",
        "plugin": "uniswap-trading",
        "invocation": "/swap-integration",
        "description": "Integrate swaps using the Uniswap API, Universal Router, or direct smart contract calls",
        "category": "trading",
        "actionable": True,
    },
    {
        "name": "swap-planner",
        "plugin": "uniswap-driver",
        "invocation": "/swap-planner",
        "description": "Plan token swaps and generate interface deep links",
        "category": "trading",
        "actionable": True,
    },
    {
        "name": "liquidity-planner",
        "plugin": "uniswap-driver",
        "invocation": "/liquidity-planner",
        "description": "Plan LP positions and generate interface deep links",
        "category": "liquidity",
        "actionable": True,
    },
    {
        "name": "pay-with-any-token",
        "plugin": "uniswap-trading",
        "invocation": "/pay-with-any-token",
        "description": "Pay HTTP 402 challenges (x402 and MPP) using tokens via Uniswap swaps",
        "category": "trading",
        "actionable": True,
    },
    {
        "name": "viem-integration",
        "plugin": "uniswap-viem",
        "invocation": "/viem-integration",
        "description": "Set up EVM clients and contract interactions with viem and wagmi",
        "category": "dev",
        "actionable": True,
    },
    {
        "name": "v4-security-foundations",
        "plugin": "uniswap-hooks",
        "invocation": "/v4-security-foundations",
        "description": "Review v4 hook architecture and security risks before implementation",
        "category": "security",
        "actionable": True,
    },
    {
        "name": "configurator",
        "plugin": "uniswap-cca",
        "invocation": "/configurator",
        "description": "Configure CCA auction parameters for a new deployment",
        "category": "deployment",
        "actionable": False,
    },
    {
        "name": "deployer",
        "plugin": "uniswap-cca",
        "invocation": "/deployer",
        "description": "Deploy CCA contracts using the factory deployment pattern",
        "category": "deployment",
        "actionable": False,
    },
]
SKILL_BY_NAME = {s["name"]: s for s in SKILLS}

INSTALL_CMD = "npx skills add Uniswap/uniswap-ai"

# ─── Constants ─────────────────────────────────────────────────────────
INTERFACE_BASE = "https://app.uniswap.org"
CHAIN_NAME = {1: "mainnet", 8453: "base", 42161: "arbitrum", 10: "optimism", 137: "polygon"}


# ─── Skill: swap-planner ───────────────────────────────────────────────
def run_swap_planner(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate an app.uniswap.org/swap deep link from a planning request.

    Required: token_in, token_out, amount (in human units, NOT wei)
    Optional: chain_id, exact_field (input|output), slippage_bps
    """
    token_in  = payload.get("token_in")
    token_out = payload.get("token_out")
    amount    = payload.get("amount")
    if not (token_in and token_out and amount):
        return {"ok": False, "error": "token_in, token_out, amount are required"}
    chain_id = int(payload.get("chain_id", 1))
    chain    = CHAIN_NAME.get(chain_id, str(chain_id))
    exact_field = payload.get("exact_field", "input")

    params = {
        "inputCurrency": token_in,
        "outputCurrency": token_out,
        "exactAmount": str(amount),
        "exactField": exact_field,
        "chain": chain,
    }
    if "slippage_bps" in payload:
        params["slippage"] = str(int(payload["slippage_bps"]) / 100)  # bps→percent
    url = f"{INTERFACE_BASE}/swap?{urlencode(params)}"
    return {
        "ok": True,
        "skill": "swap-planner",
        "deep_link": url,
        "rationale": (
            f"Generated deep link routes the user to the Uniswap interface "
            f"on chain '{chain}' with {amount} {token_in[:8]}…→{token_out[:8]}… pre-filled "
            f"for '{exact_field}' exact-side."
        ),
    }


# ─── Skill: liquidity-planner ──────────────────────────────────────────
def run_liquidity_planner(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate an app.uniswap.org/positions deep link for LP creation."""
    token_a = payload.get("token_a")
    token_b = payload.get("token_b")
    if not (token_a and token_b):
        return {"ok": False, "error": "token_a and token_b are required"}
    chain_id = int(payload.get("chain_id", 1))
    chain    = CHAIN_NAME.get(chain_id, str(chain_id))
    fee      = int(payload.get("fee_tier", 3000))   # 0.30% default
    protocol = payload.get("protocol", "v3")        # v2 | v3 | v4
    params = {
        "currencyA": token_a,
        "currencyB": token_b,
        "feeAmount": fee,
        "chain": chain,
    }
    if "min_price" in payload: params["minPrice"] = payload["min_price"]
    if "max_price" in payload: params["maxPrice"] = payload["max_price"]
    url = f"{INTERFACE_BASE}/positions/create/{protocol}?{urlencode(params)}"
    return {
        "ok": True,
        "skill": "liquidity-planner",
        "deep_link": url,
        "rationale": (
            f"LP creation deep link for {token_a[:8]}…/{token_b[:8]}… "
            f"on {chain} via Uniswap {protocol.upper()} at {fee/10000:.2f}% fee tier."
        ),
    }


# ─── Skill: pay-with-any-token ─────────────────────────────────────────
async def run_pay_with_any_token(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Plan a swap to settle an HTTP 402 / MPP challenge.

    Required: challenge_amount, challenge_token, payment_token, swapper, chain_id
    Returns: a quote in EXACT_OUTPUT mode + step-by-step settlement plan.
    """
    required = ["challenge_amount", "challenge_token", "payment_token"]
    for r in required:
        if not payload.get(r):
            return {"ok": False, "error": f"{r} is required"}

    swapper = payload.get("swapper", "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    chain_id = int(payload.get("chain_id", 1))

    try:
        from tools.uniswap_api_tool import UniswapAPITool, UniswapAPIConfig
        cfg = UniswapAPIConfig(chain_id=chain_id)
        tool = UniswapAPITool(config=cfg)
    except Exception as e:
        return {"ok": False, "error": f"trade-api tool unavailable: {e}"}

    quote_payload = {
        "type": "EXACT_OUTPUT",
        "amount_in": str(payload["challenge_amount"]),  # repurposed to "exact amount" by tool
        "amount": str(payload["challenge_amount"]),
        "token_in": payload["payment_token"],
        "token_out": payload["challenge_token"],
        "swapper": swapper,
        "chain_id_in": chain_id, "chain_id_out": chain_id, "chain_id": chain_id,
    }
    quote = await tool.execute("quote", quote_payload)
    if not quote.get("ok"):
        return {"ok": False, "skill": "pay-with-any-token", "error": "quote failed", "detail": quote}

    q = quote.get("quote", {})
    return {
        "ok": True,
        "skill": "pay-with-any-token",
        "steps": [
            {"n": 1, "step": "approve",
             "detail": f"approve(Permit2, MaxUint256) on {payload['payment_token'][:10]}… (one-time per token)"},
            {"n": 2, "step": "sign-permit",
             "detail": "sign EIP-712 permitData returned by /v1/quote"},
            {"n": 3, "step": "swap",
             "detail": f"trade {q.get('input', {}).get('amount')} {payload['payment_token'][:10]}… for exactly {payload['challenge_amount']} {payload['challenge_token'][:10]}…"},
            {"n": 4, "step": "settle-402",
             "detail": "send the received tokens to the x402/MPP challenge endpoint"},
        ],
        "quote": q,
        "input_required": q.get("input", {}).get("amount"),
        "output_exact":   q.get("output", {}).get("amount"),
        "rationale": "Used /v1/quote with type=EXACT_OUTPUT to compute the minimum input amount for paying the exact 402 challenge.",
    }


# ─── Skill: swap-integration ───────────────────────────────────────────
def run_swap_integration(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Emit working code (Python or TypeScript) for the requested integration."""
    lang = payload.get("language", "python").lower()
    token_in = payload.get("token_in", "0x0000000000000000000000000000000000000000")
    token_out = payload.get("token_out", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
    amount = payload.get("amount", "1000000000000000000")

    if lang in ("python", "py"):
        code = f"""\
# pip install aiohttp eth-account web3
import asyncio
from tools.uniswap_api_tool import UniswapAPITool, UniswapAPIConfig

async def main():
    tool = UniswapAPITool(
        swapper_pk="0x...",  # YOUR funded mainnet key
        config=UniswapAPIConfig(chain_id=1, rpc_url="https://eth.drpc.org"),
    )
    result = await tool.execute("swap", {{
        "token_in":  "{token_in}",
        "token_out": "{token_out}",
        "amount_in": "{amount}",
    }})
    print(result)   # {{ok, tx_hash, block, gas_used, amount_out_quoted, amount_out_min}}

asyncio.run(main())
"""
    elif lang in ("typescript", "ts", "viem"):
        code = f"""\
// npm i viem
import {{ createWalletClient, http, parseEther }} from 'viem';
import {{ mainnet }} from 'viem/chains';
import {{ privateKeyToAccount }} from 'viem/accounts';

const account = privateKeyToAccount('0x...');
const client = createWalletClient({{ account, chain: mainnet, transport: http() }});

const quote = await fetch('https://trade-api.gateway.uniswap.org/v1/quote', {{
  method: 'POST',
  headers: {{
    'Content-Type': 'application/json',
    'x-api-key': process.env.UNISWAP_TRADE_API_KEY!,
    'x-universal-router-version': '2.0',
  }},
  body: JSON.stringify({{
    type: 'EXACT_INPUT',
    amount: '{amount}',
    tokenIn:  '{token_in}',
    tokenOut: '{token_out}',
    tokenInChainId:  '1',
    tokenOutChainId: '1',
    swapper: account.address,
    autoSlippage: 'DEFAULT',
    routingPreference: 'BEST_PRICE',
  }}),
}}).then(r => r.json());

// Sign permit if needed (ERC20 input), then POST /v1/swap
// Full flow: see openagents/uniswap/docs/UNISWAP_API.md
"""
    else:
        return {"ok": False, "error": f"unsupported language '{lang}' (try python or typescript)"}

    return {
        "ok": True, "skill": "swap-integration", "language": lang, "code": code,
        "usage_notes": (
            "Production wrapper at tools/uniswap_api_tool.py handles approval, "
            "permit2 signing, and broadcast. The TS example uses viem for the "
            "tx side; permit signing requires permit2-sdk or manual EIP-712."
        ),
    }


# ─── Skill: viem-integration ───────────────────────────────────────────
def run_viem_integration(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Scaffold viem TypeScript boilerplate for a contract address."""
    contract = payload.get("contract", "0x66a9893cC07D91D95644AEDD05D03f95e1dBA8Af")
    chain_id = int(payload.get("chain_id", 1))
    chain_imp = {1: "mainnet", 8453: "base", 42161: "arbitrum", 10: "optimism"}.get(chain_id, "mainnet")
    code = f"""\
// npm i viem wagmi
import {{ createPublicClient, http }} from 'viem';
import {{ {chain_imp} }} from 'viem/chains';

const client = createPublicClient({{
  chain: {chain_imp},
  transport: http(),
}});

// Read a contract
const result = await client.readContract({{
  address: '{contract}' as `0x${{string}}`,
  abi: [...],   // your ABI
  functionName: 'yourFn',
  args: [],
}});

// For wallet writes, swap createPublicClient → createWalletClient with account.
"""
    return {"ok": True, "skill": "viem-integration", "code": code, "language": "typescript"}


# ─── Skill: v4-security-foundations ────────────────────────────────────
V4_SECURITY_CHECKLIST = [
    {"id": "S1", "title": "beforeSwapReturnDelta drift",
     "severity": "high",
     "detail": "If beforeSwap returns a non-zero delta, the pool's invariant can be violated. Always return BalanceDelta.wrap(0) unless you intentionally implement a hook fee or rebate."},
    {"id": "S2", "title": "Reentrancy via afterSwap into router",
     "severity": "high",
     "detail": "afterSwap with arbitrary external calls + token transfers is a re-entry hazard. Wrap state mutations + token moves with a reentrancy guard or use the lock-acquired check on PoolManager."},
    {"id": "S3", "title": "Permission flag mismatch (Hook address bits)",
     "severity": "critical",
     "detail": "Hook address LSBs encode which callbacks are enabled. Mining a hook address with the wrong flags makes other callbacks no-ops silently. Use HookMiner / verify Hooks.validateHookPermissions()."},
    {"id": "S4", "title": "Native ETH handling in afterSwap",
     "severity": "medium",
     "detail": "Currency.wrap(address(0)) refers to native ETH. Forwarding ETH from afterSwap requires call{value:} not transfer; gas stipend bugs."},
    {"id": "S5", "title": "Liquidity / sqrtPrice donation attack on init",
     "severity": "medium",
     "detail": "First afterInitialize call may receive seeded liquidity at attacker-controlled sqrtPrice. Validate sqrtPriceX96 bounds against TWAP."},
    {"id": "S6", "title": "Hook upgradeability boundary",
     "severity": "high",
     "detail": "If the hook is a proxy and admin keys exist, treat as a privileged upgrade vector. Document upgrade timelocks; consider immutable hooks."},
    {"id": "S7", "title": "Cross-pool griefing (sharing storage between hooks)",
     "severity": "medium",
     "detail": "Hooks shared across pools can have one pool grief another (storage exhaustion, gas bombing). Use per-pool storage slots; cap loops."},
    {"id": "S8", "title": "Front-running via afterAddLiquidity callback",
     "severity": "medium",
     "detail": "If afterAddLiquidity reads pool state to decide a hook fee, MEV bots can sandwich the call. Use checkpointed values from beforeAddLiquidity."},
]

def run_v4_security_foundations(payload: Dict[str, Any]) -> Dict[str, Any]:
    flags = payload.get("hook_flags") or []
    addr  = payload.get("hook_addr")
    relevant = V4_SECURITY_CHECKLIST
    if flags:
        # Filter to checks relevant to enabled callbacks (rough heuristic)
        flag_kw = {
            "beforeSwap": ["beforeSwap", "S1"],
            "afterSwap":  ["afterSwap", "S2", "S4"],
            "afterInitialize": ["afterInitialize", "S5"],
            "afterAddLiquidity": ["afterAddLiquidity", "S8"],
        }
        wanted = set()
        for fl in flags:
            for kw in flag_kw.get(fl, []):
                wanted.add(kw)
        if wanted:
            relevant = [c for c in V4_SECURITY_CHECKLIST
                        if c["id"] in wanted or any(kw in c["title"] for kw in wanted)]
    return {
        "ok": True, "skill": "v4-security-foundations",
        "hook_addr": addr,
        "checklist": relevant,
        "summary": f"{len(relevant)} of {len(V4_SECURITY_CHECKLIST)} checks relevant; review before deployment.",
        "rationale": "Curated from common Uniswap v4 hook audit findings.",
    }


# ─── Skill: configurator (CCA — agent-first stub) ──────────────────────
def run_configurator_stub(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True, "skill": "configurator", "agent_first": True,
        "manifest": SKILL_BY_NAME["configurator"],
        "install_cmd": INSTALL_CMD,
        "hint": (
            "This skill configures CCA (Custodial Cross-chain Auction) auction "
            "parameters for a new deployment. Designed to run inside Claude Code "
            "or Cursor with the Uniswap AI plugin installed. From a session, "
            "invoke with `/configurator` and supply the auction context "
            "(asset, duration, reserve, bid increments)."
        ),
        "input_template": {
            "asset": "<address>",
            "duration_seconds": "<int>",
            "reserve_price": "<wei>",
            "bid_increment_bps": 100,
        },
    }


def run_deployer_stub(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True, "skill": "deployer", "agent_first": True,
        "manifest": SKILL_BY_NAME["deployer"],
        "install_cmd": INSTALL_CMD,
        "hint": (
            "Deploy CCA contracts using the official factory pattern. Run from "
            "Claude Code/Cursor with `/deployer` after `/configurator` has "
            "produced the auction params. Server-side, this would require the "
            "factory address + signed deploy tx — not safe to expose unattended."
        ),
        "input_template": {
            "factory_addr": "<CCA factory address>",
            "config_blob":  "<output of /configurator>",
            "deployer_pk":  "<signer key — never expose>",
        },
    }


# ─── Dispatcher ────────────────────────────────────────────────────────
async def run_skill(name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Single entry point for both human (UI) and agent (BDI) skill calls."""
    payload = payload or {}
    if name not in SKILL_BY_NAME:
        return {"ok": False, "error": f"unknown skill '{name}'",
                "valid": [s["name"] for s in SKILLS]}
    if name == "swap-planner":               return run_swap_planner(payload)
    if name == "liquidity-planner":          return run_liquidity_planner(payload)
    if name == "pay-with-any-token":         return await run_pay_with_any_token(payload)
    if name == "swap-integration":           return run_swap_integration(payload)
    if name == "viem-integration":           return run_viem_integration(payload)
    if name == "v4-security-foundations":    return run_v4_security_foundations(payload)
    if name == "configurator":               return run_configurator_stub(payload)
    if name == "deployer":                   return run_deployer_stub(payload)
    return {"ok": False, "error": "unimplemented"}
