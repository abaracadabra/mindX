// SPDX-License-Identifier: Apache-2.0
//
// BankonDeploy.tsx — production React component for the bankon.eth subdomain
// minter + agent registry + generic ABI explorer. Drop into any React/Next app:
//
//   import { BankonDeploy } from "@bankoneth/react";
//   <BankonDeploy publicBase="/bankon" />
//
// Self-contained: raw window.ethereum (EIP-6963-friendly) + ethers v6 + the
// shared forms logic. No wagmi/RainbowKit required (but compatible — pass your
// own provider via `getProvider`). `.tsx` is the production React surface;
// the `.js` prototype is packages/web/bankoneth.html.

import { useCallback, useEffect, useMemo, useState } from "react";
import { ethers } from "ethers";
import * as F from "./bankon-forms.js";

const CHAINS: Record<number, string> = { 1: "Ethereum", 11155111: "Sepolia", 31337: "Anvil (local)" };

export interface BankonDeployProps {
  /** URL of the served packages/web/public dir (manifest + abis + deployments). */
  publicBase?: string;
  /** Optionally supply your own EIP-1193 provider (wagmi, RainbowKit, …). */
  getProvider?: () => Promise<{ request(a: { method: string; params?: unknown[] }): Promise<unknown> } | null>;
  className?: string;
}

type Tab = "presets" | "explorer";

export function BankonDeploy({ publicBase = "/bankon", getProvider, className }: BankonDeployProps) {
  const [account, setAccount] = useState<string | null>(null);
  const [chainId, setChainId] = useState<number | null>(null);
  const [bp, setBp] = useState<InstanceType<typeof ethers.BrowserProvider> | null>(null);
  const [manifest, setManifest] = useState<F.Manifest | null>(null);
  const [deployments, setDeployments] = useState<F.Deployments | null>(null);
  const [tab, setTab] = useState<Tab>("presets");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    F.loadManifest(publicBase).then(setManifest).catch((e) => setErr(String(e)));
  }, [publicBase]);

  useEffect(() => {
    if (chainId != null) F.loadDeployments(publicBase, chainId).then(setDeployments).catch(() => setDeployments(null));
  }, [publicBase, chainId]);

  const connect = useCallback(async () => {
    try {
      const provider = getProvider
        ? await getProvider()
        : ((globalThis as { ethereum?: { request(a: { method: string; params?: unknown[] }): Promise<unknown> } }).ethereum ?? null);
      if (!provider) { setErr("No EVM wallet found — install MetaMask."); return; }
      const accts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
      const cid = parseInt((await provider.request({ method: "eth_chainId" })) as string, 16);
      setAccount(accts[0]);
      setChainId(cid);
      setBp(new ethers.BrowserProvider(provider as never));
      setErr(null);
    } catch (e) {
      setErr(message(e));
    }
  }, [getProvider]);

  const requireAddress = useCallback(
    (key: string, title: string) => {
      const a = deployments ? F.addressFor(deployments, key) : null;
      if (!a) throw new Error(`${title} not deployed on ${CHAINS[chainId ?? 0] || "this chain"} (zero in deployments/${F.constants.deploymentFileFor(chainId ?? 0)}).`);
      return a;
    },
    [deployments, chainId],
  );

  return (
    <div className={className ?? "bankon-deploy"} style={S.root}>
      <div style={S.bar}>
        {account ? (
          <>
            <span style={S.tagOk}>{account.slice(0, 6)}…{account.slice(-4)}</span>
            <span style={S.tag}>{chainId ? CHAINS[chainId] || `chain ${chainId}` : "…"}</span>
          </>
        ) : (
          <button style={S.primary} onClick={() => void connect()}>Connect wallet</button>
        )}
      </div>
      <div style={S.tabs}>
        <button style={tab === "presets" ? S.tabActive : S.tabBtn} onClick={() => setTab("presets")}>Mint &amp; flows</button>
        <button style={tab === "explorer" ? S.tabActive : S.tabBtn} onClick={() => setTab("explorer")}>Contract explorer</button>
      </div>
      {err && <div style={S.err}>{err}</div>}
      {!manifest ? (
        <div style={S.note}>Loading manifest…</div>
      ) : tab === "presets" ? (
        <Presets manifest={manifest} account={account} bp={bp} publicBase={publicBase} requireAddress={requireAddress} />
      ) : (
        <Explorer manifest={manifest} account={account} bp={bp} publicBase={publicBase} requireAddress={requireAddress} />
      )}
    </div>
  );
}

