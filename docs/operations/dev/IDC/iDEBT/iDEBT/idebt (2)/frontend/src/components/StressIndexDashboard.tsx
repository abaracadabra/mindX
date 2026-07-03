import { useEffect, useState } from "react";
import { useReadContract } from "wagmi";
import { formatUnits } from "viem";
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from "recharts";

import { panel, tokens, REGIME_NAMES, regimeColor } from "./ui.js";
import { useAddresses } from "../hooks/useAddresses.js";

const INDEX_ABI = [
  {
    type: "function", name: "latestSnapshot", stateMutability: "view",
    inputs: [],
    outputs: [{
      type: "tuple",
      components: [
        { name: "index",     type: "uint256" },
        { name: "regime",    type: "uint8"   },
        { name: "timestamp", type: "uint64"  },
        { name: "debtGDP",   type: "uint256" },
        { name: "cds",       type: "uint256" },
        { name: "yieldInv",  type: "uint256" },
        { name: "realRate",  type: "uint256" },
        { name: "dxy",       type: "uint256" },
        { name: "vix",       type: "uint256" },
        { name: "gold",      type: "uint256" }
      ]
    }]
  },
  {
    type: "function", name: "score", stateMutability: "view",
    inputs: [], outputs: [{ type: "uint256" }]
  }
] as const;

interface Snapshot {
  index: bigint;
  regime: number;
  timestamp: bigint;
  debtGDP: bigint;
  cds: bigint;
  yieldInv: bigint;
  realRate: bigint;
  dxy: bigint;
  vix: bigint;
  gold: bigint;
}

export function StressIndexDashboard() {
  const addresses = useAddresses();
  const { data: snap, isLoading, error } = useReadContract({
    address: addresses?.index,
    abi: INDEX_ABI,
    functionName: "latestSnapshot",
    query: { enabled: !!addresses?.index, refetchInterval: 15_000 }
  });

  if (!addresses) return <Stub message="Select a chain to read the live stress index." />;
  if (isLoading)  return <Stub message="Reading live stress index…" />;
  if (error)      return <Stub message={`Error: ${error.message}`} danger />;
  if (!snap)      return <Stub message="No snapshot available yet. Trigger a poke()." />;

  const s = snap as unknown as Snapshot;
  const pct = (w: bigint) => Number(formatUnits(w, 18)) * 100;
  const components = [
    { axis: "Debt/GDP",  value: pct(s.debtGDP) },
    { axis: "CDS",       value: pct(s.cds) },
    { axis: "YieldInv",  value: pct(s.yieldInv) },
    { axis: "RealRate",  value: pct(s.realRate) },
    { axis: "DXY",       value: pct(s.dxy) },
    { axis: "VIX",       value: pct(s.vix) },
    { axis: "Gold",      value: pct(s.gold) }
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      <div style={panel}>
        <div style={{ color: tokens.textDim, fontSize: 11, letterSpacing: 1, textTransform: "uppercase" }}>Global Debt Stress Index</div>
        <div style={{ fontSize: 56, fontWeight: 700, marginTop: 8, letterSpacing: -2 }}>
          {pct(s.index).toFixed(2)}<span style={{ fontSize: 24, color: tokens.textDim }}>%</span>
        </div>
        <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            display: "inline-block", width: 10, height: 10, borderRadius: 10,
            background: regimeColor(s.regime)
          }} />
          <span style={{ fontWeight: 600, color: regimeColor(s.regime) }}>
            {REGIME_NAMES[s.regime] ?? "Unknown"}
          </span>
          <span style={{ marginLeft: "auto", color: tokens.textDim, fontSize: 12 }}>
            Updated {new Date(Number(s.timestamp) * 1000).toUTCString()}
          </span>
        </div>
        <div style={{ marginTop: 24, display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
          {components.map(c => (
            <div key={c.axis} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: `1px solid ${tokens.border}` }}>
              <span style={{ color: tokens.textDim }}>{c.axis}</span>
              <span>{c.value.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>

      <div style={panel}>
        <div style={{ color: tokens.textDim, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 16 }}>
          Component radar
        </div>
        <ResponsiveContainer width="100%" height={360}>
          <RadarChart data={components}>
            <PolarGrid stroke={tokens.borderHi} />
            <PolarAngleAxis dataKey="axis" tick={{ fill: tokens.textDim, fontSize: 11 }} />
            <Radar
              name="stress"
              dataKey="value"
              stroke={regimeColor(s.regime)}
              fill={regimeColor(s.regime)}
              fillOpacity={0.3}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Stub({ message, danger }: { message: string; danger?: boolean }) {
  return (
    <div style={{ ...panel, color: danger ? tokens.danger : tokens.textDim }}>
      {message}
    </div>
  );
}
