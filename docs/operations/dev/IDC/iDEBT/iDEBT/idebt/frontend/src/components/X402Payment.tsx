import { useState } from "react";
import { useAccount, useChainId, useWriteContract } from "wagmi";
import { ParsecX402Client, type X402ReceiptBundle } from "@deltaverse/idebt-api";

import { panel, field, button, buttonSecondary, label, tokens } from "./ui.js";
import { useAddresses } from "../hooks/useAddresses.js";

const GATEWAY_ABI = [
  {
    type: "function", name: "consume", stateMutability: "nonpayable",
    inputs: [
      {
        name: "r", type: "tuple",
        components: [
          { name: "facilitator", type: "address" },
          { name: "payer",       type: "address" },
          { name: "amount",      type: "uint256" },
          { name: "asset",       type: "bytes32" },
          { name: "scope",       type: "bytes32" },
          { name: "nonce",       type: "uint64"  },
          { name: "expiry",      type: "uint64"  },
          { name: "algoTxId",    type: "bytes32" }
        ]
      },
      { name: "sig", type: "bytes" }
    ],
    outputs: []
  }
] as const;

const client = new ParsecX402Client();

const SCOPES = [
  { label: "iDEBT.open",  value: "iDEBT.open"  },
  { label: "iDEBT.claim", value: "iDEBT.claim" }
];

export function X402Payment() {
  const { address } = useAccount();
  const chainId = useChainId();
  const addresses = useAddresses();
  const { writeContractAsync, isPending } = useWriteContract();

  const [scopeLabel, setScopeLabel] = useState(SCOPES[0]!.value);
  const [stage, setStage] = useState<"idle" | "intent" | "waiting" | "receipt" | "consumed" | "error">("idle");
  const [intent, setIntent] = useState<{ amount: bigint; asset: string; facilitatorAlgoAddress: string; expires: number; nonce: string } | null>(null);
  const [bundle, setBundle] = useState<X402ReceiptBundle | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const scope = ParsecX402Client.scope(scopeLabel);

  async function createIntent() {
    if (!address) { setErr("Connect a wallet."); setStage("error"); return; }
    setErr(null);
    setStage("intent");
    try {
      const i = await client.createIntent(address, scope, chainId);
      setIntent({
        amount: i.amount,
        asset: i.assetSymbol,
        facilitatorAlgoAddress: i.facilitatorAlgoAddress,
        expires: i.expires,
        nonce: i.nonce
      });
      setStage("waiting");
      const b = await client.waitForReceipt(i.nonce, { intervalMs: 3_000, timeoutMs: 180_000 });
      setBundle(b);
      setStage("receipt");
    } catch (e) {
      setErr((e as Error).message);
      setStage("error");
    }
  }

  async function consume() {
    if (!bundle || !addresses) return;
    try {
      const { receipt, signature } = bundle;
      await writeContractAsync({
        address: addresses.x402,
        abi:     GATEWAY_ABI,
        functionName: "consume",
        args: [{
          facilitator: receipt.facilitator,
          payer:       receipt.payer,
          amount:      receipt.amount,
          asset:       receipt.asset,
          scope:       receipt.scope,
          nonce:       receipt.nonce,
          expiry:      receipt.expiry,
          algoTxId:    receipt.algoTxId
        }, signature]
      });
      setStage("consumed");
    } catch (e) {
      setErr((e as Error).message);
      setStage("error");
    }
  }

  return (
    <div style={panel}>
      <div style={{ color: tokens.textDim, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>
        x402 payment (Parsec / Algorand)
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 12, alignItems: "end", marginBottom: 16 }}>
        <div>
          <div style={label("Scope")}>Scope</div>
          <select style={field} value={scopeLabel} onChange={e => setScopeLabel(e.target.value)}>
            {SCOPES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <button style={button} onClick={createIntent} disabled={stage === "intent" || stage === "waiting"}>
          {stage === "intent" ? "Creating…" : stage === "waiting" ? "Waiting for Algorand settlement…" : "Create payment intent"}
        </button>
      </div>

      {intent && (
        <div style={{ ...panel, background: tokens.bgField, marginBottom: 16 }}>
          <div style={label("Pay from parsec-wallet")}>Pay from parsec-wallet</div>
          <Row k="Amount" v={`${intent.amount.toString()} ${intent.asset}`} />
          <Row k="To (Algorand)" v={<span style={{ fontFamily: "monospace" }}>{intent.facilitatorAlgoAddress}</span>} />
          <Row k="Nonce" v={<span style={{ fontFamily: "monospace" }}>{intent.nonce.slice(0, 22)}…</span>} />
          <Row k="Expires" v={new Date(intent.expires * 1000).toUTCString()} />
        </div>
      )}

      {bundle && (
        <div style={{ ...panel, background: tokens.bgField, marginBottom: 16 }}>
          <div style={label("Receipt ready")}>Receipt ready</div>
          <Row k="Algorand tx" v={<span style={{ fontFamily: "monospace" }}>{bundle.receipt.algoTxId.slice(0, 22)}…</span>} />
          <Row k="Facilitator" v={<span style={{ fontFamily: "monospace" }}>{bundle.receipt.facilitator}</span>} />
          <button style={{ ...button, marginTop: 12 }} onClick={consume} disabled={isPending || stage === "consumed"}>
            {stage === "consumed" ? "Consumed ✓" : isPending ? "Submitting…" : "Submit to gateway"}
          </button>
        </div>
      )}

      {stage === "consumed" && (
        <div style={{ color: tokens.accent, fontSize: 13 }}>
          Paid — scope is now unlocked for your address until receipt expiry.
        </div>
      )}

      {err && (
        <div style={{ color: tokens.danger, fontSize: 13, marginTop: 8 }}>
          {err}
        </div>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 12, padding: "6px 0", borderBottom: `1px solid ${tokens.border}` }}>
      <span style={{ color: tokens.textDim, minWidth: 130 }}>{k}</span>
      <span>{v}</span>
    </div>
  );
}