type Shared = {
  manifest: F.Manifest;
  account: string | null;
  bp: InstanceType<typeof ethers.BrowserProvider> | null;
  publicBase: string;
  requireAddress: (key: string, title: string) => string;
};

function Presets({ manifest, account, bp, publicBase, requireAddress }: Shared) {
  const [open, setOpen] = useState<F.Preset | null>(null);
  if (!open) {
    return (
      <div style={S.grid}>
        {manifest.presets.map((p) => (
          <div key={p.id} style={S.card} onClick={() => setOpen(p)}>
            <h3 style={S.h3}>{p.title}</h3>
            <div style={S.muted}>{p.subtitle}</div>
          </div>
        ))}
      </div>
    );
  }
  return <PresetForm preset={open} onBack={() => setOpen(null)} manifest={manifest} account={account} bp={bp} publicBase={publicBase} requireAddress={requireAddress} />;
}

function PresetForm({ preset, onBack, manifest, account, bp, publicBase, requireAddress }: Shared & { preset: F.Preset; onBack: () => void }) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const f of preset.fields) init[f.name] = f.fill === "account" && account ? account : f.default ?? "";
    return init;
  });
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  const run = useCallback(async () => {
    setOut(""); setBusy(true);
    try {
      const c = manifest.contracts.find((x) => x.deploymentKey === preset.contract)!;
      const address = requireAddress(c.deploymentKey, c.title);
      const abi = await F.loadAbi(publicBase, c);
      if (preset.flow === "resolve") {
        const node = F.namehash(ethers, values.name);
        const addr = await F.readContract({ provider: bp, address, abi, fn: "addr", args: [node], ethers });
        const text = values.key ? await F.readContract({ provider: bp, address, abi, fn: "text", args: [node, values.key], ethers }) : "";
        setOut(`namehash: ${node}\naddr(): ${addr}` + (values.key ? `\ntext(${values.key}): ${text || "(empty)"}` : ""));
        return;
      }
      const args = F.buildPresetArgs(preset, values, { ethers, account });
      if (preset.mode === "read") {
        setOut(stringify(await F.readContract({ provider: bp, address, abi, fn: preset.fn!, args, ethers })));
        return;
      }
      if (!bp) throw new Error("connect a wallet first");
      setOut("awaiting signature…");
      const signer = await bp.getSigner();
      const tx = await F.writeContract({ signer, address, abi, fn: preset.fn!, args, value: preset.payable ? 0n : undefined, ethers });
      setOut("sent: " + tx.hash + "\nwaiting…");
      const r = await tx.wait();
      setOut(`✅ confirmed in block ${r.blockNumber}\n${tx.hash}`);
    } catch (e) {
      setOut("✗ " + message(e));
    } finally {
      setBusy(false);
    }
  }, [preset, values, manifest, account, bp, publicBase, requireAddress]);

  return (
    <div>
      <button style={S.link} onClick={onBack}>← all flows</button>
      <h3 style={S.h3}>{preset.title}</h3>
      {preset.note && <div style={S.note}>{preset.note}</div>}
      {!account && <div style={S.note}>Connect a wallet to submit.</div>}
      {preset.fields.map((f) => (
        <label key={f.name} style={S.field}>
          <span style={S.lbl}>{f.label || f.name} <code>{f.type}</code>{f.optional ? " · optional" : ""}</span>
          <input style={S.input} value={values[f.name] ?? ""} placeholder={f.placeholder || f.default || ""}
            onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))} />
        </label>
      ))}
      <button style={S.primary} disabled={busy} onClick={() => void run()}>{preset.mode === "read" ? "Query" : "Submit transaction"}</button>
      {out && <pre style={S.result}>{out}</pre>}
    </div>
  );
}

