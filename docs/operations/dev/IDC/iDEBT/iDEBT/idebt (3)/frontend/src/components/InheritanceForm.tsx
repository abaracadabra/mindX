import { useMemo, useState } from "react";
import { useAccount, useWriteContract } from "wagmi";
import { type Address, parseUnits } from "viem";
import { IDebtSDK, type HeirInput } from "@deltaverse/idebt-api";

import { panel, field, button, buttonSecondary, label, tokens } from "./ui.js";
import { useAddresses } from "../hooks/useAddresses.js";

const IDEBT_ABI = [
  {
    type: "function", name: "openPosition", stateMutability: "nonpayable",
    inputs: [
      { name: "principal", type: "uint256" },
      { name: "maturity",  type: "uint64"  },
      { name: "dormancy",  type: "uint64"  },
      {
        name: "heirs", type: "tuple[]",
        components: [
          { name: "successor", type: "address" },
          { name: "sharesBps", type: "uint16"  },
          { name: "proofRoot", type: "bytes32" }
        ]
      }
    ],
    outputs: [{ name: "tokenId", type: "uint256" }]
  }
] as const;

interface HeirRow { successor: string; sharesBps: string; }

const defaultRow: HeirRow = { successor: "", sharesBps: "0" };

export function InheritanceForm() {
  const { address } = useAccount();
  const addresses = useAddresses();
  const { writeContractAsync, isPending } = useWriteContract();

  const [principal, setPrincipal] = useState("1000");
  const [maturityDays, setMaturityDays] = useState("180");
  const [dormancyDays, setDormancyDays] = useState("30");
  const [rows, setRows] = useState<HeirRow[]>([{ ...defaultRow }]);
  const [status, setStatus] = useState<{ kind: "idle" | "ok" | "err"; msg?: string }>({ kind: "idle" });

  const shareSum = useMemo(
    () => rows.reduce((acc, r) => acc + (Number(r.sharesBps) || 0), 0),
    [rows]
  );

  const valid = rows.every(r => r.successor.startsWith("0x") && r.successor.length === 42)
    && shareSum === 10_000
    && Number(principal) > 0;

  function setRow(i: number, patch: Partial<HeirRow>) {
    setRows(prev => prev.map((r, j) => j === i ? { ...r, ...patch } : r));
  }

  async function onSubmit() {
    if (!address || !addresses) { setStatus({ kind: "err", msg: "Connect a wallet on a supported chain." }); return; }
    if (!valid) { setStatus({ kind: "err", msg: "Fix validation errors first." }); return; }

    const heirs: HeirInput[] = rows.map(r => ({
      successor: r.successor as Address,
      sharesBps: Number(r.sharesBps)
    }));
    const { root } = IDebtSDK.buildHeirTree(heirs);

    try {
      setStatus({ kind: "idle", msg: "Submitting…" });
      const tx = await writeContractAsync({
        address: addresses.debtToken,
        abi:     IDEBT_ABI,
        functionName: "openPosition",
        args: [
          parseUnits(principal, 18),
          BigInt(Math.floor(Date.now() / 1000) + Number(maturityDays) * 86_400),
          BigInt(Number(dormancyDays) * 86_400),
          heirs.map(h => ({
            successor: h.successor,
            sharesBps: h.sharesBps,
            proofRoot: root
          }))
        ]
      });
      setStatus({ kind: "ok", msg: `Submitted: ${tx}` });
    } catch (e) {
      setStatus({ kind: "err", msg: (e as Error).message });
    }
  }

  return (
    <div style={panel}>
      <div style={{ color: tokens.textDim, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>
        Open an iDEBT position
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
        <div>
          <div style={label("Principal")}>Principal (settlement token, 18dp)</div>
          <input style={field} value={principal} onChange={e => setPrincipal(e.target.value)} />
        </div>
        <div>
          <div style={label("Maturity")}>Maturity (days)</div>
          <input style={field} value={maturityDays} onChange={e => setMaturityDays(e.target.value)} />
        </div>
        <div>
          <div style={label("Dormancy")}>Dormancy (days)</div>
          <input style={field} value={dormancyDays} onChange={e => setDormancyDays(e.target.value)} />
        </div>
      </div>

      <div style={{ marginBottom: 8, display: "flex", justifyContent: "space-between" }}>
        <span style={{ color: tokens.textDim, fontSize: 11, letterSpacing: 1, textTransform: "uppercase" }}>Heirs</span>
        <span style={{ color: shareSum === 10_000 ? tokens.accent : tokens.warn, fontSize: 12 }}>
          shares total: {shareSum} / 10000 bps
        </span>
      </div>

      {rows.map((r, i) => (
        <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 140px auto", gap: 8, marginBottom: 8 }}>
          <input style={field} placeholder="0x…" value={r.successor} onChange={e => setRow(i, { successor: e.target.value })} />
          <input style={field} placeholder="bps (0-10000)" value={r.sharesBps} onChange={e => setRow(i, { sharesBps: e.target.value })} />
          <button style={buttonSecondary} onClick={() => setRows(rows.filter((_, j) => j !== i))} disabled={rows.length === 1}>
            remove
          </button>
        </div>
      ))}

      <button style={buttonSecondary} onClick={() => setRows([...rows, { ...defaultRow }])}>+ add heir</button>

      <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 12 }}>
        <button style={button} onClick={onSubmit} disabled={!valid || isPending}>
          {isPending ? "Submitting…" : "Open position"}
        </button>
        {status.kind !== "idle" && (
          <span style={{ color: status.kind === "ok" ? tokens.accent : tokens.danger, fontSize: 12 }}>
            {status.msg}
          </span>
        )}
      </div>

      <p style={{ marginTop: 24, fontSize: 12, color: tokens.textDim, lineHeight: 1.5 }}>
        Note: opening requires a prior <code>approve()</code> on the settlement token and, if the x402
        gateway is wired, a valid Parsec receipt for <code>iDEBT.open</code>. Use the x402 tab to pay.
      </p>
    </div>
  );
}
