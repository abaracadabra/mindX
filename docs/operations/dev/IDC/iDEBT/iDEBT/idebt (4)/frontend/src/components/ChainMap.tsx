import { CHAINS, type ChainRecord } from "@deltaverse/idebt-api/chainmap";
import deployments from "../config/deployments.json";

import { panel, tokens } from "./ui.js";

type Manifest = Record<string, Record<string, string> | undefined>;

export function ChainMap() {
  const manifest = deployments as unknown as Manifest;

  const groups: Record<string, ChainRecord[]> = {};
  for (const c of CHAINS) (groups[c.family] ??= []).push(c);

  return (
    <div>
      <div style={{ color: tokens.textDim, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>
        Canonical chainmap (mirrors agenticplace.pythai.net/allchain.html)
      </div>

      {Object.entries(groups).map(([family, chains]) => (
        <section key={family} style={{ ...panel, marginBottom: 12 }}>
          <h3 style={{ margin: 0, marginBottom: 12, fontSize: 14, color: tokens.text }}>{family}</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ color: tokens.textDim, textAlign: "left" }}>
                <th style={th}>Chain</th>
                <th style={th}>Chain ID</th>
                <th style={th}>Native gas</th>
                <th style={th}>Stable</th>
                <th style={th}>Deployed?</th>
                <th style={th}>iDEBT</th>
              </tr>
            </thead>
            <tbody>
              {chains.map(c => {
                const deployed = manifest[String(c.chainId)]?.debtToken;
                return (
                  <tr key={c.chainId} style={{ borderTop: `1px solid ${tokens.border}` }}>
                    <td style={td}>{c.name}</td>
                    <td style={td}>{c.chainId}</td>
                    <td style={td}>{c.nativeGas}</td>
                    <td style={td}>{c.stableAnchor}</td>
                    <td style={td}>
                      <span style={{ color: deployed ? tokens.accent : tokens.textDim }}>
                        {deployed ? "live" : "—"}
                      </span>
                    </td>
                    <td style={{ ...td, fontFamily: "monospace", fontSize: 11 }}>
                      {deployed ? short(deployed) : ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

const th: React.CSSProperties = { padding: "6px 8px", fontWeight: 500 };
const td: React.CSSProperties = { padding: "6px 8px" };
function short(addr: string) { return `${addr.slice(0, 6)}…${addr.slice(-4)}`; }