function Explorer({ manifest, account, bp, publicBase, requireAddress }: Shared) {
  void account;
  const [key, setKey] = useState("");
  const [abi, setAbi] = useState<F.AbiFn[] | null>(null);
  const [address, setAddress] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!key) { setAbi(null); return; }
    const c = manifest.contracts.find((x) => x.deploymentKey === key);
    if (!c) return;
    setError(null);
    F.loadAbi(publicBase, c).then((a) => {
      setAbi(a);
      try { setAddress(requireAddress(c.deploymentKey, c.title)); } catch (e) { setError(message(e)); setAddress(""); }
    }).catch((e) => setError(message(e)));
  }, [key, manifest, publicBase, requireAddress]);

  const cats = useMemo(() => (abi ? F.categorizeAbi(abi) : null), [abi]);

  return (
    <div>
      <div style={S.note}>Pick a deployed bankon contract; reads query instantly, writes prompt your wallet.</div>
      <select style={S.input} value={key} onChange={(e) => setKey(e.target.value)}>
        <option value="">— select —</option>
        {manifest.contracts.map((c) => <option key={c.deploymentKey} value={c.deploymentKey}>{c.title} · {c.name}</option>)}
      </select>
      {error && <div style={S.err}>{error}</div>}
      {cats && abi && (
        <>
          {address && <div style={S.tag}>{address}</div>}
          <h3 style={S.h3}>Read ({cats.reads.length})</h3>
          {cats.reads.map((fn) => <FnCard key={fn.name} fn={fn} abi={abi} address={address} bp={bp} write={false} />)}
          <h3 style={S.h3}>Write ({cats.writes.length})</h3>
          {cats.writes.map((fn) => <FnCard key={fn.name} fn={fn} abi={abi} address={address} bp={bp} write={true} />)}
        </>
      )}
    </div>
  );
}

function FnCard({ fn, abi, address, bp, write }: { fn: F.AbiFn; abi: F.AbiFn[]; address: string; bp: InstanceType<typeof ethers.BrowserProvider> | null; write: boolean }) {
  const payable = fn.stateMutability === "payable";
  const [vals, setVals] = useState<string[]>(() => fn.inputs.map(() => ""));
  const [value, setValue] = useState("");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  const go = useCallback(async () => {
    setOut("…"); setBusy(true);
    try {
      const args = fn.inputs.map((i, idx) => F.coerceArg(i.type, vals[idx]));
      if (!write) {
        setOut(stringify(await F.readContract({ provider: bp, address, abi, fn: fn.name, args, ethers })));
      } else {
        if (!bp) throw new Error("connect a wallet first");
        const signer = await bp.getSigner();
        const v = value ? ethers.parseEther(value) : undefined;
        const tx = await F.writeContract({ signer, address, abi, fn: fn.name, args, value: v, ethers });
        setOut("sent: " + tx.hash + "\nwaiting…");
        const r = await tx.wait();
        setOut(`✅ block ${r.blockNumber}\n${tx.hash}`);
      }
    } catch (e) { setOut("✗ " + message(e)); } finally { setBusy(false); }
  }, [fn, vals, value, abi, address, bp, write]);

  return (
    <div style={S.fn}>
      <div style={S.sig}>{F.signatureOf(fn)} <span style={S.muted}>{fn.stateMutability}</span></div>
      {fn.inputs.map((i, idx) => (
        <label key={idx} style={S.field}>
          <span style={S.lbl}>{i.name || "arg"} <code>{i.type}</code></span>
          <input style={S.input} placeholder={i.type} value={vals[idx]} onChange={(e) => setVals((a) => a.map((x, k) => (k === idx ? e.target.value : x)))} />
        </label>
      ))}
      {payable && (
        <label style={S.field}><span style={S.lbl}>value <code>ETH</code></span>
          <input style={S.input} placeholder="0.0" value={value} onChange={(e) => setValue(e.target.value)} /></label>
      )}
      <button style={write ? S.primary : S.btn} disabled={busy} onClick={() => void go()}>{write ? "Write" : "Query"}</button>
      {out && <pre style={S.result}>{out}</pre>}
    </div>
  );
}

