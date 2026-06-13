// SPDX-License-Identifier: Apache-2.0
//
// agenticplace.ts — BANKON as the AgenticPlace PAYMENT PROCESSOR for MCP service delivery. On each
// x402 settlement the proxy makes, this computes the golden-ratio BANKON fee (φ/10, the cp2048
// standard) that rakes home to bankon.eth, and reports the settlement to AgenticPlace for
// service-delivery accounting. The actual on-chain RAKE is enforced by the cp2048 / x402evm
// contracts; this is the off-chain processor ledger + report.
const PHI_OVER_TEN = 1618033988749894848n; // φ/10 × 1e18 (matches cp2048_constants.PHI_OVER_TEN_WAD)
const WAD = 1_000000000000000000n;

export interface Settlement {
  tool: string; network: string; asset: string; amount: bigint; // 6dp USDC
  resource: string; payTo: string; ts: number;
}

/** The golden BANKON fee on a settlement amount (same φ/10 rate as the on-chain gas/RAKE fee). */
export function goldenFee(amount: bigint): bigint { return (amount * PHI_OVER_TEN) / (10n * WAD); }

export class AgenticPlaceProcessor {
  ledger: Settlement[] = [];
  feesAccrued = 0n;
  constructor(public reportUrl: string | null = process.env.AGENTICPLACE_URL || null,
              public treasury: string = "0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169") {} // bankon.eth

  /** Record a settlement, accrue the φ fee (→ RAKE home to bankon.eth), and report to AgenticPlace. */
  async record(s: Settlement): Promise<{ fee: bigint }> {
    const fee = goldenFee(s.amount);
    this.feesAccrued += fee;
    this.ledger.push(s);
    if (this.reportUrl) {
      try {
        await fetch(`${this.reportUrl.replace(/\/+$/, "")}/x402/settlement`, {
          method: "POST", headers: { "content-type": "application/json" },
          body: JSON.stringify({ ...s, amount: s.amount.toString(), fee: fee.toString(), treasury: this.treasury }),
        });
      } catch { /* reporting is best-effort; settlement already happened on-chain */ }
    }
    return { fee };
  }

  summary() {
    return { calls: this.ledger.length, feesAccrued: this.feesAccrued.toString(), treasury: this.treasury };
  }
}