function message(e: unknown): string {
  const a = e as { shortMessage?: string; message?: string };
  return a?.shortMessage || a?.message || String(e);
}
function stringify(r: unknown): string {
  if (typeof r === "bigint") return r.toString();
  if (Array.isArray(r)) return r.map(stringify).join("\n");
  if (r && typeof r === "object") { try { return JSON.stringify(r, (_, v) => (typeof v === "bigint" ? v.toString() : v), 2); } catch { return String(r); } }
  return String(r);
}

// Minimal inline styles so the component is drop-in with zero CSS setup.
const S: Record<string, React.CSSProperties> = {
  root: { color: "#e8eaed", background: "#0b0d12", fontFamily: "system-ui, sans-serif", padding: 16, borderRadius: 12 },
  bar: { display: "flex", gap: 8, alignItems: "center", marginBottom: 12 },
  tabs: { display: "flex", gap: 6, marginBottom: 12 },
  tabBtn: { background: "transparent", color: "#9aa0a6", border: "1px solid transparent", borderRadius: 9, padding: "8px 14px", cursor: "pointer" },
  tabActive: { background: "#161a24", color: "#e8eaed", border: "1px solid #232a39", borderRadius: 9, padding: "8px 14px", cursor: "pointer" },
  primary: { background: "#5b78e6", color: "#fff", border: "none", borderRadius: 9, padding: "8px 14px", fontWeight: 600, cursor: "pointer" },
  btn: { background: "#1c2230", color: "#e8eaed", border: "1px solid #232a39", borderRadius: 9, padding: "8px 14px", cursor: "pointer" },
  link: { background: "transparent", color: "#7c9cff", border: "none", cursor: "pointer", padding: "6px 0" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 },
  card: { background: "#161a24", border: "1px solid #232a39", borderRadius: 12, padding: 16, cursor: "pointer" },
  h3: { margin: "8px 0 4px", fontSize: 16 },
  muted: { color: "#9aa0a6", fontSize: 12 },
  note: { background: "#11141c", borderLeft: "3px solid #7c9cff", borderRadius: 6, padding: "8px 12px", color: "#9aa0a6", fontSize: 12.5, margin: "10px 0" },
  field: { display: "block", margin: "12px 0" },
  lbl: { display: "block", fontSize: 12.5, color: "#9aa0a6", marginBottom: 4 },
  input: { width: "100%", background: "#11141c", border: "1px solid #232a39", borderRadius: 8, color: "#e8eaed", padding: "9px 11px", fontFamily: "ui-monospace, monospace", fontSize: 13 },
  result: { whiteSpace: "pre-wrap", wordBreak: "break-all", background: "#0d1017", border: "1px solid #232a39", borderRadius: 8, padding: 10, fontSize: 12.5, marginTop: 8 },
  fn: { border: "1px solid #232a39", borderRadius: 10, padding: "12px 14px", margin: "10px 0", background: "#161a24" },
  sig: { fontFamily: "ui-monospace, monospace", fontSize: 12.5, color: "#7c9cff", marginBottom: 6 },
  tag: { fontSize: 12, color: "#9aa0a6", background: "#11141c", border: "1px solid #232a39", borderRadius: 999, padding: "4px 10px" },
  tagOk: { fontSize: 12, color: "#46d39a", background: "#11141c", border: "1px solid #244e3e", borderRadius: 999, padding: "4px 10px" },
  err: { background: "#1c1416", border: "1px solid #4e2424", color: "#ff6b6b", borderRadius: 8, padding: "8px 12px", margin: "8px 0", fontSize: 13 },
};
